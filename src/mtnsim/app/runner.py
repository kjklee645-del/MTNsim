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


    def calibrate_project_run(
        self,
        manifest_path: str | Path,
        scenario_path: str | Path,
        measurement_path: str | Path | None = None,
        measurement_metadata_path: str | Path | None = None,
        use_gpu: bool = True,
    ) -> dict:
        project = self.project_api.load_manifest(manifest_path)
        scenario = self.project_api.load_scenario(scenario_path)
        artifacts = self.simulation_api.run(project, scenario, use_gpu=use_gpu)
        target_measurement = Path(measurement_path) if measurement_path else Path(project.paths.measurements)
        if not target_measurement.is_absolute():
            target_measurement = Path(manifest_path).resolve().parent.parent / target_measurement
        target_metadata = Path(measurement_metadata_path) if measurement_metadata_path else self.simulation_api.calibration_service.resolve_default_metadata_path(project)
        calibration = self.simulation_api.calibrate_run(
            artifacts.result_summary,
            target_measurement,
            measurement_metadata_file=target_metadata,
            time_step_seconds=project.simulation_defaults.time_step_seconds,
        )
        return {
            'run_id': artifacts.run_id,
            'result_summary_file': str(artifacts.result_summary_file),
            'calibration': calibration,
        }

    def calibrate_existing_result(
        self,
        result_summary_path: str | Path,
        measurement_path: str | Path,
        measurement_metadata_path: str | Path | None = None,
        time_step_seconds: float = 1.0,
    ) -> dict:
        from mtnsim.schemas.results import RunResultSummary
        loaded = RunResultSummary.load(result_summary_path)
        return self.simulation_api.calibrate_run(
            loaded,
            measurement_path,
            measurement_metadata_file=measurement_metadata_path,
            time_step_seconds=time_step_seconds,
        )
