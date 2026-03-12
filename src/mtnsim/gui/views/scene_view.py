from __future__ import annotations

from dataclasses import dataclass
from math import atan2, degrees, hypot

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QBrush, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QLabel, QSplitter, QTextEdit, QToolTip, QVBoxLayout, QWidget

from mtnsim.gui.controllers.scene_controller import SceneSnapshot


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
    body_color: str = '#f59e0b'


class SceneCanvas(QWidget):
    hover_text_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.snapshot: SceneSnapshot | None = None
        self.vehicle_glyphs: list[VehicleGlyph] = []
        self._zoom = 1.0
        self._pan = QPointF(0.0, 0.0)
        self._dragging = False
        self._last_mouse_pos = QPointF()
        self._hover_text = ''
        self.setMinimumHeight(420)
        self.setMouseTracking(True)

    def set_snapshot(self, snapshot: SceneSnapshot | None) -> None:
        self.snapshot = snapshot
        self.reset_view()

    def set_vehicle_points(self, vehicle_points: list[VehicleGlyph]) -> None:
        self.vehicle_glyphs = vehicle_points
        self.update()

    def reset_view(self) -> None:
        self._zoom = 1.0
        self._pan = QPointF(0.0, 0.0)
        self._hover_text = ''
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
            self._dragging = True
            self._last_mouse_pos = event.position()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._dragging:
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
            self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
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
        self._draw_road_bands(painter, self.snapshot.road_layer.polylines, self.snapshot.road_layer.widths, map_point, pixels_per_meter)
        self._draw_polygons(painter, self.snapshot.building_layer.polygons, map_point, LayerStyle('#315a9f', 2, '#b9ccef'))
        self._draw_polylines(painter, self.snapshot.barrier_layer.polylines, map_point, LayerStyle('#cb4335', 4))
        self._draw_polylines(painter, self.snapshot.terrain_layer.polylines, map_point, LayerStyle('#7c4a21', 3))
        self._draw_receivers(painter, self.snapshot.receiver_layer.points, map_point)
        self._draw_vehicle_glyphs(painter, self.vehicle_glyphs, map_point, pixels_per_meter)
        painter.restore()

        self._draw_overlay(painter)

    def _plot_rect(self) -> QRectF:
        margin = 28
        return QRectF(self.rect().adjusted(margin, margin, -margin, -margin))

    def _mapping_context(self):
        plot_rect = self._plot_rect()
        min_x, min_y, max_x, max_y = self.snapshot.bounds
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)
        pixels_per_meter = min(plot_rect.width() / span_x, plot_rect.height() / span_y)

        def map_point(point: tuple[float, float]) -> tuple[float, float]:
            x_ratio = (point[0] - min_x) / span_x
            y_ratio = (point[1] - min_y) / span_y
            px = plot_rect.left() + (plot_rect.width() * x_ratio)
            py = plot_rect.bottom() - (plot_rect.height() * y_ratio)
            return px, py

        return plot_rect, pixels_per_meter, map_point

    def _transform_screen_point(self, point: tuple[float, float], plot_rect: QRectF) -> QPointF:
        center = QPointF(plot_rect.center())
        base = QPointF(point[0], point[1])
        return QPointF(
            center.x() + ((base.x() - center.x()) * self._zoom) + self._pan.x(),
            center.y() + ((base.y() - center.y()) * self._zoom) + self._pan.y(),
        )

    def _distance_to_segment(self, point: QPointF, start: QPointF, end: QPointF) -> float:
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            return hypot(point.x() - start.x(), point.y() - start.y())
        t = ((point.x() - start.x()) * dx + (point.y() - start.y()) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        proj = QPointF(start.x() + (t * dx), start.y() + (t * dy))
        return hypot(point.x() - proj.x(), point.y() - proj.y())

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
                nearest_text = f'Vehicle {glyph.vehicle_id} | x={glyph.x:.1f}, y={glyph.y:.1f}, heading={glyph.heading_deg:.0f} deg'

        for label, x, y in self.snapshot.receiver_layer.points:
            pos = self._transform_screen_point(map_point((x, y)), plot_rect)
            distance = hypot(local_pos.x() - pos.x(), local_pos.y() - pos.y())
            if distance < nearest_distance and distance <= 14:
                nearest_distance = distance
                nearest_text = f'Receiver {label} | x={x:.1f}, y={y:.1f}'

        for index, (polyline, width_m) in enumerate(zip(self.snapshot.road_layer.polylines, self.snapshot.road_layer.widths), start=1):
            for seg_index in range(len(polyline) - 1):
                start = self._transform_screen_point(map_point(polyline[seg_index]), plot_rect)
                end = self._transform_screen_point(map_point(polyline[seg_index + 1]), plot_rect)
                distance = self._distance_to_segment(local_pos, start, end)
                threshold = max(8.0, width_m * pixels_per_meter * 0.55 * self._zoom)
                if distance < nearest_distance and distance <= threshold:
                    nearest_distance = distance
                    nearest_text = f'Lane {index} | width={width_m:.1f} m'

        for index, polygon in enumerate(self.snapshot.building_layer.polygons, start=1):
            qpolygon = QPolygonF([self._transform_screen_point(map_point(point), plot_rect) for point in polygon])
            if qpolygon.containsPoint(local_pos, Qt.OddEvenFill):
                return f'Building {index} | footprint points={len(polygon)}'

        return nearest_text

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
        if self._hover_text:
            overlay_lines.append(self._hover_text)
        text = '\n'.join(overlay_lines)
        box = QRectF(16, 16, min(self.width() * 0.48, 420), 86 if not self._hover_text else 112)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 195))
        painter.drawRoundedRect(box, 8, 8)
        painter.setPen(QPen(QColor('#1f2937'), 1))
        painter.drawText(box.adjusted(10, 8, -10, -8), Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, text)

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
        for glyph in glyphs:
            px, py = mapper((glyph.x, glyph.y))
            painter.save()
            painter.translate(px, py)
            painter.rotate(-glyph.heading_deg)
            painter.setPen(QPen(QColor('#5b3414'), 1))
            painter.setBrush(QBrush(QColor(glyph.body_color)))
            body = QPainterPath()
            body.moveTo(body_length * 0.55, 0)
            body.lineTo(body_length * 0.15, -body_width * 0.65)
            body.lineTo(-body_length * 0.55, -body_width * 0.55)
            body.lineTo(-body_length * 0.55, body_width * 0.55)
            body.lineTo(body_length * 0.15, body_width * 0.65)
            body.closeSubpath()
            painter.drawPath(body)
            painter.setBrush(QBrush(QColor('#1f2937')))
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
            '',
            'Bounds',
            f'- min_x: {min_x:.1f}',
            f'- min_y: {min_y:.1f}',
            f'- max_x: {max_x:.1f}',
            f'- max_y: {max_y:.1f}',
        ]
        self.legend_box.setPlainText('\n'.join(lines))
