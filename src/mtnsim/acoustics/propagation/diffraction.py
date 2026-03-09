from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DiffractionContext:
    enabled: bool = False
    attenuation_db: float = 0.0


def diffraction_correction_db(context: DiffractionContext | None = None) -> float:
    if context is None or not context.enabled:
        return 0.0
    return -abs(context.attenuation_db)
