from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BaselineArtifact:
    """
    Versioned P95 baseline artifact calibrated from historical Gold Lake data.
    """
    baseline_version: str
    calculated_at: str
    segment_id: str
    sample_size_trips: int
    p95_metrics: dict[str, float]


class CalibratedRiskScorer:
    """
    Computes a dimensionless, calibrated driving risk index in [0, 100].
    Features are normalized against versioned, segmented P95 baselines
    to eliminate fleet-composition skew between commercial freight trucks and passenger cars.
    """
    DEFAULT_WEIGHTS = {
        "harsh_brake_rate": 0.35,
        "speeding_ratio": 0.30,
        "rpm_stress_ratio": 0.20,
        "throttle_variance": 0.15,
    }

    # Versioned baseline registry
    DEFAULT_SEGMENTS: dict[tuple[str, str], BaselineArtifact] = {
        ("passenger_car", "ice_petrol"): BaselineArtifact(
            baseline_version="v2026.09.1",
            calculated_at="2026-09-11T00:00:00Z",
            segment_id="passenger_car:ice_petrol",
            sample_size_trips=85400,
            p95_metrics={
                "p95_brake_rate_per_km": 0.45,
                "p95_speeding_ratio": 0.08,
                "p95_high_rpm_ratio": 0.05,
                "p95_throttle_std": 14.2,
            },
        ),
        ("heavy_truck", "ice_diesel"): BaselineArtifact(
            baseline_version="v2026.09.1",
            calculated_at="2026-09-11T00:00:00Z",
            segment_id="heavy_truck:ice_diesel",
            sample_size_trips=142050,
            p95_metrics={
                "p95_brake_rate_per_km": 0.85,
                "p95_speeding_ratio": 0.02,
                "p95_high_rpm_ratio": 0.12,
                "p95_throttle_std": 8.5,
            },
        ),
        ("passenger_ev", "bev"): BaselineArtifact(
            baseline_version="v2026.09.1",
            calculated_at="2026-09-11T00:00:00Z",
            segment_id="passenger_ev:bev",
            sample_size_trips=32100,
            p95_metrics={
                "p95_brake_rate_per_km": 0.20,  # Regenerative braking absorbs brake wear
                "p95_speeding_ratio": 0.06,
                "p95_high_rpm_ratio": 0.01,    # Single reduction gear
                "p95_throttle_std": 18.0,
            },
        ),
        ("light_commercial", "ice_diesel"): BaselineArtifact(
            baseline_version="v2026.09.1",
            calculated_at="2026-09-11T00:00:00Z",
            segment_id="light_commercial:ice_diesel",
            sample_size_trips=64200,
            p95_metrics={
                "p95_brake_rate_per_km": 0.60,
                "p95_speeding_ratio": 0.05,
                "p95_high_rpm_ratio": 0.08,
                "p95_throttle_std": 11.0,
            },
        ),
    }

    def __init__(
        self,
        custom_artifacts: dict[tuple[str, str], BaselineArtifact] | None = None,
        weights: dict[str, float] | None = None,
    ) -> None:
        self.artifacts = custom_artifacts or self.DEFAULT_SEGMENTS
        self.weights = weights or self.DEFAULT_WEIGHTS
        # Ensure weights sum to 1.0
        total_w = sum(self.weights.values())
        if abs(total_w - 1.0) > 1e-4:
            self.weights = {k: v / total_w for k, v in self.weights.items()}

    def get_baseline(self, vehicle_class: str, powertrain: str) -> BaselineArtifact:
        key = (vehicle_class, powertrain)
        if key in self.artifacts:
            return self.artifacts[key]
        # Fallback to standard passenger ICE
        return self.artifacts[("passenger_car", "ice_petrol")]

    def calculate_risk_score(
        self,
        features: dict[str, float],
        vehicle_class: str = "passenger_car",
        powertrain: str = "ice_petrol",
    ) -> dict[str, Any]:
        """
        Calculates calibrated risk index and sub-component contributions.
        Features expected:
            - brake_events: int / float
            - distance_km: float
            - speeding_seconds: float
            - trip_duration_seconds: float
            - high_rpm_seconds: float
            - throttle_std: float
        """
        artifact = self.get_baseline(vehicle_class, powertrain)
        p95 = artifact.p95_metrics

        distance = max(features.get("distance_km", 1.0), 0.1)
        duration = max(features.get("trip_duration_seconds", 1.0), 1.0)

        raw_brake_rate = features.get("brake_events", 0.0) / distance
        raw_speeding_ratio = features.get("speeding_seconds", 0.0) / duration
        raw_rpm_stress_ratio = features.get("high_rpm_seconds", 0.0) / duration
        raw_throttle_std = features.get("throttle_std", 0.0)

        # Dimensionless normalized sub-indices bounded in [0.0, 1.0]
        norm_brake = min(raw_brake_rate / max(p95["p95_brake_rate_per_km"], 1e-3), 1.0)
        norm_speeding = min(raw_speeding_ratio / max(p95["p95_speeding_ratio"], 1e-3), 1.0)
        norm_rpm = min(raw_rpm_stress_ratio / max(p95["p95_high_rpm_ratio"], 1e-3), 1.0)
        norm_throttle = min(raw_throttle_std / max(p95["p95_throttle_std"], 1e-3), 1.0)

        sub_scores = {
            "harsh_brake_rate": norm_brake,
            "speeding_ratio": norm_speeding,
            "rpm_stress_ratio": norm_rpm,
            "throttle_variance": norm_throttle,
        }

        composite_risk = sum(self.weights[k] * sub_scores[k] for k in self.weights) * 100.0

        return {
            "risk_score": round(composite_risk, 2),
            "normalized_sub_scores": {k: round(v, 4) for k, v in sub_scores.items()},
            "segment_id": artifact.segment_id,
            "baseline_version": artifact.baseline_version,
            "sample_size_trips": artifact.sample_size_trips,
        }
