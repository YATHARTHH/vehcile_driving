"""
FleetTrack Simulation Package
Scenario-driven workload and reliability test harness.
"""

from backend.simulation.assertions import ScenarioAssertions
from backend.simulation.metrics import SimulationMetrics
from backend.simulation.physics import VehicleKinematics, VehiclePhysicsModel
from backend.simulation.pipeline_waiter import PipelineWaiter
from backend.simulation.runner import ScenarioRunner
from backend.simulation.scenarios import SCENARIO_REGISTRY, ScenarioConfig, ScenarioType
from backend.simulation.vehicle import VehicleSimulator

__all__ = [
    "SCENARIO_REGISTRY",
    "PipelineWaiter",
    "ScenarioAssertions",
    "ScenarioConfig",
    "ScenarioRunner",
    "ScenarioType",
    "SimulationMetrics",
    "VehicleKinematics",
    "VehiclePhysicsModel",
    "VehicleSimulator",
]
