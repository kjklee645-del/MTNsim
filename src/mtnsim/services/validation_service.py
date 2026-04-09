from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

from mtnsim.io.result_store import write_validation_suite_summary
from mtnsim.schemas.project import ProjectManifest
from mtnsim.schemas.scenario import ScenarioConfig
from mtnsim.schemas.validation import ValidationCaseResult, ValidationSuiteSummary, ValidationThresholds
from mtnsim.services.calibration_service import CalibrationService
from mtnsim.services.run_service import RunService


class ValidationService:
    def __init__(self, run_service: RunService | None = None, calibration_service: CalibrationService | None = None) -> None:
        self.run_service = run_service or RunService()
        self.calibration_service = calibration_service or CalibrationService()

    def run_validation_suite(
        self,
        project: ProjectManifest,
        validation_file: str | Path,
        use_gpu: bool = False,
    ) -> tuple[ValidationSuiteSummary, Path]:
        validation_path = Path(validation_file)
        payload = json.loads(validation_path.read_text(encoding='utf-8'))
        case_results: list[ValidationCaseResult] = []

        for case in payload.get('cases', []):
            scenario_path = self._resolve_project_relative(project, case['scenario'])
            measurement_path = self._resolve_project_relative(project, case['measurement'])
            measurement_meta = case.get('measurement_metadata')
            measurement_meta_path = self._resolve_project_relative(project, measurement_meta) if measurement_meta else None

            scenario = ScenarioConfig.load(scenario_path)
            context = self.run_service.create_run_context(project, scenario)
            artifacts = self.run_service.run_simulation(context, use_gpu=use_gpu and not case.get('force_cpu', True))
            calibration, calibration_path = self.calibration_service.calibrate_and_store(
                artifacts.result_summary,
                measurement_path,
                measurement_metadata_file=measurement_meta_path,
                time_step_seconds=project.simulation_defaults.time_step_seconds,
                auto_time_sync=bool(case.get('auto_time_sync', False)),
                max_time_offset_steps=int(case.get('max_time_offset_steps', 5)),
                outlier_error_threshold_db=case.get('outlier_error_threshold_db'),
                min_alignment_samples=int(case.get('min_alignment_samples', 3)),
            )

            thresholds = ValidationThresholds(**case.get('thresholds', {}))
            checks = self._evaluate_thresholds(calibration.to_dict(), thresholds)
            passed = all(item['passed'] for item in checks.values()) if checks else True
            case_results.append(
                ValidationCaseResult(
                    case_id=case['case_id'],
                    scenario=str(scenario_path),
                    passed=passed,
                    result_summary_file=str(artifacts.result_summary_file),
                    calibration_summary_file=str(calibration_path),
                    checks=checks,
                )
            )

        summary = ValidationSuiteSummary(
            project=project.project.name,
            validation_file=str(validation_path),
            passed=all(item.passed for item in case_results),
            case_results=case_results,
        )
        output_root = self._resolve_project_relative(project, project.paths.outputs)
        output_path = write_validation_suite_summary(output_root, summary)
        return summary, output_path

    def _evaluate_thresholds(self, calibration_summary: dict, thresholds: ValidationThresholds) -> dict[str, dict]:
        checks: dict[str, dict] = {}

        if thresholds.min_aligned_sample_count is not None:
            actual = calibration_summary['aligned_sample_count']
            checks['min_aligned_sample_count'] = {
                'passed': actual >= thresholds.min_aligned_sample_count,
                'actual': actual,
                'expected_min': thresholds.min_aligned_sample_count,
            }

        if thresholds.max_overall_rmse_db is not None:
            actual = calibration_summary['overall_rmse_db']
            checks['max_overall_rmse_db'] = {
                'passed': actual <= thresholds.max_overall_rmse_db,
                'actual': actual,
                'expected_max': thresholds.max_overall_rmse_db,
            }

        if thresholds.max_abs_overall_mean_bias_db is not None:
            actual = abs(calibration_summary['overall_mean_bias_db'])
            checks['max_abs_overall_mean_bias_db'] = {
                'passed': actual <= thresholds.max_abs_overall_mean_bias_db,
                'actual': actual,
                'expected_max': thresholds.max_abs_overall_mean_bias_db,
            }

        if thresholds.max_unmatched_sensor_count is not None:
            actual = calibration_summary['unmatched_sensor_count']
            checks['max_unmatched_sensor_count'] = {
                'passed': actual <= thresholds.max_unmatched_sensor_count,
                'actual': actual,
                'expected_max': thresholds.max_unmatched_sensor_count,
            }

        if thresholds.max_outlier_rejected_sample_count is not None:
            actual = calibration_summary.get('outlier_rejected_sample_count', 0)
            checks['max_outlier_rejected_sample_count'] = {
                'passed': actual <= thresholds.max_outlier_rejected_sample_count,
                'actual': actual,
                'expected_max': thresholds.max_outlier_rejected_sample_count,
            }

        if thresholds.expected_outlier_rejected_sample_count is not None:
            actual = calibration_summary.get('outlier_rejected_sample_count', 0)
            checks['expected_outlier_rejected_sample_count'] = {
                'passed': actual == thresholds.expected_outlier_rejected_sample_count,
                'actual': actual,
                'expected': thresholds.expected_outlier_rejected_sample_count,
            }

        if thresholds.expected_sensor_time_offsets:
            actual_offsets = calibration_summary.get('effective_sensor_time_offsets') or {}
            passed = all(actual_offsets.get(key) == value for key, value in thresholds.expected_sensor_time_offsets.items())
            checks['expected_sensor_time_offsets'] = {
                'passed': passed,
                'actual': actual_offsets,
                'expected': thresholds.expected_sensor_time_offsets,
            }

        return checks

    def _resolve_project_relative(self, project: ProjectManifest, raw_path: str | Path) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        if project.source_path is None:
            return path
        source_parent = project.source_path.parent
        project_root = source_parent.parent if source_parent.name == 'examples' else source_parent
        return project_root / path
