from __future__ import annotations

from pathlib import Path

from mtnsim.api.project_api import ProjectAPI
from mtnsim.api.simulation_api import SimulationAPI


class AppRunner:
    def __init__(self) -> None:
        self.project_api = ProjectAPI()
        self.simulation_api = SimulationAPI()

    def summarize_project(self, manifest_path: str | Path, scenario_path: str | Path) -> dict:
        project = self.project_api.load_manifest(manifest_path)
        scenario = self.project_api.load_scenario(scenario_path)
        return self.simulation_api.summarize_run(project, scenario)

    def run_project(self, manifest_path: str | Path, scenario_path: str | Path, use_gpu: bool = True):
        project = self.project_api.load_manifest(manifest_path)
        scenario = self.project_api.load_scenario(scenario_path)
        return self.simulation_api.run(project, scenario, use_gpu=use_gpu)

    def compare_projects(self, manifest_path: str | Path, scenario_a_path: str | Path, scenario_b_path: str | Path) -> dict:
        self.project_api.load_manifest(manifest_path)
        scenario_a = self.project_api.load_scenario(scenario_a_path)
        scenario_b = self.project_api.load_scenario(scenario_b_path)
        return self.simulation_api.compare_scenarios(scenario_a, scenario_b)

    def compare_project_runs(self, manifest_path: str | Path, scenario_a_path: str | Path, scenario_b_path: str | Path, use_gpu: bool = True) -> dict:
        project = self.project_api.load_manifest(manifest_path)
        scenario_a = self.project_api.load_scenario(scenario_a_path)
        scenario_b = self.project_api.load_scenario(scenario_b_path)
        artifacts_a = self.simulation_api.run(project, scenario_a, use_gpu=use_gpu)
        artifacts_b = self.simulation_api.run(project, scenario_b, use_gpu=use_gpu)
        comparison = self.simulation_api.compare_run_results(artifacts_a.result_summary, artifacts_b.result_summary)
        return {
            'artifacts_a': {
                'run_id': artifacts_a.run_id,
                'result_summary_file': str(artifacts_a.result_summary_file),
            },
            'artifacts_b': {
                'run_id': artifacts_b.run_id,
                'result_summary_file': str(artifacts_b.result_summary_file),
            },
            'comparison': comparison,
        }
