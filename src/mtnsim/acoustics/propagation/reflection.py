from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ReflectionContext:
    enabled: bool = False
    gain_db: float = 0.0


def reflection_correction_db(context: ReflectionContext | None = None) -> float:
    if context is None or not context.enabled:
        return 0.0
    return context.gain_db
