from __future__ import annotations

from pathlib import Path

from mtnsim.schemas.project import ProjectManifest
from mtnsim.schemas.results import RunResultSummary
from mtnsim.schemas.scenario import ScenarioConfig
from mtnsim.services.calibration_service import CalibrationService
from mtnsim.services.compare_service import CompareService
from mtnsim.services.run_service import RunService


class SimulationAPI:
    def __init__(self, run_service: RunService | None = None, compare_service: CompareService | None = None, calibration_service: CalibrationService | None = None) -> None:
        self.run_service = run_service or RunService()
        self.compare_service = compare_service or CompareService()
        self.calibration_service = calibration_service or CalibrationService()

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

    def calibrate_run(
        self,
        result_summary: RunResultSummary,
        measurement_file: str | Path,
        measurement_metadata_file: str | Path | None = None,
        time_step_seconds: float = 1.0,
        auto_time_sync: bool = False,
        max_time_offset_steps: int = 5,
        outlier_error_threshold_db: float | None = None,
        min_alignment_samples: int = 3,
    ) -> dict:
        summary, output_path = self.calibration_service.calibrate_and_store(
            result_summary,
            measurement_file,
            measurement_metadata_file=measurement_metadata_file,
            time_step_seconds=time_step_seconds,
            auto_time_sync=auto_time_sync,
            max_time_offset_steps=max_time_offset_steps,
            outlier_error_threshold_db=outlier_error_threshold_db,
            min_alignment_samples=min_alignment_samples,
        )
        return {'calibration_summary': summary.to_dict(), 'calibration_summary_file': str(output_path)}
