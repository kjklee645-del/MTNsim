from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import csv
import math

from mtnsim.io.measurements import read_measurement_metadata, read_measurement_samples
from mtnsim.io.result_store import write_calibration_summary
from mtnsim.schemas.calibration import (
    CalibrationRecommendation,
    CalibrationSummary,
    MeasurementSample,
    MeasurementSensorMetadata,
    ReceiverCalibrationStats,
)
from mtnsim.schemas.project import ProjectManifest
from mtnsim.schemas.results import RunResultSummary


class CalibrationService:
    def calibrate_run(
        self,
        result_summary: RunResultSummary,
        measurement_file: str | Path,
        measurement_metadata_file: str | Path | None = None,
        time_step_seconds: float = 1.0,
        auto_time_sync: bool = False,
        max_time_offset_steps: int = 5,
        outlier_error_threshold_db: float | None = None,
        min_alignment_samples: int = 3,
    ) -> CalibrationSummary:
        measurement_path = Path(measurement_file)
        read_result = read_measurement_samples(measurement_path, time_step_seconds=time_step_seconds)
        metadata_path = Path(measurement_metadata_file) if measurement_metadata_file else None
        metadata = read_measurement_metadata(metadata_path) if metadata_path else {}
        simulations = self._load_simulation_histories(result_summary)

        grouped_samples: dict[str, list[MeasurementSample]] = defaultdict(list)
        for sample in read_result.samples:
            grouped_samples[sample.sensor_id].append(sample)

        grouped_errors: dict[str, list[float]] = defaultdict(list)
        aligned_sample_count = 0
        skipped_sample_count = read_result.skipped_row_count
        unmatched_sensor_ids: set[str] = set()
        effective_sensor_time_offsets: dict[str, int] = {}
        base_sensor_time_offsets: dict[str, int] = {}
        receiver_from_sensor: dict[str, str] = {}

        for sensor_id, samples in grouped_samples.items():
            mapping = metadata.get(sensor_id) or metadata.get(samples[0].receiver_id)
            if mapping is not None and not mapping.enabled:
                skipped_sample_count += len(samples)
                continue

            simulation_receiver_id = mapping.simulation_receiver_id if mapping else samples[0].receiver_id
            receiver_from_sensor[sensor_id] = simulation_receiver_id
            receiver_history = simulations.get(simulation_receiver_id)
            if receiver_history is None:
                unmatched_sensor_ids.add(sensor_id)
                continue

            base_offset = mapping.time_offset_steps if mapping else 0
            base_sensor_time_offsets[sensor_id] = base_offset
            effective_offset = base_offset
            if auto_time_sync:
                estimated = self._estimate_best_offset(
                    samples,
                    receiver_history,
                    mapping,
                    base_offset,
                    max_time_offset_steps,
                    min_alignment_samples,
                )
                effective_offset = estimated if estimated is not None else base_offset
            effective_sensor_time_offsets[sensor_id] = effective_offset

            for sample in samples:
                simulation_time_index = sample.time_index + effective_offset
                if mapping is not None:
                    if mapping.start_time_index is not None and simulation_time_index < mapping.start_time_index:
                        skipped_sample_count += 1
                        continue
                    if mapping.end_time_index is not None and simulation_time_index > mapping.end_time_index:
                        skipped_sample_count += 1
                        continue
                if simulation_time_index < 0 or simulation_time_index >= len(receiver_history):
                    skipped_sample_count += 1
                    continue

                simulated = receiver_history[simulation_time_index]
                error = simulated - sample.value_db
                grouped_errors[simulation_receiver_id].append(error)
                aligned_sample_count += 1

        receiver_stats: dict[str, ReceiverCalibrationStats] = {}
        all_errors: list[float] = []
        outlier_rejected_sample_count = 0
        threshold = outlier_error_threshold_db if outlier_error_threshold_db is not None and outlier_error_threshold_db >= 0 else None

        for receiver_id, errors in grouped_errors.items():
            filtered_errors = errors
            rejected_count = 0
            if threshold is not None:
                filtered_errors = [error for error in errors if abs(error) <= threshold]
                rejected_count = len(errors) - len(filtered_errors)
                outlier_rejected_sample_count += rejected_count
            if not filtered_errors:
                receiver_stats[receiver_id] = ReceiverCalibrationStats(
                    receiver_id=receiver_id,
                    sample_count=0,
                    mean_bias_db=0.0,
                    mae_db=0.0,
                    rmse_db=0.0,
                    recommended_offset_db=0.0,
                    rejected_outlier_count=rejected_count,
                )
                continue
            all_errors.extend(filtered_errors)
            mean_bias = sum(filtered_errors) / len(filtered_errors)
            mae = sum(abs(error) for error in filtered_errors) / len(filtered_errors)
            rmse = math.sqrt(sum((error * error) for error in filtered_errors) / len(filtered_errors))
            receiver_stats[receiver_id] = ReceiverCalibrationStats(
                receiver_id=receiver_id,
                sample_count=len(filtered_errors),
                mean_bias_db=mean_bias,
                mae_db=mae,
                rmse_db=rmse,
                recommended_offset_db=-mean_bias,
                rejected_outlier_count=rejected_count,
            )

        if all_errors:
            overall_mean_bias = sum(all_errors) / len(all_errors)
            overall_mae = sum(abs(error) for error in all_errors) / len(all_errors)
            overall_rmse = math.sqrt(sum((error * error) for error in all_errors) / len(all_errors))
        else:
            overall_mean_bias = 0.0
            overall_mae = 0.0
            overall_rmse = 0.0

        suggested_sensor_time_offset_updates = {
            sensor_id: effective_offset
            for sensor_id, effective_offset in effective_sensor_time_offsets.items()
            if effective_offset != base_sensor_time_offsets.get(sensor_id, 0)
        }
        suggested_receiver_offset_db = {
            receiver_id: stats.recommended_offset_db
            for receiver_id, stats in receiver_stats.items()
            if stats.sample_count > 0
        }
        high_priority_receiver_ids = self._select_high_priority_receivers(receiver_stats, overall_rmse)
        recommendations = self._build_recommendations(
            overall_mean_bias=overall_mean_bias,
            overall_rmse=overall_rmse,
            unmatched_sensor_ids=sorted(unmatched_sensor_ids),
            outlier_rejected_sample_count=outlier_rejected_sample_count,
            suggested_sensor_time_offset_updates=suggested_sensor_time_offset_updates,
            receiver_stats=receiver_stats,
            high_priority_receiver_ids=high_priority_receiver_ids,
        )

        return CalibrationSummary(
            project=result_summary.run.project,
            scenario=result_summary.run.scenario,
            run_id=result_summary.run.run_id,
            measurement_file=str(measurement_path),
            measurement_metadata_file=str(metadata_path) if metadata_path else None,
            aligned_sample_count=aligned_sample_count,
            skipped_sample_count=skipped_sample_count,
            unmatched_sensor_count=len(unmatched_sensor_ids),
            unmatched_sensor_ids=sorted(unmatched_sensor_ids),
            overall_mean_bias_db=overall_mean_bias,
            overall_mae_db=overall_mae,
            overall_rmse_db=overall_rmse,
            recommended_global_offset_db=-overall_mean_bias,
            receiver_stats=receiver_stats,
            auto_time_sync_enabled=auto_time_sync,
            max_time_offset_steps=max_time_offset_steps if auto_time_sync else 0,
            effective_sensor_time_offsets=effective_sensor_time_offsets,
            outlier_error_threshold_db=threshold,
            outlier_rejected_sample_count=outlier_rejected_sample_count,
            suggested_sensor_time_offset_updates=suggested_sensor_time_offset_updates,
            suggested_receiver_offset_db=suggested_receiver_offset_db,
            high_priority_receiver_ids=high_priority_receiver_ids,
            recommendations=recommendations,
        )

    def calibrate_and_store(
        self,
        result_summary: RunResultSummary,
        measurement_file: str | Path,
        measurement_metadata_file: str | Path | None = None,
        time_step_seconds: float = 1.0,
        auto_time_sync: bool = False,
        max_time_offset_steps: int = 5,
        outlier_error_threshold_db: float | None = None,
        min_alignment_samples: int = 3,
    ) -> tuple[CalibrationSummary, Path]:
        summary = self.calibrate_run(
            result_summary,
            measurement_file,
            measurement_metadata_file=measurement_metadata_file,
            time_step_seconds=time_step_seconds,
            auto_time_sync=auto_time_sync,
            max_time_offset_steps=max_time_offset_steps,
            outlier_error_threshold_db=outlier_error_threshold_db,
            min_alignment_samples=min_alignment_samples,
        )
        output_path = write_calibration_summary(result_summary.output_dir, summary)
        return summary, output_path

    def resolve_default_metadata_path(self, project: ProjectManifest | None = None) -> Path | None:
        if project is None or project.paths.measurement_metadata is None:
            return None
        if project.source_path is None:
            return Path(project.paths.measurement_metadata)
        project_root = project.source_path.parent.parent if project.source_path.parent.name == 'examples' else project.source_path.parent
        path = Path(project.paths.measurement_metadata)
        return path if path.is_absolute() else project_root / path

    def _estimate_best_offset(
        self,
        samples: list[MeasurementSample],
        receiver_history: list[float],
        mapping: MeasurementSensorMetadata | None,
        base_offset: int,
        max_time_offset_steps: int,
        min_alignment_samples: int,
    ) -> int | None:
        best_offset: int | None = None
        best_score: float | None = None
        best_overlap = -1
        for delta in range(-max_time_offset_steps, max_time_offset_steps + 1):
            candidate_offset = base_offset + delta
            errors: list[float] = []
            for sample in samples:
                simulation_time_index = sample.time_index + candidate_offset
                if mapping is not None:
                    if mapping.start_time_index is not None and simulation_time_index < mapping.start_time_index:
                        continue
                    if mapping.end_time_index is not None and simulation_time_index > mapping.end_time_index:
                        continue
                if simulation_time_index < 0 or simulation_time_index >= len(receiver_history):
                    continue
                errors.append(receiver_history[simulation_time_index] - sample.value_db)
            if len(errors) < min_alignment_samples:
                continue
            score = sum(abs(error) for error in errors) / len(errors)
            if best_score is None or score < best_score or (math.isclose(score, best_score) and len(errors) > best_overlap):
                best_score = score
                best_offset = candidate_offset
                best_overlap = len(errors)
        return best_offset

    def _select_high_priority_receivers(self, receiver_stats: dict[str, ReceiverCalibrationStats], overall_rmse: float) -> list[str]:
        ranked = sorted(receiver_stats.values(), key=lambda item: (-item.rmse_db, -abs(item.mean_bias_db), item.receiver_id))
        meaningful = [
            item for item in ranked
            if item.sample_count > 0 and (item.rmse_db >= max(1.0, overall_rmse * 1.25) or abs(item.mean_bias_db) >= 0.25)
        ]
        return [item.receiver_id for item in meaningful[:5]]

    def _build_recommendations(
        self,
        overall_mean_bias: float,
        overall_rmse: float,
        unmatched_sensor_ids: list[str],
        outlier_rejected_sample_count: int,
        suggested_sensor_time_offset_updates: dict[str, int],
        receiver_stats: dict[str, ReceiverCalibrationStats],
        high_priority_receiver_ids: list[str],
    ) -> list[CalibrationRecommendation]:
        recommendations: list[CalibrationRecommendation] = []
        if abs(overall_mean_bias) >= 0.25:
            recommendations.append(
                CalibrationRecommendation(
                    kind='global_level_offset',
                    target='global',
                    priority='high' if abs(overall_mean_bias) >= 1.0 else 'medium',
                    rationale=f'Overall mean bias is {overall_mean_bias:.3f} dB, suggesting a stable global level correction candidate.',
                    value=-overall_mean_bias,
                    unit='dB',
                )
            )
        if overall_rmse >= 1.0:
            recommendations.append(
                CalibrationRecommendation(
                    kind='fit_quality_review',
                    target='global',
                    priority='medium',
                    rationale=f'Overall RMSE is {overall_rmse:.3f} dB, so scene geometry, traffic inputs, and material settings should be reviewed before locking calibration values.',
                )
            )
        for sensor_id, offset in sorted(suggested_sensor_time_offset_updates.items()):
            recommendations.append(
                CalibrationRecommendation(
                    kind='sensor_time_offset_update',
                    target=sensor_id,
                    priority='high' if abs(offset) >= 2 else 'medium',
                    rationale=f'Calibration alignment suggests sensor `{sensor_id}` should use time offset {offset} step(s).',
                    value=offset,
                    unit='steps',
                )
            )
        if unmatched_sensor_ids:
            recommendations.append(
                CalibrationRecommendation(
                    kind='sensor_mapping_review',
                    target='metadata',
                    priority='high',
                    rationale=f'Unmatched sensors were found: {unmatched_sensor_ids}. Receiver mapping or scenario receiver definitions need review.',
                    value=len(unmatched_sensor_ids),
                    unit='count',
                )
            )
        if outlier_rejected_sample_count > 0:
            recommendations.append(
                CalibrationRecommendation(
                    kind='outlier_review',
                    target='measurements',
                    priority='medium',
                    rationale=f'{outlier_rejected_sample_count} calibration sample(s) were rejected as outliers. Inspect measurement quality and sensor clocks.',
                    value=outlier_rejected_sample_count,
                    unit='count',
                )
            )
        for receiver_id in high_priority_receiver_ids:
            stats = receiver_stats.get(receiver_id)
            if stats is None:
                continue
            recommendations.append(
                CalibrationRecommendation(
                    kind='receiver_level_offset_candidate',
                    target=receiver_id,
                    priority='high' if stats.rmse_db >= max(1.5, overall_rmse * 1.5) else 'medium',
                    rationale=f'Receiver `{receiver_id}` has mean bias {stats.mean_bias_db:.3f} dB and RMSE {stats.rmse_db:.3f} dB, so it is a priority review point for local calibration or scene mismatch analysis.',
                    value=stats.recommended_offset_db,
                    unit='dB',
                )
            )
        return recommendations

    def _load_simulation_histories(self, result_summary: RunResultSummary) -> dict[str, list[float]]:
        histories: dict[str, list[float]] = {}
        for receiver_id, file_path in result_summary.receiver_history_files.items():
            histories[receiver_id] = self._read_receiver_history(file_path)
        return histories

    def _read_receiver_history(self, path: str | Path) -> list[float]:
        values: list[float] = []
        with Path(path).open('r', encoding='utf-8', newline='') as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                values.append(float(row['value_db']))
        return values
