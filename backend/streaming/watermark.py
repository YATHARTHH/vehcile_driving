import logging
from datetime import datetime, timedelta, timezone
from backend.config import settings

logger = logging.getLogger("fleettrack.streaming.watermark")


class PerVehicleWatermarkTracker:
    """
    Tracks event-time watermarks scoped per (tenant_id, vehicle_id).
    Prevents single vehicle clock drift from advancing global fleet watermark (P0-2).
    Includes 24-hour TTL state lifecycle management to prevent memory leak (P1).
    """
    def __init__(
        self,
        allowed_lateness_seconds: float | None = None,
        state_ttl_hours: float | None = None,
    ) -> None:
        self.allowed_lateness = timedelta(
            seconds=allowed_lateness_seconds or settings.TELEMETRY_ALLOWED_LATENESS_SECONDS
        )
        self.state_ttl = timedelta(
            hours=state_ttl_hours or settings.WATERMARK_STATE_TTL_HOURS
        )
        # Mapping: (tenant_id, vehicle_id) -> (max_event_time, last_seen_at)
        self._states: dict[tuple[str, str], tuple[datetime, datetime]] = {}

    def evaluate_lateness(
        self,
        tenant_id: str,
        vehicle_id: str,
        event_time: datetime,
        now_utc: datetime | None = None,
    ) -> tuple[bool, datetime]:
        """
        Evaluates whether an event is late relative to the vehicle's current watermark.
        Returns: (is_late, current_watermark)
        """
        current_time = now_utc or datetime.now(timezone.utc)
        key = (tenant_id, vehicle_id)

        # Normalize to UTC
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        if key in self._states:
            max_seen, _ = self._states[key]
            if event_time > max_seen:
                max_seen = event_time
            self._states[key] = (max_seen, current_time)
        else:
            max_seen = event_time
            self._states[key] = (max_seen, current_time)

        watermark = max_seen - self.allowed_lateness
        is_late = event_time < watermark

        return is_late, watermark

    def evict_stale_states(self, now_utc: datetime | None = None) -> int:
        """
        Evicts vehicles that have been inactive for > 24 hours.
        Returns count of evicted states.
        """
        current_time = now_utc or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        stale_keys = [
            key
            for key, (_, last_seen) in self._states.items()
            if (current_time - last_seen) > self.state_ttl
        ]

        for key in stale_keys:
            del self._states[key]

        if stale_keys:
            logger.info(f"[WatermarkTracker] Evicted {len(stale_keys)} inactive vehicle watermark states")

        return len(stale_keys)

    def get_tracked_vehicle_count(self) -> int:
        return len(self._states)
