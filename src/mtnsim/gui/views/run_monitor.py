from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mtnsim.gui.state import GuiRunState


class RunMonitorView(QWidget):
    back_requested = Signal()
    open_result_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel('Run Monitor')
        title.setObjectName('pageTitle')
        layout.addWidget(title)

        button_row = QHBoxLayout()
        self.back_button = QPushButton('Back to Project Home')
        self.back_button.clicked.connect(self.back_requested.emit)
        button_row.addWidget(self.back_button)
        self.open_result_button = QPushButton('Open Result Viewer')
        self.open_result_button.clicked.connect(self.open_result_requested.emit)
        self.open_result_button.setEnabled(False)
        button_row.addWidget(self.open_result_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.status_label = QLabel('Idle')
        self.status_label.setObjectName('statusBadgeNeutral')
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        info_card = QFrame()
        info_card.setObjectName('infoCard')
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(8)
        info_title = QLabel('Run Summary')
        info_title.setObjectName('sectionTitle')
        info_layout.addWidget(info_title)
        form = QFormLayout()
        self.project_label = QLabel('-')
        self.scenario_label = QLabel('-')
        self.execution_label = QLabel('-')
        self.run_id_label = QLabel('-')
        self.output_dir_label = QLabel('-')
        self.output_dir_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.manifest_file_label = QLabel('-')
        self.manifest_file_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.result_summary_label = QLabel('-')
        self.result_summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow('Project', self.project_label)
        form.addRow('Scenario', self.scenario_label)
        form.addRow('Execution', self.execution_label)
        form.addRow('Run ID', self.run_id_label)
        form.addRow('Output Dir', self.output_dir_label)
        form.addRow('Manifest File', self.manifest_file_label)
        form.addRow('Result Summary', self.result_summary_label)
        info_layout.addLayout(form)
        layout.addWidget(info_card)

        self.completion_summary_box = QTextEdit()
        self.completion_summary_box.setObjectName('infoCard')
        self.completion_summary_box.setReadOnly(True)
        self.completion_summary_box.setPlaceholderText('Run readiness and completion summary will appear here.')
        layout.addWidget(self.completion_summary_box, 1)

        self.receiver_files_box = QTextEdit()
        self.receiver_files_box.setObjectName('infoCard')
        self.receiver_files_box.setReadOnly(True)
        self.receiver_files_box.setPlaceholderText('Receiver output files will appear here after completion.')
        layout.addWidget(self.receiver_files_box, 1)

    def set_run_state(self, state: GuiRunState) -> None:
        self.status_label.setText(state.progress_label)
        self.progress_bar.setValue(state.progress_percent)
        self.project_label.setText(getattr(state, 'project_name', '-') or '-')
        self.scenario_label.setText(getattr(state, 'scenario_name', '-') or '-')
        execution_mode = 'GPU preferred' if getattr(state, 'requested_use_gpu', False) else 'CPU only'
        if state.result_summary_file is not None and getattr(state, 'used_gpu', None) is not None:
            execution_mode = 'GPU used' if state.used_gpu else 'CPU used'
        self.execution_label.setText(execution_mode)
        self.run_id_label.setText(state.run_id or '-')
        self.output_dir_label.setText(str(state.output_dir) if state.output_dir else '-')
        self.manifest_file_label.setText(str(state.manifest_file) if state.manifest_file else '-')
        self.result_summary_label.setText(str(state.result_summary_file) if state.result_summary_file else '-')
        self.open_result_button.setEnabled(state.result_summary_file is not None)

        summary_lines = []
        if getattr(state, 'readiness_summary', ''):
            summary_lines.append(state.readiness_summary)
        if state.run_id is not None:
            summary_lines.append(f'Run ID: {state.run_id}')
        if getattr(state, 'used_gpu', None) is not None:
            summary_lines.append('Execution outcome: ' + ('GPU used' if state.used_gpu else 'CPU used'))
        if getattr(state, 'receiver_count', None) is not None:
            summary_lines.append(f'Receiver files: {state.receiver_count}')
        if state.vehicle_trace_file is not None:
            summary_lines.append('Vehicle playback trace is available.')
        if state.final_grid_snapshot_file is not None:
            summary_lines.append('Final grid snapshot is available.')
        if state.error_message:
            summary_lines.append(f'Error: {state.error_message}')
        self.completion_summary_box.setPlainText('\n'.join(summary_lines))

        if state.receiver_history_files:
            self.receiver_files_box.setPlainText('\n'.join(f'{key}: {value}' for key, value in state.receiver_history_files.items()))
        elif state.error_message:
            self.receiver_files_box.setPlainText(f'Error: {state.error_message}')
        else:
            self.receiver_files_box.setPlainText('')
