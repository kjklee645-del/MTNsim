from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import json

from mtnsim.acoustics.propagation.diffraction import DiffractionModelSettings, build_diffraction_context
from mtnsim.acoustics.propagation.reflection import ReflectionModelSettings, build_reflection_context
from mtnsim.acoustics.propagation.shielding import BarrierSegment, build_shielding_context


@dataclass(slots=True)
class BenchmarkCaseResult:
    case_id: str
    mode: str
    passed: bool
    value_db: float | None
    expected_min_db: float | None = None
    expected_max_db: float | None = None
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BenchmarkComparisonResult:
    comparison_id: str
    mode: str
    passed: bool
    left_case: str
    right_case: str
    left_value_db: float | None
    right_value_db: float | None
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BenchmarkRunResult:
    benchmark_file: str
    case_results: list[BenchmarkCaseResult]
    comparison_results: list[BenchmarkComparisonResult]

    @property
    def passed(self) -> bool:
        return all(item.passed for item in self.case_results) and all(item.passed for item in self.comparison_results)

    def to_dict(self) -> dict[str, Any]:
        return {
            'benchmark_file': self.benchmark_file,
            'passed': self.passed,
            'case_results': [item.to_dict() for item in self.case_results],
            'comparison_results': [item.to_dict() for item in self.comparison_results],
        }


class BenchmarkService:
    def run_propagation_benchmarks(
        self,
        benchmark_file: str | Path,
        reflection_settings: ReflectionModelSettings | None = None,
        diffraction_settings: DiffractionModelSettings | None = None,
    ) -> BenchmarkRunResult:
        benchmark_path = Path(benchmark_file)
        payload = json.loads(benchmark_path.read_text(encoding='utf-8'))
        case_values: dict[str, float | None] = {}
        case_results: list[BenchmarkCaseResult] = []

        for case in payload.get('cases', []):
            result = self._run_case(case, reflection_settings=reflection_settings, diffraction_settings=diffraction_settings)
            case_results.append(result)
            case_values[result.case_id] = result.value_db

        comparison_results: list[BenchmarkComparisonResult] = []
        for comparison in payload.get('comparisons', []):
            left = case_values.get(comparison['left_case'])
            right = case_values.get(comparison['right_case'])
            mode = comparison['mode']
            if left is None or right is None:
                comparison_results.append(
                    BenchmarkComparisonResult(
                        comparison_id=comparison['comparison_id'],
                        mode=mode,
                        passed=False,
                        left_case=comparison['left_case'],
                        right_case=comparison['right_case'],
                        left_value_db=left,
                        right_value_db=right,
                        message='missing case value',
                    )
                )
                continue
            if mode == 'less_than':
                passed = left < right
                message = f'{left:.3f} < {right:.3f}' if passed else f'expected {left:.3f} < {right:.3f}'
            else:
                passed = False
                message = f'unsupported comparison mode: {mode}'
            comparison_results.append(
                BenchmarkComparisonResult(
                    comparison_id=comparison['comparison_id'],
                    mode=mode,
                    passed=passed,
                    left_case=comparison['left_case'],
                    right_case=comparison['right_case'],
                    left_value_db=left,
                    right_value_db=right,
                    message=message,
                )
            )

        return BenchmarkRunResult(
            benchmark_file=str(benchmark_path),
            case_results=case_results,
            comparison_results=comparison_results,
        )

    def _run_case(
        self,
        case: dict[str, Any],
        reflection_settings: ReflectionModelSettings | None = None,
        diffraction_settings: DiffractionModelSettings | None = None,
    ) -> BenchmarkCaseResult:
        barrier = BarrierSegment(**case['barrier'])
        receiver_pos = tuple(case['receiver_xyz'])
        source_pos = tuple(case['source_xy'])
        mode = case['mode']
        value_db: float | None = None
        message = ''

        if mode == 'reflection':
            context = build_reflection_context(
                receiver_pos=receiver_pos,
                source_pos=source_pos,
                barriers=[barrier],
                settings=reflection_settings,
            )
            value_db = None if context is None else context.gain_db
        elif mode == 'diffraction':
            shielding = build_shielding_context(receiver_pos=receiver_pos, source_pos=source_pos, barriers=[barrier])
            context = build_diffraction_context(shielding, settings=diffraction_settings)
            value_db = None if context is None else context.gain_db
        else:
            message = f'unsupported case mode: {mode}'

        expected = case.get('expected', {})
        expected_min = expected.get('min_gain_db')
        expected_max = expected.get('max_gain_db')
        passed = value_db is not None and (expected_min is None or value_db >= expected_min) and (expected_max is None or value_db <= expected_max)
        if value_db is None and not message:
            message = 'model returned no context'
        elif passed:
            message = f'value {value_db:.3f} within expected range'
        elif not message:
            message = f'value {value_db:.3f} outside range [{expected_min}, {expected_max}]'

        return BenchmarkCaseResult(
            case_id=case['case_id'],
            mode=mode,
            passed=passed,
            value_db=value_db,
            expected_min_db=expected_min,
            expected_max_db=expected_max,
            message=message,
        )
