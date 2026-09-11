from enum import Enum
from typing import Any


class SensorQualityState(str, Enum):
    VALID = "VALID"
    MISSING_TRANSIENT = "MISSING_TRANSIENT"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID = "INVALID"


class DynamicSensorValidator:
    """
    Dynamic sensor validator driven by individual VehicleProfile.
    Purely tags data quality states without mutating or imputing raw values.
    P0-4 Guarantee: Validation and imputation are strictly decoupled.
    """
    DEFAULT_RANGES = {
        "speed_kmph": (0.0, 250.0),
        "rpm": (0.0, 9000.0),
        "throttle_pct": (0.0, 100.0),
        "brake_pressure_bar": (0.0, 150.0),
        "tire_pressure_psi": (15.0, 65.0),
        "engine_load_pct": (0.0, 100.0),
        "lat": (-90.0, 90.0),
        "lon": (-180.0, 180.0),
    }

    def __init__(self, vehicle_profile: dict[str, Any] | None = None) -> None:
        self.profile = vehicle_profile or {}
        self.supported_sensors = set(
            self.profile.get(
                "supported_sensors",
                list(self.DEFAULT_RANGES.keys()),
            )
        )
        self.sensor_ranges = self.profile.get("sensor_ranges", self.DEFAULT_RANGES)

    def evaluate_sensor(
        self, sensor: str, raw_value: Any
    ) -> tuple[Any, SensorQualityState, str | None]:
        """
        Evaluates a single sensor reading against vehicle profile boundaries.
        Returns: (raw_value, quality_state, invalid_reason)
        Does NOT alter raw_value.
        """
        # 1. Hardware Capability Check
        if sensor not in self.supported_sensors:
            return raw_value, SensorQualityState.UNSUPPORTED, None

        # 2. Transient Telemetry Drop
        if raw_value is None:
            return None, SensorQualityState.MISSING_TRANSIENT, None

        # 3. Numeric Type Coercion Check
        try:
            val_float = float(raw_value)
        except (ValueError, TypeError):
            return raw_value, SensorQualityState.INVALID, f"COERCION_FAILURE:cannot_cast_{type(raw_value).__name__}_to_float"

        # 4. Dynamic Physical Limits Check
        limits = self.sensor_ranges.get(sensor)
        if limits:
            min_val, max_val = limits
            if not (min_val <= val_float <= max_val):
                return val_float, SensorQualityState.INVALID, f"RANGE_VIOLATION:{sensor}={val_float}_outside_[{min_val},{max_val}]"

        return val_float, SensorQualityState.VALID, None

    def validate_packet(
        self, telemetry_dict: dict[str, Any]
    ) -> tuple[dict[str, SensorQualityState], list[str], bool]:
        """
        Validates an entire telemetry dictionary.
        Returns:
            - states: dict mapping sensor_name -> SensorQualityState
            - invalid_reasons: list of violated rule descriptions
            - is_acceptable: True if no critical sensor is INVALID
        """
        states: dict[str, SensorQualityState] = {}
        invalid_reasons: list[str] = []
        is_acceptable = True

        for sensor, value in telemetry_dict.items():
            _, state, reason = self.evaluate_sensor(sensor, value)
            states[sensor] = state
            if state == SensorQualityState.INVALID:
                is_acceptable = False
                if reason:
                    invalid_reasons.append(reason)

        return states, invalid_reasons, is_acceptable
