from datetime import datetime, timedelta, timezone

from backend.streaming.watermark import PerVehicleWatermarkTracker


def test_per_vehicle_scoped_watermark_isolation():
    """P0-2: Verify Vehicle A clock skew does NOT corrupt watermark for Vehicle B."""
    tracker = PerVehicleWatermarkTracker(allowed_lateness_seconds=30.0)

    base_time = datetime(2026, 9, 11, 14, 0, 0, tzinfo=timezone.utc)
    # Vehicle A: clock is 10 minutes ahead
    clock_skew_time_a = base_time + timedelta(minutes=10)
    # Vehicle B: normal synchronized clock
    normal_time_b = base_time

    # Vehicle A transmits event at 14:10:00
    is_late_a, watermark_a = tracker.evaluate_lateness("tenant_1", "veh_A", clock_skew_time_a)
    assert is_late_a is False
    assert watermark_a == clock_skew_time_a - timedelta(seconds=30)

    # Vehicle B transmits normal event at 14:00:00
    # If watermark was global, this would be falsely marked LATE!
    is_late_b, watermark_b = tracker.evaluate_lateness("tenant_1", "veh_B", normal_time_b)
    assert is_late_b is False, "Vehicle B should NOT be late due to Vehicle A clock skew!"
    assert watermark_b == normal_time_b - timedelta(seconds=30)

    # Now send an actual late event for Vehicle B (60 seconds behind its own watermark)
    late_time_b = base_time - timedelta(seconds=60)
    is_late_b_2, _ = tracker.evaluate_lateness("tenant_1", "veh_B", late_time_b)
    assert is_late_b_2 is True


def test_watermark_state_ttl_eviction():
    """P1: Verify stale watermark entries inactive for > 24 hours are evicted."""
    tracker = PerVehicleWatermarkTracker(state_ttl_hours=24.0)

    t0 = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    tracker.evaluate_lateness("tenant_1", "veh_1", t0, now_utc=t0)
    tracker.evaluate_lateness("tenant_1", "veh_2", t0, now_utc=t0)
    assert tracker.get_tracked_vehicle_count() == 2

    # Advance time by 25 hours; update only veh_2
    t1 = t0 + timedelta(hours=25)
    tracker.evaluate_lateness("tenant_1", "veh_2", t1, now_utc=t1)

    # Evict inactive
    evicted_count = tracker.evict_stale_states(now_utc=t1)
    assert evicted_count == 1
    assert tracker.get_tracked_vehicle_count() == 1
