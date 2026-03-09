from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import importlib.util
import os
import sys


def _candidate_sumo_tool_paths() -> list[Path]:
    candidates: list[Path] = []
    sumo_home = os.environ.get("SUMO_HOME")
    if sumo_home:
        candidates.append(Path(sumo_home) / "tools")

    common_roots = [
        Path(r"C:\Program Files (x86)\Eclipse\Sumo"),
        Path(r"C:\Program Files\Eclipse\Sumo"),
    ]
    for root in common_roots:
        candidates.append(root / "tools")
    return candidates


def _ensure_traci_importable() -> None:
    if importlib.util.find_spec("traci") is not None:
        return
    for tool_path in _candidate_sumo_tool_paths():
        if tool_path.exists() and str(tool_path) not in sys.path:
            sys.path.append(str(tool_path))
            if importlib.util.find_spec("traci") is not None:
                return


_ensure_traci_importable()

try:
    import traci
except ImportError:  # pragma: no cover
    traci = None


@dataclass(slots=True)
class VehicleSnapshot:
    vehicle_id: str
    vehicle_type: str
    position: tuple[float, float]
    speed_mps: float


class SumoAdapter:
    def __init__(self) -> None:
        self._started = False

    def _require_traci(self) -> None:
        if traci is None:
            raise RuntimeError("traci is required for SUMO integration")

    def start(self, sumo_config: str | Path, binary: str = "sumo") -> None:
        self._require_traci()
        traci.start([binary, "-c", str(sumo_config)])
        self._started = True

    def close(self) -> None:
        if self._started and traci is not None:
            traci.close()
        self._started = False

    def simulation_step(self) -> None:
        self._require_traci()
        traci.simulationStep()

    def simulation_time(self) -> float:
        self._require_traci()
        return float(traci.simulation.getTime())

    def vehicle_ids(self) -> list[str]:
        self._require_traci()
        return list(traci.vehicle.getIDList())

    def vehicle_position(self, vehicle_id: str) -> tuple[float, float]:
        self._require_traci()
        return traci.vehicle.getPosition(vehicle_id)

    def vehicle_speed(self, vehicle_id: str) -> float:
        self._require_traci()
        return float(traci.vehicle.getSpeed(vehicle_id))

    def vehicle_type(self, vehicle_id: str) -> str:
        self._require_traci()
        return str(traci.vehicle.getTypeID(vehicle_id))

    def lane_index(self, vehicle_id: str) -> int:
        self._require_traci()
        return int(traci.vehicle.getLaneIndex(vehicle_id))

    def road_id(self, vehicle_id: str) -> str:
        self._require_traci()
        return str(traci.vehicle.getRoadID(vehicle_id))

    def lane_count(self, vehicle_id: str) -> int:
        self._require_traci()
        road_id = self.road_id(vehicle_id)
        if not road_id or road_id.startswith(':'):
            return 1
        return max(1, int(traci.edge.getLaneNumber(road_id)))

    def set_lane_change_mode(self, vehicle_id: str, mode: int) -> None:
        self._require_traci()
        traci.vehicle.setLaneChangeMode(vehicle_id, mode)

    def change_lane(self, vehicle_id: str, lane_index: int, duration: float) -> None:
        self._require_traci()
        traci.vehicle.changeLane(vehicle_id, lane_index, duration)

    def set_speed(self, vehicle_id: str, speed_mps: float) -> None:
        self._require_traci()
        traci.vehicle.setSpeed(vehicle_id, speed_mps)

    def add_vehicle(self, vehicle_id: str, route_id: str, type_id: str, depart: str, depart_speed: float | None = None) -> None:
        self._require_traci()
        traci.vehicle.add(vehicle_id, route_id, typeID=type_id, depart=depart, departSpeed=depart_speed)

    def snapshots(self) -> list[VehicleSnapshot]:
        return [
            VehicleSnapshot(
                vehicle_id=vehicle_id,
                vehicle_type=self.vehicle_type(vehicle_id),
                position=self.vehicle_position(vehicle_id),
                speed_mps=self.vehicle_speed(vehicle_id),
            )
            for vehicle_id in self.vehicle_ids()
        ]
