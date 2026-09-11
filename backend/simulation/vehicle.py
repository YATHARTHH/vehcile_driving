import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.simulation.physics import VehicleKinematics


class VehicleSimulator:
    """
    Stateful actor simulating an IoT edge dongle (CAN/OBD-II + GPS).
    Supports offline tunnel buffering, burst reconnections, configurable clock drift,
    and targeted failure injections (corruption, transient drops).
    """
    def __init__(
        self,
        vehicle_id: str,
        tenant_id: str = "tenant_fedex_in",
        fleet_id: str = "fleet_pune_north",
        vehicle_class: str = "passenger_car",
        powertrain: str = "ice_petrol",
        clock_drift_seconds: float = 0.0,
        start_lat: float = 18.5204,
        start_lon: float = 73.8567,
    ) -> None:
        self.vehicle_id = vehicle_id
        self.tenant_id = tenant_id
        self.fleet_id = fleet_id
        self.clock_drift = timedelta(seconds=clock_drift_seconds)
        self.kinematics = VehicleKinematics(
            vehicle_class=vehicle_class,
            powertrain=powertrain,
            lat=start_lat,
            lon=start_lon,
        )

        self.is_online: bool = True
        self._local_buffer: list[dict[str, Any]] = []
        self.sequence_number: int = 0

    @property
    def edge_buffer(self) -> list[dict[str, Any]]:
        """Access the buffered edge packets while offline."""
        return self._local_buffer

    def generate_packet(
        self,
        target_speed_kmph: float,
        current_wall_time: datetime | None = None,
        dt: float = 1.0,
        inject_corruption: bool = False,
        inject_transient_drop: bool = False,
        custom_event_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Advances kinematics and creates a RawIngressPayload telematics packet.
        """
        self.sequence_number += 1
        wall_time = current_wall_time or datetime.now(timezone.utc)
        # Apply vehicle-specific RTC clock drift
        effective_edge_timestamp = wall_time + self.clock_drift

        telemetry = self.kinematics.step(target_speed_kmph, dt=dt)

        if inject_corruption:
            # Physical boundary violation: negative RPM
            telemetry["rpm"] = -500.0

        if inject_transient_drop:
            # Transient missing reading
            telemetry["rpm"] = None

        event_id = custom_event_id or f"evt_{self.vehicle_id}_{self.sequence_number}_{uuid.uuid4().hex[:8]}"

        packet = {
            "event_id": event_id,
            "event_timestamp": effective_edge_timestamp.isoformat(),
            "schema_version": "v1.0.0",
            "telemetry": telemetry,
        }

        # If vehicle is offline (e.g. inside a tunnel), store in local edge FIFO buffer
        if not self.is_online:
            self._local_buffer.append(packet)

        return packet

    def disconnect_tunnel(self) -> None:
        """Simulates entering a tunnel/dead zone: switches edge to offline buffer mode."""
        self.is_online = False

    def reconnect(self, mode: str = "ordered") -> list[dict[str, Any]]:
        """
        Simulates exiting tunnel and restoring cellular link:
        - mode='ordered': FIFO chronological burst (1 -> 2 -> 3 -> 4)
        - mode='reverse': LIFO / out-of-order burst (4 -> 3 -> 2 -> 1)
        """
        self.is_online = True
        buffered_packets = list(self._local_buffer)
        self._local_buffer.clear()

        if mode == "reverse":
            buffered_packets.reverse()

        return buffered_packets

    def get_auth_headers(self) -> dict[str, str]:
        """Headers presenting edge device authentication credentials."""
        return {
            "x-device-id": self.vehicle_id,
            "x-tenant-id": self.tenant_id,
        }
