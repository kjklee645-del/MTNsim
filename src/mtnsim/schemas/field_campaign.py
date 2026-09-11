from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json

from mtnsim.security.exceptions import ConfigValidationError
from mtnsim.security.paths import campaign_root_from_manifest_path, validate_path_within_root
from mtnsim.security.validators import (
    ensure_non_empty_string,
    ensure_non_negative_number,
    ensure_positive_number,
    ensure_ratio,
)


@dataclass(slots=True)
class FieldCampaignValidationThresholds:
    min_aligned_sample_count: int | None = None
    max_overall_rmse_db: float | None = None
    max_abs_overall_mean_bias_db: float | None = None
    max_unmatched_sensor_count: int | None = None
    min_coverage_ratio: float | None = None
    min_receiver_coverage_ratio: float | None = None
    max_receiver_rmse_db: float | None = None
    max_receiver_abs_mean_bias_db: float | None = None
    max_worst_receiver_rmse_db: float | None = None
    max_outlier_rejected_sample_count: int | None = None
    max_outlier_rejection_ratio: float | None = None
    max_abs_effective_time_offset_steps: int | None = None
    max_receiver_group_rmse_db: float | None = None
    max_receiver_group_abs_mean_bias_db: float | None = None
    min_receiver_group_coverage_ratio: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FieldCampaignManifest:
    campaign_id: str
    name: str
    measurement_file: str
    sensor_metadata_file: str
    traffic_file: str | None = None
    traffic_metadata_file: str | None = None
    scene_path: str | None = None
    scene_manifest_file: str | None = None
    notes_file: str | None = None
    scenario_file: str | None = None
    description: str = ''
    time_column_preference: str | None = None
    expected_unit: str = 'dB(A)'
    expected_time_zone: str | None = None
    coordinate_system: str | None = None
    auto_time_sync: bool = False
    max_time_offset_steps: int = 5
    outlier_error_threshold_db: float | None = None
    min_alignment_samples: int = 3
    validation_thresholds: FieldCampaignValidationThresholds = field(default_factory=FieldCampaignValidationThresholds)
    receiver_groups: dict[str, list[str]] = field(default_factory=dict)
    source_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload['source_path'] = str(self.source_path) if self.source_path else None
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any], source_path: str | Path | None = None) -> 'FieldCampaignManifest':
        resolved_source = Path(source_path).expanduser().resolve() if source_path is not None else None
        try:
            manifest = cls(
                campaign_id=data['campaign_id'],
                name=data['name'],
                measurement_file=data['measurement_file'],
                sensor_metadata_file=data['sensor_metadata_file'],
                traffic_file=data.get('traffic_file'),
                traffic_metadata_file=data.get('traffic_metadata_file'),
                scene_path=data.get('scene_path'),
                scene_manifest_file=data.get('scene_manifest_file'),
                notes_file=data.get('notes_file'),
                scenario_file=data.get('scenario_file'),
                description=data.get('description', ''),
                time_column_preference=data.get('time_column_preference'),
                expected_unit=data.get('expected_unit', 'dB(A)'),
                expected_time_zone=data.get('expected_time_zone'),
                coordinate_system=data.get('coordinate_system'),
                auto_time_sync=bool(data.get('auto_time_sync', False)),
                max_time_offset_steps=int(data.get('max_time_offset_steps', 5)),
                outlier_error_threshold_db=data.get('outlier_error_threshold_db'),
                min_alignment_samples=int(data.get('min_alignment_samples', 3)),
                validation_thresholds=FieldCampaignValidationThresholds(**(data.get('validation_thresholds') or {})),
                receiver_groups={str(key): [str(item) for item in value] for key, value in (data.get('receiver_groups') or {}).items()},
                source_path=resolved_source,
            )
        except KeyError as exc:
            raise ConfigValidationError(f"Field campaign manifest is missing required field: {exc}") from exc
        except (TypeError, ValueError) as exc:
            raise ConfigValidationError(f"Field campaign manifest is invalid: {exc}") from exc
        manifest.validate()
        return manifest

    def validate(self) -> None:
        ensure_non_empty_string(self.campaign_id, 'campaign_id')
        ensure_non_empty_string(self.name, 'name')
        ensure_non_empty_string(self.measurement_file, 'measurement_file')
        ensure_non_empty_string(self.sensor_metadata_file, 'sensor_metadata_file')
        ensure_non_empty_string(self.expected_unit, 'expected_unit')
        ensure_non_negative_number(self.max_time_offset_steps, 'max_time_offset_steps')
        ensure_positive_number(self.min_alignment_samples, 'min_alignment_samples')
        if self.outlier_error_threshold_db is not None:
            ensure_non_negative_number(self.outlier_error_threshold_db, 'outlier_error_threshold_db')

        thresholds = self.validation_thresholds
        for field_name in (
            'min_aligned_sample_count',
            'max_overall_rmse_db',
            'max_abs_overall_mean_bias_db',
            'max_unmatched_sensor_count',
            'max_receiver_rmse_db',
            'max_receiver_abs_mean_bias_db',
            'max_worst_receiver_rmse_db',
            'max_outlier_rejected_sample_count',
            'max_abs_effective_time_offset_steps',
            'max_receiver_group_rmse_db',
            'max_receiver_group_abs_mean_bias_db',
        ):
            value = getattr(thresholds, field_name)
            if value is not None:
                ensure_non_negative_number(value, f'validation_thresholds.{field_name}')
        for field_name in ('min_coverage_ratio', 'min_receiver_coverage_ratio', 'max_outlier_rejection_ratio', 'min_receiver_group_coverage_ratio'):
            value = getattr(thresholds, field_name)
            if value is not None:
                ensure_ratio(value, f'validation_thresholds.{field_name}')

        for group_id, receiver_ids in self.receiver_groups.items():
            ensure_non_empty_string(group_id, f'receiver_groups[{group_id}]')
            for receiver_id in receiver_ids:
                ensure_non_empty_string(receiver_id, f'receiver_groups[{group_id}] receiver id')

        if self.source_path is None:
            return

        campaign_root = campaign_root_from_manifest_path(self.source_path)
        for label, raw_path in (
            ('measurement_file', self.measurement_file),
            ('sensor_metadata_file', self.sensor_metadata_file),
            ('traffic_file', self.traffic_file),
            ('traffic_metadata_file', self.traffic_metadata_file),
            ('scene_path', self.scene_path),
            ('scene_manifest_file', self.scene_manifest_file),
            ('notes_file', self.notes_file),
            ('scenario_file', self.scenario_file),
        ):
            if raw_path is None:
                continue
            validate_path_within_root(campaign_root, raw_path, label=label)

    @classmethod
    def load(cls, path: str | Path) -> 'FieldCampaignManifest':
        path = Path(path).expanduser().resolve()
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            raise ConfigValidationError(f"Field campaign manifest JSON is invalid: {path}") from exc
        return cls.from_dict(payload, source_path=path)


