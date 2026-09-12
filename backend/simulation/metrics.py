import statistics
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SimulationMetrics:
    """
    Tracks terminal-outcome event conservation and pipeline performance metrics.
    Enforces the Conservation of Events equation:
        events_sent = http_not_accepted + accepted_for_processing
        accepted_for_processing = canonical_valid + duplicate_replay + dlq_permanent + dlq_conflict + dlq_manual_review + unresolved_failures
        bronze_records >= accepted_for_processing (independent at-least-once raw preservation)
    """
    events_generated: int = 0
    events_sent: int = 0
    http_accepted: int = 0
    http_not_accepted: int = 0
    latencies_ms: list[float] = field(default_factory=list)

    # Bronze Lake
    bronze_written: int = 0

    # Downstream Processing Terminal Outcomes
    canonical_valid: int = 0
    on_time_events: int = 0
    late_events: int = 0
    duplicate_replays: int = 0
    dlq_permanent: int = 0
    dlq_transient: int = 0
    dlq_conflict: int = 0
    dlq_manual_review: int = 0
    unresolved_failures: int = 0

    def record_http_response(self, status_code: int, latency_ms: float) -> None:
        self.events_sent += 1
        self.latencies_ms.append(latency_ms)
        if status_code in (200, 201, 202):
            self.http_accepted += 1
        else:
            self.http_not_accepted += 1

    def verify_conservation(self) -> tuple[bool, dict[str, Any]]:
        """
        Verifies mathematical conservation of events.
        """
        accepted_for_processing = self.http_accepted
        total_accounted_outcomes = (
            self.canonical_valid
            + self.duplicate_replays
            + self.dlq_permanent
            + self.dlq_conflict
            + self.dlq_manual_review
            + self.unresolved_failures
        )

        ingress_balance = (self.events_sent == self.http_not_accepted + accepted_for_processing)
        processing_balance = (accepted_for_processing == total_accounted_outcomes)
        bronze_preservation = (self.bronze_written >= accepted_for_processing)

        is_conserved = ingress_balance and processing_balance

        audit = {
            "events_sent": self.events_sent,
            "http_accepted": self.http_accepted,
            "http_not_accepted": self.http_not_accepted,
            "total_accounted_outcomes": total_accounted_outcomes,
            "discrepancy": accepted_for_processing - total_accounted_outcomes,
            "ingress_balance": ingress_balance,
            "processing_balance": processing_balance,
            "bronze_preservation": bronze_preservation,
            "bronze_records": self.bronze_written,
        }

        return is_conserved, audit

    def format_summary_report(self, scenario_name: str, duration_sec: float) -> str:
        """Renders an audit report table."""
        is_conserved, audit = self.verify_conservation()
        avg_lat = round(statistics.mean(self.latencies_ms), 2) if self.latencies_ms else 0.0
        p95_lat = round(statistics.quantiles(self.latencies_ms, n=20)[18], 2) if len(self.latencies_ms) >= 20 else avg_lat
        throughput = round(self.events_sent / max(duration_sec, 0.1), 1)

        status_str = ">>> ALL CONSERVATION CHECKS PASSED <<<" if is_conserved else "!!! EVENT LEAK / DISCREPANCY DETECTED !!!"

        return f"""
================================================================================
                    FLEETTRACK SIMULATION AUDIT REPORT
================================================================================
Scenario:               {scenario_name}
Duration:               {duration_sec:.2f}s
Throughput:             {throughput} events/sec

[Ingestion Layer]
  Events Generated:     {self.events_generated:,}
  Events Sent:          {self.events_sent:,}
  HTTP 202 Accepted:    {self.http_accepted:,} ({(self.http_accepted / max(self.events_sent, 1)) * 100:.1f}%)
  HTTP Rejected:        {self.http_not_accepted:,}
  Avg Latency:          {avg_lat} ms (p95: {p95_lat} ms)

[Bronze Lake Layer]
  Bronze Records:       {self.bronze_written:,} (>= Accepted: {'PASS' if audit['bronze_preservation'] else 'FAIL'})

[Downstream Validation & Persistence Outcomes]
  Canonical Valid:      {self.canonical_valid:,}
    - On-Time Events:   {self.on_time_events:,}
    - Late Events:      {self.late_events:,}
  Duplicate Replays:    {self.duplicate_replays:,}
  DLQ Permanent:        {self.dlq_permanent:,}
  DLQ Conflict:         {self.dlq_conflict:,}
  DLQ Transient:        {self.dlq_transient:,}
  Unresolved Failures:  {self.unresolved_failures:,}

[Conservation of Events Check]
  Accepted for Process: {audit['http_accepted']:,}
  Accounted Outcomes:   {audit['total_accounted_outcomes']:,}
  Discrepancy (Leak):   {audit['discrepancy']:,}
  Audit Verdict:        {status_str}
================================================================================
"""
