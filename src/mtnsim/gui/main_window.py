from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QDockWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QTextEdit,
    QToolBar,
    QWidget,
)

from mtnsim.gui.controllers import ProjectController
from mtnsim.gui.state import GuiSessionState
from mtnsim.gui.views import ProjectHomeView


class MainWindow(QMainWindow):
    def __init__(self, manifest_path: str | Path | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = ProjectController()
        self.session_state = GuiSessionState()
        self._build_ui()
        self._connect_signals()
        if manifest_path is not None:
            self.load_project(Path(manifest_path))

    def _build_ui(self) -> None:
        self.setWindowTitle('MTNsim GUI Prototype')
        self.resize(1360, 860)

        self._build_toolbar()
        self._build_navigation_dock()
        self._build_details_dock()
        self._build_log_dock()

        self.project_home_view = ProjectHomeView()
        self.setCentralWidget(self.project_home_view)
        self.statusBar().showMessage('Ready')

    def _build_toolbar(self) -> None:
        toolbar = QToolBar('Main Toolbar', self)
        toolbar.setMovable(False)
        open_action = toolbar.addAction('Open Project')
        open_action.triggered.connect(self.open_project_dialog)
        toolbar.addSeparator()
        home_action = toolbar.addAction('Project Home')
        home_action.triggered.connect(lambda: self.navigation_list.setCurrentRow(0))
        self.addToolBar(toolbar)

    def _build_navigation_dock(self) -> None:
        self.navigation_list = QListWidget()
        self.navigation_list.addItem(QListWidgetItem('Project Home'))
        self.navigation_list.addItem(QListWidgetItem('Scenario Browser'))
        self.navigation_list.addItem(QListWidgetItem('Run Monitor'))
        self.navigation_list.setCurrentRow(0)

        dock = QDockWidget('Navigation', self)
        dock.setObjectName('NavigationDock')
        dock.setAllowedAreas(Qt.LeftDockWidgetArea)
        dock.setWidget(self.navigation_list)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

    def _build_details_dock(self) -> None:
        self.details_panel = QTextEdit()
        self.details_panel.setReadOnly(True)
        self.details_panel.setPlaceholderText('Scenario details will appear here.')

        dock = QDockWidget('Scenario Details', self)
        dock.setObjectName('DetailsDock')
        dock.setAllowedAreas(Qt.RightDockWidgetArea)
        dock.setWidget(self.details_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

    def _build_log_dock(self) -> None:
        self.log_panel = QPlainTextEdit()
        self.log_panel.setReadOnly(True)
        self.log_panel.setPlaceholderText('Logs and status messages will appear here.')

        dock = QDockWidget('Status / Logs', self)
        dock.setObjectName('LogDock')
        dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        dock.setWidget(self.log_panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)

    def _connect_signals(self) -> None:
        self.project_home_view.open_project_requested.connect(self.open_project_dialog)
        self.project_home_view.scenario_selected.connect(self.select_scenario)

    def open_project_dialog(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Open MTNsim Project Manifest',
            str(Path.cwd()),
            'TOML Files (*.toml);;All Files (*)',
        )
        if file_path:
            self.load_project(Path(file_path))

    def load_project(self, manifest_path: Path) -> None:
        try:
            state = self.controller.load_project(manifest_path)
        except Exception as exc:  # pragma: no cover - UI feedback path
            QMessageBox.critical(self, 'Project Load Failed', str(exc))
            self._append_log(f'[error] Failed to load project: {exc}')
            return

        self.session_state.project_state = state
        self.project_home_view.set_project_state(state)
        self._append_log(f'[info] Loaded project manifest: {manifest_path}')
        if state.selected_scenario is not None:
            self._render_scenario_details(state.selected_scenario_path, state.selected_scenario)
        self.statusBar().showMessage(f'Loaded project: {state.project.project.name}')

    def select_scenario(self, scenario_path: str) -> None:
        try:
            loaded = self.controller.load_scenario(scenario_path)
        except Exception as exc:  # pragma: no cover - UI feedback path
            QMessageBox.critical(self, 'Scenario Load Failed', str(exc))
            self._append_log(f'[error] Failed to load scenario: {exc}')
            return

        self.session_state.project_state.selected_scenario_path = Path(scenario_path)
        self.session_state.project_state.selected_scenario = loaded
        self._render_scenario_details(Path(scenario_path), loaded)
        self._append_log(f'[info] Selected scenario: {loaded.scenario.name}')
        self.statusBar().showMessage(f'Selected scenario: {loaded.scenario.name}')

    def _render_scenario_details(self, scenario_path: Path | None, scenario) -> None:
        scene = scenario.scene
        lines = [
            f'Scenario: {scenario.scenario.name}',
            f'File: {scenario_path or "-"}',
            f'Description: {scenario.scenario.description or "-"}',
            '',
            f'Max vehicles: {scenario.traffic.max_vehicles}',
            f'Start speed (km/h): {scenario.traffic.start_speed_kmh}',
            f'Lane change mode: {scenario.controls.lane_change_mode}',
            f'Background noise (dB): {scenario.noise.background_noise_db}',
            '',
            f'Receivers: {len(scenario.receivers)}',
            f'Noise barriers: {len(scene.noise_barriers)}',
            f'Terrain edges: {len(scene.terrain_edges)}',
            f'Buildings: {len(scene.buildings)}',
            f'Ground surfaces: {len(scene.ground_surfaces)}',
            f'Vegetation zones: {len(scene.vegetation_zones)}',
        ]
        self.details_panel.setPlainText('\n'.join(lines))

    def _append_log(self, message: str) -> None:
        self.session_state.recent_log_lines.append(message)
        self.log_panel.appendPlainText(message)
