from __future__ import annotations

from pathlib import Path
import json

from mtnsim.schemas.field_campaign import FieldCampaignManifest
from mtnsim.schemas.project import ProjectManifest
from mtnsim.services.campaign_validation_service import CampaignValidationService


class FieldCampaignComparisonService:
    def __init__(self, campaign_validation_service: CampaignValidationService | None = None) -> None:
        self.campaign_validation_service = campaign_validation_service or CampaignValidationService()

    def compare_campaigns(
        self,
        project: ProjectManifest,
        campaign_file_a: str | Path,
        campaign_file_b: str | Path,
        use_gpu: bool = False,
    ) -> tuple[dict, Path, Path]:
        campaign_a = FieldCampaignManifest.load(campaign_file_a)
        campaign_b = FieldCampaignManifest.load(campaign_file_b)
        scenario_a = self._resolve_scenario_path(project, campaign_a)
        scenario_b = self._resolve_scenario_path(project, campaign_b)

        summary_a, _ = self.campaign_validation_service.validate_campaign(project, scenario_a, campaign_file_a, use_gpu=use_gpu)
        summary_b, _ = self.campaign_validation_service.validate_campaign(project, scenario_b, campaign_file_b, use_gpu=use_gpu)

        output_dir = self._comparison_output_dir(project, campaign_a.campaign_id, campaign_b.campaign_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        summary = self._build_summary(summary_a.to_dict(), summary_b.to_dict())
        summary_file = output_dir / 'campaign_comparison_summary.json'
        report_file = output_dir / 'campaign_comparison_report.md'
        summary_file.write_text(json.dumps(summary, indent=2), encoding='utf-8')
        report_file.write_text(self._build_report(summary), encoding='utf-8')
        return summary, summary_file, report_file

    def _resolve_scenario_path(self, project: ProjectManifest, campaign: FieldCampaignManifest) -> Path:
        if campaign.scenario_file:
            scenario_path = Path(campaign.scenario_file)
            if not scenario_path.is_absolute() and campaign.source_path is not None:
                return campaign.source_path.parent / scenario_path
            return scenario_path
        if project.source_path is None:
            return Path(f"scenarios/{project.project.default_scenario}.toml")
        return project.source_path.parent / 'scenarios' / f'{project.project.default_scenario}.toml'

    def _comparison_output_dir(self, project: ProjectManifest, campaign_id_a: str, campaign_id_b: str) -> Path:
        base = Path(project.paths.outputs)
        if not base.is_absolute() and project.source_path is not None:
            project_root = project.source_path.parent.parent if project.source_path.parent.name == 'examples' else project.source_path.parent
            base = project_root / base
        return base / 'field_campaign_comparisons' / f'{campaign_id_a}_vs_{campaign_id_b}'

    def _build_summary(self, summary_a: dict, summary_b: dict) -> dict:
        receiver_deltas = self._receiver_deltas(summary_a, summary_b)
        group_deltas = self._group_deltas(summary_a, summary_b)
        threshold_diff = self._threshold_diff(summary_a, summary_b)
        return {
            'campaign_a': {
                'campaign_id': summary_a['campaign_id'],
                'name': summary_a['name'],
                'scenario': summary_a['scenario'],
                'acceptance_status': summary_a.get('acceptance_status'),
                'validation_passed': summary_a['validation_passed'],
                'overall_mean_bias_db': summary_a.get('overall_mean_bias_db'),
                'overall_rmse_db': summary_a.get('overall_rmse_db'),
                'coverage_ratio': summary_a.get('coverage_ratio'),
            },
            'campaign_b': {
                'campaign_id': summary_b['campaign_id'],
                'name': summary_b['name'],
                'scenario': summary_b['scenario'],
                'acceptance_status': summary_b.get('acceptance_status'),
                'validation_passed': summary_b['validation_passed'],
                'overall_mean_bias_db': summary_b.get('overall_mean_bias_db'),
                'overall_rmse_db': summary_b.get('overall_rmse_db'),
                'coverage_ratio': summary_b.get('coverage_ratio'),
            },
            'delta': {
                'overall_mean_bias_db': (summary_b.get('overall_mean_bias_db') or 0.0) - (summary_a.get('overall_mean_bias_db') or 0.0),
                'overall_rmse_db': (summary_b.get('overall_rmse_db') or 0.0) - (summary_a.get('overall_rmse_db') or 0.0),
                'coverage_ratio': (summary_b.get('coverage_ratio') or 0.0) - (summary_a.get('coverage_ratio') or 0.0),
                'aligned_sample_count': (summary_b.get('aligned_sample_count') or 0) - (summary_a.get('aligned_sample_count') or 0),
            },
            'threshold_diff': threshold_diff,
            'top_receiver_rmse_deltas': receiver_deltas,
            'top_receiver_group_rmse_deltas': group_deltas,
            'comparison_insights': self._comparison_insights(summary_a, summary_b, receiver_deltas, group_deltas, threshold_diff),
        }

    def _receiver_deltas(self, summary_a: dict, summary_b: dict) -> list[dict]:
        a_map = {item['receiver_id']: item for item in summary_a.get('receiver_diagnostics', [])}
        b_map = {item['receiver_id']: item for item in summary_b.get('receiver_diagnostics', [])}
        shared = sorted(set(a_map) & set(b_map))
        rows = []
        for receiver_id in shared:
            a_item = a_map[receiver_id]
            b_item = b_map[receiver_id]
            rows.append({
                'receiver_id': receiver_id,
                'rmse_delta_db': b_item['rmse_db'] - a_item['rmse_db'],
                'mean_bias_delta_db': b_item['mean_bias_db'] - a_item['mean_bias_db'],
                'coverage_delta': b_item['coverage_ratio'] - a_item['coverage_ratio'],
                'campaign_a_rmse_db': a_item['rmse_db'],
                'campaign_b_rmse_db': b_item['rmse_db'],
            })
        rows.sort(key=lambda item: abs(item['rmse_delta_db']), reverse=True)
        return rows[:5]

    def _group_deltas(self, summary_a: dict, summary_b: dict) -> list[dict]:
        a_map = {item['group_id']: item for item in summary_a.get('receiver_group_diagnostics', [])}
        b_map = {item['group_id']: item for item in summary_b.get('receiver_group_diagnostics', [])}
        shared = sorted(set(a_map) & set(b_map))
        rows = []
        for group_id in shared:
            a_item = a_map[group_id]
            b_item = b_map[group_id]
            rows.append({
                'group_id': group_id,
                'rmse_delta_db': b_item['rmse_db'] - a_item['rmse_db'],
                'mean_bias_delta_db': b_item['mean_bias_db'] - a_item['mean_bias_db'],
                'coverage_delta': b_item['coverage_ratio'] - a_item['coverage_ratio'],
                'campaign_a_rmse_db': a_item['rmse_db'],
                'campaign_b_rmse_db': b_item['rmse_db'],
            })
        rows.sort(key=lambda item: abs(item['rmse_delta_db']), reverse=True)
        return rows[:5]

    def _threshold_diff(self, summary_a: dict, summary_b: dict) -> dict:
        a_checks = summary_a.get('threshold_checks', {})
        b_checks = summary_b.get('threshold_checks', {})
        all_ids = sorted(set(a_checks) | set(b_checks))
        diff = {}
        for check_id in all_ids:
            diff[check_id] = {
                'campaign_a_passed': a_checks.get(check_id, {}).get('passed'),
                'campaign_b_passed': b_checks.get(check_id, {}).get('passed'),
            }
        return diff

    def _comparison_insights(self, summary_a: dict, summary_b: dict, receiver_deltas: list[dict], group_deltas: list[dict], threshold_diff: dict) -> list[str]:
        insights: list[str] = []
        insights.append(
            f"Acceptance status changed from {summary_a.get('acceptance_status')} to {summary_b.get('acceptance_status')}."
        )
        rmse_delta = (summary_b.get('overall_rmse_db') or 0.0) - (summary_a.get('overall_rmse_db') or 0.0)
        insights.append(
            f"Overall RMSE changed by {rmse_delta:.3f} dB ({summary_a.get('overall_rmse_db')} -> {summary_b.get('overall_rmse_db')})."
        )
        bias_delta = (summary_b.get('overall_mean_bias_db') or 0.0) - (summary_a.get('overall_mean_bias_db') or 0.0)
        insights.append(
            f"Overall mean bias changed by {bias_delta:.3f} dB ({summary_a.get('overall_mean_bias_db')} -> {summary_b.get('overall_mean_bias_db')})."
        )
        changed_thresholds = [check_id for check_id, payload in threshold_diff.items() if payload['campaign_a_passed'] != payload['campaign_b_passed']]
        if changed_thresholds:
            insights.append(f'Threshold pass/fail changed for: {changed_thresholds}.')
        if receiver_deltas:
            top = receiver_deltas[0]
            insights.append(
                f"Largest receiver RMSE change is at {top['receiver_id']}: {top['rmse_delta_db']:.3f} dB."
            )
        if group_deltas:
            top = group_deltas[0]
            insights.append(
                f"Largest receiver-group RMSE change is at {top['group_id']}: {top['rmse_delta_db']:.3f} dB."
            )
        return insights

    def _build_report(self, summary: dict) -> str:
        lines = [
            '# Field Campaign Comparison Report',
            '',
            '## Campaigns',
            '',
            f"- Campaign A: `{summary['campaign_a']['campaign_id']}` / scenario `{summary['campaign_a']['scenario']}` / acceptance `{summary['campaign_a']['acceptance_status']}`",
            f"- Campaign B: `{summary['campaign_b']['campaign_id']}` / scenario `{summary['campaign_b']['scenario']}` / acceptance `{summary['campaign_b']['acceptance_status']}`",
            '',
            '## Metric Deltas',
            '',
            f"- Overall RMSE delta (B - A): `{summary['delta']['overall_rmse_db']}` dB",
            f"- Overall mean bias delta (B - A): `{summary['delta']['overall_mean_bias_db']}` dB",
            f"- Coverage ratio delta (B - A): `{summary['delta']['coverage_ratio']}`",
            f"- Aligned sample count delta (B - A): `{summary['delta']['aligned_sample_count']}`",
            '',
            '## Comparison Insights',
            '',
        ]
        for item in summary.get('comparison_insights', []):
            lines.append(f'- {item}')
        lines.extend(['', '## Receiver RMSE Deltas', ''])
        if summary.get('top_receiver_rmse_deltas'):
            lines.append('| Receiver | Campaign A RMSE | Campaign B RMSE | RMSE Delta | Bias Delta | Coverage Delta |')
            lines.append('| --- | ---: | ---: | ---: | ---: | ---: |')
            for item in summary['top_receiver_rmse_deltas']:
                lines.append(
                    f"| `{item['receiver_id']}` | {item['campaign_a_rmse_db']:.3f} | {item['campaign_b_rmse_db']:.3f} | {item['rmse_delta_db']:.3f} | {item['mean_bias_delta_db']:.3f} | {item['coverage_delta']:.3f} |"
                )
        else:
            lines.append('- No shared receiver diagnostics were available.')
        lines.extend(['', '## Receiver Group RMSE Deltas', ''])
        if summary.get('top_receiver_group_rmse_deltas'):
            lines.append('| Group | Campaign A RMSE | Campaign B RMSE | RMSE Delta | Bias Delta | Coverage Delta |')
            lines.append('| --- | ---: | ---: | ---: | ---: | ---: |')
            for item in summary['top_receiver_group_rmse_deltas']:
                lines.append(
                    f"| `{item['group_id']}` | {item['campaign_a_rmse_db']:.3f} | {item['campaign_b_rmse_db']:.3f} | {item['rmse_delta_db']:.3f} | {item['mean_bias_delta_db']:.3f} | {item['coverage_delta']:.3f} |"
                )
        else:
            lines.append('- No shared receiver-group diagnostics were available.')
        lines.extend(['', '## Threshold Status Changes', ''])
        for check_id, payload in summary.get('threshold_diff', {}).items():
            lines.append(f"- `{check_id}`: A=`{payload['campaign_a_passed']}` / B=`{payload['campaign_b_passed']}`")
        lines.append('')
        return '\n'.join(lines)
