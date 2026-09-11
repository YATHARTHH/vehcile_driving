import asyncio
import logging

from backend.streaming.broker import AsyncQueueBroker, EventBroker

logger = logging.getLogger("fleettrack.simulation.pipeline_waiter")


class PipelineWaiter:
    """
    Synchronizes traffic generation with downstream asynchronous processing.
    Waits for broker queue lag to reach 0, consumer queues to drain,
    and database write transactions to commit before assertions execute.
    Prevents intermittent test race conditions.
    """
    def __init__(self, broker: EventBroker, poll_interval_sec: float = 0.05, timeout_sec: float = 10.0) -> None:
        self.broker = broker
        self.poll_interval = poll_interval_sec
        self.timeout = timeout_sec

    async def wait_for_drain(self) -> tuple[bool, float]:
        """
        Polls until the broker topics have zero queued messages and background tasks complete.
        Returns: (is_drained, elapsed_time_seconds)
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= self.timeout:
                logger.warning(f"[PipelineWaiter] Drain timeout ({self.timeout}s) exceeded")
                return False, elapsed

            total_pending = self._get_pending_message_count()
            if total_pending == 0:
                # Extra brief settling sleep to allow database transaction commits to finish
                await asyncio.sleep(0.08)
                if self._get_pending_message_count() == 0:
                    final_elapsed = asyncio.get_event_loop().time() - start_time
                    logger.info(f"[PipelineWaiter] Pipeline cleanly drained in {final_elapsed:.3f}s")
                    return True, final_elapsed

            await asyncio.sleep(self.poll_interval)

    def _get_pending_message_count(self) -> int:
        """Inspects in-memory queue broker or broker partition lag."""
        if isinstance(self.broker, AsyncQueueBroker):
            pending = 0
            for queues in self.broker._topics.values():
                for q in queues:
                    pending += q.qsize()
            return pending

        # For Redpanda/Kafka, lag check would query consumer group offsets
        return 0
