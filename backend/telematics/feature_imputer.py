from datetime import datetime
from typing import Any
from backend.telematics.sensor_validator import SensorQualityState


class FeatureImputer:
    """
    Decoupled Feature Engineering & Imputation Pipeline.
    Consumes raw readings and quality states, applying vehicle-specific baseline
    or bounded forward-fill policies and appending explicit missingness flags for ML models.
    """
    DEFAULT_BASELINES = {
        "speed_kmph": 0.0,
        "rpm": 800.0,  # Nominal idle RPM
        "throttle_pct": 0.0,
        "brake_pressure_bar": 0.0,
        "tire_pressure_psi": 32.0,
        "engine_load_pct": 20.0,
    }

    def __init__(self, vehicle_profile: dict[str, Any] | None = None) -> None:
        self.profile = vehicle_profile or {}
        self.baselines = self.profile.get("baselines", self.DEFAULT_BASELINES)
        # Recent state for bounded forward-fill: sensor -> (value, timestamp)
        self._last_readings: dict[str, tuple[float, datetime]] = {}
        self.max_forward_fill_seconds: float = 5.0

    def impute_sensor(
        self,
        sensor: str,
        raw_val: Any,
        quality_state: SensorQualityState,
        event_time: datetime
    ) -> tuple[float, float]:
        """
        Imputes a sensor reading for feature extraction based on its quality state.
        Returns: (imputed_value, missing_flag: 0.0 or 1.0)
        """
        # Case 1: Valid plausible reading
        if quality_state == SensorQualityState.VALID and raw_val is not None:
            val_float = float(raw_val)
            self._last_readings[sensor] = (val_float, event_time)
            return val_float, 0.0

        # Case 2: Transient missingness (attempt bounded forward-fill)
        if quality_state == SensorQualityState.MISSING_TRANSIENT:
            if sensor in self._last_readings:
                prev_val, prev_time = self._last_readings[sensor]
                if (event_time - prev_time).total_seconds() <= self.max_forward_fill_seconds:
                    return prev_val, 1.0  # Imputed, marked as missing originally

            # Forward-fill expired or unavailable: fallback to vehicle baseline
            baseline = self.baselines.get(sensor, self.DEFAULT_BASELINES.get(sensor, 0.0))
            return baseline, 1.0

        # Case 3: Unsupported sensor hardware on this vehicle
        if quality_state == SensorQualityState.UNSUPPORTED:
            baseline = self.baselines.get(sensor, self.DEFAULT_BASELINES.get(sensor, 0.0))
            return baseline, 1.0

        # Case 4: Invalid sensor reading (sensor short-circuit / physical impossibility)
        # Never forward-fill an invalid reading; use nominal baseline and flag as missing
        baseline = self.baselines.get(sensor, self.DEFAULT_BASELINES.get(sensor, 0.0))
        return baseline, 1.0

    def prepare_feature_vector(
        self,
        telemetry: dict[str, Any],
        quality_states: dict[str, SensorQualityState],
        event_time: datetime,
        feature_keys: list[str] | None = None
    ) -> tuple[dict[str, float], dict[str, float]]:
        """
        Prepares a complete numeric feature dict and corresponding missingness indicators.
        Returns: (imputed_features, missing_indicators)
        """
        keys = feature_keys or list(self.DEFAULT_BASELINES.keys())
        features: dict[str, float] = {}
        missing_flags: dict[str, float] = {}

        for key in keys:
            raw_val = telemetry.get(key)
            state = quality_states.get(key, SensorQualityState.VALID)
            imputed_val, is_missing = self.impute_sensor(key, raw_val, state, event_time)
            features[key] = imputed_val
            missing_flags[f"{key}_missing"] = is_missing

        return features, missing_flags
