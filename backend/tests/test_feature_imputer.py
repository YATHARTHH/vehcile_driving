from datetime import datetime, timedelta, timezone

from backend.telematics.feature_imputer import FeatureImputer
from backend.telematics.sensor_validator import SensorQualityState


def test_feature_imputer_forward_fill_and_indicators():
    """
    Test FeatureImputer:
    1. Bounded forward-fill when delta_t <= 5s for MISSING_TRANSIENT readings.
    2. Fallback to vehicle baseline when forward-fill expires (> 5s).
    3. Proper missingness indicator flags (0.0 for valid, 1.0 for imputed/missing).
    """
    imputer = FeatureImputer()
    t0 = datetime(2026, 9, 11, 14, 0, 0, tzinfo=timezone.utc)

    # Reading 1: Valid speed at t0 (65.0 kmph)
    val1, is_miss1 = imputer.impute_sensor("speed_kmph", 65.0, SensorQualityState.VALID, t0)
    assert val1 == 65.0
    assert is_miss1 == 0.0

    # Reading 2: Transient drop at t0 + 2s (within 5s limit) -> should forward-fill previous 65.0
    t1 = t0 + timedelta(seconds=2)
    val2, is_miss2 = imputer.impute_sensor("speed_kmph", None, SensorQualityState.MISSING_TRANSIENT, t1)
    assert val2 == 65.0
    assert is_miss2 == 1.0  # Flagged as missing/imputed for ML

    # Reading 3: Transient drop at t0 + 10s (exceeds 5s forward-fill limit) -> should fallback to baseline (0.0)
    t2 = t0 + timedelta(seconds=10)
    val3, is_miss3 = imputer.impute_sensor("speed_kmph", None, SensorQualityState.MISSING_TRANSIENT, t2)
    assert val3 == 0.0  # Default baseline for speed
    assert is_miss3 == 1.0


def test_feature_imputer_unsupported_hardware_baseline():
    """Verify unsupported sensor receives nominal baseline and is flagged missing."""
    custom_profile = {
        "baselines": {"brake_pressure_bar": 0.0, "rpm": 750.0}
    }
    imputer = FeatureImputer(vehicle_profile=custom_profile)
    t0 = datetime(2026, 9, 11, 14, 0, 0, tzinfo=timezone.utc)

    val, is_miss = imputer.impute_sensor("brake_pressure_bar", 20.0, SensorQualityState.UNSUPPORTED, t0)
    assert val == 0.0
    assert is_miss == 1.0
