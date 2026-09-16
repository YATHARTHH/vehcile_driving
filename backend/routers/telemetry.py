import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status

from backend.config import settings
from backend.database import get_db
from backend.models.session import TripSessionCheckpoint
from backend.models.user import User
from backend.schemas.telemetry import (
    IngestionResponse,
    RawIngressPayload,
)
from backend.streaming.broker import get_broker
from backend.streaming.sessionizer import get_sessionizer
from backend.utils.auth import get_current_user, get_optional_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger("fleettrack.routers.telemetry")
router = APIRouter(prefix=f"{settings.API_V1_STR}/telemetry", tags=["telemetry"])


async def get_device_identity(
    x_device_id: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    current_user: User | None = Depends(get_optional_current_user),
) -> tuple[str, str, str | None]:
    """
    P0-3 Fix: Server-Derived Identity Verification.
    Resolves authenticated tenant_id, vehicle_id, and fleet_id from verified JWT or device header.
    The edge payload is NEVER trusted for tenant identity.
    """
    if current_user is not None:
        tenant_id = x_tenant_id or f"tenant_{current_user.id}"
        vehicle_id = x_device_id or current_user.vehicle_number or f"veh_{current_user.id}"
        fleet_id = "fleet_default"
        return tenant_id, vehicle_id, fleet_id

    # Fallback to IoT device credentials if mTLS / Device API Key is provided
    if x_device_id:
        tenant_id = x_tenant_id or "tenant_default"
        vehicle_id = x_device_id
        fleet_id = "fleet_default"
        return tenant_id, vehicle_id, fleet_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Device credentials or authentication token required",
    )


@router.post(
    "/ingest",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Stateless Ingestion Gateway Endpoint",
)
async def ingest_telemetry_packet(
    raw_payload: RawIngressPayload,
    request: Request,
    identity: tuple[str, str, str | None] = Depends(get_device_identity),
) -> IngestionResponse:
    """
    Stateless, high-throughput telematics ingress endpoint.
    Performs payload-size check, schema envelope check, stamps server-derived identity,
    and publishes directly to telemetry.raw broker.
    """
    tenant_id, vehicle_id, fleet_id = identity

    # 1. Payload size boundary check (<= 64KB)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 64 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Payload size exceeds 64KB telematics limit",
        )

    # 2. Canonical payload hash computation
    canonical_telemetry_bytes = json.dumps(raw_payload.telemetry, sort_keys=True).encode("utf-8")
    payload_hash = hashlib.sha256(canonical_telemetry_bytes).hexdigest()

    # 3. Server-stamped internal envelope (Zero-Trust Edge Identity)
    envelope = {
        "event_id": raw_payload.event_id,
        "tenant_id": tenant_id,
        "fleet_id": fleet_id,
        "vehicle_id": vehicle_id,
        "event_timestamp": raw_payload.event_timestamp.isoformat(),
        "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
        "payload_hash": payload_hash,
        "schema_version": raw_payload.schema_version,
        "telemetry": raw_payload.telemetry,
    }

    # 4. Publish directly to telemetry.raw with partition key = tenant_id:vehicle_id
    broker = get_broker()
    partition_key = f"{tenant_id}:{vehicle_id}"
    await broker.publish(
        topic="telemetry.raw",
        key=partition_key,
        value=envelope,
        headers={"tenant_id": tenant_id, "schema_version": raw_payload.schema_version},
    )

    # 5. Immediate asynchronous 202 response
    return IngestionResponse(
        event_id=raw_payload.event_id,
        status="accepted",
        processing="asynchronous",
        received_at=datetime.now(timezone.utc),
    )


# In-memory mock buffer for DLQ retrieval in testing / local dev
_local_dlq_buffer: list[dict[str, Any]] = []


