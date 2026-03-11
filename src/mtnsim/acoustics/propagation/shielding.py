from __future__ import annotations

from dataclasses import dataclass
import math

from mtnsim.acoustics.propagation.materials import material_bonus_db


@dataclass(slots=True)
class BarrierSegment:
    id: str
    x1: float
    y1: float
    x2: float
    y2: float
    height_meters: float
    attenuation_db: float
    reflection_loss_db: float = 0.0
    diffraction_loss_db: float = 0.0
    absorption_coefficient: float = 0.0
    allows_reflection: bool = True
    allows_diffraction: bool = True


@dataclass(slots=True)
class ShieldingContext:
    is_blocked: bool = False
    attenuation_db: float = 0.0
    barrier_id: str | None = None
    reflection_loss_db: float = 0.0
    diffraction_loss_db: float = 0.0
    absorption_coefficient: float = 0.0
    allows_reflection: bool = True
    allows_diffraction: bool = True
    line_height_meters: float = 0.0
    height_excess_meters: float = 0.0
    source_receiver_distance_meters: float = 0.0
    intersection_ratio: float = 0.0
    path_excess_meters: float = 0.0
    source_to_edge_distance_meters: float = 0.0
    edge_to_receiver_distance_meters: float = 0.0


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
    best_score = float('-inf')
    receiver_xy = (receiver_pos[0], receiver_pos[1])
    receiver_height = receiver_pos[2]
    source_receiver_distance = _distance_3d(receiver_pos, source_pos, source_height_meters)

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

        intersection_x = source_pos[0] + (t * (receiver_xy[0] - source_pos[0]))
        intersection_y = source_pos[1] + (t * (receiver_xy[1] - source_pos[1]))
        height_excess = max(0.0, barrier.height_meters - line_height)
        top_point = (intersection_x, intersection_y, barrier.height_meters)
        source_to_edge_distance = _point_distance_3d((source_pos[0], source_pos[1], source_height_meters), top_point)
        edge_to_receiver_distance = _point_distance_3d(top_point, receiver_pos)
        path_excess = max(0.0, (source_to_edge_distance + edge_to_receiver_distance) - source_receiver_distance)
        score = barrier.attenuation_db + material_bonus_db(
            reflection_loss_db=barrier.reflection_loss_db,
            diffraction_loss_db=barrier.diffraction_loss_db,
            absorption_coefficient=barrier.absorption_coefficient,
            allows_reflection=barrier.allows_reflection,
            allows_diffraction=barrier.allows_diffraction,
        ) + min(height_excess * 0.25, 2.0)
        if best_context is None or score > best_score:
            best_score = score
            best_context = ShieldingContext(
                is_blocked=True,
                attenuation_db=barrier.attenuation_db,
                barrier_id=barrier.id,
                reflection_loss_db=barrier.reflection_loss_db,
                diffraction_loss_db=barrier.diffraction_loss_db,
                absorption_coefficient=barrier.absorption_coefficient,
                allows_reflection=barrier.allows_reflection,
                allows_diffraction=barrier.allows_diffraction,
                line_height_meters=line_height,
                height_excess_meters=height_excess,
                source_receiver_distance_meters=source_receiver_distance,
                intersection_ratio=t,
                path_excess_meters=path_excess,
                source_to_edge_distance_meters=source_to_edge_distance,
                edge_to_receiver_distance_meters=edge_to_receiver_distance,
            )

    return best_context


def shielding_correction_db(context: ShieldingContext | None = None) -> float:
    if context is None:
        return 0.0
    return -abs(context.attenuation_db) if context.is_blocked else 0.0


def _distance_3d(
    receiver_pos: tuple[float, float, float],
    source_pos: tuple[float, float],
    source_height_meters: float,
) -> float:
    dx = receiver_pos[0] - source_pos[0]
    dy = receiver_pos[1] - source_pos[1]
    dz = receiver_pos[2] - source_height_meters
    return math.sqrt((dx * dx) + (dy * dy) + (dz * dz))


def _point_distance_3d(
    point_a: tuple[float, float, float],
    point_b: tuple[float, float, float],
) -> float:
    return math.sqrt(
        ((point_a[0] - point_b[0]) ** 2)
        + ((point_a[1] - point_b[1]) ** 2)
        + ((point_a[2] - point_b[2]) ** 2)
    )
