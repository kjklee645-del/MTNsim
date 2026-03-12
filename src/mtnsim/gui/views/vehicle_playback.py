from __future__ import annotations

from dataclasses import dataclass, replace
from math import atan2, degrees

from PySide6.QtCore import QPointF, QRectF, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
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




@dataclass(frozen=True, slots=True)
class PlaybackTimelineEvent:
    kind: str
    label: str
    vehicle_ids: tuple[str, ...] = ()


class TimelineMarkerStrip(QWidget):
    _EVENT_COLORS = {
        'enter': '#2e8b57',
        'exit': '#6b7280',
        'speed_shift': '#d97706',
        'heading_shift': '#2563eb',
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._frame_count = 0
        self._events_by_frame: dict[int, list[PlaybackTimelineEvent]] = {}
        self._current_frame = 0
        self.setMinimumHeight(24)
        self.setMaximumHeight(24)
        self.setToolTip('Timeline events: green enter, gray exit, amber speed shift, blue heading shift')

    def set_frame_count(self, frame_count: int) -> None:
        self._frame_count = max(0, int(frame_count))
        self.update()

    def set_events_by_frame(self, events_by_frame: dict[int, list[PlaybackTimelineEvent]]) -> None:
        self._events_by_frame = {int(frame): list(events) for frame, events in events_by_frame.items()}
        self.update()

    def set_current_frame(self, frame_index: int) -> None:
        self._current_frame = max(0, int(frame_index))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor('#faf6ef'))

        rect = self.rect().adjusted(10, 4, -10, -4)
        painter.setPen(QPen(QColor('#d6cfc2'), 1))
        painter.drawRoundedRect(rect, 4, 4)

        if self._frame_count <= 1:
            return

        baseline_y = rect.bottom() - 3
        painter.setPen(QPen(QColor('#b9ae9a'), 1))
        painter.drawLine(rect.left() + 4, baseline_y, rect.right() - 4, baseline_y)

        for frame_index, events in self._events_by_frame.items():
            if not events:
                continue
            x = self._frame_to_x(frame_index, rect)
            stack_top = rect.top() + 3
            tick_width = 2 if self._frame_count > 200 else 3
            for offset, timeline_event in enumerate(events[:3]):
                color = QColor(self._EVENT_COLORS.get(timeline_event.kind, '#7c3aed'))
                painter.fillRect(QRectF(x - tick_width / 2, stack_top + (offset * 5), tick_width, 4), color)

        current_x = self._frame_to_x(self._current_frame, rect)
        painter.setPen(QPen(QColor('#111827'), 2))
        painter.drawLine(current_x, rect.top(), current_x, rect.bottom())

    def _frame_to_x(self, frame_index: int, rect: QRectF) -> float:
        usable_width = max(1.0, rect.width() - 8.0)
        ratio = max(0.0, min(1.0, frame_index / max(1, self._frame_count - 1)))
        return rect.left() + 4.0 + (usable_width * ratio)


