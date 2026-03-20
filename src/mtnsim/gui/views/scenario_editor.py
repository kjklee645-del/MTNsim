from __future__ import annotations

from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mtnsim.gui.directivity_presets import DIRECTIVITY_PRESET_OPTIONS, get_directivity_preset_values, infer_directivity_preset


class ScenarioEditorView(QWidget):
    save_as_requested = Signal(dict)
    preview_requested = Signal(dict)
    grid_region_draw_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_source_path = ''
        self._suspend_preview = False
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._emit_preview_if_valid)
        self._build_ui()
        self._connect_preview_sources()
        self._on_directivity_preset_changed()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(scroll, 1)

        content = QWidget()
        scroll.setWidget(content)

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        title = QLabel('Limited Scenario Editor')
        title.setObjectName('pageTitle')
        content_layout.addWidget(title)

        self.info_box = QTextEdit()
        self.info_box.setObjectName('infoCard')
        self.info_box.setReadOnly(True)
        self.info_box.setMaximumHeight(120)
        content_layout.addWidget(self.info_box)

        tabs = QTabWidget()
        tabs.setObjectName('infoCard')
        content_layout.addWidget(tabs, 1)

        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        basic_layout.setContentsMargins(10, 10, 10, 10)
        basic_layout.setSpacing(10)

        basic_card = QFrame()
        basic_card.setObjectName('infoCard')
        basic_card_layout = QVBoxLayout(basic_card)
        basic_card_layout.setContentsMargins(14, 14, 14, 14)
        basic_form = QFormLayout()

        self.name_edit = QLineEdit()
        basic_form.addRow('Scenario Name', self.name_edit)

        self.description_edit = QLineEdit()
        basic_form.addRow('Description', self.description_edit)

        self.max_vehicles_spin = QSpinBox()
        self.max_vehicles_spin.setRange(1, 100000)
        basic_form.addRow('Max Vehicles', self.max_vehicles_spin)

        self.start_speed_spin = QDoubleSpinBox()
        self.start_speed_spin.setRange(0.0, 300.0)
        self.start_speed_spin.setDecimals(1)
        self.start_speed_spin.setSuffix(' km/h')
        basic_form.addRow('Start Speed', self.start_speed_spin)

        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.1, 600.0)
        self.interval_spin.setDecimals(1)
        self.interval_spin.setSuffix(' s')
        basic_form.addRow('Vehicle Interval', self.interval_spin)

        self.post_distance_spin = QDoubleSpinBox()
        self.post_distance_spin.setRange(0.0, 5000.0)
        self.post_distance_spin.setDecimals(1)
        self.post_distance_spin.setSuffix(' m')
        basic_form.addRow('Post Distance', self.post_distance_spin)

        self.target_speed_spin = QDoubleSpinBox()
        self.target_speed_spin.setRange(0.0, 300.0)
        self.target_speed_spin.setDecimals(1)
        self.target_speed_spin.setSuffix(' km/h')
        basic_form.addRow('Post Target Speed', self.target_speed_spin)

        self.lane_change_mode_combo = QComboBox()
        for option in ['disable', 'enforce']:
            self.lane_change_mode_combo.addItem(option, option)
        basic_form.addRow('Lane Change Mode', self.lane_change_mode_combo)

        self.lane_change_strategy_combo = QComboBox()
        for option in ['custom']:
            self.lane_change_strategy_combo.addItem(option, option)
        basic_form.addRow('Lane Change Strategy', self.lane_change_strategy_combo)

        self.post_distance_control_check = QCheckBox('Enable post-distance speed control')
        basic_form.addRow('Post Control', self.post_distance_control_check)

        self.lane_change_force_check = QCheckBox('Force lane change')
        basic_form.addRow('Lane Change Force', self.lane_change_force_check)

        self.background_noise_spin = QDoubleSpinBox()
        self.background_noise_spin.setRange(0.0, 120.0)
        self.background_noise_spin.setDecimals(1)
        self.background_noise_spin.setSuffix(' dB')
        basic_form.addRow('Background Noise', self.background_noise_spin)

        basic_card_layout.addLayout(basic_form)
        basic_layout.addWidget(basic_card)
        basic_layout.addStretch(1)
        tabs.addTab(basic_tab, 'Basic')

        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)
        advanced_layout.setContentsMargins(10, 10, 10, 10)
        advanced_layout.setSpacing(10)

        advanced_card = QFrame()
        advanced_card.setObjectName('infoCard')
        advanced_card_layout = QVBoxLayout(advanced_card)
        advanced_card_layout.setContentsMargins(14, 14, 14, 14)
        advanced_form = QFormLayout()

        self.max_area_spin = QDoubleSpinBox()
        self.max_area_spin.setRange(1.0, 5000.0)
        self.max_area_spin.setDecimals(1)
        self.max_area_spin.setSuffix(' m')
        advanced_form.addRow('Max Area', self.max_area_spin)

        self.grid_size_spin = QDoubleSpinBox()
        self.grid_size_spin.setRange(0.1, 500.0)
        self.grid_size_spin.setDecimals(1)
        self.grid_size_spin.setSuffix(' m')
        advanced_form.addRow('Grid Size', self.grid_size_spin)

        self.receiver_height_spin = QDoubleSpinBox()
        self.receiver_height_spin.setRange(0.0, 50.0)
        self.receiver_height_spin.setDecimals(1)
        self.receiver_height_spin.setSuffix(' m')
        advanced_form.addRow('Receiver Height', self.receiver_height_spin)

        self.directivity_preset_combo = QComboBox()
        for label, value in DIRECTIVITY_PRESET_OPTIONS:
            self.directivity_preset_combo.addItem(label, value)
        advanced_form.addRow('Directivity Preset', self.directivity_preset_combo)

        self.directivity_mode_combo = QComboBox()
        for option in ['isotropic', 'wedge', 'dual_wedge']:
            self.directivity_mode_combo.addItem(option, option)
        advanced_form.addRow('Directivity Mode', self.directivity_mode_combo)

        self.directivity_strength_spin = QDoubleSpinBox()
        self.directivity_strength_spin.setRange(0.0, 30.0)
        self.directivity_strength_spin.setDecimals(1)
        self.directivity_strength_spin.setSuffix(' dB')
        advanced_form.addRow('Directivity Strength', self.directivity_strength_spin)

        self.directivity_wedge_angle_spin = QDoubleSpinBox()
        self.directivity_wedge_angle_spin.setRange(10.0, 180.0)
        self.directivity_wedge_angle_spin.setDecimals(1)
        self.directivity_wedge_angle_spin.setSuffix(' deg')
        advanced_form.addRow('Directivity Wedge Angle', self.directivity_wedge_angle_spin)

        self.directivity_vertical_strength_spin = QDoubleSpinBox()
        self.directivity_vertical_strength_spin.setRange(0.0, 30.0)
        self.directivity_vertical_strength_spin.setDecimals(1)
        self.directivity_vertical_strength_spin.setSuffix(' dB')
        advanced_form.addRow('Directivity Vertical Strength', self.directivity_vertical_strength_spin)

        self.directivity_vertical_angle_spin = QDoubleSpinBox()
        self.directivity_vertical_angle_spin.setRange(5.0, 180.0)
        self.directivity_vertical_angle_spin.setDecimals(1)
        self.directivity_vertical_angle_spin.setSuffix(' deg')
        advanced_form.addRow('Directivity Vertical Angle', self.directivity_vertical_angle_spin)

        self.grid_margin_start_spin = QDoubleSpinBox()
        self.grid_margin_start_spin.setRange(0.0, 5000.0)
        self.grid_margin_start_spin.setDecimals(1)
        self.grid_margin_start_spin.setSuffix(' m')
        advanced_form.addRow('Grid Margin Start', self.grid_margin_start_spin)

        self.grid_margin_end_spin = QDoubleSpinBox()
        self.grid_margin_end_spin.setRange(0.0, 5000.0)
        self.grid_margin_end_spin.setDecimals(1)
        self.grid_margin_end_spin.setSuffix(' m')
        advanced_form.addRow('Grid Margin End', self.grid_margin_end_spin)

        self.grid_extra_y_spin = QDoubleSpinBox()
        self.grid_extra_y_spin.setRange(0.0, 5000.0)
        self.grid_extra_y_spin.setDecimals(1)
        self.grid_extra_y_spin.setSuffix(' m')
        advanced_form.addRow('Grid Extra Y', self.grid_extra_y_spin)

        self.grid_override_check = QCheckBox('Use explicit grid bounds')
        advanced_form.addRow('Grid Override', self.grid_override_check)

        self.grid_override_min_x_spin = QDoubleSpinBox()
        self.grid_override_min_x_spin.setRange(-100000.0, 100000.0)
        self.grid_override_min_x_spin.setDecimals(1)
        self.grid_override_min_x_spin.setSuffix(' m')
        advanced_form.addRow('Grid Min X', self.grid_override_min_x_spin)

        self.grid_override_max_x_spin = QDoubleSpinBox()
        self.grid_override_max_x_spin.setRange(-100000.0, 100000.0)
        self.grid_override_max_x_spin.setDecimals(1)
        self.grid_override_max_x_spin.setSuffix(' m')
        advanced_form.addRow('Grid Max X', self.grid_override_max_x_spin)

        self.grid_override_min_y_spin = QDoubleSpinBox()
        self.grid_override_min_y_spin.setRange(-100000.0, 100000.0)
        self.grid_override_min_y_spin.setDecimals(1)
        self.grid_override_min_y_spin.setSuffix(' m')
        advanced_form.addRow('Grid Min Y', self.grid_override_min_y_spin)

        self.grid_override_max_y_spin = QDoubleSpinBox()
        self.grid_override_max_y_spin.setRange(-100000.0, 100000.0)
        self.grid_override_max_y_spin.setDecimals(1)
        self.grid_override_max_y_spin.setSuffix(' m')
        advanced_form.addRow('Grid Max Y', self.grid_override_max_y_spin)

        self.draw_grid_region_button = QPushButton('Draw Grid Region')
        self.draw_grid_region_button.clicked.connect(self.grid_region_draw_requested)
        self.draw_grid_region_button.setEnabled(False)
        advanced_form.addRow('Grid Draw', self.draw_grid_region_button)

        advanced_card_layout.addLayout(advanced_form)
        advanced_layout.addWidget(advanced_card)
        advanced_layout.addStretch(1)
        tabs.addTab(advanced_tab, 'Advanced')

        receivers_tab = QWidget()
        receivers_layout = QVBoxLayout(receivers_tab)
        receivers_layout.setContentsMargins(10, 10, 10, 10)
        receivers_layout.setSpacing(10)

        receiver_title_row = QHBoxLayout()
        receiver_title = QLabel('Receivers')
        receiver_title.setObjectName('sectionTitle')
        receiver_title_row.addWidget(receiver_title)
        receiver_title_row.addStretch(1)
        self.add_receiver_button = QPushButton('Add Receiver')
        self.add_receiver_button.clicked.connect(self._add_receiver_row)
        self.add_receiver_button.setEnabled(False)
        receiver_title_row.addWidget(self.add_receiver_button)
        self.remove_receiver_button = QPushButton('Remove Selected')
        self.remove_receiver_button.clicked.connect(self._remove_selected_receiver_rows)
        self.remove_receiver_button.setEnabled(False)
        receiver_title_row.addWidget(self.remove_receiver_button)
        receivers_layout.addLayout(receiver_title_row)

        self.receiver_table = QTableWidget(0, 4)
        self.receiver_table.setObjectName('infoCard')
        self.receiver_table.setHorizontalHeaderLabels(['ID', 'X', 'Y', 'Z'])
        self.receiver_table.horizontalHeader().setStretchLastSection(True)
        self.receiver_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.receiver_table.setAlternatingRowColors(True)
        self.receiver_table.setMinimumHeight(140)
        receivers_layout.addWidget(self.receiver_table, 1)
        tabs.addTab(receivers_tab, 'Receivers')

        button_row = QHBoxLayout()
        self.save_as_button = QPushButton('Save As New Scenario')
        self.save_as_button.clicked.connect(self._emit_save_as)
        self.save_as_button.setEnabled(False)
        button_row.addWidget(self.save_as_button)
        button_row.addStretch(1)
        content_layout.addLayout(button_row)

        self.status_label = QLabel('Select a scenario to edit its limited parameters.')
        self.status_label.setObjectName('statusBadgeNeutral')
        content_layout.addWidget(self.status_label)
        content_layout.addStretch(1)

    def _connect_preview_sources(self) -> None:
        watched = [
            self.max_vehicles_spin,
            self.start_speed_spin,
            self.interval_spin,
            self.post_distance_spin,
            self.target_speed_spin,
            self.background_noise_spin,
            self.max_area_spin,
            self.grid_size_spin,
            self.receiver_height_spin,
            self.directivity_strength_spin,
            self.directivity_wedge_angle_spin,
            self.directivity_vertical_strength_spin,
            self.directivity_vertical_angle_spin,
            self.grid_margin_start_spin,
            self.grid_margin_end_spin,
            self.grid_extra_y_spin,
            self.grid_override_min_x_spin,
            self.grid_override_max_x_spin,
            self.grid_override_min_y_spin,
            self.grid_override_max_y_spin,
        ]
        for widget in watched:
            widget.valueChanged.connect(self._sync_directivity_preset_from_controls)
            widget.valueChanged.connect(self._schedule_preview)
        self.lane_change_mode_combo.currentIndexChanged.connect(self._schedule_preview)
        self.lane_change_strategy_combo.currentIndexChanged.connect(self._schedule_preview)
        self.directivity_preset_combo.currentIndexChanged.connect(self._on_directivity_preset_changed)
        self.directivity_mode_combo.currentIndexChanged.connect(self._sync_directivity_preset_from_controls)
        self.directivity_mode_combo.currentIndexChanged.connect(self._schedule_preview)
        self.post_distance_control_check.toggled.connect(self._schedule_preview)
        self.lane_change_force_check.toggled.connect(self._schedule_preview)
        self.grid_override_check.toggled.connect(self._schedule_preview)
        self.receiver_table.itemChanged.connect(self._schedule_preview)

    def set_scenario(self, scenario_path, scenario) -> None:
        self._suspend_preview = True
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
        self.max_area_spin.setValue(float(scenario.noise.max_area_meters))
        self.grid_size_spin.setValue(float(scenario.noise.grid_size_meters))
        self.receiver_height_spin.setValue(float(scenario.noise.receiver_height_meters))
        preset = getattr(scenario.noise.directivity, 'preset', 'custom') or 'custom'
        if preset == 'custom':
            preset = infer_directivity_preset(
                scenario.noise.directivity.mode,
                float(scenario.noise.directivity.strength_db),
                float(scenario.noise.directivity.wedge_angle_deg),
                float(scenario.noise.directivity.vertical_strength_db),
                float(scenario.noise.directivity.vertical_angle_deg),
            )
        self._set_combo_value(self.directivity_preset_combo, preset)
        self._set_combo_value(self.directivity_mode_combo, scenario.noise.directivity.mode)
        self.directivity_strength_spin.setValue(float(scenario.noise.directivity.strength_db))
        self.directivity_wedge_angle_spin.setValue(float(scenario.noise.directivity.wedge_angle_deg))
        self.directivity_vertical_strength_spin.setValue(float(scenario.noise.directivity.vertical_strength_db))
        self.directivity_vertical_angle_spin.setValue(float(scenario.noise.directivity.vertical_angle_deg))
        self.grid_margin_start_spin.setValue(float(scenario.grid.margin_x_start))
        self.grid_margin_end_spin.setValue(float(scenario.grid.margin_x_end))
        self.grid_extra_y_spin.setValue(float(scenario.grid.extra_y_extent))
        self.grid_override_check.setChecked(bool(scenario.grid.override_enabled))
        self.grid_override_min_x_spin.setValue(float(scenario.grid.override_min_x or 0.0))
        self.grid_override_max_x_spin.setValue(float(scenario.grid.override_max_x or 0.0))
        self.grid_override_min_y_spin.setValue(float(scenario.grid.override_min_y or 0.0))
        self.grid_override_max_y_spin.setValue(float(scenario.grid.override_max_y or 0.0))
        self.post_distance_control_check.setChecked(bool(scenario.controls.post_distance_speed_control))
        self.lane_change_force_check.setChecked(bool(scenario.controls.lane_change_force_change))

        self.receiver_table.blockSignals(True)
        self.receiver_table.setRowCount(0)
        for receiver in scenario.receivers:
            self._append_receiver_row(receiver.id, float(receiver.x), float(receiver.y), float(receiver.z))
        self.receiver_table.blockSignals(False)

        self.info_box.setPlainText('\n'.join([
            f'Source file: {scenario_path}',
            f'Receivers: {len(scenario.receivers)}',
            f'Noise barriers: {len(scenario.scene.noise_barriers)}',
            f'Buildings: {len(scenario.scene.buildings)}',
            f'Terrain edges: {len(scenario.scene.terrain_edges)}',
            f'Vegetation zones: {len(scenario.scene.vegetation_zones)}',
        ]))
        self.status_label.setText('Edit selected fields and use Save As to create a derived scenario. Preview updates the scene live when values are valid.')
        self._apply_status_style(self.status_label.text())
        self.save_as_button.setEnabled(True)
        self.add_receiver_button.setEnabled(True)
        self.remove_receiver_button.setEnabled(True)
        self.draw_grid_region_button.setEnabled(True)
        self._suspend_preview = False
        self._emit_preview_if_valid()

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)
        self._apply_status_style(text)

    def _schedule_preview(self, *args) -> None:  # noqa: ANN002
        if self._suspend_preview:
            return
        self._preview_timer.start(120)

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)
        else:
            combo.addItem(value, value)
            combo.setCurrentIndex(combo.count() - 1)

    def _on_directivity_preset_changed(self, *args) -> None:  # noqa: ANN002
        preset = str(self.directivity_preset_combo.currentData() or 'custom')
        values = get_directivity_preset_values(preset)
        if preset != 'custom':
            self._suspend_preview = True
            self._set_combo_value(self.directivity_mode_combo, str(values['mode']))
            self.directivity_strength_spin.setValue(float(values['strength_db']))
            self.directivity_wedge_angle_spin.setValue(float(values['wedge_angle_deg']))
            self.directivity_vertical_strength_spin.setValue(float(values['vertical_strength_db']))
            self.directivity_vertical_angle_spin.setValue(float(values['vertical_angle_deg']))
            self._suspend_preview = False
        enabled = preset == 'custom'
        self.directivity_mode_combo.setEnabled(enabled)
        self.directivity_strength_spin.setEnabled(enabled)
        self.directivity_wedge_angle_spin.setEnabled(enabled)
        self.directivity_vertical_strength_spin.setEnabled(enabled)
        self.directivity_vertical_angle_spin.setEnabled(enabled)
        self._schedule_preview()

    def _sync_directivity_preset_from_controls(self, *args) -> None:  # noqa: ANN002
        if self._suspend_preview:
            return
        inferred = infer_directivity_preset(
            str(self.directivity_mode_combo.currentData() or self.directivity_mode_combo.currentText()),
            float(self.directivity_strength_spin.value()),
            float(self.directivity_wedge_angle_spin.value()),
            float(self.directivity_vertical_strength_spin.value()),
            float(self.directivity_vertical_angle_spin.value()),
        )
        current = str(self.directivity_preset_combo.currentData() or 'custom')
        if current != inferred:
            self.directivity_preset_combo.blockSignals(True)
            self._set_combo_value(self.directivity_preset_combo, inferred)
            self.directivity_preset_combo.blockSignals(False)
            enabled = inferred == 'custom'
            self.directivity_mode_combo.setEnabled(enabled)
            self.directivity_strength_spin.setEnabled(enabled)
            self.directivity_wedge_angle_spin.setEnabled(enabled)
            self.directivity_vertical_strength_spin.setEnabled(enabled)
            self.directivity_vertical_angle_spin.setEnabled(enabled)

    def _append_receiver_row(self, receiver_id: str, x: float, y: float, z: float) -> None:
        row = self.receiver_table.rowCount()
        self.receiver_table.insertRow(row)
        values = [receiver_id, f'{x:.2f}', f'{y:.2f}', f'{z:.2f}']
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            if column == 0:
                item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.receiver_table.setItem(row, column, item)

    def _add_receiver_row(self) -> None:
        self.receiver_table.blockSignals(True)
        next_index = self.receiver_table.rowCount() + 1
        self._append_receiver_row(f'receiver_{next_index}', 0.0, 0.0, 1.5)
        self.receiver_table.blockSignals(False)
        self.receiver_table.selectRow(self.receiver_table.rowCount() - 1)
        self._schedule_preview()

    def _remove_selected_receiver_rows(self) -> None:
        selected_rows = sorted({index.row() for index in self.receiver_table.selectionModel().selectedRows()}, reverse=True)
        for row in selected_rows:
            self.receiver_table.removeRow(row)
        self._schedule_preview()

    def _build_payload(self, strict: bool) -> tuple[dict | None, list[str]]:
        errors: list[str] = []

        scenario_name = self.name_edit.text().strip()
        if strict and not scenario_name:
            errors.append('Scenario name must not be empty.')

        if self.grid_size_spin.value() <= 0:
            errors.append('Grid size must be greater than 0.')
        if self.max_area_spin.value() < self.grid_size_spin.value():
            errors.append('Max area must be greater than or equal to grid size.')
        if self.post_distance_control_check.isChecked() and self.post_distance_spin.value() <= 0:
            errors.append('Post distance must be greater than 0 when post-distance control is enabled.')
        if self.receiver_height_spin.value() < 0:
            errors.append('Receiver height must not be negative.')
        if self.grid_override_check.isChecked():
            if self.grid_override_max_x_spin.value() <= self.grid_override_min_x_spin.value():
                errors.append('Grid Max X must be greater than Grid Min X when grid override is enabled.')
            if self.grid_override_max_y_spin.value() <= self.grid_override_min_y_spin.value():
                errors.append('Grid Max Y must be greater than Grid Min Y when grid override is enabled.')

        receivers: list[dict] = []
        seen_ids: set[str] = set()
        if self.receiver_table.rowCount() == 0:
            errors.append('At least one receiver is required.')

        for row in range(self.receiver_table.rowCount()):
            id_item = self.receiver_table.item(row, 0)
            x_item = self.receiver_table.item(row, 1)
            y_item = self.receiver_table.item(row, 2)
            z_item = self.receiver_table.item(row, 3)
            receiver_id = id_item.text().strip() if id_item else ''
            if strict and not receiver_id:
                errors.append(f'Receiver row {row + 1} must have a non-empty ID.')
                continue
            if receiver_id:
                if receiver_id in seen_ids:
                    errors.append(f'Duplicate receiver ID: {receiver_id}')
                seen_ids.add(receiver_id)
            try:
                x = float(x_item.text()) if x_item else 0.0
                y = float(y_item.text()) if y_item else 0.0
                z = float(z_item.text()) if z_item else 0.0
            except ValueError:
                errors.append(f'Receiver row {row + 1} has a non-numeric coordinate value.')
                continue
            if z < 0:
                errors.append(f'Receiver {receiver_id or row + 1} has a negative Z value.')
            receivers.append({'id': receiver_id or f'receiver_{row + 1}', 'x': x, 'y': y, 'z': z})

        if errors:
            return None, errors

        payload = {
            'source_path': self._current_source_path,
            'scenario_name': scenario_name or 'preview_scenario',
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
            'noise.max_area_meters': float(self.max_area_spin.value()),
            'noise.grid_size_meters': float(self.grid_size_spin.value()),
            'noise.receiver_height_meters': float(self.receiver_height_spin.value()),
            'noise.directivity.preset': str(self.directivity_preset_combo.currentData() or self.directivity_preset_combo.currentText()),
            'noise.directivity.mode': str(self.directivity_mode_combo.currentData() or self.directivity_mode_combo.currentText()),
            'noise.directivity.strength_db': float(self.directivity_strength_spin.value()),
            'noise.directivity.wedge_angle_deg': float(self.directivity_wedge_angle_spin.value()),
            'noise.directivity.vertical_strength_db': float(self.directivity_vertical_strength_spin.value()),
            'noise.directivity.vertical_angle_deg': float(self.directivity_vertical_angle_spin.value()),
            'grid.margin_x_start': float(self.grid_margin_start_spin.value()),
            'grid.margin_x_end': float(self.grid_margin_end_spin.value()),
            'grid.extra_y_extent': float(self.grid_extra_y_spin.value()),
            'grid.override_enabled': bool(self.grid_override_check.isChecked()),
            'grid.override_min_x': float(self.grid_override_min_x_spin.value()),
            'grid.override_max_x': float(self.grid_override_max_x_spin.value()),
            'grid.override_min_y': float(self.grid_override_min_y_spin.value()),
            'grid.override_max_y': float(self.grid_override_max_y_spin.value()),
            'receivers': receivers,
        }
        return payload, []

    def _emit_preview_if_valid(self) -> None:
        if not self._current_source_path:
            return
        payload, errors = self._build_payload(strict=False)
        if payload is None:
            self.status_label.setText(f'Preview paused: {errors[0]}')
            self._apply_status_style(self.status_label.text())
            return
        self.preview_requested.emit(payload)


    def apply_drawn_grid_region(self, min_x: float, max_x: float, min_y: float, max_y: float) -> None:
        self.grid_override_check.setChecked(True)
        self.grid_override_min_x_spin.setValue(float(min_x))
        self.grid_override_max_x_spin.setValue(float(max_x))
        self.grid_override_min_y_spin.setValue(float(min_y))
        self.grid_override_max_y_spin.setValue(float(max_y))
        self.set_status('Grid region updated from Scene View.')
        self._emit_preview_if_valid()

    def validate_inputs(self) -> tuple[dict | None, list[str]]:
        return self._build_payload(strict=True)

    def _emit_save_as(self) -> None:
        if not self._current_source_path:
            return
        payload, errors = self.validate_inputs()
        if errors:
            self.status_label.setText(f'Cannot save: {errors[0]}')
            self._apply_status_style(self.status_label.text())
            QMessageBox.warning(self, 'Scenario Editor Validation', '\n'.join(errors))
            return
        self._apply_status_style('Scenario ready to save.')
        self.save_as_requested.emit(payload)

    def _apply_status_style(self, text: str) -> None:
        lowered = text.lower()
        if 'cannot save' in lowered or 'paused' in lowered:
            object_name = 'statusBadgeWarning'
        elif 'ready' in lowered or 'valid' in lowered:
            object_name = 'statusBadgeReady'
        else:
            object_name = 'statusBadgeNeutral'
        if self.status_label.objectName() != object_name:
            self.status_label.setObjectName(object_name)
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)
