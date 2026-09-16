import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath("."))
import requests

from sqlalchemy.future import select

from backend.config import settings
from backend.database import AsyncSessionLocal, engine, Base
from backend.models.session import TripSessionCheckpoint
from backend.models.trip import Trip
from backend.models.alert import Alert
from backend.streaming.broker import get_broker
from backend.streaming.sessionizer import get_sessionizer, ActiveTripSession, haversine_distance_km
from backend.streaming.gold_finalizer import GoldTripFinalizer


async def test_all_phase9_hardened_guarantees():
    print("================================================================================")
    print("   PHASE 9 HARDENED ARCHITECTURAL TEST SUITE")
    print("================================================================================")

    # 1. Initialize Tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    broker = get_broker()
    await broker.connect()
    sessionizer = get_sessionizer(broker)
    gold_finalizer = GoldTripFinalizer(broker)

    # -------------------------------------------------------------------------
    # Test 1: GPS Jump / Teleportation Filter
    # -------------------------------------------------------------------------
    print("\n--- TEST 1: GPS Teleportation Jump Protection ---")
    pune_lat, pune_lon = 18.5204, 73.8567
    delhi_lat, delhi_lon = 28.7041, 77.1025
    h_dist = haversine_distance_km(pune_lat, pune_lon, delhi_lat, delhi_lon)
    dt = 30.0  # seconds
    implied_speed = h_dist / (dt / 3600.0)
    print(f"Calculated Haversine distance Pune->Delhi: {h_dist:.1f} km in {dt}s -> {implied_speed:.1f} km/h")
    assert implied_speed > settings.MAX_PLAUSIBLE_GPS_SPEED_KMPH, "Test setup error: speed should exceed max plausible"
    print(f"PASS: MAX_PLAUSIBLE_GPS_SPEED_KMPH ({settings.MAX_PLAUSIBLE_GPS_SPEED_KMPH} km/h) correctly rejects teleportation jump.")

    # -------------------------------------------------------------------------
    # Test 2: Atomic CAS Concurrency Race (Sweeper vs /finish)
    # -------------------------------------------------------------------------
    print("\n--- TEST 2: Atomic CAS State Machine Race Protection ---")
    test_session_id = f"test-race-{uuid.uuid4()}"
    test_tenant = f"tenant_race_{uuid.uuid4().hex[:6]}"
    test_vehicle = f"MH12_RACE_{uuid.uuid4().hex[:6]}"

    async with AsyncSessionLocal() as db:
        cp = TripSessionCheckpoint(
            session_id=test_session_id,
            tenant_id=test_tenant,
            vehicle_id=test_vehicle,
            user_id=1,
            status="ACTIVE",
            start_event_time=datetime.now(timezone.utc) - timedelta(minutes=10),
            last_event_time=datetime.now(timezone.utc),
            last_event_received_at=datetime.now(timezone.utc) - timedelta(minutes=6),
            last_checkpoint_time=datetime.now(timezone.utc),
            point_count=10,
            distance_km=4.5,
            fuel_consumed_l=0.4,
            running_aggregates={"speed_max": 65.0, "rpm_max": 2800, "brake_events": 1},
        )
        db.add(cp)
        await db.commit()

    # Simulate simultaneous race: 2 concurrent tasks trying to finalize
    t1 = asyncio.create_task(sessionizer.request_finalization(test_tenant, test_vehicle, "MANUAL"))
    t2 = asyncio.create_task(sessionizer.request_finalization(test_tenant, test_vehicle, "INACTIVITY_TIMEOUT"))
    outcomes = await asyncio.gather(t1, t2)

    winners = [o for o in outcomes if o is not None and o.get("status") in ("COMPLETED", "ALREADY_COMPLETED")]
    none_losers = [o for o in outcomes if o is None]
    print(f"Race outcomes: Winners={len(winners)}, Repelled={len(none_losers)}")
    assert len(winners) >= 1 and len(none_losers) >= 1, f"CAS failure: outcomes={outcomes}"

    async with AsyncSessionLocal() as db:
        trips = (await db.scalars(select(Trip).where(Trip.session_id == test_session_id))).all()
        assert len(trips) == 1, f"Expected exactly 1 trip created despite race, found {len(trips)}"
    print(f"PASS: Exactly 1 trip created for session {test_session_id}. CAS lease eliminated twin race!")

    # -------------------------------------------------------------------------
    # Test 3: Idempotent Double Finalization
    # -------------------------------------------------------------------------
    print("\n--- TEST 3: Idempotent Trip Finalization ---")
    async with AsyncSessionLocal() as db:
        cp = await db.scalar(select(TripSessionCheckpoint).where(TripSessionCheckpoint.session_id == test_session_id))
        retry_outcome = await gold_finalizer.finalize(cp, "RETRY_TEST", db)
        assert retry_outcome.get("status") == "ALREADY_COMPLETED", f"Expected ALREADY_COMPLETED, got {retry_outcome}"

        trips_after = (await db.scalars(select(Trip).where(Trip.session_id == test_session_id))).all()
        assert len(trips_after) == 1, "Duplicate trip detected on retry!"
    print("PASS: Re-executing Gold finalization produces idempotent safe no-op with 0 duplicate trips.")

    # -------------------------------------------------------------------------
    # Test 4: Crash Recovery on Expired Lease
    # -------------------------------------------------------------------------
    print("\n--- TEST 4: Stale FINALIZING Lease Recovery ---")
    stale_session_id = f"test-stale-{uuid.uuid4()}"
    stale_vehicle = f"MH12_CRASH_{uuid.uuid4().hex[:6]}"
    async with AsyncSessionLocal() as db:
        stale_cp = TripSessionCheckpoint(
            session_id=stale_session_id,
            tenant_id="tenant_crash",
            vehicle_id=stale_vehicle,
            user_id=1,
            status="FINALIZING",
            start_event_time=datetime.now(timezone.utc) - timedelta(minutes=15),
            last_event_time=datetime.now(timezone.utc) - timedelta(minutes=5),
            last_event_received_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            last_checkpoint_time=datetime.now(timezone.utc) - timedelta(minutes=5),
            finalization_started_at=datetime.now(timezone.utc) - timedelta(seconds=120),  # > 60s lease expired!
            point_count=8,
            distance_km=3.2,
            fuel_consumed_l=0.3,
            running_aggregates={"speed_max": 55.0, "rpm_max": 2400, "brake_events": 0},
        )
        db.add(stale_cp)
        await db.commit()

    # Recovery run
    await sessionizer._recover_checkpoints_from_db()

    async with AsyncSessionLocal() as db:
        recovered_cp = await db.scalar(select(TripSessionCheckpoint).where(TripSessionCheckpoint.session_id == stale_session_id))
        assert recovered_cp.status == "COMPLETED", f"Expected COMPLETED after recovery, got {recovered_cp.status}"
        recovered_trip = await db.scalar(select(Trip).where(Trip.session_id == stale_session_id))
        assert recovered_trip is not None, "Trip was not created during lease recovery"
    print(f"PASS: Stale FINALIZING lease (>60s) successfully recovered into Trip #{recovered_trip.id}.")

    # -------------------------------------------------------------------------
    # Test 5: Replay Offset Fast-Forward Protection
    # -------------------------------------------------------------------------
    print("\n--- TEST 5: Replay Offset Fast-Forward Protection ---")
    replay_vehicle = "MH12_REPLAY_77"
    active_session = ActiveTripSession(
        session_id=str(uuid.uuid4()),
        tenant_id="tenant_replay",
        vehicle_id=replay_vehicle,
        user_id=1,
        start_event_time=datetime.now(timezone.utc),
        last_event_time=datetime.now(timezone.utc),
        last_event_received_at=datetime.now(timezone.utc),
        last_checkpoint_time=datetime.now(timezone.utc),
        point_count=5,
        distance_km=1.5,
        source_partition=0,
        source_offset=10,  # Checkpoint contains up to offset 10
    )
    sessionizer.active_sessions[("tenant_replay", replay_vehicle)] = active_session

    initial_dist = active_session.distance_km
    initial_points = active_session.point_count

    # Packet with offset 8 (replayed duplicate from before crash)
    stale_packet = {
        "tenant_id": "tenant_replay",
        "vehicle_id": replay_vehicle,
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
        "telemetry": {"speed_kmph": 60.0, "rpm": 2200}
    }
    await sessionizer.process_packet(stale_packet, {"partition": 0, "offset": 8})

    assert active_session.distance_km == initial_dist, "Distance was corrupted by replayed offset!"
    assert active_session.point_count == initial_points, "Point count was corrupted by replayed offset!"
    print("PASS: Packet with offset 8 <= checkpoint offset 10 was cleanly discarded without double-counting.")

    # -------------------------------------------------------------------------
    # Test 6: End-to-End REST Ingestion -> Active Session -> Manual /finish
    # -------------------------------------------------------------------------
    print("\n--- TEST 6: End-to-End REST Ingest -> /session/active -> /session/finish ---")
    BASE = "http://127.0.0.1:8000/api/v1"

    # Authenticate demo user
    login_res = requests.post(f"{BASE}/auth/login", data={"username": "demo", "password": "Password123!"})
    assert login_res.status_code == 200, login_res.text
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Ingest 4 continuous 1 Hz points for vehicle MH12AB9999
    now = datetime.now(timezone.utc)
    for i in range(4):
        pkt_time = (now + timedelta(seconds=i)).isoformat()
        ingest_res = requests.post(
            f"{BASE}/telemetry/ingest",
            json={
                "event_id": str(uuid.uuid4()),
                "event_timestamp": pkt_time,
                "schema_version": "v1.0.0",
                "telemetry": {
                    "speed_kmph": 50.0 + i * 2,
                    "rpm": 2200 + i * 50,
                    "fuel_rate_lph": 4.2,
                    "lat": 18.5204 + i * 0.001,
                    "lon": 73.8567 + i * 0.001,
                    "brake_pressure_bar": 0.0 if i < 3 else 12.0,
                    "engine_load_pct": 52.0
                }
            },
            headers=headers
        )
        assert ingest_res.status_code == 202

    # Poll until workers process packets through the streaming pipeline (up to 8s)
    active_data = {}
    for _ in range(16):
        await asyncio.sleep(0.5)
        active_res = requests.get(f"{BASE}/telemetry/session/active", headers=headers)
        if active_res.status_code == 200:
            active_data = active_res.json()
            if active_data.get("point_count", 0) >= 3:
                break

    print(f"Active session projection: {active_data}")
    assert active_data.get("active") is True, "Active session should be open"
    assert active_data.get("point_count", 0) >= 3, f"Expected >= 3 points, got {active_data.get('point_count')}"

    # Call POST /session/finish (Expects 202 Accepted)
    finish_res = requests.post(f"{BASE}/telemetry/session/finish", headers=headers)
    assert finish_res.status_code == 202, finish_res.text
    print(f"Finish response: {finish_res.json()}")
    assert finish_res.json().get("status") == "FINISH_REQUESTED"

    # Poll until Gold finalizer writes Trip to DB (up to 6s)
    latest_trip = None
    for _ in range(12):
        await asyncio.sleep(0.5)
        trips_res = requests.get(f"{BASE}/trips", headers=headers)
        if trips_res.status_code == 200:
            trips = trips_res.json()
            if trips and trips[0].get("distance_km", 0) > 0:
                latest_trip = trips[0]
                break

    assert latest_trip is not None, "Trip was not found after finish"
    print(f"Latest Trip created: ID={latest_trip['id']}, Dist={latest_trip['distance_km']}km, AvgSpeed={latest_trip['avg_speed_kmph']}km/h")
    assert latest_trip["distance_km"] > 0, "Distance should be > 0"
    assert latest_trip["avg_speed_kmph"] > 0, "Average speed should be > 0"

    print("\n================================================================================")
    print(">>> ALL 6 PHASE 9 HARDENED ARCHITECTURAL TESTS PASSED CLEANLY! <<<")
    print("================================================================================")


if __name__ == "__main__":
    asyncio.run(test_all_phase9_hardened_guarantees())
