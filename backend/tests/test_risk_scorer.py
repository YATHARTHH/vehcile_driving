from backend.telematics.risk_scorer import CalibratedRiskScorer


def test_calibrated_risk_scorer_segmented_baselines():
    scorer = CalibratedRiskScorer()

    # Telemetry representing high braking on a route (0.60 brake events / km)
    sample_features = {
        "brake_events": 12.0,
        "distance_km": 20.0,  # 0.60 brake events/km
        "speeding_seconds": 15.0,
        "trip_duration_seconds": 600.0,
        "high_rpm_seconds": 10.0,
        "throttle_std": 10.0,
    }

    # In a passenger EV, 0.60 brake rate is highly aggressive (P95 is 0.20 due to regen braking)
    ev_score = scorer.calculate_risk_score(
        sample_features, vehicle_class="passenger_ev", powertrain="bev"
    )

    # In a heavy diesel freight truck, 0.60 brake rate is well within normal operations (P95 is 0.85)
    truck_score = scorer.calculate_risk_score(
        sample_features, vehicle_class="heavy_truck", powertrain="ice_diesel"
    )

    assert ev_score["risk_score"] > truck_score["risk_score"], (
        "EV risk score should be higher than heavy truck for identical brake rate due to segmented baselines"
    )
    assert 0.0 <= ev_score["risk_score"] <= 100.0
    assert 0.0 <= truck_score["risk_score"] <= 100.0
    assert ev_score["segment_id"] == "passenger_ev:bev"
    assert truck_score["segment_id"] == "heavy_truck:ice_diesel"
