from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from mtnsim.gui.main_window import MainWindow


def _build_stylesheet() -> str:
    return """
    QWidget {
        background: #f7f1e7;
        color: #1f2937;
        font-size: 10.5pt;
    }
    QMainWindow, QDialog {
        background: #f3ede2;
    }
    QToolBar {
        background: #ede4d6;
        border: none;
        border-bottom: 1px solid #d7ccb8;
        spacing: 8px;
        padding: 8px;
    }
    QToolButton {
        background: transparent;
        border: 1px solid transparent;
        border-radius: 8px;
        padding: 7px 10px;
        margin: 0 2px;
    }
    QToolButton:hover {
        background: #fff8ee;
        border: 1px solid #d8cbb4;
    }
    QToolButton:pressed {
        background: #e3d7c5;
    }
    QToolButton:disabled {
        color: #9ca3af;
    }
    QDockWidget {
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
        font-weight: 600;
    }
    QDockWidget::title {
        text-align: left;
        background: #e7ddcf;
        padding: 8px 10px;
        border-bottom: 1px solid #d7ccb8;
    }
    QListWidget, QTextEdit, QPlainTextEdit, QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {
        background: #fffaf2;
        border: 1px solid #d8cbb4;
        border-radius: 8px;
        selection-background-color: #d7e6f8;
        selection-color: #10263d;
        padding: 4px;
    }
    QListWidget::item {
        padding: 6px 8px;
        border-radius: 6px;
        margin: 1px 2px;
    }
    QListWidget::item:selected {
        background: #dbeafe;
        color: #10263d;
    }
    QPushButton {
        background: #fff8ee;
        border: 1px solid #d8cbb4;
        border-radius: 8px;
        padding: 7px 12px;
        font-weight: 600;
    }
    QPushButton:hover {
        background: #fffdf8;
        border-color: #c7b79d;
    }
    QPushButton:pressed {
        background: #e7ddcf;
    }
    QPushButton:disabled {
        background: #efe7db;
        color: #9ca3af;
        border-color: #ddd2c0;
    }
    QLabel {
        background: transparent;
    }
    QGroupBox {
        background: #f9f4eb;
        border: 1px solid #d8cbb4;
        border-radius: 10px;
        margin-top: 10px;
        padding-top: 12px;
        font-weight: 700;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 4px;
        color: #374151;
    }
    QHeaderView::section {
        background: #eadfcf;
        color: #374151;
        border: none;
        border-right: 1px solid #d7ccb8;
        border-bottom: 1px solid #d7ccb8;
        padding: 6px 8px;
        font-weight: 700;
    }
    QTableWidget {
        background: #fffaf2;
        alternate-background-color: #f7f1e7;
        border: 1px solid #d8cbb4;
        border-radius: 8px;
        gridline-color: #e7ddcf;
    }
    QTableWidget::item:selected {
        background: #dbeafe;
        color: #10263d;
    }
    QScrollBar:vertical, QScrollBar:horizontal {
        background: #efe7db;
        border-radius: 6px;
        margin: 2px;
    }
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
        background: #cabaa1;
        border-radius: 6px;
        min-height: 24px;
        min-width: 24px;
    }
    QStatusBar {
        background: #ede4d6;
        border-top: 1px solid #d7ccb8;
    }
    QSplitter::handle {
        background: #d8cbb4;
    }
    """


def create_application(argv: list[str] | None = None) -> QApplication:
    app = QApplication(argv or sys.argv)
    app.setApplicationName('MTNsim GUI')
    app.setOrganizationName('MTNsim')
    app.setStyle('Fusion')
    app.setFont(QFont('Segoe UI', 10))
    app.setStyleSheet(_build_stylesheet())
    return app


def create_main_window(manifest_path: str | Path | None = None) -> MainWindow:
    return MainWindow(manifest_path=manifest_path)


def launch_gui(manifest_path: str | Path | None = None) -> int:
    app = QApplication.instance() or create_application()
    window = create_main_window(manifest_path)
    window.show()
    return app.exec()


def main() -> None:
    manifest_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
    raise SystemExit(launch_gui(manifest_path))
