import asyncio
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Protocol

from pydantic import BaseModel, ConfigDict, Field

from backend.config import settings

logger = logging.getLogger("fleettrack.streaming.hot_state")


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class VehicleLiveState(BaseModel):
    """
    Disposable real-time vehicle hot state projection.
    Maintains low-latency latest snapshot in memory/Redis with monotonic state_version.
    """
    model_config = ConfigDict(extra="ignore")

    tenant_id: str
    vehicle_id: str
    state_version: int = Field(default=1, description="Monotonically incrementing sequence version")
    event_timestamp: datetime
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Kinematics & Physical Readings
    speed_kmph: float
    rpm: float

    # Disambiguated Fuel Semantics
    fuel_level_pct: float | None = None
    fuel_rate_lph: float | None = None
    fuel_consumed_total_l: float | None = None

    # Spatial Location & Heading
    lat: float | None = None
    lon: float | None = None
    heading: float | None = None

    # Upstream Scored / Lineage Metadata (Read-only projection, no scoring computation here)
    driving_score: float | None = None
    active_alerts: list[dict[str, Any]] = Field(default_factory=list)
    highest_alert_severity: AlertSeverity | None = None


class HotStateManager(Protocol):
    """Protocol governing hot state cache snapshots and ephemeral real-time pub/sub notifications."""

    async def connect(self) -> None:
        """Initializes backend connection or resource allocation."""
        ...

    async def disconnect(self) -> None:
        """Disposes connections and clears subscriptions."""
        ...

    async def set_vehicle_state(self, state: VehicleLiveState, ttl_seconds: int = 3600) -> None:
        """Saves latest vehicle state snapshot."""
        ...

    async def get_vehicle_state(self, tenant_id: str, vehicle_id: str) -> VehicleLiveState | None:
        """Retrieves instantaneous snapshot for a single vehicle."""
        ...

    async def get_tenant_vehicle_states(self, tenant_id: str) -> list[VehicleLiveState]:
        """Retrieves instantaneous snapshots for all active vehicles in a tenant."""
        ...

    async def publish_state_update(self, state: VehicleLiveState) -> None:
        """Publishes downsampled vehicle state frame to vehicle channel."""
        ...

    async def publish_fleet_notification(
        self, tenant_id: str, vehicle_id: str, state_version: int, updated_at: str
    ) -> None:
        """Publishes lightweight notification to tenant fleet broadcast channel."""
        ...

    async def subscribe_channel(self, channel: str) -> AsyncGenerator[dict[str, Any], None]:
        """Yields deserialized messages from a subscribed channel."""
        ...


class RedisHotStateManager:
    """
    Production-grade distributed Redis hot state manager and pub/sub broadcaster.
    Coordinates state across multiple FastAPI/WebSocket gateway instances.
    """

    def __init__(self, redis_url: str = settings.REDIS_URL) -> None:
        self.redis_url = redis_url
        self._redis: Any | None = None

    async def connect(self) -> None:
        import redis.asyncio as aioredis
        self._redis = aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await self._redis.ping()
        logger.info(f"[HotState] Connected to Redis at {self.redis_url}")

    async def disconnect(self) -> None:
        if self._redis:
            await self._redis.aclose()
            self._redis = None
            logger.info("[HotState] Disconnected from Redis")

    def _state_key(self, tenant_id: str, vehicle_id: str) -> str:
        return f"fleet:state:{tenant_id}:{vehicle_id}"

    def _vehicle_channel(self, tenant_id: str, vehicle_id: str) -> str:
        return f"fleet:channel:{tenant_id}:{vehicle_id}"

    def _tenant_broadcast_channel(self, tenant_id: str) -> str:
        return f"fleet:channel:{tenant_id}:all"

    async def set_vehicle_state(self, state: VehicleLiveState, ttl_seconds: int = 3600) -> None:
        if not self._redis:
            raise RuntimeError("RedisHotStateManager is not connected.")
        key = self._state_key(state.tenant_id, state.vehicle_id)
        payload = state.model_dump_json()
        await self._redis.set(key, payload, ex=ttl_seconds)

    async def get_vehicle_state(self, tenant_id: str, vehicle_id: str) -> VehicleLiveState | None:
        if not self._redis:
            raise RuntimeError("RedisHotStateManager is not connected.")
        key = self._state_key(tenant_id, vehicle_id)
        raw = await self._redis.get(key)
        if not raw:
            return None
        try:
            return VehicleLiveState.model_validate_json(raw)
        except Exception as e:
            logger.error(f"[HotState] Failed to deserialize state for {key}: {e}")
            return None

    async def get_tenant_vehicle_states(self, tenant_id: str) -> list[VehicleLiveState]:
        if not self._redis:
            raise RuntimeError("RedisHotStateManager is not connected.")
        pattern = f"fleet:state:{tenant_id}:*"
        keys = []
        async for k in self._redis.scan_iter(match=pattern):
            keys.append(k)
        if not keys:
            return []
        raw_items = await self._redis.mget(keys)
        results = []
        for raw in raw_items:
            if raw:
                try:
                    results.append(VehicleLiveState.model_validate_json(raw))
                except Exception:
                    pass
        return results

    async def publish_state_update(self, state: VehicleLiveState) -> None:
        if not self._redis:
            raise RuntimeError("RedisHotStateManager is not connected.")
        channel = self._vehicle_channel(state.tenant_id, state.vehicle_id)
        payload = state.model_dump_json()
        await self._redis.publish(channel, payload)

    async def publish_fleet_notification(
        self, tenant_id: str, vehicle_id: str, state_version: int, updated_at: str
    ) -> None:
        if not self._redis:
            raise RuntimeError("RedisHotStateManager is not connected.")
        channel = self._tenant_broadcast_channel(tenant_id)
        payload = json.dumps({
            "type": "vehicle_state_updated",
            "tenant_id": tenant_id,
            "vehicle_id": vehicle_id,
            "state_version": state_version,
            "updated_at": updated_at,
        })
        await self._redis.publish(channel, payload)

    async def subscribe_channel(self, channel: str) -> AsyncGenerator[dict[str, Any], None]:
        if not self._redis:
            raise RuntimeError("RedisHotStateManager is not connected.")
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    raw_data = msg["data"]
                    try:
                        yield json.loads(raw_data)
                    except Exception:
                        yield {"raw": raw_data}
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()


