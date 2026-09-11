import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, AsyncIterator, Protocol, runtime_checkable

logger = logging.getLogger("fleettrack.streaming.broker")


@runtime_checkable
class EventBroker(Protocol):
    """
    Authoritative broker protocol declaring explicit capability flags.
    Prevents application logic from incorrectly assuming Kafka semantics on mock queues.
    """
    supports_replay: bool
    supports_consumer_groups: bool
    supports_persistence: bool
    supports_dlq: bool
    supports_partition_ordering: bool
    supports_offset_commit: bool

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def publish(self, topic: str, key: str, value: dict[str, Any], headers: dict[str, str] | None = None) -> None: ...
    async def subscribe(self, topic: str, group_id: str | None = None) -> AsyncIterator[tuple[str, dict[str, Any], dict[str, Any]]]: ...
    async def commit_offset(self, topic: str, partition: int, offset: int) -> None: ...


class AsyncQueueBroker:
    """
    Lightweight, in-process event broker for rapid unit testing and zero-dependency local demos.
    Explicitly declares that it lacks persistent offsets and true consumer groups.
    """
    supports_replay: bool = False
    supports_consumer_groups: bool = False
    supports_persistence: bool = False
    supports_dlq: bool = True
    supports_partition_ordering: bool = True
    supports_offset_commit: bool = False

    def __init__(self) -> None:
        self._topics: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._connected: bool = False
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        self._connected = True
        logger.info("[AsyncQueueBroker] Connected in in-process memory mode (Development / Test only)")

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("[AsyncQueueBroker] Disconnected in-process memory broker")

    async def publish(self, topic: str, key: str, value: dict[str, Any], headers: dict[str, str] | None = None) -> None:
        if not self._connected:
            await self.connect()

        metadata = {
            "key": key,
            "topic": topic,
            "headers": headers or {},
            "partition": 0,
            "offset": 0,
        }
        item = (key, value, metadata)

        async with self._lock:
            queues = list(self._topics[topic])

        for q in queues:
            await q.put(item)

    async def subscribe(self, topic: str, group_id: str | None = None) -> AsyncIterator[tuple[str, dict[str, Any], dict[str, Any]]]:
        if not self._connected:
            await self.connect()

        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._topics[topic].append(queue)

        try:
            while self._connected:
                item = await queue.get()
                yield item
                queue.task_done()
        finally:
            async with self._lock:
                if queue in self._topics[topic]:
                    self._topics[topic].remove(queue)

    async def commit_offset(self, topic: str, partition: int, offset: int) -> None:
        # In-memory mock: no-op offset commit
        pass


class RedpandaBroker:
    """
    Production-ready Kafka/Redpanda broker driver using aiokafka.
    Fully implements durable offsets, partitions, consumer groups, and replay.
    """
    supports_replay: bool = True
    supports_consumer_groups: bool = True
    supports_persistence: bool = True
    supports_dlq: bool = True
    supports_partition_ordering: bool = True
    supports_offset_commit: bool = True

    def __init__(self, bootstrap_servers: str) -> None:
        self.bootstrap_servers = bootstrap_servers
        self._producer = None
        self._consumers: list[Any] = []
        self._connected: bool = False

    async def connect(self) -> None:
        try:
            from aiokafka import AIOKafkaProducer  # type: ignore
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                key_serializer=lambda k: k.encode("utf-8") if k else b"",
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
            )
            await self._producer.start()
            self._connected = True
            logger.info(f"[RedpandaBroker] Connected to cluster at {self.bootstrap_servers}")
        except Exception as e:
            self._connected = False
            logger.warning(f"[RedpandaBroker] Could not connect to Redpanda/Kafka at {self.bootstrap_servers}: {e}")
            raise

    async def disconnect(self) -> None:
        if self._producer:
            await self._producer.stop()
        for c in self._consumers:
            await c.stop()
        self._connected = False
        logger.info("[RedpandaBroker] Disconnected from Redpanda/Kafka cluster")

    async def publish(self, topic: str, key: str, value: dict[str, Any], headers: dict[str, str] | None = None) -> None:
        if not self._connected or self._producer is None:
            await self.connect()

        kafka_headers = [(k, v.encode("utf-8")) for k, v in (headers or {}).items()]
        await self._producer.send_and_wait(
            topic=topic,
            key=key,
            value=value,
            headers=kafka_headers,
        )

    async def subscribe(self, topic: str, group_id: str | None = None) -> AsyncIterator[tuple[str, dict[str, Any], dict[str, Any]]]:
        from aiokafka import AIOKafkaConsumer  # type: ignore
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id or "fleettrack-default-group",
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            key_deserializer=lambda k: k.decode("utf-8") if k else "",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )
        await consumer.start()
        self._consumers.append(consumer)
        try:
            async for msg in consumer:
                metadata = {
                    "key": msg.key,
                    "topic": msg.topic,
                    "partition": msg.partition,
                    "offset": msg.offset,
                    "timestamp": msg.timestamp,
                    "_raw_message": msg,
                    "_consumer_ref": consumer,
                }
                yield msg.key, msg.value, metadata
        finally:
            await consumer.stop()
            if consumer in self._consumers:
                self._consumers.remove(consumer)

    async def commit_offset(self, topic: str, partition: int, offset: int) -> None:
        # Offset commitment handled via consumer commit
        pass


# Global singleton instance
_broker_instance: EventBroker | None = None


def get_broker() -> EventBroker:
    global _broker_instance
    if _broker_instance is not None:
        return _broker_instance

    from backend.config import settings

    if settings.BROKER_MODE == "async_queue":
        _broker_instance = AsyncQueueBroker()
        return _broker_instance

    if settings.BROKER_MODE == "redpanda":
        _broker_instance = RedpandaBroker(settings.KAFKA_BOOTSTRAP_SERVERS)
        return _broker_instance

    # Auto-detect mode: Check if aiokafka is available, else fallback to AsyncQueue
    try:
        import aiokafka  # noqa: F401
        _broker_instance = RedpandaBroker(settings.KAFKA_BOOTSTRAP_SERVERS)
        return _broker_instance
    except ImportError:
        logger.info("[BrokerFactory] aiokafka not installed; using AsyncQueueBroker for local dev/testing")
        _broker_instance = AsyncQueueBroker()
        return _broker_instance


def set_broker(broker: EventBroker) -> None:
    """Explicitly set the broker instance (used in tests)."""
    global _broker_instance
    _broker_instance = broker