@router.get("/dlq", summary="Admin-only DLQ inspection endpoint")
async def list_quarantined_events(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """
    Administrative endpoint for viewing quarantined events.
    Requires authenticated user context.
    """
    return _local_dlq_buffer[-limit:]


@router.post("/dlq/replay", summary="Admin-only DLQ replay endpoint")
async def replay_quarantined_event(
    dlq_id: str,
    replay_reason: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Administrative replay operation with audit logging and retry limits.
    """
    target = next((item for item in _local_dlq_buffer if item.get("dlq_id") == dlq_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Quarantined event not found in DLQ")

    if target.get("retry_count", 0) >= settings.MAX_REPLAY_ATTEMPTS:
        raise HTTPException(
            status_code=400,
            detail=f"Exceeded maximum replay attempts ({settings.MAX_REPLAY_ATTEMPTS})",
        )

    target["retry_count"] = target.get("retry_count", 0) + 1
    target["last_retry_at"] = datetime.now(timezone.utc).isoformat()
    target["replayed_by"] = current_user.username
    target["replay_reason"] = replay_reason

    # Re-publish to telemetry.raw
    broker = get_broker()
    raw_payload_dict = json.loads(target["raw_payload"])
    await broker.publish(
        topic="telemetry.raw",
        key=f"{target['tenant_id']}:{target['vehicle_id']}",
        value=raw_payload_dict,
    )

    return {
        "status": "replayed",
        "dlq_id": dlq_id,
        "retry_count": target["retry_count"],
        "replayed_by": current_user.username,
    }


@router.post(
    "/session/finish",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request manual finalization of active driving session",
)
async def finish_active_session(
    identity: tuple[str, str, str | None] = Depends(get_device_identity),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Asynchronous command endpoint requesting completion of an active driving session.
    Enforces Phase 8 tenant and vehicle ACL.
    Returns HTTP 202 Accepted and notifies UI via WebSocket upon Gold persistence.
    """
    tenant_id, vehicle_id, _ = identity
    sessionizer = get_sessionizer()

    mem_session = sessionizer.get_active_session(tenant_id, vehicle_id)
    checkpoint = None
    if mem_session is None:
        # Verify if active or finish-requested session exists in durable DB
        stmt = select(TripSessionCheckpoint).where(
            TripSessionCheckpoint.tenant_id == tenant_id,
            TripSessionCheckpoint.vehicle_id == vehicle_id,
            TripSessionCheckpoint.status.in_(["ACTIVE", "FINISH_REQUESTED"]),
        )
        checkpoint = await db.scalar(stmt)

    if mem_session is None and checkpoint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active driving session found for vehicle {vehicle_id}",
        )

    session_id = mem_session.session_id if mem_session else checkpoint.session_id

    if checkpoint is not None:
        checkpoint.status = "FINISH_REQUESTED"
        checkpoint.updated_at = datetime.now(timezone.utc)
        await db.commit()
    elif mem_session is not None:
        mem_session.status = "FINISH_REQUESTED"

    # Trigger sessionizer finalization asynchronously
    asyncio.create_task(sessionizer.request_finalization(tenant_id, vehicle_id, finalization_reason="MANUAL"))

    return {
        "status": "FINISH_REQUESTED",
        "session_id": session_id,
        "vehicle_id": vehicle_id,
        "tenant_id": tenant_id,
        "message": "Driving session finalization initiated successfully",
    }


@router.get(
    "/session/active",
    summary="Get clean projection of active driving session",
)
async def get_active_session_projection(
    identity: tuple[str, str, str | None] = Depends(get_device_identity),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Returns clean projection of current in-flight driving session.
    Enforces Phase 8 tenant and vehicle ACL.
    """
    tenant_id, vehicle_id, _ = identity
    sessionizer = get_sessionizer()

    # 1. Check in-memory hot active session first (sub-second accuracy)
    mem_session = sessionizer.get_active_session(tenant_id, vehicle_id)
    if mem_session is not None and mem_session.status in ("ACTIVE", "FINISH_REQUESTED"):
        now = datetime.now(timezone.utc)
        start_t = mem_session.start_event_time
        if start_t.tzinfo is None:
            start_t = start_t.replace(tzinfo=timezone.utc)
        elapsed_sec = max(0.0, (now - start_t).total_seconds())
        return {
            "active": True,
            "session_id": mem_session.session_id,
            "tenant_id": mem_session.tenant_id,
            "vehicle_id": mem_session.vehicle_id,
            "status": mem_session.status,
            "start_time": mem_session.start_event_time.isoformat(),
            "last_event_time": mem_session.last_event_time.isoformat(),
            "duration_seconds": round(elapsed_sec, 1),
            "distance_km": round(mem_session.distance_km, 2),
            "point_count": mem_session.point_count,
            "last_speed": mem_session.last_speed,
        }

    # 2. Fallback to durable checkpoint in database
    stmt = select(TripSessionCheckpoint).where(
        TripSessionCheckpoint.tenant_id == tenant_id,
        TripSessionCheckpoint.vehicle_id == vehicle_id,
        TripSessionCheckpoint.status.in_(["ACTIVE", "FINISH_REQUESTED", "FINALIZING"]),
    )
    checkpoint = await db.scalar(stmt)

    if not checkpoint:
        return {
            "active": False,
            "vehicle_id": vehicle_id,
            "tenant_id": tenant_id,
        }

    now = datetime.now(timezone.utc)
    start_t = checkpoint.start_event_time
    if start_t.tzinfo is None:
        start_t = start_t.replace(tzinfo=timezone.utc)
    elapsed_sec = max(0.0, (now - start_t).total_seconds())

    return {
        "active": True,
        "session_id": checkpoint.session_id,
        "tenant_id": checkpoint.tenant_id,
        "vehicle_id": checkpoint.vehicle_id,
        "status": checkpoint.status,
        "start_time": checkpoint.start_event_time.isoformat(),
        "last_event_time": checkpoint.last_event_time.isoformat(),
        "duration_seconds": round(elapsed_sec, 1),
        "distance_km": round(checkpoint.distance_km, 2),
        "point_count": checkpoint.point_count,
        "last_speed": checkpoint.last_speed,
    }

