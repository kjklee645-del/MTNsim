from __future__ import annotations

from dataclasses import dataclass
import math

from mtnsim.acoustics.propagation.materials import MaterialContext, surface_reflectivity
from mtnsim.acoustics.propagation.shielding import BarrierSegment


@dataclass(slots=True)
class ReflectionContext:
    enabled: bool = False
    gain_db: float = 0.0
    barrier_id: str | None = None
    extra_path_meters: float = 0.0
    nearest_offset_meters: float = 0.0
    reflection_point_xy: tuple[float, float] | None = None
    segment_fraction: float = 0.5
    normal_alignment: float = 0.0


def build_reflection_context(
    receiver_pos: tuple[float, float, float],
    source_pos: tuple[float, float],
    barriers: list[BarrierSegment],
    source_height_meters: float = 0.3,
) -> ReflectionContext | None:
    receiver_xy = (receiver_pos[0], receiver_pos[1])
    direct_distance = _distance_3d(receiver_pos, source_pos, source_height_meters)
    best_context: ReflectionContext | None = None
    best_gain = 0.0

    for barrier in barriers:
        if not barrier.allows_reflection:
            continue

        specular = _specular_reflection_point(
            source_pos=source_pos,
            receiver_pos=receiver_xy,
            segment_start=(barrier.x1, barrier.y1),
            segment_end=(barrier.x2, barrier.y2),
        )
        if specular is None:
            continue

        reflection_point, segment_fraction = specular
        source_to_surface = _distance_3d((reflection_point[0], reflection_point[1], receiver_pos[2]), source_pos, source_height_meters)
        surface_to_receiver = math.dist(reflection_point, receiver_xy)
        reflected_path = source_to_surface + surface_to_receiver
        extra_path = max(0.0, reflected_path - direct_distance)
        nearest_offset = min(
            _point_to_segment_distance(source_pos, (barrier.x1, barrier.y1), (barrier.x2, barrier.y2)),
            _point_to_segment_distance(receiver_xy, (barrier.x1, barrier.y1), (barrier.x2, barrier.y2)),
        )
        if extra_path > 120.0 or nearest_offset > 80.0:
            continue

        normal_alignment = _normal_alignment(
            reflection_point=reflection_point,
            source_pos=source_pos,
            receiver_pos=receiver_xy,
            segment_start=(barrier.x1, barrier.y1),
            segment_end=(barrier.x2, barrier.y2),
        )
        if normal_alignment < 0.15:
            continue

        centrality = max(0.25, 1.0 - (abs(segment_fraction - 0.5) * 1.5))
        distance_factor = 1.0 / (1.0 + (extra_path / 25.0) + (source_to_surface / 180.0) + (surface_to_receiver / 180.0))
        reflectivity = surface_reflectivity(
            MaterialContext(
                reflection_loss_db=barrier.reflection_loss_db,
                absorption_coefficient=barrier.absorption_coefficient,
                diffraction_loss_db=barrier.diffraction_loss_db,
                allows_reflection=barrier.allows_reflection,
                allows_diffraction=barrier.allows_diffraction,
            )
        )
        reflected_energy = reflectivity * normal_alignment * centrality * distance_factor * 2.8
        gain = 10.0 * math.log10(1.0 + reflected_energy)
        gain = max(0.0, min(gain, 4.0))

        if gain > best_gain:
            best_gain = gain
            best_context = ReflectionContext(
                enabled=gain > 0.0,
                gain_db=gain,
                barrier_id=barrier.id,
                extra_path_meters=extra_path,
                nearest_offset_meters=nearest_offset,
                reflection_point_xy=reflection_point,
                segment_fraction=segment_fraction,
                normal_alignment=normal_alignment,
            )

    return best_context if best_context and best_context.enabled else None


def reflection_correction_db(context: ReflectionContext | None = None) -> float:
    if context is None or not context.enabled:
        return 0.0
    return max(0.0, context.gain_db)


