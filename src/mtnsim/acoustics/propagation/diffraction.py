from __future__ import annotations

from dataclasses import dataclass

from mtnsim.acoustics.propagation.shielding import ShieldingContext


@dataclass(slots=True)
class DiffractionContext:
    enabled: bool = False
    gain_db: float = 0.0
    barrier_id: str | None = None
    excess_height_meters: float = 0.0
    source_receiver_distance_meters: float = 0.0
    path_excess_meters: float = 0.0


def build_diffraction_context(context: ShieldingContext | None = None) -> DiffractionContext | None:
    if context is None or not context.is_blocked or not context.allows_diffraction:
        return None

    distance = max(context.source_receiver_distance_meters, 1.0)
    excess_height = max(context.height_excess_meters, 0.0)
    path_excess = max(context.path_excess_meters, 0.0)

    gain = 4.8
    gain -= min(excess_height * 1.10, 2.4)
    gain -= min(path_excess * 12.0, 2.4)
    gain -= min((distance / 250.0), 1.0)
    gain -= min(max(context.diffraction_loss_db, 0.0) * 0.20, 1.2)
    gain -= min(max(context.absorption_coefficient, 0.0) * 1.4, 0.9)
    gain = max(0.0, min(gain, max(context.attenuation_db - 0.5, 0.0)))

    if gain <= 0.0:
        return None

    return DiffractionContext(
        enabled=True,
        gain_db=gain,
        barrier_id=context.barrier_id,
        excess_height_meters=excess_height,
        source_receiver_distance_meters=distance,
        path_excess_meters=path_excess,
    )


def diffraction_correction_db(context: DiffractionContext | None = None) -> float:
    if context is None or not context.enabled:
        return 0.0
    return max(0.0, context.gain_db)
