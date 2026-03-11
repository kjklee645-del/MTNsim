from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QDockWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QStackedWidget,
    QTextEdit,
    QToolBar,
    QWidget,
)

from mtnsim.gui.controllers import ProjectController, ResultController, RunController, SceneController
from mtnsim.gui.state import GuiRunState, GuiSessionState
from mtnsim.gui.views import ProjectHomeView, ResultViewerView, RunMonitorView, SceneView


class MainWindow(QMainWindow):
    def __init__(self, manifest_path: str | Path | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project_controller = ProjectController()
        self.run_controller = RunController()
        self.result_controller = ResultController()
        self.scene_controller = SceneController()
        self.session_state = GuiSessionState()
        self.run_thread: QThread | None = None
        self.run_worker = None
        self.current_result_summary = None
        self.current_result_summary_path: Path | None = None
        self._build_ui()
        self._connect_signals()
        if manifest_path is not None:
            self.load_project(Path(manifest_path))

    def _build_ui(self) -> None:
        self.setWindowTitle('MTNsim GUI Prototype')
        self.resize(1480, 920)

        self._build_toolbar()
        self._build_navigation_dock()
        self._build_details_dock()
        self._build_log_dock()

        self.project_home_view = ProjectHomeView()
        self.scene_view = SceneView()
        self.run_monitor_view = RunMonitorView()
        self.result_viewer_view = ResultViewerView()
        self.central_stack = QStackedWidget()
        self.central_stack.addWidget(self.project_home_view)
        self.central_stack.addWidget(self.scene_view)
        self.central_stack.addWidget(self.run_monitor_view)
        self.central_stack.addWidget(self.result_viewer_view)
        self.setCentralWidget(self.central_stack)
        self.statusBar().showMessage('Ready')

    def _build_toolbar(self) -> None:
        toolbar = QToolBar('Main Toolbar', self)
        toolbar.setMovable(False)
        self.open_project_action = toolbar.addAction('Open Project')
        self.open_project_action.triggered.connect(self.open_project_dialog)
        self.run_selected_action = toolbar.addAction('Run Selected')
        self.run_selected_action.triggered.connect(self.run_selected_scenario)
        self.run_selected_action.setEnabled(False)
        toolbar.addSeparator()
        self.home_action = toolbar.addAction('Project Home')
        self.home_action.triggered.connect(self.show_project_home)
        self.scene_view_action = toolbar.addAction('Scene View')
        self.scene_view_action.triggered.connect(self.show_scene_view)
        self.scene_view_action.setEnabled(False)
        self.run_monitor_action = toolbar.addAction('Run Monitor')
        self.run_monitor_action.triggered.connect(self.show_run_monitor)
        self.result_viewer_action = toolbar.addAction('Result Viewer')
        self.result_viewer_action.triggered.connect(self.show_result_viewer)
        self.result_viewer_action.setEnabled(False)
        self.addToolBar(toolbar)

    def _build_navigation_dock(self) -> None:
        self.navigation_list = QListWidget()
        self.navigation_list.addItem(QListWidgetItem('Project Home'))
        self.navigation_list.addItem(QListWidgetItem('Scene View'))
        self.navigation_list.addItem(QListWidgetItem('Run Monitor'))
        self.navigation_list.addItem(QListWidgetItem('Result Viewer'))
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
        self.project_home_view.run_selected_requested.connect(self.run_selected_scenario)
        self.run_monitor_view.back_requested.connect(self.show_project_home)
        self.result_viewer_view.recent_result_selected.connect(self.load_result_summary)
        self.result_viewer_view.receiver_selected.connect(self.load_receiver_series)
        self.navigation_list.currentRowChanged.connect(self._handle_navigation_change)

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
            state = self.project_controller.load_project(manifest_path)
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, 'Project Load Failed', str(exc))
            self._append_log(f'[error] Failed to load project: {exc}')
            return

        self.session_state.project_state = state
        self.project_home_view.set_project_state(state)
        run_enabled = state.selected_scenario_path is not None
        self.run_selected_action.setEnabled(run_enabled)
        self.scene_view_action.setEnabled(run_enabled)
        self.project_home_view.set_run_enabled(run_enabled)
        self._append_log(f'[info] Loaded project manifest: {manifest_path}')
        if state.selected_scenario is not None:
            self._render_scenario_details(state.selected_scenario_path, state.selected_scenario)
            self._update_scene_view()
        self.statusBar().showMessage(f'Loaded project: {state.project.project.name}')
        self.show_project_home()

    def select_scenario(self, scenario_path: str) -> None:
        try:
            loaded = self.project_controller.load_scenario(scenario_path)
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, 'Scenario Load Failed', str(exc))
            self._append_log(f'[error] Failed to load scenario: {exc}')
            return

        self.session_state.project_state.selected_scenario_path = Path(scenario_path)
        self.session_state.project_state.selected_scenario = loaded
        self._render_scenario_details(Path(scenario_path), loaded)
        self._update_scene_view()
        self.run_selected_action.setEnabled(True)
        self.scene_view_action.setEnabled(True)
        self.project_home_view.set_run_enabled(True)
        self._append_log(f'[info] Selected scenario: {loaded.scenario.name}')
        self.statusBar().showMessage(f'Selected scenario: {loaded.scenario.name}')

    def run_selected_scenario(self) -> None:
        project_state = self.session_state.project_state
        if project_state.manifest_path is None or project_state.selected_scenario_path is None:
            QMessageBox.information(self, 'Run Unavailable', 'Load a project and select a scenario first.')
            return
        if self.run_thread is not None and self.run_thread.isRunning():
            QMessageBox.information(self, 'Run In Progress', 'A simulation run is already in progress.')
            return

        self.session_state.run_state = GuiRunState(
            is_running=True,
            progress_percent=0,
            progress_label=f'Preparing run for {project_state.selected_scenario_path.stem}',
        )
        self.run_monitor_view.set_run_state(self.session_state.run_state)
        self.show_run_monitor()
        self._append_log(f'[info] Starting run for scenario: {project_state.selected_scenario_path.stem}')
        self.statusBar().showMessage('Running simulation...')
        self.run_selected_action.setEnabled(False)
        self.project_home_view.set_run_enabled(False)

        self.run_thread = QThread(self)
        self.run_worker = self.run_controller.create_worker(
            project_state.manifest_path,
            project_state.selected_scenario_path,
            use_gpu=True,
        )
        self.run_worker.moveToThread(self.run_thread)
        self.run_thread.started.connect(self.run_worker.run)
        self.run_worker.progress_changed.connect(self._on_run_progress)
        self.run_worker.completed.connect(self._on_run_completed)
        self.run_worker.failed.connect(self._on_run_failed)
        self.run_worker.completed.connect(self.run_thread.quit)
        self.run_worker.failed.connect(self.run_thread.quit)
        self.run_thread.finished.connect(self._cleanup_run_thread)
        self.run_thread.start()

    def load_result_summary(self, result_summary_path: str | Path) -> None:
        try:
            summary = self.result_controller.load_result_summary(result_summary_path)
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, 'Result Load Failed', str(exc))
            self._append_log(f'[error] Failed to load result summary: {exc}')
            return
        self.current_result_summary = summary
        self.current_result_summary_path = Path(result_summary_path)
        self.result_viewer_view.set_result_summary(summary)
        if summary.receiver_history_files:
            first_receiver = sorted(summary.receiver_history_files.keys())[0]
            self.result_viewer_view.receiver_selector.setCurrentText(first_receiver)
            self.load_receiver_series(first_receiver)
        self.result_viewer_action.setEnabled(True)
        self.show_result_viewer()
        self._append_log(f'[info] Loaded result summary: {result_summary_path}')

    def load_receiver_series(self, receiver_id: str) -> None:
        if self.current_result_summary is None:
            return
        csv_path = self.current_result_summary.receiver_history_files.get(receiver_id)
        if not csv_path:
            return
        series = self.result_controller.load_receiver_series(receiver_id, csv_path)
        self.result_viewer_view.set_receiver_series(series.receiver_id, series.points)

    def show_project_home(self) -> None:
        self.central_stack.setCurrentWidget(self.project_home_view)
        self.navigation_list.blockSignals(True)
        self.navigation_list.setCurrentRow(0)
        self.navigation_list.blockSignals(False)

    def show_scene_view(self) -> None:
        self.central_stack.setCurrentWidget(self.scene_view)
        self.navigation_list.blockSignals(True)
        self.navigation_list.setCurrentRow(1)
        self.navigation_list.blockSignals(False)

    def show_run_monitor(self) -> None:
        self.central_stack.setCurrentWidget(self.run_monitor_view)
        self.navigation_list.blockSignals(True)
        self.navigation_list.setCurrentRow(2)
        self.navigation_list.blockSignals(False)

    def show_result_viewer(self) -> None:
        self.central_stack.setCurrentWidget(self.result_viewer_view)
        self.navigation_list.blockSignals(True)
        self.navigation_list.setCurrentRow(3)
        self.navigation_list.blockSignals(False)

    def _handle_navigation_change(self, row: int) -> None:
        if row == 0:
            self.central_stack.setCurrentWidget(self.project_home_view)
        elif row == 1:
            self.central_stack.setCurrentWidget(self.scene_view)
        elif row == 2:
            self.central_stack.setCurrentWidget(self.run_monitor_view)
        elif row == 3:
            self.central_stack.setCurrentWidget(self.result_viewer_view)

    def _on_run_progress(self, percent: int, label: str) -> None:
        state = self.session_state.run_state
        state.progress_percent = percent
        state.progress_label = label
        self.run_monitor_view.set_run_state(state)
        self.statusBar().showMessage(label)
        self._append_log(f'[run] {label}')

    def _on_run_completed(self, payload: dict) -> None:
        state = self.session_state.run_state
        state.is_running = False
        state.progress_percent = 100
        state.progress_label = 'Simulation completed'
        state.run_id = payload.get('run_id')
        state.output_dir = Path(payload['output_dir']) if payload.get('output_dir') else None
        state.manifest_file = Path(payload['manifest_file']) if payload.get('manifest_file') else None
        state.result_summary_file = Path(payload['result_summary_file']) if payload.get('result_summary_file') else None
        state.final_grid_snapshot_file = Path(payload['final_grid_snapshot_file']) if payload.get('final_grid_snapshot_file') else None
        state.receiver_history_files = {
            key: Path(value)
            for key, value in payload.get('receiver_history_files', {}).items()
        }
        state.error_message = None
        self.run_monitor_view.set_run_state(state)

        if state.result_summary_file is not None:
            recent = [state.result_summary_file, *[path for path in self.session_state.recent_result_summaries if path != state.result_summary_file]]
            self.session_state.recent_result_summaries = recent[:8]
            self.result_viewer_view.set_recent_results(self.session_state.recent_result_summaries)
            self.load_result_summary(state.result_summary_file)

        self.run_selected_action.setEnabled(self.session_state.project_state.selected_scenario_path is not None)
        self.project_home_view.set_run_enabled(self.session_state.project_state.selected_scenario_path is not None)
        self._append_log(f"[info] Run completed: {state.run_id}")
        if state.result_summary_file:
            self._append_log(f"[info] Result summary: {state.result_summary_file}")
        self.statusBar().showMessage('Run completed')

    def _on_run_failed(self, error_message: str) -> None:
        state = self.session_state.run_state
        state.is_running = False
        state.progress_label = 'Simulation failed'
        state.error_message = error_message
        self.run_monitor_view.set_run_state(state)
        self.run_selected_action.setEnabled(self.session_state.project_state.selected_scenario_path is not None)
        self.project_home_view.set_run_enabled(self.session_state.project_state.selected_scenario_path is not None)
        self._append_log(f'[error] Simulation failed: {error_message}')
        self.statusBar().showMessage('Run failed')
        QMessageBox.critical(self, 'Run Failed', error_message)
        self.show_run_monitor()

    def _cleanup_run_thread(self) -> None:
        if self.run_worker is not None:
            self.run_worker.deleteLater()
        if self.run_thread is not None:
            self.run_thread.deleteLater()
        self.run_worker = None
        self.run_thread = None

    def _update_scene_view(self) -> None:
        project = self.session_state.project_state.project
        scenario = self.session_state.project_state.selected_scenario
        if project is None or scenario is None:
            self.scene_view.set_snapshot(None)
            return
        snapshot = self.scene_controller.build_snapshot(project, scenario)
        self.scene_view.set_snapshot(snapshot)

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
