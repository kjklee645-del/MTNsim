from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mtnsim.gui.controllers.playback_controller import PlaybackDataset
from mtnsim.gui.controllers.scene_controller import SceneSnapshot
from mtnsim.gui.views.scene_view import SceneCanvas


class VehiclePlaybackView(QWidget):
    playback_frame_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.snapshot: SceneSnapshot | None = None
        self.dataset: PlaybackDataset | None = None
        self._playback_speed = 1.0
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

        self.info_box = QTextEdit()
        self.info_box.setReadOnly(True)
        self.info_box.setMaximumWidth(320)
        splitter.addWidget(self.info_box)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

    def set_snapshot(self, snapshot: SceneSnapshot | None) -> None:
        self.snapshot = snapshot
        self.canvas.set_snapshot(snapshot)
        self._refresh_info()

    def set_dataset(self, dataset: PlaybackDataset | None) -> None:
        self.dataset = dataset
        self._timer.stop()
        self.play_button.setText('Play')
        self.canvas.set_vehicle_points([])
        if dataset is None or dataset.frame_count == 0:
            self.slider.setEnabled(False)
            self.slider.setRange(0, 0)
            self.frame_label.setText('Frame: -')
            self.vehicle_label.setText('Vehicles: -')
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
        self.canvas.set_vehicle_points([(vehicle.vehicle_id, vehicle.x, vehicle.y) for vehicle in frame.vehicles])
        self.frame_label.setText(f'Frame: {frame.time_index} ({frame.sim_time_seconds:.1f}s)')
        self.vehicle_label.setText(f'Vehicles: {len(frame.vehicles)}')
        self._refresh_info(current_frame=frame_index)

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
                ]
            )
        if self.snapshot is not None:
            lines.extend(
                [
                    '',
                    'Scene Layers',
                    f'- Road polylines: {len(self.snapshot.road_layer.polylines)}',
                    f'- Receivers: {len(self.snapshot.receiver_layer.points)}',
                    f'- Buildings: {len(self.snapshot.building_layer.polygons)}',
                    f'- Barriers: {len(self.snapshot.barrier_layer.polylines)}',
                ]
            )
        self.info_box.setPlainText('\n'.join(lines))
