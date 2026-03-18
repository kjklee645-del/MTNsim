from __future__ import annotations

from math import cos, radians, sin
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from mtnsim.gui.models.scene_3d import GridRegion3D, LineWall3D, PrismMesh3D, RoadMesh3D, Scene3DFrame, SurfacePolygon3D
from mtnsim.schemas.results import RunResultSummary


class Scene3DCanvas(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.frame_data: Scene3DFrame | None = None
        self.show_roads = True
        self.show_receivers = True
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
        self.setMinimumSize(640, 420)
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
        barriers: bool,
        buildings: bool,
        ground: bool,
        vegetation: bool,
        grid_region: bool,
        noise_surface: bool,
    ) -> None:
        self.show_roads = roads
        self.show_receivers = receivers
        self.show_barriers = barriers
        self.show_buildings = buildings
        self.show_ground = ground
        self.show_vegetation = vegetation
        self.show_grid_region = grid_region
        self.show_noise_surface = noise_surface
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
        if self._drag_last_pos is None or self._drag_mode is None:
            super().mouseMoveEvent(event)
            return
        current = event.position().toPoint()
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

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor('#0f151c'))

        frame = self.frame_data
        if frame is None:
            painter.setPen(QColor('#9fb2c6'))
            painter.drawText(self.rect(), Qt.AlignCenter, '3D scene is not available yet for the current selection.')
            return

        painter.fillRect(self.rect().adjusted(16, 16, -16, -16), QColor('#121b24'))
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

        def draw_prism(mesh: PrismMesh3D) -> None:
            base = [project(x, y, 0.0) for x, y in mesh.footprint]
            top = [project(x, y, mesh.height) for x, y in mesh.footprint]
            side_color = QColor(mesh.color).darker(135)
            for idx in range(len(base)):
                nxt = (idx + 1) % len(base)
                side = QPolygonF([base[idx], base[nxt], top[nxt], top[idx]])
                painter.setBrush(side_color)
                painter.setPen(QPen(QColor(mesh.edge_color), 1.0))
                painter.drawPolygon(side)
            painter.setBrush(QColor(mesh.color))
            painter.setPen(QPen(QColor(mesh.edge_color), 1.2))
            painter.drawPolygon(QPolygonF(top))

        def draw_road(mesh: RoadMesh3D) -> None:
            if len(mesh.points) < 2:
                return
            pen = QPen(QColor(mesh.color), max(mesh.width * scale * 0.10, 2.2), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            path = QPainterPath()
            path.moveTo(project(mesh.points[0][0], mesh.points[0][1], mesh.z))
            for x, y in mesh.points[1:]:
                path.lineTo(project(x, y, mesh.z))
            painter.drawPath(path)

        def draw_wall(mesh: LineWall3D) -> None:
            p1 = project(mesh.start[0], mesh.start[1], 0.0)
            p2 = project(mesh.end[0], mesh.end[1], 0.0)
            p3 = project(mesh.end[0], mesh.end[1], mesh.height)
            p4 = project(mesh.start[0], mesh.start[1], mesh.height)
            painter.setBrush(QColor(mesh.color))
            painter.setPen(QPen(QColor(mesh.edge_color), 1.1))
            painter.drawPolygon(QPolygonF([p1, p2, p3, p4]))

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
        if self.show_noise_surface:
            draw_noise_surface(frame.noise_cells)
        if self.show_grid_region and frame.grid_region is not None:
            draw_grid_region(frame.grid_region)
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
            for marker in frame.receivers:
                base = project(marker.x, marker.y, 0.0)
                top = project(marker.x, marker.y, marker.z + 2.0)
                painter.setPen(QPen(QColor('#eff6ff'), 1.3))
                painter.drawLine(base, top)
                painter.setBrush(QColor('#eff6ff'))
                painter.drawEllipse(top, 3.5, 3.5)

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
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._result_summary: RunResultSummary | None = None
        self._result_summary_path: Path | None = None
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
        meta_layout.addRow('Run ID', self.run_id_label)
        meta_layout.addRow('Scenario', self.scenario_label)
        meta_layout.addRow('Output', self.output_label)
        meta_layout.addRow('View Mode', self.view_mode_label)
        meta_layout.addRow('dB Range', self.db_range_label)
        meta_layout.addRow('Noise Cells', self.noise_cell_label)
        root.addWidget(meta_card)

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
        for widget in [self.roads_check, self.receivers_check, self.barriers_check, self.buildings_check, self.ground_check, self.vegetation_check, self.grid_region_check, self.noise_surface_check]:
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
        root.addWidget(controls)

        self.canvas = Scene3DCanvas()
        root.addWidget(self.canvas, 1)

        for widget in [self.roads_check, self.receivers_check, self.barriers_check, self.buildings_check, self.ground_check, self.vegetation_check, self.grid_region_check, self.noise_surface_check]:
            widget.toggled.connect(self._apply_visibility)
        self.surface_mode_combo.currentIndexChanged.connect(self._apply_noise_display)
        self.auto_range_check.toggled.connect(self._apply_noise_display)
        self.min_db_spin.valueChanged.connect(self._apply_noise_display)
        self.max_db_spin.valueChanged.connect(self._apply_noise_display)
        self.reset_button.clicked.connect(self.canvas.reset_camera)
        self.auto_range_check.toggled.connect(self._update_range_enablement)
        self._update_range_enablement(self.auto_range_check.isChecked())
        self._refresh_metadata_labels()

    def set_result_context(self, summary: RunResultSummary | None, result_summary_path: str | Path | None = None) -> None:
        self._result_summary = summary
        self._result_summary_path = Path(result_summary_path) if result_summary_path else None
        self._refresh_metadata_labels()

    def set_frame(self, frame: Scene3DFrame | None) -> None:
        self.canvas.set_frame(frame)
        self._apply_visibility()
        self._apply_noise_display()
        self._refresh_metadata_labels()

    def _update_range_enablement(self, checked: bool) -> None:
        self.min_db_spin.setEnabled(not checked)
        self.max_db_spin.setEnabled(not checked)

    def _apply_visibility(self) -> None:
        self.canvas.set_layer_visibility(
            roads=self.roads_check.isChecked(),
            receivers=self.receivers_check.isChecked(),
            barriers=self.barriers_check.isChecked(),
            buildings=self.buildings_check.isChecked(),
            ground=self.ground_check.isChecked(),
            vegetation=self.vegetation_check.isChecked(),
            grid_region=self.grid_region_check.isChecked(),
            noise_surface=self.noise_surface_check.isChecked(),
        )
        self._refresh_metadata_labels()

    def _apply_noise_display(self) -> None:
        self.canvas.set_noise_display(
            render_mode=str(self.surface_mode_combo.currentData()),
            auto_range=self.auto_range_check.isChecked(),
            min_db=float(self.min_db_spin.value()),
            max_db=float(self.max_db_spin.value()),
        )
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
