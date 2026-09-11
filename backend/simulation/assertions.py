from backend.simulation.metrics import SimulationMetrics
from backend.simulation.scenarios import ScenarioConfig, ScenarioType


class ScenarioAssertionError(Exception):
    """Raised when a scenario fails its expected reliability invariant."""


class ScenarioAssertions:
    """
    Evaluates scenario outcome invariants and produces pass/fail audit verdicts.
    """
    @classmethod
    def evaluate(cls, config: ScenarioConfig, metrics: SimulationMetrics) -> tuple[bool, list[str]]:
        """
        Validates all scenario invariants against observed metrics.
        Returns: (passed: bool, violations: list[str])
        """
        violations: list[str] = []

        # Invariant 0: Conservation of Events must hold across all scenarios
        is_conserved, audit = metrics.verify_conservation()
        if not is_conserved:
            violations.append(
                f"Conservation of Events breached! Ingress balance: {audit['ingress_balance']}, "
                f"Processing balance: {audit['processing_balance']}, Leak discrepancy: {audit['discrepancy']}"
            )

        # Invariant 1: Bronze Lake must preserve raw events with at-least-once semantics
        if not audit["bronze_preservation"]:
            violations.append(
                f"Bronze raw lake preservation failed! Expected >= {metrics.http_accepted}, but got {metrics.bronze_written}"
            )

        # Scenario-specific invariants
        st = config.scenario_type

        if st == ScenarioType.NORMAL_CITY:
            if metrics.http_not_accepted > 0:
                violations.append(f"Expected 0 HTTP rejections, got {metrics.http_not_accepted}")
            if metrics.canonical_valid != metrics.events_sent:
                violations.append(f"Expected {metrics.events_sent} valid events, got {metrics.canonical_valid}")
            if metrics.late_events > 0:
                violations.append(f"Expected 0 late events in baseline city driving, got {metrics.late_events}")
            if metrics.dlq_permanent > 0:
                violations.append(f"Expected 0 DLQ permanent failures, got {metrics.dlq_permanent}")

        elif st == ScenarioType.HIGHWAY_BURST:
            if metrics.http_accepted != metrics.events_sent:
                violations.append(f"Expected 100% acceptance in highway burst, got {metrics.http_accepted}/{metrics.events_sent}")
            if metrics.canonical_valid != metrics.events_sent:
                violations.append(f"Expected all burst events to be valid, got {metrics.canonical_valid}/{metrics.events_sent}")

        elif st == ScenarioType.ORDERED_BUFFERED_REPLAY:
            if metrics.canonical_valid != metrics.events_sent:
                violations.append(f"Expected all FIFO buffered packets to be persisted, got {metrics.canonical_valid}/{metrics.events_sent}")
            if metrics.dlq_permanent > 0:
                violations.append(f"Expected 0 DLQ records during FIFO replay, got {metrics.dlq_permanent}")

        elif st == ScenarioType.OUT_OF_ORDER_REPLAY:
            if metrics.canonical_valid != metrics.events_sent:
                violations.append(f"Expected all out-of-order packets to be accepted and stored, got {metrics.canonical_valid}/{metrics.events_sent}")
            # Reverse burst should trigger late-event flagging for packets older than watermark
            if metrics.late_events == 0 and metrics.events_sent > 10:
                violations.append("Expected late_events > 0 for reverse out-of-order burst!")

        elif st == ScenarioType.CLOCK_DRIFT:
            if metrics.canonical_valid != metrics.events_sent:
                violations.append(f"Expected all clock drift packets to be validly persisted, got {metrics.canonical_valid}/{metrics.events_sent}")

        elif st == ScenarioType.SENSOR_CORRUPTION:
            if metrics.dlq_permanent == 0:
                violations.append("Expected DLQ permanent failures from injected negative RPM, but got 0!")
            if metrics.canonical_valid + metrics.dlq_permanent != metrics.http_accepted:
                violations.append("Sum of canonical valid and DLQ permanent must equal accepted events!")

        elif st == ScenarioType.CONFLICTING_DUPLICATE:
            if metrics.duplicate_replays == 0 and metrics.dlq_conflict == 0:
                violations.append("Expected duplicate replays or DLQ conflicts to be recorded, got 0!")

        elif st == ScenarioType.TRANSIENT_INFRA_FAILURE:
            if metrics.unresolved_failures > 0:
                violations.append(f"Expected 0 unresolved permanent losses after transient retry, got {metrics.unresolved_failures}")

        passed = len(violations) == 0
        return passed, violations
