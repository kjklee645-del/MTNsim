from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class CampaignValidationView(QWidget):
    open_campaign_requested = Signal()
    inspect_requested = Signal(str)
    validate_requested = Signal(str, str, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel('Campaign Validation')
        title.setStyleSheet('font-size: 22px; font-weight: 700;')
        root.addWidget(title)

        controls = QHBoxLayout()
        self.open_button = QPushButton('Open Campaign')
        self.open_button.clicked.connect(self.open_campaign_requested.emit)
        controls.addWidget(self.open_button)
        self.inspect_button = QPushButton('Inspect Campaign')
        self.inspect_button.clicked.connect(self._emit_inspect)
        self.inspect_button.setEnabled(False)
        controls.addWidget(self.inspect_button)
        self.validate_button = QPushButton('Validate Campaign')
        self.validate_button.clicked.connect(self._emit_validate)
        self.validate_button.setEnabled(False)
        controls.addWidget(self.validate_button)
        controls.addWidget(QLabel('Scenario Override'))
        self.scenario_combo = QComboBox()
        self.scenario_combo.addItem('Auto from Campaign / Project', '')
        controls.addWidget(self.scenario_combo, 1)
        self.use_gpu_check = QCheckBox('Use GPU')
        self.use_gpu_check.setChecked(True)
        controls.addWidget(self.use_gpu_check)
        root.addLayout(controls)

        self.status_label = QLabel('Open a campaign manifest to inspect or validate it.')
        root.addWidget(self.status_label)

        summary_form = QFormLayout()
        self.campaign_file_label = QLabel('-')
        self.campaign_id_label = QLabel('-')
        self.scenario_label = QLabel('-')
        self.acceptance_label = QLabel('-')
        self.output_dir_label = QLabel('-')
        summary_form.addRow('Campaign File', self.campaign_file_label)
        summary_form.addRow('Campaign ID', self.campaign_id_label)
        summary_form.addRow('Scenario', self.scenario_label)
        summary_form.addRow('Acceptance', self.acceptance_label)
        summary_form.addRow('Output Dir', self.output_dir_label)
        root.addLayout(summary_form)

        self.summary_box = QTextEdit()
        self.summary_box.setReadOnly(True)
        self.summary_box.setMaximumHeight(180)
        root.addWidget(self.summary_box)

        self.threshold_table = QTableWidget(0, 3)
        self.threshold_table.setHorizontalHeaderLabels(['Check', 'Passed', 'Details'])
        self.threshold_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.threshold_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.threshold_table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.threshold_table, 1)

        self.recommendation_box = QTextEdit()
        self.recommendation_box.setReadOnly(True)
        self.recommendation_box.setPlaceholderText('Recommendations and next actions will appear here.')
        root.addWidget(self.recommendation_box, 1)

    def set_campaign(self, campaign_path: Path, campaign_manifest, scenario_paths: list[Path]) -> None:
        self.campaign_file_label.setText(str(campaign_path))
        self.campaign_id_label.setText(campaign_manifest.campaign_id)
        self.scenario_label.setText(str(campaign_manifest.scenario_file or '-'))
        self.acceptance_label.setText('-')
        self.output_dir_label.setText('-')
        self.summary_box.setPlainText(campaign_manifest.description or 'No campaign description provided.')
        self.recommendation_box.clear()
        self.threshold_table.setRowCount(0)
        self.status_label.setText('Campaign loaded. You can inspect or validate it.')
        self.inspect_button.setEnabled(True)
        self.validate_button.setEnabled(True)
        self.scenario_combo.blockSignals(True)
        self.scenario_combo.clear()
        self.scenario_combo.addItem('Auto from Campaign / Project', '')
        for scenario_path in scenario_paths:
            self.scenario_combo.addItem(scenario_path.stem, str(scenario_path))
        self.scenario_combo.blockSignals(False)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_inspection_result(self, payload: dict) -> None:
        summary = payload['summary']
        self.acceptance_label.setText('inspect ok' if summary.get('passed') else 'inspect failed')
        self.output_dir_label.setText(payload.get('output_dir', '-'))
        checks = summary.get('checks', [])
        self.summary_box.setPlainText(
            '\n'.join([
                f"Inspection passed: {summary.get('passed')}",
                f"Measurement rows: {summary.get('measurement_row_count')}",
                f"Measurement sensors: {summary.get('measurement_sensor_count')}",
                f"Metadata sensors: {summary.get('metadata_sensor_count')}",
                f"Traffic rows: {summary.get('traffic_row_count')}",
                f"Summary file: {payload.get('summary_file')}",
                f"Report file: {payload.get('report_file')}",
            ])
        )
        self._populate_checks(checks)
        issues = [f"- [{item.get('severity')}] {item.get('check_id')}: {item.get('message')}" for item in checks if not item.get('passed')]
        self.recommendation_box.setPlainText('\n'.join(issues) if issues else 'No inspection issues were reported.')

    def set_validation_result(self, payload: dict) -> None:
        summary = payload['summary']
        self.acceptance_label.setText(str(summary.get('acceptance_status', '-')))
        report_lines = [
            f"Validation passed: {summary.get('validation_passed')}",
            f"Acceptance status: {summary.get('acceptance_status')}",
            f"Overall RMSE: {summary.get('overall_rmse_db')}",
            f"Overall mean bias: {summary.get('overall_mean_bias_db')}",
            f"Coverage ratio: {summary.get('coverage_ratio')}",
            f"Worst receiver: {summary.get('worst_receiver_id')}",
            f"Result summary: {payload.get('result_summary_file')}",
            f"Calibration summary: {payload.get('calibration_summary_file')}",
            f"Validation summary: {payload.get('summary_file')}",
            f"Validation report: {payload.get('report_file')}",
        ]
        self.summary_box.setPlainText('\n'.join(report_lines))
        checks = []
        for check_id, item in (summary.get('threshold_checks') or {}).items():
            checks.append({'check_id': check_id, 'passed': item.get('passed', False), 'details': item})
        self._populate_checks(checks)
        rec_lines = []
        for item in summary.get('recommended_next_actions') or []:
            rec_lines.append(f'- {item}')
        calibration_recommendations = summary.get('calibration_recommendations') or []
        if calibration_recommendations:
            rec_lines.append('')
            rec_lines.append('Calibration recommendations:')
            for item in calibration_recommendations[:10]:
                rec_lines.append(f"- [{item.get('priority')}] {item.get('kind')} -> {item.get('target')} ({item.get('value')})")
        self.recommendation_box.setPlainText('\n'.join(rec_lines) if rec_lines else 'No follow-up recommendations were generated.')

    def _populate_checks(self, checks: list[dict]) -> None:
        self.threshold_table.setRowCount(len(checks))
        for row, item in enumerate(checks):
            self.threshold_table.setItem(row, 0, QTableWidgetItem(str(item.get('check_id', '-'))))
            self.threshold_table.setItem(row, 1, QTableWidgetItem('yes' if item.get('passed') else 'no'))
            details = item.get('details')
            self.threshold_table.setItem(row, 2, QTableWidgetItem(str(details if details is not None else item.get('message', '-'))))
        self.threshold_table.resizeColumnsToContents()

    def _emit_inspect(self) -> None:
        campaign_file = self.campaign_file_label.text()
        if campaign_file and campaign_file != '-':
            self.inspect_requested.emit(campaign_file)

    def _emit_validate(self) -> None:
        campaign_file = self.campaign_file_label.text()
        if campaign_file and campaign_file != '-':
            self.validate_requested.emit(campaign_file, self.scenario_combo.currentData() or '', self.use_gpu_check.isChecked())
