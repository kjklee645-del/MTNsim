from __future__ import annotations

from mtnsim.schemas.project import ProjectManifest
from mtnsim.schemas.results import RunResultSummary
from mtnsim.schemas.scenario import ScenarioConfig
from mtnsim.services.compare_service import CompareService
from mtnsim.services.run_service import RunService


class SimulationAPI:
    def __init__(self, run_service: RunService | None = None, compare_service: CompareService | None = None) -> None:
        self.run_service = run_service or RunService()
        self.compare_service = compare_service or CompareService()

    def create_run_context(self, project: ProjectManifest, scenario: ScenarioConfig):
        return self.run_service.create_run_context(project, scenario)

    def summarize_run(self, project: ProjectManifest, scenario: ScenarioConfig) -> dict:
        context = self.create_run_context(project, scenario)
        return self.run_service.summarize(context).to_dict()

    def run(self, project: ProjectManifest, scenario: ScenarioConfig, use_gpu: bool = True):
        context = self.create_run_context(project, scenario)
        return self.run_service.run_simulation(context, use_gpu=use_gpu)

    def compare_scenarios(self, scenario_a: ScenarioConfig, scenario_b: ScenarioConfig) -> dict:
        return self.compare_service.compare_scenarios(scenario_a, scenario_b).to_dict()

    def compare_run_results(self, result_a: RunResultSummary, result_b: RunResultSummary) -> dict:
        return self.compare_service.compare_run_results(result_a, result_b).to_dict()
