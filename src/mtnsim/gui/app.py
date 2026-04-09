from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from mtnsim.gui.main_window import MainWindow


def _build_stylesheet() -> str:
    return """
    QWidget {
        background: #11161d;
        color: #e8edf5;
        font-size: 10.5pt;
    }
    QMainWindow, QDialog {
        background: #0d1218;
    }
    QToolBar {
        background: #151c24;
        border: none;
        border-bottom: 1px solid #243041;
        spacing: 8px;
        padding: 8px 12px;
    }
    QToolButton {
        background: transparent;
        color: #dbe7f5;
        border: 1px solid transparent;
        border-radius: 10px;
        padding: 7px 12px;
        margin: 0 2px;
    }
    QToolButton:hover {
        background: #1e2835;
        border: 1px solid #31455f;
    }
    QToolButton:pressed {
        background: #233246;
    }
    QToolButton:disabled {
        color: #66788c;
    }
    QPushButton {
        background: #18222e;
        color: #e8edf5;
        border: 1px solid #2d4157;
        border-radius: 10px;
        padding: 8px 12px;
        font-weight: 600;
    }
    QPushButton:hover {
        background: #223247;
        border-color: #3d5e80;
    }
    QPushButton:pressed {
        background: #2a425c;
    }
    QPushButton:checked {
        background: #204a6c;
        border-color: #4fb3ff;
        color: #f6fbff;
    }
    QPushButton:disabled {
        background: #131b24;
        color: #6b7785;
        border-color: #243041;
    }
    QDockWidget {
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
        font-weight: 700;
    }
    QDockWidget::title {
        text-align: left;
        background: #18212b;
        color: #f3f6fb;
        padding: 10px 12px;
        border-bottom: 1px solid #253446;
    }
    QListWidget, QTextEdit, QPlainTextEdit, QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {
        background: #151d26;
        color: #e8edf5;
        border: 1px solid #263547;
        border-radius: 10px;
        selection-background-color: #1d4d78;
        selection-color: #f6fbff;
        padding: 4px;
    }
    QListWidget#WorkspaceList::item {
        padding: 8px 10px;
        border-radius: 8px;
        margin: 2px 2px;
    }
    QListWidget#WorkspaceList::item:selected {
        background: #1c537d;
        color: #f6fbff;
    }
    QLabel {
        background: transparent;
    }
    QLabel#pageTitle {
        font-size: 24px;
        font-weight: 800;
        color: #f4f7fb;
        padding-bottom: 2px;
    }
    QLabel#sectionTitle {
        font-size: 14px;
        font-weight: 700;
        color: #c1d1e3;
        padding-top: 4px;
    }
    QLabel#panelTitle {
        font-size: 17px;
        font-weight: 800;
        color: #f4f7fb;
    }
    QLabel#shellSectionLabel {
        font-size: 10px;
        font-weight: 800;
        color: #7dbbe8;
        letter-spacing: 0.08em;
        padding-top: 4px;
    }
    QLabel#homeHelperLabel {
        color: #9db0c4;
        padding: 2px 0 6px 0;
    }
    QLabel#statusBadgeReady, QLabel#statusBadgeWarning, QLabel#statusBadgeNeutral {
        border-radius: 10px;
        padding: 6px 10px;
        font-weight: 700;
    }
    QLabel#statusBadgeReady {
        background: #153527;
        color: #79e2a7;
        border: 1px solid #25523b;
    }
    QLabel#statusBadgeWarning {
        background: #402513;
        color: #ffbf80;
        border: 1px solid #6a3b1d;
    }
    QLabel#statusBadgeNeutral {
        background: #1a2430;
        color: #b9c7d6;
        border: 1px solid #2a3b4f;
    }
    QWidget#infoCard, QFrame#infoCard, QFrame#viewerHeaderCard {
        background: #151d26;
        border: 1px solid #253446;
        border-radius: 14px;
    }
    QTextEdit#infoCard, QPlainTextEdit#infoCard, QListWidget#infoCard, QTableWidget#infoCard {
        background: #151d26;
        border: 1px solid #253446;
        border-radius: 14px;
    }
    QHeaderView::section {
        background: #18222e;
        color: #dbe7f5;
        border: none;
        border-right: 1px solid #2a3a4d;
        border-bottom: 1px solid #2a3a4d;
        padding: 7px 8px;
        font-weight: 700;
    }
    QTableWidget {
        background: #131b24;
        alternate-background-color: #18222d;
        border: 1px solid #253446;
        border-radius: 10px;
        gridline-color: #233243;
    }
    QTableWidget::item:selected {
        background: #1d4d78;
        color: #f6fbff;
    }
    QScrollBar:vertical, QScrollBar:horizontal {
        background: #111820;
        border-radius: 6px;
        margin: 2px;
    }
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
        background: #38506a;
        border-radius: 6px;
        min-height: 24px;
        min-width: 24px;
    }
    QStatusBar {
        background: #111820;
        color: #aab8c8;
        border-top: 1px solid #243041;
    }
    QSplitter::handle {
        background: #223041;
    }
    QSplitter::handle:horizontal {
        width: 10px;
        margin: 0 1px;
    }
    QSplitter::handle:vertical {
        height: 10px;
        margin: 1px 0;
    }
    QScrollArea#IntegratedViewerHeaderScroll, QScrollArea#ProjectHomeOverviewScroll {
        background: transparent;
        border: none;
    }
    QToolButton#ActionTile {
        background: #18222e;
        border: 1px solid #2d4157;
        border-radius: 12px;
        padding: 10px 8px;
        min-width: 78px;
        min-height: 58px;
    }
    QToolButton#ActionTile:hover {
        background: #223247;
        border-color: #3d5e80;
    }
    QToolButton#QuickRunButton {
        background: #1d6ea0;
        color: #f6fbff;
        border: 1px solid #3aa7ea;
        border-radius: 10px;
        padding: 8px 16px;
        font-weight: 700;
    }
    QPushButton#viewerTabButton {
        background: #18222e;
        border: 1px solid #2a3a4d;
        border-radius: 10px;
        padding: 8px 14px;
    }
    QPushButton#viewerTabButton:checked {
        background: #1e4b6d;
        border-color: #57b3ff;
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
