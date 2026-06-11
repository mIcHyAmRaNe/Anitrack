"""Headless smoke test: import the app, build the window, quit after 800ms.

Verifies that all modules import, the window builds, and the event loop
runs without exceptions. Does NOT hit the network.
"""

from __future__ import annotations

import os
import sys
import traceback

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from qfluentwidgets import FluentTranslator

from app.config.settings import cfg
from app.theme.theme import Flavor, init_theme
from app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("anitrack")
    app.setOrganizationName("anitrack")
    app.installTranslator(FluentTranslator())

    try:
        flavor = Flavor(cfg.get(cfg.themeMode))
    except ValueError:
        flavor = Flavor.MOCHA
    init_theme(flavor)

    window = MainWindow()
    window.show()
    QTimer.singleShot(800, app.quit)
    rc = app.exec()
    print(f"event loop exited with code {rc}")
    return rc


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(2)
