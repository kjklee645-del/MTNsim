from __future__ import annotations

from dataclasses import dataclass, field
import math
import random


@dataclass(slots=True)
class LaneChangeState:
    lane_change_vehicle_set: set[str] = field(default_factory=set)
    vehicle_lane_change_positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    vehicle_start_positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    speed_reduced_vehicles: set[str] = field(default_factory=set)
    original_speeds: dict[str, float] = field(default_factory=dict)
    restore_times: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class VehicleDeploymentConfig:
    vehicle_types: list[str]
    vehicle_weights: list[float]
    route_types: list[str]
    start_mode: str
    vehicle_interval_seconds: float
    max_simulation_steps: int
    lane_change_ratio: float


def _clamp_lane_index(sim, vehicle_id: str, requested_lane: int) -> int:
    lane_count = sim.lane_count(vehicle_id)
    return max(0, min(requested_lane, lane_count - 1))


def disable_lane_change(sim, vehicle_id: str) -> None:
    sim.set_lane_change_mode(vehicle_id, 0b000000000000)


def apply_speed_after_distance(
    sim,
    state: LaneChangeState,
    vehicle_id: str,
    current_pos: tuple[float, float],
    distance_threshold: float,
    target_speed: float,
    enabled: bool = True,
) -> None:
    if not enabled:
        return
    if vehicle_id not in state.vehicle_start_positions:
        state.vehicle_start_positions[vehicle_id] = current_pos
        return
    if vehicle_id in state.speed_reduced_vehicles:
        return
    start_x, start_y = state.vehicle_start_positions[vehicle_id]
    current_x, current_y = current_pos
    traveled = math.hypot(current_x - start_x, current_y - start_y)
    if traveled >= distance_threshold:
        sim.set_speed(vehicle_id, target_speed)
        state.speed_reduced_vehicles.add(vehicle_id)


def restore_vehicle_speeds(sim, state: LaneChangeState) -> None:
    current_time = sim.simulation_time()
    for vehicle_id in list(state.restore_times.keys()):
        if current_time >= state.restore_times[vehicle_id]:
            original_speed = state.original_speeds.get(vehicle_id, 8.34)
            sim.set_speed(vehicle_id, original_speed)
            del state.restore_times[vehicle_id]
            state.original_speeds.pop(vehicle_id, None)


def enforce_lane_change(
    sim,
    state: LaneChangeState,
    lane_index: int,
    designated_lane: int,
    min_x: float,
    max_x: float,
    min_y: float,
    max_y: float,
    check_radius: float = 10,
    force_change: bool = False,
    mode: str = "variable",
    target_positions: list[tuple[float, float]] | None = None,
    constant_speed: float | None = None,
    speed_change: float | None = None,
    restore_time: float = 30,
) -> None:
    for vehicle_id in sim.vehicle_ids():
        if vehicle_id in state.lane_change_vehicle_set:
            vehicle_x, vehicle_y = sim.vehicle_position(vehicle_id)
            if vehicle_id not in state.vehicle_lane_change_positions:
                if mode == "fixed":
                    target_x, target_y = 800, 0
                elif mode == "variable":
                    vehicle_number = len(state.vehicle_lane_change_positions)
                    target_x = max(0, 800 - (vehicle_number * 10))
                    target_y = 0
                elif mode == "custom":
                    if not target_positions:
                        raise ValueError("target_positions is required for custom lane-change mode")
                    target_x, target_y = target_positions[len(state.vehicle_lane_change_positions) % len(target_positions)]
                elif mode == "random":
                    target_x = random.uniform(min_x, max_x)
                    target_y = random.uniform(min_y, max_y)
                else:
                    raise ValueError(f"unsupported lane-change mode: {mode}")
                state.vehicle_lane_change_positions[vehicle_id] = (target_x, target_y)
            else:
                target_x, target_y = state.vehicle_lane_change_positions[vehicle_id]

            distance = math.hypot(vehicle_x - target_x, vehicle_y - target_y)
            if distance <= check_radius:
                effective_lane = _clamp_lane_index(sim, vehicle_id, lane_index)
                if force_change:
                    sim.set_lane_change_mode(vehicle_id, 0b000000000000)
                current_speed = sim.vehicle_speed(vehicle_id)
                state.original_speeds.setdefault(vehicle_id, current_speed)
                if constant_speed is not None:
                    sim.set_speed(vehicle_id, constant_speed)
                elif speed_change is not None:
                    sim.set_speed(vehicle_id, max(0.1, current_speed + speed_change))
                    state.restore_times[vehicle_id] = sim.simulation_time() + restore_time
                if sim.lane_index(vehicle_id) != effective_lane:
                    sim.change_lane(vehicle_id, effective_lane, 30)
        else:
            effective_designated_lane = _clamp_lane_index(sim, vehicle_id, designated_lane)
            if sim.lane_index(vehicle_id) != effective_designated_lane:
                sim.change_lane(vehicle_id, effective_designated_lane, 30)


def add_vehicle(
    sim,
    state: LaneChangeState,
    deployed_vehicles: int,
    time_step: int,
    config: VehicleDeploymentConfig,
    constant_speed: float | None = None,
) -> str:
    new_vehicle_id = f"vehicle_{deployed_vehicles}"
    vehicle_type = random.choices(config.vehicle_types, config.vehicle_weights)[0]
    route_type = random.choice(config.route_types)
    if config.start_mode == "random":
        depart_time = random.randint(time_step, config.max_simulation_steps)
    elif config.start_mode == "interval":
        depart_time = time_step + ((deployed_vehicles + 1) * int(config.vehicle_interval_seconds))
    else:
        raise ValueError("start_mode must be 'random' or 'interval'")
    sim.add_vehicle(new_vehicle_id, route_type, vehicle_type, str(depart_time), constant_speed)
    if constant_speed is not None:
        sim.set_speed(new_vehicle_id, constant_speed)
    if random.random() < config.lane_change_ratio:
        state.lane_change_vehicle_set.add(new_vehicle_id)
    return new_vehicle_id
