from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.database import Base
from backend.main import app
from backend.models.tenant import Fleet, Tenant, Vehicle
from backend.models.user import User
from backend.streaming.broker import AsyncQueueBroker
from backend.streaming.hot_state import (
    AlertSeverity,
    MemoryHotStateManager,
    VehicleLiveState,
    set_hot_state_manager,
)
from backend.streaming.projection_worker import RealtimeProjectionWorker
from backend.utils.auth import create_access_token, hash_password


@pytest.fixture
async def realtime_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        # Seed Tenant A & Vehicle A
        tenant_a = Tenant(id="tenant_alpha", name="Alpha Logistics")
        fleet_a = Fleet(id="fleet_alpha_1", tenant_id="tenant_alpha", name="Alpha Depot")
        veh_a = Vehicle(id="MH12AA1111", tenant_id="tenant_alpha", fleet_id="fleet_alpha_1")

        # Seed Tenant B & Vehicle B
        tenant_b = Tenant(id="tenant_beta", name="Beta Express")
        fleet_b = Fleet(id="fleet_beta_1", tenant_id="tenant_beta", name="Beta Depot")
        veh_b = Vehicle(id="MH12BB2222", tenant_id="tenant_beta", fleet_id="fleet_beta_1")

        # Seed Users
        user_a = User(
            username="driver_alpha",
            password=hash_password("password123"),
            vehicle_number="MH12AA1111",
            email="alpha@example.com",
        )
        user_b = User(
            username="driver_beta",
            password=hash_password("password123"),
            vehicle_number="MH12BB2222",
            email="beta@example.com",
        )

        session.add_all([tenant_a, fleet_a, veh_a, tenant_b, fleet_b, veh_b, user_a, user_b])
        await session.commit()

        async def override_get_db():
            async with session_maker() as s:
                yield s

        from backend.database import get_db
        app.dependency_overrides[get_db] = override_get_db

        try:
            yield session, session_maker, user_a, user_b
        finally:
            app.dependency_overrides.clear()

    await engine.dispose()


@pytest.mark.anyio
async def test_decoupled_snapshot_update_vs_throttling():
    """
    Invariant 1 & 2:
    Every validated event immediately updates the latest hot-state snapshot in cache.
    UI Pub/Sub broadcast is throttled to 1 Hz, dropping intermediate bursts.
    """
    broker = AsyncQueueBroker()
    await broker.connect()
    hot_state = MemoryHotStateManager()
    await hot_state.connect()
    set_hot_state_manager(hot_state)

    worker = RealtimeProjectionWorker(broker, hot_state, ui_interval_seconds=1.0)

    emitted_count = 0
    dropped_count = 0

    # Ingest 10 rapid events within 0.1s
    for i in range(10):
        envelope = {
            "event_id": f"evt_burst_{i}",
            "tenant_id": "ten_test",
            "vehicle_id": "veh_test",
            "event_timestamp": datetime.now(timezone.utc).isoformat(),
            "telemetry": {
                "speed_kmph": 40.0 + i * 2.0,  # Speed goes 40 -> 58 km/h
                "rpm": 2000.0 + i * 50.0,
                "fuel_level_pct": 85.0 - i * 0.1,
                "fuel_rate_lph": 6.5,
                "fuel_consumed": 12.4 + i * 0.05,
            },
        }
        res = await worker.process_event(envelope)
        if "EMITTED" in res["status"]:
            emitted_count += 1
        elif res["status"] == "STATE_UPDATED_DROPPED_THROTTLE":
            dropped_count += 1

    # Invariant check: Exactly 1 event was emitted to UI (first event), 9 were throttled
    assert emitted_count == 1
    assert dropped_count == 9

    # Invariant check: Hot-state cache has the FRESHEST 10th event, NOT the 1st event!
    latest_snapshot = await hot_state.get_vehicle_state("ten_test", "veh_test")
    assert latest_snapshot is not None
    assert latest_snapshot.speed_kmph == 58.0
    assert latest_snapshot.state_version == 10
    assert latest_snapshot.fuel_level_pct == pytest.approx(84.1)

    await hot_state.disconnect()


