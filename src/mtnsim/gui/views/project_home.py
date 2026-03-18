from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from mtnsim.gui.state import GuiProjectState, GuiRunState


class ProjectHomeView(QWidget):
    open_project_requested = Signal()
    new_project_requested = Signal()
    import_project_requested = Signal()
    attach_sumo_requested = Signal()
    scene_requested = Signal()
    scenario_selected = Signal(str)
    run_selected_requested = Signal()
    edit_selected_requested = Signal()
    recent_result_selected = Signal(str)
    open_recent_result_requested = Signal(str)
    open_latest_output_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(12)

        title = QLabel('MTNsim Project Home')
        title.setObjectName('pageTitle')
        root_layout.addWidget(title)

        helper_label = QLabel('Use the top toolbar menus for project creation, import, attachment, validation, and help. Use the left workspace list to switch views.')
        helper_label.setWordWrap(True)
        helper_label.setObjectName('homeHelperLabel')
        root_layout.addWidget(helper_label)

        shortcut_row = QHBoxLayout()
        shortcut_row.setSpacing(8)

        self.attach_sumo_button = QPushButton('Attach SUMO')
        self.attach_sumo_button.clicked.connect(self.attach_sumo_requested.emit)
        self.attach_sumo_button.setEnabled(False)
        shortcut_row.addWidget(self.attach_sumo_button)

        self.open_scene_button = QPushButton('Open Scene View')
        self.open_scene_button.clicked.connect(self.scene_requested.emit)
        self.open_scene_button.setEnabled(False)
        shortcut_row.addWidget(self.open_scene_button)

        self.edit_selected_button = QPushButton('Edit Selected Scenario')
        self.edit_selected_button.clicked.connect(self.edit_selected_requested.emit)
        self.edit_selected_button.setEnabled(False)
        shortcut_row.addWidget(self.edit_selected_button)

        self.run_selected_button = QPushButton('Run Selected Scenario')
        self.run_selected_button.clicked.connect(self.run_selected_requested.emit)
        self.run_selected_button.setEnabled(False)
        shortcut_row.addWidget(self.run_selected_button)

        shortcut_row.addStretch(1)
        root_layout.addLayout(shortcut_row)

        summary_card = QFrame()
        summary_card.setObjectName('infoCard')
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(14, 12, 14, 12)
        summary_layout.setSpacing(6)
        self.project_name_label = QLabel('Project: not loaded')
        self.project_path_label = QLabel('Manifest: -')
        self.project_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.project_status_label = QLabel('Status: not loaded')
        self.project_status_label.setObjectName('statusBadgeWarning')
        self.readiness_label = QLabel('Readiness: load or create a project to see what is missing before a run.')
        self.readiness_label.setWordWrap(True)
        summary_layout.addWidget(self.project_name_label)
        summary_layout.addWidget(self.project_path_label)
        summary_layout.addWidget(self.project_status_label)
        summary_layout.addWidget(self.readiness_label)
        root_layout.addWidget(summary_card)

        splitter = QSplitter()
        root_layout.addWidget(splitter, 1)

        scenarios_panel = QWidget()
        scenarios_layout = QVBoxLayout(scenarios_panel)
        scenarios_layout.setContentsMargins(0, 0, 0, 0)
        scenarios_layout.setSpacing(8)

        scenarios_label = QLabel('Available Scenarios')
        scenarios_label.setObjectName('sectionTitle')
        scenarios_layout.addWidget(scenarios_label)

        self.scenario_list = QListWidget()
        self.scenario_list.setObjectName('infoCard')
        self.scenario_list.currentItemChanged.connect(self._emit_current_scenario)
        scenarios_layout.addWidget(self.scenario_list, 1)

        self.summary_label = QLabel('Load a project manifest or create/import a project to browse scenarios.')
        self.summary_label.setWordWrap(True)
        scenarios_layout.addWidget(self.summary_label)

        splitter.addWidget(scenarios_panel)

        recent_panel = QWidget()
        recent_layout = QVBoxLayout(recent_panel)
        recent_layout.setContentsMargins(0, 0, 0, 0)
        recent_layout.setSpacing(8)

        recent_label = QLabel('Recent Runs')
        recent_label.setObjectName('sectionTitle')
        recent_layout.addWidget(recent_label)

        self.latest_run_label = QLabel('Latest run: -')
        self.latest_run_label.setWordWrap(True)
        recent_layout.addWidget(self.latest_run_label)

        recent_button_row = QHBoxLayout()
        self.open_recent_result_button = QPushButton('Open Selected Result')
        self.open_recent_result_button.setEnabled(False)
        self.open_recent_result_button.clicked.connect(self._emit_open_recent_result)
        recent_button_row.addWidget(self.open_recent_result_button)
        self.open_latest_output_button = QPushButton('Open Latest Output Folder')
        self.open_latest_output_button.setEnabled(False)
        self.open_latest_output_button.clicked.connect(self.open_latest_output_requested.emit)
        recent_button_row.addWidget(self.open_latest_output_button)
        recent_layout.addLayout(recent_button_row)

        self.recent_results_list = QListWidget()
        self.recent_results_list.setObjectName('infoCard')
        self.recent_results_list.currentItemChanged.connect(self._handle_recent_result_changed)
        self.recent_results_list.itemDoubleClicked.connect(lambda item: self._emit_open_recent_result())
        recent_layout.addWidget(self.recent_results_list, 1)

        self.recent_summary_label = QLabel('No recent run selected.')
        self.recent_summary_label.setWordWrap(True)
        recent_layout.addWidget(self.recent_summary_label)

        splitter.addWidget(recent_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

    def set_project_state(self, state: GuiProjectState) -> None:
        if state.project is None or state.manifest_path is None:
            self.project_name_label.setText('Project: not loaded')
            self.project_path_label.setText('Manifest: -')
            self.summary_label.setText('Load a project manifest or create/import a project to browse scenarios.')
            self.project_status_label.setText('Status: not loaded')
            self.project_status_label.setObjectName('statusBadgeWarning')
            self.project_status_label.style().unpolish(self.project_status_label)
            self.project_status_label.style().polish(self.project_status_label)
            self.readiness_label.setText('Readiness: load or create a project to see what is missing before a run.')
            self.scenario_list.clear()
            self.run_selected_button.setEnabled(False)
            self.edit_selected_button.setEnabled(False)
            self.open_scene_button.setEnabled(False)
            self.attach_sumo_button.setEnabled(False)
            return

        self.project_name_label.setText(f'Project: {state.project.project.name} ({state.project.project.version})')
        self.project_path_label.setText(f'Manifest: {state.manifest_path}')
        self.summary_label.setText(
            f"Default scenario: {state.project.project.default_scenario} | "
            f"Scenarios found: {len(state.scenario_paths)}"
        )

        self.scenario_list.blockSignals(True)
        self.scenario_list.clear()
        selected_row = -1
        for index, scenario_path in enumerate(state.scenario_paths):
            item = QListWidgetItem(scenario_path.stem)
            item.setData(Qt.UserRole, str(scenario_path))
            item.setToolTip(str(scenario_path))
            self.scenario_list.addItem(item)
            if state.selected_scenario_path is not None and Path(scenario_path) == Path(state.selected_scenario_path):
                selected_row = index
        if selected_row >= 0:
            self.scenario_list.setCurrentRow(selected_row)
        self.scenario_list.blockSignals(False)
        enabled = state.selected_scenario_path is not None
        self.run_selected_button.setEnabled(enabled)
        self.open_scene_button.setEnabled(enabled)
        self.edit_selected_button.setEnabled(enabled)
        self.open_scene_button.setEnabled(enabled)
        self.attach_sumo_button.setEnabled(state.manifest_path is not None)


    def set_project_readiness(self, *, status_title: str, status_color: str, summary: str) -> None:
        self.project_status_label.setText(status_title)
        if status_color == '#166534':
            self.project_status_label.setObjectName('statusBadgeReady')
        elif status_color == '#9a3412':
            self.project_status_label.setObjectName('statusBadgeWarning')
        else:
            self.project_status_label.setObjectName('statusBadgeNeutral')
        self.project_status_label.style().unpolish(self.project_status_label)
        self.project_status_label.style().polish(self.project_status_label)
        self.readiness_label.setText(summary)

    def set_run_enabled(self, enabled: bool) -> None:
        self.run_selected_button.setEnabled(enabled)
        self.open_scene_button.setEnabled(enabled)

    def set_recent_results(self, result_paths: list[Path]) -> None:
        self.recent_results_list.blockSignals(True)
        self.recent_results_list.clear()
        for path in result_paths:
            item = QListWidgetItem(path.parent.name)
            item.setData(Qt.UserRole, str(path))
            item.setToolTip(str(path))
            self.recent_results_list.addItem(item)
        if result_paths:
            self.recent_results_list.setCurrentRow(0)
            self.open_recent_result_button.setEnabled(True)
        else:
            self.open_recent_result_button.setEnabled(False)
            self.recent_summary_label.setText('No recent results yet.')
        self.recent_results_list.blockSignals(False)

    def set_last_run(self, state: GuiRunState) -> None:
        if state.run_id is None:
            self.latest_run_label.setText('Latest run: -')
            self.open_latest_output_button.setEnabled(False)
            return
        output_dir = state.output_dir if state.output_dir is not None else '-'
        self.latest_run_label.setText(f'Latest run: {state.run_id}\nOutput: {output_dir}')
        self.open_latest_output_button.setEnabled(state.output_dir is not None)

    def _handle_recent_result_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:  # noqa: ARG002
        if current is None:
            self.open_recent_result_button.setEnabled(False)
            self.recent_summary_label.setText('No recent run selected.')
            return
        result_path = current.data(Qt.UserRole)
        self.open_recent_result_button.setEnabled(bool(result_path))
        self.recent_summary_label.setText(f'Selected result summary:\n{result_path}')
        if result_path:
            self.recent_result_selected.emit(str(result_path))

    def _emit_open_recent_result(self) -> None:
        current = self.recent_results_list.currentItem()
        if current is None:
            return
        result_path = current.data(Qt.UserRole)
        if result_path:
            self.open_recent_result_requested.emit(str(result_path))

    def _emit_current_scenario(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:  # noqa: ARG002
        if current is None:
            self.run_selected_button.setEnabled(False)
            self.edit_selected_button.setEnabled(False)
            self.open_scene_button.setEnabled(False)
            self.attach_sumo_button.setEnabled(False)
            return
        scenario_path = current.data(Qt.UserRole)
        enabled = bool(scenario_path)
        self.run_selected_button.setEnabled(enabled)
        self.open_scene_button.setEnabled(enabled)
        self.edit_selected_button.setEnabled(enabled)
        if scenario_path:
            self.scenario_selected.emit(str(scenario_path))
