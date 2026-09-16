import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import AsyncSessionLocal, get_db
from backend.models.tenant import Vehicle
from backend.models.user import User
from backend.streaming.hot_state import VehicleLiveState, get_hot_state_manager
from backend.utils.auth import get_current_user

logger = logging.getLogger("fleettrack.routers.ws_telemetry")

router = APIRouter(prefix=f"{settings.API_V1_STR}/telemetry", tags=["Real-Time Telemetry & Projections"])


async def resolve_user_tenant_and_vehicles(user: User, db: AsyncSession) -> tuple[str, set[str]]:
    """
    Resolves tenant_id and authorized vehicle IDs for an authenticated user.
    Enforces strict tenant isolation and per-vehicle authorization.
    """
    # 1. Check if user's assigned vehicle exists in the Vehicle hierarchy
    stmt = select(Vehicle).where(Vehicle.id == user.vehicle_number)
    res = await db.execute(stmt)
    vehicle = res.scalars().first()

    if vehicle:
        tenant_id = vehicle.tenant_id
        # In multi-vehicle fleet scenario, fetch all vehicles in the user's fleet/tenant
        fleet_vehicles_stmt = select(Vehicle.id).where(Vehicle.tenant_id == tenant_id)
        if vehicle.fleet_id:
            fleet_vehicles_stmt = select(Vehicle.id).where(Vehicle.fleet_id == vehicle.fleet_id)
        f_res = await db.execute(fleet_vehicles_stmt)
        authorized_vehicles = set(f_res.scalars().all())
        authorized_vehicles.add(user.vehicle_number)
        return tenant_id, authorized_vehicles

    # 2. Fallback for standalone / demo users: bound to their own vehicle
    fallback_tenant = "tenant_default"
    return fallback_tenant, {user.vehicle_number}


