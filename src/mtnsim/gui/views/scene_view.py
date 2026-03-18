from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from typing import Iterable

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QBrush, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QLabel, QSplitter, QTextEdit, QToolTip, QVBoxLayout, QWidget

from mtnsim.gui.controllers.scene_controller import SceneSnapshot
from mtnsim.gui.controllers.result_controller import HeatmapCell


@dataclass(frozen=True, slots=True)
class LayerStyle:
    pen_color: str
    pen_width: int = 1
    brush_color: str | None = None


@dataclass(frozen=True, slots=True)
class VehicleGlyph:
    vehicle_id: str
    x: float
    y: float
    heading_deg: float = 0.0
    speed_mps: float = 0.0
    vehicle_type: str = 'default'
    body_color: str = '#f59e0b'


class SceneCanvas(QWidget):
    hover_text_changed = Signal(str)
    vehicle_selected = Signal(str)
    scene_object_selected = Signal(str, str)
    scene_object_drawn = Signal(str, dict)
    scene_object_geometry_edited = Signal(str, str, dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.snapshot: SceneSnapshot | None = None
        self.vehicle_glyphs: list[VehicleGlyph] = []
        self.vehicle_trails: list[list[tuple[float, float]]] = []
        self.heatmap_cells: list[HeatmapCell] = []
        self.selected_vehicle_id: str | None = None
        self.selected_scene_object: tuple[str, str] | None = None
        self._heatmap_auto_range = True
        self._heatmap_min_db = 40.0
        self._heatmap_max_db = 80.0
        self._heatmap_opacity = 96
        self._zoom = 1.0
        self._pan = QPointF(0.0, 0.0)
        self._dragging = False
        self._last_mouse_pos = QPointF()
        self._hover_text = ''
        self._draw_mode: str | None = None
        self._draw_template: dict | None = None
        self._draw_points: list[tuple[float, float]] = []
        self._edit_mode: str | None = None
        self._edit_vertex_index: int | None = None
        self._edit_last_world: tuple[float, float] | None = None
        self.setMinimumHeight(420)
        self.setMouseTracking(True)

    def set_snapshot(self, snapshot: SceneSnapshot | None) -> None:
        if snapshot is None:
            if self.snapshot is None:
                self.update()
                return
            self.snapshot = None
            self.reset_view()
            return

        if self.snapshot is not None and snapshot.bounds == self.snapshot.bounds:
            self.snapshot = snapshot
            self.update()
            return

        self.snapshot = snapshot
        self.reset_view()

    def set_vehicle_points(self, vehicle_points: list[VehicleGlyph], trails: list[list[tuple[float, float]]] | None = None) -> None:
        self.vehicle_glyphs = vehicle_points
        self.vehicle_trails = trails or []
        self.update()

    def set_selected_vehicle(self, vehicle_id: str | None) -> None:
        self.selected_vehicle_id = vehicle_id or None
        self.update()

    def set_selected_scene_object(self, object_type: str | None, object_id: str | None) -> None:
        if object_type and object_id:
            self.selected_scene_object = (object_type, object_id)
        else:
            self.selected_scene_object = None
        self.update()

    def start_draw_mode(self, object_type: str, template: dict | None = None) -> None:
        self._draw_mode = object_type
        self._draw_template = dict(template or {})
        self._draw_points = []
        self.update()

    def finish_draw_mode(self) -> None:
        if self._draw_mode in {'buildings', 'ground_surfaces', 'vegetation_zones'} and len(self._draw_points) >= 3:
            self._emit_drawn_object()
            return
        self.cancel_draw_mode()

    def cancel_draw_mode(self) -> None:
        self._draw_mode = None
        self._draw_template = None
        self._draw_points = []
        self.update()

    def set_heatmap_cells(self, cells: list[HeatmapCell]) -> None:
        self.heatmap_cells = cells
        self.update()

    def set_heatmap_settings(
        self,
        *,
        auto_range: bool | None = None,
        min_db: float | None = None,
        max_db: float | None = None,
        opacity: int | None = None,
    ) -> None:
        if auto_range is not None:
            self._heatmap_auto_range = auto_range
        if min_db is not None:
            self._heatmap_min_db = float(min_db)
        if max_db is not None:
            self._heatmap_max_db = float(max(max_db, self._heatmap_min_db + 0.1))
        if opacity is not None:
            self._heatmap_opacity = int(max(0, min(255, opacity)))
        self.update()

    def reset_view(self) -> None:
        self._zoom = 1.0
        self._pan = QPointF(0.0, 0.0)
        self._hover_text = ''
        self.update()

    def center_on_world_point(self, world_point: tuple[float, float]) -> None:
        if self.snapshot is None:
            return
        plot_rect, _, map_point = self._mapping_context()
        center = QPointF(plot_rect.center())
        base_x, base_y = map_point(world_point)
        self._pan = QPointF(
            -((base_x - center.x()) * self._zoom),
            -((base_y - center.y()) * self._zoom),
        )
        self.update()

    def wheelEvent(self, event) -> None:  # noqa: N802
        if self.snapshot is None:
            return
        delta = event.angleDelta().y()
        if delta == 0:
            return
        plot_rect = self._plot_rect()
        center = QPointF(plot_rect.center())
        old_zoom = self._zoom
        factor = 1.15 if delta > 0 else (1.0 / 1.15)
        new_zoom = max(0.5, min(8.0, old_zoom * factor))
        if abs(new_zoom - old_zoom) < 1e-6:
            return
        cursor = event.position()
        base_point = QPointF(
            center.x() + ((cursor.x() - center.x() - self._pan.x()) / old_zoom),
            center.y() + ((cursor.y() - center.y() - self._pan.y()) / old_zoom),
        )
        self._zoom = new_zoom
        self._pan = QPointF(
            cursor.x() - center.x() - ((base_point.x() - center.x()) * new_zoom),
            cursor.y() - center.y() - ((base_point.y() - center.y()) * new_zoom),
        )
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            if self._draw_mode is not None:
                self._append_draw_point(event.position())
                return
            if self._begin_scene_object_edit(event.position()):
                return
            selected_vehicle = self._find_vehicle_at_position(event.position())
            if selected_vehicle is not None:
                self.selected_vehicle_id = selected_vehicle.vehicle_id
                self.vehicle_selected.emit(selected_vehicle.vehicle_id)
                self.update()
            else:
                selected_scene_object = self._find_scene_object_at_position(event.position())
                if selected_scene_object is not None:
                    self.selected_scene_object = selected_scene_object
                    self.scene_object_selected.emit(selected_scene_object[0], selected_scene_object[1])
                    self.update()
                else:
                    if self.selected_vehicle_id is not None:
                        self.selected_vehicle_id = None
                        self.vehicle_selected.emit('')
                        self.update()
                    self._dragging = True
                    self._last_mouse_pos = event.position()
                    self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._edit_mode is not None:
            self._update_scene_object_edit(event.position())
        elif self._dragging:
            delta = event.position() - self._last_mouse_pos
            self._pan = QPointF(self._pan.x() + delta.x(), self._pan.y() + delta.y())
            self._last_mouse_pos = event.position()
            self.update()
        else:
            hover = self._find_hover_info(event.position())
            self._set_hover_text(hover, event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self._edit_mode = None
            self._edit_vertex_index = None
            self._edit_last_world = None
            self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            if self._draw_mode in {'buildings', 'ground_surfaces', 'vegetation_zones'} and len(self._draw_points) >= 3:
                self._emit_drawn_object()
                return
            if self._draw_mode is None:
                self.reset_view()
        super().mouseDoubleClickEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover_text = ''
        self.hover_text_changed.emit('')
        QToolTip.hideText()
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor('#efe9dd'))
        gradient.setColorAt(1.0, QColor('#e5dccd'))
        painter.fillRect(self.rect(), gradient)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.snapshot is None:
            painter.setPen(QPen(QColor('#374151'), 1))
            painter.drawText(self.rect(), Qt.AlignCenter, 'Load a project and scenario to view the scene.')
            return

        plot_rect, pixels_per_meter, map_point = self._mapping_context()
        center = QPointF(plot_rect.center())

        painter.save()
        painter.translate(center.x() + self._pan.x(), center.y() + self._pan.y())
        painter.scale(self._zoom, self._zoom)
        painter.translate(-center.x(), -center.y())

        painter.setPen(QPen(QColor('#d8cfc2'), 1))
        painter.drawRect(plot_rect)
        self._draw_grid(painter, plot_rect)
        self._draw_polygons(painter, self.snapshot.ground_layer.polygons, map_point, LayerStyle('#7aa65a', 1, '#cfdf9f'))
        self._draw_polygons(painter, self.snapshot.vegetation_layer.polygons, map_point, LayerStyle('#2f6b3d', 1, '#9bd18b'))
        self._draw_polygons(painter, self.snapshot.junction_layer.polygons, map_point, LayerStyle('#4b5563', 1, '#505864'))
        self._draw_heatmap(painter, map_point, pixels_per_meter)
        self._draw_road_bands(painter, self.snapshot.road_layer.polylines, self.snapshot.road_layer.widths, map_point, pixels_per_meter)
        self._draw_polygons(painter, self.snapshot.building_layer.polygons, map_point, LayerStyle('#315a9f', 2, '#b9ccef'))
        self._draw_polylines(painter, self.snapshot.barrier_layer.polylines, map_point, LayerStyle('#cb4335', 4))
        self._draw_polylines(painter, self.snapshot.terrain_layer.polylines, map_point, LayerStyle('#7c4a21', 3))
        self._draw_selected_scene_object(painter, map_point)
        self._draw_draw_mode_overlay(painter, map_point)
        self._draw_vehicle_trails(painter, self.vehicle_trails, map_point)
        self._draw_receivers(painter, self.snapshot.receiver_layer.points, map_point)
        self._draw_vehicle_glyphs(painter, self.vehicle_glyphs, map_point, pixels_per_meter)
        painter.restore()

        self._draw_overlay(painter)
        self._draw_minimap(painter)

    def _plot_rect(self) -> QRectF:
        margin = 28
        return QRectF(self.rect().adjusted(margin, margin, -margin, -margin))

    def _mapping_context(self):
        plot_rect = self._plot_rect()
        min_x, min_y, max_x, max_y = self.snapshot.bounds
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)
        pixels_per_meter = min(plot_rect.width() / span_x, plot_rect.height() / span_y)
        content_width = span_x * pixels_per_meter
        content_height = span_y * pixels_per_meter
        offset_x = plot_rect.left() + ((plot_rect.width() - content_width) / 2.0)
        offset_y = plot_rect.top() + ((plot_rect.height() - content_height) / 2.0)

        def map_point(point: tuple[float, float]) -> tuple[float, float]:
            px = offset_x + ((point[0] - min_x) * pixels_per_meter)
            py = offset_y + content_height - ((point[1] - min_y) * pixels_per_meter)
            return px, py

        return plot_rect, pixels_per_meter, map_point

    def _transform_screen_point(self, point: tuple[float, float], plot_rect: QRectF) -> QPointF:
        center = QPointF(plot_rect.center())
        base = QPointF(point[0], point[1])
        return QPointF(
            center.x() + ((base.x() - center.x()) * self._zoom) + self._pan.x(),
            center.y() + ((base.y() - center.y()) * self._zoom) + self._pan.y(),
        )

    def _screen_to_world(self, screen: QPointF, plot_rect: QRectF) -> tuple[float, float]:
        min_x, min_y, max_x, max_y = self.snapshot.bounds
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)
        pixels_per_meter = min(plot_rect.width() / span_x, plot_rect.height() / span_y)
        content_width = span_x * pixels_per_meter
        content_height = span_y * pixels_per_meter
        offset_x = plot_rect.left() + ((plot_rect.width() - content_width) / 2.0)
        offset_y = plot_rect.top() + ((plot_rect.height() - content_height) / 2.0)
        center = QPointF(plot_rect.center())
        base_x = center.x() + ((screen.x() - center.x() - self._pan.x()) / self._zoom)
        base_y = center.y() + ((screen.y() - center.y() - self._pan.y()) / self._zoom)
        world_x = min_x + ((base_x - offset_x) / pixels_per_meter)
        world_y = min_y + ((offset_y + content_height - base_y) / pixels_per_meter)
        world_x = max(min_x, min(max_x, world_x))
        world_y = max(min_y, min(max_y, world_y))
        return (world_x, world_y)

    def _distance_to_segment(self, point: QPointF, start: QPointF, end: QPointF) -> float:
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            return hypot(point.x() - start.x(), point.y() - start.y())
        t = ((point.x() - start.x()) * dx + (point.y() - start.y()) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        proj = QPointF(start.x() + (t * dx), start.y() + (t * dy))
        return hypot(point.x() - proj.x(), point.y() - proj.y())


    def _find_vehicle_at_position(self, local_pos: QPointF) -> VehicleGlyph | None:
        if self.snapshot is None or not self.vehicle_glyphs:
            return None
        plot_rect, _, map_point = self._mapping_context()
        nearest: VehicleGlyph | None = None
        nearest_distance = 1e9
        for glyph in self.vehicle_glyphs:
            pos = self._transform_screen_point(map_point((glyph.x, glyph.y)), plot_rect)
            distance = hypot(local_pos.x() - pos.x(), local_pos.y() - pos.y())
            if distance < nearest_distance and distance <= 18:
                nearest = glyph
                nearest_distance = distance
        return nearest

    def _speed_color(self, speed_mps: float) -> QColor:
        speed_kmh = max(0.0, speed_mps * 3.6)
        ratio = max(0.0, min(1.0, speed_kmh / 120.0))
        if ratio < 0.5:
            t = ratio / 0.5
            r = int(39 + (245 - 39) * t)
            g = int(174 + (158 - 174) * t)
            b = int(96 + (11 - 96) * t)
        else:
            t = (ratio - 0.5) / 0.5
            r = int(245 + (220 - 245) * t)
            g = int(158 + (38 - 158) * t)
            b = int(11 + (38 - 11) * t)
        return QColor(r, g, b)

    def _heatmap_color(self, value: float, min_value: float, max_value: float) -> QColor:
        if max_value <= min_value:
            return QColor(59, 130, 246, self._heatmap_opacity)
        ratio = max(0.0, min(1.0, (value - min_value) / (max_value - min_value)))
        if ratio < 0.5:
            t = ratio / 0.5
            r = int(37 + (234 - 37) * t)
            g = int(99 + (179 - 99) * t)
            b = int(235 + (8 - 235) * t)
        else:
            t = (ratio - 0.5) / 0.5
            r = int(234 + (220 - 234) * t)
            g = int(179 + (38 - 179) * t)
            b = int(8 + (38 - 8) * t)
        return QColor(r, g, b, self._heatmap_opacity)

    def _find_hover_info(self, local_pos: QPointF) -> str:
        if self.snapshot is None:
            return ''
        plot_rect, pixels_per_meter, map_point = self._mapping_context()

        nearest_text = ''
        nearest_distance = 1e9

        for glyph in self.vehicle_glyphs:
            pos = self._transform_screen_point(map_point((glyph.x, glyph.y)), plot_rect)
            distance = hypot(local_pos.x() - pos.x(), local_pos.y() - pos.y())
            if distance < nearest_distance and distance <= 18:
                nearest_distance = distance
                nearest_text = f'Vehicle {glyph.vehicle_id} | type={glyph.vehicle_type} | {glyph.speed_mps * 3.6:.1f} km/h | heading={glyph.heading_deg:.0f} deg'

        for label, x, y in self.snapshot.receiver_layer.points:
            pos = self._transform_screen_point(map_point((x, y)), plot_rect)
            distance = hypot(local_pos.x() - pos.x(), local_pos.y() - pos.y())
            if distance < nearest_distance and distance <= 14:
                nearest_distance = distance
                nearest_text = f'Receiver {label} | x={x:.1f}, y={y:.1f}'

        for cell in self.heatmap_cells:
            pos = self._transform_screen_point(map_point((cell.x, cell.y)), plot_rect)
            distance = hypot(local_pos.x() - pos.x(), local_pos.y() - pos.y())
            if distance < nearest_distance and distance <= max(10.0, 3.0 * self._zoom):
                nearest_distance = distance
                nearest_text = f'Grid cell | x={cell.x:.1f}, y={cell.y:.1f} | {cell.value_db:.1f} dB'

        for index, (polyline, width_m) in enumerate(zip(self.snapshot.road_layer.polylines, self.snapshot.road_layer.widths), start=1):
            for seg_index in range(len(polyline) - 1):
                start = self._transform_screen_point(map_point(polyline[seg_index]), plot_rect)
                end = self._transform_screen_point(map_point(polyline[seg_index + 1]), plot_rect)
                distance = self._distance_to_segment(local_pos, start, end)
                threshold = max(8.0, width_m * pixels_per_meter * 0.55 * self._zoom)
                if distance < nearest_distance and distance <= threshold:
                    nearest_distance = distance
                    nearest_text = f'Lane {index} | width={width_m:.1f} m'

        scene_object_hit = self._find_scene_object_at_position(local_pos)
        if scene_object_hit is not None:
            object_type, object_id = scene_object_hit
            return self._selected_scene_object_text(object_type, object_id)

        return nearest_text

    def _find_scene_object_at_position(self, local_pos: QPointF) -> tuple[str, str] | None:
        if self.snapshot is None:
            return None
        plot_rect, pixels_per_meter, map_point = self._mapping_context()

        def find_polyline(layer, object_type: str, base_threshold: float) -> tuple[str, str] | None:
            nearest = None
            nearest_distance = 1e9
            for index, polyline in enumerate(layer.polylines):
                object_id = layer.ids[index] if index < len(layer.ids) else f'{object_type}_{index + 1}'
                width_value = layer.widths[index] if index < len(layer.widths) else 1.0
                threshold = max(base_threshold, width_value * pixels_per_meter * 0.4 * self._zoom)
                for seg_index in range(len(polyline) - 1):
                    start = self._transform_screen_point(map_point(polyline[seg_index]), plot_rect)
                    end = self._transform_screen_point(map_point(polyline[seg_index + 1]), plot_rect)
                    distance = self._distance_to_segment(local_pos, start, end)
                    if distance < nearest_distance and distance <= threshold:
                        nearest = (object_type, object_id)
                        nearest_distance = distance
            return nearest

        def find_polygon(layer, object_type: str) -> tuple[str, str] | None:
            for index, polygon in enumerate(layer.polygons):
                qpolygon = QPolygonF([self._transform_screen_point(map_point(point), plot_rect) for point in polygon])
                if qpolygon.containsPoint(local_pos, Qt.OddEvenFill):
                    object_id = layer.ids[index] if index < len(layer.ids) else f'{object_type}_{index + 1}'
                    return (object_type, object_id)
            return None

        for layer, object_type, threshold in [
            (self.snapshot.barrier_layer, 'noise_barriers', 10.0),
            (self.snapshot.terrain_layer, 'terrain_edges', 9.0),
        ]:
            hit = find_polyline(layer, object_type, threshold)
            if hit is not None:
                return hit

        for layer, object_type in [
            (self.snapshot.building_layer, 'buildings'),
            (self.snapshot.ground_layer, 'ground_surfaces'),
            (self.snapshot.vegetation_layer, 'vegetation_zones'),
        ]:
            hit = find_polygon(layer, object_type)
            if hit is not None:
                return hit
        return None

    def _selected_scene_object_text(self, object_type: str, object_id: str) -> str:
        labels = {
            'noise_barriers': 'Noise barrier',
            'terrain_edges': 'Terrain edge',
            'buildings': 'Building',
            'ground_surfaces': 'Ground surface',
            'vegetation_zones': 'Vegetation zone',
        }
        return f'{labels.get(object_type, object_type)} {object_id}'

    def _draw_selected_scene_object(self, painter: QPainter, mapper) -> None:
        if self.snapshot is None or self.selected_scene_object is None:
            return
        object_type, object_id = self.selected_scene_object
        highlight_pen = QPen(QColor('#f59e0b'), 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        highlight_brush = QBrush(QColor(245, 158, 11, 60))

        def draw_polyline(layer) -> bool:
            if object_id not in layer.ids:
                return False
            index = layer.ids.index(object_id)
            polyline = layer.polylines[index]
            painter.setPen(highlight_pen)
            for seg_index in range(len(polyline) - 1):
                x1, y1 = mapper(polyline[seg_index])
                x2, y2 = mapper(polyline[seg_index + 1])
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            return True

        def draw_polygon(layer) -> bool:
            if object_id not in layer.ids:
                return False
            index = layer.ids.index(object_id)
            polygon = layer.polygons[index]
            if len(polygon) < 3:
                return False
            painter.setPen(highlight_pen)
            painter.setBrush(highlight_brush)
            qpolygon = QPolygonF([QPointF(*mapper(point)) for point in polygon])
            painter.drawPolygon(qpolygon)
            return True

        if object_type == 'noise_barriers':
            draw_polyline(self.snapshot.barrier_layer)
            self._draw_selected_linear_handles(painter, mapper, self.snapshot.barrier_layer, object_id)
        elif object_type == 'terrain_edges':
            draw_polyline(self.snapshot.terrain_layer)
            self._draw_selected_linear_handles(painter, mapper, self.snapshot.terrain_layer, object_id)
        elif object_type == 'buildings':
            draw_polygon(self.snapshot.building_layer)
            self._draw_selected_polygon_handles(painter, mapper, self.snapshot.building_layer, object_id)
        elif object_type == 'ground_surfaces':
            draw_polygon(self.snapshot.ground_layer)
            self._draw_selected_polygon_handles(painter, mapper, self.snapshot.ground_layer, object_id)
        elif object_type == 'vegetation_zones':
            draw_polygon(self.snapshot.vegetation_layer)
            self._draw_selected_polygon_handles(painter, mapper, self.snapshot.vegetation_layer, object_id)

    def _get_selected_layer_and_index(self):
        if self.snapshot is None or self.selected_scene_object is None:
            return None, None, None
        object_type, object_id = self.selected_scene_object
        layer_map = {
            'noise_barriers': self.snapshot.barrier_layer,
            'terrain_edges': self.snapshot.terrain_layer,
            'buildings': self.snapshot.building_layer,
            'ground_surfaces': self.snapshot.ground_layer,
            'vegetation_zones': self.snapshot.vegetation_layer,
        }
        layer = layer_map.get(object_type)
        if layer is None or object_id not in layer.ids:
            return object_type, None, None
        return object_type, layer, layer.ids.index(object_id)

    def _begin_scene_object_edit(self, local_pos: QPointF) -> bool:
        if self.selected_scene_object is None or self.snapshot is None:
            return False
        hit = self._find_selected_object_edit_hit(local_pos)
        if hit is None:
            return False
        self._edit_mode, self._edit_vertex_index = hit
        self._edit_last_world = self._screen_to_world(local_pos, self._plot_rect())
        self.setCursor(Qt.SizeAllCursor if self._edit_mode == 'move' else Qt.CrossCursor)
        return True

    def _find_selected_object_edit_hit(self, local_pos: QPointF) -> tuple[str, int | None] | None:
        object_type, layer, index = self._get_selected_layer_and_index()
        if layer is None or index is None:
            return None
        plot_rect, pixels_per_meter, map_point = self._mapping_context()
        handle_threshold = max(10.0, 8.0 * self._zoom)
        if object_type in {'noise_barriers', 'terrain_edges'}:
            polyline = layer.polylines[index]
            for point_index, point in enumerate(polyline[:2]):
                pos = self._transform_screen_point(map_point(point), plot_rect)
                if hypot(local_pos.x() - pos.x(), local_pos.y() - pos.y()) <= handle_threshold:
                    return ('endpoint', point_index)
            for seg_index in range(len(polyline) - 1):
                start = self._transform_screen_point(map_point(polyline[seg_index]), plot_rect)
                end = self._transform_screen_point(map_point(polyline[seg_index + 1]), plot_rect)
                threshold = max(8.0, (layer.widths[index] if index < len(layer.widths) else 1.0) * pixels_per_meter * 0.4 * self._zoom)
                if self._distance_to_segment(local_pos, start, end) <= threshold:
                    return ('move', None)
            return None
        polygon = layer.polygons[index]
        for point_index, point in enumerate(polygon):
            pos = self._transform_screen_point(map_point(point), plot_rect)
            if hypot(local_pos.x() - pos.x(), local_pos.y() - pos.y()) <= handle_threshold:
                return ('vertex', point_index)
        qpolygon = QPolygonF([self._transform_screen_point(map_point(point), plot_rect) for point in polygon])
        if qpolygon.containsPoint(local_pos, Qt.OddEvenFill):
            return ('move', None)
        return None

    def _update_scene_object_edit(self, local_pos: QPointF) -> None:
        if self.snapshot is None or self.selected_scene_object is None or self._edit_mode is None:
            return
        object_type, layer, index = self._get_selected_layer_and_index()
        if layer is None or index is None:
            return
        current_world = self._screen_to_world(local_pos, self._plot_rect())
        last_world = self._edit_last_world or current_world
        dx = current_world[0] - last_world[0]
        dy = current_world[1] - last_world[1]
        if object_type in {'noise_barriers', 'terrain_edges'}:
            polyline = list(layer.polylines[index])
            if self._edit_mode == 'endpoint' and self._edit_vertex_index is not None:
                polyline[self._edit_vertex_index] = current_world
            elif self._edit_mode == 'move':
                polyline = [(point[0] + dx, point[1] + dy) for point in polyline]
            layer.polylines[index] = polyline
            payload = {
                'x1': float(polyline[0][0]),
                'y1': float(polyline[0][1]),
                'x2': float(polyline[1][0]),
                'y2': float(polyline[1][1]),
            }
        else:
            polygon = list(layer.polygons[index])
            if self._edit_mode == 'vertex' and self._edit_vertex_index is not None:
                polygon[self._edit_vertex_index] = current_world
            elif self._edit_mode == 'move':
                polygon = [(point[0] + dx, point[1] + dy) for point in polygon]
            layer.polygons[index] = polygon
            payload = {'footprint': [[float(x), float(y)] for x, y in polygon]}
        self._edit_last_world = current_world
        self.scene_object_geometry_edited.emit(object_type, self.selected_scene_object[1], payload)
        self.update()

    def _draw_selected_linear_handles(self, painter: QPainter, mapper, layer, object_id: str) -> None:
        if object_id not in layer.ids:
            return
        index = layer.ids.index(object_id)
        painter.save()
        painter.setPen(QPen(QColor('#78350f'), 2))
        painter.setBrush(QBrush(QColor('#fde68a')))
        for point in layer.polylines[index][:2]:
            px, py = mapper(point)
            painter.drawEllipse(QPointF(px, py), 5, 5)
        painter.restore()

    def _draw_selected_polygon_handles(self, painter: QPainter, mapper, layer, object_id: str) -> None:
        if object_id not in layer.ids:
            return
        index = layer.ids.index(object_id)
        painter.save()
        painter.setPen(QPen(QColor('#78350f'), 2))
        painter.setBrush(QBrush(QColor('#fde68a')))
        for point in layer.polygons[index]:
            px, py = mapper(point)
            painter.drawRect(QRectF(px - 4, py - 4, 8, 8))
        painter.restore()

    def _append_draw_point(self, screen_pos: QPointF) -> None:
        if self.snapshot is None or self._draw_mode is None:
            return
        world_point = self._screen_to_world(screen_pos, self._plot_rect())
        self._draw_points.append(world_point)
        if self._draw_mode in {'noise_barriers', 'terrain_edges'} and len(self._draw_points) >= 2:
            self._emit_drawn_object()
            return
        self.update()

    def _emit_drawn_object(self) -> None:
        if self._draw_mode is None:
            return
        template = dict(self._draw_template or {})
        object_type = self._draw_mode
        if object_type in {'noise_barriers', 'terrain_edges'}:
            if len(self._draw_points) < 2:
                return
            payload = {
                'id': str(template.get('id', object_type[:-1] if object_type.endswith('s') else object_type)),
                'x1': float(self._draw_points[0][0]),
                'y1': float(self._draw_points[0][1]),
                'x2': float(self._draw_points[1][0]),
                'y2': float(self._draw_points[1][1]),
                'height_meters': float(template.get('height_meters', 4.0)),
                'attenuation_db': float(template.get('attenuation_db', 0.0)),
                'material': str(template.get('material', 'generic')),
            }
        else:
            if len(self._draw_points) < 3:
                return
            payload = {
                'id': str(template.get('id', object_type[:-1] if object_type.endswith('s') else object_type)),
                'footprint': [[float(x), float(y)] for x, y in self._draw_points],
                'material': str(template.get('material', 'generic')),
            }
            if object_type in {'buildings', 'vegetation_zones'}:
                payload['height_meters'] = float(template.get('height_meters', 6.0))
                payload['attenuation_db'] = float(template.get('attenuation_db', 0.0))
        self.scene_object_drawn.emit(object_type, payload)
        self.cancel_draw_mode()

    def _draw_draw_mode_overlay(self, painter: QPainter, mapper) -> None:
        if self._draw_mode is None or not self._draw_points:
            return
        painter.save()
        painter.setPen(QPen(QColor('#f59e0b'), 3, Qt.DashLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(QBrush(QColor(245, 158, 11, 55)))
        if self._draw_mode in {'noise_barriers', 'terrain_edges'}:
            if len(self._draw_points) >= 2:
                x1, y1 = mapper(self._draw_points[0])
                x2, y2 = mapper(self._draw_points[1])
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        else:
            if len(self._draw_points) >= 2:
                qpolygon = QPolygonF([QPointF(*mapper(point)) for point in self._draw_points])
                painter.drawPolyline(qpolygon)
            if len(self._draw_points) >= 3:
                qpolygon = QPolygonF([QPointF(*mapper(point)) for point in self._draw_points])
                painter.drawPolygon(qpolygon)
        painter.setPen(QPen(QColor('#92400e'), 2))
        painter.setBrush(QBrush(QColor('#f59e0b')))
        for point in self._draw_points:
            px, py = mapper(point)
            painter.drawEllipse(QPointF(px, py), 4, 4)
        painter.restore()

    def _set_hover_text(self, text: str, event) -> None:
        if text == self._hover_text:
            return
        self._hover_text = text
        self.hover_text_changed.emit(text)
        if text:
            QToolTip.showText(event.globalPosition().toPoint(), text, self)
        else:
            QToolTip.hideText()
        self.update()

    def _draw_overlay(self, painter: QPainter) -> None:
        overlay_lines = [
            f'Zoom {self._zoom:.2f}x',
            'Wheel: zoom',
            'Drag: pan',
            'Double-click: reset',
        ]
        if self.heatmap_cells:
            values = [cell.value_db for cell in self.heatmap_cells]
            if self._heatmap_auto_range:
                overlay_lines.append(f'Heatmap auto {min(values):.1f} to {max(values):.1f} dB')
            else:
                overlay_lines.append(f'Heatmap fixed {self._heatmap_min_db:.1f} to {self._heatmap_max_db:.1f} dB')
            overlay_lines.append(f'Heatmap opacity {int(round(self._heatmap_opacity / 255 * 100))}%')
        if self.selected_vehicle_id:
            overlay_lines.append(f'Selected vehicle {self.selected_vehicle_id}')
        if self.selected_scene_object is not None:
            overlay_lines.append(self._selected_scene_object_text(*self.selected_scene_object))
        if self._draw_mode is not None:
            overlay_lines.append(f'Draw mode: {self._draw_mode} ({len(self._draw_points)} pts)')
        if self._hover_text:
            overlay_lines.append(self._hover_text)
        text = '\n'.join(overlay_lines)
        box = QRectF(16, 16, min(self.width() * 0.5, 450), 96 if not self._hover_text else 124)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 200))
        painter.drawRoundedRect(box, 8, 8)
        painter.setPen(QPen(QColor('#1f2937'), 1))
        painter.drawText(box.adjusted(10, 8, -10, -8), Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, text)

    def _draw_minimap(self, painter: QPainter) -> None:
        if self.snapshot is None:
            return
        box = QRectF(self.width() - 196, self.height() - 156, 180, 140)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 205))
        painter.drawRoundedRect(box, 8, 8)
        painter.setPen(QPen(QColor('#475569'), 1))
        painter.drawText(box.adjusted(8, 6, -8, -8), Qt.AlignTop | Qt.AlignLeft, 'Minimap')

        inner = box.adjusted(10, 24, -10, -10)
        min_x, min_y, max_x, max_y = self.snapshot.bounds
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)
        mini_ppm = min(inner.width() / span_x, inner.height() / span_y)
        mini_width = span_x * mini_ppm
        mini_height = span_y * mini_ppm
        mini_offset_x = inner.left() + ((inner.width() - mini_width) / 2.0)
        mini_offset_y = inner.top() + ((inner.height() - mini_height) / 2.0)

        def mini_map(point: tuple[float, float]) -> QPointF:
            return QPointF(
                mini_offset_x + ((point[0] - min_x) * mini_ppm),
                mini_offset_y + mini_height - ((point[1] - min_y) * mini_ppm),
            )

        painter.setPen(QPen(QColor('#cbd5e1'), 1))
        painter.drawRect(inner)
        painter.setPen(QPen(QColor('#4b5563'), 2))
        for polyline in self.snapshot.road_layer.polylines:
            for idx in range(len(polyline) - 1):
                p1 = mini_map(polyline[idx])
                p2 = mini_map(polyline[idx + 1])
                painter.drawLine(p1, p2)
        painter.setPen(QPen(QColor('#0f172a'), 1))
        painter.setBrush(QBrush(QColor('#0f172a')))
        for _, x, y in self.snapshot.receiver_layer.points:
            pos = mini_map((x, y))
            painter.drawEllipse(pos, 1.8, 1.8)

        plot_rect = self._plot_rect()
        top_left_world = self._screen_to_world(plot_rect.topLeft(), plot_rect)
        top_right_world = self._screen_to_world(plot_rect.topRight(), plot_rect)
        bottom_right_world = self._screen_to_world(plot_rect.bottomRight(), plot_rect)
        bottom_left_world = self._screen_to_world(plot_rect.bottomLeft(), plot_rect)
        viewport = QPolygonF([mini_map(top_left_world), mini_map(top_right_world), mini_map(bottom_right_world), mini_map(bottom_left_world)])
        painter.setPen(QPen(QColor('#dc2626'), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawPolygon(viewport)

    def _draw_grid(self, painter: QPainter, plot_rect: QRectF) -> None:
        painter.setPen(QPen(QColor('#e7ddcf'), 1, Qt.DotLine))
        for index in range(1, 7):
            x = plot_rect.left() + (plot_rect.width() * index / 7.0)
            y = plot_rect.top() + (plot_rect.height() * index / 7.0)
            painter.drawLine(int(x), int(plot_rect.top()), int(x), int(plot_rect.bottom()))
            painter.drawLine(int(plot_rect.left()), int(y), int(plot_rect.right()), int(y))

    def _draw_polylines(self, painter: QPainter, polylines, mapper, style: LayerStyle) -> None:
        painter.setPen(QPen(QColor(style.pen_color), style.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        for polyline in polylines:
            for index in range(len(polyline) - 1):
                x1, y1 = mapper(polyline[index])
                x2, y2 = mapper(polyline[index + 1])
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

    def _draw_polygons(self, painter: QPainter, polygons, mapper, style: LayerStyle) -> None:
        painter.setPen(QPen(QColor(style.pen_color), style.pen_width))
        painter.setBrush(QBrush(QColor(style.brush_color)) if style.brush_color else Qt.NoBrush)
        for polygon in polygons:
            if len(polygon) < 3:
                continue
            qpolygon = QPolygonF([QPointF(*mapper(point)) for point in polygon])
            painter.drawPolygon(qpolygon)

    def _draw_heatmap(self, painter: QPainter, mapper, pixels_per_meter: float) -> None:
        if not self.heatmap_cells:
            return
        if self._heatmap_auto_range:
            values = [cell.value_db for cell in self.heatmap_cells]
            min_value = min(values)
            max_value = max(values)
        else:
            min_value = self._heatmap_min_db
            max_value = self._heatmap_max_db
        radius = max(2.5, 2.2 * pixels_per_meter)
        painter.setPen(Qt.NoPen)
        for cell in self.heatmap_cells:
            px, py = mapper((cell.x, cell.y))
            painter.setBrush(QBrush(self._heatmap_color(cell.value_db, min_value, max_value)))
            painter.drawEllipse(QPointF(px, py), radius, radius)

    def _draw_road_bands(self, painter: QPainter, polylines, widths, mapper, pixels_per_meter: float) -> None:
        for polyline, width_m in zip(polylines, widths or [3.5] * len(polylines)):
            lane_px = max(8.0, width_m * pixels_per_meter * 1.15)
            path = QPainterPath()
            start_x, start_y = mapper(polyline[0])
            path.moveTo(start_x, start_y)
            for point in polyline[1:]:
                x, y = mapper(point)
                path.lineTo(x, y)
            painter.setPen(QPen(QColor('#31363f'), lane_px + 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPath(path)
            painter.setPen(QPen(QColor('#4d5561'), lane_px, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPath(path)
            painter.setPen(QPen(QColor('#e9ecef'), max(1.0, lane_px * 0.10), Qt.DashLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPath(path)

    def _draw_vehicle_trails(self, painter: QPainter, trails: list[list[tuple[float, float]]], mapper) -> None:
        if not trails:
            return
        for trail in trails:
            if len(trail) < 2:
                continue
            selected = False
            if self.selected_vehicle_id is not None:
                for glyph in self.vehicle_glyphs:
                    if glyph.vehicle_id == self.selected_vehicle_id and any(abs(glyph.x - x) < 1e-6 and abs(glyph.y - y) < 1e-6 for x, y in trail):
                        selected = True
                        break
            color = QColor(245, 158, 11, 220 if selected else 90)
            width = 3 if selected else 2
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            for idx in range(len(trail) - 1):
                x1, y1 = mapper(trail[idx])
                x2, y2 = mapper(trail[idx + 1])
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

    def _draw_receivers(self, painter: QPainter, points, mapper) -> None:
        for label, x, y in points:
            px, py = mapper((x, y))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 180)))
            painter.drawEllipse(QPointF(px, py), 7, 7)
            painter.setPen(QPen(QColor('#0f172a'), 1))
            painter.setBrush(QBrush(QColor('#0f172a')))
            painter.drawEllipse(QPointF(px, py), 4, 4)
            painter.drawText(int(px) + 8, int(py) - 8, label)

    def _draw_vehicle_glyphs(self, painter: QPainter, glyphs: list[VehicleGlyph], mapper, pixels_per_meter: float) -> None:
        if not glyphs:
            return
        body_length = max(12.0, 4.5 * pixels_per_meter)
        body_width = max(7.0, 2.0 * pixels_per_meter)
        selected_exists = self.selected_vehicle_id is not None
        for glyph in glyphs:
            px, py = mapper((glyph.x, glyph.y))
            painter.save()
            painter.translate(px, py)
            painter.rotate(-glyph.heading_deg)
            is_selected = glyph.vehicle_id == self.selected_vehicle_id
            alpha = 255 if (not selected_exists or is_selected) else 95
            outline = QColor('#0f172a' if is_selected else '#5b3414')
            outline.setAlpha(alpha)
            fill = self._speed_color(glyph.speed_mps)
            fill.setAlpha(alpha)
            painter.setPen(QPen(outline, 2 if is_selected else 1))
            painter.setBrush(QBrush(fill))
            body = QPainterPath()
            body.moveTo(body_length * 0.55, 0)
            body.lineTo(body_length * 0.15, -body_width * 0.65)
            body.lineTo(-body_length * 0.55, -body_width * 0.55)
            body.lineTo(-body_length * 0.55, body_width * 0.55)
            body.lineTo(body_length * 0.15, body_width * 0.65)
            body.closeSubpath()
            painter.drawPath(body)
            if is_selected:
                painter.setPen(QPen(QColor('#f8fafc'), 2))
                painter.drawPath(body)
            wheel_color = QColor('#1f2937')
            wheel_color.setAlpha(alpha)
            painter.setBrush(QBrush(wheel_color))
            wheel_radius = max(1.5, body_width * 0.14)
            for wheel_x, wheel_y in [(-body_length * 0.25, -body_width * 0.55), (-body_length * 0.25, body_width * 0.55), (body_length * 0.15, -body_width * 0.55), (body_length * 0.15, body_width * 0.55)]:
                painter.drawEllipse(QPointF(wheel_x, wheel_y), wheel_radius, wheel_radius)
            painter.restore()


class SceneView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel('Scene View')
        title.setStyleSheet('font-size: 22px; font-weight: 700;')
        layout.addWidget(title)

        splitter = QSplitter()
        layout.addWidget(splitter, 1)

        self.canvas = SceneCanvas()
        splitter.addWidget(self.canvas)

        self.legend_box = QTextEdit()
        self.legend_box.setReadOnly(True)
        self.legend_box.setMaximumWidth(280)
        splitter.addWidget(self.legend_box)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

    def set_snapshot(self, snapshot: SceneSnapshot | None) -> None:
        self.canvas.set_snapshot(snapshot)
        self.canvas.set_vehicle_points([])
        if snapshot is None:
            self.legend_box.setPlainText('No scene snapshot loaded.')
            return

        min_x, min_y, max_x, max_y = snapshot.bounds
        lines = [
            'Layers',
            '- Road network',
            '- Junctions',
            '- Noise barriers',
            '- Terrain edges',
            '- Buildings',
            '- Ground surfaces',
            '- Vegetation zones',
            '- Receivers',
            '- Heatmap overlay (if loaded)',
            '',
            'Counts',
            f'- Road lanes: {len(snapshot.road_layer.polylines)}',
            f'- Junction polygons: {len(snapshot.junction_layer.polygons)}',
            f'- Barriers: {len(snapshot.barrier_layer.polylines)}',
            f'- Terrain edges: {len(snapshot.terrain_layer.polylines)}',
            f'- Buildings: {len(snapshot.building_layer.polygons)}',
            f'- Ground surfaces: {len(snapshot.ground_layer.polygons)}',
            f'- Vegetation zones: {len(snapshot.vegetation_layer.polygons)}',
            f'- Receivers: {len(snapshot.receiver_layer.points)}',
            '',
            'Controls',
            '- Wheel: zoom',
            '- Drag: pan',
            '- Double-click: reset',
            '- Hover: lane / receiver / vehicle / grid cell info',
            '- Click scene object: select in editor',
            '- Drag selected object or its handles to edit geometry',
            '',
            'Bounds',
            f'- min_x: {min_x:.1f}',
            f'- min_y: {min_y:.1f}',
            f'- max_x: {max_x:.1f}',
            f'- max_y: {max_y:.1f}',
        ]
        self.legend_box.setPlainText('\n'.join(lines))

    def set_selected_scene_object(self, object_type: str | None, object_id: str | None) -> None:
        self.canvas.set_selected_scene_object(object_type, object_id)

    def start_draw_mode(self, object_type: str, template: dict | None = None) -> None:
        self.canvas.start_draw_mode(object_type, template)

    def finish_draw_mode(self) -> None:
        self.canvas.finish_draw_mode()

    def cancel_draw_mode(self) -> None:
        self.canvas.cancel_draw_mode()
