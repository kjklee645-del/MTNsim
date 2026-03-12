from __future__ import annotations

from pathlib import Path
from io import BytesIO

import imageio.v2 as imageio
from PIL import Image
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt, QThread, QTimer
from PySide6.QtWidgets import QApplication
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

from mtnsim.gui.controllers import CompareController, PlaybackController, ProjectController, ResultController, RunController, SceneController
from mtnsim.gui.state import GuiRunState, GuiSessionState
from mtnsim.gui.views import ProjectHomeView, ResultViewerView, RunMonitorView, ScenarioComparisonView, SceneView, VehiclePlaybackView


class MainWindow(QMainWindow):
    def __init__(self, manifest_path: str | Path | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project_controller = ProjectController()
        self.compare_controller = CompareController()
        self.run_controller = RunController()
        self.result_controller = ResultController()
        self.scene_controller = SceneController()
        self.playback_controller = PlaybackController()
        self.session_state = GuiSessionState()
        self.run_thread: QThread | None = None
        self.run_worker = None
        self.compare_thread: QThread | None = None
        self.compare_worker = None
        self.current_compare_payload: dict | None = None
        self.current_compare_result_a = None
        self.current_compare_result_b = None
        self.current_result_summary = None
        self.current_result_summary_path: Path | None = None
        self.dynamic_heatmap_context = None
        self._playback_prefetch_timer = QTimer(self)
        self._playback_prefetch_timer.setSingleShot(True)
        self._playback_prefetch_timer.timeout.connect(self._run_playback_prefetch)
        self._pending_prefetch_frame_indices: list[int] = []
        self._build_ui()
        self._connect_signals()
        if manifest_path is not None:
            self.load_project(Path(manifest_path))

    def _build_ui(self) -> None:
        self.setWindowTitle('MTNsim GUI Prototype')
        self.resize(1520, 940)

        self._build_toolbar()
        self._build_navigation_dock()
        self._build_details_dock()
        self._build_log_dock()

        self.project_home_view = ProjectHomeView()
        self.scene_view = SceneView()
        self.scenario_comparison_view = ScenarioComparisonView()
        self.run_monitor_view = RunMonitorView()
        self.result_viewer_view = ResultViewerView()
        self.vehicle_playback_view = VehiclePlaybackView()
        self.central_stack = QStackedWidget()
        self.central_stack.addWidget(self.project_home_view)
        self.central_stack.addWidget(self.scene_view)
        self.central_stack.addWidget(self.scenario_comparison_view)
        self.central_stack.addWidget(self.run_monitor_view)
        self.central_stack.addWidget(self.result_viewer_view)
        self.central_stack.addWidget(self.vehicle_playback_view)
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
        self.compare_view_action = toolbar.addAction('Compare')
        self.compare_view_action.triggered.connect(self.show_scenario_comparison)
        self.compare_view_action.setEnabled(False)
        self.run_monitor_action = toolbar.addAction('Run Monitor')
        self.run_monitor_action.triggered.connect(self.show_run_monitor)
        self.result_viewer_action = toolbar.addAction('Result Viewer')
        self.result_viewer_action.triggered.connect(self.show_result_viewer)
        self.result_viewer_action.setEnabled(False)
        self.playback_action = toolbar.addAction('Vehicle Playback')
        self.playback_action.triggered.connect(self.show_vehicle_playback)
        self.playback_action.setEnabled(False)
        self.addToolBar(toolbar)

    def _build_navigation_dock(self) -> None:
        self.navigation_list = QListWidget()
        self.navigation_list.addItem(QListWidgetItem('Project Home'))
        self.navigation_list.addItem(QListWidgetItem('Scene View'))
        self.navigation_list.addItem(QListWidgetItem('Compare'))
        self.navigation_list.addItem(QListWidgetItem('Run Monitor'))
        self.navigation_list.addItem(QListWidgetItem('Result Viewer'))
        self.navigation_list.addItem(QListWidgetItem('Vehicle Playback'))
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
        self.scenario_comparison_view.compare_requested.connect(self.compare_selected_scenarios)
        self.scenario_comparison_view.run_compare_requested.connect(self.run_compare_selected_scenarios)
        self.scenario_comparison_view.receiver_selected.connect(self.load_comparison_receiver_series)
        self.run_monitor_view.back_requested.connect(self.show_project_home)
        self.result_viewer_view.recent_result_selected.connect(self.load_result_summary)
        self.result_viewer_view.receiver_selected.connect(self.load_receiver_series)
        self.vehicle_playback_view.playback_frame_changed.connect(self._sync_heatmap_to_playback_frame)
        self.vehicle_playback_view.contribution_view_changed.connect(self._refresh_playback_contribution_view)
        self.vehicle_playback_view.export_png_sequence_requested.connect(self.export_playback_png_sequence)
        self.vehicle_playback_view.export_gif_requested.connect(self.export_playback_gif)
        self.vehicle_playback_view.export_mp4_requested.connect(self.export_playback_mp4)
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
        self.compare_view_action.setEnabled(len(state.scenario_paths) >= 2)
        self.project_home_view.set_run_enabled(run_enabled)
        self.scenario_comparison_view.set_scenarios(state.scenario_paths, state.selected_scenario_path)
        self.scenario_comparison_view.set_comparison(None)
        self.scenario_comparison_view.set_run_comparison(None)
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
        self.compare_view_action.setEnabled(len(self.session_state.project_state.scenario_paths) >= 2)
        self.project_home_view.set_run_enabled(True)
        self.scenario_comparison_view.set_scenarios(self.session_state.project_state.scenario_paths, self.session_state.project_state.selected_scenario_path)
        self.scenario_comparison_view.set_run_comparison(None)
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
            record_vehicle_trace=True,
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
        self._prepare_dynamic_heatmap_context(summary)
        self._load_heatmap_from_result_summary(summary)
        self._load_playback_from_result_summary(summary)
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
        frame_index = self.vehicle_playback_view.slider.value() if self.vehicle_playback_view.dataset is not None else None
        self.result_viewer_view.set_playback_cursor(frame_index)

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

    def show_scenario_comparison(self) -> None:
        self.central_stack.setCurrentWidget(self.scenario_comparison_view)
        self.navigation_list.blockSignals(True)
        self.navigation_list.setCurrentRow(2)
        self.navigation_list.blockSignals(False)

    def show_run_monitor(self) -> None:
        self.central_stack.setCurrentWidget(self.run_monitor_view)
        self.navigation_list.blockSignals(True)
        self.navigation_list.setCurrentRow(3)
        self.navigation_list.blockSignals(False)

    def show_result_viewer(self) -> None:
        self.central_stack.setCurrentWidget(self.result_viewer_view)
        self.navigation_list.blockSignals(True)
        self.navigation_list.setCurrentRow(4)
        self.navigation_list.blockSignals(False)

    def show_vehicle_playback(self) -> None:
        self.central_stack.setCurrentWidget(self.vehicle_playback_view)
        self.navigation_list.blockSignals(True)
        self.navigation_list.setCurrentRow(5)
        self.navigation_list.blockSignals(False)

    def _handle_navigation_change(self, row: int) -> None:
        if row == 0:
            self.central_stack.setCurrentWidget(self.project_home_view)
        elif row == 1:
            self.central_stack.setCurrentWidget(self.scene_view)
        elif row == 2:
            self.central_stack.setCurrentWidget(self.scenario_comparison_view)
        elif row == 3:
            self.central_stack.setCurrentWidget(self.run_monitor_view)
        elif row == 4:
            self.central_stack.setCurrentWidget(self.result_viewer_view)
        elif row == 5:
            self.central_stack.setCurrentWidget(self.vehicle_playback_view)

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
        state.vehicle_trace_file = Path(payload['vehicle_trace_file']) if payload.get('vehicle_trace_file') else None
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
        if state.vehicle_trace_file:
            self._append_log(f"[info] Vehicle trace: {state.vehicle_trace_file}")
        self.statusBar().showMessage('Run completed')

    def _on_run_failed(self, error_message: str) -> None:
        state = self.session_state.run_state
        state.is_running = False
        state.progress_label = 'Simulation failed'
        state.error_message = error_message
        self.run_monitor_view.set_run_state(state)
        self.run_selected_action.setEnabled(self.session_state.project_state.selected_scenario_path is not None)
        self.project_home_view.set_run_enabled(self.session_state.project_state.selected_scenario_path is not None)
        self._append_log(f'[error] {error_message}')
        self.statusBar().showMessage('Run failed')
        QMessageBox.critical(self, 'Simulation Failed', error_message)

    def _cleanup_run_thread(self) -> None:
        if self.run_thread is not None:
            self.run_thread.deleteLater()
        if self.run_worker is not None:
            self.run_worker.deleteLater()
        self.run_thread = None
        self.run_worker = None

    def compare_selected_scenarios(self, scenario_path_a: str, scenario_path_b: str) -> None:
        if scenario_path_a == scenario_path_b:
            QMessageBox.information(self, 'Scenario Comparison', 'Select two different scenarios to compare.')
            return
        try:
            comparison = self.compare_controller.load_and_compare(self.project_controller, scenario_path_a, scenario_path_b)
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, 'Scenario Comparison Failed', str(exc))
            self._append_log(f'[error] Failed to compare scenarios: {exc}')
            return
        self.current_compare_payload = None
        self.current_compare_result_a = None
        self.current_compare_result_b = None
        self.scenario_comparison_view.set_comparison(comparison)
        self.scenario_comparison_view.set_status(f'Compared configs: {comparison.scenario_a} vs {comparison.scenario_b}')
        self.scenario_comparison_view.set_run_comparison(None)
        self._append_log(f'[info] Compared scenarios: {comparison.scenario_a} vs {comparison.scenario_b}')
        self.statusBar().showMessage(f'Compared scenarios: {comparison.scenario_a} vs {comparison.scenario_b}')
        self.show_scenario_comparison()

    def run_compare_selected_scenarios(self, scenario_path_a: str, scenario_path_b: str, use_gpu: bool) -> None:
        project_state = self.session_state.project_state
        if project_state.manifest_path is None:
            QMessageBox.information(self, 'Scenario Comparison', 'Load a project first.')
            return
        if scenario_path_a == scenario_path_b:
            QMessageBox.information(self, 'Scenario Comparison', 'Select two different scenarios to compare.')
            return
        if (self.run_thread is not None and self.run_thread.isRunning()) or (self.compare_thread is not None and self.compare_thread.isRunning()):
            QMessageBox.information(self, 'Comparison In Progress', 'Another simulation task is already running.')
            return

        self.scenario_comparison_view.set_status('Running scenario comparison...')
        self._append_log(f'[info] Starting run comparison: {Path(scenario_path_a).stem} vs {Path(scenario_path_b).stem}')
        self.statusBar().showMessage('Running scenario comparison...')

        self.compare_thread = QThread(self)
        self.compare_worker = self.run_controller.create_compare_worker(
            project_state.manifest_path,
            scenario_path_a,
            scenario_path_b,
            use_gpu=use_gpu,
        )
        self.compare_worker.moveToThread(self.compare_thread)
        self.compare_thread.started.connect(self.compare_worker.run)
        self.compare_worker.progress_changed.connect(self._on_compare_run_progress)
        self.compare_worker.completed.connect(self._on_compare_run_completed)
        self.compare_worker.failed.connect(self._on_compare_run_failed)
        self.compare_worker.completed.connect(self.compare_thread.quit)
        self.compare_worker.failed.connect(self.compare_thread.quit)
        self.compare_thread.finished.connect(self._cleanup_compare_thread)
        self.compare_thread.start()
        self.show_scenario_comparison()

    def _on_compare_run_progress(self, percent: int, label: str) -> None:
        self.scenario_comparison_view.set_status(f'Run comparison {percent}% | {label}')
        self.statusBar().showMessage(label)
        self._append_log(f'[compare] {label}')

    def _on_compare_run_completed(self, payload: dict) -> None:
        self.current_compare_payload = payload
        self.current_compare_result_a = self.result_controller.load_result_summary(payload['artifacts_a']['result_summary_file'])
        self.current_compare_result_b = self.result_controller.load_result_summary(payload['artifacts_b']['result_summary_file'])
        self.scenario_comparison_view.set_run_comparison(payload)
        self.scenario_comparison_view.set_status('Run comparison completed')
        if self.scenario_comparison_view.receiver_selector.count() > 0:
            self.load_comparison_receiver_series(self.scenario_comparison_view.receiver_selector.currentText())
        self._append_log('[info] Scenario run comparison completed')
        self.statusBar().showMessage('Scenario run comparison completed')
        self.show_scenario_comparison()

    def _on_compare_run_failed(self, error_message: str) -> None:
        self.scenario_comparison_view.set_status('Run comparison failed')
        self._append_log(f'[error] {error_message}')
        self.statusBar().showMessage('Scenario comparison failed')
        QMessageBox.critical(self, 'Scenario Comparison Failed', error_message)

    def _cleanup_compare_thread(self) -> None:
        if self.compare_thread is not None:
            self.compare_thread.deleteLater()
        if self.compare_worker is not None:
            self.compare_worker.deleteLater()
        self.compare_thread = None
        self.compare_worker = None

    def load_comparison_receiver_series(self, receiver_id: str) -> None:
        if not receiver_id or self.current_compare_result_a is None or self.current_compare_result_b is None or self.current_compare_payload is None:
            return
        csv_a = self.current_compare_result_a.receiver_history_files.get(receiver_id)
        csv_b = self.current_compare_result_b.receiver_history_files.get(receiver_id)
        if not csv_a or not csv_b:
            return
        series_a = self.result_controller.load_receiver_series(receiver_id, csv_a)
        series_b = self.result_controller.load_receiver_series(receiver_id, csv_b)
        self.scenario_comparison_view.set_receiver_overlay(
            receiver_id,
            series_a.points,
            series_b.points,
            self.current_compare_payload['comparison']['scenario_a'],
            self.current_compare_payload['comparison']['scenario_b'],
        )

    def _render_scenario_details(self, scenario_path: Path | None, scenario) -> None:
        receiver_lines = [f'- {receiver.id}: ({receiver.x:.1f}, {receiver.y:.1f}, {receiver.z:.1f})' for receiver in scenario.receivers]
        lines = [
            f'Scenario: {scenario.scenario.name}',
            f'Source file: {scenario_path}',
            '',
            'Traffic',
            f'- Max vehicles: {scenario.traffic.max_vehicles}',
            f'- Start speed (km/h): {scenario.traffic.start_speed_kmh}',
            f'- Vehicle interval (s): {scenario.traffic.vehicle_interval_seconds}',
            '',
            'Controls',
            f'- Lane change mode: {scenario.controls.lane_change_mode}',
            f'- Strategy: {scenario.controls.lane_change_strategy}',
            f'- Post target speed (km/h): {scenario.controls.post_target_speed_kmh}',
            '',
            'Receivers',
            *receiver_lines,
        ]
        self.details_panel.setPlainText('\n'.join(lines))

    def _update_scene_view(self) -> None:
        project_state = self.session_state.project_state
        if project_state.project is None or project_state.selected_scenario is None:
            self.scene_view.set_snapshot(None)
            self.vehicle_playback_view.set_snapshot(None)
            self.dynamic_heatmap_context = None
            self._pending_prefetch_frame_indices = []
            self._playback_prefetch_timer.stop()
            return
        snapshot = self.scene_controller.build_snapshot(project_state.project, project_state.selected_scenario)
        self.scene_view.set_snapshot(snapshot)
        self.vehicle_playback_view.set_snapshot(snapshot)
        if self.current_result_summary is not None:
            self._load_heatmap_from_result_summary(self.current_result_summary)
        self._append_log('[info] Updated scene view from selected scenario')


    def _prepare_dynamic_heatmap_context(self, summary) -> None:
        project_state = self.session_state.project_state
        if project_state.project is None:
            self.dynamic_heatmap_context = None
            return
        scenario = self._resolve_scenario_for_summary(summary)
        if scenario is None:
            self.dynamic_heatmap_context = None
            return
        self.dynamic_heatmap_context = self.result_controller.build_dynamic_heatmap_context(project_state.project, scenario, summary)

    def _resolve_scenario_for_summary(self, summary):
        project_state = self.session_state.project_state
        selected = project_state.selected_scenario
        if selected is not None and selected.scenario.name == summary.run.scenario:
            return selected
        for scenario_path in project_state.scenario_paths:
            try:
                candidate = self.project_controller.load_scenario(scenario_path)
            except Exception:
                continue
            if candidate.scenario.name == summary.run.scenario or scenario_path.stem == summary.run.scenario:
                project_state.selected_scenario_path = Path(scenario_path)
                project_state.selected_scenario = candidate
                self._render_scenario_details(Path(scenario_path), candidate)
                snapshot = self.scene_controller.build_snapshot(project_state.project, candidate)
                self.scene_view.set_snapshot(snapshot)
                self.vehicle_playback_view.set_snapshot(snapshot)
                return candidate
        return selected

    def _load_heatmap_from_result_summary(self, summary) -> None:
        cells = self.result_controller.load_heatmap_cells(getattr(summary, 'final_grid_snapshot_file', None))
        self.scene_view.canvas.set_heatmap_cells(cells)
        self.vehicle_playback_view.set_heatmap_cells(cells)
        if cells:
            self._append_log(f'[info] Loaded heatmap overlay with {len(cells)} cells')

    def _sync_heatmap_to_playback_frame(self, frame_index: int) -> None:
        dataset = self.vehicle_playback_view.dataset
        if dataset is None or self.dynamic_heatmap_context is None:
            return
        if frame_index < 0 or frame_index >= dataset.frame_count:
            return
        frame = dataset.frames[frame_index]
        selected_vehicle_id = self.vehicle_playback_view.selected_vehicle_id()
        contribution_only = self.vehicle_playback_view.is_selected_vehicle_contribution_only()

        if contribution_only and selected_vehicle_id:
            cells = self.result_controller.compute_vehicle_contribution_heatmap(self.dynamic_heatmap_context, frame, selected_vehicle_id)
        elif contribution_only:
            cells = []
        else:
            cells = self.result_controller.compute_dynamic_heatmap(self.dynamic_heatmap_context, frame)
            self._schedule_playback_prefetch(frame_index)

        self.scene_view.canvas.set_heatmap_cells(cells)
        self.vehicle_playback_view.set_heatmap_cells(cells)
        self.result_viewer_view.set_playback_cursor(frame.time_index)

        project_state = self.session_state.project_state
        receiver_positions = {}
        if project_state.selected_scenario is not None:
            receiver_positions = {
                receiver.id: (receiver.x, receiver.y, receiver.z)
                for receiver in project_state.selected_scenario.receivers
            }
        contributions = self.result_controller.compute_vehicle_receiver_contributions(
            self.dynamic_heatmap_context,
            frame,
            selected_vehicle_id,
            receiver_positions,
        )
        self.vehicle_playback_view.set_selected_vehicle_receiver_contributions(contributions)

    def _schedule_playback_prefetch(self, anchor_frame_index: int) -> None:
        dataset = self.vehicle_playback_view.dataset
        context = self.dynamic_heatmap_context
        if dataset is None or context is None or dataset.frame_count == 0:
            return
        candidate_indices: list[int] = []
        for offset in range(1, 7):
            candidate_indices.append(anchor_frame_index + offset)
        for offset in range(1, 3):
            candidate_indices.append(anchor_frame_index - offset)
        pending: list[int] = []
        seen: set[int] = set()
        for index in candidate_indices:
            if index < 0 or index >= dataset.frame_count or index in seen:
                continue
            seen.add(index)
            frame = dataset.frames[index]
            if frame.time_index in context.cache:
                context.cache.move_to_end(frame.time_index)
                continue
            pending.append(index)
        self._pending_prefetch_frame_indices = pending
        if pending:
            self._playback_prefetch_timer.start(1)

    def _run_playback_prefetch(self) -> None:
        dataset = self.vehicle_playback_view.dataset
        context = self.dynamic_heatmap_context
        if dataset is None or context is None or not self._pending_prefetch_frame_indices:
            return
        next_index = self._pending_prefetch_frame_indices.pop(0)
        if 0 <= next_index < dataset.frame_count:
            self.result_controller.prefetch_dynamic_heatmap_frames(context, [dataset.frames[next_index]], max_frames=1)
        if self._pending_prefetch_frame_indices:
            self._playback_prefetch_timer.start(1)

    def _refresh_playback_contribution_view(self) -> None:
        dataset = self.vehicle_playback_view.dataset
        if dataset is None or dataset.frame_count == 0:
            self.vehicle_playback_view.set_selected_vehicle_receiver_contributions({})
            return
        self._sync_heatmap_to_playback_frame(self.vehicle_playback_view.slider.value())

    def _load_playback_from_result_summary(self, summary) -> None:
        trace_file = getattr(summary, 'vehicle_trace_file', None)
        if not trace_file:
            self.vehicle_playback_view.set_dataset(None)
            self.vehicle_playback_view.set_selected_vehicle_receiver_contributions({})
            self.playback_action.setEnabled(False)
            return
        try:
            dataset = self.playback_controller.load_trace(trace_file)
        except Exception as exc:  # pragma: no cover
            self.playback_action.setEnabled(False)
            self.vehicle_playback_view.set_dataset(None)
            self._append_log(f'[error] Failed to load vehicle trace: {exc}')
            return
        self.vehicle_playback_view.set_dataset(dataset)
        self.playback_action.setEnabled(dataset.frame_count > 0)
        if dataset.frame_count > 0:
            self._sync_heatmap_to_playback_frame(self.vehicle_playback_view.slider.value())
        else:
            self.result_viewer_view.set_playback_cursor(None)
        self._append_log(f'[info] Loaded vehicle playback trace: {trace_file}')

    def export_playback_png_sequence(self) -> None:
        dataset = self.vehicle_playback_view.dataset
        if dataset is None or dataset.frame_count == 0:
            QMessageBox.information(self, 'Playback Export', 'Load a playback result before exporting frames.')
            return

        default_root = dataset.trace_file.parent / 'playback_png_sequence'
        output_dir = QFileDialog.getExistingDirectory(
            self,
            'Select Playback PNG Export Folder',
            str(default_root),
        )
        if not output_dir:
            return

        output_path = self._export_playback_png_sequence_to(Path(output_dir))
        QMessageBox.information(self, 'Playback Export Complete', 'PNG sequence saved to:\n' + str(output_path))

    def export_playback_gif(self) -> None:
        dataset = self.vehicle_playback_view.dataset
        if dataset is None or dataset.frame_count == 0:
            QMessageBox.information(self, 'Playback Export', 'Load a playback result before exporting a GIF.')
            return

        default_path = dataset.trace_file.parent / 'playback.gif'
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            'Save Playback GIF',
            str(default_path),
            'GIF Files (*.gif)',
        )
        if not file_path:
            return

        output_path = self._export_playback_gif_to(Path(file_path))
        QMessageBox.information(self, 'Playback Export Complete', 'Animated GIF saved to:\n' + str(output_path))

    def export_playback_mp4(self) -> None:
        dataset = self.vehicle_playback_view.dataset
        if dataset is None or dataset.frame_count == 0:
            QMessageBox.information(self, 'Playback Export', 'Load a playback result before exporting an MP4.')
            return

        default_path = dataset.trace_file.parent / 'playback.mp4'
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            'Save Playback MP4',
            str(default_path),
            'MP4 Files (*.mp4)',
        )
        if not file_path:
            return

        output_path = self._export_playback_mp4_to(Path(file_path))
        QMessageBox.information(self, 'Playback Export Complete', 'MP4 video saved to:\n' + str(output_path))

    def _export_playback_png_sequence_to(self, output_path: Path) -> Path:
        dataset = self.vehicle_playback_view.dataset
        if dataset is None or dataset.frame_count == 0:
            raise RuntimeError('Playback dataset is not loaded.')

        output_path.mkdir(parents=True, exist_ok=True)
        was_playing = self.vehicle_playback_view._timer.isActive()
        if was_playing:
            self.vehicle_playback_view.toggle_playback()
        original_frame = self.vehicle_playback_view.slider.value()

        self.statusBar().showMessage('Exporting playback PNG sequence...')
        self._append_log(f'[info] Exporting playback PNG sequence to {output_path}')

        try:
            for frame_index in range(dataset.frame_count):
                self.vehicle_playback_view.set_frame_index(frame_index)
                QApplication.processEvents()
                image = self.vehicle_playback_view.canvas.grab().toImage()
                frame = dataset.frames[frame_index]
                filename = output_path / f'frame_{frame_index:04d}_t{frame.time_index:04d}.png'
                image.save(str(filename), 'PNG')
                if frame_index == 0 or (frame_index + 1) % 50 == 0 or frame_index == dataset.frame_count - 1:
                    self.statusBar().showMessage(f'Exporting playback PNG sequence... {frame_index + 1}/{dataset.frame_count}')
                    self._append_log(f'[export] Saved frame {frame_index + 1}/{dataset.frame_count}')
        finally:
            self.vehicle_playback_view.set_frame_index(original_frame)
            QApplication.processEvents()
            if was_playing:
                self.vehicle_playback_view.toggle_playback()

        self._append_log(f'[info] Playback PNG export completed: {output_path}')
        self.statusBar().showMessage(f'Playback PNG export completed: {output_path}')
        return output_path

    def _export_playback_gif_to(self, output_path: Path) -> Path:
        dataset = self.vehicle_playback_view.dataset
        if dataset is None or dataset.frame_count == 0:
            raise RuntimeError('Playback dataset is not loaded.')

        output_path.parent.mkdir(parents=True, exist_ok=True)
        was_playing = self.vehicle_playback_view._timer.isActive()
        if was_playing:
            self.vehicle_playback_view.toggle_playback()
        original_frame = self.vehicle_playback_view.slider.value()
        gif_frames: list[Image.Image] = []

        self.statusBar().showMessage('Exporting playback GIF...')
        self._append_log(f'[info] Exporting playback GIF to {output_path}')

        try:
            for frame_index in range(dataset.frame_count):
                self.vehicle_playback_view.set_frame_index(frame_index)
                QApplication.processEvents()
                qimage = self.vehicle_playback_view.canvas.grab().toImage()
                gif_frames.append(self._qimage_to_pil(qimage))
                if frame_index == 0 or (frame_index + 1) % 50 == 0 or frame_index == dataset.frame_count - 1:
                    self.statusBar().showMessage(f'Exporting playback GIF... {frame_index + 1}/{dataset.frame_count}')
                    self._append_log(f'[export] Prepared GIF frame {frame_index + 1}/{dataset.frame_count}')
        finally:
            self.vehicle_playback_view.set_frame_index(original_frame)
            QApplication.processEvents()
            if was_playing:
                self.vehicle_playback_view.toggle_playback()

        if not gif_frames:
            raise RuntimeError('No GIF frames were captured.')

        frame_duration_ms = self._playback_frame_duration_ms(dataset)
        gif_frames[0].save(
            output_path,
            save_all=True,
            append_images=gif_frames[1:],
            duration=frame_duration_ms,
            loop=0,
            optimize=False,
            disposal=2,
        )
        self._append_log(f'[info] Playback GIF export completed: {output_path}')
        self.statusBar().showMessage(f'Playback GIF export completed: {output_path}')
        return output_path

    def _export_playback_mp4_to(self, output_path: Path) -> Path:
        dataset = self.vehicle_playback_view.dataset
        if dataset is None or dataset.frame_count == 0:
            raise RuntimeError('Playback dataset is not loaded.')

        output_path.parent.mkdir(parents=True, exist_ok=True)
        was_playing = self.vehicle_playback_view._timer.isActive()
        if was_playing:
            self.vehicle_playback_view.toggle_playback()
        original_frame = self.vehicle_playback_view.slider.value()
        fps = self._playback_fps(dataset)

        self.statusBar().showMessage('Exporting playback MP4...')
        self._append_log(f'[info] Exporting playback MP4 to {output_path}')

        writer = imageio.get_writer(str(output_path), fps=fps, codec='libx264', format='FFMPEG', quality=7, pixelformat='yuv420p')
        try:
            for frame_index in range(dataset.frame_count):
                self.vehicle_playback_view.set_frame_index(frame_index)
                QApplication.processEvents()
                qimage = self.vehicle_playback_view.canvas.grab().toImage()
                pil_image = self._qimage_to_pil(qimage).convert('RGB')
                writer.append_data(self._pil_to_ndarray_rgb(pil_image))
                if frame_index == 0 or (frame_index + 1) % 50 == 0 or frame_index == dataset.frame_count - 1:
                    self.statusBar().showMessage(f'Exporting playback MP4... {frame_index + 1}/{dataset.frame_count}')
                    self._append_log(f'[export] Prepared MP4 frame {frame_index + 1}/{dataset.frame_count}')
        finally:
            writer.close()
            self.vehicle_playback_view.set_frame_index(original_frame)
            QApplication.processEvents()
            if was_playing:
                self.vehicle_playback_view.toggle_playback()

        self._append_log(f'[info] Playback MP4 export completed: {output_path}')
        self.statusBar().showMessage(f'Playback MP4 export completed: {output_path}')
        return output_path

    def _qimage_to_pil(self, qimage) -> Image.Image:
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        qimage.save(buffer, 'PNG')
        buffer.close()
        return Image.open(BytesIO(bytes(byte_array))).convert('RGBA')

    def _pil_to_ndarray_rgb(self, image: Image.Image):
        import numpy as np
        return np.asarray(image, dtype=np.uint8)

    def _playback_fps(self, dataset) -> int:
        duration_ms = self._playback_frame_duration_ms(dataset)
        return max(1, int(round(1000.0 / max(1, duration_ms))))

    def _playback_frame_duration_ms(self, dataset) -> int:
        if dataset.frame_count <= 1:
            return 120
        deltas = []
        for index in range(1, min(dataset.frame_count, 20)):
            delta = dataset.frames[index].sim_time_seconds - dataset.frames[index - 1].sim_time_seconds
            if delta > 0:
                deltas.append(delta)
        if not deltas:
            return 120
        return max(40, int(round((sum(deltas) / len(deltas)) * 1000.0)))

    def _append_log(self, line: str) -> None:
        self.session_state.recent_log_lines.append(line)
        self.session_state.recent_log_lines = self.session_state.recent_log_lines[-200:]
        self.log_panel.setPlainText('\n'.join(self.session_state.recent_log_lines))
        self.log_panel.verticalScrollBar().setValue(self.log_panel.verticalScrollBar().maximum())
