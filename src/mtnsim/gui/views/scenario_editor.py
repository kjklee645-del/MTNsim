from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ScenarioEditorView(QWidget):
    save_as_requested = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_source_path = ''
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel('Limited Scenario Editor')
        title.setStyleSheet('font-size: 22px; font-weight: 700;')
        root.addWidget(title)

        self.info_box = QTextEdit()
        self.info_box.setReadOnly(True)
        self.info_box.setMaximumHeight(120)
        root.addWidget(self.info_box)

        form = QFormLayout()

        self.name_edit = QLineEdit()
        form.addRow('Scenario Name', self.name_edit)

        self.description_edit = QLineEdit()
        form.addRow('Description', self.description_edit)

        self.max_vehicles_spin = QSpinBox()
        self.max_vehicles_spin.setRange(1, 100000)
        form.addRow('Max Vehicles', self.max_vehicles_spin)

        self.start_speed_spin = QDoubleSpinBox()
        self.start_speed_spin.setRange(0.0, 300.0)
        self.start_speed_spin.setDecimals(1)
        self.start_speed_spin.setSuffix(' km/h')
        form.addRow('Start Speed', self.start_speed_spin)

        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.1, 600.0)
        self.interval_spin.setDecimals(1)
        self.interval_spin.setSuffix(' s')
        form.addRow('Vehicle Interval', self.interval_spin)

        self.post_distance_spin = QDoubleSpinBox()
        self.post_distance_spin.setRange(0.0, 5000.0)
        self.post_distance_spin.setDecimals(1)
        self.post_distance_spin.setSuffix(' m')
        form.addRow('Post Distance', self.post_distance_spin)

        self.target_speed_spin = QDoubleSpinBox()
        self.target_speed_spin.setRange(0.0, 300.0)
        self.target_speed_spin.setDecimals(1)
        self.target_speed_spin.setSuffix(' km/h')
        form.addRow('Post Target Speed', self.target_speed_spin)

        self.lane_change_mode_combo = QComboBox()
        for option in ['disable', 'enforce']:
            self.lane_change_mode_combo.addItem(option, option)
        form.addRow('Lane Change Mode', self.lane_change_mode_combo)

        self.lane_change_strategy_combo = QComboBox()
        for option in ['custom']:
            self.lane_change_strategy_combo.addItem(option, option)
        form.addRow('Lane Change Strategy', self.lane_change_strategy_combo)

        self.background_noise_spin = QDoubleSpinBox()
        self.background_noise_spin.setRange(0.0, 120.0)
        self.background_noise_spin.setDecimals(1)
        self.background_noise_spin.setSuffix(' dB')
        form.addRow('Background Noise', self.background_noise_spin)

        self.post_distance_control_check = QCheckBox('Enable post-distance speed control')
        form.addRow('Post Control', self.post_distance_control_check)

        self.lane_change_force_check = QCheckBox('Force lane change')
        form.addRow('Lane Change Force', self.lane_change_force_check)

        root.addLayout(form)

        button_row = QHBoxLayout()
        self.save_as_button = QPushButton('Save As New Scenario')
        self.save_as_button.clicked.connect(self._emit_save_as)
        self.save_as_button.setEnabled(False)
        button_row.addWidget(self.save_as_button)
        button_row.addStretch(1)
        root.addLayout(button_row)

        self.status_label = QLabel('Select a scenario to edit its limited parameters.')
        root.addWidget(self.status_label)

    def set_scenario(self, scenario_path, scenario) -> None:
        self._current_source_path = str(scenario_path) if scenario_path is not None else ''
        self.name_edit.setText(scenario.scenario.name)
        self.description_edit.setText(scenario.scenario.description)
        self.max_vehicles_spin.setValue(int(scenario.traffic.max_vehicles))
        self.start_speed_spin.setValue(float(scenario.traffic.start_speed_kmh))
        self.interval_spin.setValue(float(scenario.traffic.vehicle_interval_seconds))
        self.post_distance_spin.setValue(float(scenario.controls.post_distance_meters))
        self.target_speed_spin.setValue(float(scenario.controls.post_target_speed_kmh))
        self._set_combo_value(self.lane_change_mode_combo, scenario.controls.lane_change_mode)
        self._set_combo_value(self.lane_change_strategy_combo, scenario.controls.lane_change_strategy)
        self.background_noise_spin.setValue(float(scenario.noise.background_noise_db))
        self.post_distance_control_check.setChecked(bool(scenario.controls.post_distance_speed_control))
        self.lane_change_force_check.setChecked(bool(scenario.controls.lane_change_force_change))
        self.info_box.setPlainText('\n'.join([
            f'Source file: {scenario_path}',
            f'Receivers: {len(scenario.receivers)}',
            f'Noise barriers: {len(scenario.scene.noise_barriers)}',
            f'Buildings: {len(scenario.scene.buildings)}',
            f'Terrain edges: {len(scenario.scene.terrain_edges)}',
            f'Vegetation zones: {len(scenario.scene.vegetation_zones)}',
        ]))
        self.status_label.setText('Edit selected fields and use Save As to create a derived scenario.')
        self.save_as_button.setEnabled(True)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)
        else:
            combo.addItem(value, value)
            combo.setCurrentIndex(combo.count() - 1)

    def _emit_save_as(self) -> None:
        if not self._current_source_path:
            return
        payload = {
            'source_path': self._current_source_path,
            'scenario_name': self.name_edit.text().strip(),
            'description': self.description_edit.text().strip(),
            'traffic.max_vehicles': int(self.max_vehicles_spin.value()),
            'traffic.start_speed_kmh': float(self.start_speed_spin.value()),
            'traffic.vehicle_interval_seconds': float(self.interval_spin.value()),
            'controls.post_distance_meters': float(self.post_distance_spin.value()),
            'controls.post_target_speed_kmh': float(self.target_speed_spin.value()),
            'controls.lane_change_mode': str(self.lane_change_mode_combo.currentData() or self.lane_change_mode_combo.currentText()),
            'controls.lane_change_strategy': str(self.lane_change_strategy_combo.currentData() or self.lane_change_strategy_combo.currentText()),
            'controls.post_distance_speed_control': bool(self.post_distance_control_check.isChecked()),
            'controls.lane_change_force_change': bool(self.lane_change_force_check.isChecked()),
            'noise.background_noise_db': float(self.background_noise_spin.value()),
        }
        self.save_as_requested.emit(payload)
