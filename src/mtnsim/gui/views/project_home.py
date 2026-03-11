from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mtnsim.gui.state import GuiProjectState


class ProjectHomeView(QWidget):
    open_project_requested = Signal()
    scenario_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(12)

        title = QLabel('MTNsim Project Home')
        title.setObjectName('pageTitle')
        title.setStyleSheet('font-size: 22px; font-weight: 700;')
        root_layout.addWidget(title)

        button_row = QHBoxLayout()
        self.open_project_button = QPushButton('Open Project')
        self.open_project_button.clicked.connect(self.open_project_requested.emit)
        button_row.addWidget(self.open_project_button)
        button_row.addStretch(1)
        root_layout.addLayout(button_row)

        self.project_name_label = QLabel('Project: not loaded')
        self.project_path_label = QLabel('Manifest: -')
        self.project_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root_layout.addWidget(self.project_name_label)
        root_layout.addWidget(self.project_path_label)

        scenarios_label = QLabel('Available Scenarios')
        scenarios_label.setStyleSheet('font-size: 15px; font-weight: 600; margin-top: 8px;')
        root_layout.addWidget(scenarios_label)

        self.scenario_list = QListWidget()
        self.scenario_list.currentItemChanged.connect(self._emit_current_scenario)
        root_layout.addWidget(self.scenario_list, 1)

        self.summary_label = QLabel('Load a project manifest to browse scenarios.')
        self.summary_label.setWordWrap(True)
        root_layout.addWidget(self.summary_label)

    def set_project_state(self, state: GuiProjectState) -> None:
        if state.project is None or state.manifest_path is None:
            self.project_name_label.setText('Project: not loaded')
            self.project_path_label.setText('Manifest: -')
            self.summary_label.setText('Load a project manifest to browse scenarios.')
            self.scenario_list.clear()
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

    def _emit_current_scenario(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:  # noqa: ARG002
        if current is None:
            return
        scenario_path = current.data(Qt.UserRole)
        if scenario_path:
            self.scenario_selected.emit(str(scenario_path))
