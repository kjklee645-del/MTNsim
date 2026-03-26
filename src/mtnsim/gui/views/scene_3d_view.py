from __future__ import annotations

from math import atan2, cos, hypot, radians, sin
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from mtnsim.gui.models.scene_3d import GridRegion3D, LineWall3D, PrismMesh3D, RoadMesh3D, Scene3DFrame, SurfacePolygon3D
from mtnsim.schemas.results import RunResultSummary


class Scene3DCanvas(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.frame_data: Scene3DFrame | None = None
        self.show_roads = True
        self.show_receivers = True
        self.show_vehicles = True
        self.show_vehicle_trails = True
        self.show_source_field = True
        self.show_barriers = True
        self.show_buildings = True
        self.show_ground = True
        self.show_vegetation = True
        self.show_grid_region = True
        self.show_noise_surface = True
        self.render_mode = 'raised'
        self.auto_range = True
        self.min_db_override = 40.0
        self.max_db_override = 90.0
        self.zoom_factor = 1.0
        self.yaw_deg = 36.0
        self.pitch_deg = 30.0
        self.pan_offset = QPointF(0.0, 0.0)
        self._drag_last_pos: QPoint | None = None
        self._drag_mode: str | None = None
        self._last_noise_range: tuple[float, float] | None = None
        self._hover_targets: list[dict[str, object]] = []
        self._hovered_target: dict[str, object] | None = None
        self._last_pointer_pos: QPoint | None = None
        self.setMinimumSize(240, 140)
        self.setMouseTracking(True)

    @property
    def last_noise_range(self) -> tuple[float, float] | None:
        return self._last_noise_range

    def set_frame(self, frame: Scene3DFrame | None) -> None:
        self.frame_data = frame
        self.update()

    def set_layer_visibility(
        self,
        *,
        roads: bool,
        receivers: bool,
        vehicles: bool,
        vehicle_trails: bool,
        barriers: bool,
        buildings: bool,
        ground: bool,
        vegetation: bool,
        grid_region: bool,
        noise_surface: bool,
        source_field: bool,
    ) -> None:
        self.show_roads = roads
        self.show_receivers = receivers
        self.show_vehicles = vehicles
        self.show_vehicle_trails = vehicle_trails
        self.show_barriers = barriers
        self.show_buildings = buildings
        self.show_ground = ground
        self.show_vegetation = vegetation
        self.show_grid_region = grid_region
        self.show_noise_surface = noise_surface
        self.show_source_field = source_field
        self.update()

    def set_noise_display(self, *, render_mode: str, auto_range: bool, min_db: float, max_db: float) -> None:
        self.render_mode = render_mode
        self.auto_range = auto_range
        self.min_db_override = min_db
        self.max_db_override = max_db
        self.update()

    def reset_camera(self) -> None:
        self.zoom_factor = 1.0
        self.yaw_deg = 36.0
        self.pitch_deg = 30.0
        self.pan_offset = QPointF(0.0, 0.0)
        self.update()

    def center_on_world_point(self, x: float, y: float, z: float = 0.0) -> None:
        frame = self.frame_data
        if frame is None:
            return
        min_x, min_y, max_x, max_y = frame.bounds
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)
        center_x = (min_x + max_x) * 0.5
        center_y = (min_y + max_y) * 0.5
        yaw = radians(self.yaw_deg)
        pitch = radians(self.pitch_deg)
        cos_yaw = cos(yaw)
        sin_yaw = sin(yaw)
        sin_pitch = sin(pitch)
        base_scale = min(
            (self.width() - 120) / max(span_x + span_y, 1.0),
            (self.height() - 160) / max((span_x + span_y) * 0.7 + 40.0, 1.0),
        )
        scale = max(base_scale * self.zoom_factor, 0.2)
        dx = x - center_x
        dy = y - center_y
        rx = dx * cos_yaw - dy * sin_yaw
        ry = dx * sin_yaw + dy * cos_yaw
        sx = rx * scale
        sy = ry * sin_pitch * scale - z * scale * 3.0
        target = QPointF(self.width() * 0.5, self.height() * 0.62)
        current = QPointF(self.width() * 0.5 + self.pan_offset.x() + sx, self.height() * 0.70 + self.pan_offset.y() + sy)
        self.pan_offset += target - current
        self.update()

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        if delta == 0:
            return
        if delta > 0:
            self.zoom_factor *= 1.1
        else:
            self.zoom_factor /= 1.1
        self.zoom_factor = max(0.3, min(4.0, self.zoom_factor))
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_mode = 'rotate'
            self._drag_last_pos = event.position().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
        elif event.button() in {Qt.RightButton, Qt.MiddleButton}:
            self._drag_mode = 'pan'
            self._drag_last_pos = event.position().toPoint()
            self.setCursor(Qt.SizeAllCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        current = event.position().toPoint()
        self._last_pointer_pos = current
        if self._drag_last_pos is None or self._drag_mode is None:
            self._update_hover_target(current)
            super().mouseMoveEvent(event)
            return
        delta = current - self._drag_last_pos
        self._drag_last_pos = current
        if self._drag_mode == 'rotate':
            self.yaw_deg += delta.x() * 0.4
            self.pitch_deg -= delta.y() * 0.25
            self.pitch_deg = max(8.0, min(70.0, self.pitch_deg))
        elif self._drag_mode == 'pan':
            self.pan_offset += QPointF(delta.x(), delta.y())
        self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_mode = None
        self._drag_last_pos = None
        self.unsetCursor()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self.reset_camera()
        super().mouseDoubleClickEvent(event)

    def leaveEvent(self, event) -> None:
        self._last_pointer_pos = None
        self._hovered_target = None
        self.update()
        super().leaveEvent(event)

    def _update_hover_target(self, position: QPoint | None) -> None:
        previous = self._hovered_target
        if position is None or not self._hover_targets:
            self._hovered_target = None
        else:
            px = float(position.x())
            py = float(position.y())
            best = None
            best_dist = 1e9
            for item in self._hover_targets:
                point = item['point']
                dx = float(point.x()) - px
                dy = float(point.y()) - py
                dist = hypot(dx, dy)
                if dist <= float(item.get('radius', 16.0)) and dist < best_dist:
                    best = item
                    best_dist = dist
            self._hovered_target = best
        if previous != self._hovered_target:
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        background = QLinearGradient(0, 0, 0, self.height())
        background.setColorAt(0.0, QColor('#182534'))
        background.setColorAt(0.35, QColor('#121b24'))
        background.setColorAt(1.0, QColor('#0b1117'))
        painter.fillRect(self.rect(), background)

        frame = self.frame_data
        if frame is None:
            painter.setPen(QColor('#9fb2c6'))
            painter.drawText(self.rect(), Qt.AlignCenter, '3D scene is not available yet for the current selection.')
            return

        inner_rect = self.rect().adjusted(16, 16, -16, -16)
        stage = QLinearGradient(0, inner_rect.top(), 0, inner_rect.bottom())
        stage.setColorAt(0.0, QColor('#16212d'))
        stage.setColorAt(0.5, QColor('#121b24'))
        stage.setColorAt(1.0, QColor('#0f1720'))
        painter.fillRect(inner_rect, stage)
        haze = QLinearGradient(0, inner_rect.top(), 0, inner_rect.bottom())
        haze.setColorAt(0.0, QColor(90, 160, 255, 28))
        haze.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(inner_rect, haze)
        min_x, min_y, max_x, max_y = frame.bounds
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)
        center_x = (min_x + max_x) * 0.5
        center_y = (min_y + max_y) * 0.5
        yaw = radians(self.yaw_deg)
        pitch = radians(self.pitch_deg)
        cos_yaw = cos(yaw)
        sin_yaw = sin(yaw)
        sin_pitch = sin(pitch)
        base_scale = min(
            (self.width() - 120) / max(span_x + span_y, 1.0),
            (self.height() - 160) / max((span_x + span_y) * 0.7 + 40.0, 1.0),
        )
        scale = max(base_scale * self.zoom_factor, 0.2)
        origin = QPointF(self.width() * 0.5 + self.pan_offset.x(), self.height() * 0.70 + self.pan_offset.y())

        def project(x: float, y: float, z: float) -> QPointF:
            dx = x - center_x
            dy = y - center_y
            rx = dx * cos_yaw - dy * sin_yaw
            ry = dx * sin_yaw + dy * cos_yaw
            sx = rx * scale
            sy = ry * sin_pitch * scale - z * scale * 3.0
            return QPointF(origin.x() + sx, origin.y() + sy)

        def draw_surface(surface: SurfacePolygon3D, alpha: int = 220) -> None:
            polygon = QPolygonF([project(x, y, surface.z) for x, y in surface.polygon])
            color = QColor(surface.color)
            color.setAlpha(alpha)
            painter.setBrush(color)
            painter.setPen(QPen(QColor(surface.edge_color), 1.2))
            painter.drawPolygon(polygon)

        def lerp_point(p1: QPointF, p2: QPointF, t: float) -> QPointF:
            return QPointF(p1.x() + (p2.x() - p1.x()) * t, p1.y() + (p2.y() - p1.y()) * t)

        hover_targets: list[dict[str, object]] = []

        def register_hover_target(point: QPointF, label: str, kind: str, *, radius: float = 16.0) -> None:
            if not label:
                return
            hover_targets.append({
                'point': QPointF(point),
                'label': label,
                'kind': kind,
                'radius': radius,
            })

        def draw_screen_label(anchor: QPointF, text_value: str, *, fill: str = '#111a23', border: str = '#314355', fg: str = '#eef6ff') -> None:
            if not text_value:
                return
            metrics = painter.fontMetrics()
            width = metrics.horizontalAdvance(text_value) + 14
            height = metrics.height() + 8
            x = anchor.x() + 8
            y = anchor.y() - height - 6
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(fill))
            painter.drawRoundedRect(int(x), int(y), int(width), int(height), 7, 7)
            painter.setPen(QPen(QColor(border), 1.0))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(int(x), int(y), int(width), int(height), 7, 7)
            painter.setPen(QColor(fg))
            painter.drawText(int(x) + 7, int(y) + height - 6, text_value)

        def draw_prism(mesh: PrismMesh3D) -> None:
            base = [project(x, y, 0.0) for x, y in mesh.footprint]
            top = [project(x, y, mesh.height) for x, y in mesh.footprint]
            side_color = QColor(mesh.color).darker(135)
            roof_color = QColor(mesh.color).lighter(118)
            center = QPointF(sum(point.x() for point in top) / len(top), sum(point.y() for point in top) / len(top)) if top else QPointF()
            for idx in range(len(base)):
                nxt = (idx + 1) % len(base)
                side = QPolygonF([base[idx], base[nxt], top[nxt], top[idx]])
                painter.setBrush(side_color)
                painter.setPen(QPen(QColor(mesh.edge_color), 1.0))
                painter.drawPolygon(side)
                painter.setPen(QPen(QColor('#8fb3d9'), 0.7))
                for t in (0.32, 0.56, 0.8):
                    left = lerp_point(base[idx], top[idx], t)
                    right = lerp_point(base[nxt], top[nxt], t)
                    painter.drawLine(left, right)
                for t in (0.33, 0.66):
                    bottom = lerp_point(base[idx], base[nxt], t)
                    top_p = lerp_point(top[idx], top[nxt], t)
                    painter.drawLine(bottom, top_p)
            painter.setBrush(roof_color)
            painter.setPen(QPen(QColor(mesh.edge_color), 1.3))
            painter.drawPolygon(QPolygonF(top))
            if len(top) >= 3:
                painter.setPen(QPen(QColor('#7dd3fc'), 0.9))
                for idx in range(len(top)):
                    nxt = (idx + 1) % len(top)
                    mid = QPointF((top[idx].x() + top[nxt].x()) * 0.5, (top[idx].y() + top[nxt].y()) * 0.5)
                    painter.drawLine(mid, center)
                if mesh.label:
                    draw_screen_label(center, mesh.label, fill='#16212d', border='#3c5269')
                register_hover_target(center, mesh.label or 'Building', 'Building', radius=20.0)

        def draw_road(mesh: RoadMesh3D) -> None:
            if len(mesh.points) < 2:
                return
            path = QPainterPath()
            path.moveTo(project(mesh.points[0][0], mesh.points[0][1], mesh.z))
            for x, y in mesh.points[1:]:
                path.lineTo(project(x, y, mesh.z))
            body_width = max(mesh.width * scale * 0.12, 3.0)
            shadow_pen = QPen(QColor(8, 12, 18, 190), body_width + 3.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(shadow_pen)
            painter.drawPath(path)
            glow_pen = QPen(QColor(95, 130, 180, 35), body_width + 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(glow_pen)
            painter.drawPath(path)
            asphalt_pen = QPen(QColor('#3a4654'), body_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(asphalt_pen)
            painter.drawPath(path)
            shoulder_pen = QPen(QColor('#6a7687'), max(1.0, body_width * 0.22), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(shoulder_pen)
            painter.drawPath(path)
            edge_pen = QPen(QColor('#d7dce4'), max(1.0, body_width * 0.08), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(edge_pen)
            painter.drawPath(path)
            lane_pen = QPen(QColor(255, 238, 160, 180), max(1.0, body_width * 0.05), Qt.DashLine, Qt.RoundCap, Qt.RoundJoin)
            lane_pen.setDashPattern([8.0, 10.0])
            painter.setPen(lane_pen)
            painter.drawPath(path)

        def draw_wall(mesh: LineWall3D) -> None:
            dx = mesh.end[0] - mesh.start[0]
            dy = mesh.end[1] - mesh.start[1]
            length = hypot(dx, dy)
            if length <= 1e-6:
                return
            nx = -dy / length
            ny = dx / length
            half_t = max(mesh.thickness, 0.8) * 0.5
            s1 = (mesh.start[0] + nx * half_t, mesh.start[1] + ny * half_t)
            s2 = (mesh.start[0] - nx * half_t, mesh.start[1] - ny * half_t)
            e1 = (mesh.end[0] + nx * half_t, mesh.end[1] + ny * half_t)
            e2 = (mesh.end[0] - nx * half_t, mesh.end[1] - ny * half_t)
            p_front_a = project(s1[0], s1[1], 0.0)
            p_front_b = project(e1[0], e1[1], 0.0)
            p_front_c = project(e1[0], e1[1], mesh.height)
            p_front_d = project(s1[0], s1[1], mesh.height)
            front = QPolygonF([p_front_a, p_front_b, p_front_c, p_front_d])
            side = QPolygonF([project(e1[0], e1[1], 0.0), project(e2[0], e2[1], 0.0), project(e2[0], e2[1], mesh.height), project(e1[0], e1[1], mesh.height)])
            top = QPolygonF([project(s1[0], s1[1], mesh.height), project(e1[0], e1[1], mesh.height), project(e2[0], e2[1], mesh.height), project(s2[0], s2[1], mesh.height)])
            is_barrier = QColor(mesh.color).red() > QColor(mesh.color).green()
            painter.setPen(QPen(QColor(mesh.edge_color), 1.0))
            painter.setBrush(QColor(mesh.color).darker(125))
            painter.drawPolygon(side)
            painter.setBrush(QColor(mesh.color))
            painter.drawPolygon(front)
            if is_barrier:
                painter.setPen(QPen(QColor('#ffd7b8'), 0.9))
                for t in (0.18, 0.36, 0.54, 0.72, 0.9):
                    left = lerp_point(p_front_a, p_front_d, t)
                    right = lerp_point(p_front_b, p_front_c, t)
                    painter.drawLine(left, right)
                painter.setPen(QPen(QColor('#8b3b10'), 1.0))
                for t in (0.15, 0.5, 0.85):
                    bottom = lerp_point(p_front_a, p_front_b, t)
                    top_p = lerp_point(p_front_d, p_front_c, t)
                    painter.drawLine(bottom, top_p)
            else:
                painter.setPen(QPen(QColor('#a6b391'), 0.8, Qt.DashLine))
                for t in (0.2, 0.4, 0.6, 0.8):
                    bottom = lerp_point(p_front_a, p_front_b, t - 0.12)
                    top_p = lerp_point(p_front_d, p_front_c, t + 0.08)
                    painter.drawLine(bottom, top_p)
            painter.setBrush(QColor(mesh.color).lighter(118))
            painter.setPen(QPen(QColor('#fff0d9') if is_barrier else '#dfe8cf', 1.1))
            painter.drawPolygon(top)
            anchor = QPointF((p_front_d.x() + p_front_c.x()) * 0.5, (p_front_d.y() + p_front_c.y()) * 0.5)
            register_hover_target(anchor, mesh.label or ('Barrier' if is_barrier else 'Terrain Edge'), 'Barrier' if is_barrier else 'Terrain', radius=20.0)

        def noise_color(value: float, min_db: float, max_db: float) -> QColor:
            span = max(max_db - min_db, 1.0)
            t = max(0.0, min(1.0, (value - min_db) / span))
            if t < 0.25:
                local = t / 0.25
                r = int(30 + 20 * local)
                g = int(80 + 110 * local)
                b = int(170 - 20 * local)
            elif t < 0.5:
                local = (t - 0.25) / 0.25
                r = int(50 + 70 * local)
                g = int(190 + 30 * local)
                b = int(150 - 90 * local)
            elif t < 0.75:
                local = (t - 0.5) / 0.25
                r = int(120 + 100 * local)
                g = int(220 - 70 * local)
                b = int(60 - 40 * local)
            else:
                local = (t - 0.75) / 0.25
                r = int(220 + 20 * local)
                g = int(150 - 80 * local)
                b = int(20 - 10 * local)
            return QColor(r, g, b)

        def draw_noise_surface(cells) -> None:
            if not cells:
                self._last_noise_range = None
                return
            values = [cell.value_db for cell in cells]
            min_db = min(values) if self.auto_range else min(self.min_db_override, self.max_db_override - 0.1)
            max_db = max(values) if self.auto_range else max(self.max_db_override, self.min_db_override + 0.1)
            self._last_noise_range = (min_db, max_db)
            for cell in sorted(cells, key=lambda item: item.x + item.y):
                half = cell.cell_size * 0.5
                normalized = max(0.0, min(1.0, (cell.value_db - min_db) / max(max_db - min_db, 1.0)))
                height = 0.18 if self.render_mode == 'flat' else max(normalized * 3.5, 0.18)
                corners = [
                    (cell.x - half, cell.y - half),
                    (cell.x + half, cell.y - half),
                    (cell.x + half, cell.y + half),
                    (cell.x - half, cell.y + half),
                ]
                top = QPolygonF([project(x, y, height) for x, y in corners])
                color = noise_color(cell.value_db, min_db, max_db)
                base_points = [project(x, y, 0.0) for x, y in corners]
                if self.render_mode != 'flat':
                    side = QColor(color).darker(145)
                    for idx in range(4):
                        nxt = (idx + 1) % 4
                        side_poly = QPolygonF([base_points[idx], base_points[nxt], top[nxt], top[idx]])
                        painter.setBrush(side)
                        painter.setPen(QPen(QColor('#10161d'), 0.35))
                        painter.drawPolygon(side_poly)
                fill = QColor(color)
                fill.setAlpha(215)
                painter.setBrush(fill)
                painter.setPen(QPen(QColor('#0f1722'), 0.35))
                painter.drawPolygon(top)

        def draw_grid_region(mesh: GridRegion3D) -> None:
            min_x2, min_y2, max_x2, max_y2 = mesh.bounds
            surface = [(min_x2, min_y2), (max_x2, min_y2), (max_x2, max_y2), (min_x2, max_y2)]
            poly = QPolygonF([project(x, y, mesh.z) for x, y in surface])
            fill = QColor(mesh.color)
            fill.setAlpha(35)
            painter.setBrush(fill)
            painter.setPen(QPen(QColor(mesh.color), 1.5, Qt.DashLine))
            painter.drawPolygon(poly)

        if self.show_ground:
            for surface in frame.ground_surfaces:
                draw_surface(surface, alpha=170)
        if self.show_vegetation:
            for surface in frame.vegetation_zones:
                draw_surface(surface, alpha=165)
                if surface.polygon:
                    cx = sum(x for x, _ in surface.polygon) / len(surface.polygon)
                    cy = sum(y for _, y in surface.polygon) / len(surface.polygon)
                    anchors = [(cx, cy)] + list(surface.polygon[:min(4, len(surface.polygon))])
                    for idx, (vx, vy) in enumerate(anchors):
                        canopy = project(vx, vy, 2.0 + idx * 0.35)
                        rx = max(8.0, 16.0 - idx * 1.5)
                        ry = max(5.0, 11.0 - idx)
                        painter.setPen(QPen(QColor('#143323'), 0.8))
                        painter.setBrush(QColor(58, 148, 97, 110 if idx else 135))
                        painter.drawEllipse(canopy, rx, ry)
        if self.show_noise_surface:
            draw_noise_surface(frame.noise_cells)
        if self.show_grid_region and frame.grid_region is not None:
            draw_grid_region(frame.grid_region)
        if self.show_vehicle_trails:
            for trail in frame.vehicle_trails:
                if len(trail.points) < 2:
                    continue
                path = QPainterPath()
                path.moveTo(project(trail.points[0][0], trail.points[0][1], trail.z))
                for x, y in trail.points[1:]:
                    path.lineTo(project(x, y, trail.z))
                color = QColor(trail.color)
                color.setAlpha(255 if trail.selected else 150)
                width = 2.4 if trail.selected else 1.3
                painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                painter.drawPath(path)
        if self.show_source_field:
            for link in frame.source_field_links:
                start = project(link.start[0], link.start[1], link.start[2])
                end = project(link.end[0], link.end[1], link.end[2])
                color = QColor(link.color)
                color.setAlpha(165)
                painter.setPen(QPen(color, 1.1, Qt.DashLine))
                painter.drawLine(start, end)
            for overlay in frame.source_field_overlays:
                if len(overlay.footprint) < 3:
                    continue
                base = [project(x, y, 0.0) for x, y in overlay.footprint]
                top = [project(x, y, overlay.height) for x, y in overlay.footprint]
                side_color = QColor(overlay.color).darker(145)
                side_color.setAlpha(int(255 * max(0.05, min(0.95, overlay.opacity)) * 0.65))
                fill_color = QColor(overlay.color)
                fill_color.setAlpha(int(255 * max(0.05, min(0.95, overlay.opacity))))
                for idx in range(len(base)):
                    nxt = (idx + 1) % len(base)
                    side = QPolygonF([base[idx], base[nxt], top[nxt], top[idx]])
                    painter.setBrush(side_color)
                    painter.setPen(QPen(QColor(overlay.edge_color), 0.7))
                    painter.drawPolygon(side)
                painter.setBrush(fill_color)
                painter.setPen(QPen(QColor(overlay.edge_color), 1.1))
                painter.drawPolygon(QPolygonF(top))
        if self.show_roads:
            for road in frame.roads:
                draw_road(road)
        if self.show_barriers:
            for wall in frame.barriers:
                draw_wall(wall)
            for wall in frame.terrain_edges:
                draw_wall(wall)
        if self.show_buildings:
            for building in frame.buildings:
                draw_prism(building)
        if self.show_receivers:
            label_receivers = len(frame.receivers) <= 10
            for marker in frame.receivers:
                base = project(marker.x, marker.y, 0.0)
                top = project(marker.x, marker.y, marker.z + 2.0)
                line_color = QColor('#fff4b2') if marker.highlighted else QColor('#eff6ff')
                fill_color = QColor('#fff4b2') if marker.highlighted else QColor('#eff6ff')
                radius = 4.6 if marker.highlighted else 3.5
                painter.setPen(QPen(line_color, 1.4 if marker.highlighted else 1.3))
                painter.drawLine(base, top)
                painter.setBrush(fill_color)
                painter.drawEllipse(top, radius, radius)
                if marker.highlighted or label_receivers:
                    draw_screen_label(top, marker.label, fill='#121b24', border='#394d63', fg='#fff4b2' if marker.highlighted else '#eef6ff')
                register_hover_target(top, marker.label, 'Receiver', radius=14.0)

        trail_heading = {}
        for trail in frame.vehicle_trails:
            if len(trail.points) >= 2:
                x1, y1 = trail.points[-2]
                x2, y2 = trail.points[-1]
                trail_heading[(x2, y2)] = atan2(y2 - y1, x2 - x1)

        if self.show_vehicles:
            label_vehicles = len(frame.vehicles) <= 6
            for vehicle in frame.vehicles:
                base = project(vehicle.x, vehicle.y, 0.0)
                top = project(vehicle.x, vehicle.y, vehicle.z)
                heading = trail_heading.get((vehicle.x, vehicle.y), 0.0)
                nose_world = (vehicle.x + cos(heading) * 3.2, vehicle.y + sin(heading) * 3.2)
                nose_point = project(nose_world[0], nose_world[1], vehicle.z)
                vx = nose_point.x() - top.x()
                vy = nose_point.y() - top.y()
                vlen = hypot(vx, vy)
                if vlen <= 1e-6:
                    vx, vy, vlen = 1.0, -0.25, 1.03
                ux, uy = vx / vlen, vy / vlen
                px, py = -uy, ux
                fill = QColor(vehicle.color)
                border = QColor('#f8fafc') if vehicle.selected else QColor('#08111c')
                body_len = 11.0 if vehicle.selected else 9.0
                body_w = 5.8 if vehicle.selected else 4.8
                shadow = QPolygonF([
                    QPointF(top.x() - ux * body_len * 0.45 + px * body_w * 0.55 + 1.8, top.y() - uy * body_len * 0.45 + py * body_w * 0.55 + 2.4),
                    QPointF(top.x() + ux * body_len * 0.9 + 1.8, top.y() + uy * body_len * 0.9 + 2.4),
                    QPointF(top.x() - ux * body_len * 0.35 - px * body_w * 0.55 + 1.8, top.y() - uy * body_len * 0.35 - py * body_w * 0.55 + 2.4),
                ])
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(4, 8, 14, 120))
                painter.drawPolygon(shadow)
                body = QPolygonF([
                    QPointF(top.x() - ux * body_len * 0.45 + px * body_w * 0.52, top.y() - uy * body_len * 0.45 + py * body_w * 0.52),
                    QPointF(top.x() + ux * body_len * 0.95, top.y() + uy * body_len * 0.95),
                    QPointF(top.x() - ux * body_len * 0.10 - px * body_w * 0.62, top.y() - uy * body_len * 0.10 - py * body_w * 0.62),
                    QPointF(top.x() - ux * body_len * 0.60 - px * body_w * 0.44, top.y() - uy * body_len * 0.60 - py * body_w * 0.44),
                ])
                painter.setBrush(fill)
                painter.setPen(QPen(border, 1.4 if vehicle.selected else 1.0))
                painter.drawPolygon(body)
                windshield = QPolygonF([
                    QPointF(top.x() + ux * body_len * 0.25 + px * body_w * 0.25, top.y() + uy * body_len * 0.25 + py * body_w * 0.25),
                    QPointF(top.x() + ux * body_len * 0.58, top.y() + uy * body_len * 0.58),
                    QPointF(top.x() + ux * body_len * 0.12 - px * body_w * 0.25, top.y() + uy * body_len * 0.12 - py * body_w * 0.25),
                ])
                painter.setBrush(QColor('#d9f3ff'))
                painter.setPen(Qt.NoPen)
                painter.drawPolygon(windshield)
                painter.setPen(QPen(QColor('#9ad8ff'), 0.8))
                painter.drawLine(base, QPointF(top.x() - ux * body_len * 0.25, top.y() - uy * body_len * 0.25))
                vehicle_label = vehicle.vehicle_id if vehicle.selected else vehicle.vehicle_type or vehicle.vehicle_id
                if vehicle.selected or label_vehicles:
                    draw_screen_label(top, vehicle_label, fill='#102032', border='#40627c', fg='#eef8ff')
                register_hover_target(top, vehicle_label, 'Vehicle', radius=16.0)

        self._hover_targets = hover_targets
        if self._last_pointer_pos is None or not hover_targets:
            self._hovered_target = None
        else:
            px = float(self._last_pointer_pos.x())
            py = float(self._last_pointer_pos.y())
            best = None
            best_dist = 1e9
            for item in hover_targets:
                point = item['point']
                dx = float(point.x()) - px
                dy = float(point.y()) - py
                dist = hypot(dx, dy)
                if dist <= float(item.get('radius', 16.0)) and dist < best_dist:
                    best = item
                    best_dist = dist
            self._hovered_target = best
        if self._hovered_target is not None:
            point = self._hovered_target['point']
            radius = float(self._hovered_target.get('radius', 16.0)) + 4.0
            halo_fill = QColor('#7dd3fc')
            halo_fill.setAlpha(34)
            painter.setBrush(halo_fill)
            painter.setPen(QPen(QColor('#7dd3fc'), 1.8))
            painter.drawEllipse(point, radius, radius)
            draw_screen_label(point, f"{self._hovered_target['kind']}: {self._hovered_target['label']}", fill='#0d1720', border='#7dd3fc', fg='#eef8ff')

        painter.setPen(QColor('#f4f7fb'))
        painter.drawText(24, 28, '3D Scene & Noise')
        painter.setPen(QColor('#93a7bd'))
        painter.drawText(24, 48, 'Wheel: zoom | Left drag: orbit | Right drag: pan | Double-click: reset')
        self._draw_legend(painter)

    def _draw_legend(self, painter: QPainter) -> None:
        legend_rect_x = self.width() - 220
        legend_rect_y = 24
        legend_w = 180
        legend_h = 64
        panel = QColor('#111a23')
        panel.setAlpha(225)
        painter.setBrush(panel)
        painter.setPen(QPen(QColor('#314355'), 1.0))
        painter.drawRoundedRect(legend_rect_x, legend_rect_y, legend_w, legend_h, 10, 10)
        painter.setPen(QColor('#f4f7fb'))
        painter.drawText(legend_rect_x + 14, legend_rect_y + 18, 'dB')
        min_db, max_db = self._last_noise_range or (self.min_db_override, self.max_db_override)
        bar_x = legend_rect_x + 14
        bar_y = legend_rect_y + 28
        bar_w = legend_w - 28
        bar_h = 12
        for idx in range(bar_w):
            t = idx / max(bar_w - 1, 1)
            painter.setPen(QPen(self._legend_color(t), 1.0))
            painter.drawLine(bar_x + idx, bar_y, bar_x + idx, bar_y + bar_h)
        painter.setPen(QColor('#d8e2ef'))
        painter.drawText(bar_x, legend_rect_y + 56, f'{min_db:.0f}')
        painter.drawText(bar_x + bar_w - 26, legend_rect_y + 56, f'{max_db:.0f}')

    def _legend_color(self, t: float) -> QColor:
        t = max(0.0, min(1.0, t))
        if t < 0.25:
            local = t / 0.25
            return QColor(int(30 + 20 * local), int(80 + 110 * local), int(170 - 20 * local))
        if t < 0.5:
            local = (t - 0.25) / 0.25
            return QColor(int(50 + 70 * local), int(190 + 30 * local), int(150 - 90 * local))
        if t < 0.75:
            local = (t - 0.5) / 0.25
            return QColor(int(120 + 100 * local), int(220 - 70 * local), int(60 - 40 * local))
        local = (t - 0.75) / 0.25
        return QColor(int(220 + 20 * local), int(150 - 80 * local), int(20 - 10 * local))


class Scene3DView(QWidget):
    open_result_summary_requested = Signal()
    export_snapshot_requested = Signal()
    export_snapshot_hires_requested = Signal()
    export_markdown_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._result_summary: RunResultSummary | None = None
        self._result_summary_path: Path | None = None
        self._playback_time_index: int | None = None
        self._playback_sim_seconds: float | None = None
        self._playback_vehicle_count: int = 0
        self._selected_vehicle_id: str | None = None
        self._follow_selected_vehicle: bool = False
        self._source_field_mode: str = 'off'
        self._affected_receiver_count: int = 0
        self._calc_directivity_preset: str = 'custom'
        self._calc_directivity_vehicle_types: list[str] = []
        self._calc_visual_profile: str = 'custom'
        self._calc_directivity_mode: str = 'isotropic'
        self._calc_directivity_strength_db: float = 6.0
        self._calc_directivity_wedge_angle_deg: float = 70.0
        self._calc_directivity_vertical_strength_db: float = 0.0
        self._calc_directivity_vertical_angle_deg: float = 55.0
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel('3D View')
        title.setObjectName('pageTitle')
        root.addWidget(title)

        helper = QLabel('Static 3D scene and static 3D noise surface. Use the wheel to zoom, left drag to orbit, right drag to pan, and double-click to reset.')
        helper.setWordWrap(True)
        helper.setObjectName('homeHelperLabel')
        root.addWidget(helper)

        top_panel = QWidget()
        top_layout = QVBoxLayout(top_panel)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)

        action_row = QHBoxLayout()
        self.open_result_summary_button = QLabel('<a href="#">Open Result Summary</a>')
        self.open_result_summary_button.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.open_result_summary_button.linkActivated.connect(lambda *_: self.open_result_summary_requested.emit())
        action_row.addWidget(self.open_result_summary_button)
        self.export_snapshot_button = QLabel('<a href="#">Export 3D Snapshot</a>')
        self.export_snapshot_button.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.export_snapshot_button.linkActivated.connect(lambda *_: self.export_snapshot_requested.emit())
        action_row.addWidget(self.export_snapshot_button)
        self.export_snapshot_hires_button = QLabel('<a href="#">Export Hi-Res Snapshot</a>')
        self.export_snapshot_hires_button.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.export_snapshot_hires_button.linkActivated.connect(lambda *_: self.export_snapshot_hires_requested.emit())
        action_row.addWidget(self.export_snapshot_hires_button)
        self.export_markdown_button = QLabel('<a href="#">Export 3D Markdown</a>')
        self.export_markdown_button.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.export_markdown_button.linkActivated.connect(lambda *_: self.export_markdown_requested.emit())
        action_row.addWidget(self.export_markdown_button)
        action_row.addStretch(1)
        top_layout.addLayout(action_row)

        meta_card = QFrame()
        meta_card.setObjectName('infoCard')
        meta_layout = QFormLayout(meta_card)
        meta_layout.setContentsMargins(12, 10, 12, 10)
        meta_layout.setSpacing(8)
        self.run_id_label = QLabel('-')
        self.scenario_label = QLabel('-')
        self.output_label = QLabel('-')
        self.view_mode_label = QLabel('-')
        self.db_range_label = QLabel('-')
        self.noise_cell_label = QLabel('-')
        self.playback_frame_label = QLabel('-')
        self.playback_vehicle_count_label = QLabel('-')
        self.selected_vehicle_label = QLabel('-')
        self.follow_label = QLabel('-')
        self.source_field_label = QLabel('-')
        self.source_field_detail_label = QLabel('-')
        self.directivity_preset_label = QLabel('-')
        self.directivity_vehicle_types_label = QLabel('-')
        self.visual_profile_label = QLabel('-')
        self.affected_receivers_label = QLabel('-')
        meta_layout.addRow('Run ID', self.run_id_label)
        meta_layout.addRow('Scenario', self.scenario_label)
        meta_layout.addRow('Output', self.output_label)
        meta_layout.addRow('View Mode', self.view_mode_label)
        meta_layout.addRow('dB Range', self.db_range_label)
        meta_layout.addRow('Noise Cells', self.noise_cell_label)
        meta_layout.addRow('Playback Frame', self.playback_frame_label)
        meta_layout.addRow('Playback Vehicles', self.playback_vehicle_count_label)
        meta_layout.addRow('Selected Vehicle', self.selected_vehicle_label)
        meta_layout.addRow('Camera Follow', self.follow_label)
        meta_layout.addRow('Source Field', self.source_field_label)
        meta_layout.addRow('Field Detail', self.source_field_detail_label)
        meta_layout.addRow('Directivity Preset', self.directivity_preset_label)
        meta_layout.addRow('Vehicle Types', self.directivity_vehicle_types_label)
        meta_layout.addRow('Visual Profile', self.visual_profile_label)
        meta_layout.addRow('Affected Receivers', self.affected_receivers_label)
        top_layout.addWidget(meta_card)

        controls = QFrame()
        controls.setObjectName('infoCard')
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(12, 10, 12, 10)
        controls_layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        self.roads_check = QCheckBox('Roads')
        self.roads_check.setChecked(True)
        self.receivers_check = QCheckBox('Receivers')
        self.receivers_check.setChecked(True)
        self.vehicles_check = QCheckBox('Vehicles')
        self.vehicles_check.setChecked(True)
        self.vehicle_trails_check = QCheckBox('Vehicle Trails')
        self.vehicle_trails_check.setChecked(True)
        self.source_field_check = QCheckBox('Source Field')
        self.source_field_check.setChecked(True)
        self.highlight_receivers_check = QCheckBox('Highlight Receivers')
        self.highlight_receivers_check.setChecked(True)
        self.receiver_links_check = QCheckBox('Receiver Links')
        self.receiver_links_check.setChecked(True)
        self.follow_selected_check = QCheckBox('Follow selected')
        self.follow_selected_check.setChecked(False)
        self.barriers_check = QCheckBox('Barriers')
        self.barriers_check.setChecked(True)
        self.buildings_check = QCheckBox('Buildings')
        self.buildings_check.setChecked(True)
        self.ground_check = QCheckBox('Ground')
        self.ground_check.setChecked(True)
        self.vegetation_check = QCheckBox('Vegetation')
        self.vegetation_check.setChecked(True)
        self.grid_region_check = QCheckBox('Grid Region')
        self.grid_region_check.setChecked(True)
        self.noise_surface_check = QCheckBox('3D Noise Surface')
        self.noise_surface_check.setChecked(True)
        for widget in [self.roads_check, self.receivers_check, self.vehicles_check, self.vehicle_trails_check, self.source_field_check, self.highlight_receivers_check, self.receiver_links_check, self.follow_selected_check, self.barriers_check, self.buildings_check, self.ground_check, self.vegetation_check, self.grid_region_check, self.noise_surface_check]:
            top_row.addWidget(widget)
        top_row.addStretch(1)
        controls_layout.addLayout(top_row)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)
        bottom_row.addWidget(QLabel('Surface Mode'))
        self.surface_mode_combo = QComboBox()
        self.surface_mode_combo.addItem('Raised Surface', 'raised')
        self.surface_mode_combo.addItem('Color Plate', 'flat')
        bottom_row.addWidget(self.surface_mode_combo)
        bottom_row.addWidget(QLabel('Source Field'))
        self.source_field_mode_combo = QComboBox()
        self.source_field_mode_combo.addItem('Off', 'off')
        self.source_field_mode_combo.addItem('Sphere', 'sphere')
        self.source_field_mode_combo.addItem('Wedge', 'wedge')
        self.source_field_mode_combo.addItem('Dual Wedge', 'dual_wedge')
        bottom_row.addWidget(self.source_field_mode_combo)
        self.link_calc_directivity_check = QCheckBox('Use Calc Directivity')
        self.link_calc_directivity_check.setChecked(True)
        bottom_row.addWidget(self.link_calc_directivity_check)
        bottom_row.addWidget(QLabel('Scale'))
        self.source_field_scale_spin = QDoubleSpinBox()
        self.source_field_scale_spin.setRange(0.2, 4.0)
        self.source_field_scale_spin.setSingleStep(0.1)
        self.source_field_scale_spin.setValue(1.0)
        bottom_row.addWidget(self.source_field_scale_spin)
        bottom_row.addWidget(QLabel('Height'))
        self.source_field_height_spin = QDoubleSpinBox()
        self.source_field_height_spin.setRange(0.2, 4.0)
        self.source_field_height_spin.setSingleStep(0.1)
        self.source_field_height_spin.setValue(1.0)
        bottom_row.addWidget(self.source_field_height_spin)
        bottom_row.addWidget(QLabel('Opacity'))
        self.source_field_opacity_spin = QDoubleSpinBox()
        self.source_field_opacity_spin.setRange(0.05, 0.95)
        self.source_field_opacity_spin.setSingleStep(0.05)
        self.source_field_opacity_spin.setValue(0.32)
        bottom_row.addWidget(self.source_field_opacity_spin)
        bottom_row.addWidget(QLabel('Wedge Angle'))
        self.source_field_wedge_angle_spin = QDoubleSpinBox()
        self.source_field_wedge_angle_spin.setRange(20.0, 160.0)
        self.source_field_wedge_angle_spin.setSingleStep(5.0)
        self.source_field_wedge_angle_spin.setValue(70.0)
        self.source_field_wedge_angle_spin.setSuffix(' deg')
        bottom_row.addWidget(self.source_field_wedge_angle_spin)
        self.auto_range_check = QCheckBox('Auto dB Range')
        self.auto_range_check.setChecked(True)
        bottom_row.addWidget(self.auto_range_check)
        bottom_row.addWidget(QLabel('Min dB'))
        self.min_db_spin = QDoubleSpinBox()
        self.min_db_spin.setRange(0.0, 150.0)
        self.min_db_spin.setValue(40.0)
        self.min_db_spin.setSuffix(' dB')
        bottom_row.addWidget(self.min_db_spin)
        bottom_row.addWidget(QLabel('Max dB'))
        self.max_db_spin = QDoubleSpinBox()
        self.max_db_spin.setRange(0.0, 150.0)
        self.max_db_spin.setValue(90.0)
        self.max_db_spin.setSuffix(' dB')
        bottom_row.addWidget(self.max_db_spin)
        self.reset_button = QPushButton('Reset View')
        bottom_row.addWidget(self.reset_button)
        bottom_row.addStretch(1)
        controls_layout.addLayout(bottom_row)
        top_layout.addWidget(controls)

        self.top_scroll = QScrollArea()
        self.top_scroll.setWidgetResizable(True)
        self.top_scroll.setFrameShape(QFrame.NoFrame)
        self.top_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.top_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.top_scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.top_scroll.setMaximumHeight(260)
        self.top_scroll.setWidget(top_panel)
        root.addWidget(self.top_scroll, 0)

        self.canvas = Scene3DCanvas()
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.canvas, 1)

        for widget in [self.roads_check, self.receivers_check, self.vehicles_check, self.vehicle_trails_check, self.source_field_check, self.highlight_receivers_check, self.receiver_links_check, self.barriers_check, self.buildings_check, self.ground_check, self.vegetation_check, self.grid_region_check, self.noise_surface_check]:
            widget.toggled.connect(self._apply_visibility)
        self.follow_selected_check.toggled.connect(self._on_follow_changed)
        self.source_field_mode_combo.currentIndexChanged.connect(self._apply_noise_display)
        self.link_calc_directivity_check.toggled.connect(self._on_calc_directivity_link_changed)
        self.source_field_scale_spin.valueChanged.connect(self._apply_noise_display)
        self.source_field_height_spin.valueChanged.connect(self._apply_noise_display)
        self.source_field_opacity_spin.valueChanged.connect(self._apply_noise_display)
        self.source_field_wedge_angle_spin.valueChanged.connect(self._apply_noise_display)
        self.surface_mode_combo.currentIndexChanged.connect(self._apply_noise_display)
        self.auto_range_check.toggled.connect(self._apply_noise_display)
        self.min_db_spin.valueChanged.connect(self._apply_noise_display)
        self.max_db_spin.valueChanged.connect(self._apply_noise_display)
        self.reset_button.clicked.connect(self.canvas.reset_camera)
        self.auto_range_check.toggled.connect(self._update_range_enablement)
        self._update_range_enablement(self.auto_range_check.isChecked())
        self._update_source_field_control_enablement()
        self._refresh_metadata_labels()

    def set_result_context(self, summary: RunResultSummary | None, result_summary_path: str | Path | None = None) -> None:
        self._result_summary = summary
        self._result_summary_path = Path(result_summary_path) if result_summary_path else None
        self._sync_calculation_directivity_from_summary(summary)
        self._update_source_field_control_enablement()
        self._refresh_metadata_labels()

    def set_frame(self, frame: Scene3DFrame | None) -> None:
        self.canvas.set_frame(frame)
        self._apply_visibility()
        self._apply_noise_display()
        self._refresh_metadata_labels()

    def set_playback_context(self, time_index: int | None, sim_time_seconds: float | None, vehicle_count: int) -> None:
        self._playback_time_index = time_index
        self._playback_sim_seconds = sim_time_seconds
        self._playback_vehicle_count = int(vehicle_count)
        self._refresh_metadata_labels()

    def current_source_field_mode(self) -> str:
        if self.link_calc_directivity_check.isChecked():
            return self._mapped_source_field_mode_from_calculation()
        return str(self.source_field_mode_combo.currentData())

    def current_source_field_settings(self) -> dict[str, float | bool]:
        return {
            'scale': float(self.source_field_scale_spin.value()),
            'height_scale': float(self.source_field_height_spin.value()),
            'opacity': float(self.source_field_opacity_spin.value()),
            'wedge_span_deg': float(self._calc_directivity_wedge_angle_deg if self.link_calc_directivity_check.isChecked() else self.source_field_wedge_angle_spin.value()),
            'vertical_angle_deg': float(self._calc_directivity_vertical_angle_deg),
            'vertical_strength_db': float(self._calc_directivity_vertical_strength_db),
            'highlight_receivers': self.highlight_receivers_check.isChecked(),
            'show_receiver_links': self.receiver_links_check.isChecked(),
            'calculation_linked': self.link_calc_directivity_check.isChecked(),
            'calculation_preset': self._calc_directivity_preset,
            'calculation_mode': self._calc_directivity_mode,
            'calculation_strength_db': float(self._calc_directivity_strength_db),
        }

    def set_playback_selection(self, selected_vehicle_id: str | None, follow_selected: bool) -> None:
        self._selected_vehicle_id = selected_vehicle_id
        self._follow_selected_vehicle = bool(follow_selected)
        self.follow_selected_check.blockSignals(True)
        self.follow_selected_check.setChecked(self._follow_selected_vehicle)
        self.follow_selected_check.blockSignals(False)
        self._apply_follow_if_needed()
        self._refresh_metadata_labels()

    def _update_range_enablement(self, checked: bool) -> None:
        self.min_db_spin.setEnabled(not checked)
        self.max_db_spin.setEnabled(not checked)

    def _update_source_field_control_enablement(self) -> None:
        linked = self.link_calc_directivity_check.isChecked()
        self.source_field_mode_combo.setEnabled(not linked)
        self.source_field_wedge_angle_spin.setEnabled(not linked)

    def _on_calc_directivity_link_changed(self, checked: bool) -> None:
        self._update_source_field_control_enablement()
        if checked:
            self._sync_calculation_directivity_from_summary(self._result_summary)
        self._apply_noise_display()

    def _on_follow_changed(self, checked: bool) -> None:
        self._follow_selected_vehicle = checked
        self._apply_follow_if_needed()
        self._refresh_metadata_labels()

    def _apply_follow_if_needed(self) -> None:
        if not self._follow_selected_vehicle or self._selected_vehicle_id is None:
            return
        frame = self.canvas.frame_data
        if frame is None:
            return
        for vehicle in frame.vehicles:
            if vehicle.vehicle_id == self._selected_vehicle_id:
                self.canvas.center_on_world_point(vehicle.x, vehicle.y, vehicle.z)
                break

    def _apply_visibility(self) -> None:
        self.canvas.set_layer_visibility(
            roads=self.roads_check.isChecked(),
            receivers=self.receivers_check.isChecked(),
            vehicles=self.vehicles_check.isChecked(),
            vehicle_trails=self.vehicle_trails_check.isChecked(),
            barriers=self.barriers_check.isChecked(),
            buildings=self.buildings_check.isChecked(),
            ground=self.ground_check.isChecked(),
            vegetation=self.vegetation_check.isChecked(),
            grid_region=self.grid_region_check.isChecked(),
            noise_surface=self.noise_surface_check.isChecked(),
            source_field=self.source_field_check.isChecked(),
        )
        self._refresh_metadata_labels()

    def _apply_noise_display(self) -> None:
        self.canvas.set_noise_display(
            render_mode=str(self.surface_mode_combo.currentData()),
            auto_range=self.auto_range_check.isChecked(),
            min_db=float(self.min_db_spin.value()),
            max_db=float(self.max_db_spin.value()),
        )
        self._apply_follow_if_needed()
        self._refresh_metadata_labels()

    def _refresh_metadata_labels(self) -> None:
        summary = self._result_summary
        if summary is None:
            self.run_id_label.setText('-')
            self.scenario_label.setText('-')
            self.output_label.setText('-')
        else:
            self.run_id_label.setText(summary.run.run_id)
            self.scenario_label.setText(summary.run.scenario)
            output_text = self._result_summary_path.parent.name if self._result_summary_path is not None else summary.output_dir
            self.output_label.setText(output_text)
        mode_text = 'Raised Surface' if self.surface_mode_combo.currentData() == 'raised' else 'Color Plate'
        if not self.noise_surface_check.isChecked():
            mode_text += ' | noise hidden'
        self.view_mode_label.setText(mode_text)
        if self.auto_range_check.isChecked():
            range_value = self.canvas.last_noise_range
            if range_value is None:
                self.db_range_label.setText('Auto')
            else:
                self.db_range_label.setText(f'Auto ({range_value[0]:.1f} to {range_value[1]:.1f} dB)')
        else:
            self.db_range_label.setText(f'Manual ({self.min_db_spin.value():.1f} to {self.max_db_spin.value():.1f} dB)')
        noise_cells = len(self.canvas.frame_data.noise_cells) if self.canvas.frame_data is not None else 0
        self.noise_cell_label.setText(str(noise_cells))
        affected_receivers = len([receiver for receiver in self.canvas.frame_data.receivers if receiver.highlighted]) if self.canvas.frame_data is not None else 0
        self._affected_receiver_count = affected_receivers
        self.affected_receivers_label.setText(str(affected_receivers))
        self.selected_vehicle_label.setText(self._selected_vehicle_id or '-')
        self.follow_label.setText('on' if self._follow_selected_vehicle else 'off')
        self.directivity_preset_label.setText(self._calc_directivity_preset)
        self.directivity_vehicle_types_label.setText(', '.join(self._calc_directivity_vehicle_types) if self._calc_directivity_vehicle_types else '-')
        self.visual_profile_label.setText(self._calc_visual_profile)
        source_field_mode = self.current_source_field_mode()
        if self.link_calc_directivity_check.isChecked():
            self.source_field_label.setText(f'{source_field_mode} (calc-linked)')
        else:
            self.source_field_label.setText(source_field_mode)
        settings = self.current_source_field_settings()
        detail_parts = [
            f'calc {self._calc_directivity_preset}/{self._calc_directivity_mode}',
            f'strength {self._calc_directivity_strength_db:.1f} dB',
            f"angle {settings['wedge_span_deg']:.0f} deg",
            f"vertical {settings['vertical_strength_db']:.1f} dB / {settings['vertical_angle_deg']:.0f} deg",
            f"scale {settings['scale']:.1f}",
            f"height {settings['height_scale']:.1f}",
            f"opacity {settings['opacity']:.2f}",
        ]
        self.source_field_detail_label.setText(' | '.join(detail_parts))
        if self._playback_time_index is None:
            self.playback_frame_label.setText('-')
        elif self._playback_sim_seconds is None:
            self.playback_frame_label.setText(str(self._playback_time_index))
        else:
            self.playback_frame_label.setText(f'{self._playback_time_index} ({self._playback_sim_seconds:.1f}s)')
        self.playback_vehicle_count_label.setText(str(self._playback_vehicle_count))

    def _sync_calculation_directivity_from_summary(self, summary: RunResultSummary | None) -> None:
        directivity = {}
        if summary is not None and isinstance(summary.propagation_features, dict):
            directivity = summary.propagation_features.get('noise_directivity') or {}
        self._calc_directivity_preset = str(directivity.get('preset', 'custom'))
        self._calc_visual_profile = self._calc_directivity_preset
        vehicle_types = []
        if summary is not None and isinstance(summary.propagation_features, dict):
            raw_vehicle_types = summary.propagation_features.get('noise_directivity_vehicle_types') or []
            vehicle_types = [str(item) for item in raw_vehicle_types]
        self._calc_directivity_vehicle_types = vehicle_types
        self._calc_directivity_mode = str(directivity.get('mode', 'isotropic'))
        self._calc_directivity_strength_db = float(directivity.get('strength_db', 6.0))
        self._calc_directivity_wedge_angle_deg = float(directivity.get('wedge_angle_deg', 70.0))
        self._calc_directivity_vertical_strength_db = float(directivity.get('vertical_strength_db', 0.0))
        self._calc_directivity_vertical_angle_deg = float(directivity.get('vertical_angle_deg', 55.0))
        if self.link_calc_directivity_check.isChecked():
            mapped_mode = self._mapped_source_field_mode_from_calculation()
            self.source_field_mode_combo.blockSignals(True)
            index = self.source_field_mode_combo.findData(mapped_mode)
            if index >= 0:
                self.source_field_mode_combo.setCurrentIndex(index)
            self.source_field_mode_combo.blockSignals(False)
            self.source_field_wedge_angle_spin.blockSignals(True)
            self.source_field_wedge_angle_spin.setValue(self._calc_directivity_wedge_angle_deg)
            self.source_field_wedge_angle_spin.blockSignals(False)

    def _mapped_source_field_mode_from_calculation(self) -> str:
        if self._calc_directivity_mode == 'wedge':
            return 'wedge'
        if self._calc_directivity_mode == 'dual_wedge':
            return 'dual_wedge'
        if self._calc_directivity_mode == 'isotropic':
            return 'sphere'
        return 'off'
