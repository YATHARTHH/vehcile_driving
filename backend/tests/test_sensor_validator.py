from backend.telematics.sensor_validator import (
    DynamicSensorValidator,
    SensorQualityState,
)


def test_sensor_validator_valid_readings():
    validator = DynamicSensorValidator()
    raw_val, state, reason = validator.evaluate_sensor("rpm", 2200)
    assert state == SensorQualityState.VALID
    assert raw_val == 2200.0
    assert reason is None

    raw_val, state, reason = validator.evaluate_sensor("speed_kmph", 65.5)
    assert state == SensorQualityState.VALID
    assert raw_val == 65.5
    assert reason is None


def test_sensor_validator_missing_transient():
    validator = DynamicSensorValidator()
    raw_val, state, reason = validator.evaluate_sensor("rpm", None)
    assert state == SensorQualityState.MISSING_TRANSIENT
    assert raw_val is None
    assert reason is None


def test_sensor_validator_unsupported_sensor():
    custom_profile = {
        "supported_sensors": ["speed_kmph", "rpm"],
    }
    validator = DynamicSensorValidator(custom_profile)
    # brake_pressure_bar is not in supported_sensors
    raw_val, state, reason = validator.evaluate_sensor("brake_pressure_bar", 45.0)
    assert state == SensorQualityState.UNSUPPORTED
    assert raw_val == 45.0
    assert reason is None


def test_sensor_validator_invalid_out_of_bounds():
    validator = DynamicSensorValidator()
    # RPM < 0 (physically impossible)
    raw_val, state, reason = validator.evaluate_sensor("rpm", -500.0)
    assert state == SensorQualityState.INVALID
    assert raw_val == -500.0
    assert "RANGE_VIOLATION" in reason

    # RPM > 9000
    raw_val, state, reason = validator.evaluate_sensor("rpm", 15000.0)
    assert state == SensorQualityState.INVALID
    assert "RANGE_VIOLATION" in reason


def test_sensor_validator_invalid_type_coercion():
    validator = DynamicSensorValidator()
    raw_val, state, reason = validator.evaluate_sensor("speed_kmph", "not_a_number")
    assert state == SensorQualityState.INVALID
    assert raw_val == "not_a_number"
    assert "COERCION_FAILURE" in reason


def test_sensor_validator_non_mutation_guarantee():
    """P0-4: Verify validator does not mutate or impute raw sensor values."""
    validator = DynamicSensorValidator()
    packet = {
        "speed_kmph": 80.0,
        "rpm": None,
        "throttle_pct": -20.0,  # Invalid
    }
    states, reasons, is_acceptable = validator.validate_packet(packet)
    assert states["speed_kmph"] == SensorQualityState.VALID
    assert states["rpm"] == SensorQualityState.MISSING_TRANSIENT
    assert states["throttle_pct"] == SensorQualityState.INVALID
    assert is_acceptable is False
    assert len(reasons) == 1
    # Original packet untouched
    assert packet["rpm"] is None
    assert packet["throttle_pct"] == -20.0
