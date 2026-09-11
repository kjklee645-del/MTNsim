from __future__ import annotations

from collections import defaultdict
from math import sqrt
from pathlib import Path

from mtnsim.io.measurements import read_measurement_metadata, read_measurement_samples
from mtnsim.io.result_store import write_field_campaign_validation_summary
from mtnsim.security import PathSecurityError
from mtnsim.security.paths import resolve_campaign_path, resolve_project_path
from mtnsim.schemas.field_campaign import (
    FieldCampaignManifest,
    FieldCampaignValidationSummary,
    FieldCampaignValidationThresholds,
    ReceiverCampaignDiagnostic,
    ReceiverGroupDiagnostic,
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
        scenario_path = self._resolve_scenario_path(project, campaign, scenario_file)
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
                acceptance_status='rejected',
                acceptance_reasons=['Structural inspection failed before simulation/calibration could run.'],
                recommended_next_actions=['Fix campaign package quality issues reported by inspection before rerunning validation.'],
            )
            report_file.write_text(self._build_report(summary, campaign, inspection.summary, None, None), encoding='utf-8')
            output_path = write_field_campaign_validation_summary(inspection.output_dir, summary)
            return summary, output_path

        context = self.run_service.create_run_context(project, scenario)
        artifacts = self.run_service.run_simulation(context, use_gpu=use_gpu)
        measurement_path = self._resolve_campaign_path(campaign, campaign.measurement_file, label='campaign.measurement_file')
        metadata_path = self._resolve_campaign_path(campaign, campaign.sensor_metadata_file, label='campaign.sensor_metadata_file')
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
        receiver_group_diagnostics = self._build_receiver_group_diagnostics(receiver_diagnostics, campaign.receiver_groups)
        coverage_ratio = (calibration.aligned_sample_count / inspection.summary.measurement_row_count) if inspection.summary.measurement_row_count else 0.0
        outlier_rejection_ratio = (calibration.outlier_rejected_sample_count / calibration.aligned_sample_count) if calibration.aligned_sample_count else 0.0
        max_abs_effective_time_offset_steps = max((abs(value) for value in (calibration.effective_sensor_time_offsets or {}).values()), default=0)
        low_coverage_receiver_ids = self._find_low_coverage_receivers(receiver_diagnostics, campaign.validation_thresholds)
        low_coverage_receiver_group_ids = self._find_low_coverage_receiver_groups(receiver_group_diagnostics, campaign.validation_thresholds)
        threshold_checks = self._evaluate_thresholds(
            calibration,
            campaign.validation_thresholds,
            coverage_ratio,
            receiver_diagnostics,
            receiver_group_diagnostics,
            outlier_rejection_ratio,
            max_abs_effective_time_offset_steps,
            low_coverage_receiver_ids,
            low_coverage_receiver_group_ids,
        )
        validation_passed = all(item['passed'] for item in threshold_checks.values()) if threshold_checks else True
        worst_receiver_id = self._find_worst_receiver(receiver_diagnostics)
        worst_receiver_group_id = self._find_worst_receiver_group(receiver_group_diagnostics)
        high_error_receiver_ids = self._find_high_error_receivers(receiver_diagnostics, campaign.validation_thresholds)
        high_error_receiver_group_ids = self._find_high_error_receiver_groups(receiver_group_diagnostics, campaign.validation_thresholds)
        acceptance_status, acceptance_reasons = self._build_acceptance_decision(inspection.summary.passed, threshold_checks)
        comparison_insights = self._build_comparison_insights(receiver_diagnostics, receiver_group_diagnostics)
        recommended_next_actions = self._build_recommended_next_actions(
            acceptance_status,
            threshold_checks,
            calibration.recommendations,
            high_error_receiver_ids,
            high_error_receiver_group_ids,
            low_coverage_receiver_ids,
            low_coverage_receiver_group_ids,
        )

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
            receiver_group_diagnostics=receiver_group_diagnostics,
            high_error_receiver_ids=high_error_receiver_ids,
            high_error_receiver_group_ids=high_error_receiver_group_ids,
            low_coverage_receiver_ids=low_coverage_receiver_ids,
            low_coverage_receiver_group_ids=low_coverage_receiver_group_ids,
            calibration_recommendations=[item.to_dict() for item in calibration.recommendations],
            calibration_high_priority_receiver_ids=calibration.high_priority_receiver_ids,
            recommended_global_offset_db=calibration.recommended_global_offset_db,
            suggested_sensor_time_offset_updates=calibration.suggested_sensor_time_offset_updates,
            suggested_receiver_offset_db=calibration.suggested_receiver_offset_db,
            acceptance_status=acceptance_status,
            acceptance_reasons=acceptance_reasons,
            comparison_insights=comparison_insights,
            recommended_next_actions=recommended_next_actions,
            worst_receiver_id=worst_receiver_id,
            worst_receiver_group_id=worst_receiver_group_id,
            overall_mean_bias_db=calibration.overall_mean_bias_db,
            overall_rmse_db=calibration.overall_rmse_db,
            aligned_sample_count=calibration.aligned_sample_count,
            unmatched_sensor_count=calibration.unmatched_sensor_count,
            coverage_ratio=coverage_ratio,
            outlier_rejected_sample_count=calibration.outlier_rejected_sample_count,
            outlier_rejection_ratio=outlier_rejection_ratio,
            max_abs_effective_time_offset_steps=max_abs_effective_time_offset_steps,
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

    def _build_receiver_group_diagnostics(
        self,
        receiver_diagnostics: list[ReceiverCampaignDiagnostic],
        receiver_groups: dict[str, list[str]],
    ) -> list[ReceiverGroupDiagnostic]:
        if not receiver_groups:
            return []
        by_receiver = {item.receiver_id: item for item in receiver_diagnostics}
        diagnostics: list[ReceiverGroupDiagnostic] = []
        for group_id, receiver_ids in sorted(receiver_groups.items()):
            members = [by_receiver[receiver_id] for receiver_id in receiver_ids if receiver_id in by_receiver]
            if not members:
                diagnostics.append(
                    ReceiverGroupDiagnostic(
                        group_id=group_id,
                        receiver_ids=list(receiver_ids),
                        receiver_count=0,
                        sample_count=0,
                        expected_sample_count=0,
                        coverage_ratio=0.0,
                        mean_bias_db=0.0,
                        mae_db=0.0,
                        rmse_db=0.0,
                        rejected_outlier_count=0,
                    )
                )
                continue
            sample_count = sum(item.sample_count for item in members)
            expected_count = sum(item.expected_sample_count for item in members)
            coverage_ratio = (sample_count / expected_count) if expected_count else 0.0
            if sample_count > 0:
                mean_bias = sum(item.mean_bias_db * item.sample_count for item in members) / sample_count
                mae = sum(item.mae_db * item.sample_count for item in members) / sample_count
                rmse = sqrt(sum((item.rmse_db ** 2) * item.sample_count for item in members) / sample_count)
            else:
                weight_total = len(members)
                mean_bias = sum(item.mean_bias_db for item in members) / weight_total
                mae = sum(item.mae_db for item in members) / weight_total
                rmse = sqrt(sum(item.rmse_db ** 2 for item in members) / weight_total)
            diagnostics.append(
                ReceiverGroupDiagnostic(
                    group_id=group_id,
                    receiver_ids=list(receiver_ids),
                    receiver_count=len(members),
                    sample_count=sample_count,
                    expected_sample_count=expected_count,
                    coverage_ratio=coverage_ratio,
                    mean_bias_db=mean_bias,
                    mae_db=mae,
                    rmse_db=rmse,
                    rejected_outlier_count=sum(item.rejected_outlier_count for item in members),
                )
            )
        diagnostics.sort(key=lambda item: (-item.rmse_db, item.group_id))
        return diagnostics

    def _find_worst_receiver(self, diagnostics: list[ReceiverCampaignDiagnostic]) -> str | None:
        if not diagnostics:
            return None
        return max(diagnostics, key=lambda item: (item.rmse_db, abs(item.mean_bias_db), item.receiver_id)).receiver_id

    def _find_worst_receiver_group(self, diagnostics: list[ReceiverGroupDiagnostic]) -> str | None:
        if not diagnostics:
            return None
        return max(diagnostics, key=lambda item: (item.rmse_db, abs(item.mean_bias_db), item.group_id)).group_id

    def _find_high_error_receivers(self, diagnostics: list[ReceiverCampaignDiagnostic], thresholds: FieldCampaignValidationThresholds) -> list[str]:
        flagged: list[str] = []
        for item in diagnostics:
            if thresholds.max_receiver_rmse_db is not None and item.rmse_db > thresholds.max_receiver_rmse_db:
                flagged.append(item.receiver_id)
                continue
            if thresholds.max_receiver_abs_mean_bias_db is not None and abs(item.mean_bias_db) > thresholds.max_receiver_abs_mean_bias_db:
                flagged.append(item.receiver_id)
        return flagged

    def _find_high_error_receiver_groups(self, diagnostics: list[ReceiverGroupDiagnostic], thresholds: FieldCampaignValidationThresholds) -> list[str]:
        flagged: list[str] = []
        for item in diagnostics:
            if thresholds.max_receiver_group_rmse_db is not None and item.rmse_db > thresholds.max_receiver_group_rmse_db:
                flagged.append(item.group_id)
                continue
            if thresholds.max_receiver_group_abs_mean_bias_db is not None and abs(item.mean_bias_db) > thresholds.max_receiver_group_abs_mean_bias_db:
                flagged.append(item.group_id)
        return flagged

    def _find_low_coverage_receivers(self, diagnostics: list[ReceiverCampaignDiagnostic], thresholds: FieldCampaignValidationThresholds) -> list[str]:
        if thresholds.min_receiver_coverage_ratio is None:
            return []
        return [item.receiver_id for item in diagnostics if item.coverage_ratio < thresholds.min_receiver_coverage_ratio]

    def _find_low_coverage_receiver_groups(self, diagnostics: list[ReceiverGroupDiagnostic], thresholds: FieldCampaignValidationThresholds) -> list[str]:
        if thresholds.min_receiver_group_coverage_ratio is None:
            return []
        return [item.group_id for item in diagnostics if item.coverage_ratio < thresholds.min_receiver_group_coverage_ratio]

    def _build_acceptance_decision(self, inspection_passed: bool, threshold_checks: dict[str, dict]) -> tuple[str, list[str]]:
        if not inspection_passed:
            return 'rejected', ['Structural inspection did not pass.']
        failed_checks = [check_id for check_id, payload in threshold_checks.items() if not payload.get('passed', True)]
        if not failed_checks:
            return 'accepted', ['All declared campaign validation checks passed.']
        severe = {
            'min_aligned_sample_count',
            'max_unmatched_sensor_count',
            'min_coverage_ratio',
            'min_receiver_coverage_ratio',
            'min_receiver_group_coverage_ratio',
        }
        status = 'rejected' if any(check_id in severe for check_id in failed_checks) else 'conditional'
        reasons = [f'Failed validation check: {check_id}' for check_id in failed_checks]
        return status, reasons

    def _build_comparison_insights(
        self,
        receiver_diagnostics: list[ReceiverCampaignDiagnostic],
        receiver_group_diagnostics: list[ReceiverGroupDiagnostic],
    ) -> list[str]:
        insights: list[str] = []
        if receiver_diagnostics:
            worst_receiver = max(receiver_diagnostics, key=lambda item: (item.rmse_db, abs(item.mean_bias_db), item.receiver_id))
            insights.append(
                f'Worst receiver is {worst_receiver.receiver_id} with RMSE {worst_receiver.rmse_db:.3f} dB and mean bias {worst_receiver.mean_bias_db:.3f} dB.'
            )
        if receiver_group_diagnostics:
            worst_group = max(receiver_group_diagnostics, key=lambda item: (item.rmse_db, abs(item.mean_bias_db), item.group_id))
            insights.append(
                f'Worst receiver group is {worst_group.group_id} with RMSE {worst_group.rmse_db:.3f} dB and mean bias {worst_group.mean_bias_db:.3f} dB.'
            )
            by_group = {item.group_id: item for item in receiver_group_diagnostics}
            if 'near_field' in by_group and 'far_field' in by_group:
                near_item = by_group['near_field']
                far_item = by_group['far_field']
                insights.append(
                    f'Near/far RMSE split: near_field {near_item.rmse_db:.3f} dB vs far_field {far_item.rmse_db:.3f} dB.'
                )
                insights.append(
                    f'Near/far mean-bias split: near_field {near_item.mean_bias_db:.3f} dB vs far_field {far_item.mean_bias_db:.3f} dB.'
                )
            if 'shielded' in by_group and 'unshielded' in by_group:
                shielded_item = by_group['shielded']
                unshielded_item = by_group['unshielded']
                insights.append(
                    f'Shielded/unshielded RMSE split: shielded {shielded_item.rmse_db:.3f} dB vs unshielded {unshielded_item.rmse_db:.3f} dB.'
                )
        return insights

    def _build_recommended_next_actions(
        self,
        acceptance_status: str,
        threshold_checks: dict[str, dict],
        calibration_recommendations,
        high_error_receiver_ids: list[str],
        high_error_receiver_group_ids: list[str],
        low_coverage_receiver_ids: list[str],
        low_coverage_receiver_group_ids: list[str],
    ) -> list[str]:
        actions: list[str] = []
        failed_checks = [check_id for check_id, payload in threshold_checks.items() if not payload.get('passed', True)]
        if low_coverage_receiver_ids or low_coverage_receiver_group_ids:
            actions.append('Increase usable overlap or fix receiver/sensor time windows for low-coverage receivers before accepting the campaign.')
        if 'max_abs_effective_time_offset_steps' in failed_checks:
            actions.append('Review sensor clocks and time alignment settings because effective offsets are larger than the campaign limit.')
        if 'max_outlier_rejected_sample_count' in failed_checks or 'max_outlier_rejection_ratio' in failed_checks:
            actions.append('Inspect measurement quality and remove or annotate suspicious outlier segments.')
        if high_error_receiver_ids or high_error_receiver_group_ids:
            actions.append('Inspect geometry, traffic inputs, and local scene assumptions for the highest-error receivers or groups.')
        if calibration_recommendations:
            actions.append('Review the structured calibration recommendations before changing any physical model parameters.')
        if acceptance_status == 'accepted' and not actions:
            actions.append('Freeze this campaign package as a reusable validation baseline.')
        elif acceptance_status == 'conditional' and not actions:
            actions.append('Address the failed validation checks and rerun the campaign before accepting it as validation-grade.')
        elif acceptance_status == 'rejected' and not actions:
            actions.append('Resolve structural or severe validation failures before using this campaign for model decisions.')
        return actions

    def _evaluate_thresholds(
        self,
        calibration,
        thresholds: FieldCampaignValidationThresholds,
        coverage_ratio: float,
        receiver_diagnostics: list[ReceiverCampaignDiagnostic],
        receiver_group_diagnostics: list[ReceiverGroupDiagnostic],
        outlier_rejection_ratio: float,
        max_abs_effective_time_offset_steps: int,
        low_coverage_receiver_ids: list[str],
        low_coverage_receiver_group_ids: list[str],
    ) -> dict[str, dict]:
        checks: dict[str, dict] = {}
        if thresholds.min_aligned_sample_count is not None:
            actual = calibration.aligned_sample_count
            checks['min_aligned_sample_count'] = {'passed': actual >= thresholds.min_aligned_sample_count, 'actual': actual, 'expected_min': thresholds.min_aligned_sample_count}
        if thresholds.max_overall_rmse_db is not None:
            actual = calibration.overall_rmse_db
            checks['max_overall_rmse_db'] = {'passed': actual <= thresholds.max_overall_rmse_db, 'actual': actual, 'expected_max': thresholds.max_overall_rmse_db}
        if thresholds.max_abs_overall_mean_bias_db is not None:
            actual = abs(calibration.overall_mean_bias_db)
            checks['max_abs_overall_mean_bias_db'] = {'passed': actual <= thresholds.max_abs_overall_mean_bias_db, 'actual': actual, 'expected_max': thresholds.max_abs_overall_mean_bias_db}
        if thresholds.max_unmatched_sensor_count is not None:
            actual = calibration.unmatched_sensor_count
            checks['max_unmatched_sensor_count'] = {'passed': actual <= thresholds.max_unmatched_sensor_count, 'actual': actual, 'expected_max': thresholds.max_unmatched_sensor_count}
        if thresholds.min_coverage_ratio is not None:
            checks['min_coverage_ratio'] = {'passed': coverage_ratio >= thresholds.min_coverage_ratio, 'actual': coverage_ratio, 'expected_min': thresholds.min_coverage_ratio}
        if thresholds.min_receiver_coverage_ratio is not None:
            checks['min_receiver_coverage_ratio'] = {
                'passed': not low_coverage_receiver_ids,
                'actual_failed_receivers': low_coverage_receiver_ids,
                'expected_min': thresholds.min_receiver_coverage_ratio,
            }
        if thresholds.max_receiver_rmse_db is not None:
            failed = [item.receiver_id for item in receiver_diagnostics if item.rmse_db > thresholds.max_receiver_rmse_db]
            checks['max_receiver_rmse_db'] = {'passed': not failed, 'actual_failed_receivers': failed, 'expected_max': thresholds.max_receiver_rmse_db}
        if thresholds.max_receiver_abs_mean_bias_db is not None:
            failed = [item.receiver_id for item in receiver_diagnostics if abs(item.mean_bias_db) > thresholds.max_receiver_abs_mean_bias_db]
            checks['max_receiver_abs_mean_bias_db'] = {'passed': not failed, 'actual_failed_receivers': failed, 'expected_max': thresholds.max_receiver_abs_mean_bias_db}
        if thresholds.max_worst_receiver_rmse_db is not None:
            worst_rmse = max((item.rmse_db for item in receiver_diagnostics), default=0.0)
            checks['max_worst_receiver_rmse_db'] = {'passed': worst_rmse <= thresholds.max_worst_receiver_rmse_db, 'actual': worst_rmse, 'expected_max': thresholds.max_worst_receiver_rmse_db}
        if thresholds.max_outlier_rejected_sample_count is not None:
            actual = calibration.outlier_rejected_sample_count
            checks['max_outlier_rejected_sample_count'] = {'passed': actual <= thresholds.max_outlier_rejected_sample_count, 'actual': actual, 'expected_max': thresholds.max_outlier_rejected_sample_count}
        if thresholds.max_outlier_rejection_ratio is not None:
            checks['max_outlier_rejection_ratio'] = {'passed': outlier_rejection_ratio <= thresholds.max_outlier_rejection_ratio, 'actual': outlier_rejection_ratio, 'expected_max': thresholds.max_outlier_rejection_ratio}
        if thresholds.max_abs_effective_time_offset_steps is not None:
            checks['max_abs_effective_time_offset_steps'] = {'passed': max_abs_effective_time_offset_steps <= thresholds.max_abs_effective_time_offset_steps, 'actual': max_abs_effective_time_offset_steps, 'expected_max': thresholds.max_abs_effective_time_offset_steps}
        if thresholds.min_receiver_group_coverage_ratio is not None:
            checks['min_receiver_group_coverage_ratio'] = {
                'passed': not low_coverage_receiver_group_ids,
                'actual_failed_groups': low_coverage_receiver_group_ids,
                'expected_min': thresholds.min_receiver_group_coverage_ratio,
            }
        if thresholds.max_receiver_group_rmse_db is not None:
            failed = [item.group_id for item in receiver_group_diagnostics if item.rmse_db > thresholds.max_receiver_group_rmse_db]
            checks['max_receiver_group_rmse_db'] = {'passed': not failed, 'actual_failed_groups': failed, 'expected_max': thresholds.max_receiver_group_rmse_db}
        if thresholds.max_receiver_group_abs_mean_bias_db is not None:
            failed = [item.group_id for item in receiver_group_diagnostics if abs(item.mean_bias_db) > thresholds.max_receiver_group_abs_mean_bias_db]
            checks['max_receiver_group_abs_mean_bias_db'] = {'passed': not failed, 'actual_failed_groups': failed, 'expected_max': thresholds.max_receiver_group_abs_mean_bias_db}
        return checks

    def _resolve_campaign_path(self, campaign: FieldCampaignManifest, raw_path: str | Path, *, label: str) -> Path:
        resolved = resolve_campaign_path(campaign, raw_path, label=label, must_exist=False)
        assert resolved is not None
        return resolved

    def _resolve_scenario_path(
        self,
        project: ProjectManifest,
        campaign: FieldCampaignManifest,
        scenario_file: str | Path,
    ) -> Path:
        scenario_text = str(scenario_file).strip()
        if campaign.scenario_file:
            try:
                resolved = resolve_campaign_path(campaign, scenario_text, label='campaign.scenario_file', expected_kind='file')
            except PathSecurityError:
                resolved = None
            if resolved is not None:
                return resolved
        resolved = resolve_project_path(project, scenario_text, label='project scenario path', expected_kind='file')
        assert resolved is not None
        return resolved

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
            '## Acceptance Decision',
            '',
            f'- Acceptance status: `{summary.acceptance_status}`',
            f'- Acceptance reasons: `{summary.acceptance_reasons}`',
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
                f'- Outlier rejected sample count: `{summary.outlier_rejected_sample_count}`',
                f'- Outlier rejection ratio: `{summary.outlier_rejection_ratio}`',
                f'- Max abs effective time offset (steps): `{summary.max_abs_effective_time_offset_steps}`',
                f'- Recommended global offset (dB): `{summary.recommended_global_offset_db}`',
                f'- Worst receiver: `{summary.worst_receiver_id}`',
                f'- Worst receiver group: `{summary.worst_receiver_group_id}`',
                f'- High-error receivers: `{summary.high_error_receiver_ids}`',
                f'- High-error receiver groups: `{summary.high_error_receiver_group_ids}`',
                f'- Low-coverage receivers: `{summary.low_coverage_receiver_ids}`',
                f'- Low-coverage receiver groups: `{summary.low_coverage_receiver_group_ids}`',
                f'- Calibration high-priority receivers: `{summary.calibration_high_priority_receiver_ids}`',
                f'- Suggested sensor time-offset updates: `{summary.suggested_sensor_time_offset_updates}`',
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
            lines.extend(['', '## Receiver Group Diagnostics', ''])
            if summary.receiver_group_diagnostics:
                lines.append('| Group | Receiver Count | Samples | Expected | Coverage | Mean Bias | MAE | RMSE | Rejected Outliers | Members |')
                lines.append('| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |')
                for item in summary.receiver_group_diagnostics:
                    members = ', '.join(f'`{receiver_id}`' for receiver_id in item.receiver_ids)
                    lines.append(
                        f'| `{item.group_id}` | {item.receiver_count} | {item.sample_count} | {item.expected_sample_count} | {item.coverage_ratio:.3f} | {item.mean_bias_db:.3f} | {item.mae_db:.3f} | {item.rmse_db:.3f} | {item.rejected_outlier_count} | {members} |'
                    )
            else:
                lines.append('- No receiver groups were declared in the campaign manifest.')
            lines.extend(['', '## Comparison Insights', ''])
            if summary.comparison_insights:
                for item in summary.comparison_insights:
                    lines.append(f'- {item}')
            else:
                lines.append('- No comparison insights were generated.')
            lines.extend(['', '## Calibration Recommendations', ''])
            if summary.calibration_recommendations:
                lines.append('| Priority | Kind | Target | Value | Unit | Rationale |')
                lines.append('| --- | --- | --- | ---: | --- | --- |')
                for item in summary.calibration_recommendations:
                    value = '' if item.get('value') is None else item.get('value')
                    unit = '' if item.get('unit') is None else item.get('unit')
                    rationale = str(item.get('rationale', '')).replace('|', '/')
                    lines.append(
                        f"| `{item.get('priority', '')}` | `{item.get('kind', '')}` | `{item.get('target', '')}` | {value} | {unit} | {rationale} |"
                    )
            else:
                lines.append('- No calibration recommendations were generated.')
        else:
            lines.extend([
                '## Validation Status',
                '',
                '- Validation run was skipped because structural inspection did not pass.',
            ])
        lines.extend(['', '## Next Action', ''])
        if summary.recommended_next_actions:
            for item in summary.recommended_next_actions:
                lines.append(f'- {item}')
        elif summary.validation_passed:
            lines.append('- Campaign passed the current validation gate and can be used as a baseline comparison package.')
        else:
            lines.append('- Review threshold failures, group-level diagnostics, low-coverage receivers, and time-sync/outlier diagnostics before accepting this campaign as validation-grade.')
        lines.append('')
        return '\n'.join(lines)
