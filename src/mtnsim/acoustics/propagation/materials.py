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
    absorption = _clamp(absorption_coefficient, 0.0, 1.0)
    shielding_bonus = absorption * 3.0
    edge_bonus = min(max(diffraction_loss_db, 0.0) * 0.12, 1.0) if allows_diffraction else 0.4
    reflection_bonus = min(max(reflection_loss_db, 0.0) * 0.08, 0.6) if allows_reflection else 0.25
    return shielding_bonus + edge_bonus + reflection_bonus


def shielding_material_correction_db(context: MaterialContext | None = None) -> float:
    if context is None:
        return 0.0
    absorption = _clamp(context.absorption_coefficient, 0.0, 1.0)
    attenuation = (absorption * 2.8) + min(max(context.diffraction_loss_db, 0.0) * 0.10, 0.9)
    return -attenuation


def reflection_material_correction_db(context: MaterialContext | None = None) -> float:
    if context is None:
        return 0.0
    if not context.allows_reflection:
        return -3.0
    reflectivity = surface_reflectivity(context)
    if reflectivity <= 0.0:
        return -3.0
    return 10.0 * math.log10(reflectivity)


def diffraction_material_correction_db(context: MaterialContext | None = None) -> float:
    if context is None:
        return 0.0
    if not context.allows_diffraction:
        return -2.5
    efficiency = edge_efficiency(context)
    if efficiency <= 0.0:
        return -2.5
    return 10.0 * math.log10(efficiency)


def material_correction_db(context: MaterialContext | None = None) -> float:
    if context is None:
        return 0.0
    return shielding_material_correction_db(context)


def surface_reflectivity(context: MaterialContext) -> float:
    reflection_penalty = _clamp(context.reflection_loss_db / 12.0, 0.0, 0.95)
    absorption_penalty = _clamp(context.absorption_coefficient * 0.85, 0.0, 0.85)
    return _clamp(1.0 - reflection_penalty - absorption_penalty, 0.05, 1.0)


def edge_efficiency(context: MaterialContext) -> float:
    diffraction_penalty = _clamp(context.diffraction_loss_db / 14.0, 0.0, 0.9)
    absorption_penalty = _clamp(context.absorption_coefficient * 0.55, 0.0, 0.55)
    return _clamp(1.0 - diffraction_penalty - absorption_penalty, 0.08, 1.0)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))
