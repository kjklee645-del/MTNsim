from __future__ import annotations

from dataclasses import dataclass
import math

from mtnsim.acoustics.propagation.shielding import ShieldingContext


@dataclass(slots=True)
class DiffractionContext:
    enabled: bool = False
    gain_db: float = 0.0
    barrier_id: str | None = None
    excess_height_meters: float = 0.0
    source_receiver_distance_meters: float = 0.0
    path_excess_meters: float = 0.0
    knife_edge_loss_db: float = 0.0
    fresnel_number: float = 0.0


def build_diffraction_context(
    context: ShieldingContext | None = None,
    wavelength_meters: float = 0.68,
) -> DiffractionContext | None:
    if context is None or not context.is_blocked or not context.allows_diffraction:
        return None

    d1 = max(context.source_to_edge_distance_meters, 0.1)
    d2 = max(context.edge_to_receiver_distance_meters, 0.1)
    delta = max(context.path_excess_meters, 0.0)
    fresnel_number = _fresnel_number(d1=d1, d2=d2, path_excess_meters=delta, wavelength_meters=wavelength_meters)
    knife_edge_loss = _knife_edge_loss_db(fresnel_number)

    geometric_regain = max(context.attenuation_db - knife_edge_loss, 0.0)
    geometric_regain -= min(context.height_excess_meters * 0.30, 1.6)
    geometric_regain = max(0.0, min(geometric_regain, max(context.attenuation_db - 0.5, 0.0)))
    if geometric_regain <= 0.0:
        return None

    return DiffractionContext(
        enabled=True,
        gain_db=geometric_regain,
        barrier_id=context.barrier_id,
        excess_height_meters=context.height_excess_meters,
        source_receiver_distance_meters=context.source_receiver_distance_meters,
        path_excess_meters=delta,
        knife_edge_loss_db=knife_edge_loss,
        fresnel_number=fresnel_number,
    )


def diffraction_correction_db(context: DiffractionContext | None = None) -> float:
    if context is None or not context.enabled:
        return 0.0
    return max(0.0, context.gain_db)


def _fresnel_number(d1: float, d2: float, path_excess_meters: float, wavelength_meters: float) -> float:
    if path_excess_meters <= 0.0:
        return 0.0
    term = (2.0 / wavelength_meters) * path_excess_meters * ((d1 + d2) / (d1 * d2))
    return math.sqrt(max(term, 0.0))


def _knife_edge_loss_db(fresnel_number: float) -> float:
    if fresnel_number <= 0.0:
        return 0.0
    return 6.9 + (20.0 * math.log10(math.sqrt(((fresnel_number - 0.1) ** 2) + 1.0) + fresnel_number - 0.1))
