from __future__ import annotations

from loguru import logger
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QAction, QIcon, QKeySequence
from PyQt6.QtWidgets import QApplication, QLineEdit
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import (
    FluentWindow,
    InfoBar,
    InfoBarPosition,
    NavigationItemPosition,
)

from ..config.app_config import AppConfig
from ..models.anime import Anime, AnimeStatus
from .pages.about_page import AboutPage
from .pages.detail_page import DetailPage
from .pages.home_page import HomePage
from .pages.list_page import ListPage
from .pages.settings_page import SettingsPage
from .signal_bus import signalBus

_SETTINGS_KEY = "MainWindow"


def _toast(parent, title: str, content: str, error: bool = False) -> None:
    (InfoBar.error if error else InfoBar.success)(
        title=title,
        content=content,
        orient=Qt.Orientation.Horizontal,
        isClosable=True,
        position=InfoBarPosition.TOP_RIGHT,
        duration=2000,
        parent=parent,
    )


def _status_label(value: str) -> str:
    try:
        return AnimeStatus(value).label
    except ValueError:
        return value


class MainWindow(FluentWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(AppConfig.app_name())
        from pathlib import Path

        asset = str(Path(__file__).parent.parent / "assets" / "anitrack.png")
        self.setWindowIcon(QIcon(asset))
        self._restore_window_state()
        self.setMinimumSize(960, 600)

        self.homeInterface = HomePage(self)
        self.watchingInterface = ListPage(AnimeStatus.WATCHING, self)
        self.completedInterface = ListPage(AnimeStatus.COMPLETED, self)
        self.onHoldInterface = ListPage(AnimeStatus.ON_HOLD, self)
        self.droppedInterface = ListPage(AnimeStatus.DROPPED, self)
        self.planInterface = ListPage(AnimeStatus.PLAN, self)
        self.settingsInterface = SettingsPage(self)
        self.aboutInterface = AboutPage(self)
        self.initNavigation()

        self.detailInterface = DetailPage(self)
        self.stackedWidget.addWidget(self.detailInterface)
        self._previous_widget = None

        self._setup_shortcuts()

        signalBus.openAnimeDetail.connect(self._on_open_detail)
        signalBus.goBack.connect(self._on_go_back)
        signalBus.libraryAdded.connect(
            lambda a: _toast(self, "Added to library", a.title)
        )
        signalBus.libraryRemoved.connect(
            lambda a: _toast(self, "Removed from library", a.title)
        )
        signalBus.libraryStatusChanged.connect(
            lambda a, s: _toast(
                self,
                "Status updated",
                f"{a.title} \u2192 {_status_label(s)}",
            )
        )
        signalBus.libraryFavoriteToggled.connect(
            lambda a, v: _toast(self, "Favorited" if v else "Unfavorited", a.title)
        )

    def _restore_window_state(self) -> None:
        s = QSettings(_SETTINGS_KEY)
        geom = s.value("geometry")
        if geom is not None:
            self.restoreGeometry(geom)
        else:
            self.resize(1200, 760)

    def closeEvent(self, a0) -> None:
        s = QSettings(_SETTINGS_KEY)
        s.setValue("geometry", self.saveGeometry())
        super().closeEvent(a0)

    def _setup_shortcuts(self) -> None:
        s = QSettings("Shortcuts")
        default_esc = QKeySequence(QKeySequence.StandardKey.Cancel).toString()
        default_find = QKeySequence(QKeySequence.StandardKey.Find).toString()

        self._esc_action = QAction(self)
        self._esc_action.setShortcut(QKeySequence(s.value("goBack", default_esc)))
        self._esc_action.triggered.connect(self._handle_esc)
        self.addAction(self._esc_action)

        self._search_action = QAction(self)
        self._search_action.setShortcut(
            QKeySequence(s.value("focusSearch", default_find))
        )
        self._search_action.triggered.connect(self._focus_search)
        self.addAction(self._search_action)

        signalBus.shortcutsChanged.connect(self._reload_shortcuts)

    def _handle_esc(self) -> None:
        widget = QApplication.focusWidget()
        if isinstance(widget, QLineEdit) and widget.text():
            widget.clear()
            widget.clearFocus()
            return
        signalBus.goBack.emit()

    def _reload_shortcuts(self) -> None:
        s = QSettings("Shortcuts")
        self._esc_action.setShortcut(
            QKeySequence(
                s.value(
                    "goBack", QKeySequence(QKeySequence.StandardKey.Cancel).toString()
                )
            )
        )
        self._search_action.setShortcut(
            QKeySequence(
                s.value(
                    "focusSearch",
                    QKeySequence(QKeySequence.StandardKey.Find).toString(),
                )
            )
        )

    def _focus_search(self) -> None:
        current = self.stackedWidget.currentWidget()
        if hasattr(current, "searchEdit"):
            current.searchEdit.setFocus()
            current.searchEdit.selectAll()

    def initNavigation(self) -> None:
        self.addSubInterface(self.homeInterface, FIF.HOME, "Home")
        self.addSubInterface(self.watchingInterface, FIF.VIEW, "Watching")
        self.addSubInterface(self.completedInterface, FIF.COMPLETED, "Completed")
        self.addSubInterface(self.onHoldInterface, FIF.PAUSE, "On Hold")
        self.addSubInterface(self.droppedInterface, FIF.DELETE, "Dropped")
        self.addSubInterface(self.planInterface, FIF.CALENDAR, "Plan to Watch")
        self.navigationInterface.addSeparator()
        self.addSubInterface(
            self.settingsInterface,
            FIF.SETTING,
            "Settings",
            position=NavigationItemPosition.BOTTOM,
        )
        self.addSubInterface(
            self.aboutInterface,
            FIF.INFO,
            "About",
            position=NavigationItemPosition.BOTTOM,
        )
        self.navigationInterface.setCurrentItem(self.homeInterface.objectName())

    def _on_open_detail(self, anime: Anime) -> None:
        if not isinstance(anime, Anime):
            logger.warning("openAnimeDetail received non-Anime object")
            return
        if self.stackedWidget.currentWidget() != self.detailInterface:
            self._previous_widget = self.stackedWidget.currentWidget()
        self.detailInterface.load_anime(anime)
        self.stackedWidget.setCurrentWidget(self.detailInterface)

    def _on_go_back(self) -> None:
        if self._previous_widget is not None:
            self.stackedWidget.setCurrentWidget(self._previous_widget)
