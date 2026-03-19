from __future__ import annotations

import math
from dataclasses import dataclass

from mtnsim.acoustics.propagation.distance import free_field_attenuation_db, receiver_level_with_background


@dataclass(slots=True)
class VehicleNoiseProfile:
    a: float
    b: float

    def power_level(self, speed_mps: float) -> float:
        speed_mps = max(speed_mps, 0.1)
        return self.a + (self.b * math.log10(3.6 * speed_mps))


def calculate_3d_distance(poi_pos: tuple[float, float, float], vehicle_pos: tuple[float, float], vehicle_z: float = 0.3) -> float:
    dx = poi_pos[0] - vehicle_pos[0]
    dy = poi_pos[1] - vehicle_pos[1]
    dz = poi_pos[2] - vehicle_z
    return math.sqrt((dx * dx) + (dy * dy) + (dz * dz))


def attenuation(distance: float) -> float:
    return free_field_attenuation_db(distance)


def receiver_level(power_level: float, distance: float, background_noise_db: float) -> float:
    return receiver_level_with_background(power_level, free_field_attenuation_db(distance), 0.0, background_noise_db)


def resolve_heading_vector(previous_position: tuple[float, float] | None, current_position: tuple[float, float]) -> tuple[float, float] | None:
    if previous_position is None:
        return None
    dx = current_position[0] - previous_position[0]
    dy = current_position[1] - previous_position[1]
    norm = math.hypot(dx, dy)
    if norm < 1e-6:
        return None
    return (dx / norm, dy / norm)


def directional_gain_db(
    target_position_xy: tuple[float, float],
    vehicle_position_xy: tuple[float, float],
    heading_vector: tuple[float, float] | None,
    *,
    mode: str = 'isotropic',
    strength_db: float = 0.0,
    wedge_angle_deg: float = 70.0,
) -> float:
    if heading_vector is None or mode == 'isotropic' or strength_db <= 0.0:
        return 0.0

    target_dx = target_position_xy[0] - vehicle_position_xy[0]
    target_dy = target_position_xy[1] - vehicle_position_xy[1]
    target_norm = math.hypot(target_dx, target_dy)
    if target_norm < 1e-6:
        return 0.0

    target_dir = (target_dx / target_norm, target_dy / target_norm)
    dot = max(-1.0, min(1.0, (heading_vector[0] * target_dir[0]) + (heading_vector[1] * target_dir[1])))
    angle = math.acos(dot)
    half_span = math.radians(max(10.0, min(170.0, wedge_angle_deg))) * 0.5

    if mode == 'wedge':
        if angle <= half_span:
            return 0.0
        ratio = min(1.0, (angle - half_span) / max(math.pi - half_span, 1e-6))
        return -strength_db * ratio

    if mode == 'dual_wedge':
        mirrored_angle = min(angle, abs(math.pi - angle))
        if mirrored_angle <= half_span:
            return 0.0
        ratio = min(1.0, (mirrored_angle - half_span) / max((math.pi * 0.5) - half_span, 1e-6))
        return -strength_db * ratio

    return 0.0
