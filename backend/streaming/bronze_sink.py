import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import settings
from backend.streaming.broker import EventBroker

logger = logging.getLogger("fleettrack.streaming.bronze_sink")


class BronzeSinkWorker:
    """
    Bronze Lake Sink Worker.
    Consumes verbatim streams from telemetry.raw BEFORE any validation occurs (P0-1).
    Enforces the Durability Commit Sequence (P1):
        1. Consume message from broker
        2. Append verbatim JSONL to local/object store buffer
        3. Flush and fsync (durable write)
        4. Commit broker offset
    Bronze Policy: At-least-once raw preservation, duplicates retained for forensics.
    """
    def __init__(
        self,
        broker: EventBroker,
        lake_root: str | None = None,
        batch_size: int = 50,
    ) -> None:
        self.broker = broker
        self.lake_root = Path(lake_root or settings.LOCAL_LAKE_PATH) / "bronze"
        self.batch_size = batch_size
        self._running: bool = False
        self.lake_root.mkdir(parents=True, exist_ok=True)

    def _get_target_path(self, event_time_str: str) -> Path:
        """Partition by event_date=YYYY-MM-DD/hour=HH to avoid small file proliferation."""
        try:
            dt = datetime.fromisoformat(event_time_str.replace("Z", "+00:00"))
        except Exception:
            dt = datetime.now(timezone.utc)

        date_part = dt.strftime("%Y-%m-%d")
        hour_part = dt.strftime("%H")
        dir_path = self.lake_root / f"event_date={date_part}" / f"hour={hour_part}"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path / "raw_stream.jsonl"

    async def run(self) -> None:
        self._running = True
        logger.info(f"[BronzeSink] Started raw sink worker targeting {self.lake_root}")

        buffer: list[tuple[Path, str, dict[str, Any]]] = []

        try:
            async for key, value, metadata in self.broker.subscribe("telemetry.raw", group_id="fleettrack-bronze-sink"):
                if not self._running:
                    break

                event_time = value.get("event_timestamp", datetime.now(timezone.utc).isoformat())
                target_file = self._get_target_path(event_time)

                # Lineage stamped on receipt
                lineage_envelope = {
                    "_raw_receipt_timestamp": datetime.now(timezone.utc).isoformat(),
                    "_broker_partition": metadata.get("partition", 0),
                    "_broker_offset": metadata.get("offset", 0),
                    "_topic": "telemetry.raw",
                    "payload": value,
                }
                serialized = json.dumps(lineage_envelope) + "\n"
                buffer.append((target_file, serialized, metadata))

                if len(buffer) >= self.batch_size:
                    await self._flush_buffer(buffer)
                    buffer.clear()

            # Flush remaining upon clean stop
            if buffer:
                await self._flush_buffer(buffer)
                buffer.clear()

        except Exception as e:
            logger.error(f"[BronzeSink] Error in Bronze sink loop: {e}", exc_info=True)
            raise

    async def _flush_buffer(self, buffer: list[tuple[Path, str, dict[str, Any]]]) -> None:
        """
        Durably commits the batch to disk/storage before committing offsets.
        """
        # Group by target file
        file_map: dict[Path, list[str]] = {}
        for target_file, serialized, _ in buffer:
            file_map.setdefault(target_file, []).append(serialized)

        # Durable write & fsync
        for target_file, lines in file_map.items():
            with open(target_file, "a", encoding="utf-8") as f:
                f.writelines(lines)
                f.flush()
                os.fsync(f.fileno())  # Guaranteed hardware durable write

        # Offset commitment strictly follows durable file write
        if self.broker.supports_offset_commit and buffer:
            last_metadata = buffer[-1][2]
            await self.broker.commit_offset(
                topic=last_metadata.get("topic", "telemetry.raw"),
                partition=last_metadata.get("partition", 0),
                offset=last_metadata.get("offset", 0),
            )

    def stop(self) -> None:
        self._running = False
        logger.info("[BronzeSink] Stopping Bronze sink worker")
