from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mtnsim.schemas.results import RunResultSummary


class ReceiverSeriesChart(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.points: list[tuple[int, float]] = []
        self.title = 'Receiver Time Series'
        self.active_time_index: int | None = None
        self.active_value_db: float | None = None
        self.setMinimumHeight(260)

    def set_series(self, receiver_id: str, points: list[tuple[int, float]]) -> None:
        self.points = points
        self.title = f'Receiver Time Series: {receiver_id}'
        self.active_value_db = None
        if self.active_time_index is not None:
            self._update_active_value()
        self.update()

    def set_playback_cursor(self, time_index: int | None) -> None:
        self.active_time_index = time_index
        self._update_active_value()
        self.update()

    def _update_active_value(self) -> None:
        if self.active_time_index is None or not self.points:
            self.active_value_db = None
            return
        closest = min(self.points, key=lambda item: abs(item[0] - self.active_time_index))
        self.active_value_db = float(closest[1])

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#faf7f0'))
        painter.setRenderHint(QPainter.Antialiasing)

        margin_left = 56
        margin_right = 16
        margin_top = 28
        margin_bottom = 34
        plot_rect = self.rect().adjusted(margin_left, margin_top, -margin_right, -margin_bottom)

        painter.setPen(QPen(QColor('#1f2937'), 1))
        painter.drawText(12, 18, self.title)
        painter.drawRect(plot_rect)

        if not self.points:
            painter.drawText(plot_rect.adjusted(8, 8, -8, -8), Qt.AlignCenter, 'No receiver series loaded.')
            return

        xs = [point[0] for point in self.points]
        ys = [point[1] for point in self.points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        if max_x == min_x:
            max_x += 1
        if max_y == min_y:
            max_y += 1

        painter.drawText(8, plot_rect.top() + 12, f'{max_y:.1f} dB')
        painter.drawText(8, plot_rect.bottom(), f'{min_y:.1f} dB')
        painter.drawText(plot_rect.left(), self.height() - 10, str(min_x))
        painter.drawText(plot_rect.right() - 30, self.height() - 10, str(max_x))

        polyline = []
        for x, y in self.points:
            ratio_x = (x - min_x) / (max_x - min_x)
            ratio_y = (y - min_y) / (max_y - min_y)
            px = plot_rect.left() + (plot_rect.width() * ratio_x)
            py = plot_rect.bottom() - (plot_rect.height() * ratio_y)
            polyline.append((px, py))

        painter.setPen(QPen(QColor('#c2410c'), 2))
        for index in range(len(polyline) - 1):
            painter.drawLine(int(polyline[index][0]), int(polyline[index][1]), int(polyline[index + 1][0]), int(polyline[index + 1][1]))

        if self.active_time_index is not None:
            clamped_time = max(min_x, min(max_x, self.active_time_index))
            ratio_x = (clamped_time - min_x) / (max_x - min_x)
            cursor_x = plot_rect.left() + (plot_rect.width() * ratio_x)
            painter.setPen(QPen(QColor('#0f766e'), 2, Qt.DashLine))
            painter.drawLine(int(cursor_x), int(plot_rect.top()), int(cursor_x), int(plot_rect.bottom()))
            if self.active_value_db is not None:
                value_ratio_y = (self.active_value_db - min_y) / (max_y - min_y)
                value_y = plot_rect.bottom() - (plot_rect.height() * value_ratio_y)
                painter.setBrush(QColor('#0f766e'))
                painter.setPen(QPen(QColor('#0f766e'), 1))
                painter.drawEllipse(int(cursor_x) - 4, int(value_y) - 4, 8, 8)
                label = f't={clamped_time}, {self.active_value_db:.1f} dB'
                label_rect_x = min(plot_rect.right() - 118, cursor_x + 8)
                painter.fillRect(int(label_rect_x), int(max(plot_rect.top() + 4, value_y - 22)), 114, 20, QColor(255, 255, 255, 220))
                painter.setPen(QPen(QColor('#0f172a'), 1))
                painter.drawText(int(label_rect_x) + 6, int(max(plot_rect.top() + 18, value_y - 8)), label)


class ResultViewerView(QWidget):
    recent_result_selected = Signal(str)
    receiver_selected = Signal(str)
    open_output_dir_requested = Signal()
    open_result_summary_requested = Signal()
    open_manifest_requested = Signal()
    export_markdown_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._result_summary_path = ''
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(12)

        title = QLabel('Result Viewer')
        title.setObjectName('pageTitle')
        outer.addWidget(title)

        action_row = QHBoxLayout()
        self.open_output_dir_button = QLabel('<a href="#">Open Output Folder</a>')
        self.open_output_dir_button.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.open_output_dir_button.linkActivated.connect(lambda *_: self.open_output_dir_requested.emit())
        action_row.addWidget(self.open_output_dir_button)
        self.open_result_summary_button = QLabel('<a href="#">Open Result Summary</a>')
        self.open_result_summary_button.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.open_result_summary_button.linkActivated.connect(lambda *_: self.open_result_summary_requested.emit())
        action_row.addWidget(self.open_result_summary_button)
        self.open_manifest_button = QLabel('<a href="#">Open Run Manifest</a>')
        self.open_manifest_button.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.open_manifest_button.linkActivated.connect(lambda *_: self.open_manifest_requested.emit())
        action_row.addWidget(self.open_manifest_button)
        self.export_markdown_button = QLabel('<a href="#">Export Markdown</a>')
        self.export_markdown_button.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.export_markdown_button.linkActivated.connect(lambda *_: self.export_markdown_requested.emit())
        action_row.addWidget(self.export_markdown_button)
        action_row.addStretch(1)
        outer.addLayout(action_row)

        splitter = QSplitter()
        outer.addWidget(splitter, 1)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        recent_label = QLabel('Recent Results')
        recent_label.setObjectName('sectionTitle')
        left_layout.addWidget(recent_label)

        self.recent_results_list = QListWidget()
        self.recent_results_list.setObjectName('infoCard')
        self.recent_results_list.currentItemChanged.connect(self._emit_recent_result)
        left_layout.addWidget(self.recent_results_list, 1)

        self.metadata_box = QTextEdit()
        self.metadata_box.setObjectName('infoCard')
        self.metadata_box.setReadOnly(True)
        self.metadata_box.setPlaceholderText('Result metadata will appear here.')
        left_layout.addWidget(self.metadata_box, 1)

        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        summary_card = QFrame()
        summary_card.setObjectName('infoCard')
        summary_card_layout = QVBoxLayout(summary_card)
        summary_card_layout.setContentsMargins(14, 12, 14, 12)
        summary_card_layout.setSpacing(8)
        summary_title = QLabel('Run Details')
        summary_title.setObjectName('sectionTitle')
        summary_card_layout.addWidget(summary_title)
        summary_form = QFormLayout()
        self.run_id_label = QLabel('-')
        self.scenario_label = QLabel('-')
        self.output_dir_label = QLabel('-')
        self.output_dir_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.execution_label = QLabel('-')
        self.receiver_count_label = QLabel('-')
        self.playback_cursor_label = QLabel('-')
        summary_form.addRow('Run ID', self.run_id_label)
        summary_form.addRow('Scenario', self.scenario_label)
        summary_form.addRow('Output Dir', self.output_dir_label)
        summary_form.addRow('Execution', self.execution_label)
        summary_form.addRow('Receivers', self.receiver_count_label)
        summary_form.addRow('Playback Cursor', self.playback_cursor_label)
        summary_card_layout.addLayout(summary_form)
        right_layout.addWidget(summary_card)

        self.receiver_table = QTableWidget(0, 4)
        self.receiver_table.setObjectName('infoCard')
        self.receiver_table.setHorizontalHeaderLabels(['Receiver', 'Min dB', 'Max dB', 'Mean dB'])
        self.receiver_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.receiver_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.receiver_table.itemSelectionChanged.connect(self._emit_selected_receiver)
        right_layout.addWidget(self.receiver_table, 1)

        receiver_row = QHBoxLayout()
        receiver_series_label = QLabel('Receiver Series')
        receiver_series_label.setObjectName('sectionTitle')
        receiver_row.addWidget(receiver_series_label)
        self.receiver_selector = QComboBox()
        self.receiver_selector.currentTextChanged.connect(self._emit_combo_receiver)
        receiver_row.addWidget(self.receiver_selector, 1)
        right_layout.addLayout(receiver_row)

        self.chart_widget = ReceiverSeriesChart()
        right_layout.addWidget(self.chart_widget, 2)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

    def set_result_summary_source(self, result_summary_path: str | Path | None) -> None:
        self._result_summary_path = str(result_summary_path) if result_summary_path else ''

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
        self.recent_results_list.blockSignals(False)

    def set_result_summary(self, summary: RunResultSummary) -> None:
        self.run_id_label.setText(summary.run.run_id)
        self.scenario_label.setText(summary.run.scenario)
        self.output_dir_label.setText(summary.output_dir)
        self.execution_label.setText('GPU used' if summary.used_gpu else 'CPU used')
        self.receiver_count_label.setText(str(len(summary.receiver_stats)))
        metadata_lines = [
            f'Project: {summary.run.project}',
            f'Used GPU: {summary.used_gpu}',
            f'Receiver count: {len(summary.receiver_stats)}',
        ]
        if summary.propagation_features:
            metadata_lines.append('')
            metadata_lines.append('Propagation Features:')
            for key, value in sorted(summary.propagation_features.items()):
                metadata_lines.append(f'- {key}: {value}')
        self.metadata_box.setPlainText('\n'.join(metadata_lines))

        receiver_ids = sorted(summary.receiver_stats.keys())
        self.receiver_table.setRowCount(len(receiver_ids))
        self.receiver_selector.blockSignals(True)
        self.receiver_selector.clear()
        for row, receiver_id in enumerate(receiver_ids):
            stats = summary.receiver_stats[receiver_id]
            self.receiver_table.setItem(row, 0, QTableWidgetItem(receiver_id))
            self.receiver_table.setItem(row, 1, QTableWidgetItem(f'{stats.min_db:.2f}'))
            self.receiver_table.setItem(row, 2, QTableWidgetItem(f'{stats.max_db:.2f}'))
            self.receiver_table.setItem(row, 3, QTableWidgetItem(f'{stats.mean_db:.2f}'))
            self.receiver_selector.addItem(receiver_id)
        self.receiver_selector.blockSignals(False)
        if receiver_ids:
            self.receiver_table.selectRow(0)
            self.receiver_selector.setCurrentText(receiver_ids[0])
        else:
            self.chart_widget.set_series('none', [])
            self.set_playback_cursor(None)

    def set_receiver_series(self, receiver_id: str, points: list[tuple[int, float]]) -> None:
        self.chart_widget.set_series(receiver_id, points)

    def set_playback_cursor(self, time_index: int | None) -> None:
        self.chart_widget.set_playback_cursor(time_index)
        if time_index is None:
            self.playback_cursor_label.setText('-')
            return
        if self.chart_widget.active_value_db is None:
            self.playback_cursor_label.setText(f't={time_index}')
            return
        self.playback_cursor_label.setText(f't={time_index}, {self.chart_widget.active_value_db:.1f} dB')

    def _emit_recent_result(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:  # noqa: ARG002
        if current is None:
            return
        result_path = current.data(Qt.UserRole)
        if result_path:
            self.recent_result_selected.emit(str(result_path))

    def _emit_selected_receiver(self) -> None:
        selected_items = self.receiver_table.selectedItems()
        if not selected_items:
            return
        self.receiver_selected.emit(selected_items[0].text())

    def _emit_combo_receiver(self, receiver_id: str) -> None:
        if receiver_id:
            self.receiver_selected.emit(receiver_id)
