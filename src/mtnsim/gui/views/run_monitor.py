from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
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

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel('Run Monitor')
        title.setStyleSheet('font-size: 22px; font-weight: 700;')
        layout.addWidget(title)

        button_row = QHBoxLayout()
        self.back_button = QPushButton('Back to Project Home')
        self.back_button.clicked.connect(self.back_requested.emit)
        button_row.addWidget(self.back_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.status_label = QLabel('Idle')
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        form = QFormLayout()
        self.run_id_label = QLabel('-')
        self.output_dir_label = QLabel('-')
        self.output_dir_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.manifest_file_label = QLabel('-')
        self.manifest_file_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.result_summary_label = QLabel('-')
        self.result_summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow('Run ID', self.run_id_label)
        form.addRow('Output Dir', self.output_dir_label)
        form.addRow('Manifest File', self.manifest_file_label)
        form.addRow('Result Summary', self.result_summary_label)
        layout.addLayout(form)

        self.receiver_files_box = QTextEdit()
        self.receiver_files_box.setReadOnly(True)
        self.receiver_files_box.setPlaceholderText('Receiver output files will appear here after completion.')
        layout.addWidget(self.receiver_files_box, 1)

    def set_run_state(self, state: GuiRunState) -> None:
        self.status_label.setText(state.progress_label)
        self.progress_bar.setValue(state.progress_percent)
        self.run_id_label.setText(state.run_id or '-')
        self.output_dir_label.setText(str(state.output_dir) if state.output_dir else '-')
        self.manifest_file_label.setText(str(state.manifest_file) if state.manifest_file else '-')
        self.result_summary_label.setText(str(state.result_summary_file) if state.result_summary_file else '-')
        if state.receiver_history_files:
            self.receiver_files_box.setPlainText('\n'.join(f'{key}: {value}' for key, value in state.receiver_history_files.items()))
        elif state.error_message:
            self.receiver_files_box.setPlainText(f'Error: {state.error_message}')
        else:
            self.receiver_files_box.setPlainText('')