def _distance_3d(
    receiver_pos: tuple[float, float, float],
    source_pos: tuple[float, float],
    source_height_meters: float,
) -> float:
    dx = receiver_pos[0] - source_pos[0]
    dy = receiver_pos[1] - source_pos[1]
    dz = receiver_pos[2] - source_height_meters
    return math.sqrt((dx * dx) + (dy * dy) + (dz * dz))


def _point_to_segment_distance(
    point: tuple[float, float],
    segment_start: tuple[float, float],
    segment_end: tuple[float, float],
) -> float:
    px, py = point
    x1, y1 = segment_start
    x2, y2 = segment_end
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0.0 and dy == 0.0:
        return math.dist(point, segment_start)
    t = ((px - x1) * dx + (py - y1) * dy) / ((dx * dx) + (dy * dy))
    t = max(0.0, min(1.0, t))
    projection = (x1 + (t * dx), y1 + (t * dy))
    return math.dist(point, projection)


def _specular_reflection_point(
    source_pos: tuple[float, float],
    receiver_pos: tuple[float, float],
    segment_start: tuple[float, float],
    segment_end: tuple[float, float],
    epsilon: float = 1e-9,
) -> tuple[tuple[float, float], float] | None:
    x1, y1 = segment_start
    x2, y2 = segment_end
    dx = x2 - x1
    dy = y2 - y1
    length_sq = (dx * dx) + (dy * dy)
    if length_sq <= epsilon:
        return None

    mirrored_source = _reflect_point_across_line(source_pos, segment_start, segment_end)
    line_dx = receiver_pos[0] - mirrored_source[0]
    line_dy = receiver_pos[1] - mirrored_source[1]
    denom = _cross(line_dx, line_dy, dx, dy)
    if abs(denom) <= epsilon:
        return None

    diff_x = x1 - mirrored_source[0]
    diff_y = y1 - mirrored_source[1]
    t = _cross(diff_x, diff_y, dx, dy) / denom
    u = _cross(diff_x, diff_y, line_dx, line_dy) / denom
    if not (0.0 <= t <= 1.0 and 0.0 <= u <= 1.0):
        return None

    point = (mirrored_source[0] + (t * line_dx), mirrored_source[1] + (t * line_dy))
    return point, u


def _reflect_point_across_line(
    point: tuple[float, float],
    line_start: tuple[float, float],
    line_end: tuple[float, float],
) -> tuple[float, float]:
    px, py = point
    x1, y1 = line_start
    x2, y2 = line_end
    dx = x2 - x1
    dy = y2 - y1
    length_sq = (dx * dx) + (dy * dy)
    if length_sq == 0.0:
        return point
    t = ((px - x1) * dx + (py - y1) * dy) / length_sq
    proj_x = x1 + (t * dx)
    proj_y = y1 + (t * dy)
    return (2.0 * proj_x - px, 2.0 * proj_y - py)


def _normal_alignment(
    reflection_point: tuple[float, float],
    source_pos: tuple[float, float],
    receiver_pos: tuple[float, float],
    segment_start: tuple[float, float],
    segment_end: tuple[float, float],
) -> float:
    dx = segment_end[0] - segment_start[0]
    dy = segment_end[1] - segment_start[1]
    length = math.sqrt((dx * dx) + (dy * dy))
    if length == 0.0:
        return 0.0
    normal = (-dy / length, dx / length)
    source_vec = _unit_vector((source_pos[0] - reflection_point[0], source_pos[1] - reflection_point[1]))
    receiver_vec = _unit_vector((receiver_pos[0] - reflection_point[0], receiver_pos[1] - reflection_point[1]))
    source_alignment = abs((source_vec[0] * normal[0]) + (source_vec[1] * normal[1]))
    receiver_alignment = abs((receiver_vec[0] * normal[0]) + (receiver_vec[1] * normal[1]))
    return (source_alignment + receiver_alignment) * 0.5


def _unit_vector(vector: tuple[float, float]) -> tuple[float, float]:
    length = math.sqrt((vector[0] * vector[0]) + (vector[1] * vector[1]))
    if length == 0.0:
        return (0.0, 0.0)
    return (vector[0] / length, vector[1] / length)


def _cross(ax: float, ay: float, bx: float, by: float) -> float:
    return (ax * by) - (ay * bx)
