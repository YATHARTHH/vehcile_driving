import shutil
import tempfile
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.database import Base
from backend.simulation.metrics import SimulationMetrics
from backend.simulation.physics import VehiclePhysicsModel
from backend.simulation.runner import ScenarioRunner
from backend.simulation.scenarios import ScenarioConfig, ScenarioType
from backend.simulation.vehicle import VehicleSimulator
from backend.streaming.broker import AsyncQueueBroker, set_broker


@pytest.fixture
async def sim_db_session():
    """Provides an isolated in-memory SQLite database for scenario testing."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await test_engine.dispose()


@pytest.fixture
async def sim_broker():
    """Provides a fresh, connected AsyncQueueBroker for each test."""
    broker = AsyncQueueBroker()
    await broker.connect()
    set_broker(broker)
    try:
        yield broker
    finally:
        await broker.disconnect()


def test_physics_kinematics_model():
    """Verify kinematic equations, gear calculations, and fuel consumption bounds."""
    physics = VehiclePhysicsModel(lat=37.7749, lon=-122.4194)

    # Initial state
    assert physics.speed_kmph == 0.0
    assert physics.rpm == 800.0
    assert physics.gear == 1

    # Accelerate towards 60 km/h
    for _ in range(5):
        state = physics.step(target_speed_kmph=60.0, dt=1.0)

    assert state["speed_kmph"] > 0.0
    assert 800.0 <= state["rpm"] <= 6500.0
    assert state["odometer_km"] > 0.0
    assert state["fuel_level_pct"] <= 100.0
    assert state["engine_temp_c"] >= 90.0


def test_vehicle_simulator_disconnect_and_buffer():
    """Verify edge vehicle buffering during network disconnect and FIFO vs reverse replay."""
    vehicle = VehicleSimulator("veh_edge_01", "ten_test", "fleet_test")
    now = datetime.now(timezone.utc)

    # Normal generation when online
    _ = vehicle.generate_packet(target_speed_kmph=40.0, current_wall_time=now, dt=1.0)
    assert vehicle.is_online is True
    assert len(vehicle.edge_buffer) == 0

    # Tunnel disconnect
    vehicle.disconnect_tunnel()
    assert vehicle.is_online is False

    pkt2 = vehicle.generate_packet(target_speed_kmph=40.0, current_wall_time=now, dt=1.0)
    pkt3 = vehicle.generate_packet(target_speed_kmph=40.0, current_wall_time=now, dt=1.0)
    assert len(vehicle.edge_buffer) == 2

    # Reconnect in FIFO mode
    buffered = vehicle.reconnect(mode="ordered")
    assert len(buffered) == 2
    assert buffered[0]["event_id"] == pkt2["event_id"]
    assert buffered[1]["event_id"] == pkt3["event_id"]
    assert len(vehicle.edge_buffer) == 0


def test_conservation_of_events_accounting():
    """Verifies Conservation of Events mathematical auditing."""
    metrics = SimulationMetrics()
    metrics.record_http_response(202, 10.5)
    metrics.record_http_response(202, 12.0)
    metrics.record_http_response(400, 5.0)

    # Ingress balance check
    assert metrics.events_sent == 3
    assert metrics.http_accepted == 2
    assert metrics.http_not_accepted == 1

    # Downstream outcomes
    metrics.canonical_valid = 1
    metrics.duplicate_replays = 1
    metrics.bronze_written = 2

    is_conserved, audit = metrics.verify_conservation()
    assert is_conserved is True
    assert audit["discrepancy"] == 0
    assert audit["bronze_preservation"] is True

    # Introduce intentional leak
    metrics.canonical_valid = 0
    is_conserved_leak, audit_leak = metrics.verify_conservation()
    assert is_conserved_leak is False
    assert audit_leak["discrepancy"] == 1


@pytest.mark.anyio
async def test_scenario_normal_city(sim_db_session, sim_broker):
    """Scenario 1: Fast deterministic test for Normal City Driving."""
    temp_dir = tempfile.mkdtemp()
    try:
        runner = ScenarioRunner(broker=sim_broker, lake_root=temp_dir)
        config = ScenarioConfig(
            scenario_type=ScenarioType.NORMAL_CITY,
            name="Test City Driving",
            description="Fast city driving test",
            vehicle_count=2,
            duration_seconds=2.0,
            send_frequency_hz=1.0,
        )

        metrics, passed, violations = await runner.run_scenario(config, db_session=sim_db_session)
        assert passed is True, f"Violations: {violations}"
        assert metrics.events_sent == 4
        assert metrics.canonical_valid == 4
        assert metrics.http_accepted == 4
        assert metrics.bronze_written >= 4
        assert metrics.dlq_permanent == 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.anyio
async def test_scenario_highway_burst(sim_db_session, sim_broker):
    """Scenario 2: Fast deterministic test for Highway Burst."""
    temp_dir = tempfile.mkdtemp()
    try:
        runner = ScenarioRunner(broker=sim_broker, lake_root=temp_dir)
        config = ScenarioConfig(
            scenario_type=ScenarioType.HIGHWAY_BURST,
            name="Test Highway Burst",
            description="High frequency throughput burst test",
            vehicle_count=3,
            duration_seconds=1.5,
            send_frequency_hz=4.0,
        )

        metrics, passed, violations = await runner.run_scenario(config, db_session=sim_db_session)
        assert passed is True, f"Violations: {violations}"
        assert metrics.events_sent == 18  # 3 veh * 1.5s * 4 Hz = 18
        assert metrics.canonical_valid == 18
        assert metrics.http_accepted == 18
        assert metrics.bronze_written >= 18
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.anyio
async def test_scenario_out_of_order_replay(sim_db_session, sim_broker):
    """Scenario 4: Fast test for Out-of-Order Reverse Replay."""
    temp_dir = tempfile.mkdtemp()
    try:
        runner = ScenarioRunner(broker=sim_broker, lake_root=temp_dir)
        config = ScenarioConfig(
            scenario_type=ScenarioType.OUT_OF_ORDER_REPLAY,
            name="Test Out of Order Replay",
            description="Reverse chronological burst test",
            vehicle_count=2,
            duration_seconds=4.0,
            send_frequency_hz=1.0,
            disconnect_after_seconds=1.0,
            reconnect_after_seconds=3.0,
            reconnect_mode="reverse",
        )

        metrics, passed, violations = await runner.run_scenario(config, db_session=sim_db_session)
        assert passed is True, f"Violations: {violations}"
        assert metrics.canonical_valid == metrics.events_sent
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.anyio
async def test_scenario_ordered_buffered_replay(sim_db_session, sim_broker):
    """Scenario 3: Fast test for FIFO Ordered Buffered Replay."""
    temp_dir = tempfile.mkdtemp()
    try:
        runner = ScenarioRunner(broker=sim_broker, lake_root=temp_dir)
        config = ScenarioConfig(
            scenario_type=ScenarioType.ORDERED_BUFFERED_REPLAY,
            name="Test Ordered Replay",
            description="FIFO buffered replay test",
            vehicle_count=2,
            duration_seconds=4.0,
            send_frequency_hz=1.0,
            disconnect_after_seconds=1.0,
            reconnect_after_seconds=3.0,
            reconnect_mode="ordered",
        )

        metrics, passed, violations = await runner.run_scenario(config, db_session=sim_db_session)
        assert passed is True, f"Violations: {violations}"
        assert metrics.canonical_valid == metrics.events_sent
        assert metrics.dlq_permanent == 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.anyio
async def test_scenario_clock_drift(sim_db_session, sim_broker):
    """Scenario 5: Fast test for Scoped Watermark Clock Drift Isolation."""
    temp_dir = tempfile.mkdtemp()
    try:
        runner = ScenarioRunner(broker=sim_broker, lake_root=temp_dir)
        config = ScenarioConfig(
            scenario_type=ScenarioType.CLOCK_DRIFT,
            name="Test Clock Drift",
            description="Scoped watermark isolation test",
            vehicle_count=2,
            duration_seconds=2.0,
            send_frequency_hz=1.0,
            clock_drift_seconds=300.0,
        )

        metrics, passed, violations = await runner.run_scenario(config, db_session=sim_db_session)
        assert passed is True, f"Violations: {violations}"
        assert metrics.canonical_valid == metrics.events_sent
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.anyio
async def test_scenario_sensor_corruption_dlq(sim_db_session, sim_broker):
    """Scenario 6: Fast test for Physical Range Violations quarantined to DLQ."""
    temp_dir = tempfile.mkdtemp()
    try:
        runner = ScenarioRunner(broker=sim_broker, lake_root=temp_dir)
        config = ScenarioConfig(
            scenario_type=ScenarioType.SENSOR_CORRUPTION,
            name="Test Sensor Corruption",
            description="DLQ corruption test",
            vehicle_count=2,
            duration_seconds=3.0,
            send_frequency_hz=1.0,
            corruption_rate=0.5,
        )

        metrics, passed, violations = await runner.run_scenario(config, db_session=sim_db_session)
        assert passed is True, f"Violations: {violations}"
        assert metrics.dlq_permanent > 0, "Corrupted packets must be routed to DLQ"
        # Conservation must hold exactly
        is_conserved, audit = metrics.verify_conservation()
        assert is_conserved is True
        assert audit["discrepancy"] == 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.anyio
async def test_scenario_conflicting_duplicate_dlq(sim_db_session, sim_broker):
    """Scenario 7: Fast test for Idempotent Replay vs Conflicting Payload Hash."""
    temp_dir = tempfile.mkdtemp()
    try:
        runner = ScenarioRunner(broker=sim_broker, lake_root=temp_dir)
        config = ScenarioConfig(
            scenario_type=ScenarioType.CONFLICTING_DUPLICATE,
            name="Test Conflicting Duplicate",
            description="Conflict detection test",
            vehicle_count=1,
            duration_seconds=2.0,
            send_frequency_hz=1.0,
            conflicting_duplicates_count=2,
        )

        metrics, passed, violations = await runner.run_scenario(config, db_session=sim_db_session)
        assert passed is True, f"Violations: {violations}"
        assert metrics.duplicate_replays > 0, "Benign replay must be deduplicated"
        assert metrics.dlq_conflict > 0, "Payload hash mismatch must be quarantined to DLQ"
        is_conserved, audit = metrics.verify_conservation()
        assert is_conserved is True
        assert audit["discrepancy"] == 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.anyio
async def test_scenario_transient_infra_failure_recovery(sim_db_session, sim_broker):
    """Scenario 8: Fast test for Transient Infrastructure Failure Retry & Recovery."""
    temp_dir = tempfile.mkdtemp()
    try:
        runner = ScenarioRunner(broker=sim_broker, lake_root=temp_dir)
        config = ScenarioConfig(
            scenario_type=ScenarioType.TRANSIENT_INFRA_FAILURE,
            name="Test Transient Failure",
            description="Transient retry test",
            vehicle_count=2,
            duration_seconds=2.0,
            send_frequency_hz=1.0,
            inject_db_dropout=True,
        )

        metrics, passed, violations = await runner.run_scenario(config, db_session=sim_db_session)
        assert passed is True, f"Violations: {violations}"
        assert metrics.dlq_transient > 0, "Transient failure must be recorded"
        assert metrics.unresolved_failures == 0, "All events must eventually resolve"
        is_conserved, _audit = metrics.verify_conservation()
        assert is_conserved is True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
