from __future__ import annotations

from pathlib import Path

from mtnsim.api.project_api import ProjectAPI
from mtnsim.api.simulation_api import SimulationAPI
from mtnsim.security.paths import resolve_campaign_path, resolve_project_path
from mtnsim.services.benchmark_service import BenchmarkService
from mtnsim.services.tuning_service import TuningService
from mtnsim.services.validation_service import ValidationService
from mtnsim.services.field_campaign_service import FieldCampaignService
from mtnsim.services.campaign_validation_service import CampaignValidationService
from mtnsim.services.field_campaign_comparison_service import FieldCampaignComparisonService


class AppRunner:
    def __init__(self) -> None:
        self.project_api = ProjectAPI()
        self.simulation_api = SimulationAPI()
        self.benchmark_service = BenchmarkService()
        self.tuning_service = TuningService(self.benchmark_service)
        self.validation_service = ValidationService()
        self.field_campaign_service = FieldCampaignService()
        self.campaign_validation_service = CampaignValidationService(self.field_campaign_service, self.simulation_api.run_service, self.simulation_api.calibration_service)
        self.field_campaign_comparison_service = FieldCampaignComparisonService(self.campaign_validation_service)

    def summarize_project(self, manifest_path: str | Path, scenario_path: str | Path) -> dict:
        project = self.project_api.load_manifest(manifest_path)
        scenario = self.project_api.load_scenario(self._resolve_project_scenario_path(project, scenario_path))
        return self.simulation_api.summarize_run(project, scenario)

    def run_project(self, manifest_path: str | Path, scenario_path: str | Path, use_gpu: bool = True):
        project = self.project_api.load_manifest(manifest_path)
        scenario = self.project_api.load_scenario(self._resolve_project_scenario_path(project, scenario_path))
        return self.simulation_api.run(project, scenario, use_gpu=use_gpu)

    def compare_projects(self, manifest_path: str | Path, scenario_a_path: str | Path, scenario_b_path: str | Path) -> dict:
        project = self.project_api.load_manifest(manifest_path)
        scenario_a = self.project_api.load_scenario(self._resolve_project_scenario_path(project, scenario_a_path))
        scenario_b = self.project_api.load_scenario(self._resolve_project_scenario_path(project, scenario_b_path))
        return self.simulation_api.compare_scenarios(scenario_a, scenario_b)

    def compare_project_runs(self, manifest_path: str | Path, scenario_a_path: str | Path, scenario_b_path: str | Path, use_gpu: bool = True) -> dict:
        project = self.project_api.load_manifest(manifest_path)
        scenario_a = self.project_api.load_scenario(self._resolve_project_scenario_path(project, scenario_a_path))
        scenario_b = self.project_api.load_scenario(self._resolve_project_scenario_path(project, scenario_b_path))
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
        auto_time_sync: bool = False,
        max_time_offset_steps: int = 5,
        outlier_error_threshold_db: float | None = None,
        min_alignment_samples: int = 3,
    ) -> dict:
        project = self.project_api.load_manifest(manifest_path)
        scenario = self.project_api.load_scenario(self._resolve_project_scenario_path(project, scenario_path))
        artifacts = self.simulation_api.run(project, scenario, use_gpu=use_gpu)
        target_measurement = (
            resolve_project_path(project, measurement_path, label='calibration measurement path', expected_kind='file')
            if measurement_path else
            resolve_project_path(project, project.paths.measurements, label='project.paths.measurements', expected_kind='file')
        )
        target_metadata = (
            resolve_project_path(project, measurement_metadata_path, label='calibration measurement metadata path', expected_kind='file')
            if measurement_metadata_path else
            self.simulation_api.calibration_service.resolve_default_metadata_path(project)
        )
        if target_measurement is None:
            raise ValueError('A measurement file is required for calibration.')
        calibration = self.simulation_api.calibrate_run(
            artifacts.result_summary,
            target_measurement,
            measurement_metadata_file=target_metadata,
            time_step_seconds=project.simulation_defaults.time_step_seconds,
            auto_time_sync=auto_time_sync,
            max_time_offset_steps=max_time_offset_steps,
            outlier_error_threshold_db=outlier_error_threshold_db,
            min_alignment_samples=min_alignment_samples,
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
        auto_time_sync: bool = False,
        max_time_offset_steps: int = 5,
        outlier_error_threshold_db: float | None = None,
        min_alignment_samples: int = 3,
    ) -> dict:
        from mtnsim.schemas.results import RunResultSummary
        loaded = RunResultSummary.load(result_summary_path)
        return self.simulation_api.calibrate_run(
            loaded,
            measurement_path,
            measurement_metadata_file=measurement_metadata_path,
            time_step_seconds=time_step_seconds,
            auto_time_sync=auto_time_sync,
            max_time_offset_steps=max_time_offset_steps,
            outlier_error_threshold_db=outlier_error_threshold_db,
            min_alignment_samples=min_alignment_samples,
        )

    def run_propagation_benchmarks(self, benchmark_file: str | Path) -> dict:
        return self.benchmark_service.run_propagation_benchmarks(benchmark_file).to_dict()

    def tune_propagation(self, benchmark_file: str | Path, tuning_file: str | Path) -> dict:
        return self.tuning_service.tune_propagation(benchmark_file, tuning_file).to_dict()

    def run_validation_suite(self, manifest_path: str | Path, validation_file: str | Path, use_gpu: bool = False) -> dict:
        project = self.project_api.load_manifest(manifest_path)
        summary, output_path = self.validation_service.run_validation_suite(project, validation_file, use_gpu=use_gpu)
        return {
            'validation_summary': summary.to_dict(),
            'validation_summary_file': str(output_path),
        }

    def inspect_field_campaign(self, campaign_file: str | Path) -> dict:
        artifacts = self.field_campaign_service.inspect_campaign(campaign_file)
        return {
            'inspection_summary': artifacts.summary.to_dict(),
            'output_dir': str(artifacts.output_dir),
            'summary_file': str(artifacts.summary_file),
            'report_file': str(artifacts.report_file),
        }

    def validate_field_campaign(self, manifest_path: str | Path, scenario_path: str | Path | None, campaign_file: str | Path, use_gpu: bool = False) -> dict:
        project = self.project_api.load_manifest(manifest_path)
        if scenario_path is None:
            from mtnsim.schemas.field_campaign import FieldCampaignManifest
            campaign = FieldCampaignManifest.load(campaign_file)
            if campaign.scenario_file:
                resolved = resolve_campaign_path(campaign, campaign.scenario_file, label='campaign.scenario_file', expected_kind='file')
                assert resolved is not None
                scenario_path = resolved
            else:
                scenario_path = self._resolve_project_scenario_path(project, Path('scenarios') / f"{project.project.default_scenario}.toml")
        else:
            scenario_path = self._resolve_project_scenario_path(project, scenario_path)
        summary, output_path = self.campaign_validation_service.validate_campaign(project, scenario_path, campaign_file, use_gpu=use_gpu)
        return {
            'campaign_validation_summary': summary.to_dict(),
            'campaign_validation_summary_file': str(output_path),
        }

    def compare_field_campaigns(self, manifest_path: str | Path, campaign_file_a: str | Path, campaign_file_b: str | Path, use_gpu: bool = False) -> dict:
        project = self.project_api.load_manifest(manifest_path)
        summary, summary_file, report_file = self.field_campaign_comparison_service.compare_campaigns(
            project,
            campaign_file_a,
            campaign_file_b,
            use_gpu=use_gpu,
        )
        return {
            'campaign_comparison_summary': summary,
            'campaign_comparison_summary_file': str(summary_file),
            'campaign_comparison_report_file': str(report_file),
        }

    def _resolve_project_scenario_path(self, project, scenario_path: str | Path) -> Path:
        resolved = resolve_project_path(project, scenario_path, label='project scenario path', expected_kind='file')
        assert resolved is not None
        return resolved
