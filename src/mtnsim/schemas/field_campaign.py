from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json


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
    source_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload['source_path'] = str(self.source_path) if self.source_path else None
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any], source_path: str | Path | None = None) -> 'FieldCampaignManifest':
        return cls(
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
            source_path=Path(source_path) if source_path is not None else None,
        )

    @classmethod
    def load(cls, path: str | Path) -> 'FieldCampaignManifest':
        path = Path(path)
        return cls.from_dict(json.loads(path.read_text(encoding='utf-8')), source_path=path)


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
    high_error_receiver_ids: list[str] = field(default_factory=list)
    low_coverage_receiver_ids: list[str] = field(default_factory=list)
    worst_receiver_id: str | None = None
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
            'high_error_receiver_ids': self.high_error_receiver_ids,
            'low_coverage_receiver_ids': self.low_coverage_receiver_ids,
            'worst_receiver_id': self.worst_receiver_id,
            'overall_mean_bias_db': self.overall_mean_bias_db,
            'overall_rmse_db': self.overall_rmse_db,
            'aligned_sample_count': self.aligned_sample_count,
            'unmatched_sensor_count': self.unmatched_sensor_count,
            'coverage_ratio': self.coverage_ratio,
            'outlier_rejected_sample_count': self.outlier_rejected_sample_count,
            'outlier_rejection_ratio': self.outlier_rejection_ratio,
            'max_abs_effective_time_offset_steps': self.max_abs_effective_time_offset_steps,
        }
