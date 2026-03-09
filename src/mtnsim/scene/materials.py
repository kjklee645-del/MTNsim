from __future__ import annotations

from dataclasses import dataclass

from mtnsim.schemas.scenario import PropagationProperties


@dataclass(frozen=True, slots=True)
class MaterialDefaults:
    reflection_loss_db: float
    diffraction_loss_db: float
    absorption_coefficient: float
    allows_reflection: bool
    allows_diffraction: bool


_DEFAULTS: dict[str, dict[str, MaterialDefaults]] = {
    'noise_barrier': {
        'generic': MaterialDefaults(3.0, 2.0, 0.30, True, True),
        'concrete': MaterialDefaults(2.0, 1.5, 0.18, True, True),
        'absorptive_panel': MaterialDefaults(5.0, 2.0, 0.65, True, True),
        'metal': MaterialDefaults(1.5, 1.0, 0.10, True, True),
    },
    'building': {
        'generic': MaterialDefaults(2.5, 1.5, 0.15, True, True),
        'concrete': MaterialDefaults(2.0, 1.0, 0.12, True, True),
        'glass': MaterialDefaults(1.0, 1.0, 0.05, True, False),
        'brick': MaterialDefaults(2.5, 1.5, 0.18, True, True),
    },
}


def resolve_propagation_properties(
    object_type: str,
    material_name: str,
    overrides: PropagationProperties | None = None,
) -> PropagationProperties:
    material_group = _DEFAULTS.get(object_type, {})
    defaults = material_group.get(material_name, material_group.get('generic', MaterialDefaults(3.0, 2.0, 0.20, True, True)))
    overrides = overrides or PropagationProperties()
    return PropagationProperties(
        reflection_loss_db=_pick(overrides.reflection_loss_db, defaults.reflection_loss_db),
        diffraction_loss_db=_pick(overrides.diffraction_loss_db, defaults.diffraction_loss_db),
        absorption_coefficient=_pick(overrides.absorption_coefficient, defaults.absorption_coefficient),
        allows_reflection=_pick(overrides.allows_reflection, defaults.allows_reflection),
        allows_diffraction=_pick(overrides.allows_diffraction, defaults.allows_diffraction),
    )


def _pick(value, fallback):
    if value is None:
        return fallback
    return value