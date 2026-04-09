from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path
from typing import Any
import json

from mtnsim.acoustics.propagation.diffraction import DEFAULT_DIFFRACTION_SETTINGS, DiffractionModelSettings
from mtnsim.acoustics.propagation.reflection import DEFAULT_REFLECTION_SETTINGS, ReflectionModelSettings
from mtnsim.services.benchmark_service import BenchmarkRunResult, BenchmarkService


@dataclass(slots=True)
class PropagationTuningResult:
    benchmark_file: str
    tuning_file: str
    best_score: float
    evaluated_candidates: int
    reflection_settings: dict[str, float]
    diffraction_settings: dict[str, float]
    benchmark_result: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TuningService:
    def __init__(self, benchmark_service: BenchmarkService | None = None) -> None:
        self.benchmark_service = benchmark_service or BenchmarkService()

    def tune_propagation(self, benchmark_file: str | Path, tuning_file: str | Path) -> PropagationTuningResult:
        benchmark_path = Path(benchmark_file)
        tuning_path = Path(tuning_file)
        tuning_payload = json.loads(tuning_path.read_text(encoding='utf-8'))

        reflection_candidates = self._candidate_reflection_settings(tuning_payload.get('reflection', {}))
        diffraction_candidates = self._candidate_diffraction_settings(tuning_payload.get('diffraction', {}))

        best_score = float('inf')
        best_result: BenchmarkRunResult | None = None
        best_reflection = DEFAULT_REFLECTION_SETTINGS
        best_diffraction = DEFAULT_DIFFRACTION_SETTINGS
        evaluated = 0

        for reflection_settings, diffraction_settings in product(reflection_candidates, diffraction_candidates):
            evaluated += 1
            result = self.benchmark_service.run_propagation_benchmarks(
                benchmark_path,
                reflection_settings=reflection_settings,
                diffraction_settings=diffraction_settings,
            )
            score = self._score(result)
            if score < best_score:
                best_score = score
                best_result = result
                best_reflection = reflection_settings
                best_diffraction = diffraction_settings

        if best_result is None:
            raise RuntimeError('no tuning candidates evaluated')

        return PropagationTuningResult(
            benchmark_file=str(benchmark_path),
            tuning_file=str(tuning_path),
            best_score=best_score,
            evaluated_candidates=evaluated,
            reflection_settings={
                'max_extra_path_meters': best_reflection.max_extra_path_meters,
                'max_nearest_offset_meters': best_reflection.max_nearest_offset_meters,
                'min_normal_alignment': best_reflection.min_normal_alignment,
                'centrality_floor': best_reflection.centrality_floor,
                'centrality_weight': best_reflection.centrality_weight,
                'extra_path_scale_meters': best_reflection.extra_path_scale_meters,
                'source_distance_scale_meters': best_reflection.source_distance_scale_meters,
                'receiver_distance_scale_meters': best_reflection.receiver_distance_scale_meters,
                'energy_scale': best_reflection.energy_scale,
                'max_gain_db': best_reflection.max_gain_db,
            },
            diffraction_settings={
                'wavelength_meters': best_diffraction.wavelength_meters,
                'height_penalty_scale': best_diffraction.height_penalty_scale,
                'height_penalty_cap_db': best_diffraction.height_penalty_cap_db,
                'min_remaining_attenuation_db': best_diffraction.min_remaining_attenuation_db,
            },
            benchmark_result=best_result.to_dict(),
        )

    def _candidate_reflection_settings(self, payload: dict[str, Any]) -> list[ReflectionModelSettings]:
        base = DEFAULT_REFLECTION_SETTINGS
        keys = ['min_normal_alignment', 'energy_scale', 'extra_path_scale_meters', 'max_gain_db']
        values = [payload.get(key, [getattr(base, key)]) for key in keys]
        candidates: list[ReflectionModelSettings] = []
        for min_normal_alignment, energy_scale, extra_path_scale_meters, max_gain_db in product(*values):
            candidates.append(
                ReflectionModelSettings(
                    max_extra_path_meters=base.max_extra_path_meters,
                    max_nearest_offset_meters=base.max_nearest_offset_meters,
                    min_normal_alignment=float(min_normal_alignment),
                    centrality_floor=base.centrality_floor,
                    centrality_weight=base.centrality_weight,
                    extra_path_scale_meters=float(extra_path_scale_meters),
                    source_distance_scale_meters=base.source_distance_scale_meters,
                    receiver_distance_scale_meters=base.receiver_distance_scale_meters,
                    energy_scale=float(energy_scale),
                    max_gain_db=float(max_gain_db),
                )
            )
        return candidates

    def _candidate_diffraction_settings(self, payload: dict[str, Any]) -> list[DiffractionModelSettings]:
        base = DEFAULT_DIFFRACTION_SETTINGS
        keys = ['wavelength_meters', 'height_penalty_scale', 'height_penalty_cap_db', 'min_remaining_attenuation_db']
        values = [payload.get(key, [getattr(base, key)]) for key in keys]
        candidates: list[DiffractionModelSettings] = []
        for wavelength_meters, height_penalty_scale, height_penalty_cap_db, min_remaining_attenuation_db in product(*values):
            candidates.append(
                DiffractionModelSettings(
                    wavelength_meters=float(wavelength_meters),
                    height_penalty_scale=float(height_penalty_scale),
                    height_penalty_cap_db=float(height_penalty_cap_db),
                    min_remaining_attenuation_db=float(min_remaining_attenuation_db),
                )
            )
        return candidates

    def _score(self, result: BenchmarkRunResult) -> float:
        score = 0.0
        for case in result.case_results:
            if case.expected_context is False:
                if case.value_db is not None:
                    score += 100.0 + abs(case.value_db)
                continue
            if case.value_db is None:
                score += 100.0
                continue
            if case.expected_min_db is not None and case.value_db < case.expected_min_db:
                score += (case.expected_min_db - case.value_db) ** 2
            if case.expected_max_db is not None and case.value_db > case.expected_max_db:
                score += (case.value_db - case.expected_max_db) ** 2
        for comparison in result.comparison_results:
            if not comparison.passed:
                score += 25.0
                if comparison.left_value_db is not None and comparison.right_value_db is not None:
                    score += abs(comparison.left_value_db - comparison.right_value_db)
        return score
