import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import AsyncSessionLocal
from backend.models.telemetry import TelemetryEvent
from backend.models.tenant import Vehicle
from backend.schemas.telemetry import DLQFailureCategory, DLQQuarantineEvent, ValidatedTelemetryEvent
from backend.streaming.broker import EventBroker
from backend.streaming.watermark import PerVehicleWatermarkTracker
from backend.telematics.sensor_validator import DynamicSensorValidator

logger = logging.getLogger("fleettrack.streaming.validation_worker")


class ValidationWorker:
    """
    Decoupled Stream Validation Worker.
    Consumes from telemetry.raw, performs deep dynamic physical validation,
    authoritative payload-hash idempotency conflict detection, scoped watermarking,
    and routes records to telemetry.validated or telemetry.dlq.
    """
    def __init__(
        self,
        broker: EventBroker,
        watermark_tracker: PerVehicleWatermarkTracker | None = None,
    ) -> None:
        self.broker = broker
        self.watermark_tracker = watermark_tracker or PerVehicleWatermarkTracker()
        self._running: bool = False
        self._vehicle_profiles: dict[str, dict[str, Any]] = {}

    async def get_vehicle_profile(self, vehicle_id: str, db: AsyncSession) -> dict[str, Any]:
        """Loads vehicle profile configuration from database cache."""
        if vehicle_id in self._vehicle_profiles:
            return self._vehicle_profiles[vehicle_id]

        stmt = select(Vehicle).where(Vehicle.id == vehicle_id)
        result = await db.execute(stmt)
        vehicle = result.scalars().first()
        profile = vehicle.profile_config if (vehicle and vehicle.profile_config) else {}
        self._vehicle_profiles[vehicle_id] = profile
        return profile

    async def process_record(
        self,
        key: str,
        envelope: dict[str, Any],
        db: AsyncSession
    ) -> dict[str, Any]:
        """
        Core pipeline logic for a single telemetry record.
        Returns execution status dict for audit and assertions.
        """
        event_id = envelope.get("event_id", "")
        tenant_id = envelope.get("tenant_id", "")
        vehicle_id = envelope.get("vehicle_id", "")
        raw_telemetry = envelope.get("telemetry", {})
        schema_version = envelope.get("schema_version", "v1.0.0")
        incoming_hash = envelope.get("payload_hash", "")

        if not incoming_hash:
            incoming_hash = hashlib.sha256(
                json.dumps(raw_telemetry, sort_keys=True).encode("utf-8")
            ).hexdigest()

        try:
            event_time = datetime.fromisoformat(
                envelope.get("event_timestamp", "").replace("Z", "+00:00")
            )
        except Exception:
            event_time = datetime.now(timezone.utc)

        # ---------------------------------------------------------------------
        # 1. Dynamic Physical Range & Quality Validation
        # ---------------------------------------------------------------------
        profile = await self.get_vehicle_profile(vehicle_id, db)
        validator = DynamicSensorValidator(profile)
        states, invalid_reasons, is_acceptable = validator.validate_packet(raw_telemetry)

        if not is_acceptable:
            # Physical boundary violation -> Permanent failure quarantine
            dlq_event = DLQQuarantineEvent(
                original_event_id=event_id,
                tenant_id=tenant_id,
                vehicle_id=vehicle_id,
                failure_stage="DYNAMIC_PHYSICAL_VALIDATION",
                failure_category=DLQFailureCategory.PERMANENT_FAILURE,
                error_code="PHYSICAL_RANGE_VIOLATION",
                error_message="; ".join(invalid_reasons),
                raw_payload=json.dumps(envelope),
                schema_version=schema_version,
            )
            await self.broker.publish(
                topic="telemetry.dlq",
                key=f"{tenant_id}:{vehicle_id}",
                value=dlq_event.model_dump(mode="json"),
            )
            return {"status": "QUARANTINED_PERMANENT", "reasons": invalid_reasons}

        # ---------------------------------------------------------------------
        # 2. Authoritative Database Idempotency & Conflict Check (P0-6)
        # ---------------------------------------------------------------------
        stmt = select(TelemetryEvent).where(
            TelemetryEvent.tenant_id == tenant_id,
            TelemetryEvent.vehicle_id == vehicle_id,
            TelemetryEvent.event_id == event_id,
        )
        result = await db.execute(stmt)
        existing_event = result.scalars().first()

        if existing_event is not None:
            if existing_event.payload_hash == incoming_hash:
                # Benign network replay
                logger.info(f"[ValidationWorker] Duplicate replay detected for event {event_id} - safely ignored")
                return {"status": "DUPLICATE_REPLAY", "event_id": event_id}
            else:
                # Conflicting duplicate! Reused event ID with different data
                logger.warning(f"[ValidationWorker] Conflict detected on event {event_id}: payload hash mismatch!")
                dlq_event = DLQQuarantineEvent(
                    original_event_id=event_id,
                    tenant_id=tenant_id,
                    vehicle_id=vehicle_id,
                    failure_stage="IDEMPOTENCY_CONFLICT",
                    failure_category=DLQFailureCategory.CONFLICTING_EVENT,
                    error_code="CONFLICTING_EVENT_PAYLOAD",
                    error_message=f"Event ID reused with conflicting hash (existing: {existing_event.payload_hash}, new: {incoming_hash})",
                    raw_payload=json.dumps(envelope),
                    schema_version=schema_version,
                )
                await self.broker.publish(
                    topic="telemetry.dlq",
                    key=f"{tenant_id}:{vehicle_id}",
                    value=dlq_event.model_dump(mode="json"),
                )
                return {"status": "CONFLICTING_EVENT_QUARANTINED", "event_id": event_id}

        # ---------------------------------------------------------------------
        # 3. Scoped Per-Vehicle Watermarking Check (P0-2)
        # ---------------------------------------------------------------------
        is_late, watermark = self.watermark_tracker.evaluate_lateness(
            tenant_id=tenant_id,
            vehicle_id=vehicle_id,
            event_time=event_time,
        )

        # ---------------------------------------------------------------------
        # 4. Authoritative Database Persistence
        # ---------------------------------------------------------------------
        telemetry_row = TelemetryEvent(
            tenant_id=tenant_id,
            vehicle_id=vehicle_id,
            event_id=event_id,
            payload_hash=incoming_hash,
            event_timestamp=event_time,
            ingestion_timestamp=datetime.now(timezone.utc),
            data_quality_status="VALID",
            invalid_reasons=invalid_reasons or None,
            is_late=is_late,
            is_duplicate=False,
            is_imputed=False,
            schema_version=schema_version,
            telemetry_data=raw_telemetry,
        )
        db.add(telemetry_row)
        await db.commit()

        # ---------------------------------------------------------------------
        # 5. Publish to telemetry.validated for hot state workers & downstream
        # ---------------------------------------------------------------------
        validated_event = ValidatedTelemetryEvent(
            event_id=event_id,
            tenant_id=tenant_id,
            fleet_id=envelope.get("fleet_id"),
            vehicle_id=vehicle_id,
            event_timestamp=event_time,
            ingestion_timestamp=datetime.now(timezone.utc),
            payload_hash=incoming_hash,
            schema_version=schema_version,
            data_quality_status="VALID",
            invalid_reasons=invalid_reasons,
            is_late=is_late,
            is_duplicate=False,
            is_imputed=False,
            telemetry=raw_telemetry,
        )
        await self.broker.publish(
            topic="telemetry.validated",
            key=f"{tenant_id}:{vehicle_id}",
            value=validated_event.model_dump(mode="json"),
        )

        return {
            "status": "VALIDATED_AND_PERSISTED",
            "event_id": event_id,
            "is_late": is_late,
        }

    async def run(self) -> None:
        self._running = True
        logger.info("[ValidationWorker] Started telemetry validation worker")

        try:
            async for key, envelope, metadata in self.broker.subscribe("telemetry.raw", group_id="fleettrack-validator"):
                if not self._running:
                    break

                async with AsyncSessionLocal() as session:
                    try:
                        await self.process_record(key, envelope, session)
                    except Exception as e:
                        logger.error(f"[ValidationWorker] Transient processing failure on event: {e}", exc_info=True)
                        # Route transient system error to DLQ
                        dlq_event = DLQQuarantineEvent(
                            original_event_id=envelope.get("event_id", "unknown"),
                            tenant_id=envelope.get("tenant_id", "unknown"),
                            vehicle_id=envelope.get("vehicle_id", "unknown"),
                            failure_stage="PIPELINE_EXECUTION",
                            failure_category=DLQFailureCategory.TRANSIENT_FAILURE,
                            error_code="TRANSIENT_SYSTEM_EXCEPTION",
                            error_message=str(e),
                            raw_payload=json.dumps(envelope),
                        )
                        await self.broker.publish(
                            topic="telemetry.dlq",
                            key=key,
                            value=dlq_event.model_dump(mode="json"),
                        )

        except Exception as e:
            logger.error(f"[ValidationWorker] Fatal worker error: {e}", exc_info=True)
            raise

    def stop(self) -> None:
        self._running = False
        logger.info("[ValidationWorker] Stopping validation worker")