@dataclass(slots=True)
class CampaignQualityCheck:
    check_id: str
    passed: bool
    severity: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FieldCampaignInspectionSummary:
    campaign_id: str
    name: str
    passed: bool
    measurement_row_count: int
    measurement_sensor_count: int
    metadata_sensor_count: int
    traffic_row_count: int | None
    checks: list[CampaignQualityCheck]

    def to_dict(self) -> dict[str, Any]:
        return {
            'campaign_id': self.campaign_id,
            'name': self.name,
            'passed': self.passed,
            'measurement_row_count': self.measurement_row_count,
            'measurement_sensor_count': self.measurement_sensor_count,
            'metadata_sensor_count': self.metadata_sensor_count,
            'traffic_row_count': self.traffic_row_count,
            'checks': [item.to_dict() for item in self.checks],
        }


@dataclass(slots=True)
class ReceiverCampaignDiagnostic:
    receiver_id: str
    sample_count: int
    expected_sample_count: int
    coverage_ratio: float
    mean_bias_db: float
    mae_db: float
    rmse_db: float
    rejected_outlier_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReceiverGroupDiagnostic:
    group_id: str
    receiver_ids: list[str]
    receiver_count: int
    sample_count: int
    expected_sample_count: int
    coverage_ratio: float
    mean_bias_db: float
    mae_db: float
    rmse_db: float
    rejected_outlier_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FieldCampaignValidationSummary:
    campaign_id: str
    name: str
    project: str
    scenario: str
    inspection_passed: bool
    validation_passed: bool
    simulation_executed: bool
    inspection_summary_file: str
    inspection_report_file: str
    result_summary_file: str | None
    calibration_summary_file: str | None
    campaign_validation_report_file: str
    threshold_checks: dict[str, dict[str, Any]] = field(default_factory=dict)
    receiver_diagnostics: list[ReceiverCampaignDiagnostic] = field(default_factory=list)
    receiver_group_diagnostics: list[ReceiverGroupDiagnostic] = field(default_factory=list)
    high_error_receiver_ids: list[str] = field(default_factory=list)
    high_error_receiver_group_ids: list[str] = field(default_factory=list)
    low_coverage_receiver_ids: list[str] = field(default_factory=list)
    low_coverage_receiver_group_ids: list[str] = field(default_factory=list)
    calibration_recommendations: list[dict[str, Any]] = field(default_factory=list)
    calibration_high_priority_receiver_ids: list[str] = field(default_factory=list)
    recommended_global_offset_db: float | None = None
    suggested_sensor_time_offset_updates: dict[str, int] = field(default_factory=dict)
    suggested_receiver_offset_db: dict[str, float] = field(default_factory=dict)
    acceptance_status: str | None = None
    acceptance_reasons: list[str] = field(default_factory=list)
    comparison_insights: list[str] = field(default_factory=list)
    recommended_next_actions: list[str] = field(default_factory=list)
    worst_receiver_id: str | None = None
    worst_receiver_group_id: str | None = None
    overall_mean_bias_db: float | None = None
    overall_rmse_db: float | None = None
    aligned_sample_count: int | None = None
    unmatched_sensor_count: int | None = None
    coverage_ratio: float | None = None
    outlier_rejected_sample_count: int | None = None
    outlier_rejection_ratio: float | None = None
    max_abs_effective_time_offset_steps: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'campaign_id': self.campaign_id,
            'name': self.name,
            'project': self.project,
            'scenario': self.scenario,
            'inspection_passed': self.inspection_passed,
            'validation_passed': self.validation_passed,
            'simulation_executed': self.simulation_executed,
            'inspection_summary_file': self.inspection_summary_file,
            'inspection_report_file': self.inspection_report_file,
            'result_summary_file': self.result_summary_file,
            'calibration_summary_file': self.calibration_summary_file,
            'campaign_validation_report_file': self.campaign_validation_report_file,
            'threshold_checks': self.threshold_checks,
            'receiver_diagnostics': [item.to_dict() for item in self.receiver_diagnostics],
            'receiver_group_diagnostics': [item.to_dict() for item in self.receiver_group_diagnostics],
            'high_error_receiver_ids': self.high_error_receiver_ids,
            'high_error_receiver_group_ids': self.high_error_receiver_group_ids,
            'low_coverage_receiver_ids': self.low_coverage_receiver_ids,
            'low_coverage_receiver_group_ids': self.low_coverage_receiver_group_ids,
            'calibration_recommendations': self.calibration_recommendations,
            'calibration_high_priority_receiver_ids': self.calibration_high_priority_receiver_ids,
            'recommended_global_offset_db': self.recommended_global_offset_db,
            'suggested_sensor_time_offset_updates': self.suggested_sensor_time_offset_updates,
            'suggested_receiver_offset_db': self.suggested_receiver_offset_db,
            'acceptance_status': self.acceptance_status,
            'acceptance_reasons': self.acceptance_reasons,
            'comparison_insights': self.comparison_insights,
            'recommended_next_actions': self.recommended_next_actions,
            'worst_receiver_id': self.worst_receiver_id,
            'worst_receiver_group_id': self.worst_receiver_group_id,
            'overall_mean_bias_db': self.overall_mean_bias_db,
            'overall_rmse_db': self.overall_rmse_db,
            'aligned_sample_count': self.aligned_sample_count,
            'unmatched_sensor_count': self.unmatched_sensor_count,
            'coverage_ratio': self.coverage_ratio,
            'outlier_rejected_sample_count': self.outlier_rejected_sample_count,
            'outlier_rejection_ratio': self.outlier_rejection_ratio,
            'max_abs_effective_time_offset_steps': self.max_abs_effective_time_offset_steps,
        }
