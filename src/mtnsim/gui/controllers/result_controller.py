from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv

from mtnsim.schemas.results import RunResultSummary


@dataclass(slots=True)
class ReceiverSeries:
    receiver_id: str
    points: list[tuple[int, float]]


class ResultController:
    def load_result_summary(self, result_summary_path: str | Path) -> RunResultSummary:
        return RunResultSummary.load(result_summary_path)

    def load_receiver_series(self, receiver_id: str, csv_path: str | Path) -> ReceiverSeries:
        points: list[tuple[int, float]] = []
        with Path(csv_path).open('r', encoding='utf-8', newline='') as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                points.append((int(row['time_index']), float(row['value_db'])))
        return ReceiverSeries(receiver_id=receiver_id, points=points)
