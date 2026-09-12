import asyncio
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.database import Base
from backend.main import app
from backend.schemas.registry import schema_registry
from backend.streaming.broker import AsyncQueueBroker, set_broker
from backend.streaming.bronze_sink import BronzeSinkWorker
from backend.streaming.validation_worker import ValidationWorker


@pytest.fixture
async def test_db_session():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session_maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with test_session_maker() as session:
        yield session

    await test_engine.dispose()


@pytest.mark.anyio
async def test_bronze_sink_persists_raw_before_validation():
    """P0-1: Verify Bronze sink writes verbatim JSONL before validation occurs."""
    temp_dir = tempfile.mkdtemp()
    try:
        broker = AsyncQueueBroker()
        await broker.connect()
        sink = BronzeSinkWorker(broker, lake_root=temp_dir, batch_size=1)

        # Publish a corrupted packet (RPM = -500)
        corrupted_packet = {
            "event_id": "evt_corrupt_001",
            "tenant_id": "ten_1",
            "vehicle_id": "veh_1",
            "event_timestamp": datetime.now(timezone.utc).isoformat(),
            "telemetry": {"rpm": -500.0, "speed_kmph": 60.0},
        }

        # Start sink task and publish
        sink_task = asyncio.create_task(sink.run())
        await asyncio.sleep(0.05)
        await broker.publish("telemetry.raw", "ten_1:veh_1", corrupted_packet)

        # Wait a moment for consumer processing
        await asyncio.sleep(0.05)
        sink.stop()
        sink_task.cancel()
        try:
            await sink_task
        except asyncio.CancelledError:
            pass

        # Verify Bronze file exists and contains the corrupted packet
        bronze_files = list(Path(temp_dir).rglob("raw_stream.jsonl"))
        assert len(bronze_files) >= 1, "Bronze raw_stream.jsonl must exist"

        with open(bronze_files[0], "r", encoding="utf-8") as f:  # noqa: ASYNC230
            content = f.read()
            assert "evt_corrupt_001" in content
            assert "-500.0" in content, "Corrupted sensor value must be preserved in raw Bronze forensics!"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.anyio
async def test_validation_worker_quarantines_invalid_sensor(test_db_session):
    """Verify physical range violation routes to DLQ as PERMANENT_FAILURE."""
    broker = AsyncQueueBroker()
    await broker.connect()
    worker = ValidationWorker(broker)

    dlq_received = []

    async def dlq_listener():
        async for key, val, _ in broker.subscribe("telemetry.dlq"):
            dlq_received.append(val)

    listener_task = asyncio.create_task(dlq_listener())

    corrupt_envelope = {
        "event_id": "evt_bad_rpm",
        "tenant_id": "ten_test",
        "vehicle_id": "veh_test",
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
        "telemetry": {"rpm": -500.0, "speed_kmph": 50.0},
    }

    result = await worker.process_record("ten_test:veh_test", corrupt_envelope, test_db_session)
    assert result["status"] == "QUARANTINED_PERMANENT"

    await asyncio.sleep(0.05)
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass

    assert len(dlq_received) == 1
    assert dlq_received[0]["error_code"] == "PHYSICAL_RANGE_VIOLATION"
    assert dlq_received[0]["failure_category"] == "PERMANENT_FAILURE"


@pytest.mark.anyio
async def test_validation_worker_idempotency_payload_hash(test_db_session):
    """P0-6: Verify payload hash differentiates benign replay from conflicting event ID."""
    broker = AsyncQueueBroker()
    await broker.connect()
    worker = ValidationWorker(broker)

    valid_envelope_1 = {
        "event_id": "evt_idemp_100",
        "tenant_id": "ten_test",
        "vehicle_id": "veh_test",
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
        "payload_hash": "hash_abc_123",
        "telemetry": {"speed_kmph": 60.0, "rpm": 2000.0},
    }

    # First insert: success
    res1 = await worker.process_record("ten_test:veh_test", valid_envelope_1, test_db_session)
    assert res1["status"] == "VALIDATED_AND_PERSISTED"

    # Second insert with SAME event_id and SAME payload hash: benign duplicate
    res2 = await worker.process_record("ten_test:veh_test", valid_envelope_1, test_db_session)
    assert res2["status"] == "DUPLICATE_REPLAY"

    # Third insert with SAME event_id but DIFFERENT payload hash: conflict!
    conflicting_envelope = dict(valid_envelope_1)
    conflicting_envelope["payload_hash"] = "hash_xyz_999"  # Altered data!
    conflicting_envelope["telemetry"] = {"speed_kmph": 120.0, "rpm": 5000.0}

    res3 = await worker.process_record("ten_test:veh_test", conflicting_envelope, test_db_session)
    assert res3["status"] == "CONFLICTING_EVENT_QUARANTINED"


def test_schema_registry_backward_compatibility():
    """P0-5: Verify Schema Registry BACKWARD compatibility rules."""
    base_schema = schema_registry.get_schema("v1.0.0")
    assert base_schema is not None

    # Compatible modification: add an optional field
    compatible_schema = json.loads(json.dumps(base_schema))
    compatible_schema["properties"]["ambient_temp"] = {"type": "number", "default": 25.0}

    is_compat, violations = schema_registry.validate_backward_compatibility("v1.0.0", compatible_schema)
    assert is_compat is True
    assert len(violations) == 0

    # Incompatible modification: remove required 'event_id'
    incompatible_schema = json.loads(json.dumps(base_schema))
    del incompatible_schema["properties"]["event_id"]

    is_compat, violations = schema_registry.validate_backward_compatibility("v1.0.0", incompatible_schema)
    assert is_compat is False
    assert any("Cannot remove required fields" in v for v in violations)


@pytest.mark.anyio
async def test_stateless_ingestion_api():
    """Verify POST /api/v1/telemetry/ingest endpoint returns 202 Accepted with server-derived identity."""
    broker = AsyncQueueBroker()
    await broker.connect()
    set_broker(broker)

    raw_published = []

    async def raw_listener():
        async for key, val, _ in broker.subscribe("telemetry.raw"):
            raw_published.append((key, val))

    listener_task = asyncio.create_task(raw_listener())
    await asyncio.sleep(0.05)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "event_id": "evt_api_001",
            "event_timestamp": "2026-09-11T14:30:00Z",
            "schema_version": "v1.0.0",
            "telemetry": {"speed_kmph": 72.0, "rpm": 2300.0},
        }

        # Device passes credentials in headers (P0-3)
        headers = {
            "x-device-id": "MH12AB1234",
            "x-tenant-id": "tenant_fedex_india",
        }

        response = await client.post("/api/v1/telemetry/ingest", json=payload, headers=headers)
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert data["event_id"] == "evt_api_001"
        assert data["processing"] == "asynchronous"

    await asyncio.sleep(0.05)
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass

    assert len(raw_published) == 1
    key, envelope = raw_published[0]
    assert key == "tenant_fedex_india:MH12AB1234"
    assert envelope["tenant_id"] == "tenant_fedex_india"
    assert envelope["vehicle_id"] == "MH12AB1234"
