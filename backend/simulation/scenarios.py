from dataclasses import dataclass
from enum import Enum


class ScenarioType(str, Enum):
    NORMAL_CITY = "normal_city"
    HIGHWAY_BURST = "highway_burst"
    ORDERED_BUFFERED_REPLAY = "ordered_buffered_replay"
    OUT_OF_ORDER_REPLAY = "out_of_order_replay"
    CLOCK_DRIFT = "clock_drift"
    SENSOR_CORRUPTION = "sensor_corruption"
    CONFLICTING_DUPLICATE = "conflicting_duplicate"
    TRANSIENT_INFRA_FAILURE = "transient_infra_failure"


@dataclass
class ScenarioConfig:
    """
    Configuration parameters for a declarative simulation scenario.
    """
    scenario_type: ScenarioType
    name: str
    description: str
    vehicle_count: int = 5
    duration_seconds: float = 10.0
    send_frequency_hz: float = 1.0
    clock_drift_seconds: float = 0.0
    disconnect_after_seconds: float | None = None
    reconnect_after_seconds: float | None = None
    reconnect_mode: str = "ordered"  # "ordered" or "reverse"
    corruption_rate: float = 0.0      # Probability of corrupting packet
    conflicting_duplicates_count: int = 0
    inject_db_dropout: bool = False


# Declarative registry of the 8 canonical scenarios
SCENARIO_REGISTRY: dict[ScenarioType, ScenarioConfig] = {
    ScenarioType.NORMAL_CITY: ScenarioConfig(
        scenario_type=ScenarioType.NORMAL_CITY,
        name="Normal City Driving",
        description="5 vehicles driving in urban stop-and-go traffic for 10s at 1 Hz.",
        vehicle_count=5,
        duration_seconds=10.0,
        send_frequency_hz=1.0,
    ),
    ScenarioType.HIGHWAY_BURST: ScenarioConfig(
        scenario_type=ScenarioType.HIGHWAY_BURST,
        name="Highway Cruise Burst",
        description="10 vehicles cruising on highway at 5 Hz to test throughput and consumer lag.",
        vehicle_count=10,
        duration_seconds=5.0,
        send_frequency_hz=5.0,
    ),
    ScenarioType.ORDERED_BUFFERED_REPLAY: ScenarioConfig(
        scenario_type=ScenarioType.ORDERED_BUFFERED_REPLAY,
        name="Tunnel Reconnect (FIFO Ordered Replay)",
        description="Vehicles disconnect, buffer in local edge memory, reconnect and burst in chronological order.",
        vehicle_count=3,
        duration_seconds=8.0,
        send_frequency_hz=1.0,
        disconnect_after_seconds=2.0,
        reconnect_after_seconds=6.0,
        reconnect_mode="ordered",
    ),
    ScenarioType.OUT_OF_ORDER_REPLAY: ScenarioConfig(
        scenario_type=ScenarioType.OUT_OF_ORDER_REPLAY,
        name="Tunnel Reconnect (Out-of-Order Replay)",
        description="Vehicles disconnect and on reconnect emit in reverse chronological order to test watermark logic.",
        vehicle_count=3,
        duration_seconds=8.0,
        send_frequency_hz=1.0,
        disconnect_after_seconds=2.0,
        reconnect_after_seconds=6.0,
        reconnect_mode="reverse",
    ),
    ScenarioType.CLOCK_DRIFT: ScenarioConfig(
        scenario_type=ScenarioType.CLOCK_DRIFT,
        name="Clock Drift (Scoped Watermark Isolation)",
        description="Vehicle 1 has +300s clock drift, Vehicle 2 has normal time; verifies per-vehicle isolation.",
        vehicle_count=2,
        duration_seconds=5.0,
        send_frequency_hz=1.0,
        clock_drift_seconds=300.0,  # 5 minutes ahead
    ),
    ScenarioType.SENSOR_CORRUPTION: ScenarioConfig(
        scenario_type=ScenarioType.SENSOR_CORRUPTION,
        name="Sensor Corruption (Permanent DLQ)",
        description="Injects negative RPM (-500) and impossible sensor ranges routed to telemetry.dlq.",
        vehicle_count=3,
        duration_seconds=5.0,
        send_frequency_hz=1.0,
        corruption_rate=0.4,
    ),
    ScenarioType.CONFLICTING_DUPLICATE: ScenarioConfig(
        scenario_type=ScenarioType.CONFLICTING_DUPLICATE,
        name="Conflicting Event ID (Idempotency Audit)",
        description="Reuses event ID with identical payload (benign replay) vs altered payload (conflict quarantine).",
        vehicle_count=2,
        duration_seconds=5.0,
        send_frequency_hz=1.0,
        conflicting_duplicates_count=5,
    ),
    ScenarioType.TRANSIENT_INFRA_FAILURE: ScenarioConfig(
        scenario_type=ScenarioType.TRANSIENT_INFRA_FAILURE,
        name="Transient Infrastructure Outage",
        description="Simulates temporary persistence failure; verifies TRANSIENT_FAILURE classification and retry.",
        vehicle_count=3,
        duration_seconds=5.0,
        send_frequency_hz=1.0,
        inject_db_dropout=True,
    ),
}
