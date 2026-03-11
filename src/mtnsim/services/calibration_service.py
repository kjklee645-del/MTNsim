from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import csv
import math

from mtnsim.io.measurements import read_measurement_metadata, read_measurement_samples
from mtnsim.io.result_store import write_calibration_summary
from mtnsim.schemas.calibration import CalibrationSummary, ReceiverCalibrationStats
from mtnsim.schemas.project import ProjectManifest
from mtnsim.schemas.results import RunResultSummary


class CalibrationService:
    def calibrate_run(
        self,
        result_summary: RunResultSummary,
        measurement_file: str | Path,
        measurement_metadata_file: str | Path | None = None,
        time_step_seconds: float = 1.0,
    ) -> CalibrationSummary:
        measurement_path = Path(measurement_file)
        read_result = read_measurement_samples(measurement_path, time_step_seconds=time_step_seconds)
        metadata_path = Path(measurement_metadata_file) if measurement_metadata_file else None
        metadata = read_measurement_metadata(metadata_path) if metadata_path else {}
        simulations = self._load_simulation_histories(result_summary)

        grouped_errors: dict[str, list[float]] = defaultdict(list)
        aligned_sample_count = 0
        skipped_sample_count = read_result.skipped_row_count
        unmatched_sensor_ids: set[str] = set()

        for sample in read_result.samples:
            mapping = metadata.get(sample.sensor_id) or metadata.get(sample.receiver_id)
            if mapping is not None and not mapping.enabled:
                skipped_sample_count += 1
                continue

            simulation_receiver_id = mapping.simulation_receiver_id if mapping else sample.receiver_id
            simulation_time_index = sample.time_index + (mapping.time_offset_steps if mapping else 0)

            if mapping is not None:
                if mapping.start_time_index is not None and simulation_time_index < mapping.start_time_index:
                    skipped_sample_count += 1
                    continue
                if mapping.end_time_index is not None and simulation_time_index > mapping.end_time_index:
                    skipped_sample_count += 1
                    continue

            receiver_history = simulations.get(simulation_receiver_id)
            if receiver_history is None:
                unmatched_sensor_ids.add(sample.sensor_id)
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
        for receiver_id, errors in grouped_errors.items():
            if not errors:
                continue
            all_errors.extend(errors)
            mean_bias = sum(errors) / len(errors)
            mae = sum(abs(error) for error in errors) / len(errors)
            rmse = math.sqrt(sum((error * error) for error in errors) / len(errors))
            receiver_stats[receiver_id] = ReceiverCalibrationStats(
                receiver_id=receiver_id,
                sample_count=len(errors),
                mean_bias_db=mean_bias,
                mae_db=mae,
                rmse_db=rmse,
                recommended_offset_db=-mean_bias,
            )

        if all_errors:
            overall_mean_bias = sum(all_errors) / len(all_errors)
            overall_mae = sum(abs(error) for error in all_errors) / len(all_errors)
            overall_rmse = math.sqrt(sum((error * error) for error in all_errors) / len(all_errors))
        else:
            overall_mean_bias = 0.0
            overall_mae = 0.0
            overall_rmse = 0.0

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
        )

    def calibrate_and_store(
        self,
        result_summary: RunResultSummary,
        measurement_file: str | Path,
        measurement_metadata_file: str | Path | None = None,
        time_step_seconds: float = 1.0,
    ) -> tuple[CalibrationSummary, Path]:
        summary = self.calibrate_run(
            result_summary,
            measurement_file,
            measurement_metadata_file=measurement_metadata_file,
            time_step_seconds=time_step_seconds,
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
