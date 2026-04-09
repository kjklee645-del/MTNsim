from __future__ import annotations

from pathlib import Path

from mtnsim.services.compare_service import CompareService
from mtnsim.schemas.results import ScenarioComparison
from mtnsim.schemas.scenario import ScenarioConfig


class CompareController:
    def __init__(self, compare_service: CompareService | None = None) -> None:
        self.compare_service = compare_service or CompareService()

    def compare_scenarios(self, scenario_a: ScenarioConfig, scenario_b: ScenarioConfig) -> ScenarioComparison:
        return self.compare_service.compare_scenarios(scenario_a, scenario_b)

    def load_and_compare(self, project_controller, scenario_path_a: str | Path, scenario_path_b: str | Path) -> ScenarioComparison:
        scenario_a = project_controller.load_scenario(scenario_path_a)
        scenario_b = project_controller.load_scenario(scenario_path_b)
        return self.compare_scenarios(scenario_a, scenario_b)
