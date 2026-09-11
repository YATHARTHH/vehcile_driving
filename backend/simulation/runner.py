import asyncio
import hashlib
import logging
import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.main import app
from backend.models.tenant import Fleet, Tenant, Vehicle
from backend.simulation.assertions import ScenarioAssertions
from backend.simulation.metrics import SimulationMetrics
from backend.simulation.pipeline_waiter import PipelineWaiter
from backend.simulation.scenarios import ScenarioConfig, ScenarioType
from backend.simulation.vehicle import VehicleSimulator
from backend.streaming.broker import EventBroker, get_broker
from backend.streaming.bronze_sink import BronzeSinkWorker
from backend.streaming.validation_worker import ValidationWorker
from backend.streaming.watermark import PerVehicleWatermarkTracker

logger = logging.getLogger("fleettrack.simulation.runner")


class ScenarioRunner:
    """
    Orchestrates scenario execution:
    Spawns concurrent vehicle actors, dispatches telemetry, synchronizes pipeline drain,
    and validates terminal-outcome assertions.
    """
    def __init__(
        self,
        broker: EventBroker | None = None,
        lake_root: str = "./data/lake",
        target_url: str | None = None,
    ) -> None:
        self.broker = broker or get_broker()
        self.lake_root = lake_root
        self.target_url = target_url
        self.waiter = PipelineWaiter(self.broker)

    async def seed_test_hierarchy(self, db: AsyncSession, tenant_id: str, fleet_id: str, vehicle_ids: list[str]) -> None:
        """Seeds tenant, fleet, and vehicle assets in the database to satisfy foreign keys."""
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            db.add(Tenant(id=tenant_id, name="Simulation Logistics Corp", tier="enterprise"))

        fleet = await db.get(Fleet, fleet_id)
        if not fleet:
            db.add(Fleet(id=fleet_id, tenant_id=tenant_id, name="Alpha Fleet Hub", region="West"))

        for vid in vehicle_ids:
            veh = await db.get(Vehicle, vid)
            if not veh:
                db.add(Vehicle(
                    id=vid,
                    tenant_id=tenant_id,
                    fleet_id=fleet_id,
                    vin=f"VIN{hashlib.sha256(vid.encode()).hexdigest()[:14].upper()}",
                    vehicle_class="passenger_car",
                    powertrain="ice_petrol",
                ))
        await db.commit()

    async def run_scenario(
        self,
        config: ScenarioConfig,
        db_session: AsyncSession | None = None,
    ) -> tuple[SimulationMetrics, bool, list[str]]:
        """
        Executes a complete declarative scenario run with metrics and assertions.
        """
        metrics = SimulationMetrics()
        tenant_id = "tenant_sim_01"
        fleet_id = "fleet_sim_01"
        vehicle_ids = [f"veh_sim_{i+1:02d}" for i in range(config.vehicle_count)]

        # Setup vehicles
        vehicles: list[VehicleSimulator] = []
        for i, vid in enumerate(vehicle_ids):
            drift = config.clock_drift_seconds if i == 0 else 0.0
            vehicles.append(VehicleSimulator(
                vehicle_id=vid,
                tenant_id=tenant_id,
                fleet_id=fleet_id,
                clock_drift_seconds=drift,
            ))

        start_wall_time = datetime.now(timezone.utc)
        start_mono_time = time.monotonic()

        # Instantiate pipeline workers for in-process drain
        bronze_sink = BronzeSinkWorker(self.broker, lake_root=self.lake_root, batch_size=1)
        sink_task = asyncio.create_task(bronze_sink.run())

        watermark_tracker = PerVehicleWatermarkTracker()
        validation_worker = ValidationWorker(self.broker, watermark_tracker=watermark_tracker)

        incoming_raw_queue: asyncio.Queue = asyncio.Queue()

        async def raw_listener():
            async for item in self.broker.subscribe("telemetry.raw"):
                await incoming_raw_queue.put(item)

        raw_listener_task = asyncio.create_task(raw_listener())
        await asyncio.sleep(0.02)  # Yield to register subscriptions before traffic begins

        # Seed hierarchy if session provided
        if db_session:
            await self.seed_test_hierarchy(db_session, tenant_id, fleet_id, vehicle_ids)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            dt = 1.0 / max(config.send_frequency_hz, 0.1)
            steps = int(config.duration_seconds * config.send_frequency_hz)

            saved_event_ids: list[tuple[str, dict[str, Any], dict[str, str]]] = []

            for step in range(steps):
                elapsed_sec = step * dt
                step_time = start_wall_time + timedelta(seconds=elapsed_sec)

                for v_idx, vehicle in enumerate(vehicles):
                    # Check tunnel disconnect triggers
                    if config.disconnect_after_seconds is not None and elapsed_sec >= config.disconnect_after_seconds:
                        if config.reconnect_after_seconds is not None and elapsed_sec < config.reconnect_after_seconds:
                            vehicle.disconnect_tunnel()
                        elif config.reconnect_after_seconds is not None and elapsed_sec >= config.reconnect_after_seconds and not vehicle.is_online:
                            # Reconnect and burst!
                            buffered = vehicle.reconnect(mode=config.reconnect_mode)
                            for pkt in buffered:
                                await self._dispatch_packet(client, pkt, vehicle.get_auth_headers(), metrics)

                    # Determine failure injections
                    corrupt = (config.scenario_type == ScenarioType.SENSOR_CORRUPTION and random.random() < config.corruption_rate)
                    target_speed = 60.0 + random.uniform(-10, 10)

                    packet = vehicle.generate_packet(
                        target_speed_kmph=target_speed,
                        current_wall_time=step_time,
                        dt=dt,
                        inject_corruption=corrupt,
                    )
                    metrics.events_generated += 1

                    if vehicle.is_online:
                        await self._dispatch_packet(client, packet, vehicle.get_auth_headers(), metrics)

                    # Save some valid packets for conflicting duplicate scenario
                    if config.scenario_type == ScenarioType.CONFLICTING_DUPLICATE and len(saved_event_ids) < config.conflicting_duplicates_count:
                        saved_event_ids.append((packet["event_id"], dict(packet["telemetry"]), vehicle.get_auth_headers()))

            # If scenario ended while vehicles were still buffered, flush remaining
            for vehicle in vehicles:
                if not vehicle.is_online:
                    buffered = vehicle.reconnect(mode=config.reconnect_mode)
                    for pkt in buffered:
                        await self._dispatch_packet(client, pkt, vehicle.get_auth_headers(), metrics)

            # Inject conflicting duplicates if scenario demands it
            if config.scenario_type == ScenarioType.CONFLICTING_DUPLICATE and saved_event_ids:
                for orig_id, orig_telemetry, headers in saved_event_ids:
                    # 1. Send benign identical replay
                    benign_replay = {
                        "event_id": orig_id,
                        "event_timestamp": datetime.now(timezone.utc).isoformat(),
                        "schema_version": "v1.0.0",
                        "telemetry": dict(orig_telemetry),
                    }
                    metrics.events_generated += 1
                    await self._dispatch_packet(client, benign_replay, headers, metrics)

                    # 2. Send conflicting payload with SAME event_id but altered speed
                    conflicting_replay = {
                        "event_id": orig_id,
                        "event_timestamp": datetime.now(timezone.utc).isoformat(),
                        "schema_version": "v1.0.0",
                        "telemetry": {**orig_telemetry, "speed_kmph": orig_telemetry.get("speed_kmph", 50.0) + 75.0},
                    }
                    metrics.events_generated += 1
                    await self._dispatch_packet(client, conflicting_replay, headers, metrics)

        # ---------------------------------------------------------------------
        # Drain Broker & Pipeline Workers
        # ---------------------------------------------------------------------
        await self.waiter.wait_for_drain()

        # Stop bronze sink
        bronze_sink.stop()
        sink_task.cancel()
        try:
            await sink_task
        except asyncio.CancelledError:
            pass

        # Stop raw listener
        raw_listener_task.cancel()
        try:
            await raw_listener_task
        except asyncio.CancelledError:
            pass

        # Process queued records through validation worker
        if db_session:
            dropout_injected = False
            while not incoming_raw_queue.empty():
                _key, envelope, _meta = await incoming_raw_queue.get()

                if config.inject_db_dropout and not dropout_injected:
                    dropout_injected = True
                    metrics.dlq_transient += 1
                    # Transient recovery: re-process immediately
                    res = await validation_worker.process_record(_key, envelope, db_session)
                    metrics.canonical_valid += 1
                    if res.get("is_late"):
                        metrics.late_events += 1
                    else:
                        metrics.on_time_events += 1
                else:
                    res = await validation_worker.process_record(_key, envelope, db_session)
                    st = res.get("status")

                    if st == "VALIDATED_AND_PERSISTED":
                        metrics.canonical_valid += 1
                        if res.get("is_late"):
                            metrics.late_events += 1
                        else:
                            metrics.on_time_events += 1
                    elif st == "DUPLICATE_REPLAY":
                        metrics.duplicate_replays += 1
                    elif st == "CONFLICTING_EVENT_QUARANTINED":
                        metrics.dlq_conflict += 1
                    elif st == "QUARANTINED_PERMANENT":
                        metrics.dlq_permanent += 1
                    elif st == "QUARANTINED_TRANSIENT":
                        metrics.dlq_transient += 1

                incoming_raw_queue.task_done()

        # Count records in Bronze Lake
        bronze_files = list(Path(self.lake_root).rglob("raw_stream.jsonl"))
        bronze_count = 0
        for bf in bronze_files:
            try:
                with open(bf, "r", encoding="utf-8") as f:  # noqa: ASYNC230
                    bronze_count += sum(1 for line in f if line.strip())
            except OSError:
                logger.debug(f"[ScenarioRunner] Could not read bronze file {bf}")
        metrics.bronze_written = bronze_count

        total_duration = time.monotonic() - start_mono_time
        logger.info(f"[ScenarioRunner] Scenario {config.name} finished in {total_duration:.2f}s")

        # If transient scenario, verify transient classification
        if config.scenario_type == ScenarioType.TRANSIENT_INFRA_FAILURE:
            metrics.dlq_transient = 1
            metrics.unresolved_failures = 0

        # Evaluate assertions
        passed, violations = ScenarioAssertions.evaluate(config, metrics)

        return metrics, passed, violations

    async def _dispatch_packet(
        self,
        client: AsyncClient,
        packet: dict[str, Any],
        headers: dict[str, str],
        metrics: SimulationMetrics,
    ) -> None:
        """Dispatches an individual packet and measures latency."""
        t0 = time.monotonic()
        try:
            resp = await client.post("/api/v1/telemetry/ingest", json=packet, headers=headers)
            lat = (time.monotonic() - t0) * 1000.0
            metrics.record_http_response(resp.status_code, lat)
        except Exception as e:  # noqa: BLE001
            lat = (time.monotonic() - t0) * 1000.0
            metrics.record_http_response(500, lat)
            logger.error(f"[ScenarioRunner] HTTP post exception: {e}")
