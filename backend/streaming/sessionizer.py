import asyncio
import logging
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.models.session import TripSessionCheckpoint
from backend.models.user import User
from backend.streaming.broker import EventBroker
from backend.streaming.gold_finalizer import GoldTripFinalizer

logger = logging.getLogger("fleettrack.streaming.sessionizer")


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two GPS coordinates in kilometers."""
    r = 6371.0  # Earth's radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class ActiveTripSession:
    """
    In-memory working accumulator for 1 Hz validated telemetry.
    Backed by periodic durable checkpoints to TripSessionCheckpoint.
    """
    session_id: str
    tenant_id: str
    vehicle_id: str
    user_id: int | None
    start_event_time: datetime
    last_event_time: datetime
    last_event_received_at: datetime
    last_checkpoint_time: datetime
    point_count: int = 0
    moving_point_count: int = 0
    distance_km: float = 0.0
    fuel_consumed_l: float = 0.0
    last_speed: float = 0.0
    last_latitude: float | None = None
    last_longitude: float | None = None
    start_latitude: float | None = None
    start_longitude: float | None = None
    running_aggregates: dict[str, Any] = field(default_factory=dict)
    gps_breadcrumbs: list[list[float]] = field(default_factory=list)
    source_partition: int = 0
    source_offset: int = -1
    last_checkpoint_packet_count: int = 0
    status: str = "ACTIVE"


class TripSessionizerWorker:
    """
    Phase 9 Trip Sessionizer Worker.
    Consumes from 'telemetry.validated' with strict partition key 'tenant_id:vehicle_id'.
    Guarantees:
      - Single-writer per vehicle session.
      - Bounded durable state checkpointing with consumer offset progress tracking.
      - Dual clock semantics (processing-time inactivity sweeper vs event-time kinematics).
      - Replay fast-forward protection.
      - Atomic CAS state transitions to prevent race conditions.
    """

    def __init__(self, broker: EventBroker, gold_finalizer: GoldTripFinalizer | None = None) -> None:
        self.broker = broker
        self.gold_finalizer = gold_finalizer or GoldTripFinalizer(broker)
        self.active_sessions: dict[tuple[str, str], ActiveTripSession] = {}
        self._user_cache: dict[str, int] = {}
        self._running: bool = False
        self._sweeper_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    def get_active_session(self, tenant_id: str, vehicle_id: str) -> ActiveTripSession | None:
        return self.active_sessions.get((tenant_id, vehicle_id))

    async def start(self) -> None:
        self._running = True
        logger.info("[TripSessionizer] Starting worker and recovering durable checkpoints...")
        await self._recover_checkpoints_from_db()
        self._sweeper_task = asyncio.create_task(self._inactivity_and_lease_sweeper())
        logger.info("[TripSessionizer] Inactivity & recovery sweeper started.")

    async def stop(self) -> None:
        self._running = False
        if self._sweeper_task and not self._sweeper_task.done():
            self._sweeper_task.cancel()

        # Flush active checkpoints cleanly on shutdown
        async with AsyncSessionLocal() as db:
            for session in list(self.active_sessions.values()):
                try:
                    await self._persist_checkpoint(session, db)
                except Exception as ex:
                    logger.error(f"[TripSessionizer] Error checkpointing session {session.session_id} during shutdown: {ex}")
            await db.commit()
        logger.info("[TripSessionizer] Cleanly flushed active checkpoints on worker stop.")

    async def run(self) -> None:
        await self.start()
        try:
            async for key, value, metadata in self.broker.subscribe(
                "telemetry.validated", group_id="fleettrack-trip-sessionizer"
            ):
                if not self._running:
                    break
                await self.process_packet(value, metadata)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[TripSessionizer] Fatal error in consumption loop: {e}", exc_info=True)
            raise
        finally:
            await self.stop()

    async def _resolve_user_id(self, vehicle_id: str, db: AsyncSession) -> int:
        if vehicle_id in self._user_cache:
            return self._user_cache[vehicle_id]

        res = await db.execute(select(User.id).where(User.vehicle_number == vehicle_id))
        uid = res.scalar_one_or_none()
        if uid is None:
            # Fallback to default user 1 if not registered
            uid = 1
        self._user_cache[vehicle_id] = uid
        return uid

    async def _recover_checkpoints_from_db(self) -> None:
        """
        Boots active sessions from the durable checkpoint store on worker start.
        Also reclaims any stale 'FINALIZING' leases.
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(TripSessionCheckpoint).where(
                    TripSessionCheckpoint.status.in_(["ACTIVE", "FINISH_REQUESTED", "FINALIZING"])
                )
            )
            checkpoints = result.scalars().all()
            now = datetime.now(timezone.utc)

            for cp in checkpoints:
                session_key = (cp.tenant_id, cp.vehicle_id)

                # Case A: Stale FINALIZING lease recovery
                if cp.status == "FINALIZING":
                    ref_time = ensure_utc(cp.finalization_started_at) or ensure_utc(cp.updated_at)
                    lease_age = (now - ref_time).total_seconds() if ref_time else 999.0
                    if lease_age > settings.FINALIZATION_LEASE_TIMEOUT_SECONDS:
                        logger.warning(
                            f"[TripSessionizer] Reclaiming stale FINALIZING lease for session {cp.session_id} (age: {lease_age:.1f}s)"
                        )
                        cp.finalization_attempts += 1
                        await self.gold_finalizer.finalize(cp, "CRASH_RECOVERY", db)
                        continue

                # Case B: Active or Finish Requested session restoration
                active = ActiveTripSession(
                    session_id=cp.session_id,
                    tenant_id=cp.tenant_id,
                    vehicle_id=cp.vehicle_id,
                    user_id=cp.user_id,
                    start_event_time=ensure_utc(cp.start_event_time),
                    last_event_time=ensure_utc(cp.last_event_time),
                    last_event_received_at=ensure_utc(cp.last_event_received_at),
                    last_checkpoint_time=ensure_utc(cp.last_checkpoint_time),
                    point_count=cp.point_count,
                    moving_point_count=cp.moving_point_count,
                    distance_km=cp.distance_km,
                    fuel_consumed_l=cp.fuel_consumed_l,
                    last_speed=cp.last_speed,
                    last_latitude=cp.last_latitude,
                    last_longitude=cp.last_longitude,
                    start_latitude=cp.start_latitude,
                    start_longitude=cp.start_longitude,
                    running_aggregates=dict(cp.running_aggregates or {}),
                    gps_breadcrumbs=list(cp.gps_breadcrumbs or []),
                    source_partition=cp.source_partition,
                    source_offset=cp.source_offset,
                    last_checkpoint_packet_count=cp.point_count,
                    status=cp.status,
                )
                self.active_sessions[session_key] = active
                logger.info(
                    f"[TripSessionizer] Restored active session {active.session_id} for {session_key} at offset {active.source_offset}"
                )

            await db.commit()

    async def process_packet(self, value: dict[str, Any], metadata: dict[str, Any]) -> None:
        """
        Processes a single validated telemetry packet.
        """
        tenant_id = value.get("tenant_id") or "tenant_default"
        vehicle_id = value.get("vehicle_id") or "veh_default"
        session_key = (tenant_id, vehicle_id)

        try:
            event_time = datetime.fromisoformat(value.get("event_timestamp", "").replace("Z", "+00:00"))
        except Exception:
            event_time = datetime.now(timezone.utc)

        received_at = datetime.now(timezone.utc)
        partition = metadata.get("partition", 0)
        offset = metadata.get("offset", 0)
        telemetry = value.get("telemetry", {})

        speed = float(telemetry.get("speed_kmph") or telemetry.get("speed") or 0.0)
        rpm = int(telemetry.get("rpm") or telemetry.get("engine_rpm") or 0)
        fuel_rate = float(telemetry.get("fuel_rate_lph") or 0.0)
        lat = telemetry.get("lat") or telemetry.get("latitude")
        lon = telemetry.get("lon") or telemetry.get("longitude")
        brake_pressure = float(telemetry.get("brake_pressure_bar") or telemetry.get("brake_pressure") or 0.0)
        engine_load = float(telemetry.get("engine_load_pct") or telemetry.get("engine_load") or 0.0)
        throttle = float(telemetry.get("throttle_position") or telemetry.get("throttle_pct") or 0.0)
        steering = float(telemetry.get("steering_angle") or 0.0)
        angular_vel = float(telemetry.get("angular_velocity") or 0.0)
        tire_press = float(telemetry.get("tire_pressure_psi") or telemetry.get("tire_pressure") or 32.0)
        gear = int(telemetry.get("gear_position") or telemetry.get("gear") or 1)

        async with self._lock:
            session = self.active_sessions.get(session_key)

            # Replay Fast-Forward Protection:
            # If packet offset is already absorbed in the durable checkpoint, discard it safely
            if session and offset > 0 and session.source_offset >= 0 and offset <= session.source_offset:
                logger.debug(f"[TripSessionizer] Replay skipped for offset {offset} <= checkpoint offset {session.source_offset}")
                return

            if not session:
                # Start new active session
                async with AsyncSessionLocal() as db:
                    user_id = await self._resolve_user_id(vehicle_id, db)

                session_id = str(uuid.uuid4())
                session = ActiveTripSession(
                    session_id=session_id,
                    tenant_id=tenant_id,
                    vehicle_id=vehicle_id,
                    user_id=user_id,
                    start_event_time=event_time,
                    last_event_time=event_time,
                    last_event_received_at=received_at,
                    last_checkpoint_time=received_at,
                    point_count=0,
                    moving_point_count=0,
                    distance_km=0.0,
                    fuel_consumed_l=0.0,
                    last_speed=speed,
                    last_latitude=float(lat) if lat is not None else None,
                    last_longitude=float(lon) if lon is not None else None,
                    start_latitude=float(lat) if lat is not None else None,
                    start_longitude=float(lon) if lon is not None else None,
                    running_aggregates={
                        "speed_sum": 0.0,
                        "speed_max": speed,
                        "rpm_sum": 0,
                        "rpm_max": rpm,
                        "brake_events": 0,
                        "brake_pressure_sum": 0.0,
                        "brake_pressure_max": brake_pressure,
                        "engine_load_sum": 0.0,
                        "throttle_sum": 0.0,
                        "steering_sum": 0.0,
                        "angular_vel_sum": 0.0,
                        "tire_pressure_sum": 0.0,
                        "acceleration_max": 0.0,
                        "last_gear": gear,
                    },
                    gps_breadcrumbs=[],
                    source_partition=partition,
                    source_offset=offset,
                    status="ACTIVE",
                )
                self.active_sessions[session_key] = session
                logger.info(f"[TripSessionizer] Started new active session {session_id} for vehicle {vehicle_id}")

            # -------------------------------------------------------------
            # Kinematic Accumulation with Sanity & GPS Jump Guards
            # -------------------------------------------------------------
            dt = (event_time - session.last_event_time).total_seconds()

            if dt > 0:
                delta_d = 0.0
                if dt <= settings.MAX_INTEGRATION_GAP_SECONDS:
                    # Trapezoidal Speed Integration
                    v_avg = (session.last_speed + speed) / 2.0
                    delta_d = (v_avg * (dt / 3600.0))
                else:
                    # Gapped packet: Fallback to Haversine GPS delta with velocity jump guard
                    if (
                        lat is not None
                        and lon is not None
                        and session.last_latitude is not None
                        and session.last_longitude is not None
                    ):
                        h_dist = haversine_distance_km(
                            session.last_latitude, session.last_longitude, float(lat), float(lon)
                        )
                        implied_speed = h_dist / (dt / 3600.0)
                        if implied_speed <= settings.MAX_PLAUSIBLE_GPS_SPEED_KMPH:
                            delta_d = h_dist
                        else:
                            logger.warning(
                                f"[TripSessionizer] GPS jump rejected: {h_dist:.1f}km in {dt}s ({implied_speed:.1f} km/h)"
                            )

                session.distance_km += delta_d

                # Explicit Fuel Integration: fuel_rate_lph * dt / 3600
                if fuel_rate > 0:
                    session.fuel_consumed_l += fuel_rate * (dt / 3600.0)

                # Harsh deceleration detection
                accel = (speed - session.last_speed) / (dt * 3.6) if dt > 0 else 0.0
                if accel < -3.5 or brake_pressure > 50.0:
                    session.running_aggregates["brake_events"] = session.running_aggregates.get("brake_events", 0) + 1
                if abs(accel) > session.running_aggregates.get("acceleration_max", 0.0):
                    session.running_aggregates["acceleration_max"] = round(abs(accel), 2)

            # Update running scalar aggregates
            session.point_count += 1
            if speed >= settings.MOVING_SPEED_THRESHOLD_KMPH:
                session.moving_point_count += 1

            session.running_aggregates["speed_sum"] += speed
            if speed > session.running_aggregates.get("speed_max", 0.0):
                session.running_aggregates["speed_max"] = round(speed, 2)

            session.running_aggregates["rpm_sum"] += rpm
            if rpm > session.running_aggregates.get("rpm_max", 0):
                session.running_aggregates["rpm_max"] = rpm

            session.running_aggregates["brake_pressure_sum"] += brake_pressure
            if brake_pressure > session.running_aggregates.get("brake_pressure_max", 0.0):
                session.running_aggregates["brake_pressure_max"] = round(brake_pressure, 2)

            session.running_aggregates["engine_load_sum"] += engine_load
            session.running_aggregates["throttle_sum"] += throttle
            session.running_aggregates["steering_sum"] += abs(steering)
            session.running_aggregates["angular_vel_sum"] += abs(angular_vel)
            session.running_aggregates["tire_pressure_sum"] += tire_press
            session.running_aggregates["last_gear"] = gear

            session.last_speed = speed
            session.last_event_time = event_time
            session.last_event_received_at = received_at
            session.source_partition = partition
            session.source_offset = offset

            if lat is not None and lon is not None:
                cur_lat = round(float(lat), 6)
                cur_lon = round(float(lon), 6)
                session.last_latitude = cur_lat
                session.last_longitude = cur_lon
                if session.start_latitude is None:
                    session.start_latitude = cur_lat
                    session.start_longitude = cur_lon

                # Bounded breadcrumb decimation (max 500 coordinates)
                breadcrumbs = session.gps_breadcrumbs
                if len(breadcrumbs) < 500:
                    if not breadcrumbs:
                        breadcrumbs.append([cur_lat, cur_lon])
                    else:
                        last_pt = breadcrumbs[-1]
                        dist_from_last = haversine_distance_km(last_pt[0], last_pt[1], cur_lat, cur_lon)
                        # Record if vehicle moved > 25 meters or on first points
                        if dist_from_last >= 0.025:
                            breadcrumbs.append([cur_lat, cur_lon])

            # -------------------------------------------------------------
            # Dual-Threshold Durable Checkpoint Persistence
            # -------------------------------------------------------------
            elapsed_sec = (received_at - session.last_checkpoint_time).total_seconds()
            pkts_since_cp = session.point_count - session.last_checkpoint_packet_count

            if (
                elapsed_sec >= settings.SESSION_CHECKPOINT_INTERVAL_SECONDS
                or pkts_since_cp >= settings.SESSION_CHECKPOINT_INTERVAL_PACKETS
            ):
                async with AsyncSessionLocal() as db:
                    await self._persist_checkpoint(session, db)
                    await db.commit()

                session.last_checkpoint_time = received_at
                session.last_checkpoint_packet_count = session.point_count
                await self.broker.commit_offset("telemetry.validated", partition, offset)

    async def _persist_checkpoint(self, session: ActiveTripSession, db: AsyncSession) -> None:
        """
        Durable checkpoint write to database.
        """
        existing = await db.scalar(
            select(TripSessionCheckpoint).where(TripSessionCheckpoint.session_id == session.session_id)
        )
        if existing:
            existing.last_event_time = session.last_event_time
            existing.last_event_received_at = session.last_event_received_at
            existing.last_checkpoint_time = datetime.now(timezone.utc)
            existing.point_count = session.point_count
            existing.moving_point_count = session.moving_point_count
            existing.distance_km = session.distance_km
            existing.fuel_consumed_l = session.fuel_consumed_l
            existing.last_speed = session.last_speed
            existing.last_latitude = session.last_latitude
            existing.last_longitude = session.last_longitude
            existing.running_aggregates = session.running_aggregates
            existing.gps_breadcrumbs = session.gps_breadcrumbs
            existing.source_partition = session.source_partition
            existing.source_offset = session.source_offset
            existing.checkpoint_version += 1
            existing.updated_at = datetime.now(timezone.utc)
        else:
            cp = TripSessionCheckpoint(
                session_id=session.session_id,
                tenant_id=session.tenant_id,
                vehicle_id=session.vehicle_id,
                user_id=session.user_id,
                status=session.status,
                start_event_time=session.start_event_time,
                last_event_time=session.last_event_time,
                last_event_received_at=session.last_event_received_at,
                last_checkpoint_time=datetime.now(timezone.utc),
                point_count=session.point_count,
                moving_point_count=session.moving_point_count,
                distance_km=session.distance_km,
                fuel_consumed_l=session.fuel_consumed_l,
                last_speed=session.last_speed,
                last_latitude=session.last_latitude,
                last_longitude=session.last_longitude,
                start_latitude=session.start_latitude,
                start_longitude=session.start_longitude,
                running_aggregates=session.running_aggregates,
                gps_breadcrumbs=session.gps_breadcrumbs,
                source_partition=session.source_partition,
                source_offset=session.source_offset,
                checkpoint_version=1,
            )
            db.add(cp)

    async def _inactivity_and_lease_sweeper(self) -> None:
        """
        Background sweeper enforcing:
          1. Processing-time inactivity timeout (now - received_at > 300s).
          2. Stale FINALIZING lease recovery (now - started_at > 60s).
        """
        while self._running:
            try:
                await asyncio.sleep(5.0)
                now = datetime.now(timezone.utc)

                # Check in-memory sessions for processing-time inactivity
                sessions_to_close: list[tuple[str, str]] = []
                async with self._lock:
                    for key, session in self.active_sessions.items():
                        inact_ref = ensure_utc(session.last_event_received_at)
                        inactivity_age = (now - inact_ref).total_seconds() if inact_ref else 0.0
                        if inactivity_age >= settings.SESSION_INACTIVITY_TIMEOUT_SECONDS:
                            sessions_to_close.append(key)

                for key in sessions_to_close:
                    await self.request_finalization(key[0], key[1], finalization_reason="INACTIVITY_TIMEOUT")

                # Check database for stale FINALIZING leases
                async with AsyncSessionLocal() as db:
                    stale_leases = await db.scalars(
                        select(TripSessionCheckpoint).where(TripSessionCheckpoint.status == "FINALIZING")
                    )
                    for cp in stale_leases.all():
                        ref_time = ensure_utc(cp.finalization_started_at) or ensure_utc(cp.updated_at)
                        lease_age = (now - ref_time).total_seconds() if ref_time else 999.0
                        if lease_age > settings.FINALIZATION_LEASE_TIMEOUT_SECONDS:
                            logger.warning(
                                f"[TripSessionizer] Sweeper recovering stale FINALIZING lease for session {cp.session_id} (age: {lease_age:.1f}s)"
                            )
                            cp.finalization_attempts += 1
                            await self.gold_finalizer.finalize(cp, "CRASH_RECOVERY", db)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[TripSessionizer] Sweeper iteration error: {e}", exc_info=True)

    async def request_finalization(
        self, tenant_id: str, vehicle_id: str, finalization_reason: str = "MANUAL"
    ) -> dict[str, Any] | None:
        """
        Atomic CAS state transition to 'FINALIZING' and Gold trip finalization.
        Prevents race conditions between user /finish and inactivity sweeper.
        """
        session_key = (tenant_id, vehicle_id)
        now = datetime.now(timezone.utc)

        async with self._lock:
            active_session = self.active_sessions.pop(session_key, None)

        async with AsyncSessionLocal() as db:
            # 1. Flush active session checkpoint to DB if present in memory
            if active_session:
                await self._persist_checkpoint(active_session, db)
                await db.commit()

            # 2. Atomic Compare-And-Swap (CAS) transition: ACTIVE/FINISH_REQUESTED -> FINALIZING
            stmt = (
                update(TripSessionCheckpoint)
                .where(
                    TripSessionCheckpoint.tenant_id == tenant_id,
                    TripSessionCheckpoint.vehicle_id == vehicle_id,
                    TripSessionCheckpoint.status.in_(["ACTIVE", "FINISH_REQUESTED"]),
                )
                .values(
                    status="FINALIZING",
                    finalization_started_at=now,
                    updated_at=now,
                )
                .returning(TripSessionCheckpoint.session_id)
            )
            res = await db.execute(stmt)
            claimed_session_id = res.scalar_one_or_none()
            await db.commit()

            if not claimed_session_id:
                logger.debug(f"[TripSessionizer] CAS finalization lease not acquired for {session_key} (already claimed or inactive).")
                return None

            # 3. Retrieve claimed checkpoint row and execute Gold finalization
            checkpoint = await db.scalar(
                select(TripSessionCheckpoint).where(TripSessionCheckpoint.session_id == claimed_session_id)
            )
            if not checkpoint:
                return None

            logger.info(
                f"[TripSessionizer] CAS lease acquired for session {claimed_session_id}. Handing off to GoldTripFinalizer..."
            )
            outcome = await self.gold_finalizer.finalize(checkpoint, finalization_reason, db)
            return outcome


_sessionizer_instance: TripSessionizerWorker | None = None


def get_sessionizer(broker: EventBroker | None = None) -> TripSessionizerWorker:
    """Returns singleton TripSessionizerWorker instance."""
    global _sessionizer_instance
    if _sessionizer_instance is None:
        if broker is None:
            from backend.streaming.broker import get_broker
            broker = get_broker()
        _sessionizer_instance = TripSessionizerWorker(broker)
    return _sessionizer_instance