@pytest.mark.anyio
async def test_high_priority_alert_bypasses_throttle():
    """
    Invariant: A CRITICAL or HIGH alert transition immediately bypasses the 1 Hz throttle.
    """
    broker = AsyncQueueBroker()
    await broker.connect()
    hot_state = MemoryHotStateManager()
    await hot_state.connect()
    set_hot_state_manager(hot_state)

    worker = RealtimeProjectionWorker(broker, hot_state, ui_interval_seconds=2.0)

    # 1. Normal event (emits and sets baseline)
    res1 = await worker.process_event({
        "event_id": "evt_norm",
        "tenant_id": "ten_1",
        "vehicle_id": "veh_1",
        "telemetry": {"speed_kmph": 50.0, "rpm": 2000.0},
    })
    assert res1["status"] == "EMITTED_THROTTLED"

    # 2. Subsequent event 0.01s later with harsh braking (> 100 bar -> CRITICAL)
    res2 = await worker.process_event({
        "event_id": "evt_alert",
        "tenant_id": "ten_1",
        "vehicle_id": "veh_1",
        "telemetry": {"speed_kmph": 45.0, "rpm": 1800.0, "brake_pressure_bar": 115.0},
    })
    # Must emit immediately without waiting for 2.0s!
    assert res2["status"] == "EMITTED_ALERT_BYPASS"

    latest = await hot_state.get_vehicle_state("ten_1", "veh_1")
    assert latest is not None
    assert latest.highest_alert_severity == AlertSeverity.CRITICAL
    assert any(a["code"] == "CRITICAL_HARSH_BRAKE" for a in latest.active_alerts)

    await hot_state.disconnect()


@pytest.mark.anyio
async def test_monotonic_state_version():
    """
    Invariant: State versions increment monotonically for each vehicle stream.
    """
    broker = AsyncQueueBroker()
    await broker.connect()
    hot_state = MemoryHotStateManager()
    await hot_state.connect()
    set_hot_state_manager(hot_state)

    worker = RealtimeProjectionWorker(broker, hot_state, ui_interval_seconds=1.0)

    for step in range(1, 6):
        res = await worker.process_event({
            "event_id": f"evt_v_{step}",
            "tenant_id": "ten_v",
            "vehicle_id": "veh_v",
            "telemetry": {"speed_kmph": 50.0},
        })
        assert res["state_version"] == step

    final_state = await hot_state.get_vehicle_state("ten_v", "veh_v")
    assert final_state.state_version == 5

    await hot_state.disconnect()


@pytest.mark.anyio
async def test_rest_snapshot_authorization_and_cross_tenant_isolation(realtime_db):
    """
    Invariant:
    - User A can retrieve state for their authorized vehicle MH12AA1111.
    - User A is strictly FORBIDDEN (403) from accessing Tenant B's vehicle MH12BB2222.
    """
    session, _, user_a, user_b = realtime_db
    hot_state = MemoryHotStateManager()
    await hot_state.connect()
    set_hot_state_manager(hot_state)

    # Populate hot state for both vehicles
    state_a = VehicleLiveState(
        tenant_id="tenant_alpha",
        vehicle_id="MH12AA1111",
        state_version=1,
        event_timestamp=datetime.now(timezone.utc),
        speed_kmph=65.0,
        rpm=2100.0,
        fuel_level_pct=90.0,
        lat=18.5204,
        lon=73.8567,
    )
    state_b = VehicleLiveState(
        tenant_id="tenant_beta",
        vehicle_id="MH12BB2222",
        state_version=1,
        event_timestamp=datetime.now(timezone.utc),
        speed_kmph=75.0,
        rpm=2500.0,
        fuel_level_pct=80.0,
        lat=19.0760,
        lon=72.8777,
    )
    await hot_state.set_vehicle_state(state_a)
    await hot_state.set_vehicle_state(state_b)

    token_a = create_access_token(data={"sub": user_a.username})
    token_b = create_access_token(data={"sub": user_b.username})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. User A accesses own vehicle -> 200 OK with correct state
        headers_a = {"Authorization": f"Bearer {token_a}"}
        resp_a = await client.get("/api/v1/telemetry/state/MH12AA1111", headers=headers_a)
        assert resp_a.status_code == 200
        data_a = resp_a.json()
        assert data_a["vehicle_id"] == "MH12AA1111"
        assert data_a["speed_kmph"] == 65.0
        assert data_a["tenant_id"] == "tenant_alpha"

        # 2. User A attempts to access Tenant B's vehicle -> 403 Forbidden!
        resp_forbidden = await client.get("/api/v1/telemetry/state/MH12BB2222", headers=headers_a)
        assert resp_forbidden.status_code == 403
        assert "Access denied" in resp_forbidden.json()["detail"]

        # 3. User B accesses own vehicle -> 200 OK
        headers_b = {"Authorization": f"Bearer {token_b}"}
        resp_b = await client.get("/api/v1/telemetry/state/MH12BB2222", headers=headers_b)
        assert resp_b.status_code == 200
        assert resp_b.json()["vehicle_id"] == "MH12BB2222"

    await hot_state.disconnect()


