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
    if hasattr(propagation_contexts, 'correction_for_pair'):
        context = propagation_contexts.correction_for_pair(poi_id, poi_position, vehicle_id, vehicle_position)
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
    if propagation_contexts is not None and hasattr(propagation_contexts, 'corrections_for_vehicle'):
        return _update_noise_grid_cpu_batched(
            grid_positions,
            vehicle_positions,
            vehicle_types,
            vehicle_speeds,
            coefficients,
            background_noise_db,
            max_area_meters,
            propagation_contexts,
        )

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


def _update_noise_grid_cpu_batched(
    grid_positions: dict[str, tuple[float, float, float]],
    vehicle_positions: dict[str, tuple[float, float]],
    vehicle_types: dict[str, str],
    vehicle_speeds: dict[str, float],
    coefficients: dict[str, tuple[float, float]],
    background_noise_db: float,
    max_area_meters: float,
    propagation_provider,
) -> dict[str, float]:
    background_power = 10 ** (background_noise_db / 10)
    total_powers = {poi_id: 0.0 for poi_id in grid_positions}
    vehicle_inside = {poi_id: False for poi_id in grid_positions}

    for vehicle_id, vehicle_position in vehicle_positions.items():
        a, b = coefficients[vehicle_types[vehicle_id]]
        speed = max(vehicle_speeds[vehicle_id], 0.1)
        pwl = a + (b * math.log10(3.6 * speed))
        samples = propagation_provider.corrections_for_vehicle(
            grid_positions,
            vehicle_id,
            vehicle_position,
            max_area_meters,
        )
        for poi_id, sample in samples.items():
            vehicle_inside[poi_id] = True
            attenuation_db = free_field_attenuation_db(sample.distance_meters)
            total_powers[poi_id] += (10 ** ((pwl - attenuation_db + sample.correction_db) / 10)) + background_power

    return {
        poi_id: (10 * math.log10(total_powers[poi_id]) if vehicle_inside[poi_id] else background_noise_db)
        for poi_id in grid_positions
    }


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

    if propagation_contexts is not None and hasattr(propagation_contexts, 'corrections_for_vehicle'):
        return _update_noise_grid_gpu_hybrid(
            grid_positions,
            vehicle_positions,
            vehicle_types,
            vehicle_speeds,
            coefficients,
            background_noise_db,
            max_area_meters,
            propagation_contexts,
        )

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


def _update_noise_grid_gpu_hybrid(
    grid_positions: dict[str, tuple[float, float, float]],
    vehicle_positions: dict[str, tuple[float, float]],
    vehicle_types: dict[str, str],
    vehicle_speeds: dict[str, float],
    coefficients: dict[str, tuple[float, float]],
    background_noise_db: float,
    max_area_meters: float,
    propagation_provider,
) -> dict[str, float]:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    poi_ids = list(grid_positions.keys())
    poi_index = {poi_id: index for index, poi_id in enumerate(poi_ids)}
    total_powers = torch.zeros((len(poi_ids),), dtype=torch.float32, device=device)
    vehicle_inside = torch.zeros((len(poi_ids),), dtype=torch.bool, device=device)
    background_power = float(10 ** (background_noise_db / 10))

    for vehicle_id, vehicle_position in vehicle_positions.items():
        a, b = coefficients[vehicle_types[vehicle_id]]
        speed = max(vehicle_speeds[vehicle_id], 0.1)
        pwl = a + (b * math.log10(3.6 * speed))
        samples = propagation_provider.corrections_for_vehicle(
            grid_positions,
            vehicle_id,
            vehicle_position,
            max_area_meters,
        )
        if not samples:
            continue
        indices = torch.tensor([poi_index[poi_id] for poi_id in samples.keys()], dtype=torch.long, device=device)
        distances = torch.tensor([sample.distance_meters for sample in samples.values()], dtype=torch.float32, device=device)
        corrections = torch.tensor([sample.correction_db for sample in samples.values()], dtype=torch.float32, device=device)
        attenuation_db = free_field_attenuation_torch_db(distances)
        powers = torch.pow(10.0, (pwl - attenuation_db + corrections) / 10.0) + background_power
        total_powers.index_add_(0, indices, powers)
        vehicle_inside[indices] = True

    background_fill = torch.full_like(total_powers, float(background_noise_db))
    result = torch.where(vehicle_inside, 10 * torch.log10(total_powers + 1e-6), background_fill)
    return {poi_id: float(value) for poi_id, value in zip(poi_ids, result.cpu().tolist())}
