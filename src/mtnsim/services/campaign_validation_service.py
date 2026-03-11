from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from mtnsim.io.measurements import read_measurement_metadata, read_measurement_samples
from mtnsim.io.result_store import write_field_campaign_validation_summary
from mtnsim.schemas.field_campaign import (
    FieldCampaignManifest,
    FieldCampaignValidationSummary,
    FieldCampaignValidationThresholds,
    ReceiverCampaignDiagnostic,
)
from mtnsim.schemas.project import ProjectManifest
from mtnsim.schemas.scenario import ScenarioConfig
from mtnsim.services.calibration_service import CalibrationService
from mtnsim.services.field_campaign_service import FieldCampaignService
from mtnsim.services.run_service import RunService


class CampaignValidationService:
    def __init__(
        self,
        field_campaign_service: FieldCampaignService | None = None,
        run_service: RunService | None = None,
        calibration_service: CalibrationService | None = None,
    ) -> None:
        self.field_campaign_service = field_campaign_service or FieldCampaignService()
        self.run_service = run_service or RunService()
        self.calibration_service = calibration_service or CalibrationService()

    def validate_campaign(
        self,
        project: ProjectManifest,
        scenario_file: str | Path,
        campaign_file: str | Path,
        use_gpu: bool = False,
    ) -> tuple[FieldCampaignValidationSummary, Path]:
        inspection = self.field_campaign_service.inspect_campaign(campaign_file)
        campaign = FieldCampaignManifest.load(campaign_file)
        campaign_root = campaign.source_path.parent if campaign.source_path else Path.cwd()
        scenario_path = self._resolve(campaign_root, scenario_file)
        scenario = ScenarioConfig.load(scenario_path)
        report_file = inspection.output_dir / 'campaign_validation_report.md'

        if not inspection.summary.passed:
            summary = FieldCampaignValidationSummary(
                campaign_id=campaign.campaign_id,
                name=campaign.name,
                project=project.project.name,
                scenario=scenario.scenario.name,
                inspection_passed=False,
                validation_passed=False,
                simulation_executed=False,
                inspection_summary_file=str(inspection.summary_file),
                inspection_report_file=str(inspection.report_file),
                result_summary_file=None,
                calibration_summary_file=None,
                campaign_validation_report_file=str(report_file),
            )
            report_file.write_text(self._build_report(summary, campaign, inspection.summary, None, None), encoding='utf-8')
            output_path = write_field_campaign_validation_summary(inspection.output_dir, summary)
            return summary, output_path

        context = self.run_service.create_run_context(project, scenario)
        artifacts = self.run_service.run_simulation(context, use_gpu=use_gpu)
        measurement_path = self._resolve(campaign_root, campaign.measurement_file)
        metadata_path = self._resolve(campaign_root, campaign.sensor_metadata_file)
        calibration, calibration_path = self.calibration_service.calibrate_and_store(
            artifacts.result_summary,
            measurement_path,
            measurement_metadata_file=metadata_path,
            time_step_seconds=project.simulation_defaults.time_step_seconds,
            auto_time_sync=campaign.auto_time_sync,
            max_time_offset_steps=campaign.max_time_offset_steps,
            outlier_error_threshold_db=campaign.outlier_error_threshold_db,
            min_alignment_samples=campaign.min_alignment_samples,
        )

        receiver_diagnostics = self._build_receiver_diagnostics(measurement_path, metadata_path, calibration, project.simulation_defaults.time_step_seconds)
        coverage_ratio = (calibration.aligned_sample_count / inspection.summary.measurement_row_count) if inspection.summary.measurement_row_count else 0.0
        threshold_checks = self._evaluate_thresholds(calibration.to_dict(), campaign.validation_thresholds, coverage_ratio, receiver_diagnostics)
        validation_passed = all(item['passed'] for item in threshold_checks.values()) if threshold_checks else True
        worst_receiver_id = self._find_worst_receiver(receiver_diagnostics)
        high_error_receiver_ids = self._find_high_error_receivers(receiver_diagnostics, campaign.validation_thresholds)

        summary = FieldCampaignValidationSummary(
            campaign_id=campaign.campaign_id,
            name=campaign.name,
            project=project.project.name,
            scenario=scenario.scenario.name,
            inspection_passed=True,
            validation_passed=validation_passed,
            simulation_executed=True,
            inspection_summary_file=str(inspection.summary_file),
            inspection_report_file=str(inspection.report_file),
            result_summary_file=str(artifacts.result_summary_file),
            calibration_summary_file=str(calibration_path),
            campaign_validation_report_file=str(report_file),
            threshold_checks=threshold_checks,
            receiver_diagnostics=receiver_diagnostics,
            high_error_receiver_ids=high_error_receiver_ids,
            worst_receiver_id=worst_receiver_id,
            overall_mean_bias_db=calibration.overall_mean_bias_db,
            overall_rmse_db=calibration.overall_rmse_db,
            aligned_sample_count=calibration.aligned_sample_count,
            unmatched_sensor_count=calibration.unmatched_sensor_count,
            coverage_ratio=coverage_ratio,
        )
        report_file.write_text(self._build_report(summary, campaign, inspection.summary, artifacts.result_summary_file, calibration_path), encoding='utf-8')
        output_path = write_field_campaign_validation_summary(inspection.output_dir, summary)
        return summary, output_path

    def _build_receiver_diagnostics(self, measurement_path: Path, metadata_path: Path, calibration, time_step_seconds: float) -> list[ReceiverCampaignDiagnostic]:
        read_result = read_measurement_samples(measurement_path, time_step_seconds=time_step_seconds)
        metadata = read_measurement_metadata(metadata_path)
        expected_counts: dict[str, int] = defaultdict(int)
        for sample in read_result.samples:
            mapping = metadata.get(sample.sensor_id) or metadata.get(sample.receiver_id)
            if mapping is not None and not mapping.enabled:
                continue
            receiver_id = mapping.simulation_receiver_id if mapping else sample.receiver_id
            expected_counts[receiver_id] += 1

        diagnostics: list[ReceiverCampaignDiagnostic] = []
        all_receiver_ids = set(expected_counts) | set(calibration.receiver_stats)
        for receiver_id in sorted(all_receiver_ids):
            stats = calibration.receiver_stats.get(receiver_id)
            expected = expected_counts.get(receiver_id, 0)
            sample_count = stats.sample_count if stats else 0
            coverage = (sample_count / expected) if expected else 0.0
            diagnostics.append(
                ReceiverCampaignDiagnostic(
                    receiver_id=receiver_id,
                    sample_count=sample_count,
                    expected_sample_count=expected,
                    coverage_ratio=coverage,
                    mean_bias_db=stats.mean_bias_db if stats else 0.0,
                    mae_db=stats.mae_db if stats else 0.0,
                    rmse_db=stats.rmse_db if stats else 0.0,
                    rejected_outlier_count=stats.rejected_outlier_count if stats else 0,
                )
            )
        diagnostics.sort(key=lambda item: (-item.rmse_db, item.receiver_id))
        return diagnostics

    def _find_worst_receiver(self, diagnostics: list[ReceiverCampaignDiagnostic]) -> str | None:
        if not diagnostics:
            return None
        return max(diagnostics, key=lambda item: (item.rmse_db, abs(item.mean_bias_db), item.receiver_id)).receiver_id

    def _find_high_error_receivers(self, diagnostics: list[ReceiverCampaignDiagnostic], thresholds: FieldCampaignValidationThresholds) -> list[str]:
        flagged: list[str] = []
        for item in diagnostics:
            if thresholds.max_receiver_rmse_db is not None and item.rmse_db > thresholds.max_receiver_rmse_db:
                flagged.append(item.receiver_id)
                continue
            if thresholds.max_receiver_abs_mean_bias_db is not None and abs(item.mean_bias_db) > thresholds.max_receiver_abs_mean_bias_db:
                flagged.append(item.receiver_id)
        return flagged

    def _evaluate_thresholds(
        self,
        calibration_summary: dict,
        thresholds: FieldCampaignValidationThresholds,
        coverage_ratio: float,
        receiver_diagnostics: list[ReceiverCampaignDiagnostic],
    ) -> dict[str, dict]:
        checks: dict[str, dict] = {}
        if thresholds.min_aligned_sample_count is not None:
            actual = calibration_summary['aligned_sample_count']
            checks['min_aligned_sample_count'] = {'passed': actual >= thresholds.min_aligned_sample_count, 'actual': actual, 'expected_min': thresholds.min_aligned_sample_count}
        if thresholds.max_overall_rmse_db is not None:
            actual = calibration_summary['overall_rmse_db']
            checks['max_overall_rmse_db'] = {'passed': actual <= thresholds.max_overall_rmse_db, 'actual': actual, 'expected_max': thresholds.max_overall_rmse_db}
        if thresholds.max_abs_overall_mean_bias_db is not None:
            actual = abs(calibration_summary['overall_mean_bias_db'])
            checks['max_abs_overall_mean_bias_db'] = {'passed': actual <= thresholds.max_abs_overall_mean_bias_db, 'actual': actual, 'expected_max': thresholds.max_abs_overall_mean_bias_db}
        if thresholds.max_unmatched_sensor_count is not None:
            actual = calibration_summary['unmatched_sensor_count']
            checks['max_unmatched_sensor_count'] = {'passed': actual <= thresholds.max_unmatched_sensor_count, 'actual': actual, 'expected_max': thresholds.max_unmatched_sensor_count}
        if thresholds.min_coverage_ratio is not None:
            checks['min_coverage_ratio'] = {'passed': coverage_ratio >= thresholds.min_coverage_ratio, 'actual': coverage_ratio, 'expected_min': thresholds.min_coverage_ratio}
        if thresholds.max_receiver_rmse_db is not None:
            failed = [item.receiver_id for item in receiver_diagnostics if item.rmse_db > thresholds.max_receiver_rmse_db]
            checks['max_receiver_rmse_db'] = {'passed': not failed, 'actual_failed_receivers': failed, 'expected_max': thresholds.max_receiver_rmse_db}
        if thresholds.max_receiver_abs_mean_bias_db is not None:
            failed = [item.receiver_id for item in receiver_diagnostics if abs(item.mean_bias_db) > thresholds.max_receiver_abs_mean_bias_db]
            checks['max_receiver_abs_mean_bias_db'] = {'passed': not failed, 'actual_failed_receivers': failed, 'expected_max': thresholds.max_receiver_abs_mean_bias_db}
        return checks

    def _resolve(self, root: Path, raw_path: str | Path) -> Path:
        path = Path(raw_path)
        return path if path.is_absolute() else root / path

    def _build_report(self, summary: FieldCampaignValidationSummary, campaign: FieldCampaignManifest, inspection_summary, result_summary_file: Path | None, calibration_summary_file: Path | None) -> str:
        lines = [
            f'# Field Campaign Validation Report: {campaign.name}',
            '',
            f'- Campaign ID: `{campaign.campaign_id}`',
            f'- Project: `{summary.project}`',
            f'- Scenario: `{summary.scenario}`',
            f'- Inspection passed: `{summary.inspection_passed}`',
            f'- Validation passed: `{summary.validation_passed}`',
            f'- Simulation executed: `{summary.simulation_executed}`',
            f'- Inspection summary: `{summary.inspection_summary_file}`',
            f'- Inspection report: `{summary.inspection_report_file}`',
            f'- Result summary: `{result_summary_file}`' if result_summary_file else '- Result summary: not generated',
            f'- Calibration summary: `{calibration_summary_file}`' if calibration_summary_file else '- Calibration summary: not generated',
            '',
            '## Campaign Description',
            '',
            campaign.description or 'No description provided.',
            '',
            '## Inspection Snapshot',
            '',
            f'- Measurement rows: `{inspection_summary.measurement_row_count}`',
            f'- Measurement sensors: `{inspection_summary.measurement_sensor_count}`',
            f'- Metadata sensors: `{inspection_summary.metadata_sensor_count}`',
            f'- Traffic rows: `{inspection_summary.traffic_row_count}`',
            '',
        ]
        if summary.simulation_executed:
            lines.extend([
                '## Calibration Summary',
                '',
                f'- Aligned sample count: `{summary.aligned_sample_count}`',
                f'- Coverage ratio: `{summary.coverage_ratio}`',
                f'- Overall mean bias (dB): `{summary.overall_mean_bias_db}`',
                f'- Overall RMSE (dB): `{summary.overall_rmse_db}`',
                f'- Unmatched sensor count: `{summary.unmatched_sensor_count}`',
                f'- Worst receiver: `{summary.worst_receiver_id}`',
                f'- High-error receivers: `{summary.high_error_receiver_ids}`',
                '',
                '## Threshold Checks',
                '',
            ])
            if summary.threshold_checks:
                for check_id, payload in summary.threshold_checks.items():
                    lines.append(f"- [{'x' if payload['passed'] else ' '}] `{check_id}`: `{payload}`")
            else:
                lines.append('- No threshold checks were declared in the campaign manifest.')
            lines.extend(['', '## Receiver Diagnostics', ''])
            if summary.receiver_diagnostics:
                lines.append('| Receiver | Samples | Expected | Coverage | Mean Bias | MAE | RMSE | Rejected Outliers |')
                lines.append('| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |')
                for item in summary.receiver_diagnostics:
                    lines.append(
                        f'| `{item.receiver_id}` | {item.sample_count} | {item.expected_sample_count} | {item.coverage_ratio:.3f} | {item.mean_bias_db:.3f} | {item.mae_db:.3f} | {item.rmse_db:.3f} | {item.rejected_outlier_count} |'
                    )
            else:
                lines.append('- No receiver diagnostics were generated.')
        else:
            lines.extend([
                '## Validation Status',
                '',
                '- Validation run was skipped because structural inspection did not pass.',
            ])
        lines.extend(['', '## Next Action', ''])
        if summary.validation_passed:
            lines.append('- Campaign passed the current validation gate and can be used as a baseline comparison package.')
        else:
            lines.append('- Review threshold failures and receiver-level diagnostics before accepting this campaign as validation-grade.')
        lines.append('')
        return '\n'.join(lines)