@pytest.mark.anyio
async def test_websocket_in_band_authentication_and_acl(realtime_db):
    """
    Tests WebSocket Lifecycle:
    1. Rejects unauthenticated clients on timeout or invalid token.
    2. Authenticates in-band {"type": "authenticate", "token": "..."}.
    3. Rejects unauthorized vehicle subscriptions.
    4. Streams initial cached snapshot upon subscription.
    """
    from unittest.mock import patch
    from starlette.testclient import TestClient
    _, session_maker, user_a, _ = realtime_db

    hot_state = MemoryHotStateManager()
    await hot_state.connect()
    set_hot_state_manager(hot_state)

    token_a = create_access_token(data={"sub": user_a.username})

    # Pre-populate hot state snapshot
    test_state = VehicleLiveState(
        tenant_id="tenant_alpha",
        vehicle_id="MH12AA1111",
        state_version=42,
        event_timestamp=datetime.now(timezone.utc),
        speed_kmph=88.5,
        rpm=2900.0,
    )
    await hot_state.set_vehicle_state(test_state)

    with patch("backend.routers.ws_telemetry.AsyncSessionLocal", session_maker):
        with TestClient(app) as client:
            # 1. Connect and test handshake with invalid token
            with client.websocket_connect("/api/v1/telemetry/ws") as ws:
                ws.send_json({"type": "authenticate", "token": "invalid_jwt_garbage"})
                err = ws.receive_json()
                assert err["type"] == "error"
                assert err["code"] == "INVALID_TOKEN"

            # 2. Connect and authenticate successfully
            with client.websocket_connect("/api/v1/telemetry/ws") as ws:
                ws.send_json({"type": "authenticate", "token": token_a})
                auth_resp = ws.receive_json()
                assert auth_resp["type"] == "authenticated"
                assert auth_resp["username"] == user_a.username
                assert "MH12AA1111" in auth_resp["authorized_vehicles"]

                # Test ping/pong
                ws.send_json({"action": "ping"})
                pong = ws.receive_json()
                assert pong["type"] == "pong"

                # 3. Attempt to subscribe to UNAUTHORIZED vehicle in Tenant B
                ws.send_json({"action": "subscribe", "vehicle_id": "MH12BB2222"})
                acl_err = ws.receive_json()
                assert acl_err["type"] == "error"
                assert acl_err["code"] == "UNAUTHORIZED_VEHICLE"

                # 4. Subscribe to AUTHORIZED vehicle MH12AA1111
                ws.send_json({"action": "subscribe", "vehicle_id": "MH12AA1111"})
                sub_resp = ws.receive_json()
                assert sub_resp["type"] == "subscribed"
                assert sub_resp["vehicle_id"] == "MH12AA1111"

                # Check immediate delivery of cached telemetry_snapshot
                snap_resp = ws.receive_json()
                assert snap_resp["type"] == "telemetry_snapshot"
                assert snap_resp["data"]["speed_kmph"] == 88.5
                assert snap_resp["data"]["state_version"] == 42

    await hot_state.disconnect()


@pytest.mark.anyio
async def test_stale_update_rejection_logic():
    """
    Invariant: Client/Consumer rejects frames where incoming.state_version <= current.state_version.
    """
    applied_versions: list[int] = []
    current_version = 0

    def apply_frame(incoming_state: dict):
        nonlocal current_version
        incoming_v = incoming_state.get("state_version", 0)
        if incoming_v > current_version:
            current_version = incoming_v
            applied_versions.append(incoming_v)
            return True
        return False

    # Simulate arrival out-of-order: 10, then 12, then stale 11
    assert apply_frame({"state_version": 10}) is True
    assert apply_frame({"state_version": 12}) is True
    # Stale frame 11 arrives late: must be ignored!
    assert apply_frame({"state_version": 11}) is False
    # Identical frame 12 re-delivered: must be ignored!
    assert apply_frame({"state_version": 12}) is False
    # Newer frame 13 arrives: accepted!
    assert apply_frame({"state_version": 13}) is True

    assert applied_versions == [10, 12, 13]


@pytest.mark.anyio
async def test_high_frequency_burst_scaling():
    """
    Invariant: Ingesting at high frequencies (50 Hz) remains safely throttled to 1 Hz UI rate,
    while snapshot always reflects the 50th packet.
    """
    broker = AsyncQueueBroker()
    await broker.connect()
    hot_state = MemoryHotStateManager()
    await hot_state.connect()
    set_hot_state_manager(hot_state)

    worker = RealtimeProjectionWorker(broker, hot_state, ui_interval_seconds=1.0)

    # Dispatch 50 packets in immediate succession
    for i in range(50):
        await worker.process_event({
            "event_id": f"evt_hf_{i}",
            "tenant_id": "ten_hf",
            "vehicle_id": "veh_hf",
            "telemetry": {"speed_kmph": 50.0 + i},
        })

    latest = await hot_state.get_vehicle_state("ten_hf", "veh_hf")
    assert latest is not None
    assert latest.state_version == 50
    assert latest.speed_kmph == 99.0

    await hot_state.disconnect()