class MemoryHotStateManager:
    """
    Single-process, in-memory hot state manager and pub/sub broadcaster.
    Engineered for 100% local development and unit tests without external services.
    Note: Not intended for distributed multi-process production scaling.
    """

    def __init__(self) -> None:
        self._states: dict[tuple[str, str], VehicleLiveState] = {}
        self._subscribers: dict[str, set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        logger.info("[HotState] Initialized in-memory HotStateManager (local/test mode)")

    async def disconnect(self) -> None:
        async with self._lock:
            self._states.clear()
            self._subscribers.clear()
        logger.info("[HotState] Disconnected in-memory HotStateManager")

    def _state_key(self, tenant_id: str, vehicle_id: str) -> tuple[str, str]:
        return (tenant_id, vehicle_id)

    def _vehicle_channel(self, tenant_id: str, vehicle_id: str) -> str:
        return f"fleet:channel:{tenant_id}:{vehicle_id}"

    def _tenant_broadcast_channel(self, tenant_id: str) -> str:
        return f"fleet:channel:{tenant_id}:all"

    async def set_vehicle_state(self, state: VehicleLiveState, ttl_seconds: int = 3600) -> None:
        async with self._lock:
            self._states[self._state_key(state.tenant_id, state.vehicle_id)] = state

    async def get_vehicle_state(self, tenant_id: str, vehicle_id: str) -> VehicleLiveState | None:
        async with self._lock:
            return self._states.get(self._state_key(tenant_id, vehicle_id))

    async def get_tenant_vehicle_states(self, tenant_id: str) -> list[VehicleLiveState]:
        async with self._lock:
            return [s for (t, _), s in self._states.items() if t == tenant_id]

    async def publish_state_update(self, state: VehicleLiveState) -> None:
        channel = self._vehicle_channel(state.tenant_id, state.vehicle_id)
        payload = state.model_dump(mode="json")
        await self._dispatch(channel, payload)

    async def publish_fleet_notification(
        self, tenant_id: str, vehicle_id: str, state_version: int, updated_at: str
    ) -> None:
        channel = self._tenant_broadcast_channel(tenant_id)
        payload = {
            "type": "vehicle_state_updated",
            "tenant_id": tenant_id,
            "vehicle_id": vehicle_id,
            "state_version": state_version,
            "updated_at": updated_at,
        }
        await self._dispatch(channel, payload)

    async def _dispatch(self, channel: str, message: dict[str, Any]) -> None:
        async with self._lock:
            queues = list(self._subscribers.get(channel, set()))
        for q in queues:
            await q.put(message)

    async def subscribe_channel(self, channel: str) -> AsyncGenerator[dict[str, Any], None]:
        q: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            if channel not in self._subscribers:
                self._subscribers[channel] = set()
            self._subscribers[channel].add(q)
        try:
            while True:
                msg = await q.get()
                yield msg
        finally:
            async with self._lock:
                if channel in self._subscribers and q in self._subscribers[channel]:
                    self._subscribers[channel].remove(q)
                    if not self._subscribers[channel]:
                        del self._subscribers[channel]


_GLOBAL_HOT_STATE_MANAGER: HotStateManager | None = None


async def get_hot_state_manager() -> HotStateManager:
    """
    Factory resolving active HotStateManager according to settings.HOT_STATE_BACKEND.
    - 'redis': Strictly requires Redis connection.
    - 'memory': Explicit in-memory backend for local testing.
    - 'auto': Attempts Redis ping with short timeout; falls back gracefully to in-memory.
    """
    global _GLOBAL_HOT_STATE_MANAGER
    if _GLOBAL_HOT_STATE_MANAGER is not None:
        return _GLOBAL_HOT_STATE_MANAGER

    mode = settings.HOT_STATE_BACKEND.lower()

    if mode == "redis":
        manager = RedisHotStateManager()
        await manager.connect()
        _GLOBAL_HOT_STATE_MANAGER = manager
        return manager

    elif mode == "memory":
        manager = MemoryHotStateManager()
        await manager.connect()
        _GLOBAL_HOT_STATE_MANAGER = manager
        return manager

    else:  # "auto"
        try:
            manager = RedisHotStateManager()
            # Fast ping with 0.5s timeout
            await asyncio.wait_for(manager.connect(), timeout=0.5)
            _GLOBAL_HOT_STATE_MANAGER = manager
            return manager
        except Exception as e:
            logger.warning(f"[HotState] Redis connection failed in 'auto' mode ({e}). Falling back to in-memory broker.")
            mem_manager = MemoryHotStateManager()
            await mem_manager.connect()
            _GLOBAL_HOT_STATE_MANAGER = mem_manager
            return mem_manager


def set_hot_state_manager(manager: HotStateManager | None) -> None:
    """Overrides global HotStateManager (e.g. for unit and integration testing)."""
    global _GLOBAL_HOT_STATE_MANAGER
    _GLOBAL_HOT_STATE_MANAGER = manager
