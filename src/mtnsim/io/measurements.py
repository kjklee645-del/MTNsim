from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv

from mtnsim.schemas.calibration import MeasurementSample, MeasurementSensorMetadata


@dataclass(slots=True)
class MeasurementReadResult:
    samples: list[MeasurementSample]
    skipped_row_count: int


def read_measurement_samples(path: str | Path, time_step_seconds: float = 1.0) -> MeasurementReadResult:
    samples: list[MeasurementSample] = []
    skipped = 0
    with Path(path).open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                value_raw = row.get('value_db')
                if value_raw in (None, ''):
                    skipped += 1
                    continue
                sensor_id = str(row.get('sensor_id') or row.get('receiver_id') or '').strip()
                receiver_id = str(row.get('receiver_id') or sensor_id).strip()
                if not sensor_id or not receiver_id:
                    skipped += 1
                    continue
                if row.get('time_index') not in (None, ''):
                    time_index = int(row['time_index'])
                elif row.get('time_seconds') not in (None, ''):
                    time_index = round(float(row['time_seconds']) / time_step_seconds)
                else:
                    skipped += 1
                    continue
                samples.append(
                    MeasurementSample(
                        sensor_id=sensor_id,
                        receiver_id=receiver_id,
                        time_index=time_index,
                        value_db=float(value_raw),
                    )
                )
            except (TypeError, ValueError):
                skipped += 1
    return MeasurementReadResult(samples=samples, skipped_row_count=skipped)


def read_measurement_metadata(path: str | Path) -> dict[str, MeasurementSensorMetadata]:
    metadata: dict[str, MeasurementSensorMetadata] = {}
    with Path(path).open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            sensor_id = str(row.get('sensor_id') or '').strip()
            simulation_receiver_id = str(row.get('simulation_receiver_id') or '').strip()
            if not sensor_id or not simulation_receiver_id:
                continue
            metadata[sensor_id] = MeasurementSensorMetadata(
                sensor_id=sensor_id,
                simulation_receiver_id=simulation_receiver_id,
                time_offset_steps=int(row.get('time_offset_steps') or 0),
                enabled=_parse_bool(row.get('enabled'), True),
                start_time_index=_parse_optional_int(row.get('start_time_index')),
                end_time_index=_parse_optional_int(row.get('end_time_index')),
            )
    return metadata


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None or value == '':
        return default
    return str(value).strip().lower() in {'1', 'true', 'yes', 'y'}


def _parse_optional_int(value: str | None) -> int | None:
    if value is None or value == '':
        return None
    return int(value)
