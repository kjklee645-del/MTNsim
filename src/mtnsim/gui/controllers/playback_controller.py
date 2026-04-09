from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import csv


@dataclass(slots=True)
class VehicleTracePoint:
    vehicle_id: str
    x: float
    y: float
    speed_mps: float
    vehicle_type: str


@dataclass(slots=True)
class PlaybackFrame:
    time_index: int
    sim_time_seconds: float
    vehicles: list[VehicleTracePoint] = field(default_factory=list)


@dataclass(slots=True)
class PlaybackDataset:
    trace_file: Path
    frames: list[PlaybackFrame]
    max_vehicle_count: int

    @property
    def frame_count(self) -> int:
        return len(self.frames)


class PlaybackController:
    def load_trace(self, trace_file: str | Path) -> PlaybackDataset:
        path = Path(trace_file)
        frames: list[PlaybackFrame] = []
        current_time_index: int | None = None
        current_sim_time = 0.0
        current_vehicles: list[VehicleTracePoint] = []
        max_vehicle_count = 0

        with path.open('r', encoding='utf-8', newline='') as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                time_index = int(row['time_index'])
                sim_time_seconds = float(row['sim_time_seconds'])
                point = VehicleTracePoint(
                    vehicle_id=row['vehicle_id'],
                    vehicle_type=row['vehicle_type'],
                    x=float(row['x']),
                    y=float(row['y']),
                    speed_mps=float(row['speed_mps']),
                )
                if current_time_index is None:
                    current_time_index = time_index
                    current_sim_time = sim_time_seconds
                if time_index != current_time_index:
                    frames.append(PlaybackFrame(time_index=current_time_index, sim_time_seconds=current_sim_time, vehicles=current_vehicles))
                    max_vehicle_count = max(max_vehicle_count, len(current_vehicles))
                    current_time_index = time_index
                    current_sim_time = sim_time_seconds
                    current_vehicles = []
                current_vehicles.append(point)

        if current_time_index is not None:
            frames.append(PlaybackFrame(time_index=current_time_index, sim_time_seconds=current_sim_time, vehicles=current_vehicles))
            max_vehicle_count = max(max_vehicle_count, len(current_vehicles))

        return PlaybackDataset(trace_file=path, frames=frames, max_vehicle_count=max_vehicle_count)
