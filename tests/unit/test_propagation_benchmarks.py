from pathlib import Path

from mtnsim.services.benchmark_service import BenchmarkService
from mtnsim.services.tuning_service import TuningService


def test_propagation_reference_benchmarks_pass() -> None:
    root = Path(__file__).resolve().parents[2]
    result = BenchmarkService().run_propagation_benchmarks(root / 'benchmarks' / 'propagation_reference_cases.json')
    assert result.passed
    assert len(result.case_results) >= 4
    assert len(result.comparison_results) >= 2


def test_propagation_tuning_finds_zero_penalty_candidate() -> None:
    root = Path(__file__).resolve().parents[2]
    result = TuningService().tune_propagation(root / 'benchmarks' / 'propagation_reference_cases.json', root / 'benchmarks' / 'propagation_tuning_space.json')
    assert result.best_score == 0.0
    assert result.evaluated_candidates > 1
