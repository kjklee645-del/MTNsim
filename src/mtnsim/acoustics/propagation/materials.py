from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(slots=True)
class MaterialContext:
    reflection_loss_db: float = 0.0
    diffraction_loss_db: float = 0.0
    absorption_coefficient: float = 0.0
    allows_reflection: bool = True
    allows_diffraction: bool = True


def material_bonus_db(
    reflection_loss_db: float,
    diffraction_loss_db: float,
    absorption_coefficient: float,
    allows_reflection: bool,
    allows_diffraction: bool,
) -> float:
    context = MaterialContext(
        reflection_loss_db=reflection_loss_db,
        diffraction_loss_db=diffraction_loss_db,
        absorption_coefficient=absorption_coefficient,
        allows_reflection=allows_reflection,
        allows_diffraction=allows_diffraction,
    )
    transmission = transmission_loss_db(context)
    edge_blocking = 1.0 - edge_efficiency(context)
    absorption = _clamp(context.absorption_coefficient, 0.0, 1.0)
    return min((transmission * 0.11) + (edge_blocking * 0.9) + (absorption * 1.2), 3.0)


def shielding_material_correction_db(context: MaterialContext | None = None, shielding_context=None) -> float:
    if context is None:
        return 0.0
    transmission = transmission_loss_db(context)
    absorption = _clamp(context.absorption_coefficient, 0.0, 1.0)
    edge_blocking = 1.0 - edge_efficiency(context)

    geometry_factor = 1.0
    centrality = 1.0
    if shielding_context is not None:
        geometry_factor += min(shielding_context.height_excess_meters * 0.05, 0.55)
        geometry_factor += min(shielding_context.path_excess_meters / 24.0, 0.65)
        centrality = max(0.65, 1.0 - abs(shielding_context.intersection_ratio - 0.5) * 1.1)

    attenuation = ((transmission * 0.16) + (absorption * 0.9) + (edge_blocking * 0.7)) * geometry_factor * centrality
    return -min(attenuation, 5.0)


def reflection_material_correction_db(context: MaterialContext | None = None, reflection_context=None) -> float:
    if context is None:
        return 0.0
    if not context.allows_reflection:
        return -3.5

    reflectivity = surface_reflectivity(context)
    hardness = surface_hardness(context)
    scattering = scattering_factor(context)

    alignment = reflection_context.normal_alignment if reflection_context is not None else 0.6
    segment_fraction = reflection_context.segment_fraction if reflection_context is not None else 0.5
    extra_path = reflection_context.extra_path_meters if reflection_context is not None else 0.0

    centrality = max(0.55, 1.0 - abs(segment_fraction - 0.5) * 1.0)
    extra_path_penalty = min(extra_path / 90.0, 0.9)

    correction = (
        ((reflectivity - 0.45) * 1.7)
        + ((hardness - 0.5) * 0.6)
        + ((alignment - 0.5) * 0.8)
        + ((centrality - 0.7) * 0.4)
        - (scattering * 0.8)
        - extra_path_penalty
    )
    return _clamp(correction, -2.5, 0.8)


def diffraction_material_correction_db(context: MaterialContext | None = None, diffraction_context=None, shielding_context=None) -> float:
    if context is None:
        return 0.0
    if not context.allows_diffraction:
        return -2.8

    efficiency = edge_efficiency(context)
    absorption = _clamp(context.absorption_coefficient, 0.0, 1.0)
    transmission = transmission_loss_db(context)

    fresnel = diffraction_context.fresnel_number if diffraction_context is not None else 0.0
    path_excess = diffraction_context.path_excess_meters if diffraction_context is not None else 0.0
    if path_excess <= 0.0 and shielding_context is not None:
        path_excess = shielding_context.path_excess_meters

    correction = (
        ((efficiency - 0.45) * 1.6)
        + (min(fresnel / 4.0, 1.0) * 0.35)
        - min(path_excess / 25.0, 0.7)
        - (absorption * 0.7)
        - (min(transmission / 14.0, 1.0) * 0.3)
    )
    return _clamp(correction, -2.2, 0.7)


def material_correction_db(context: MaterialContext | None = None, shielding_context=None) -> float:
    if context is None:
        return 0.0
    return shielding_material_correction_db(context, shielding_context=shielding_context)


def transmission_loss_db(context: MaterialContext) -> float:
    absorption = _clamp(context.absorption_coefficient, 0.0, 1.0)
    reflection_term = _clamp(context.reflection_loss_db, 0.0, 12.0) * 0.55
    diffraction_term = _clamp(context.diffraction_loss_db, 0.0, 12.0) * 0.35
    absorption_term = absorption * 6.5
    non_diffracting_term = 0.8 if not context.allows_diffraction else 0.0
    return _clamp(1.5 + reflection_term + diffraction_term + absorption_term + non_diffracting_term, 1.0, 14.0)


def surface_hardness(context: MaterialContext) -> float:
    absorption = _clamp(context.absorption_coefficient, 0.0, 1.0)
    return _clamp(1.0 - (absorption * 0.82), 0.10, 1.0)


def surface_reflectivity(context: MaterialContext) -> float:
    if not context.allows_reflection:
        return 0.0
    hardness = surface_hardness(context)
    reflection_penalty = _clamp(context.reflection_loss_db / 13.0, 0.0, 0.8)
    absorption_penalty = _clamp(context.absorption_coefficient * 0.75, 0.0, 0.75)
    reflectivity = (hardness ** 1.1) * (1.0 - reflection_penalty) * (1.0 - absorption_penalty)
    reflectivity += max(hardness - 0.75, 0.0) * 0.20
    return _clamp(reflectivity, 0.03, 0.98)


def edge_efficiency(context: MaterialContext) -> float:
    if not context.allows_diffraction:
        return 0.0
    absorption = _clamp(context.absorption_coefficient, 0.0, 1.0)
    rigidity = 1.0 - (absorption * 0.40)
    diffraction_penalty = _clamp(context.diffraction_loss_db / 18.0, 0.0, 0.75)
    return _clamp(rigidity * (1.0 - diffraction_penalty), 0.04, 1.0)


def scattering_factor(context: MaterialContext) -> float:
    absorption = _clamp(context.absorption_coefficient, 0.0, 1.0)
    roughness = _clamp(context.diffraction_loss_db / 20.0, 0.0, 0.3)
    return _clamp(0.15 + (absorption * 0.55) + roughness, 0.15, 0.95)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))

