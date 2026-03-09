from __future__ import annotations

from collections.abc import Callable
import math

from mtnsim.acoustics.emission.road_vehicle import calculate_3d_distance
from mtnsim.acoustics.propagation.correction import total_propagation_correction_db
from mtnsim.acoustics.propagation.distance import free_field_attenuation_db, free_field_attenuation_torch_db

try:
    import torch
except ImportError:  # pragma: no cover
    torch = None


PropagationProvider = Callable[[str, tuple[float, float, float], str, tuple[float, float]], object | None]


def _resolve_correction_db(
    propagation_contexts: dict[str, object] | PropagationProvider | None,
    poi_id: str,
    poi_position: tuple[float, float, float],
    vehicle_id: str,
    vehicle_position: tuple[float, float],
) -> float:
    if propagation_contexts is None:
        return 0.0
    if callable(propagation_contexts):
        context = propagation_contexts(poi_id, poi_position, vehicle_id, vehicle_position)
        return total_propagation_correction_db(context)
    return total_propagation_correction_db(propagation_contexts.get(poi_id))


def update_noise_grid_cpu(
    grid_positions: dict[str, tuple[float, float, float]],
    vehicle_positions: dict[str, tuple[float, float]],
    vehicle_types: dict[str, str],
    vehicle_speeds: dict[str, float],
    coefficients: dict[str, tuple[float, float]],
    background_noise_db: float,
    max_area_meters: float,
    propagation_contexts: dict[str, object] | PropagationProvider | None = None,
) -> dict[str, float]:
    values: dict[str, float] = {}
    background_power = 10 ** (background_noise_db / 10)
    for poi_id, poi_position in grid_positions.items():
        x, y, z = poi_position
        total_power = 0.0
        vehicle_inside = False
        for vehicle_id, vehicle_position in vehicle_positions.items():
            distance = calculate_3d_distance((x, y, z), vehicle_position)
            if distance > max_area_meters:
                continue
            vehicle_inside = True
            a, b = coefficients[vehicle_types[vehicle_id]]
            speed = max(vehicle_speeds[vehicle_id], 0.1)
            pwl = a + (b * math.log10(3.6 * speed))
            attenuation_db = free_field_attenuation_db(distance)
            correction_db = _resolve_correction_db(propagation_contexts, poi_id, poi_position, vehicle_id, vehicle_position)
            total_power += (10 ** ((pwl - attenuation_db + correction_db) / 10)) + background_power
        values[poi_id] = 10 * math.log10(total_power) if vehicle_inside else background_noise_db
    return values


def update_noise_grid_gpu(
    grid_positions: dict[str, tuple[float, float, float]],
    vehicle_positions: dict[str, tuple[float, float]],
    vehicle_types: dict[str, str],
    vehicle_speeds: dict[str, float],
    coefficients: dict[str, tuple[float, float]],
    background_noise_db: float,
    max_area_meters: float,
    propagation_contexts: dict[str, object] | PropagationProvider | None = None,
) -> dict[str, float]:
    if torch is None:
        raise RuntimeError("torch is required for GPU noise updates")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    poi_ids = list(grid_positions.keys())
    poi_positions = torch.tensor(list(grid_positions.values()), dtype=torch.float32, device=device)
    total_powers = torch.full((len(poi_positions),), 10 ** (background_noise_db / 10), dtype=torch.float32, device=device)

    if vehicle_positions:
        vehicle_position_tensor = torch.tensor([[x, y, 0.3] for x, y in vehicle_positions.values()], dtype=torch.float32, device=device)
        for vehicle_id, vehicle_pos in zip(vehicle_positions.keys(), vehicle_position_tensor):
            distances = torch.norm(poi_positions - vehicle_pos, dim=1)
            mask = distances <= max_area_meters
            if not mask.any():
                continue
            a, b = coefficients[vehicle_types[vehicle_id]]
            speed = max(vehicle_speeds[vehicle_id], 0.1)
            pwl = a + (b * math.log10(3.6 * speed))
            attenuation_db = free_field_attenuation_torch_db(distances[mask])
            total_powers[mask] += (10 ** ((pwl - attenuation_db) / 10)) + (10 ** (background_noise_db / 10))

    result = 10 * torch.log10(total_powers + 1e-6)
    return {poi_id: float(value) for poi_id, value in zip(poi_ids, result.cpu().tolist())}