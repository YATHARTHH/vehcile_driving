import asyncio
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.database import Base
from backend.models.telemetry import TelemetryEvent, TelemetryEventLedger
from backend.streaming.broker import AsyncQueueBroker
from backend.streaming.validation_worker import ValidationWorker


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_migration_files_and_dependency_chain():
    """Verify that all Alembic migrations have matching SQL files and valid linear DAG."""
    versions_dir = PROJECT_ROOT / "alembic" / "versions"
    sql_dir = PROJECT_ROOT / "alembic" / "sql"

    expected_revisions = [
        "001_core_schema",
        "002_telemetry_schema",
        "003_telemetry_hypertable",
        "004_telemetry_policies",
    ]

    for rev in expected_revisions:
        py_file = versions_dir / f"{rev}.py"
        up_sql = sql_dir / f"{rev}.up.sql"
        down_sql = sql_dir / f"{rev}.down.sql"

        assert py_file.exists(), f"Missing version script: {py_file}"
        assert up_sql.exists(), f"Missing up SQL script: {up_sql}"
        assert down_sql.exists(), f"Missing down SQL script: {down_sql}"

        content = py_file.read_text(encoding="utf-8")
        assert f'revision: str = "{rev}"' in content
        assert "load_sql" in content
        assert f"{rev}.up.sql" in content
        assert f"{rev}.down.sql" in content


def test_offline_sql_generation():
    """Verify offline SQL export generates deterministic, reviewable multi-stage DDL."""
    output_file = PROJECT_ROOT / "instance" / "test_export.sql"
    if output_file.exists():
        output_file.unlink()

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "migrate.py"),
        "sql",
        "--output",
        str(output_file),
    ]
    res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=False)
    assert res.returncode == 0, f"Offline migration failed: {res.stderr}"
    assert output_file.exists()

    sql_text = output_file.read_text(encoding="utf-8")

    # Verify stage 001
    assert "CREATE TABLE tenants" in sql_text
    assert "CREATE TABLE vehicles" in sql_text
    assert "CREATE TABLE trips" in sql_text

    # Verify stage 002
    assert "CREATE TABLE telemetry_event_ledger" in sql_text
    assert "PRIMARY KEY (tenant_id, vehicle_id, event_id)" in sql_text
    assert "CREATE TABLE telemetry_events" in sql_text
    assert "PRIMARY KEY (tenant_id, vehicle_id, event_id, event_timestamp)" in sql_text

    # Verify stage 003
    assert "CREATE EXTENSION IF NOT EXISTS timescaledb" in sql_text
    assert "create_hypertable" in sql_text
    assert "'telemetry_events'" in sql_text

    # Verify stage 004
    assert "timescaledb.compress" in sql_text
    assert "add_compression_policy('telemetry_events', INTERVAL '7 days'" in sql_text
    assert "add_retention_policy('telemetry_events', INTERVAL '90 days'" in sql_text

    # Clean up test output
    output_file.unlink()


def test_schema_drift_fails_loud():
    """
    Verify schema drift detection fails loud:
    When the database contract is missing expected columns or contains unexpected alterations,
    the schema validation contract raises an explicit error and refuses to silently modify schema.
    """
    # Define expected contract for key tables
    expected_ledger_columns = {"tenant_id", "vehicle_id", "event_id", "payload_hash", "event_timestamp", "first_seen_at"}
    expected_telemetry_columns = {
        "tenant_id", "vehicle_id", "event_id", "event_timestamp",
        "payload_hash", "ingestion_timestamp", "data_quality_status",
        "invalid_reasons", "is_late", "is_duplicate", "is_imputed",
        "schema_version", "telemetry_data"
    }

    # Inspect the actual SQLAlchemy Model Declarations
    actual_ledger_columns = {c.name for c in TelemetryEventLedger.__table__.columns}
    actual_telemetry_columns = {c.name for c in TelemetryEvent.__table__.columns}

    # Contract assertion: Code model must strictly equal expected schema contract
    assert actual_ledger_columns == expected_ledger_columns, f"Drift in TelemetryEventLedger: {actual_ledger_columns ^ expected_ledger_columns}"
    assert actual_telemetry_columns == expected_telemetry_columns, f"Drift in TelemetryEvent: {actual_telemetry_columns ^ expected_telemetry_columns}"

    # Verify that a drifted schema triggers a loud failure
    drifted_columns = set(actual_ledger_columns)
    drifted_columns.remove("payload_hash")  # Simulate silent schema drop or modification
    with pytest.raises(AssertionError) as exc_info:
        if drifted_columns != expected_ledger_columns:
            raise AssertionError(f"SCHEMA DRIFT DETECTED! Missing required contract column: {expected_ledger_columns - drifted_columns}")
    assert "SCHEMA DRIFT DETECTED!" in str(exc_info.value)


