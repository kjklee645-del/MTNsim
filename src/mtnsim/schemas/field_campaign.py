from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json


@dataclass(slots=True)
class FieldCampaignManifest:
    campaign_id: str
    name: str
    measurement_file: str
    sensor_metadata_file: str
    traffic_file: str | None = None
    scene_path: str | None = None
    notes_file: str | None = None
    description: str = ''
    time_column_preference: str | None = None
    expected_unit: str = 'dB(A)'
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
            scene_path=data.get('scene_path'),
            notes_file=data.get('notes_file'),
            description=data.get('description', ''),
            time_column_preference=data.get('time_column_preference'),
            expected_unit=data.get('expected_unit', 'dB(A)'),
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
