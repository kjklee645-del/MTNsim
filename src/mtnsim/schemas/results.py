from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import json

from mtnsim.schemas.run import RunSummary


@dataclass(slots=True)
class ReceiverStats:
    min_db: float
    max_db: float
    mean_db: float
    sample_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ReceiverStats':
        return cls(**data)


@dataclass(slots=True)
class ReceiverDelta:
    min_db_delta: float
    max_db_delta: float
    mean_db_delta: float
    sample_count_delta: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RunResultSummary:
    run: RunSummary
    output_dir: str
    manifest_file: str
    receiver_history_files: dict[str, str]
    final_grid_snapshot_file: str | None
    used_gpu: bool
    receiver_stats: dict[str, ReceiverStats]
    propagation_features: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'run': self.run.to_dict(),
            'output_dir': self.output_dir,
            'manifest_file': self.manifest_file,
            'receiver_history_files': self.receiver_history_files,
            'final_grid_snapshot_file': self.final_grid_snapshot_file,
            'used_gpu': self.used_gpu,
            'receiver_stats': {key: value.to_dict() for key, value in self.receiver_stats.items()},
            'propagation_features': self.propagation_features,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'RunResultSummary':
        return cls(
            run=RunSummary(**data['run']),
            output_dir=data['output_dir'],
            manifest_file=data['manifest_file'],
            receiver_history_files=data['receiver_history_files'],
            final_grid_snapshot_file=data.get('final_grid_snapshot_file'),
            used_gpu=data['used_gpu'],
            receiver_stats={key: ReceiverStats.from_dict(value) for key, value in data['receiver_stats'].items()},
            propagation_features=data.get('propagation_features'),
        )

    @classmethod
    def load(cls, path: str | Path) -> 'RunResultSummary':
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        return cls.from_dict(data)


@dataclass(slots=True)
class ScenarioComparison:
    project: str
    scenario_a: str
    scenario_b: str
    differing_fields: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RunResultComparison:
    project: str
    scenario_a: str
    scenario_b: str
    run_a_id: str
    run_b_id: str
    receiver_deltas: dict[str, ReceiverDelta]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            'project': self.project,
            'scenario_a': self.scenario_a,
            'scenario_b': self.scenario_b,
            'run_a_id': self.run_a_id,
            'run_b_id': self.run_b_id,
            'receiver_deltas': {key: value.to_dict() for key, value in self.receiver_deltas.items()},
            'summary': self.summary,
        }