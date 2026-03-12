from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mtnsim.schemas.results import ScenarioComparison


class ComparisonSeriesChart(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.series_a: list[tuple[int, float]] = []
        self.series_b: list[tuple[int, float]] = []
        self.label_a = 'Scenario A'
        self.label_b = 'Scenario B'
        self.receiver_id = '-'
        self.setMinimumHeight(260)

    def set_series(
        self,
        receiver_id: str,
        series_a: list[tuple[int, float]],
        series_b: list[tuple[int, float]],
        label_a: str,
        label_b: str,
    ) -> None:
        self.receiver_id = receiver_id
        self.series_a = series_a
        self.series_b = series_b
        self.label_a = label_a
        self.label_b = label_b
        self.update()

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
        painter.drawText(12, 18, f'Receiver Comparison: {self.receiver_id}')
        painter.drawRect(plot_rect)

        if not self.series_a and not self.series_b:
            painter.drawText(plot_rect.adjusted(8, 8, -8, -8), Qt.AlignCenter, 'No comparison receiver series loaded.')
            return

        xs = [point[0] for point in self.series_a + self.series_b]
        ys = [point[1] for point in self.series_a + self.series_b]
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

        self._draw_series(painter, plot_rect, self.series_a, min_x, max_x, min_y, max_y, QColor('#c2410c'))
        self._draw_series(painter, plot_rect, self.series_b, min_x, max_x, min_y, max_y, QColor('#0f766e'))

        legend_y = plot_rect.top() + 8
        painter.fillRect(plot_rect.right() - 180, legend_y, 10, 10, QColor('#c2410c'))
        painter.drawText(plot_rect.right() - 164, legend_y + 10, self.label_a)
        painter.fillRect(plot_rect.right() - 88, legend_y, 10, 10, QColor('#0f766e'))
        painter.drawText(plot_rect.right() - 72, legend_y + 10, self.label_b)

    def _draw_series(self, painter: QPainter, plot_rect, points, min_x, max_x, min_y, max_y, color: QColor) -> None:
        if len(points) < 2:
            return
        polyline = []
        for x, y in points:
            ratio_x = (x - min_x) / (max_x - min_x)
            ratio_y = (y - min_y) / (max_y - min_y)
            px = plot_rect.left() + (plot_rect.width() * ratio_x)
            py = plot_rect.bottom() - (plot_rect.height() * ratio_y)
            polyline.append((px, py))
        painter.setPen(QPen(color, 2))
        for index in range(len(polyline) - 1):
            painter.drawLine(int(polyline[index][0]), int(polyline[index][1]), int(polyline[index + 1][0]), int(polyline[index + 1][1]))


class ScenarioComparisonView(QWidget):
    compare_requested = Signal(str, str)
    run_compare_requested = Signal(str, str, bool)
    receiver_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel('Scenario Comparison')
        title.setStyleSheet('font-size: 22px; font-weight: 700;')
        root.addWidget(title)

        controls = QHBoxLayout()
        controls.setSpacing(10)
        controls.addWidget(QLabel('Scenario A'))
        self.scenario_a_combo = QComboBox()
        controls.addWidget(self.scenario_a_combo, 1)
        controls.addWidget(QLabel('Scenario B'))
        self.scenario_b_combo = QComboBox()
        controls.addWidget(self.scenario_b_combo, 1)
        self.use_gpu_check = QCheckBox('Use GPU')
        self.use_gpu_check.setChecked(True)
        controls.addWidget(self.use_gpu_check)
        self.compare_button = QPushButton('Compare Configs')
        self.compare_button.clicked.connect(self._emit_compare_request)
        controls.addWidget(self.compare_button)
        self.run_compare_button = QPushButton('Run and Compare')
        self.run_compare_button.clicked.connect(self._emit_run_compare_request)
        controls.addWidget(self.run_compare_button)
        root.addLayout(controls)

        self.status_label = QLabel('Select two scenarios to compare their configuration differences.')
        root.addWidget(self.status_label)

        splitter = QSplitter()
        root.addWidget(splitter, 1)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        summary_form = QFormLayout()
        self.project_label = QLabel('-')
        self.scenario_a_label = QLabel('-')
        self.scenario_b_label = QLabel('-')
        self.diff_count_label = QLabel('0')
        self.receiver_delta_count_label = QLabel('0')
        summary_form.addRow('Project', self.project_label)
        summary_form.addRow('Scenario A', self.scenario_a_label)
        summary_form.addRow('Scenario B', self.scenario_b_label)
        summary_form.addRow('Config Diffs', self.diff_count_label)
        summary_form.addRow('Receiver Deltas', self.receiver_delta_count_label)
        left_layout.addLayout(summary_form)

        self.summary_box = QTextEdit()
        self.summary_box.setReadOnly(True)
        self.summary_box.setMaximumHeight(120)
        left_layout.addWidget(self.summary_box)

        self.diff_table = QTableWidget(0, 3)
        self.diff_table.setHorizontalHeaderLabels(['Field', 'Scenario A', 'Scenario B'])
        self.diff_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.diff_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.diff_table.horizontalHeader().setStretchLastSection(True)
        left_layout.addWidget(self.diff_table, 1)

        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        self.delta_summary_box = QTextEdit()
        self.delta_summary_box.setReadOnly(True)
        self.delta_summary_box.setMaximumHeight(120)
        self.delta_summary_box.setPlaceholderText('Run-and-compare output will appear here.')
        right_layout.addWidget(self.delta_summary_box)

        self.receiver_delta_table = QTableWidget(0, 4)
        self.receiver_delta_table.setHorizontalHeaderLabels(['Receiver', 'Mean dB Δ', 'Min dB Δ', 'Max dB Δ'])
        self.receiver_delta_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.receiver_delta_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.receiver_delta_table.itemSelectionChanged.connect(self._emit_selected_receiver)
        right_layout.addWidget(self.receiver_delta_table, 1)

        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel('Receiver Overlay'))
        self.receiver_selector = QComboBox()
        self.receiver_selector.currentTextChanged.connect(self._emit_combo_receiver)
        selector_row.addWidget(self.receiver_selector, 1)
        right_layout.addLayout(selector_row)

        self.chart_widget = ComparisonSeriesChart()
        right_layout.addWidget(self.chart_widget, 2)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        self.set_comparison(None)
        self.set_run_comparison(None)

    def set_scenarios(self, scenario_paths: list[Path], selected_path: Path | None = None) -> None:
        items = [(path.stem, str(path)) for path in scenario_paths]
        previous_b = self.scenario_b_combo.currentData()
        self.scenario_a_combo.blockSignals(True)
        self.scenario_b_combo.blockSignals(True)
        self.scenario_a_combo.clear()
        self.scenario_b_combo.clear()
        for label, raw_path in items:
            self.scenario_a_combo.addItem(label, raw_path)
            self.scenario_b_combo.addItem(label, raw_path)
        if items:
            selected_index = 0
            if selected_path is not None:
                for index, (_, raw_path) in enumerate(items):
                    if Path(raw_path) == Path(selected_path):
                        selected_index = index
                        break
            self.scenario_a_combo.setCurrentIndex(selected_index)
            compare_index = 1 if len(items) > 1 and selected_index == 0 else 0
            if previous_b:
                for index, (_, raw_path) in enumerate(items):
                    if raw_path == previous_b and index != selected_index:
                        compare_index = index
                        break
            if compare_index == selected_index and len(items) > 1:
                compare_index = (selected_index + 1) % len(items)
            self.scenario_b_combo.setCurrentIndex(compare_index)
        self.scenario_a_combo.blockSignals(False)
        self.scenario_b_combo.blockSignals(False)
        enabled = len(items) >= 2
        self.compare_button.setEnabled(enabled)
        self.run_compare_button.setEnabled(enabled)

    def current_selection(self) -> tuple[str | None, str | None]:
        return self.scenario_a_combo.currentData(), self.scenario_b_combo.currentData()

    def set_selected_pair(self, scenario_a_path: str | Path, scenario_b_path: str | Path) -> None:
        target_a = str(scenario_a_path)
        target_b = str(scenario_b_path)
        for combo, target in ((self.scenario_a_combo, target_a), (self.scenario_b_combo, target_b)):
            for index in range(combo.count()):
                if combo.itemData(index) == target:
                    combo.setCurrentIndex(index)
                    break

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_comparison(self, comparison: ScenarioComparison | None) -> None:
        if comparison is None:
            self.project_label.setText('-')
            self.scenario_a_label.setText('-')
            self.scenario_b_label.setText('-')
            self.diff_count_label.setText('0')
            self.summary_box.setPlainText('Select two scenarios to compare their configuration differences.')
            self.diff_table.setRowCount(0)
            return
        self.project_label.setText(comparison.project)
        self.scenario_a_label.setText(comparison.scenario_a)
        self.scenario_b_label.setText(comparison.scenario_b)
        self.diff_count_label.setText(str(len(comparison.differing_fields)))
        summary_lines = [
            f'Compared {comparison.scenario_a} against {comparison.scenario_b}.',
            f'Found {len(comparison.differing_fields)} differing configuration fields.',
        ]
        preview_items = list(comparison.differing_fields.items())[:5]
        if preview_items:
            summary_lines.append('Top differences:')
            for field, values in preview_items:
                summary_lines.append(f"- {field}: {self._stringify(values.get('scenario_a'))} -> {self._stringify(values.get('scenario_b'))}")
        self.summary_box.setPlainText('\n'.join(summary_lines))
        self.diff_table.setRowCount(len(comparison.differing_fields))
        for row, (field, values) in enumerate(comparison.differing_fields.items()):
            self.diff_table.setItem(row, 0, QTableWidgetItem(field))
            self.diff_table.setItem(row, 1, QTableWidgetItem(self._stringify(values.get('scenario_a'))))
            self.diff_table.setItem(row, 2, QTableWidgetItem(self._stringify(values.get('scenario_b'))))
        self.diff_table.resizeColumnsToContents()

    def set_run_comparison(self, comparison_payload: dict | None) -> None:
        if comparison_payload is None:
            self.receiver_delta_count_label.setText('0')
            self.delta_summary_box.setPlainText('Run-and-compare output will appear here.')
            self.receiver_delta_table.setRowCount(0)
            self.receiver_selector.clear()
            self.chart_widget.set_series('-', [], [], 'Scenario A', 'Scenario B')
            return
        comparison = comparison_payload['comparison']
        receiver_deltas = comparison['receiver_deltas']
        self.receiver_delta_count_label.setText(str(len(receiver_deltas)))
        summary = comparison['summary']
        lines = [
            f"Run A: {comparison_payload['artifacts_a']['run_id']}",
            f"Run B: {comparison_payload['artifacts_b']['run_id']}",
            f"Mean of mean dB deltas: {summary.get('mean_of_mean_db_deltas', 0.0):.2f}",
        ]
        if summary.get('largest_mean_db_decrease_receiver'):
            item = summary['largest_mean_db_decrease_receiver']
            lines.append(f"Largest decrease: {item['receiver_id']} ({item['mean_db_delta']:.2f} dB)")
        if summary.get('largest_mean_db_increase_receiver'):
            item = summary['largest_mean_db_increase_receiver']
            lines.append(f"Largest increase: {item['receiver_id']} ({item['mean_db_delta']:.2f} dB)")
        self.delta_summary_box.setPlainText('\n'.join(lines))

        receiver_ids = sorted(receiver_deltas.keys())
        self.receiver_delta_table.setRowCount(len(receiver_ids))
        self.receiver_selector.blockSignals(True)
        self.receiver_selector.clear()
        for row, receiver_id in enumerate(receiver_ids):
            delta = receiver_deltas[receiver_id]
            self.receiver_delta_table.setItem(row, 0, QTableWidgetItem(receiver_id))
            self.receiver_delta_table.setItem(row, 1, QTableWidgetItem(f"{delta['mean_db_delta']:.2f}"))
            self.receiver_delta_table.setItem(row, 2, QTableWidgetItem(f"{delta['min_db_delta']:.2f}"))
            self.receiver_delta_table.setItem(row, 3, QTableWidgetItem(f"{delta['max_db_delta']:.2f}"))
            self.receiver_selector.addItem(receiver_id)
        self.receiver_selector.blockSignals(False)
        self.receiver_delta_table.resizeColumnsToContents()
        if receiver_ids:
            self.receiver_selector.setCurrentIndex(0)

    def set_receiver_overlay(self, receiver_id: str, series_a, series_b, label_a: str, label_b: str) -> None:
        self.chart_widget.set_series(receiver_id, series_a, series_b, label_a, label_b)

    def _emit_compare_request(self) -> None:
        path_a, path_b = self.current_selection()
        if path_a and path_b:
            self.compare_requested.emit(str(path_a), str(path_b))

    def _emit_run_compare_request(self) -> None:
        path_a, path_b = self.current_selection()
        if path_a and path_b:
            self.run_compare_requested.emit(str(path_a), str(path_b), self.use_gpu_check.isChecked())

    def _emit_selected_receiver(self) -> None:
        selected_items = self.receiver_delta_table.selectedItems()
        if selected_items:
            self.receiver_selected.emit(selected_items[0].text())

    def _emit_combo_receiver(self, receiver_id: str) -> None:
        if receiver_id:
            self.receiver_selected.emit(receiver_id)

    def _stringify(self, value) -> str:
        if value is None:
            return '-'
        text = str(value)
        return text if len(text) <= 120 else text[:117] + '...'
