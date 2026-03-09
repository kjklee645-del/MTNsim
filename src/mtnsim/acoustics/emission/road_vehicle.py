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
