from __future__ import annotations

from dataclasses import dataclass

from mtnsim.acoustics.propagation.diffraction import DiffractionContext, diffraction_correction_db
from mtnsim.acoustics.propagation.reflection import ReflectionContext, reflection_correction_db
from mtnsim.acoustics.propagation.shielding import ShieldingContext, shielding_correction_db


@dataclass(slots=True)
class PropagationContext:
    shielding: ShieldingContext | None = None
    reflection: ReflectionContext | None = None
    diffraction: DiffractionContext | None = None


def total_propagation_correction_db(context: PropagationContext | None = None) -> float:
    if context is None:
        return 0.0
    return (
        shielding_correction_db(context.shielding)
        + reflection_correction_db(context.reflection)
        + diffraction_correction_db(context.diffraction)
    )
