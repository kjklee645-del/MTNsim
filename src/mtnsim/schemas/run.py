from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class RunSummary:
    run_id: str
    project: str
    scenario: str
    max_steps: int
    max_vehicles: int
    receiver_count: int
    lane_change_mode: str
    lane_change_strategy: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