@router.get("/state/{vehicle_id}", response_model=VehicleLiveState)
async def get_vehicle_live_state(
    vehicle_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    REST Snapshot Endpoint:
    Returns the latest instantaneous hot-state projection for a vehicle.
    Enforces the exact same tenant and vehicle authorization policy as WebSockets.
    """
    tenant_id, authorized_vehicles = await resolve_user_tenant_and_vehicles(current_user, db)

    if vehicle_id not in authorized_vehicles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: vehicle '{vehicle_id}' is not authorized for your account.",
        )

    manager = await get_hot_state_manager()
    state = await manager.get_vehicle_state(tenant_id, vehicle_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No hot state projection found for vehicle '{vehicle_id}'.",
        )
    return state


@router.get("/state", response_model=list[VehicleLiveState])
async def get_tenant_live_states(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    REST Snapshot Endpoint:
    Returns instantaneous snapshots for all active vehicles authorized for the user.
    """
    tenant_id, authorized_vehicles = await resolve_user_tenant_and_vehicles(current_user, db)
    manager = await get_hot_state_manager()
    all_states = await manager.get_tenant_vehicle_states(tenant_id)
    # Filter strictly to authorized vehicles
    return [s for s in all_states if s.vehicle_id in authorized_vehicles]


@router.websocket("/ws")
async def websocket_telemetry_endpoint(
    websocket: WebSocket,
    token: str | None = Query(default=None, description="Fallback query token (in-band preferred)"),
):
    """
    Authenticated Multi-Tenant Telemetry WebSocket Gateway.
    Lifecycle:
    1. Connects in UNAUTHENTICATED state.
    2. Expects in-band JSON {"type": "authenticate", "token": "<jwt>"} within 5s.
    3. Resolves user identity, tenant_id, and authorized vehicle ACL.
    4. Handles client subscriptions: {"action": "subscribe", "vehicle_id": "..."}.
    5. Streams low-latency 1 Hz / alert-bypassed updates with monotonic state_version.
    """
    await websocket.accept()

    user: User | None = None
    tenant_id: str = ""
    authorized_vehicles: set[str] = set()

    # -------------------------------------------------------------------------
    # 1. In-Band Authentication with Strict Timeout
    # -------------------------------------------------------------------------
    jwt_token: str | None = token
    if not jwt_token:
        try:
            raw_init = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=settings.WS_AUTH_TIMEOUT_SECONDS,
            )
            init_msg = json.loads(raw_init)
            if init_msg.get("type") == "authenticate":
                jwt_token = init_msg.get("token")
        except asyncio.TimeoutError:
            logger.warning("[WS Gateway] Authentication timed out. Closing socket.")
            await websocket.send_json({
                "type": "error",
                "code": "AUTH_TIMEOUT",
                "message": f"Authentication token required within {settings.WS_AUTH_TIMEOUT_SECONDS}s.",
            })
            await websocket.close(code=4001)
            return
        except Exception as e:
            logger.warning(f"[WS Gateway] Invalid handshake message: {e}")
            await websocket.close(code=4001)
            return

    if not jwt_token:
        await websocket.send_json({"type": "error", "code": "AUTH_REQUIRED", "message": "Missing JWT token"})
        await websocket.close(code=4001)
        return

    # Verify JWT
    try:
        payload = jwt.decode(jwt_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub", "")
        if not username:
            raise JWTError("Missing 'sub' in token")
    except JWTError as e:
        logger.warning(f"[WS Gateway] Token verification failed: {e}")
        await websocket.send_json({"type": "error", "code": "INVALID_TOKEN", "message": "Invalid JWT credentials"})
        await websocket.close(code=4001)
        return

    # Resolve User & Vehicle ACL in DB Session
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.username == username))
        user = user_res.scalars().first()
        if not user:
            await websocket.send_json({"type": "error", "code": "USER_NOT_FOUND", "message": "User does not exist"})
            await websocket.close(code=4001)
            return

        tenant_id, authorized_vehicles = await resolve_user_tenant_and_vehicles(user, session)

    logger.info(f"[WS Gateway] Client authenticated: user={username}, tenant={tenant_id}, authorized_vehicles={authorized_vehicles}")
    await websocket.send_json({
        "type": "authenticated",
        "tenant_id": tenant_id,
        "username": username,
        "authorized_vehicles": list(authorized_vehicles),
    })

    # -------------------------------------------------------------------------
    # 2. Subscription Management & Message Dispatch Loop
    # -------------------------------------------------------------------------
    manager = await get_hot_state_manager()
    subscription_tasks: dict[str, asyncio.Task] = {}

    async def vehicle_channel_listener(vehicle_id: str, channel: str):
        try:
            async for frame in manager.subscribe_channel(channel):
                await websocket.send_json({
                    "type": "telemetry_update",
                    "channel": channel,
                    "data": frame,
                })
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[WS Gateway] Error streaming channel {channel}: {e}")

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                msg = json.loads(raw_text)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON format"})
                continue

            action = msg.get("action")

            if action == "subscribe":
                req_vehicle_id = msg.get("vehicle_id")
                if not req_vehicle_id or req_vehicle_id not in authorized_vehicles:
                    logger.warning(f"[WS Gateway] Unauthorized vehicle subscription attempt: {req_vehicle_id} by user {username}")
                    await websocket.send_json({
                        "type": "error",
                        "code": "UNAUTHORIZED_VEHICLE",
                        "message": f"You are not authorized to subscribe to vehicle '{req_vehicle_id}'",
                    })
                    continue

                channel = f"fleet:channel:{tenant_id}:{req_vehicle_id}"
                if req_vehicle_id not in subscription_tasks or subscription_tasks[req_vehicle_id].done():
                    task = asyncio.create_task(vehicle_channel_listener(req_vehicle_id, channel))
                    subscription_tasks[req_vehicle_id] = task
                    logger.info(f"[WS Gateway] Subscribed user {username} to vehicle {req_vehicle_id} ({channel})")

                await websocket.send_json({
                    "type": "subscribed",
                    "vehicle_id": req_vehicle_id,
                    "channel": channel,
                })

                # Deliver current cached snapshot immediately upon subscription
                current_snapshot = await manager.get_vehicle_state(tenant_id, req_vehicle_id)
                if current_snapshot:
                    await websocket.send_json({
                        "type": "telemetry_snapshot",
                        "channel": channel,
                        "data": current_snapshot.model_dump(mode="json"),
                    })

            elif action == "unsubscribe":
                req_vehicle_id = msg.get("vehicle_id")
                if req_vehicle_id and req_vehicle_id in subscription_tasks:
                    subscription_tasks[req_vehicle_id].cancel()
                    del subscription_tasks[req_vehicle_id]
                    logger.info(f"[WS Gateway] Unsubscribed user {username} from vehicle {req_vehicle_id}")

                await websocket.send_json({
                    "type": "unsubscribed",
                    "vehicle_id": req_vehicle_id,
                })

            elif action == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            else:
                await websocket.send_json({"type": "error", "message": f"Unknown action '{action}'"})

    except WebSocketDisconnect:
        logger.info(f"[WS Gateway] Client disconnected cleanly: user={username}")
    except Exception as e:
        logger.error(f"[WS Gateway] WebSocket unexpected error for user {username}: {e}")
    finally:
        for t in subscription_tasks.values():
            t.cancel()
