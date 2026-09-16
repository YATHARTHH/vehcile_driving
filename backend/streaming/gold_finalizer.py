import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.config import settings
from backend.models.alert import Alert
from backend.models.session import TripOutboxEvent, TripSessionCheckpoint
from backend.models.trip import Trip
from backend.streaming.broker import EventBroker
from ml_model.driving_logic import calculate_driving_score
from ml_model.maintenance_logic import build_alerts

# ML Inference Artifacts Loader
try:
    from ml_model.model_utils import load_artifacts, predict_behavior
    ml_model_obj, scaler_obj, le_obj, model_info_obj = load_artifacts()
    ML_MODEL_LOADED = True
except Exception as e:
    logging.warning(f"[GoldTripFinalizer] ML Pipeline artifact connection warning: {e}")
    ML_MODEL_LOADED = False
    ml_model_obj = scaler_obj = le_obj = model_info_obj = None

logger = logging.getLogger("fleettrack.streaming.gold_finalizer")


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class GoldTripFinalizer:
    """
    Dedicated Gold-tier Trip Finalizer.
    Responsible for:
      1. Aggregating dynamic session kinematics into authoritative Gold metrics.
      2. Scoring driving performance (0-100) and ML behavior classification.
      3. Evaluating maintenance alert triggers.
      4. Committing atomically to `trips`, `alerts`, `trip_session_checkpoints`, and `trip_outbox_events`.
      5. Publishing `telemetry.gold.trip_completed` to the streaming broker.
    """

    def __init__(self, broker: EventBroker):
        self.broker = broker

    async def finalize(
        self, checkpoint: TripSessionCheckpoint, trigger_source: str, db: AsyncSession
    ) -> dict[str, Any]:
        """
        Executes Gold-tier trip finalization with strict idempotency and atomic transactional guarantees.
        """
        finalization_reason = trigger_source
        session_id = checkpoint.session_id
        tenant_id = checkpoint.tenant_id
        vehicle_id = checkpoint.vehicle_id
        user_id = checkpoint.user_id or 1
        logger.info(f"[GoldFinalizer] Finalizing session {session_id} (trigger: {trigger_source})")

        # 1. Idempotency Check: Verify if trip already committed for this session_id
        existing_trip = await db.scalar(select(Trip).where(Trip.session_id == session_id))
        if existing_trip is not None:
            logger.warning(f"[GoldFinalizer] Trip already exists for session {session_id} (trip_id: {existing_trip.id})")
            checkpoint.status = "COMPLETED"
            await db.commit()
            return {"status": "ALREADY_COMPLETED", "trip_id": existing_trip.id}

        # 2. Check Min Trip Validity
        point_count = checkpoint.point_count
        distance_km = round(checkpoint.distance_km, 2)

        if trigger_source == "MANUAL":
            if point_count < settings.MIN_MANUAL_TRIP_POINTS:
                logger.info(f"[GoldFinalizer] Manual session {session_id} discarded: points={point_count} < {settings.MIN_MANUAL_TRIP_POINTS}")
                checkpoint.status = "DISCARDED"
                await db.commit()
                return {"status": "DISCARDED", "reason": f"Points ({point_count}) < {settings.MIN_MANUAL_TRIP_POINTS}"}
        else:
            if point_count < settings.MIN_AUTO_TRIP_POINTS or distance_km < settings.MIN_AUTO_TRIP_DISTANCE_KM:
                logger.info(f"[GoldFinalizer] Auto session {session_id} discarded: points={point_count}, dist={distance_km}km")
                checkpoint.status = "DISCARDED"
                await db.commit()
                return {"status": "DISCARDED", "reason": "Below auto threshold"}

        # 3. Kinematic Metric Aggregation
        start_t = ensure_utc(checkpoint.start_event_time)
        last_t = ensure_utc(checkpoint.last_event_time)
        duration_seconds = max(1.0, (last_t - start_t).total_seconds()) if (start_t and last_t) else 1.0
        trip_duration_min = round(duration_seconds / 60.0, 2)

        # Average speed overall vs moving
        avg_speed_kmph = round(distance_km / (duration_seconds / 3600.0), 2) if duration_seconds > 0 else 0.0
        moving_duration_seconds = max(1.0, checkpoint.moving_point_count * 1.0)
        avg_moving_speed_kmph = round(distance_km / (moving_duration_seconds / 3600.0), 2)

        fuel_consumed = round(checkpoint.fuel_consumed_l, 2)
        aggregates = checkpoint.running_aggregates or {}

        max_speed = round(float(aggregates.get("speed_max", 0.0)), 2)
        max_rpm = int(aggregates.get("rpm_max", 0))
        brake_events = int(aggregates.get("brake_events", 0))

        count_divisor = max(1, point_count)
        avg_brake_pressure = round(float(aggregates.get("brake_pressure_sum", 0.0)) / count_divisor, 2)
        avg_engine_load = round(float(aggregates.get("engine_load_sum", 0.0)) / count_divisor, 2)
        avg_throttle = round(float(aggregates.get("throttle_sum", 0.0)) / count_divisor, 2)
        avg_steering = round(float(aggregates.get("steering_sum", 0.0)) / count_divisor, 2)
        avg_angular_vel = round(float(aggregates.get("angular_vel_sum", 0.0)) / count_divisor, 2)
        avg_tire_press = round(float(aggregates.get("tire_pressure_sum", 32.0 * count_divisor)) / count_divisor, 1)
        max_accel = round(float(aggregates.get("acceleration_max", 0.0)), 2)
        last_gear = int(aggregates.get("last_gear", 1))

        start_location = (
            f"{checkpoint.start_latitude:.4f}, {checkpoint.start_longitude:.4f}"
            if checkpoint.start_latitude is not None
            else "N/A"
        )
        end_location = (
            f"{checkpoint.last_latitude:.4f}, {checkpoint.last_longitude:.4f}"
            if checkpoint.last_latitude is not None
            else "N/A"
        )
        gps_path_str = json.dumps(checkpoint.gps_breadcrumbs or [])
        trip_date_str = checkpoint.start_event_time.strftime("%Y-%m-%d")

        # 4. Deterministic Driving Score & ML Behavior
        logic_behavior, logic_score = calculate_driving_score(
            avg_speed_kmph,
            max_rpm,
            brake_events,
            avg_steering,
            avg_angular_vel,
            max_accel,
            last_gear,
            avg_tire_press,
            avg_engine_load,
            avg_throttle,
            avg_brake_pressure,
            trip_duration_min,
        )

        trip_dict_for_ml = {
            "avg_speed_kmph": avg_speed_kmph,
            "max_speed": max_speed,
            "max_rpm": max_rpm,
            "fuel_consumed": fuel_consumed,
            "brake_events": brake_events,
            "steering_angle": avg_steering,
            "angular_velocity": avg_angular_vel,
            "acceleration": max_accel,
            "gear_position": last_gear,
            "tire_pressure": avg_tire_press,
            "engine_load": avg_engine_load,
            "throttle_position": avg_throttle,
            "brake_pressure": avg_brake_pressure,
            "trip_duration": trip_duration_min,
            "distance_km": distance_km,
        }

        ml_behavior = "Unknown"
        ml_confidence = 0.0
        model_version = "rf-v1.0.0"
        feature_version = "trip-features-v1"

        if ML_MODEL_LOADED and ml_model_obj is not None:
            try:
                ml_res = predict_behavior(trip_dict_for_ml, ml_model_obj, scaler_obj, le_obj, model_info_obj)
                ml_behavior = ml_res.get("behavior_class", logic_behavior)
                ml_confidence = float(ml_res.get("confidence", 85.0))
            except Exception as ex:
                logger.warning(f"[GoldFinalizer] ML prediction error: {ex}")
                ml_behavior = logic_behavior
                ml_confidence = 80.0
        else:
            ml_behavior = logic_behavior
            ml_confidence = 85.0

        # 5. Maintenance Alert Evaluation
        alerts_list, health_rec = build_alerts(trip_dict_for_ml)

        # 6. Atomic Database Commit
        new_trip = Trip(
            session_id=session_id,
            user_id=user_id,
            trip_date=trip_date_str,
            distance_km=distance_km,
            avg_speed_kmph=avg_speed_kmph,
            max_speed=max_speed,
            max_rpm=max_rpm,
            fuel_consumed=fuel_consumed,
            brake_events=brake_events,
            steering_angle=avg_steering,
            angular_velocity=avg_angular_vel,
            acceleration=max_accel,
            gear_position=last_gear,
            tire_pressure=avg_tire_press,
            engine_load=avg_engine_load,
            throttle_position=avg_throttle,
            brake_pressure=avg_brake_pressure,
            trip_duration=trip_duration_min,
            start_location=start_location,
            end_location=end_location,
            gps_path=gps_path_str,
        )
        db.add(new_trip)
        await db.flush()  # Populates new_trip.id

        # Insert alerts with deduplication by alert_type per trip
        existing_alert_types = set()
        for a in alerts_list:
            atype = a.get("alert_type", "general")
            if atype not in existing_alert_types:
                existing_alert_types.add(atype)
                alert_entry = Alert(
                    user_id=user_id,
                    trip_id=new_trip.id,
                    alert_type=atype,
                    severity=a.get("severity", "warning"),
                    title=a.get("title", "Maintenance Notice"),
                    message=a.get("description", ""),
                    icon=a.get("icon", "fa-triangle-exclamation"),
                )
                db.add(alert_entry)

        # Update Checkpoint status
        checkpoint.status = "COMPLETED"
        checkpoint.updated_at = datetime.now(timezone.utc)

        # Insert Transactional Outbox Event
        outbox_event_id = str(uuid.uuid4())
        outbox_payload = {
            "event_id": outbox_event_id,
            "type": "TRIP_COMPLETED",
            "session_id": session_id,
            "trip_id": new_trip.id,
            "tenant_id": tenant_id,
            "vehicle_id": vehicle_id,
            "user_id": user_id,
            "distance_km": distance_km,
            "avg_speed_kmph": avg_speed_kmph,
            "avg_moving_speed_kmph": avg_moving_speed_kmph,
            "duration_minutes": trip_duration_min,
            "logic_score": logic_score,
            "ml_behavior": ml_behavior,
            "ml_confidence": ml_confidence,
            "model_version": model_version,
            "feature_version": feature_version,
            "finalization_reason": finalization_reason,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        outbox_entry = TripOutboxEvent(
            event_id=outbox_event_id,
            event_type="TRIP_COMPLETED",
            topic="telemetry.gold.trip_completed",
            payload=outbox_payload,
            status="PENDING",
            created_at=datetime.now(timezone.utc),
        )
        db.add(outbox_entry)

        # Explicit COMMIT strictly before broker publication
        await db.commit()
        logger.info(f"[GoldFinalizer] Successfully committed Gold trip #{new_trip.id} for session {session_id}")

        # 7. Broker Publication (Post-commit outbox release)
        try:
            await self.broker.publish(
                topic="telemetry.gold.trip_completed",
                key=f"{tenant_id}:{vehicle_id}",
                value=outbox_payload,
                headers={"tenant_id": tenant_id, "schema_version": "v1.0.0"},
            )
            outbox_entry.status = "PUBLISHED"
            outbox_entry.published_at = datetime.now(timezone.utc)
            await db.commit()
        except Exception as pub_ex:
            logger.error(f"[GoldFinalizer] Broker publish warning for trip {new_trip.id}: {pub_ex}. Outbox record retained.")

        return {
            "status": "COMPLETED",
            "trip_id": new_trip.id,
            "session_id": session_id,
            "distance_km": distance_km,
            "avg_speed_kmph": avg_speed_kmph,
            "logic_score": logic_score,
            "ml_behavior": ml_behavior,
            "model_version": model_version,
            "finalization_reason": finalization_reason,
        }
