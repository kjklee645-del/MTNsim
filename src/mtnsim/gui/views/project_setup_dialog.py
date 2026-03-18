from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mtnsim.gui.controllers.project_controller import ProjectController


class ProjectSetupDialog(QDialog):
    def __init__(
        self,
        controller: ProjectController,
        *,
        mode: str,
        initial_project_root: str = '',
        initial_project_name: str = '',
        initial_description: str = '',
        initial_scenario_name: str = 'baseline',
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.mode = mode
        self.initial_project_root = initial_project_root
        self.initial_project_name = initial_project_name
        self.initial_description = initial_description
        self.initial_scenario_name = initial_scenario_name or 'baseline'
        self.inspection = None
        title_map = {
            'new': 'Create New Project',
            'import': 'Import SUMO Project',
            'attach': 'Attach SUMO To Project',
        }
        self.setWindowTitle(title_map.get(mode, 'Project Setup'))
        self.resize(760, 560)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        if self.mode == 'new':
            title_text = 'Create a new MTNsim project from a SUMO case'
        elif self.mode == 'attach':
            title_text = 'Attach a SUMO case to the currently loaded MTNsim project'
        else:
            title_text = 'Import an existing SUMO project into MTNsim'
        title = QLabel(title_text)
        title.setWordWrap(True)
        title.setStyleSheet('font-size: 18px; font-weight: 700;')
        root.addWidget(title)

        subtitle = QLabel(
            'This wizard generates or refreshes the project manifest and starter scenario links from the selected SUMO config.'
        )
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(10)

        self.project_name_edit = QLineEdit(self.initial_project_name)
        form.addRow('Project name', self.project_name_edit)

        self.description_edit = QLineEdit(self.initial_description)
        form.addRow('Description', self.description_edit)

        self.default_scenario_edit = QLineEdit(self.initial_scenario_name)
        form.addRow('Default scenario', self.default_scenario_edit)

        self.attach_sumo_checkbox = QCheckBox('Attach SUMO config now')
        self.attach_sumo_checkbox.setChecked(self.mode != 'new')
        self.attach_sumo_checkbox.setEnabled(self.mode == 'new')
        form.addRow('Project mode', self.attach_sumo_checkbox)

        self.project_folder_edit = QLineEdit(self.initial_project_root)
        project_folder_row = QHBoxLayout()
        project_folder_row.addWidget(self.project_folder_edit, 1)
        browse_project_folder = QPushButton('Browse...')
        browse_project_folder.clicked.connect(self._choose_project_folder)
        browse_project_folder.setEnabled(self.mode != 'attach')
        project_folder_row.addWidget(browse_project_folder)
        project_folder_widget = QWidget()
        project_folder_widget.setLayout(project_folder_row)
        form.addRow('Project folder', project_folder_widget)

        self.sumo_config_edit = QLineEdit()
        sumo_config_row = QHBoxLayout()
        sumo_config_row.addWidget(self.sumo_config_edit, 1)
        browse_sumo_config = QPushButton('Browse...')
        browse_sumo_config.clicked.connect(self._choose_sumo_config)
        sumo_config_row.addWidget(browse_sumo_config)
        sumo_config_widget = QWidget()
        sumo_config_widget.setLayout(sumo_config_row)
        form.addRow('SUMO config (.sumocfg)', sumo_config_widget)

        self.copy_files_checkbox = QCheckBox('Copy SUMO files into the project')
        self.copy_files_checkbox.setChecked(True)
        form.addRow('Import mode', self.copy_files_checkbox)

        self.overwrite_checkbox = QCheckBox('Allow overwrite if manifest/scenario already exist')
        self.overwrite_checkbox.setChecked(False)
        form.addRow('Overwrite', self.overwrite_checkbox)

        self.scene_path_edit = QLineEdit()
        scene_row = QHBoxLayout()
        scene_row.addWidget(self.scene_path_edit, 1)
        browse_scene = QPushButton('Browse...')
        browse_scene.clicked.connect(self._choose_scene_file)
        scene_row.addWidget(browse_scene)
        scene_widget = QWidget()
        scene_widget.setLayout(scene_row)
        form.addRow('Scene file (optional)', scene_widget)

        self.measurements_path_edit = QLineEdit()
        measurements_row = QHBoxLayout()
        measurements_row.addWidget(self.measurements_path_edit, 1)
        browse_measurements = QPushButton('Browse...')
        browse_measurements.clicked.connect(self._choose_measurements_file)
        measurements_row.addWidget(browse_measurements)
        measurements_widget = QWidget()
        measurements_widget.setLayout(measurements_row)
        form.addRow('Measurements file (optional)', measurements_widget)

        self.measurement_metadata_path_edit = QLineEdit()
        metadata_row = QHBoxLayout()
        metadata_row.addWidget(self.measurement_metadata_path_edit, 1)
        browse_metadata = QPushButton('Browse...')
        browse_metadata.clicked.connect(self._choose_measurement_metadata_file)
        metadata_row.addWidget(browse_metadata)
        metadata_widget = QWidget()
        metadata_widget.setLayout(metadata_row)
        form.addRow('Measurement metadata (optional)', metadata_widget)

        root.addLayout(form)

        self.attach_refresh_group = QGroupBox('Attach Refresh Scope')
        attach_layout = QVBoxLayout(self.attach_refresh_group)
        attach_layout.setContentsMargins(10, 10, 10, 10)
        attach_layout.setSpacing(6)
        self.attach_selected_only_checkbox = QCheckBox('Refresh only the selected/default scenario')
        self.attach_selected_only_checkbox.setChecked(True)
        attach_layout.addWidget(self.attach_selected_only_checkbox)
        self.attach_update_traffic_checkbox = QCheckBox('Update route types and vehicle types')
        self.attach_update_traffic_checkbox.setChecked(True)
        attach_layout.addWidget(self.attach_update_traffic_checkbox)
        self.attach_update_coefficients_checkbox = QCheckBox('Rebuild vehicle noise coefficients')
        self.attach_update_coefficients_checkbox.setChecked(True)
        attach_layout.addWidget(self.attach_update_coefficients_checkbox)
        self.attach_replace_receivers_checkbox = QCheckBox('Replace placeholder receivers when still unused')
        self.attach_replace_receivers_checkbox.setChecked(True)
        attach_layout.addWidget(self.attach_replace_receivers_checkbox)
        self.attach_update_lane_targets_checkbox = QCheckBox('Refresh lane-change target positions from receivers')
        self.attach_update_lane_targets_checkbox.setChecked(True)
        attach_layout.addWidget(self.attach_update_lane_targets_checkbox)
        self.attach_refresh_group.setVisible(self.mode == 'attach')
        root.addWidget(self.attach_refresh_group)

        inspect_row = QHBoxLayout()
        self.inspect_button = QPushButton('Inspect SUMO Files')
        self.inspect_button.clicked.connect(self.inspect_sumo_source)
        inspect_row.addWidget(self.inspect_button)
        inspect_row.addStretch(1)
        root.addLayout(inspect_row)

        self.validation_label = QLabel('Fill in the fields and inspect the SUMO config before creating the project.')
        self.validation_label.setWordWrap(True)
        root.addWidget(self.validation_label)

        self.summary_box = QPlainTextEdit()
        self.summary_box.setReadOnly(True)
        self.summary_box.setPlaceholderText('Inspection and validation summary will appear here.')
        root.addWidget(self.summary_box, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.accept_button = buttons.button(QDialogButtonBox.Ok)
        if self.mode == 'new':
            self.accept_button.setText('Create Project')
        elif self.mode == 'attach':
            self.accept_button.setText('Attach SUMO')
        else:
            self.accept_button.setText('Import Project')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        for widget in [
            self.project_name_edit,
            self.description_edit,
            self.default_scenario_edit,
            self.project_folder_edit,
            self.sumo_config_edit,
            self.scene_path_edit,
            self.measurements_path_edit,
            self.measurement_metadata_path_edit,
        ]:
            widget.textChanged.connect(self._refresh_validation_summary)
        self.attach_sumo_checkbox.toggled.connect(self._toggle_sumo_mode)
        self.copy_files_checkbox.toggled.connect(self._refresh_validation_summary)
        self.overwrite_checkbox.toggled.connect(self._refresh_validation_summary)
        self.attach_selected_only_checkbox.toggled.connect(self._refresh_validation_summary)
        self.attach_update_traffic_checkbox.toggled.connect(self._refresh_validation_summary)
        self.attach_update_coefficients_checkbox.toggled.connect(self._refresh_validation_summary)
        self.attach_replace_receivers_checkbox.toggled.connect(self._refresh_validation_summary)
        self.attach_update_lane_targets_checkbox.toggled.connect(self._refresh_validation_summary)
        self.sumo_config_edit.textChanged.connect(self._autofill_from_sumo)
        if self.mode == 'attach':
            self.project_name_edit.setEnabled(False)
            self.project_folder_edit.setEnabled(False)
            self.default_scenario_edit.setEnabled(False)
        self._toggle_sumo_mode(self.attach_sumo_checkbox.isChecked())

    def _choose_project_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, 'Choose Project Folder', str(Path.cwd()))
        if folder:
            self.project_folder_edit.setText(folder)
            if not self.project_name_edit.text().strip():
                self.project_name_edit.setText(Path(folder).name)

    def _choose_scene_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Choose Scene File',
            str(Path.cwd()),
            'Scene Files (*.geojson *.json *.csv *.txt);;All Files (*)',
        )
        if file_path:
            self.scene_path_edit.setText(file_path)

    def _choose_measurements_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Choose Measurements File',
            str(Path.cwd()),
            'Measurement Files (*.csv *.json *.txt);;All Files (*)',
        )
        if file_path:
            self.measurements_path_edit.setText(file_path)

    def _choose_measurement_metadata_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Choose Measurement Metadata File',
            str(Path.cwd()),
            'Metadata Files (*.csv *.json *.txt);;All Files (*)',
        )
        if file_path:
            self.measurement_metadata_path_edit.setText(file_path)

    def _choose_sumo_config(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Choose SUMO Config',
            str(Path.cwd()),
            'SUMO Config (*.sumocfg);;XML Files (*.xml);;All Files (*)',
        )
        if file_path:
            self.sumo_config_edit.setText(file_path)

    def _toggle_sumo_mode(self, enabled: bool) -> None:
        self.sumo_config_edit.setEnabled(enabled)
        self.copy_files_checkbox.setEnabled(enabled)
        self.inspect_button.setEnabled(enabled)
        if not enabled:
            self.inspection = None
        self._refresh_validation_summary()

    def _autofill_from_sumo(self) -> None:
        raw = self.sumo_config_edit.text().strip()
        if not raw:
            return
        path = Path(raw)
        if not self.project_name_edit.text().strip():
            self.project_name_edit.setText(path.stem)
        if not self.project_folder_edit.text().strip():
            self.project_folder_edit.setText(str(path.parent / f'{path.stem}_mtnsim'))
        if not self.description_edit.text().strip():
            self.description_edit.setText(f'MTNsim project imported from {path.name}')

    def inspect_sumo_source(self) -> None:
        raw = self.sumo_config_edit.text().strip()
        if not raw:
            QMessageBox.information(self, 'SUMO Config Required', 'Choose a SUMO config file first.')
            return
        try:
            self.inspection = self.controller.inspect_sumo_project(raw)
        except Exception as exc:
            self.inspection = None
            self.validation_label.setText('Inspection failed.')
            self.summary_box.setPlainText(str(exc))
            return
        self._refresh_validation_summary()

    def payload(self) -> dict:
        return {
            'project_name': self.project_name_edit.text().strip(),
            'description': self.description_edit.text().strip(),
            'default_scenario': self.default_scenario_edit.text().strip() or 'baseline',
            'project_root': self.project_folder_edit.text().strip(),
            'attach_sumo_now': self.attach_sumo_checkbox.isChecked(),
            'sumo_config_path': self.sumo_config_edit.text().strip(),
            'copy_sumo_files': self.copy_files_checkbox.isChecked(),
            'overwrite_existing': self.overwrite_checkbox.isChecked(),
            'scene_path': self.scene_path_edit.text().strip(),
            'measurements_path': self.measurements_path_edit.text().strip(),
            'measurement_metadata_path': self.measurement_metadata_path_edit.text().strip(),
            'attach_refresh_selected_only': self.attach_selected_only_checkbox.isChecked(),
            'attach_update_traffic_metadata': self.attach_update_traffic_checkbox.isChecked(),
            'attach_update_vehicle_coefficients': self.attach_update_coefficients_checkbox.isChecked(),
            'attach_replace_placeholder_receivers': self.attach_replace_receivers_checkbox.isChecked(),
            'attach_update_lane_targets': self.attach_update_lane_targets_checkbox.isChecked(),
        }

    def _refresh_validation_summary(self) -> None:
        payload = self.payload()
        project_root = Path(payload['project_root']).expanduser() if payload['project_root'] else None
        manifest_path = project_root / 'project.toml' if project_root is not None else None
        scenario_path = (
            project_root / 'scenarios' / f"{payload['default_scenario']}.toml"
            if project_root is not None and payload['default_scenario']
            else None
        )

        lines: list[str] = []
        problems: list[str] = []
        warnings: list[str] = []

        mode_label = 'New Project' if self.mode == 'new' else ('Attach SUMO To Project' if self.mode == 'attach' else 'Import SUMO Project')
        lines.append(f"Mode: {mode_label}")
        lines.append(f"Project name: {payload['project_name'] or '-'}")
        lines.append(f"Project root: {project_root if project_root is not None else '-'}")
        lines.append(f"Starter scenario: {payload['default_scenario']}")
        lines.append(f"SUMO attached now: {'yes' if payload['attach_sumo_now'] else 'no'}")
        lines.append(f"SUMO config: {payload['sumo_config_path'] or '-'}")
        lines.append(f"Import handling: {'copy into project' if payload['copy_sumo_files'] else 'reference in place'}")
        lines.append(f"Overwrite existing outputs: {'yes' if payload['overwrite_existing'] else 'no'}")
        lines.append(f"Scene file: {payload['scene_path'] or '-'}")
        lines.append(f"Measurements file: {payload['measurements_path'] or '-'}")
        lines.append(f"Measurement metadata: {payload['measurement_metadata_path'] or '-'}")

        if not payload['project_name']:
            problems.append('Project name is required.')
        if project_root is None:
            problems.append('Project folder is required.')
        if payload['attach_sumo_now'] and not payload['sumo_config_path']:
            problems.append('SUMO config is required when SUMO attachment is enabled.')
        if self.mode != 'new' and not payload['sumo_config_path']:
            problems.append('SUMO config is required.')
        if self.mode == 'new' and not payload['attach_sumo_now']:
            warnings.append('This will create an empty project shell. Run actions stay disabled until SUMO is attached later.')
        if self.mode == 'attach':
            refresh_scope = 'selected/default scenario only' if payload['attach_refresh_selected_only'] else 'all discovered scenarios'
            lines.append('Attach target: current project manifest and selected/default scenario will be refreshed.')
            lines.append(f'Attach refresh scope: {refresh_scope}')
            lines.append(f"- update traffic metadata: {'yes' if payload['attach_update_traffic_metadata'] else 'no'}")
            lines.append(f"- rebuild vehicle coefficients: {'yes' if payload['attach_update_vehicle_coefficients'] else 'no'}")
            lines.append(f"- replace placeholder receivers: {'yes' if payload['attach_replace_placeholder_receivers'] else 'no'}")
            lines.append(f"- update lane-change targets: {'yes' if payload['attach_update_lane_targets'] else 'no'}")

        for label, raw_path in [
            ('scene file', payload['scene_path']),
            ('measurements file', payload['measurements_path']),
            ('measurement metadata file', payload['measurement_metadata_path']),
        ]:
            if raw_path and not Path(raw_path).expanduser().exists():
                problems.append(f'{label.capitalize()} does not exist: {raw_path}')
        if payload['measurement_metadata_path'] and not payload['measurements_path']:
            warnings.append('Measurement metadata was provided without a measurements file.')

        if manifest_path is not None:
            lines.append(f'Manifest target: {manifest_path}')
            if self.mode != 'attach' and manifest_path.exists() and not payload['overwrite_existing']:
                warnings.append('Manifest target already exists and overwrite is disabled.')
        if scenario_path is not None:
            lines.append(f'Starter scenario target: {scenario_path}')
            if self.mode != 'attach' and scenario_path.exists() and not payload['overwrite_existing']:
                warnings.append('Starter scenario target already exists and overwrite is disabled.')

        if self.inspection is not None and payload['attach_sumo_now']:
            lines.append('')
            lines.append('SUMO inspection:')
            lines.append(f'- network: {self.inspection.network_path if self.inspection.network_path is not None else "not found"}')
            lines.append(f'- route files: {len(self.inspection.route_paths)}')
            lines.append(f'- additional files: {len(self.inspection.additional_paths)}')
            lines.append(f'- route IDs: {len(self.inspection.route_ids)}')
            lines.append(f'- vehicle types: {", ".join(self.inspection.vehicle_types) if self.inspection.vehicle_types else "not found"}')
            if self.inspection.bounds is not None:
                lines.append(f'- network bounds: {self.inspection.bounds}')
            if self.inspection.missing_paths:
                problems.extend(f'Missing SUMO file: {path}' for path in self.inspection.missing_paths)
            warnings.extend(self.inspection.warnings)

        if problems:
            self.validation_label.setText('Validation blocked: fix the required items below before continuing.')
        elif warnings:
            self.validation_label.setText('Validation passed with warnings. You can continue, but review the warnings below.')
        else:
            self.validation_label.setText('Validation passed. The project can be created/imported.')

        if problems:
            lines.append('')
            lines.append('Blocking issues:')
            lines.extend(f'- {item}' for item in problems)
        if warnings:
            lines.append('')
            lines.append('Warnings:')
            lines.extend(f'- {item}' for item in warnings)

        self.summary_box.setPlainText('\n'.join(lines))

    def accept(self) -> None:
        payload = self.payload()
        if not payload['project_name']:
            QMessageBox.warning(self, 'Project Name Required', 'Enter a project name.')
            return
        if not payload['project_root']:
            QMessageBox.warning(self, 'Project Folder Required', 'Choose a project folder.')
            return
        if self.mode != 'new' or payload['attach_sumo_now']:
            if not payload['sumo_config_path']:
                QMessageBox.warning(self, 'SUMO Config Required', 'Choose a SUMO config file.')
                return
            if self.inspection is None or Path(payload['sumo_config_path']).resolve() != self.inspection.sumo_config_path:
                self.inspect_sumo_source()
                if self.inspection is None:
                    QMessageBox.warning(self, 'SUMO Inspection Failed', self.summary_box.toPlainText() or 'SUMO inspection failed. Review the summary and correct the input files.')
                    return
            if self.inspection.missing_paths:
                QMessageBox.warning(self, 'Missing SUMO Files', 'Resolve the missing SUMO files listed in the summary before continuing.')
                return
        super().accept()
