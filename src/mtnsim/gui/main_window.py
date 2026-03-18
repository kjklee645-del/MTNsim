from __future__ import annotations

from pathlib import Path
from copy import deepcopy
from io import BytesIO
import json
import os

import imageio.v2 as imageio
from PIL import Image
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt, QThread, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import (
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QDialog,
    QDockWidget,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from mtnsim.gui.controllers import CampaignController, CompareController, PlaybackController, ProjectController, ResultController, RunController, Scene3DController, SceneController
from mtnsim.gui.state import GuiRunState, GuiSessionState
from mtnsim.gui.views import CampaignValidationView, ProjectHomeView, ProjectSetupDialog, ResultViewerView, RunMonitorView, ScenarioComparisonView, ScenarioEditorView, Scene3DView, SceneObjectEditorView, SceneView, VehiclePlaybackView
from mtnsim.schemas.scenario import Building, GroundSurface, NoiseBarrier, Receiver, TerrainEdge, VegetationZone


class MainWindow(QMainWindow):
    def __init__(self, manifest_path: str | Path | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project_controller = ProjectController()
        self.campaign_controller = CampaignController()
        self.compare_controller = CompareController()
        self.run_controller = RunController()
        self.result_controller = ResultController()
        self.scene_controller = SceneController()
        self.scene3d_controller = Scene3DController()
        self.playback_controller = PlaybackController()
        self.session_state = GuiSessionState()
        self.run_thread: QThread | None = None
        self.run_worker = None
        self.compare_thread: QThread | None = None
        self.compare_worker = None
        self.campaign_thread: QThread | None = None
        self.campaign_worker = None
        self.current_config_comparison = None
        self.current_compare_payload: dict | None = None
        self.current_compare_result_a = None
        self.current_compare_result_b = None
        self.current_result_summary = None
        self.current_result_summary_path: Path | None = None
        self.dynamic_heatmap_context = None
        self.preview_scenario = None
        self.selected_scene_object_key: tuple[str, str] | None = None
        self._playback_prefetch_timer = QTimer(self)
        self._playback_prefetch_timer.setSingleShot(True)
        self._playback_prefetch_timer.timeout.connect(self._run_playback_prefetch)
        self._pending_prefetch_frame_indices: list[int] = []
        self._build_ui()
        self._connect_signals()
        if manifest_path is not None:
            self.load_project(Path(manifest_path))

    def _build_ui(self) -> None:
        self.setWindowTitle('MTNsim - Urban Corridor Analysis')
        self.setObjectName('MainWorkbenchWindow')
        self.resize(1520, 940)

        self._build_toolbar()
        self._build_navigation_dock()
        self._build_details_dock()
        self._build_log_dock()

        self.project_home_view = ProjectHomeView()
        self.scene_view = SceneView()
        self.scenario_editor_view = ScenarioEditorView()
        self.scene_object_editor_view = SceneObjectEditorView()
        self.scene_3d_view = Scene3DView()
        self.scenario_comparison_view = ScenarioComparisonView()
        self.campaign_validation_view = CampaignValidationView()
        self.run_monitor_view = RunMonitorView()
        self.result_viewer_view = ResultViewerView()
        self.vehicle_playback_view = VehiclePlaybackView()
        self.central_stack = QStackedWidget()
        self.central_stack.setObjectName('CentralWorkspace')
        self.central_stack.addWidget(self.project_home_view)
        self.central_stack.addWidget(self.scene_view)
        self.central_stack.addWidget(self.scenario_editor_view)
        self.central_stack.addWidget(self.scene_object_editor_view)
        self.central_stack.addWidget(self.scene_3d_view)
        self.central_stack.addWidget(self.scenario_comparison_view)
        self.central_stack.addWidget(self.campaign_validation_view)
        self.central_stack.addWidget(self.run_monitor_view)
        self.central_stack.addWidget(self.result_viewer_view)
        self.central_stack.addWidget(self.vehicle_playback_view)
        self._build_central_workspace_shell()
        self.statusBar().setObjectName('AppStatusBar')
        self.statusBar().showMessage('Ready')

    def _build_toolbar(self) -> None:
        toolbar = QToolBar('Main Toolbar', self)
        toolbar.setObjectName('MainToolbar')
        toolbar.setMovable(False)

        self.open_project_action = QAction('Open Project', self)
        self.open_project_action.triggered.connect(self.open_project_dialog)
        self.new_project_action = QAction('New Project', self)
        self.new_project_action.triggered.connect(self.open_new_project_dialog)
        self.import_project_action = QAction('Import SUMO Project', self)
        self.import_project_action.triggered.connect(self.open_import_project_dialog)
        self.attach_sumo_action = QAction('Attach SUMO', self)
        self.attach_sumo_action.triggered.connect(self.open_attach_sumo_dialog)
        self.attach_sumo_action.setEnabled(False)

        self.run_selected_action = QAction('Run Selected', self)
        self.run_selected_action.triggered.connect(self.run_selected_scenario)
        self.run_selected_action.setEnabled(False)
        self.run_monitor_action = QAction('Run Monitor', self)
        self.run_monitor_action.triggered.connect(self.show_run_monitor)

        self.home_action = QAction('Project Home', self)
        self.home_action.triggered.connect(self.show_project_home)
        self.scene_view_action = QAction('Scene View', self)
        self.scene_view_action.triggered.connect(self.show_scene_view)
        self.scene_view_action.setEnabled(False)
        self.scenario_editor_action = QAction('Scenario Editor', self)
        self.scenario_editor_action.triggered.connect(self.show_scenario_editor)
        self.scenario_editor_action.setEnabled(False)
        self.scene_object_editor_action = QAction('Scene Objects', self)
        self.scene_object_editor_action.triggered.connect(self.show_scene_object_editor)
        self.scene_object_editor_action.setEnabled(False)
        self.scene_3d_view_action = QAction('3D View', self)
        self.scene_3d_view_action.triggered.connect(self.show_scene_3d_view)
        self.scene_3d_view_action.setEnabled(False)

        self.compare_view_action = QAction('Compare', self)
        self.compare_view_action.triggered.connect(self.show_scenario_comparison)
        self.compare_view_action.setEnabled(False)
        self.result_viewer_action = QAction('Result Viewer', self)
        self.result_viewer_action.triggered.connect(self.show_result_viewer)
        self.result_viewer_action.setEnabled(False)
        self.playback_action = QAction('Vehicle Playback', self)
        self.playback_action.triggered.connect(self.show_vehicle_playback)
        self.playback_action.setEnabled(False)

        self.campaign_view_action = QAction('Campaign Validation', self)
        self.campaign_view_action.triggered.connect(self.show_campaign_validation)
        self.campaign_view_action.setEnabled(False)
        self.open_campaign_action = QAction('Open Campaign Manifest', self)
        self.open_campaign_action.triggered.connect(self.open_campaign_dialog)

        self.open_quickstart_action = QAction('Open Quickstart', self)
        self.open_quickstart_action.triggered.connect(self.open_quickstart_guide)
        self.open_user_guide_action = QAction('Open User Guide', self)
        self.open_user_guide_action.triggered.connect(self.open_user_guide)
        self.about_action = QAction('About MTNsim', self)
        self.about_action.triggered.connect(self.show_about_dialog)

        self._add_toolbar_menu_button(toolbar, 'Project', [
            self.home_action,
            None,
            self.open_project_action,
            self.new_project_action,
            self.import_project_action,
            self.attach_sumo_action,
            None,
            self.scene_view_action,
            self.scenario_editor_action,
            self.scene_object_editor_action,
        ])
        self._add_toolbar_menu_button(toolbar, 'Run', [
            self.run_selected_action,
            self.run_monitor_action,
        ])
        self._add_toolbar_menu_button(toolbar, 'Results', [
            self.result_viewer_action,
            self.playback_action,
            self.compare_view_action,
        ])
        self._add_toolbar_menu_button(toolbar, 'Validation', [
            self.campaign_view_action,
            self.open_campaign_action,
        ])
        self._add_toolbar_menu_button(toolbar, 'Help', [
            self.open_quickstart_action,
            self.open_user_guide_action,
            None,
            self.about_action,
        ])

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        quick_run_button = QToolButton(self)
        quick_run_button.setObjectName('QuickRunButton')
        quick_run_button.setDefaultAction(self.run_selected_action)
        quick_run_button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        toolbar.addWidget(quick_run_button)
        self.addToolBar(toolbar)

    def _add_toolbar_menu_button(self, toolbar: QToolBar, label: str, entries: list[QAction | None]) -> None:
        menu = QMenu(self)
        for entry in entries:
            if entry is None:
                menu.addSeparator()
            else:
                menu.addAction(entry)
        button = QToolButton(self)
        button.setText(label)
        button.setPopupMode(QToolButton.InstantPopup)
        button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        button.setMenu(menu)
        button.setObjectName(f'{label.replace(' ', '')}MenuButton')
        toolbar.addWidget(button)

    def _build_navigation_dock(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        title = QLabel('Tools & Config')
        title.setObjectName('panelTitle')
        layout.addWidget(title)

        project_label = self._build_shell_section_label('PROJECT')
        layout.addWidget(project_label)

        project_grid = QGridLayout()
        project_grid.setHorizontalSpacing(8)
        project_grid.setVerticalSpacing(8)
        project_grid.addWidget(self._build_action_tile('New', self.new_project_action), 0, 0)
        project_grid.addWidget(self._build_action_tile('Open', self.open_project_action), 0, 1)
        project_grid.addWidget(self._build_action_tile('Import', self.import_project_action), 0, 2)
        project_grid.addWidget(self._build_action_tile('Attach', self.attach_sumo_action), 1, 0)
        project_grid.addWidget(self._build_action_tile('Run', self.run_selected_action), 1, 1)
        project_grid.addWidget(self._build_action_tile('Monitor', self.run_monitor_action), 1, 2)
        layout.addLayout(project_grid)

        edit_label = self._build_shell_section_label('MAP EDITOR')
        layout.addWidget(edit_label)

        edit_grid = QGridLayout()
        edit_grid.setHorizontalSpacing(8)
        edit_grid.setVerticalSpacing(8)
        edit_grid.addWidget(self._build_action_tile('Scene', self.scene_view_action), 0, 0)
        edit_grid.addWidget(self._build_action_tile('Objects', self.scene_object_editor_action), 0, 1)
        edit_grid.addWidget(self._build_action_tile('Scenario', self.scenario_editor_action), 0, 2)
        edit_grid.addWidget(self._build_action_tile('Compare', self.compare_view_action), 1, 0)
        edit_grid.addWidget(self._build_action_tile('Results', self.result_viewer_action), 1, 1)
        edit_grid.addWidget(self._build_action_tile('Playback', self.playback_action), 1, 2)
        edit_grid.addWidget(self._build_action_tile('3D View', self.scene_3d_view_action), 2, 0)
        layout.addLayout(edit_grid)

        validation_label = self._build_shell_section_label('VALIDATION')
        layout.addWidget(validation_label)
        validation_row = QHBoxLayout()
        validation_row.setSpacing(8)
        validation_row.addWidget(self._build_action_tile('Campaign', self.campaign_view_action))
        validation_row.addWidget(self._build_action_tile('Manifest', self.open_campaign_action))
        validation_row.addStretch(1)
        layout.addLayout(validation_row)

        workspace_label = self._build_shell_section_label('WORKSPACE')
        layout.addWidget(workspace_label)

        self.navigation_list = QListWidget()
        self.navigation_list.setObjectName('WorkspaceList')
        self.navigation_list.addItem(QListWidgetItem('Home'))
        self.navigation_list.addItem(QListWidgetItem('Scene'))
        self.navigation_list.addItem(QListWidgetItem('Scene Objects'))
        self.navigation_list.addItem(QListWidgetItem('Editor'))
        self.navigation_list.addItem(QListWidgetItem('Compare'))
        self.navigation_list.addItem(QListWidgetItem('Validation'))
        self.navigation_list.addItem(QListWidgetItem('Run Monitor'))
        self.navigation_list.addItem(QListWidgetItem('Results'))
        self.navigation_list.addItem(QListWidgetItem('Playback'))
        self.navigation_list.addItem(QListWidgetItem('3D View'))
        self.navigation_list.setCurrentRow(0)
        layout.addWidget(self.navigation_list, 1)

        dock = QDockWidget('Tools & Config', self)
        dock.setObjectName('NavigationDock')
        dock.setAllowedAreas(Qt.LeftDockWidgetArea)
        dock.setWidget(panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

    def _build_details_dock(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        title = QLabel('Analysis & Data')
        title.setObjectName('panelTitle')
        layout.addWidget(title)

        self.analysis_status_label = QLabel('Status: idle')
        self.analysis_status_label.setObjectName('statusBadgeNeutral')
        layout.addWidget(self.analysis_status_label)

        summary_card = QFrame()
        summary_card.setObjectName('infoCard')
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(12, 12, 12, 12)
        summary_layout.setSpacing(6)
        summary_title = QLabel('LIVE ANALYTICS')
        summary_title.setObjectName('sectionTitle')
        summary_layout.addWidget(summary_title)
        self.analysis_project_label = QLabel('Project: -')
        self.analysis_scenario_label = QLabel('Scenario: -')
        self.analysis_run_label = QLabel('Last run: -')
        self.analysis_mode_label = QLabel('Execution: -')
        for widget in [self.analysis_project_label, self.analysis_scenario_label, self.analysis_run_label, self.analysis_mode_label]:
            widget.setWordWrap(True)
            summary_layout.addWidget(widget)
        layout.addWidget(summary_card)

        details_title = QLabel('SCENARIO DETAILS')
        details_title.setObjectName('sectionTitle')
        layout.addWidget(details_title)

        self.details_panel = QTextEdit()
        self.details_panel.setObjectName('infoCard')
        self.details_panel.setReadOnly(True)
        self.details_panel.setPlaceholderText('Scenario details will appear here.')
        layout.addWidget(self.details_panel, 1)

        dock = QDockWidget('Analysis & Data', self)
        dock.setObjectName('DetailsDock')
        dock.setAllowedAreas(Qt.RightDockWidgetArea)
        dock.setWidget(panel)
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


    def _build_central_workspace_shell(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header_card = QFrame()
        header_card.setObjectName('viewerHeaderCard')
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(10)

        title = QLabel('Integrated Viewer')
        title.setObjectName('pageTitle')
        header_layout.addWidget(title)

        tabs_row = QHBoxLayout()
        tabs_row.setSpacing(8)
        self.center_view_buttons = {}
        center_specs = [
            ('Scene', self.show_scene_view, 'scene'),
            ('Objects', self.show_scene_object_editor, 'objects'),
            ('Scenario', self.show_scenario_editor, 'editor'),
            ('Noise Map', self.show_result_viewer, 'results'),
            ('Vehicle Path', self.show_vehicle_playback, 'playback'),
            ('Compare', self.show_scenario_comparison, 'compare'),
            ('Validation', self.show_campaign_validation, 'validation'),
            ('3D View', self.show_scene_3d_view, '3d'),
        ]
        for label, handler, key in center_specs:
            button = QPushButton(label)
            button.setObjectName('viewerTabButton')
            button.setCheckable(True)
            button.clicked.connect(handler)
            tabs_row.addWidget(button)
            self.center_view_buttons[key] = button
        tabs_row.addStretch(1)
        header_layout.addLayout(tabs_row)

        layout.addWidget(header_card)
        layout.addWidget(self.central_stack, 1)
        self.setCentralWidget(container)

    def _build_action_tile(self, label: str, action: QAction) -> QToolButton:
        button = QToolButton(self)
        button.setObjectName('ActionTile')
        button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        button.setText(label)
        return button

    def _build_shell_section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName('shellSectionLabel')
        return label

    def _set_active_center_button(self, key: str | None) -> None:
        for name, button in getattr(self, 'center_view_buttons', {}).items():
            button.blockSignals(True)
            button.setChecked(name == key)
            button.blockSignals(False)

    def _sync_shell_controls(self) -> None:
        if hasattr(self, 'center_view_buttons'):
            if 'scene' in self.center_view_buttons:
                self.center_view_buttons['scene'].setEnabled(self.scene_view_action.isEnabled())
            if 'objects' in self.center_view_buttons:
                self.center_view_buttons['objects'].setEnabled(self.scene_object_editor_action.isEnabled())
            if 'editor' in self.center_view_buttons:
                self.center_view_buttons['editor'].setEnabled(self.scenario_editor_action.isEnabled())
            if 'results' in self.center_view_buttons:
                self.center_view_buttons['results'].setEnabled(self.result_viewer_action.isEnabled())
            if 'playback' in self.center_view_buttons:
                self.center_view_buttons['playback'].setEnabled(self.playback_action.isEnabled())
            if 'compare' in self.center_view_buttons:
                self.center_view_buttons['compare'].setEnabled(self.compare_view_action.isEnabled())
            if 'validation' in self.center_view_buttons:
                self.center_view_buttons['validation'].setEnabled(self.campaign_view_action.isEnabled())
            if '3d' in self.center_view_buttons:
                self.center_view_buttons['3d'].setEnabled(self.scene_3d_view_action.isEnabled())

    def _refresh_analysis_panel(self) -> None:
        project_state = self.session_state.project_state
        run_state = self.session_state.run_state
        project_name = project_state.project.project.name if project_state.project is not None else '-'
        scenario_name = project_state.selected_scenario.scenario.name if project_state.selected_scenario is not None else '-'
        if run_state.run_id:
            run_label = f'Last run: {run_state.run_id[:8]}'
        else:
            run_label = 'Last run: -'
        if run_state.is_running:
            status_text = f'Status: running ({run_state.progress_percent}%)'
            status_object = 'statusBadgeWarning'
        elif run_state.error_message:
            status_text = 'Status: run failed'
            status_object = 'statusBadgeWarning'
        elif self.current_result_summary is not None:
            status_text = 'Status: result loaded'
            status_object = 'statusBadgeReady'
        elif project_state.project is not None:
            status_text = 'Status: project loaded'
            status_object = 'statusBadgeNeutral'
        else:
            status_text = 'Status: idle'
            status_object = 'statusBadgeNeutral'
        execution = '-'
        if run_state.requested_use_gpu is not None:
            execution = 'GPU requested' if run_state.requested_use_gpu else 'CPU requested'
        if run_state.used_gpu is not None:
            execution = 'GPU used' if run_state.used_gpu else 'CPU used'

        self.analysis_status_label.setText(status_text)
        self.analysis_status_label.setObjectName(status_object)
        self.analysis_status_label.style().unpolish(self.analysis_status_label)
        self.analysis_status_label.style().polish(self.analysis_status_label)
        self.analysis_project_label.setText(f'Project: {project_name}')
        self.analysis_scenario_label.setText(f'Scenario: {scenario_name}')
        self.analysis_run_label.setText(run_label)
        self.analysis_mode_label.setText(f'Execution: {execution}')

    def _connect_signals(self) -> None:
        self.project_home_view.open_project_requested.connect(self.open_project_dialog)
        self.project_home_view.new_project_requested.connect(self.open_new_project_dialog)
        self.project_home_view.import_project_requested.connect(self.open_import_project_dialog)
        self.project_home_view.attach_sumo_requested.connect(self.open_attach_sumo_dialog)
        self.project_home_view.scene_requested.connect(self.show_scene_view)
        self.project_home_view.scenario_selected.connect(self.select_scenario)
        self.project_home_view.run_selected_requested.connect(self.run_selected_scenario)
        self.project_home_view.edit_selected_requested.connect(self.show_scenario_editor)
        self.project_home_view.recent_result_selected.connect(self._sync_home_recent_result_selection)
        self.project_home_view.open_recent_result_requested.connect(self.open_recent_result_from_home)
        self.project_home_view.open_latest_output_requested.connect(self.open_latest_output_from_home)
        self.scenario_editor_view.save_as_requested.connect(self.save_scenario_variant)
        self.scenario_editor_view.preview_requested.connect(self.apply_scenario_preview)
        self.scenario_editor_view.grid_region_draw_requested.connect(self.start_grid_region_draw_mode)
        self.scene_object_editor_view.save_as_requested.connect(self.save_scene_object_variant)
        self.scene_object_editor_view.preview_requested.connect(self.apply_scene_object_preview)
        self.scene_object_editor_view.object_selected.connect(self.handle_scene_object_editor_selection)
        self.scene_object_editor_view.draw_mode_requested.connect(self.start_scene_object_draw_mode)
        self.scene_object_editor_view.finish_draw_requested.connect(self.finish_scene_object_draw_mode)
        self.scene_object_editor_view.cancel_draw_requested.connect(self.cancel_scene_object_draw_mode)
        self.scene_view.canvas.scene_object_selected.connect(self.handle_scene_view_object_selection)
        self.scene_view.canvas.scene_object_drawn.connect(self.handle_scene_object_drawn)
        self.scene_view.canvas.scene_object_geometry_edited.connect(self.handle_scene_object_geometry_edited)
        self.vehicle_playback_view.canvas.scene_object_selected.connect(self.handle_scene_view_object_selection)
        self.scenario_comparison_view.compare_requested.connect(self.compare_selected_scenarios)
        self.scenario_comparison_view.run_compare_requested.connect(self.run_compare_selected_scenarios)
        self.scenario_comparison_view.receiver_selected.connect(self.load_comparison_receiver_series)
        self.scenario_comparison_view.open_run_a_requested.connect(self.open_compare_run_a_summary)
        self.scenario_comparison_view.open_run_b_requested.connect(self.open_compare_run_b_summary)
        self.scenario_comparison_view.export_json_requested.connect(self.export_scenario_comparison_json)
        self.scenario_comparison_view.export_markdown_requested.connect(self.export_scenario_comparison_markdown)
        self.campaign_validation_view.open_campaign_requested.connect(self.open_campaign_dialog)
        self.campaign_validation_view.inspect_requested.connect(self.inspect_campaign)
        self.campaign_validation_view.validate_requested.connect(self.validate_campaign)
        self.campaign_validation_view.open_output_dir_requested.connect(self.open_campaign_output_dir)
        self.campaign_validation_view.open_summary_requested.connect(self.open_campaign_summary_file)
        self.campaign_validation_view.open_report_requested.connect(self.open_campaign_report_file)
        self.campaign_validation_view.open_result_summary_requested.connect(self.open_campaign_result_summary_file)
        self.campaign_validation_view.open_calibration_summary_requested.connect(self.open_campaign_calibration_summary_file)
        self.run_monitor_view.back_requested.connect(self.show_project_home)
        self.run_monitor_view.open_result_requested.connect(self.show_result_viewer)
        self.result_viewer_view.recent_result_selected.connect(self.load_result_summary)
        self.result_viewer_view.receiver_selected.connect(self.load_receiver_series)
        self.result_viewer_view.open_output_dir_requested.connect(self.open_current_result_output_dir)
        self.result_viewer_view.open_result_summary_requested.connect(self.open_current_result_summary_file)
        self.result_viewer_view.open_manifest_requested.connect(self.open_current_run_manifest_file)
        self.result_viewer_view.open_3d_view_requested.connect(self.open_current_result_in_3d_view)
        self.result_viewer_view.export_markdown_requested.connect(self.export_current_result_markdown)
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

    def open_new_project_dialog(self) -> None:
        self._open_project_setup_dialog(mode='new')

    def open_import_project_dialog(self) -> None:
        self._open_project_setup_dialog(mode='import')

    def open_attach_sumo_dialog(self) -> None:
        project_state = self.session_state.project_state
        if project_state.manifest_path is None or project_state.project is None:
            QMessageBox.information(self, 'Attach SUMO', 'Load or create a project first.')
            return
        selected_name = project_state.selected_scenario_path.stem if project_state.selected_scenario_path is not None else project_state.project.project.default_scenario
        self._open_project_setup_dialog(
            mode='attach',
            initial_project_root=str(self.project_controller._project_root(project_state.manifest_path)),
            initial_project_name=project_state.project.project.name,
            initial_description=project_state.project.project.description,
            initial_scenario_name=selected_name,
        )

    def _open_project_setup_dialog(
        self,
        *,
        mode: str,
        initial_project_root: str = '',
        initial_project_name: str = '',
        initial_description: str = '',
        initial_scenario_name: str = 'baseline',
    ) -> None:
        dialog = ProjectSetupDialog(
            self.project_controller,
            mode=mode,
            initial_project_root=initial_project_root,
            initial_project_name=initial_project_name,
            initial_description=initial_description,
            initial_scenario_name=initial_scenario_name,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        payload = dialog.payload()
        project_root = Path(payload['project_root']).resolve()
        manifest_path = project_root / 'project.toml'
        scenario_path = project_root / 'scenarios' / f"{payload['default_scenario']}.toml"
        overwrite_existing = bool(payload.get('overwrite_existing'))
        conflicts = [path for path in [manifest_path, scenario_path] if path.exists()] if mode != 'attach' else []
        if conflicts and not overwrite_existing:
            paths = '\n'.join(str(path) for path in conflicts)
            answer = QMessageBox.question(
                self,
                'Overwrite Existing Project Files?',
                'The following files already exist:\n\n'
                f'{paths}\n\n'
                'Do you want to overwrite them and continue?',
            )
            if answer != QMessageBox.Yes:
                self._append_log('[info] Project creation/import cancelled because existing files were not overwritten.')
                return
            overwrite_existing = True
        try:
            if mode == 'new' and not payload.get('attach_sumo_now', True):
                result = self.project_controller.create_empty_project(
                    project_root=payload['project_root'],
                    project_name=payload['project_name'],
                    description=payload['description'],
                    default_scenario=payload['default_scenario'],
                    overwrite_existing=overwrite_existing,
                    scene_path=payload['scene_path'] or None,
                    measurements_path=payload['measurements_path'] or None,
                    measurement_metadata_path=payload['measurement_metadata_path'] or None,
                    copy_external_files=payload['copy_sumo_files'],
                )
            elif mode == 'attach':
                current_state = self.session_state.project_state
                target_scenario_path = current_state.selected_scenario_path
                result = self.project_controller.attach_sumo_to_project(
                    manifest_path=current_state.manifest_path,
                    sumo_config_path=payload['sumo_config_path'],
                    copy_sumo_files=payload['copy_sumo_files'],
                    overwrite_existing=overwrite_existing,
                    scenario_path=target_scenario_path,
                    refresh_selected_scenario_only=payload['attach_refresh_selected_only'],
                    update_traffic_metadata=payload['attach_update_traffic_metadata'],
                    update_vehicle_coefficients=payload['attach_update_vehicle_coefficients'],
                    replace_placeholder_receivers=payload['attach_replace_placeholder_receivers'],
                    update_lane_change_targets=payload['attach_update_lane_targets'],
                    scene_path=payload['scene_path'] or None,
                    measurements_path=payload['measurements_path'] or None,
                    measurement_metadata_path=payload['measurement_metadata_path'] or None,
                )
            else:
                result = self.project_controller.create_project_from_sumo(
                    project_root=payload['project_root'],
                    project_name=payload['project_name'],
                    description=payload['description'],
                    sumo_config_path=payload['sumo_config_path'],
                    default_scenario=payload['default_scenario'],
                    copy_sumo_files=payload['copy_sumo_files'],
                    overwrite_existing=overwrite_existing,
                    scene_path=payload['scene_path'] or None,
                    measurements_path=payload['measurements_path'] or None,
                    measurement_metadata_path=payload['measurement_metadata_path'] or None,
                )
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, 'Project Creation Failed', str(exc))
            self._append_log(f'[error] Failed to create/import project: {exc}')
            return
        if mode == 'attach':
            self._append_log(f'[info] Updated project manifest with attached SUMO assets: {result.manifest_path}')
            self._append_log(f'[info] Refreshed target scenario for SUMO attachment: {result.scenario_path}')
        else:
            self._append_log(f'[info] Created project manifest: {result.manifest_path}')
            self._append_log(f'[info] Created starter scenario: {result.scenario_path}')
        if result.inspection is not None and result.inspection.warnings:
            for warning in result.inspection.warnings:
                self._append_log(f'[warn] {warning}')
        self.statusBar().showMessage(f'Project ready: {result.manifest_path.parent.name}')
        self.load_project(result.manifest_path)
        self._show_project_creation_guidance(result, mode=mode)


    def _show_project_creation_guidance(self, result, *, mode: str) -> None:
        note_lines = [
            f'Project manifest: {result.manifest_path}',
            f'Target scenario: {result.scenario_path.name}',
        ]
        if mode == 'attach':
            note_lines.extend([
                'SUMO is now attached to this project.',
                'Next recommended steps:',
                '- Review the refreshed starter scenario in Scenario Editor.',
                '- Inspect the imported network in Scene View.',
                '- Run the scenario to confirm the project is now runnable.',
            ])
        elif result.inspection is None:
            note_lines.extend([
                'This project was created as an empty MTNsim shell.',
                'Next recommended steps:',
                '- Use Scenario Editor to shape the starter scenario.',
                '- Attach SUMO later when the network files are ready.',
                '- Scene View stays available, but Run remains disabled until SUMO is attached.',
            ])
        else:
            note_lines.extend([
                'Next recommended steps:',
                '- Review starter receivers in Scenario Editor.',
                '- Inspect the imported network in Scene View.',
                '- Run the starter baseline once before deeper edits.',
            ])
        if result.inspection is not None and result.inspection.warnings:
            note_lines.append('')
            note_lines.append('Import warnings:')
            note_lines.extend(f'- {warning}' for warning in result.inspection.warnings[:5])
        QMessageBox.information(self, 'Project Ready', '\n'.join(note_lines))

    def _project_has_runnable_sumo(self, project) -> bool:
        if project is None:
            return False
        network_raw = (project.paths.network or '').strip()
        sumo_raw = (project.paths.sumo_config or '').strip()
        if not network_raw or not sumo_raw:
            return False
        return self._resolve_project_path(project, network_raw).exists() and self._resolve_project_path(project, sumo_raw).exists()

    def _resolve_project_path(self, project, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        if project.source_path is None:
            return Path.cwd() / path
        source_parent = project.source_path.parent
        project_root = source_parent.parent if source_parent.name == 'examples' else source_parent
        return project_root / path

    def _build_project_readiness(self) -> tuple[str, str, str]:
        project_state = self.session_state.project_state
        if project_state.project is None or project_state.manifest_path is None:
            return (
                'Status: no project loaded',
                '#9a3412',
                'Readiness: load, create, or import a project to start editing and running scenarios.',
            )
        issues: list[str] = []
        next_actions: list[str] = []
        if project_state.selected_scenario_path is None:
            issues.append('No scenario is selected.')
            next_actions.append('Choose a scenario from Project Home.')
        if not self._project_has_runnable_sumo(project_state.project):
            issues.append('SUMO network/config is not attached or cannot be resolved.')
            next_actions.append('Use Attach SUMO to Project before running.')
        if project_state.selected_scenario is not None and not project_state.selected_scenario.receivers:
            issues.append('The selected scenario has no receivers.')
            next_actions.append('Add receivers in Scenario Editor before running.')
        if not issues:
            return (
                'Status: ready to run',
                '#166534',
                'Readiness: this project has a selected scenario, valid SUMO paths, and can be run now.',
            )
        return (
            'Status: setup still needed',
            '#9a3412',
            'Readiness: ' + ' '.join(issues + next_actions),
        )

    def _refresh_project_home_readiness(self) -> None:
        status_title, status_color, summary = self._build_project_readiness()
        self.project_home_view.set_project_readiness(
            status_title=status_title,
            status_color=status_color,
            summary=summary,
        )

    def _update_run_enablement(self) -> None:
        project_state = self.session_state.project_state
        run_enabled = (
            project_state.selected_scenario_path is not None
            and project_state.project is not None
            and self._project_has_runnable_sumo(project_state.project)
        )
        self.run_selected_action.setEnabled(run_enabled)
        self.project_home_view.set_run_enabled(run_enabled)
        self._refresh_project_home_readiness()
        self._sync_shell_controls()
        self._refresh_analysis_panel()

    def load_project(self, manifest_path: Path) -> None:
        try:
            state = self.project_controller.load_project(manifest_path)
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, 'Project Load Failed', str(exc))
            self._append_log(f'[error] Failed to load project: {exc}')
            return

        self.preview_scenario = None
        self.current_config_comparison = None
        self.current_compare_payload = None
        self.session_state.project_state = state
        self.project_home_view.set_project_state(state)
        self.project_home_view.set_recent_results(self.session_state.recent_result_summaries)
        self.project_home_view.set_last_run(self.session_state.run_state)
        self.attach_sumo_action.setEnabled(state.manifest_path is not None)
        run_enabled = state.selected_scenario_path is not None
        self.scene_view_action.setEnabled(run_enabled)
        self.scenario_editor_action.setEnabled(run_enabled)
        self.scene_3d_view_action.setEnabled(run_enabled)
        self.compare_view_action.setEnabled(len(state.scenario_paths) >= 2)
        self.campaign_view_action.setEnabled(state.manifest_path is not None)
        self._update_run_enablement()
        self.scenario_comparison_view.set_scenarios(state.scenario_paths, state.selected_scenario_path)
        self.scenario_comparison_view.set_comparison(None)
        self.scenario_comparison_view.set_run_comparison(None)
        self._append_log(f'[info] Loaded project manifest: {manifest_path}')
        if state.selected_scenario is not None:
            self._render_scenario_details(state.selected_scenario_path, state.selected_scenario)
            self.scenario_editor_view.set_scenario(state.selected_scenario_path, state.selected_scenario)
            self.scene_object_editor_view.set_scenario(state.selected_scenario_path, state.selected_scenario)
            self._update_scene_view()
        self.statusBar().showMessage(f'Loaded project: {state.project.project.name}')
        self._sync_shell_controls()
        self._refresh_analysis_panel()
        self.show_project_home()

    def select_scenario(self, scenario_path: str) -> None:
        try:
            loaded = self.project_controller.load_scenario(scenario_path)
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, 'Scenario Load Failed', str(exc))
            self._append_log(f'[error] Failed to load scenario: {exc}')
            return

        self.preview_scenario = None
        self.current_config_comparison = None
        self.current_compare_payload = None
        self.project_home_view.set_recent_results(self.session_state.recent_result_summaries)
        self.project_home_view.set_last_run(self.session_state.run_state)
        self.session_state.project_state.selected_scenario_path = Path(scenario_path)
        self.session_state.project_state.selected_scenario = loaded
        self._render_scenario_details(Path(scenario_path), loaded)
        self.scenario_editor_view.set_scenario(Path(scenario_path), loaded)
        self.scene_object_editor_view.set_scenario(Path(scenario_path), loaded)
        self._update_scene_view()
        self.scene_view_action.setEnabled(True)
        self.scenario_editor_action.setEnabled(True)
        self.scene_object_editor_action.setEnabled(True)
        self.scene_3d_view_action.setEnabled(True)
        self.compare_view_action.setEnabled(len(self.session_state.project_state.scenario_paths) >= 2)
        self.campaign_view_action.setEnabled(self.session_state.project_state.manifest_path is not None)
        self._update_run_enablement()
        self.scenario_comparison_view.set_scenarios(self.session_state.project_state.scenario_paths, self.session_state.project_state.selected_scenario_path)
        self.scenario_comparison_view.set_run_comparison(None)
        self._append_log(f'[info] Selected scenario: {loaded.scenario.name}')
        self.statusBar().showMessage(f'Selected scenario: {loaded.scenario.name}')
        self._sync_shell_controls()
        self._refresh_analysis_panel()

    def run_selected_scenario(self) -> None:
        project_state = self.session_state.project_state
        if project_state.manifest_path is None or project_state.selected_scenario_path is None:
            QMessageBox.information(self, 'Run Unavailable', 'Load a project and select a scenario first.')
            return
        if project_state.project is None or not self._project_has_runnable_sumo(project_state.project):
            QMessageBox.information(self, 'Run Unavailable', 'Attach a valid SUMO config and network before running this project.')
            return
        if self.run_thread is not None and self.run_thread.isRunning():
            QMessageBox.information(self, 'Run In Progress', 'A simulation run is already in progress.')
            return

        readiness_summary = self._build_project_readiness()[2]
        self.session_state.run_state = GuiRunState(
            is_running=True,
            progress_percent=0,
            progress_label=f'Preparing run for {project_state.selected_scenario_path.stem}',
            project_name=project_state.project.project.name if project_state.project is not None else None,
            scenario_name=project_state.selected_scenario_path.stem,
            requested_use_gpu=True,
            readiness_summary=readiness_summary,
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
        self.result_viewer_view.set_result_summary_source(result_summary_path)
        self.result_viewer_view.set_result_summary(summary)
        self.scene_3d_view.set_result_context(summary, result_summary_path)
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
        self._refresh_analysis_panel()

    def open_current_result_in_3d_view(self) -> None:
        if self.current_result_summary is None:
            QMessageBox.information(self, '3D View', 'Load a result summary before opening the 3D view.')
            return
        self.show_scene_3d_view()

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

    def _sync_home_recent_result_selection(self, result_summary_path: str) -> None:
        self.statusBar().showMessage(f'Recent result selected: {Path(result_summary_path).parent.name}')

    def open_recent_result_from_home(self, result_summary_path: str) -> None:
        self.load_result_summary(result_summary_path)
        self.show_result_viewer()

    def open_latest_output_from_home(self) -> None:
        state = self.session_state.run_state
        self._open_path(state.output_dir, label='latest output folder')

    def show_project_home(self) -> None:
        self.central_stack.setCurrentWidget(self.project_home_view)
        self.navigation_list.blockSignals(True)
        self.navigation_list.setCurrentRow(0)
        self.navigation_list.blockSignals(False)
        self._set_active_center_button(None)

    def show_scene_view(self) -> None:
        self.central_stack.setCurrentWidget(self.scene_view)
        self.navigation_list.blockSignals(True)
        self.navigation_list.setCurrentRow(1)
        self.navigation_list.blockSignals(False)
        self._set_active_center_button('scene')

    def show_scenario_editor(self) -> None:
        self.central_stack.setCurrentWidget(self.scenario_editor_view)
        self.navigation_list.blockSignals(True)
        self.navigation_list.setCurrentRow(3)
        self.navigation_list.blockSignals(False)
        self._set_active_center_button('editor')

    def show_scene_object_editor(self) -> None:
        self.central_stack.setCurrentWidget(self.scene_object_editor_view)
        self.navigation_list.blockSignals(True)
        self.navigation_list.setCurrentRow(2)
        self.navigation_list.blockSignals(False)
        self._set_active_center_button('objects')

    def show_scene_3d_view(self) -> None:
        self.central_stack.setCurrentWidget(self.scene_3d_view)
        self.navigation_list.blockSignals(True)
        self.navigation_list.setCurrentRow(9)
        self.navigation_list.blockSignals(False)
        self._set_active_center_button('3d')

    def show_scenario_comparison(self) -> None:
        self.central_stack.setCurrentWidget(self.scenario_comparison_view)
        self.navigation_list.blockSignals(True)
        self.navigation_list.setCurrentRow(4)
        self.navigation_list.blockSignals(False)
        self._set_active_center_button('compare')

    def show_campaign_validation(self) -> None:
        self.central_stack.setCurrentWidget(self.campaign_validation_view)
        self.navigation_list.blockSignals(True)
        self.navigation_list.setCurrentRow(5)
        self.navigation_list.blockSignals(False)
        self._set_active_center_button('validation')

    def show_run_monitor(self) -> None:
        self.central_stack.setCurrentWidget(self.run_monitor_view)
        self.navigation_list.blockSignals(True)
        self.navigation_list.setCurrentRow(6)
        self.navigation_list.blockSignals(False)
        self._set_active_center_button(None)

    def show_result_viewer(self) -> None:
        self.central_stack.setCurrentWidget(self.result_viewer_view)
        self.navigation_list.blockSignals(True)
        self.navigation_list.setCurrentRow(7)
        self.navigation_list.blockSignals(False)
        self._set_active_center_button('results')

    def show_vehicle_playback(self) -> None:
        self.central_stack.setCurrentWidget(self.vehicle_playback_view)
        self.navigation_list.blockSignals(True)
        self.navigation_list.setCurrentRow(8)
        self.navigation_list.blockSignals(False)
        self._set_active_center_button('playback')

    def _handle_navigation_change(self, row: int) -> None:
        if row == 0:
            self.central_stack.setCurrentWidget(self.project_home_view)
            self._set_active_center_button(None)
        elif row == 1:
            self.central_stack.setCurrentWidget(self.scene_view)
            self._set_active_center_button('scene')
        elif row == 2:
            self.central_stack.setCurrentWidget(self.scene_object_editor_view)
            self._set_active_center_button('objects')
        elif row == 3:
            self.central_stack.setCurrentWidget(self.scenario_editor_view)
            self._set_active_center_button('editor')
        elif row == 4:
            self.central_stack.setCurrentWidget(self.scenario_comparison_view)
            self._set_active_center_button('compare')
        elif row == 5:
            self.central_stack.setCurrentWidget(self.campaign_validation_view)
            self._set_active_center_button('validation')
        elif row == 6:
            self.central_stack.setCurrentWidget(self.run_monitor_view)
            self._set_active_center_button(None)
        elif row == 7:
            self.central_stack.setCurrentWidget(self.result_viewer_view)
            self._set_active_center_button('results')
        elif row == 8:
            self.central_stack.setCurrentWidget(self.vehicle_playback_view)
            self._set_active_center_button('playback')
        elif row == 9:
            self.central_stack.setCurrentWidget(self.scene_3d_view)
            self._set_active_center_button('3d')

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
        state.receiver_count = len(state.receiver_history_files)
        state.used_gpu = None
        self.run_monitor_view.set_run_state(state)

        if state.result_summary_file is not None:
            recent = [state.result_summary_file, *[path for path in self.session_state.recent_result_summaries if path != state.result_summary_file]]
            self.session_state.recent_result_summaries = recent[:8]
            self.result_viewer_view.set_recent_results(self.session_state.recent_result_summaries)
            self.project_home_view.set_recent_results(self.session_state.recent_result_summaries)
            self.load_result_summary(state.result_summary_file)
            if self.current_result_summary is not None:
                state.used_gpu = self.current_result_summary.used_gpu
                state.receiver_count = len(self.current_result_summary.receiver_stats)
                state.readiness_summary = (
                    f"Run finished for {self.current_result_summary.run.scenario}. "
                    f"Used {'GPU' if self.current_result_summary.used_gpu else 'CPU'} and produced {len(self.current_result_summary.receiver_stats)} receiver summaries."
                )
                self.run_monitor_view.set_run_state(state)

        self._update_run_enablement()
        self.project_home_view.set_last_run(state)
        self._append_log(f"[info] Run completed: {state.run_id}")
        if state.result_summary_file:
            self._append_log(f"[info] Result summary: {state.result_summary_file}")
        if state.vehicle_trace_file:
            self._append_log(f"[info] Vehicle trace: {state.vehicle_trace_file}")
        self.statusBar().showMessage('Run completed')
        self._refresh_analysis_panel()

    def _on_run_failed(self, error_message: str) -> None:
        state = self.session_state.run_state
        state.is_running = False
        state.progress_label = 'Simulation failed'
        state.error_message = error_message
        state.readiness_summary = 'Run failed before a valid result summary could be produced.'
        self.run_monitor_view.set_run_state(state)
        self._update_run_enablement()
        self._append_log(f'[error] {error_message}')
        self.statusBar().showMessage('Run failed')
        self._refresh_analysis_panel()
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
        self.current_config_comparison = comparison
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

    def open_campaign_dialog(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Open Campaign Manifest',
            str(Path.cwd()),
            'JSON Files (*.json);;All Files (*)',
        )
        if file_path:
            self.load_campaign(Path(file_path))

    def load_campaign(self, campaign_path: Path) -> None:
        try:
            manifest = self.campaign_controller.load_campaign_manifest(campaign_path)
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, 'Campaign Load Failed', str(exc))
            self._append_log(f'[error] Failed to load campaign: {exc}')
            return
        scenario_paths = self.session_state.project_state.scenario_paths if self.session_state.project_state.project is not None else []
        self.campaign_validation_view.set_campaign(campaign_path, manifest, scenario_paths)
        self.campaign_validation_view.set_status('Campaign loaded. Inspect or validate when ready.')
        self._append_log(f'[info] Loaded campaign: {campaign_path}')
        self.show_campaign_validation()

    def inspect_campaign(self, campaign_file: str) -> None:
        if self.campaign_thread is not None and self.campaign_thread.isRunning():
            QMessageBox.information(self, 'Campaign Task In Progress', 'Another campaign task is already running.')
            return
        self.campaign_validation_view.set_status('Inspecting campaign...')
        self.statusBar().showMessage('Inspecting campaign...')
        self.campaign_thread = QThread(self)
        self.campaign_worker = self.campaign_controller.create_inspect_worker(campaign_file)
        self.campaign_worker.moveToThread(self.campaign_thread)
        self.campaign_thread.started.connect(self.campaign_worker.run)
        self.campaign_worker.completed.connect(self._on_campaign_inspection_completed)
        self.campaign_worker.failed.connect(self._on_campaign_task_failed)
        self.campaign_worker.completed.connect(self.campaign_thread.quit)
        self.campaign_worker.failed.connect(self.campaign_thread.quit)
        self.campaign_thread.finished.connect(self._cleanup_campaign_thread)
        self.campaign_thread.start()

    def validate_campaign(self, campaign_file: str, scenario_override_path: str, use_gpu: bool) -> None:
        project_state = self.session_state.project_state
        if project_state.manifest_path is None:
            QMessageBox.information(self, 'Campaign Validation', 'Load a project first.')
            return
        if self.campaign_thread is not None and self.campaign_thread.isRunning():
            QMessageBox.information(self, 'Campaign Task In Progress', 'Another campaign task is already running.')
            return
        scenario_override = scenario_override_path or None
        self.campaign_validation_view.set_status('Validating campaign...')
        self.statusBar().showMessage('Validating campaign...')
        self.campaign_thread = QThread(self)
        self.campaign_worker = self.campaign_controller.create_validate_worker(
            project_state.manifest_path,
            campaign_file,
            scenario_override_path=scenario_override,
            use_gpu=use_gpu,
        )
        self.campaign_worker.moveToThread(self.campaign_thread)
        self.campaign_thread.started.connect(self.campaign_worker.run)
        self.campaign_worker.completed.connect(self._on_campaign_validation_completed)
        self.campaign_worker.failed.connect(self._on_campaign_task_failed)
        self.campaign_worker.completed.connect(self.campaign_thread.quit)
        self.campaign_worker.failed.connect(self.campaign_thread.quit)
        self.campaign_thread.finished.connect(self._cleanup_campaign_thread)
        self.campaign_thread.start()

    def _on_campaign_inspection_completed(self, payload: dict) -> None:
        self.campaign_validation_view.set_inspection_result(payload)
        self.campaign_validation_view.set_status('Campaign inspection completed')
        self._append_log(f"[info] Campaign inspection completed: {payload.get('summary_file')}")
        self.statusBar().showMessage('Campaign inspection completed')
        self.show_campaign_validation()

    def _on_campaign_validation_completed(self, payload: dict) -> None:
        self.campaign_validation_view.set_validation_result(payload)
        self.campaign_validation_view.set_status('Campaign validation completed')
        self._append_log(f"[info] Campaign validation completed: {payload.get('summary_file')}")
        self.statusBar().showMessage('Campaign validation completed')
        self.show_campaign_validation()

    def _on_campaign_task_failed(self, error_message: str) -> None:
        self.campaign_validation_view.set_status('Campaign task failed')
        self._append_log(f'[error] {error_message}')
        self.statusBar().showMessage('Campaign task failed')
        QMessageBox.critical(self, 'Campaign Task Failed', error_message)

    def _cleanup_campaign_thread(self) -> None:
        if self.campaign_thread is not None:
            self.campaign_thread.deleteLater()
        if self.campaign_worker is not None:
            self.campaign_worker.deleteLater()
        self.campaign_thread = None
        self.campaign_worker = None

    def apply_scenario_preview(self, payload: dict) -> None:
        project_state = self.session_state.project_state
        if project_state.project is None or project_state.selected_scenario is None:
            return
        preview = deepcopy(project_state.selected_scenario)
        preview.scenario.name = payload.get('scenario_name') or preview.scenario.name
        preview.scenario.description = payload.get('description', preview.scenario.description)
        preview.traffic.max_vehicles = int(payload['traffic.max_vehicles'])
        preview.traffic.start_speed_kmh = float(payload['traffic.start_speed_kmh'])
        preview.traffic.vehicle_interval_seconds = float(payload['traffic.vehicle_interval_seconds'])
        preview.controls.post_distance_meters = float(payload['controls.post_distance_meters'])
        preview.controls.post_target_speed_kmh = float(payload['controls.post_target_speed_kmh'])
        preview.controls.lane_change_mode = str(payload['controls.lane_change_mode'])
        preview.controls.lane_change_strategy = str(payload['controls.lane_change_strategy'])
        preview.controls.post_distance_speed_control = bool(payload['controls.post_distance_speed_control'])
        preview.controls.lane_change_force_change = bool(payload['controls.lane_change_force_change'])
        preview.noise.background_noise_db = float(payload['noise.background_noise_db'])
        preview.noise.max_area_meters = float(payload['noise.max_area_meters'])
        preview.noise.grid_size_meters = float(payload['noise.grid_size_meters'])
        preview.noise.receiver_height_meters = float(payload['noise.receiver_height_meters'])
        preview.grid.margin_x_start = float(payload['grid.margin_x_start'])
        preview.grid.margin_x_end = float(payload['grid.margin_x_end'])
        preview.grid.extra_y_extent = float(payload['grid.extra_y_extent'])
        preview.grid.override_enabled = bool(payload.get('grid.override_enabled', False))
        preview.grid.override_min_x = float(payload['grid.override_min_x']) if payload.get('grid.override_enabled', False) else None
        preview.grid.override_max_x = float(payload['grid.override_max_x']) if payload.get('grid.override_enabled', False) else None
        preview.grid.override_min_y = float(payload['grid.override_min_y']) if payload.get('grid.override_enabled', False) else None
        preview.grid.override_max_y = float(payload['grid.override_max_y']) if payload.get('grid.override_enabled', False) else None
        preview.receivers = [
            Receiver(
                id=str(receiver['id']),
                x=float(receiver['x']),
                y=float(receiver['y']),
                z=float(receiver['z']),
            )
            for receiver in payload['receivers']
        ]
        self.preview_scenario = preview
        self._render_scenario_details(project_state.selected_scenario_path, preview, is_preview=True)
        snapshot = self.scene_controller.build_snapshot(project_state.project, preview)
        self.scene_view.set_snapshot(snapshot)
        self._append_log('[info] Updated unsaved scenario preview in scene/details view')

    def save_scenario_variant(self, payload: dict) -> None:
        project_state = self.session_state.project_state
        source_path = payload.get('source_path')
        if project_state.manifest_path is None or not source_path:
            QMessageBox.information(self, 'Scenario Editor', 'Load a project and select a scenario first.')
            return
        suggested_name = (payload.get('scenario_name') or Path(source_path).stem or 'scenario_variant').strip()
        default_path = Path(source_path).resolve().parent / f'{suggested_name}.toml'
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            'Save Derived Scenario As',
            str(default_path),
            'TOML Files (*.toml)',
        )
        if not file_path:
            return
        try:
            self.preview_scenario = None
            saved_path = self.project_controller.save_scenario_variant(source_path, file_path, payload)
            reloaded = self.project_controller.load_project(project_state.manifest_path)
            reloaded.selected_scenario_path = saved_path
            reloaded.selected_scenario = self.project_controller.load_scenario(saved_path)
            self.session_state.project_state = reloaded
            self.project_home_view.set_project_state(reloaded)
            self.scenario_comparison_view.set_scenarios(reloaded.scenario_paths, reloaded.selected_scenario_path)
            self.scenario_comparison_view.set_selected_pair(source_path, saved_path)
            self._update_run_enablement()
            self.scene_view_action.setEnabled(True)
            self.scenario_editor_action.setEnabled(True)
            self.compare_view_action.setEnabled(len(reloaded.scenario_paths) >= 2)
            self._render_scenario_details(saved_path, reloaded.selected_scenario)
            self.scenario_editor_view.set_scenario(saved_path, reloaded.selected_scenario)
            self._update_scene_view()
            self.scenario_editor_view.set_status(f'Saved derived scenario: {saved_path.name}')
            self._append_log(f'[info] Saved derived scenario: {saved_path}')
            self.statusBar().showMessage(f'Saved derived scenario: {saved_path.name}')
            self.compare_selected_scenarios(str(source_path), str(saved_path))
            self.scenario_comparison_view.set_status(f'Derived scenario saved. Comparing {Path(source_path).stem} vs {saved_path.stem}')
            self.show_scenario_comparison()
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, 'Scenario Save Failed', str(exc))
            self._append_log(f'[error] Failed to save scenario variant: {exc}')

    def handle_scene_view_object_selection(self, object_type: str, object_id: str) -> None:
        self.selected_scene_object_key = (object_type, object_id) if object_type and object_id else None
        self.scene_view.set_selected_scene_object(object_type or None, object_id or None)
        self.vehicle_playback_view.set_selected_scene_object(object_type or None, object_id or None)
        if object_type == 'grid_region':
            self._append_log('[info] Selected grid region from view')
            self.statusBar().showMessage('Selected grid region')
            self.show_scenario_editor()
            return
        if object_type and object_id:
            self.scene_object_editor_view.set_selected_object(object_type, object_id)
            self._append_log(f'[info] Selected scene object from view: {object_type}:{object_id}')
            self.statusBar().showMessage(f'Selected scene object: {object_id}')
            self.show_scene_object_editor()

    def handle_scene_object_editor_selection(self, object_type: str, object_id: str) -> None:
        self.selected_scene_object_key = (object_type, object_id) if object_type and object_id else None
        self.scene_view.set_selected_scene_object(object_type or None, object_id or None)
        self.vehicle_playback_view.set_selected_scene_object(object_type or None, object_id or None)

    def start_scene_object_draw_mode(self, payload: dict) -> None:
        object_type = str(payload.get('object_type', '')).strip()
        if not object_type:
            return
        self.scene_view.start_draw_mode(object_type, payload.get('template'))
        self.show_scene_view()
        if object_type in {'noise_barriers', 'terrain_edges'}:
            message = f'Draw mode active for {object_type}: click two points in Scene View.'
        else:
            message = f'Draw mode active for {object_type}: click vertices, then Finish Draw.'
        self.scene_object_editor_view.set_draw_status(message)
        self.statusBar().showMessage(message)
        self._append_log(f'[info] Started draw mode for {object_type}')

    def finish_scene_object_draw_mode(self) -> None:
        self.scene_view.finish_draw_mode()

    def cancel_scene_object_draw_mode(self) -> None:
        self.scene_view.cancel_draw_mode()
        self.scene_object_editor_view.set_draw_status('Draw mode cancelled.')
        self.statusBar().showMessage('Scene-object draw mode cancelled.')


    def start_grid_region_draw_mode(self) -> None:
        self.scene_view.start_draw_mode('grid_region', None)
        self.show_scene_view()
        message = 'Draw mode active for grid region: drag a rectangle in Scene View.'
        self.scenario_editor_view.set_status(message)
        self.statusBar().showMessage(message)
        self._append_log('[info] Started grid-region draw mode')

    def handle_grid_region_drawn(self, payload: dict) -> None:
        self.scenario_editor_view.apply_drawn_grid_region(
            float(payload['min_x']),
            float(payload['max_x']),
            float(payload['min_y']),
            float(payload['max_y']),
        )
        self.show_scenario_editor()
        self.statusBar().showMessage('Grid region updated from Scene View.')
        self._append_log(
            f"[info] Updated grid region from Scene View: x=({payload['min_x']:.1f}, {payload['max_x']:.1f}), y=({payload['min_y']:.1f}, {payload['max_y']:.1f})"
        )


    def handle_grid_region_edited(self, payload: dict) -> None:
        self.scenario_editor_view.apply_drawn_grid_region(
            float(payload['min_x']),
            float(payload['max_x']),
            float(payload['min_y']),
            float(payload['max_y']),
        )
        self.scene_view.set_selected_scene_object('grid_region', 'grid_region')
        self.vehicle_playback_view.set_selected_scene_object('grid_region', 'grid_region')
        self.statusBar().showMessage('Edited grid region geometry.')
        self._append_log(
            f"[info] Edited grid region geometry: x=({payload['min_x']:.1f}, {payload['max_x']:.1f}), y=({payload['min_y']:.1f}, {payload['max_y']:.1f})"
        )

    def handle_scene_object_drawn(self, object_type: str, payload: dict) -> None:
        self.scene_object_editor_view.add_drawn_object(object_type, payload)
        object_id = str(payload.get('id', '')).strip()
        self.selected_scene_object_key = (object_type, object_id) if object_id else None
        self.scene_view.cancel_draw_mode()
        self.show_scene_object_editor()
        self.statusBar().showMessage(f'Drawn new {object_type} object.')
        self._append_log(f'[info] Added scene object from Scene View: {object_type}:{object_id}')

    def handle_scene_object_geometry_edited(self, object_type: str, object_id: str, geometry_payload: dict) -> None:
        self.scene_object_editor_view.update_object_geometry(object_type, object_id, geometry_payload)
        self.selected_scene_object_key = (object_type, object_id)
        self.scene_view.set_selected_scene_object(object_type, object_id)
        self.vehicle_playback_view.set_selected_scene_object(object_type, object_id)
        self.statusBar().showMessage(f'Edited scene object geometry: {object_id}')

    def apply_scene_object_preview(self, payload: dict) -> None:
        project_state = self.session_state.project_state
        if project_state.project is None or project_state.selected_scenario is None:
            return
        preview = deepcopy(project_state.selected_scenario)
        preview.scenario.name = payload.get('scenario_name') or preview.scenario.name
        preview.scenario.description = payload.get('description', preview.scenario.description)
        scene_payload = payload.get('scene', {})
        preview.scene.noise_barriers = [NoiseBarrier(**item) for item in scene_payload.get('noise_barriers', [])]
        preview.scene.buildings = [
            Building(
                id=item['id'],
                footprint=[tuple(point) for point in item.get('footprint', [])],
                height_meters=float(item.get('height_meters', 0.0)),
                attenuation_db=float(item.get('attenuation_db', 0.0)),
                material=str(item.get('material', 'generic')),
            )
            for item in scene_payload.get('buildings', [])
        ]
        preview.scene.terrain_edges = [TerrainEdge(**item) for item in scene_payload.get('terrain_edges', [])]
        preview.scene.ground_surfaces = [
            GroundSurface(
                id=item['id'],
                footprint=[tuple(point) for point in item.get('footprint', [])],
                material=str(item.get('material', 'grass')),
            )
            for item in scene_payload.get('ground_surfaces', [])
        ]
        preview.scene.vegetation_zones = [
            VegetationZone(
                id=item['id'],
                footprint=[tuple(point) for point in item.get('footprint', [])],
                height_meters=float(item.get('height_meters', 0.0)),
                attenuation_db=float(item.get('attenuation_db', 0.0)),
                material=str(item.get('material', 'generic')),
            )
            for item in scene_payload.get('vegetation_zones', [])
        ]
        self.preview_scenario = preview
        self._render_scenario_details(project_state.selected_scenario_path, preview, is_preview=True)
        snapshot = self.scene_controller.build_snapshot(project_state.project, preview)
        self.scene_view.set_snapshot(snapshot)
        self.vehicle_playback_view.set_snapshot(snapshot)
        if self.selected_scene_object_key is not None:
            self.scene_view.set_selected_scene_object(*self.selected_scene_object_key)
            self.vehicle_playback_view.set_selected_scene_object(*self.selected_scene_object_key)
        else:
            self.scene_view.set_selected_scene_object(None, None)
            self.vehicle_playback_view.set_selected_scene_object(None, None)
        self.scene_view.canvas.set_heatmap_cells([])
        self.vehicle_playback_view.set_heatmap_cells([])
        self._append_log('[info] Updated unsaved scene-object preview in scene/details view')

    def save_scene_object_variant(self, payload: dict) -> None:
        project_state = self.session_state.project_state
        source_path = payload.get('source_path')
        if project_state.manifest_path is None or not source_path:
            QMessageBox.information(self, 'Scene Object Editor', 'Load a project and select a scenario first.')
            return
        suggested_name = (payload.get('scenario_name') or Path(source_path).stem or 'scene_variant').strip()
        default_path = Path(source_path).resolve().parent / f'{suggested_name}.toml'
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            'Save Scene-Object Scenario As',
            str(default_path),
            'TOML Files (*.toml)',
        )
        if not file_path:
            return
        try:
            self.preview_scenario = None
            saved_path = self.project_controller.save_scene_object_variant(source_path, file_path, payload)
            reloaded = self.project_controller.load_project(project_state.manifest_path)
            reloaded.selected_scenario_path = saved_path
            reloaded.selected_scenario = self.project_controller.load_scenario(saved_path)
            self.session_state.project_state = reloaded
            self.project_home_view.set_project_state(reloaded)
            self.scenario_comparison_view.set_scenarios(reloaded.scenario_paths, reloaded.selected_scenario_path)
            self.scenario_comparison_view.set_selected_pair(source_path, saved_path)
            self._update_run_enablement()
            self.scene_view_action.setEnabled(True)
            self.scenario_editor_action.setEnabled(True)
            self.scene_object_editor_action.setEnabled(True)
            self.compare_view_action.setEnabled(len(reloaded.scenario_paths) >= 2)
            self._render_scenario_details(saved_path, reloaded.selected_scenario)
            self.scenario_editor_view.set_scenario(saved_path, reloaded.selected_scenario)
            self.scene_object_editor_view.set_scenario(saved_path, reloaded.selected_scenario)
            self._update_scene_view()
            self.scene_object_editor_view.set_status(f'Saved scene-object scenario: {saved_path.name}')
            self._append_log(f'[info] Saved scene-object scenario: {saved_path}')
            self.statusBar().showMessage(f'Saved scene-object scenario: {saved_path.name}')
            self.compare_selected_scenarios(str(source_path), str(saved_path))
            self.scenario_comparison_view.set_status(f'Derived scene-object scenario saved. Comparing {Path(source_path).stem} vs {saved_path.stem}')
            self.show_scenario_comparison()
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, 'Scene Object Save Failed', str(exc))
            self._append_log(f'[error] Failed to save scene-object scenario: {exc}')

    def _render_scenario_details(self, scenario_path: Path | None, scenario, is_preview: bool = False) -> None:
        receiver_lines = [f'- {receiver.id}: ({receiver.x:.1f}, {receiver.y:.1f}, {receiver.z:.1f})' for receiver in scenario.receivers]
        project = self.session_state.project_state.project
        sumo_ready = self._project_has_runnable_sumo(project) if project is not None else False
        lines = [
            f'Scenario: {scenario.scenario.name}',
            '- Preview: unsaved editor values' if is_preview else '- Preview: saved scenario values',
            f'Source file: {scenario_path}',
            f'SUMO attached: {'yes' if sumo_ready else 'no'}',
            '',
            'Scene Objects',
            f'- Noise barriers: {len(scenario.scene.noise_barriers)}',
            f'- Buildings: {len(scenario.scene.buildings)}',
            f'- Terrain edges: {len(scenario.scene.terrain_edges)}',
            f'- Ground surfaces: {len(scenario.scene.ground_surfaces)}',
            f'- Vegetation zones: {len(scenario.scene.vegetation_zones)}',
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
        self._refresh_analysis_panel()

    def _update_scene_view(self) -> None:
        project_state = self.session_state.project_state
        scenario = self.preview_scenario or project_state.selected_scenario
        if project_state.project is None or scenario is None:
            self.scene_view.set_snapshot(None)
            self.vehicle_playback_view.set_snapshot(None)
            self.scene_3d_view.set_frame(None)
            self.dynamic_heatmap_context = None
            self._pending_prefetch_frame_indices = []
            self._playback_prefetch_timer.stop()
            return
        snapshot = self.scene_controller.build_snapshot(project_state.project, scenario)
        self.scene_view.set_snapshot(snapshot)
        self.vehicle_playback_view.set_snapshot(snapshot)
        self.scene_3d_view.set_frame(self.scene3d_controller.build_frame(snapshot))
        if self.selected_scene_object_key is not None:
            self.scene_view.set_selected_scene_object(*self.selected_scene_object_key)
            self.vehicle_playback_view.set_selected_scene_object(*self.selected_scene_object_key)
        else:
            self.scene_view.set_selected_scene_object(None, None)
            self.vehicle_playback_view.set_selected_scene_object(None, None)
        if self.preview_scenario is None and self.current_result_summary is not None:
            self._load_heatmap_from_result_summary(self.current_result_summary)
        else:
            self.scene_view.canvas.set_heatmap_cells([])
            self.vehicle_playback_view.set_heatmap_cells([])
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
                self.scene_3d_view.set_frame(self.scene3d_controller.build_frame(snapshot))
                return candidate
        return selected

    def _load_heatmap_from_result_summary(self, summary) -> None:
        cells = self.result_controller.load_heatmap_cells(getattr(summary, 'final_grid_snapshot_file', None))
        self.scene_view.canvas.set_heatmap_cells(cells)
        self.vehicle_playback_view.set_heatmap_cells(cells)
        frame = self.scene_3d_view.canvas.frame_data
        if frame is not None:
            self.scene_3d_view.set_frame(self.scene3d_controller.apply_noise_cells(frame, cells))
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
        scene3d_frame = self.scene_3d_view.canvas.frame_data
        if scene3d_frame is not None:
            self.scene_3d_view.set_frame(self.scene3d_controller.apply_noise_cells(scene3d_frame, cells))
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

    def open_quickstart_guide(self) -> None:
        self._open_path(Path.cwd() / 'docs' / 'new_project_quickstart.md', label='quickstart guide')

    def open_user_guide(self) -> None:
        self._open_path(Path.cwd() / 'docs' / 'user_guide.md', label='user guide')

    def show_about_dialog(self) -> None:
        QMessageBox.information(
            self,
            'About MTNsim',
            'MTNsim Noise Simulation Workbench\n\nA GUI prototype for microscopic traffic-noise simulation, playback, comparison, and validation workflows.',
        )

    def _open_path(self, path_like: str | Path | None, *, label: str) -> None:
        if not path_like:
            QMessageBox.information(self, 'Open Path', f'{label} is not available yet.')
            return
        path = Path(path_like)
        if not path.exists():
            QMessageBox.warning(self, 'Open Path', f'{label} does not exist:\n{path}')
            return
        os.startfile(str(path))
        self._append_log(f'[info] Opened {label}: {path}')

    def _write_text_export(self, default_path: Path, title: str, content: str, file_filter: str) -> Path | None:
        file_path, _ = QFileDialog.getSaveFileName(self, title, str(default_path), file_filter)
        if not file_path:
            return None
        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding='utf-8')
        self._append_log(f'[info] Exported {title}: {output_path}')
        self.statusBar().showMessage(f'Exported: {output_path.name}')
        return output_path

    def open_current_result_output_dir(self) -> None:
        summary = self.current_result_summary
        self._open_path(summary.output_dir if summary else None, label='result output folder')

    def open_current_result_summary_file(self) -> None:
        self._open_path(self.current_result_summary_path, label='result summary file')

    def open_current_run_manifest_file(self) -> None:
        summary = self.current_result_summary
        self._open_path(summary.manifest_file if summary else None, label='run manifest file')

    def export_current_result_markdown(self) -> None:
        summary = self.current_result_summary
        if summary is None:
            QMessageBox.information(self, 'Result Export', 'Load a result summary first.')
            return
        lines = [
            '# MTNsim Result Summary',
            '',
            f'- Run ID: {summary.run.run_id}',
            f'- Project: {summary.run.project}',
            f'- Scenario: {summary.run.scenario}',
            f'- Output Dir: {summary.output_dir}',
            f'- Used GPU: {summary.used_gpu}',
            '',
            '## Receivers',
        ]
        for receiver_id, stats in sorted(summary.receiver_stats.items()):
            lines.append(f'- {receiver_id}: min={stats.min_db:.2f}, max={stats.max_db:.2f}, mean={stats.mean_db:.2f}, samples={stats.sample_count}')
        if summary.propagation_features:
            lines.extend(['', '## Propagation Features'])
            for key, value in sorted(summary.propagation_features.items()):
                lines.append(f'- {key}: {value}')
        default_path = Path(summary.output_dir) / 'result_summary_report.md'
        output_path = self._write_text_export(default_path, 'Export Result Markdown', '\n'.join(lines) + '\n', 'Markdown Files (*.md)')
        if output_path is not None:
            QMessageBox.information(self, 'Result Export', 'Markdown summary saved to:\n' + str(output_path))

    def open_compare_run_a_summary(self) -> None:
        self._open_path(self.scenario_comparison_view._run_a_summary_file, label='comparison run A summary')

    def open_compare_run_b_summary(self) -> None:
        self._open_path(self.scenario_comparison_view._run_b_summary_file, label='comparison run B summary')

    def export_scenario_comparison_json(self) -> None:
        if self.current_config_comparison is None:
            QMessageBox.information(self, 'Scenario Comparison Export', 'Run or load a scenario comparison first.')
            return
        payload = {'config_comparison': self.current_config_comparison.to_dict()}
        if self.current_compare_payload is not None:
            payload['run_comparison'] = self.current_compare_payload
        scenario_a = self.current_config_comparison.scenario_a
        scenario_b = self.current_config_comparison.scenario_b
        default_path = Path.cwd() / f'{scenario_a}_vs_{scenario_b}_comparison.json'
        output_path = self._write_text_export(default_path, 'Export Scenario Comparison JSON', json.dumps(payload, ensure_ascii=False, indent=2), 'JSON Files (*.json)')
        if output_path is not None:
            QMessageBox.information(self, 'Scenario Comparison Export', 'Comparison JSON saved to:\n' + str(output_path))

    def export_scenario_comparison_markdown(self) -> None:
        if self.current_config_comparison is None:
            QMessageBox.information(self, 'Scenario Comparison Export', 'Run or load a scenario comparison first.')
            return
        comparison = self.current_config_comparison
        lines = [
            '# MTNsim Scenario Comparison',
            '',
            f'- Project: {comparison.project}',
            f'- Scenario A: {comparison.scenario_a}',
            f'- Scenario B: {comparison.scenario_b}',
            f'- Config diff count: {len(comparison.differing_fields)}',
            '',
            '## Configuration Differences',
        ]
        if comparison.differing_fields:
            for field, values in comparison.differing_fields.items():
                lines.append(f"- {field}: {values.get('scenario_a')} -> {values.get('scenario_b')}")
        else:
            lines.append('- No configuration differences detected.')
        if self.current_compare_payload is not None:
            run_cmp = self.current_compare_payload['comparison']
            lines.extend(['', '## Run Comparison'])
            lines.append(f"- Run A: {self.current_compare_payload['artifacts_a']['run_id']}")
            lines.append(f"- Run B: {self.current_compare_payload['artifacts_b']['run_id']}")
            for key, value in sorted(run_cmp.get('summary', {}).items()):
                lines.append(f'- {key}: {value}')
        default_path = Path.cwd() / f'{comparison.scenario_a}_vs_{comparison.scenario_b}_comparison.md'
        output_path = self._write_text_export(default_path, 'Export Scenario Comparison Markdown', '\n'.join(lines) + '\n', 'Markdown Files (*.md)')
        if output_path is not None:
            QMessageBox.information(self, 'Scenario Comparison Export', 'Comparison Markdown saved to:\n' + str(output_path))

    def open_campaign_output_dir(self) -> None:
        value = self.campaign_validation_view.output_dir_label.text()
        self._open_path(None if value == '-' else value, label='campaign output folder')

    def open_campaign_summary_file(self) -> None:
        self._open_path(self.campaign_validation_view._summary_file, label='campaign summary file')

    def open_campaign_report_file(self) -> None:
        self._open_path(self.campaign_validation_view._report_file, label='campaign report file')

    def open_campaign_result_summary_file(self) -> None:
        self._open_path(self.campaign_validation_view._result_summary_file, label='campaign result summary file')

    def open_campaign_calibration_summary_file(self) -> None:
        self._open_path(self.campaign_validation_view._calibration_summary_file, label='campaign calibration summary file')

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