class VehiclePlaybackView(QWidget):
    playback_frame_changed = Signal(int)
    contribution_view_changed = Signal()
    export_png_sequence_requested = Signal()
    export_gif_requested = Signal()
    export_mp4_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.snapshot: SceneSnapshot | None = None
        self.dataset: PlaybackDataset | None = None
        self._playback_speed = 1.0
        self._raw_heatmap_cells: list[HeatmapCell] = []
        self._raw_glyphs: list[VehicleGlyph] = []
        self._raw_trails: list[list[tuple[float, float]]] = []
        self._selected_vehicle_id: str | None = None
        self._current_frame_index: int | None = None
        self._current_frame_vehicle_lookup: dict[str, object] = {}
        self._selected_vehicle_receiver_contributions: dict[str, float] = {}
        self._timeline_events_by_frame: dict[int, list[PlaybackTimelineEvent]] = {}
        self._follow_selected_vehicle = False
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
        self.follow_vehicle_check = QCheckBox('Follow selected')
        self.follow_vehicle_check.toggled.connect(self._on_follow_mode_changed)
        controls.addWidget(self.follow_vehicle_check)
        self.export_png_button = QPushButton('Export PNGs')
        self.export_png_button.setEnabled(False)
        self.export_png_button.clicked.connect(self.export_png_sequence_requested.emit)
        controls.addWidget(self.export_png_button)
        self.export_gif_button = QPushButton('Export GIF')
        self.export_gif_button.setEnabled(False)
        self.export_gif_button.clicked.connect(self.export_gif_requested.emit)
        controls.addWidget(self.export_gif_button)
        self.export_mp4_button = QPushButton('Export MP4')
        self.export_mp4_button.setEnabled(False)
        self.export_mp4_button.clicked.connect(self.export_mp4_requested.emit)
        controls.addWidget(self.export_mp4_button)
        layout.addLayout(controls)

        self.timeline_strip = TimelineMarkerStrip()
        layout.addWidget(self.timeline_strip)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.slider)

        splitter = QSplitter()
        layout.addWidget(splitter, 1)

        self.canvas = SceneCanvas()
        self.canvas.vehicle_selected.connect(self._on_vehicle_selected)
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
        self.selected_vehicle_contribution_check = QCheckBox('Selected vehicle contribution only')
        self.selected_vehicle_contribution_check.toggled.connect(self._on_contribution_mode_changed)
        heatmap_form.addRow('Contribution', self.selected_vehicle_contribution_check)
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

    def _on_follow_mode_changed(self, checked: bool) -> None:
        self._follow_selected_vehicle = checked
        if checked:
            self._focus_selected_vehicle()
        self._refresh_info(current_frame=self._current_frame_index)

    def _on_contribution_mode_changed(self, checked: bool) -> None:
        self.contribution_view_changed.emit()
        self._refresh_info(current_frame=self._current_frame_index)

    def is_selected_vehicle_contribution_only(self) -> bool:
        return self.selected_vehicle_contribution_check.isChecked()

    def selected_vehicle_id(self) -> str | None:
        return self._selected_vehicle_id

    def set_selected_vehicle_receiver_contributions(self, contributions: dict[str, float]) -> None:
        self._selected_vehicle_receiver_contributions = dict(contributions)
        self._refresh_info(current_frame=self._current_frame_index)

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
        self._selected_vehicle_id = None
        self._current_frame_index = None
        self._current_frame_vehicle_lookup = {}
        self._selected_vehicle_receiver_contributions = {}
        self._timeline_events_by_frame = {}
        self.timeline_strip.set_events_by_frame({})
        self.timeline_strip.set_frame_count(0)
        self.timeline_strip.set_current_frame(0)
        if dataset is None or dataset.frame_count == 0:
            self.export_png_button.setEnabled(False)
            self.export_gif_button.setEnabled(False)
            self.export_mp4_button.setEnabled(False)
            self.slider.setEnabled(False)
            self.slider.setRange(0, 0)
            self.frame_label.setText('Frame: -')
            self.vehicle_label.setText('Vehicles: -')
            self._apply_display_state()
            self._refresh_info()
            return
        self.export_png_button.setEnabled(True)
        self.export_gif_button.setEnabled(True)
        self.export_mp4_button.setEnabled(True)
        self._timeline_events_by_frame = self._build_timeline_events(dataset)
        self.timeline_strip.set_frame_count(dataset.frame_count)
        self.timeline_strip.set_events_by_frame(self._timeline_events_by_frame)

        self.slider.blockSignals(True)
        self.slider.setEnabled(True)
        self.slider.setRange(0, dataset.frame_count - 1)
        self.slider.setValue(0)
        self.slider.blockSignals(False)
        self._render_frame(0)
        self._refresh_info()

    def current_frame_index(self) -> int | None:
        return self._current_frame_index

    def set_frame_index(self, frame_index: int) -> None:
        if self.dataset is None:
            return
        clamped = max(0, min(frame_index, self.slider.maximum()))
        self.slider.setValue(clamped)

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
                    vehicle_type=vehicle.vehicle_type,
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
        self._current_frame_index = frame.time_index
        self._current_frame_vehicle_lookup = {vehicle.vehicle_id: vehicle for vehicle in frame.vehicles}
        self.timeline_strip.set_current_frame(frame_index)
        self._focus_selected_vehicle()
        if self._selected_vehicle_id is not None and self._selected_vehicle_id not in self._current_frame_vehicle_lookup:
            # Keep the selection pinned even when the vehicle is off-frame.
            pass
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

    def _on_vehicle_selected(self, vehicle_id: str) -> None:
        self._selected_vehicle_id = vehicle_id or None
        if self._selected_vehicle_id is None:
            self._selected_vehicle_receiver_contributions = {}
        self._apply_display_state()
        self._focus_selected_vehicle()
        self._refresh_info(current_frame=self._current_frame_index)
        self.contribution_view_changed.emit()


    def _focus_selected_vehicle(self) -> None:
        if not self._follow_selected_vehicle or self._selected_vehicle_id is None:
            return
        vehicle = self._current_frame_vehicle_lookup.get(self._selected_vehicle_id)
        if vehicle is None:
            return
        self.canvas.center_on_world_point((vehicle.x, vehicle.y))

    def _selected_vehicle_lines(self) -> list[str]:
        contribution_mode = 'on' if self.is_selected_vehicle_contribution_only() else 'off'
        follow_mode = 'on' if self._follow_selected_vehicle else 'off'
        if self._selected_vehicle_id is None:
            return [
                '- Selected vehicle: none',
                f'- Contribution-only heatmap: {contribution_mode}',
                f'- Camera follow: {follow_mode}',
            ]
        vehicle = self._current_frame_vehicle_lookup.get(self._selected_vehicle_id)
        if vehicle is None:
            return [
                f'- Selected vehicle: {self._selected_vehicle_id}',
                '- Status: not present in current frame',
                f'- Contribution-only heatmap: {contribution_mode}',
                f'- Camera follow: {follow_mode}',
            ]
        lines = [
            f'- Selected vehicle: {vehicle.vehicle_id}',
            f'- Type: {vehicle.vehicle_type}',
            f'- Speed: {vehicle.speed_mps * 3.6:.1f} km/h',
            f'- Position: ({vehicle.x:.1f}, {vehicle.y:.1f})',
            f'- Frame: {self._current_frame_index}',
            f'- Contribution-only heatmap: {contribution_mode}',
            f'- Camera follow: {follow_mode}',
        ]
        if self._selected_vehicle_receiver_contributions:
            top_items = sorted(self._selected_vehicle_receiver_contributions.items(), key=lambda item: item[1], reverse=True)[:3]
            lines.append('- Receiver contributions:')
            for receiver_id, value_db in top_items:
                lines.append(f'  {receiver_id}: {value_db:.1f} dB')
        return lines


    def _build_timeline_events(self, dataset: PlaybackDataset) -> dict[int, list[PlaybackTimelineEvent]]:
        events_by_frame: dict[int, list[PlaybackTimelineEvent]] = {}
        for frame_index, frame in enumerate(dataset.frames):
            frame_events: list[PlaybackTimelineEvent] = []
            current_lookup = {vehicle.vehicle_id: vehicle for vehicle in frame.vehicles}
            previous_lookup = {}
            next_lookup = {}
            if frame_index > 0:
                previous_lookup = {vehicle.vehicle_id: vehicle for vehicle in dataset.frames[frame_index - 1].vehicles}
            if frame_index + 1 < dataset.frame_count:
                next_lookup = {vehicle.vehicle_id: vehicle for vehicle in dataset.frames[frame_index + 1].vehicles}

            if previous_lookup:
                entered = sorted(current_lookup.keys() - previous_lookup.keys())
                exited = sorted(previous_lookup.keys() - current_lookup.keys())
                if entered:
                    frame_events.append(PlaybackTimelineEvent('enter', self._event_label('Enter', entered), tuple(entered[:3])))
                if exited:
                    frame_events.append(PlaybackTimelineEvent('exit', self._event_label('Exit', exited), tuple(exited[:3])))

                speed_shift_ids: list[tuple[float, str]] = []
                for vehicle_id in current_lookup.keys() & previous_lookup.keys():
                    delta_kmh = abs(current_lookup[vehicle_id].speed_mps - previous_lookup[vehicle_id].speed_mps) * 3.6
                    if delta_kmh >= 10.0:
                        speed_shift_ids.append((delta_kmh, vehicle_id))
                if speed_shift_ids:
                    speed_shift_ids.sort(reverse=True)
                    speed_ids = [vehicle_id for _, vehicle_id in speed_shift_ids]
                    frame_events.append(
                        PlaybackTimelineEvent(
                            'speed_shift',
                            f"Speed shift x{len(speed_shift_ids)} (max {speed_shift_ids[0][0]:.1f} km/h)",
                            tuple(speed_ids[:3]),
                        )
                    )

            if previous_lookup and next_lookup:
                heading_shift_ids: list[tuple[float, str]] = []
                common_ids = current_lookup.keys() & previous_lookup.keys() & next_lookup.keys()
                for vehicle_id in common_ids:
                    before_heading = self._heading_between(previous_lookup[vehicle_id], current_lookup[vehicle_id])
                    after_heading = self._heading_between(current_lookup[vehicle_id], next_lookup[vehicle_id])
                    if before_heading is None or after_heading is None:
                        continue
                    delta_heading = abs(self._wrapped_angle_diff(after_heading, before_heading))
                    if delta_heading >= 18.0:
                        heading_shift_ids.append((delta_heading, vehicle_id))
                if heading_shift_ids:
                    heading_shift_ids.sort(reverse=True)
                    heading_ids = [vehicle_id for _, vehicle_id in heading_shift_ids]
                    frame_events.append(
                        PlaybackTimelineEvent(
                            'heading_shift',
                            f"Heading shift x{len(heading_shift_ids)} (max {heading_shift_ids[0][0]:.0f} deg)",
                            tuple(heading_ids[:3]),
                        )
                    )

            if frame_events:
                events_by_frame[frame_index] = frame_events
        return events_by_frame

    def _event_label(self, prefix: str, vehicle_ids: list[str]) -> str:
        sample = ', '.join(vehicle_ids[:3])
        suffix = f' [{sample}]' if sample else ''
        if len(vehicle_ids) > 3:
            suffix += ' +'
        return f'{prefix} x{len(vehicle_ids)}{suffix}'

    def _heading_between(self, first, second) -> float | None:
        dx = second.x - first.x
        dy = second.y - first.y
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            return None
        return degrees(atan2(dy, dx))

    def _wrapped_angle_diff(self, angle_a: float, angle_b: float) -> float:
        diff = angle_a - angle_b
        while diff > 180.0:
            diff -= 360.0
        while diff < -180.0:
            diff += 360.0
        return diff

    def _timeline_event_lines(self, current_frame: int | None) -> list[str]:
        if self.dataset is None:
            return ['- Timeline events unavailable']
        total_events = sum(len(events) for events in self._timeline_events_by_frame.values())
        if total_events == 0:
            return ['- No timeline events detected']
        frame_index = current_frame if current_frame is not None else self.slider.value()
        lines = [f'- Event frames: {len(self._timeline_events_by_frame)}', f'- Event count: {total_events}']
        current_events = self._timeline_events_by_frame.get(frame_index, [])
        if current_events:
            lines.append('- Current frame events:')
            for event in current_events:
                lines.append(f'  {event.label}')
        upcoming_frames = [index for index in sorted(self._timeline_events_by_frame) if index > frame_index][:3]
        if upcoming_frames:
            lines.append('- Upcoming events:')
            for upcoming_index in upcoming_frames:
                joined = '; '.join(event.label for event in self._timeline_events_by_frame[upcoming_index][:2])
                lines.append(f'  @{upcoming_index}: {joined}')
        return lines

    def _apply_display_state(self, *args) -> None:  # noqa: ARG002
        self.canvas.set_snapshot(self._filtered_snapshot())
        self.canvas.set_vehicle_points(self._raw_glyphs if self.vehicles_check.isChecked() else [], trails=self._raw_trails if self.trails_check.isChecked() else [])
        self.canvas.set_selected_vehicle(self._selected_vehicle_id if self.vehicles_check.isChecked() else None)
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
                    f"- Camera follow: {'on' if self._follow_selected_vehicle else 'off'}",
                    '- Vehicle color: speed colormap',
                    '- Right panel: layer toggles + heatmap controls',
                ]
            )
        lines.extend(['', 'Timeline Events', *self._timeline_event_lines(current_frame), '', 'Selected Vehicle', *self._selected_vehicle_lines()])
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
