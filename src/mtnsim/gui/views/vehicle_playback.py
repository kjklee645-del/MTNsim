from __future__ import annotations

from dataclasses import replace
from math import atan2, degrees

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QDoubleSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mtnsim.gui.controllers.playback_controller import PlaybackDataset
from mtnsim.gui.controllers.scene_controller import PointLayer, PolygonLayer, PolylineLayer, SceneSnapshot
from mtnsim.gui.controllers.result_controller import HeatmapCell
from mtnsim.gui.views.scene_view import SceneCanvas, VehicleGlyph


class VehiclePlaybackView(QWidget):
    playback_frame_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.snapshot: SceneSnapshot | None = None
        self.dataset: PlaybackDataset | None = None
        self._playback_speed = 1.0
        self._raw_heatmap_cells: list[HeatmapCell] = []
        self._raw_glyphs: list[VehicleGlyph] = []
        self._raw_trails: list[list[tuple[float, float]]] = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_frame)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel('Vehicle Playback')
        title.setStyleSheet('font-size: 22px; font-weight: 700;')
        layout.addWidget(title)

        controls = QHBoxLayout()
        controls.setSpacing(10)
        self.play_button = QPushButton('Play')
        self.play_button.clicked.connect(self.toggle_playback)
        self.frame_label = QLabel('Frame: -')
        self.vehicle_label = QLabel('Vehicles: -')
        self.speed_selector = QComboBox()
        self.speed_selector.addItems(['0.5x', '1.0x', '2.0x', '4.0x'])
        self.speed_selector.setCurrentText('1.0x')
        self.speed_selector.currentTextChanged.connect(self._change_speed)
        controls.addWidget(self.play_button)
        controls.addWidget(self.frame_label)
        controls.addWidget(self.vehicle_label)
        controls.addStretch(1)
        controls.addWidget(QLabel('Speed'))
        controls.addWidget(self.speed_selector)
        layout.addLayout(controls)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.slider)

        splitter = QSplitter()
        layout.addWidget(splitter, 1)

        self.canvas = SceneCanvas()
        splitter.addWidget(self.canvas)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        layer_group = QGroupBox('Display Controls')
        layer_layout = QVBoxLayout(layer_group)
        layer_layout.setSpacing(4)
        self.roads_check = self._add_checkbox(layer_layout, 'Roads', True)
        self.junctions_check = self._add_checkbox(layer_layout, 'Junctions', True)
        self.receivers_check = self._add_checkbox(layer_layout, 'Receivers', True)
        self.buildings_check = self._add_checkbox(layer_layout, 'Buildings', True)
        self.barriers_check = self._add_checkbox(layer_layout, 'Barriers', True)
        self.terrain_check = self._add_checkbox(layer_layout, 'Terrain', True)
        self.ground_check = self._add_checkbox(layer_layout, 'Ground', True)
        self.vegetation_check = self._add_checkbox(layer_layout, 'Vegetation', True)
        self.vehicles_check = self._add_checkbox(layer_layout, 'Vehicles', True)
        self.trails_check = self._add_checkbox(layer_layout, 'Trails', True)
        self.heatmap_check = self._add_checkbox(layer_layout, 'Heatmap', True)
        right_layout.addWidget(layer_group)

        heatmap_group = QGroupBox('Heatmap Controls')
        heatmap_form = QFormLayout(heatmap_group)
        self.heatmap_auto_range_check = QCheckBox('Auto range')
        self.heatmap_auto_range_check.setChecked(True)
        self.heatmap_auto_range_check.toggled.connect(self._update_manual_range_enabled)
        self.heatmap_auto_range_check.toggled.connect(self._apply_display_state)
        heatmap_form.addRow('Range', self.heatmap_auto_range_check)

        self.heatmap_min_spin = QDoubleSpinBox()
        self.heatmap_min_spin.setRange(0.0, 200.0)
        self.heatmap_min_spin.setDecimals(1)
        self.heatmap_min_spin.setValue(40.0)
        self.heatmap_min_spin.valueChanged.connect(self._apply_display_state)
        heatmap_form.addRow('Min dB', self.heatmap_min_spin)

        self.heatmap_max_spin = QDoubleSpinBox()
        self.heatmap_max_spin.setRange(0.0, 200.0)
        self.heatmap_max_spin.setDecimals(1)
        self.heatmap_max_spin.setValue(80.0)
        self.heatmap_max_spin.valueChanged.connect(self._apply_display_state)
        heatmap_form.addRow('Max dB', self.heatmap_max_spin)

        self.heatmap_opacity_slider = QSlider(Qt.Horizontal)
        self.heatmap_opacity_slider.setRange(0, 100)
        self.heatmap_opacity_slider.setValue(70)
        self.heatmap_opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.heatmap_opacity_slider.valueChanged.connect(self._apply_display_state)
        heatmap_form.addRow('Opacity', self.heatmap_opacity_slider)

        self.heatmap_opacity_label = QLabel('70%')
        heatmap_form.addRow('Opacity Label', self.heatmap_opacity_label)
        right_layout.addWidget(heatmap_group)

        self.info_box = QTextEdit()
        self.info_box.setReadOnly(True)
        self.info_box.setMaximumWidth(340)
        right_layout.addWidget(self.info_box, 1)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        self._update_manual_range_enabled(True)

    def _add_checkbox(self, layout: QVBoxLayout, label: str, checked: bool) -> QCheckBox:
        checkbox = QCheckBox(label)
        checkbox.setChecked(checked)
        checkbox.toggled.connect(self._apply_display_state)
        layout.addWidget(checkbox)
        return checkbox

    def _on_opacity_changed(self, value: int) -> None:
        self.heatmap_opacity_label.setText(f'{value}%')

    def _update_manual_range_enabled(self, checked: bool) -> None:
        self.heatmap_min_spin.setEnabled(not checked)
        self.heatmap_max_spin.setEnabled(not checked)

    def set_snapshot(self, snapshot: SceneSnapshot | None) -> None:
        self.snapshot = snapshot
        self._apply_display_state()
        self._refresh_info()

    def set_heatmap_cells(self, cells) -> None:
        self._raw_heatmap_cells = list(cells)
        if cells:
            values = [cell.value_db for cell in cells]
            min_value = min(values)
            max_value = max(values)
            for spin in (self.heatmap_min_spin, self.heatmap_max_spin):
                spin.blockSignals(True)
                spin.setRange(0.0, max(200.0, max_value + 20.0))
            self.heatmap_min_spin.setValue(min_value)
            self.heatmap_max_spin.setValue(max_value)
            self.heatmap_min_spin.blockSignals(False)
            self.heatmap_max_spin.blockSignals(False)
        self._apply_display_state()
        self._refresh_info()

    def set_dataset(self, dataset: PlaybackDataset | None) -> None:
        self.dataset = dataset
        self._timer.stop()
        self.play_button.setText('Play')
        self._raw_glyphs = []
        self._raw_trails = []
        if dataset is None or dataset.frame_count == 0:
            self.slider.setEnabled(False)
            self.slider.setRange(0, 0)
            self.frame_label.setText('Frame: -')
            self.vehicle_label.setText('Vehicles: -')
            self._apply_display_state()
            self._refresh_info()
            return
        self.slider.blockSignals(True)
        self.slider.setEnabled(True)
        self.slider.setRange(0, dataset.frame_count - 1)
        self.slider.setValue(0)
        self.slider.blockSignals(False)
        self._render_frame(0)
        self._refresh_info()

    def toggle_playback(self) -> None:
        if self.dataset is None or self.dataset.frame_count == 0:
            return
        if self._timer.isActive():
            self._timer.stop()
            self.play_button.setText('Play')
        else:
            self._timer.start(self._frame_interval_ms())
            self.play_button.setText('Pause')

    def _change_speed(self, label: str) -> None:
        self._playback_speed = float(label.replace('x', ''))
        if self._timer.isActive():
            self._timer.start(self._frame_interval_ms())

    def _frame_interval_ms(self) -> int:
        base = 250
        return max(40, int(base / max(self._playback_speed, 0.25)))

    def _advance_frame(self) -> None:
        if self.dataset is None:
            return
        if self.slider.value() >= self.slider.maximum():
            self._timer.stop()
            self.play_button.setText('Play')
            return
        self.slider.setValue(self.slider.value() + 1)

    def _on_slider_changed(self, frame_index: int) -> None:
        self._render_frame(frame_index)
        self.playback_frame_changed.emit(frame_index)

    def _render_frame(self, frame_index: int) -> None:
        if self.dataset is None or frame_index < 0 or frame_index >= self.dataset.frame_count:
            return
        frame = self.dataset.frames[frame_index]
        previous_lookup = {}
        if frame_index > 0:
            previous_lookup = {vehicle.vehicle_id: vehicle for vehicle in self.dataset.frames[frame_index - 1].vehicles}
        next_lookup = {}
        if frame_index + 1 < self.dataset.frame_count:
            next_lookup = {vehicle.vehicle_id: vehicle for vehicle in self.dataset.frames[frame_index + 1].vehicles}

        glyphs: list[VehicleGlyph] = []
        trails: list[list[tuple[float, float]]] = []
        tail_start = max(0, frame_index - 12)
        tail_frames = self.dataset.frames[tail_start:frame_index + 1]
        for vehicle in frame.vehicles:
            heading_deg = 0.0
            reference = previous_lookup.get(vehicle.vehicle_id) or next_lookup.get(vehicle.vehicle_id)
            if reference is not None:
                dx = vehicle.x - reference.x if vehicle.vehicle_id in previous_lookup else reference.x - vehicle.x
                dy = vehicle.y - reference.y if vehicle.vehicle_id in previous_lookup else reference.y - vehicle.y
                if abs(dx) > 1e-6 or abs(dy) > 1e-6:
                    heading_deg = degrees(atan2(dy, dx))
            glyphs.append(
                VehicleGlyph(
                    vehicle_id=vehicle.vehicle_id,
                    x=vehicle.x,
                    y=vehicle.y,
                    heading_deg=heading_deg,
                    speed_mps=vehicle.speed_mps,
                )
            )
            trail = []
            for tail_frame in tail_frames:
                for tail_vehicle in tail_frame.vehicles:
                    if tail_vehicle.vehicle_id == vehicle.vehicle_id:
                        trail.append((tail_vehicle.x, tail_vehicle.y))
                        break
            if len(trail) >= 2:
                trails.append(trail)

        self._raw_glyphs = glyphs
        self._raw_trails = trails
        self._apply_display_state()
        self.frame_label.setText(f'Frame: {frame.time_index} ({frame.sim_time_seconds:.1f}s)')
        self.vehicle_label.setText(f'Vehicles: {len(frame.vehicles)}')
        self._refresh_info(current_frame=frame_index)

    def _filtered_snapshot(self) -> SceneSnapshot | None:
        if self.snapshot is None:
            return None
        return SceneSnapshot(
            bounds=self.snapshot.bounds,
            road_layer=self.snapshot.road_layer if self.roads_check.isChecked() else PolylineLayer(name=self.snapshot.road_layer.name),
            junction_layer=self.snapshot.junction_layer if self.junctions_check.isChecked() else PolygonLayer(name=self.snapshot.junction_layer.name),
            barrier_layer=self.snapshot.barrier_layer if self.barriers_check.isChecked() else PolylineLayer(name=self.snapshot.barrier_layer.name),
            terrain_layer=self.snapshot.terrain_layer if self.terrain_check.isChecked() else PolylineLayer(name=self.snapshot.terrain_layer.name),
            building_layer=self.snapshot.building_layer if self.buildings_check.isChecked() else PolygonLayer(name=self.snapshot.building_layer.name),
            ground_layer=self.snapshot.ground_layer if self.ground_check.isChecked() else PolygonLayer(name=self.snapshot.ground_layer.name),
            vegetation_layer=self.snapshot.vegetation_layer if self.vegetation_check.isChecked() else PolygonLayer(name=self.snapshot.vegetation_layer.name),
            receiver_layer=self.snapshot.receiver_layer if self.receivers_check.isChecked() else PointLayer(name=self.snapshot.receiver_layer.name),
        )

    def _apply_display_state(self, *args) -> None:  # noqa: ARG002
        self.canvas.set_snapshot(self._filtered_snapshot())
        self.canvas.set_vehicle_points(self._raw_glyphs if self.vehicles_check.isChecked() else [], trails=self._raw_trails if self.trails_check.isChecked() else [])
        self.canvas.set_heatmap_cells(self._raw_heatmap_cells if self.heatmap_check.isChecked() else [])
        self.canvas.set_heatmap_settings(
            auto_range=self.heatmap_auto_range_check.isChecked(),
            min_db=min(self.heatmap_min_spin.value(), self.heatmap_max_spin.value()),
            max_db=max(self.heatmap_min_spin.value(), self.heatmap_max_spin.value()),
            opacity=int(round(self.heatmap_opacity_slider.value() / 100.0 * 255.0)),
        )

    def _refresh_info(self, current_frame: int | None = None) -> None:
        lines = ['Playback Summary']
        if self.dataset is None:
            lines.append('No playback dataset loaded.')
        else:
            lines.extend(
                [
                    f'- Trace file: {self.dataset.trace_file.name}',
                    f'- Frames: {self.dataset.frame_count}',
                    f'- Max vehicles/frame: {self.dataset.max_vehicle_count}',
                    f'- Current frame: {current_frame if current_frame is not None else self.slider.value()}',
                    '- Tail length: 12 frames',
                    '- Vehicle color: speed colormap',
                    '- Right panel: layer toggles + heatmap controls',
                ]
            )
        if self.snapshot is not None:
            lines.extend(
                [
                    '',
                    'Scene Layers',
                    f'- Road lanes: {len(self.snapshot.road_layer.polylines)}',
                    f'- Junction polygons: {len(self.snapshot.junction_layer.polygons)}',
                    f'- Receivers: {len(self.snapshot.receiver_layer.points)}',
                    f'- Buildings: {len(self.snapshot.building_layer.polygons)}',
                    f'- Barriers: {len(self.snapshot.barrier_layer.polylines)}',
                    f'- Heatmap cells: {len(self._raw_heatmap_cells)}',
                ]
            )
        self.info_box.setPlainText('\n'.join(lines))