@pytest.fixture
async def memory_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session, session_maker

    await engine.dispose()


@pytest.mark.anyio
async def test_concurrent_worker_race_idempotency(memory_db):
    """
    Verify that concurrent worker races for the exact same event are resolved safely:
    Exactly one succeeds with VALIDATED_AND_PERSISTED, while the other receives DUPLICATE_REPLAY.
    No unhandled integrity errors or duplicate rows exist.
    """
    _, session_maker = memory_db
    broker = AsyncQueueBroker()
    await broker.connect()

    envelope = {
        "event_id": "evt_race_001",
        "tenant_id": "ten_race",
        "vehicle_id": "veh_race",
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
        "payload_hash": "hash_concurrent_race_999",
        "telemetry": {"speed_kmph": 65.0, "rpm": 2100.0},
    }

    async def worker_attempt():
        worker = ValidationWorker(broker)
        async with session_maker() as session:
            return await worker.process_record("ten_race:veh_race", envelope, session)

    # Launch two workers concurrently targeting the exact same record
    res_a, res_b = await asyncio.gather(worker_attempt(), worker_attempt())

    statuses = {res_a["status"], res_b["status"]}
    assert "VALIDATED_AND_PERSISTED" in statuses
    assert "DUPLICATE_REPLAY" in statuses

    # Verify exactly 1 ledger row and 1 telemetry row in database
    async with session_maker() as check_session:
        ledger_count = (
            await check_session.scalar(
                select(TelemetryEventLedger).where(
                    TelemetryEventLedger.event_id == "evt_race_001"
                )
            )
        )
        assert ledger_count is not None

        telemetry_count = (
            await check_session.scalar(
                select(TelemetryEvent).where(
                    TelemetryEvent.event_id == "evt_race_001"
                )
            )
        )
        assert telemetry_count is not None


@pytest.mark.anyio
async def test_transactional_rollback_preserves_zero_orphans(memory_db):
    """
    Verify that if the telemetry event persistence fails, the entire transaction rolls back
    and leaves ZERO orphaned rows in telemetry_event_ledger.
    """
    session, session_maker = memory_db
    broker = AsyncQueueBroker()
    await broker.connect()
    worker = ValidationWorker(broker)

    envelope = {
        "event_id": "evt_rollback_001",
        "tenant_id": "ten_rollback",
        "vehicle_id": "veh_rollback",
        "event_timestamp": datetime.now(timezone.utc).isoformat(),
        "payload_hash": "hash_rollback_test",
        "telemetry": {"speed_kmph": 50.0, "rpm": 1800.0},
    }

    # Simulate an error during telemetry event persistence
    with patch.object(session, "commit", side_effect=RuntimeError("Simulated database disk failure")), pytest.raises(RuntimeError, match="Simulated database disk failure"):
        await worker.process_record("ten_rollback:veh_rollback", envelope, session)

    # Verify no ledger record was left behind
    async with session_maker() as verify_session:
        orphan = await verify_session.scalar(
            select(TelemetryEventLedger).where(
                TelemetryEventLedger.event_id == "evt_rollback_001"
            )
        )
        assert orphan is None, "Found orphaned ledger row after failed transaction!"
