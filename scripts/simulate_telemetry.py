#!/usr/bin/env python3
"""
FleetTrack Live Telemetry & Reliability Simulator CLI
Executes declarative failure, burst, and edge network scenarios against FleetTrack
and audits terminal outcomes using the Conservation of Events equation.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import AsyncSessionLocal, Base, engine
from backend.simulation.runner import ScenarioRunner
from backend.simulation.scenarios import SCENARIO_REGISTRY, ScenarioConfig, ScenarioType
from backend.streaming.broker import get_broker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fleettrack.simulator_cli")


async def run_scenarios(
    scenario_keys: list[ScenarioType],
    vehicles_override: int | None = None,
    duration_override: float | None = None,
    frequency_override: float | None = None,
    target_url: str | None = None,
    lake_root: str = "./data/lake",
    output_json: str | None = None,
) -> int:
    """
    Initializes infrastructure, runs the specified scenarios, and produces audit verdicts.
    Returns exit code (0 for pass, 1 for fail).
    """
    # 1. Initialize DB schema
    os.makedirs("instance", exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Connect broker
    broker = get_broker()
    await broker.connect()

    runner = ScenarioRunner(broker=broker, lake_root=lake_root, target_url=target_url)

    overall_passed = True
    audit_results: dict[str, dict] = {}

    try:
        for st in scenario_keys:
            base_config = SCENARIO_REGISTRY[st]
            # Apply overrides if provided
            config = ScenarioConfig(
                scenario_type=base_config.scenario_type,
                name=base_config.name,
                description=base_config.description,
                vehicle_count=vehicles_override if vehicles_override is not None else base_config.vehicle_count,
                duration_seconds=duration_override if duration_override is not None else base_config.duration_seconds,
                send_frequency_hz=frequency_override if frequency_override is not None else base_config.send_frequency_hz,
                clock_drift_seconds=base_config.clock_drift_seconds,
                disconnect_after_seconds=base_config.disconnect_after_seconds,
                reconnect_after_seconds=base_config.reconnect_after_seconds,
                reconnect_mode=base_config.reconnect_mode,
                corruption_rate=base_config.corruption_rate,
                conflicting_duplicates_count=base_config.conflicting_duplicates_count,
                inject_db_dropout=base_config.inject_db_dropout,
            )

            print("\n================================================================================")
            print(f"   STARTING SCENARIO: {config.name.upper()} ({config.scenario_type.value})")
            print(f"   {config.description}")
            print(f"   Vehicles: {config.vehicle_count} | Duration: {config.duration_seconds}s | Freq: {config.send_frequency_hz} Hz")
            print("================================================================================")

            async with AsyncSessionLocal() as db_session:
                metrics, passed, violations = await runner.run_scenario(config, db_session=db_session)

            report = metrics.format_summary_report(config.name, config.duration_seconds)
            print(report)

            if not passed:
                overall_passed = False
                print(f"FAILED INVARIANTS FOR {config.name}:")
                for v in violations:
                    print(f"  [X] {v}")
            else:
                print("PASSED: All reliability and conservation invariants verified.")

            _is_conserved, audit = metrics.verify_conservation()
            audit_results[config.scenario_type.value] = {
                "name": config.name,
                "passed": passed,
                "violations": violations,
                "metrics": asdict(metrics),
                "audit": audit,
            }

        if output_json:
            out_p = Path(output_json)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as f:  # noqa: ASYNC230
                json.dump(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "all_passed": overall_passed,
                        "results": audit_results,
                    },
                    f,
                    indent=2,
                )
            print(f"\nAudit results written to {out_p.resolve()}")

    finally:
        await broker.disconnect()
        await engine.dispose()

    return 0 if overall_passed else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FleetTrack Telematics Scenario-Driven Workload & Reliability Simulator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    valid_scenarios = [s.value for s in ScenarioType]
    parser.add_argument(
        "--scenario",
        type=str,
        default="normal_city",
        choices=valid_scenarios + ["all"],
        help="Specific scenario to execute or 'all' to run all 8 scenarios sequentially.",
    )
    parser.add_argument("--vehicles", type=int, default=None, help="Override vehicle count")
    parser.add_argument("--duration", type=float, default=None, help="Override duration in seconds")
    parser.add_argument("--frequency", type=float, default=None, help="Override frequency in Hz")
    parser.add_argument("--target-url", type=str, default=None, help="External target URL (e.g. http://localhost:8000)")
    parser.add_argument("--lake-root", type=str, default="./data/lake", help="Path to Bronze Parquet/JSONL Lake root")
    parser.add_argument("--output-json", type=str, default=None, help="Save structured audit results to JSON file")

    args = parser.parse_args()

    if args.scenario == "all":
        selected = list(ScenarioType)
    else:
        selected = [ScenarioType(args.scenario)]

    exit_code = asyncio.run(
        run_scenarios(
            scenario_keys=selected,
            vehicles_override=args.vehicles,
            duration_override=args.duration,
            frequency_override=args.frequency,
            target_url=args.target_url,
            lake_root=args.lake_root,
            output_json=args.output_json,
        )
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
