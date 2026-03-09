from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BarrierSegment:
    id: str
    x1: float
    y1: float
    x2: float
    y2: float
    height_meters: float
    attenuation_db: float


@dataclass(slots=True)
class ShieldingContext:
    is_blocked: bool = False
    attenuation_db: float = 0.0
    barrier_id: str | None = None


def _cross(ax: float, ay: float, bx: float, by: float) -> float:
    return (ax * by) - (ay * bx)


def segment_intersection_parameter(
    source_xy: tuple[float, float],
    receiver_xy: tuple[float, float],
    barrier_start_xy: tuple[float, float],
    barrier_end_xy: tuple[float, float],
    epsilon: float = 1e-9,
) -> float | None:
    px, py = source_xy
    rx = receiver_xy[0] - px
    ry = receiver_xy[1] - py
    qx, qy = barrier_start_xy
    sx = barrier_end_xy[0] - qx
    sy = barrier_end_xy[1] - qy

    r_cross_s = _cross(rx, ry, sx, sy)
    q_minus_p_x = qx - px
    q_minus_p_y = qy - py
    if abs(r_cross_s) <= epsilon:
        return None

    t = _cross(q_minus_p_x, q_minus_p_y, sx, sy) / r_cross_s
    u = _cross(q_minus_p_x, q_minus_p_y, rx, ry) / r_cross_s
    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        return t
    return None


def build_shielding_context(
    receiver_pos: tuple[float, float, float],
    source_pos: tuple[float, float],
    barriers: list[BarrierSegment],
    source_height_meters: float = 0.3,
) -> ShieldingContext | None:
    best_context: ShieldingContext | None = None
    receiver_xy = (receiver_pos[0], receiver_pos[1])
    receiver_height = receiver_pos[2]

    for barrier in barriers:
        t = segment_intersection_parameter(
            source_xy=source_pos,
            receiver_xy=receiver_xy,
            barrier_start_xy=(barrier.x1, barrier.y1),
            barrier_end_xy=(barrier.x2, barrier.y2),
        )
        if t is None:
            continue

        line_height = source_height_meters + (t * (receiver_height - source_height_meters))
        if barrier.height_meters < line_height:
            continue

        if best_context is None or barrier.attenuation_db > best_context.attenuation_db:
            best_context = ShieldingContext(
                is_blocked=True,
                attenuation_db=barrier.attenuation_db,
                barrier_id=barrier.id,
            )

    return best_context


def shielding_correction_db(context: ShieldingContext | None = None) -> float:
    if context is None:
        return 0.0
    return -abs(context.attenuation_db) if context.is_blocked else 0.0