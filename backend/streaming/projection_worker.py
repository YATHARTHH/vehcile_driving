import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from backend.config import settings
from backend.streaming.broker import EventBroker
from backend.streaming.hot_state import AlertSeverity, HotStateManager, VehicleLiveState

logger = logging.getLogger("fleettrack.streaming.projection_worker")


class RealtimeProjectionWorker:
    """
    Real-Time Projection Worker.
    Consumes from telemetry.validated topic.
    Invariants:
    1. Every validated event immediately updates the disposable hot-state snapshot in Redis.
    2. UI Pub/Sub broadcast is independently throttled (default 1 Hz per vehicle)
       with immediate bypass on HIGH or CRITICAL alert transitions.
    3. Monotonically increments per-vehicle state_version.
    """

    def __init__(
        self,
        broker: EventBroker,
        hot_state: HotStateManager,
        ui_interval_seconds: float = settings.UI_STREAM_INTERVAL_SECONDS,
    ) -> None:
        self.broker = broker
        self.hot_state = hot_state
        self.ui_interval_seconds = ui_interval_seconds
        self._running: bool = False
        self._state_versions: dict[tuple[str, str], int] = {}
        self._last_emitted_at: dict[tuple[str, str], float] = {}
        self._previous_alerts: dict[tuple[str, str], set[str]] = {}

    def _derive_alerts_and_severity(
        self, telemetry: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], AlertSeverity | None]:
        """Derives active alerts and highest severity from raw telemetry packet readings."""
        alerts: list[dict[str, Any]] = []
        highest: AlertSeverity | None = None

        speed = float(telemetry.get("speed_kmph", 0.0) or 0.0)
        rpm = float(telemetry.get("rpm", 0.0) or 0.0)
        brake = float(telemetry.get("brake_pressure_bar", 0.0) or 0.0)
        engine_load = float(telemetry.get("engine_load_pct", 0.0) or 0.0)

        # Critical threshold: extreme harsh braking event
        if brake > 100.0:
            alerts.append({
                "code": "CRITICAL_HARSH_BRAKE",
                "severity": AlertSeverity.CRITICAL.value,
                "message": f"Critical harsh braking detected: {brake:.1f} bar",
            })
            highest = AlertSeverity.CRITICAL

        # High threshold: severe speeding or engine stress
        if speed > 130.0:
            alerts.append({
                "code": "HIGH_SPEED_VIOLATION",
                "severity": AlertSeverity.HIGH.value,
                "message": f"Excessive speed detected: {speed:.1f} km/h",
            })
            if highest != AlertSeverity.CRITICAL:
                highest = AlertSeverity.HIGH

        if rpm > 6500.0:
            alerts.append({
                "code": "HIGH_ENGINE_STRESS",
                "severity": AlertSeverity.HIGH.value,
                "message": f"High engine RPM stress: {rpm:.0f} RPM",
            })
            if highest != AlertSeverity.CRITICAL:
                highest = AlertSeverity.HIGH

        # Warning threshold: high engine load
        if engine_load > 90.0:
            alerts.append({
                "code": "WARNING_HIGH_LOAD",
                "severity": AlertSeverity.WARNING.value,
                "message": f"Elevated engine load: {engine_load:.1f}%",
            })
            if highest is None or highest == AlertSeverity.INFO:
                highest = AlertSeverity.WARNING

        return alerts, highest

    def _map_to_live_state(self, envelope: dict[str, Any]) -> VehicleLiveState:
        """Converts validated telemetry event envelope into strongly typed VehicleLiveState."""
        tenant_id = envelope.get("tenant_id", "")
        vehicle_id = envelope.get("vehicle_id", "")
        key = (tenant_id, vehicle_id)

        current_version = self._state_versions.get(key, 0) + 1
        self._state_versions[key] = current_version

        telemetry = envelope.get("telemetry", {})
        alerts, highest_sev = self._derive_alerts_and_severity(telemetry)

        # Parse timestamp safely
        try:
            ts_raw = envelope.get("event_timestamp", "")
            event_time = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except Exception:
            event_time = datetime.now(timezone.utc)

        # Fuel disambiguation
        fuel_level_pct = telemetry.get("fuel_level_pct")
        if fuel_level_pct is None and "fuel_pct" in telemetry:
            fuel_level_pct = telemetry.get("fuel_pct")

        fuel_rate_lph = telemetry.get("fuel_rate_lph")
        if fuel_rate_lph is None and "fuel_rate" in telemetry:
            fuel_rate_lph = telemetry.get("fuel_rate")

        fuel_consumed_total_l = telemetry.get("fuel_consumed")
        if fuel_consumed_total_l is None and "fuel_consumed_l" in telemetry:
            fuel_consumed_total_l = telemetry.get("fuel_consumed_l")

        return VehicleLiveState(
            tenant_id=tenant_id,
            vehicle_id=vehicle_id,
            state_version=current_version,
            event_timestamp=event_time,
            updated_at=datetime.now(timezone.utc),
            speed_kmph=float(telemetry.get("speed_kmph", 0.0) or 0.0),
            rpm=float(telemetry.get("rpm", 0.0) or 0.0),
            fuel_level_pct=float(fuel_level_pct) if fuel_level_pct is not None else None,
            fuel_rate_lph=float(fuel_rate_lph) if fuel_rate_lph is not None else None,
            fuel_consumed_total_l=float(fuel_consumed_total_l) if fuel_consumed_total_l is not None else None,
            lat=float(telemetry.get("lat")) if telemetry.get("lat") is not None else None,
            lon=float(telemetry.get("lon")) if telemetry.get("lon") is not None else None,
            heading=float(telemetry.get("heading")) if telemetry.get("heading") is not None else None,
            driving_score=float(envelope.get("driving_score")) if envelope.get("driving_score") is not None else None,
            active_alerts=alerts,
            highest_alert_severity=highest_sev,
        )

    async def process_event(self, envelope: dict[str, Any]) -> dict[str, Any]:
        """
        Processes a single validated telemetry event.
        Step 1: Always update Redis hot state snapshot.
        Step 2: Check throttle vs alert transition for UI pub/sub emission.
        """
        state = self._map_to_live_state(envelope)
        key = (state.tenant_id, state.vehicle_id)

        # ---------------------------------------------------------------------
        # Invariant 1: Every validated event updates the latest hot-state snapshot
        # ---------------------------------------------------------------------
        await self.hot_state.set_vehicle_state(state, ttl_seconds=3600)

        # ---------------------------------------------------------------------
        # Invariant 2: Evaluate UI throttle & alert transition
        # ---------------------------------------------------------------------
        now_mono = time.monotonic()
        last_emitted = self._last_emitted_at.get(key, 0.0)
        elapsed = now_mono - last_emitted

        # Detect new alert transitions
        current_alert_codes = {a["code"] for a in state.active_alerts}
        prev_alert_codes = self._previous_alerts.get(key, set())
        has_new_alert = bool(current_alert_codes - prev_alert_codes)
        self._previous_alerts[key] = current_alert_codes

        is_high_priority = state.highest_alert_severity in (AlertSeverity.HIGH, AlertSeverity.CRITICAL)
        should_bypass = is_high_priority and has_new_alert
        should_emit = should_bypass or (elapsed >= self.ui_interval_seconds)

        if should_emit:
            self._last_emitted_at[key] = now_mono
            await self.hot_state.publish_state_update(state)
            await self.hot_state.publish_fleet_notification(
                tenant_id=state.tenant_id,
                vehicle_id=state.vehicle_id,
                state_version=state.state_version,
                updated_at=state.updated_at.isoformat(),
            )
            return {
                "status": "EMITTED_ALERT_BYPASS" if should_bypass else "EMITTED_THROTTLED",
                "state_version": state.state_version,
                "vehicle_id": state.vehicle_id,
            }
        else:
            return {
                "status": "STATE_UPDATED_DROPPED_THROTTLE",
                "state_version": state.state_version,
                "vehicle_id": state.vehicle_id,
            }

    async def run(self) -> None:
        """Continuous consumer loop listening to telemetry.validated."""
        self._running = True
        logger.info("[ProjectionWorker] Starting real-time projection consumer loop on telemetry.validated...")
        try:
            async for _, envelope, _ in self.broker.subscribe("telemetry.validated"):
                if not self._running:
                    break
                try:
                    await self.process_event(envelope)
                except Exception as e:
                    logger.error(f"[ProjectionWorker] Error projecting event {envelope.get('event_id')}: {e}")
        except asyncio.CancelledError:
            logger.info("[ProjectionWorker] Consumer task cancelled cleanly.")
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False
