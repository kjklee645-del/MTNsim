from __future__ import annotations

from dataclasses import dataclass
import math

from mtnsim.acoustics.propagation.shielding import BarrierSegment


@dataclass(slots=True)
class ReflectionContext:
    enabled: bool = False
    gain_db: float = 0.0
    barrier_id: str | None = None
    extra_path_meters: float = 0.0
    nearest_offset_meters: float = 0.0
    reflection_point_xy: tuple[float, float] | None = None


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

        reflection_point = _specular_reflection_point(
            source_pos=source_pos,
            receiver_pos=receiver_xy,
            segment_start=(barrier.x1, barrier.y1),
            segment_end=(barrier.x2, barrier.y2),
        )
        if reflection_point is None:
            continue

        source_to_surface = _distance_3d((reflection_point[0], reflection_point[1], receiver_pos[2]), source_pos, source_height_meters)
        surface_to_receiver = math.dist(reflection_point, receiver_xy)
        reflected_path = source_to_surface + surface_to_receiver
        extra_path = max(0.0, reflected_path - direct_distance)
        nearest_offset = min(
            _point_to_segment_distance(source_pos, (barrier.x1, barrier.y1), (barrier.x2, barrier.y2)),
            _point_to_segment_distance(receiver_xy, (barrier.x1, barrier.y1), (barrier.x2, barrier.y2)),
        )

        if extra_path > 100.0 or nearest_offset > 70.0:
            continue

        gain = 3.4
        gain -= min(extra_path * 0.030, 2.1)
        gain -= min(nearest_offset * 0.012, 1.0)
        gain -= min(max(barrier.reflection_loss_db, 0.0) * 0.24, 1.8)
        gain -= min(max(barrier.absorption_coefficient, 0.0) * 1.8, 1.1)
        gain = max(0.0, min(gain, 3.5))

        if gain > best_gain:
            best_gain = gain
            best_context = ReflectionContext(
                enabled=gain > 0.0,
                gain_db=gain,
                barrier_id=barrier.id,
                extra_path_meters=extra_path,
                nearest_offset_meters=nearest_offset,
                reflection_point_xy=reflection_point,
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
) -> tuple[float, float] | None:
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

    return (mirrored_source[0] + (t * line_dx), mirrored_source[1] + (t * line_dy))


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


def _cross(ax: float, ay: float, bx: float, by: float) -> float:
    return (ax * by) - (ay * bx)
