from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json


@dataclass(slots=True)
class ValidationThresholds:
    min_aligned_sample_count: int | None = None
    max_overall_rmse_db: float | None = None
    max_abs_overall_mean_bias_db: float | None = None
    max_unmatched_sensor_count: int | None = None
    max_outlier_rejected_sample_count: int | None = None
    expected_outlier_rejected_sample_count: int | None = None
    expected_sensor_time_offsets: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ValidationCaseResult:
    case_id: str
    scenario: str
    passed: bool
    result_summary_file: str
    calibration_summary_file: str
    checks: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            'case_id': self.case_id,
            'scenario': self.scenario,
            'passed': self.passed,
            'result_summary_file': self.result_summary_file,
            'calibration_summary_file': self.calibration_summary_file,
            'checks': self.checks,
        }


@dataclass(slots=True)
class ValidationSuiteSummary:
    project: str
    validation_file: str
    passed: bool
    case_results: list[ValidationCaseResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            'project': self.project,
            'validation_file': self.validation_file,
            'passed': self.passed,
            'case_results': [item.to_dict() for item in self.case_results],
        }

    @classmethod
    def load(cls, path: str | Path) -> 'ValidationSuiteSummary':
        payload = json.loads(Path(path).read_text(encoding='utf-8'))
        return cls(
            project=payload['project'],
            validation_file=payload['validation_file'],
            passed=payload['passed'],
            case_results=[ValidationCaseResult(**item) for item in payload['case_results']],
        )
