from __future__ import annotations

from dataclasses import dataclass

from mtnsim.acoustics.propagation.diffraction import DiffractionContext, diffraction_correction_db
from mtnsim.acoustics.propagation.materials import (
    MaterialContext,
    diffraction_material_correction_db,
    reflection_material_correction_db,
    shielding_material_correction_db,
)
from mtnsim.acoustics.propagation.reflection import ReflectionContext, reflection_correction_db
from mtnsim.acoustics.propagation.shielding import ShieldingContext, shielding_correction_db


@dataclass(slots=True)
class PropagationContext:
    shielding: ShieldingContext | None = None
    reflection: ReflectionContext | None = None
    diffraction: DiffractionContext | None = None
    material: MaterialContext | None = None
    ground_correction_db: float = 0.0
    vegetation_correction_db: float = 0.0


def total_propagation_correction_db(context: PropagationContext | None = None) -> float:
    if context is None:
        return 0.0

    total = 0.0
    total += shielding_correction_db(context.shielding)
    total += reflection_correction_db(context.reflection)
    total += diffraction_correction_db(context.diffraction)
    total += context.ground_correction_db
    total += context.vegetation_correction_db

    if context.material is not None:
        if context.shielding is not None:
            total += shielding_material_correction_db(context.material, shielding_context=context.shielding)
        if context.reflection is not None:
            total += reflection_material_correction_db(context.material, reflection_context=context.reflection)
        if context.diffraction is not None:
            total += diffraction_material_correction_db(
                context.material,
                diffraction_context=context.diffraction,
                shielding_context=context.shielding,
            )

    return total
