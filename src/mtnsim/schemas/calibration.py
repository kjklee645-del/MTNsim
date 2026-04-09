from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json


@dataclass(slots=True)
class MeasurementSample:
    sensor_id: str
    receiver_id: str
    time_index: int
    value_db: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MeasurementSensorMetadata:
    sensor_id: str
    simulation_receiver_id: str
    time_offset_steps: int = 0
    enabled: bool = True
    start_time_index: int | None = None
    end_time_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReceiverCalibrationStats:
    receiver_id: str
    sample_count: int
    mean_bias_db: float
    mae_db: float
    rmse_db: float
    recommended_offset_db: float
    rejected_outlier_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ReceiverCalibrationStats':
        return cls(**data)


@dataclass(slots=True)
class CalibrationRecommendation:
    kind: str
    target: str
    priority: str
    rationale: str
    value: float | int | None = None
    unit: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'CalibrationRecommendation':
        return cls(**data)


@dataclass(slots=True)
class CalibrationSummary:
    project: str
    scenario: str
    run_id: str
    measurement_file: str
    measurement_metadata_file: str | None
    aligned_sample_count: int
    skipped_sample_count: int
    unmatched_sensor_count: int
    unmatched_sensor_ids: list[str]
    overall_mean_bias_db: float
    overall_mae_db: float
    overall_rmse_db: float
    recommended_global_offset_db: float
    receiver_stats: dict[str, ReceiverCalibrationStats]
    auto_time_sync_enabled: bool = False
    max_time_offset_steps: int = 0
    effective_sensor_time_offsets: dict[str, int] | None = None
    outlier_error_threshold_db: float | None = None
    outlier_rejected_sample_count: int = 0
    suggested_sensor_time_offset_updates: dict[str, int] = field(default_factory=dict)
    suggested_receiver_offset_db: dict[str, float] = field(default_factory=dict)
    high_priority_receiver_ids: list[str] = field(default_factory=list)
    recommendations: list[CalibrationRecommendation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            'project': self.project,
            'scenario': self.scenario,
            'run_id': self.run_id,
            'measurement_file': self.measurement_file,
            'measurement_metadata_file': self.measurement_metadata_file,
            'aligned_sample_count': self.aligned_sample_count,
            'skipped_sample_count': self.skipped_sample_count,
            'unmatched_sensor_count': self.unmatched_sensor_count,
            'unmatched_sensor_ids': self.unmatched_sensor_ids,
            'overall_mean_bias_db': self.overall_mean_bias_db,
            'overall_mae_db': self.overall_mae_db,
            'overall_rmse_db': self.overall_rmse_db,
            'recommended_global_offset_db': self.recommended_global_offset_db,
            'receiver_stats': {key: value.to_dict() for key, value in self.receiver_stats.items()},
            'auto_time_sync_enabled': self.auto_time_sync_enabled,
            'max_time_offset_steps': self.max_time_offset_steps,
            'effective_sensor_time_offsets': self.effective_sensor_time_offsets,
            'outlier_error_threshold_db': self.outlier_error_threshold_db,
            'outlier_rejected_sample_count': self.outlier_rejected_sample_count,
            'suggested_sensor_time_offset_updates': self.suggested_sensor_time_offset_updates,
            'suggested_receiver_offset_db': self.suggested_receiver_offset_db,
            'high_priority_receiver_ids': self.high_priority_receiver_ids,
            'recommendations': [item.to_dict() for item in self.recommendations],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'CalibrationSummary':
        return cls(
            project=data['project'],
            scenario=data['scenario'],
            run_id=data['run_id'],
            measurement_file=data['measurement_file'],
            measurement_metadata_file=data.get('measurement_metadata_file'),
            aligned_sample_count=data['aligned_sample_count'],
            skipped_sample_count=data.get('skipped_sample_count', 0),
            unmatched_sensor_count=data.get('unmatched_sensor_count', 0),
            unmatched_sensor_ids=list(data.get('unmatched_sensor_ids', [])),
            overall_mean_bias_db=data['overall_mean_bias_db'],
            overall_mae_db=data['overall_mae_db'],
            overall_rmse_db=data['overall_rmse_db'],
            recommended_global_offset_db=data['recommended_global_offset_db'],
            receiver_stats={key: ReceiverCalibrationStats.from_dict(value) for key, value in data['receiver_stats'].items()},
            auto_time_sync_enabled=data.get('auto_time_sync_enabled', False),
            max_time_offset_steps=data.get('max_time_offset_steps', 0),
            effective_sensor_time_offsets=data.get('effective_sensor_time_offsets'),
            outlier_error_threshold_db=data.get('outlier_error_threshold_db'),
            outlier_rejected_sample_count=data.get('outlier_rejected_sample_count', 0),
            suggested_sensor_time_offset_updates=dict(data.get('suggested_sensor_time_offset_updates', {})),
            suggested_receiver_offset_db=dict(data.get('suggested_receiver_offset_db', {})),
            high_priority_receiver_ids=list(data.get('high_priority_receiver_ids', [])),
            recommendations=[CalibrationRecommendation.from_dict(item) for item in data.get('recommendations', [])],
        )

    @classmethod
    def load(cls, path: str | Path) -> 'CalibrationSummary':
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        return cls.from_dict(data)
