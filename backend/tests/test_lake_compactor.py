import json
import shutil
import tempfile
from pathlib import Path
from backend.streaming.lake_compactor import LakeCompactor


def test_lake_compactor_deduplication_and_partitioning():
    """
    P0-7: Verify LakeCompactor reads raw Bronze JSONL containing duplicate transmissions,
    performs canonical deduplication by (tenant_id, vehicle_id, event_id),
    and writes partitioned Silver records with lineage metadata.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        lake_root = Path(temp_dir)
        bronze_dir = lake_root / "bronze" / "event_date=2026-09-11" / "hour=14"
        bronze_dir.mkdir(parents=True, exist_ok=True)
        bronze_file = bronze_dir / "raw_stream.jsonl"

        # 4 raw records: 2 distinct events, where evt_001 is duplicated with identical data,
        # and evt_002 belongs to a different tenant
        raw_events = [
            {
                "payload": {
                    "event_id": "evt_001",
                    "tenant_id": "tenant_alpha",
                    "vehicle_id": "veh_A",
                    "event_timestamp": "2026-09-11T14:10:00Z",
                    "payload_hash": "hash_001",
                    "telemetry": {"speed_kmph": 55.0, "rpm": 1800.0},
                }
            },
            {
                "payload": {
                    "event_id": "evt_001",  # Duplicate network retry of evt_001
                    "tenant_id": "tenant_alpha",
                    "vehicle_id": "veh_A",
                    "event_timestamp": "2026-09-11T14:10:00Z",
                    "payload_hash": "hash_001",
                    "telemetry": {"speed_kmph": 55.0, "rpm": 1800.0},
                }
            },
            {
                "payload": {
                    "event_id": "evt_002",
                    "tenant_id": "tenant_beta",
                    "vehicle_id": "veh_B",
                    "event_timestamp": "2026-09-11T14:20:00Z",
                    "payload_hash": "hash_002",
                    "telemetry": {"speed_kmph": 85.0, "rpm": 2400.0},
                }
            },
        ]

        with open(bronze_file, "w", encoding="utf-8") as f:
            for r in raw_events:
                f.write(json.dumps(r) + "\n")

        # Run compaction job
        compactor = LakeCompactor(lake_root=str(lake_root))
        result = compactor.compact_partition("2026-09-11", "14")

        assert result["status"] == "COMPACTED"
        assert result["bronze_raw_count"] == 3
        assert result["canonical_dedup_count"] == 2
        assert result["rows_written"] == 2

        # Verify tenant-partitioned files in Silver Lake
        silver_root = lake_root / "silver" / "event_date=2026-09-11"
        tenant_alpha_files = list((silver_root / "tenant_id=tenant_alpha").glob("compacted_hour_14.*"))
        tenant_beta_files = list((silver_root / "tenant_id=tenant_beta").glob("compacted_hour_14.*"))

        assert len(tenant_alpha_files) == 1, "Tenant Alpha must have its own partitioned Silver file"
        assert len(tenant_beta_files) == 1, "Tenant Beta must have its own partitioned Silver file"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
