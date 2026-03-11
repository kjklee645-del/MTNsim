from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from mtnsim.gui.main_window import MainWindow


def create_application(argv: list[str] | None = None) -> QApplication:
    app = QApplication(argv or sys.argv)
    app.setApplicationName('MTNsim GUI')
    app.setOrganizationName('MTNsim')
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
