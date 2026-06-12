from __future__ import annotations

import signal
import sys
import traceback

from loguru import logger
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication
from qfluentwidgets import FluentTranslator

from .config.app_config import AppConfig
from .config.settings import current_flavor
from .theme.theme import Flavor, init_theme
from .ui.main_window import MainWindow


def _excepthook(exc_type, exc_value, exc_tb) -> None:
    logger.critical(
        "Unhandled exception:\n{}",
        "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
    )


class _Application(QApplication):
    def notify(self, a0, a1) -> bool:
        try:
            return super().notify(a0, a1)
        except Exception:
            logger.critical(
                "Unhandled Qt exception in {}:{}",
                type(a0).__name__,
                a1.type(),  # type: ignore[union-attr]
            )
            traceback.print_exc()
            return False


def main() -> int:
    sys.excepthook = _excepthook
    AppConfig.load()

    logger.remove()
    if sys.stderr is not None:
        logger.add(
            sys.stderr,
            format="<level>{level:7}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True,
            level="DEBUG",
        )
    log_dir = AppConfig.logs_dir()
    log_file = log_dir / "anitrack.log"
    logger.add(
        str(log_file),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:7} | {name}:{line} - {message}",
        level="ERROR",
        rotation="10 MB",
        retention=3,
    )
    logger.info("Starting {}", AppConfig.app_name())

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = _Application(sys.argv)
    app.setApplicationName(AppConfig.app_name())
    app.setOrganizationName(AppConfig.app_name().lower())
    app.installTranslator(FluentTranslator())
    app.setFont(QFont(AppConfig.font_family(), AppConfig.font_size()))

    try:
        flavor = current_flavor()
    except ValueError:
        logger.warning("Invalid theme in config, falling back to FRAPPE")
        flavor = Flavor.FRAPPE
    init_theme(flavor)
    logger.info("Initial theme: {}", flavor.value)

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    window = MainWindow()
    window.show()
    ret = app.exec()
    logger.info("Shutting down")
    return ret


if __name__ == "__main__":
    raise SystemExit(main())
