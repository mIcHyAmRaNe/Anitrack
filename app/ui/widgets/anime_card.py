from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QContextMenuEvent, QDesktopServices, QMouseEvent
from PyQt6.QtWidgets import QLabel, QWidget
from qfluentwidgets import Action, RoundMenu, ToolButton
from qfluentwidgets import FluentIcon as FIF

from ...config.app_config import AppConfig
from ...models.anime import Anime
from ...models.library import get_library
from ..signal_bus import signalBus
from .base_card import BaseCard


class _HeartMenuForwarder(QObject):
    def __init__(self, card: AnimeCard, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._card = card

    def eventFilter(self, a0: QObject | None, a1: QEvent | None) -> bool:
        if a1 is not None and a1.type() == QEvent.Type.ContextMenu:
            self._card.contextMenuEvent(a1)
            return True
        return False


class AnimeCard(BaseCard):
    favoriteToggled = pyqtSignal(object, bool)
    selectionToggled = pyqtSignal(object, bool)
    selectRequested = pyqtSignal(object)

    def __init__(self, anime: Anime, parent: QWidget | None = None) -> None:
        if not isinstance(anime, Anime):
            raise TypeError(f"Expected Anime, got {type(anime).__name__}")
        super().__init__(anime, content_h=AppConfig.card_cover_h(), parent=parent)

        self._selection_mode = False
        self._selectable = False

        cover_w = AppConfig.card_cover_w()
        hb = AppConfig.get("ui", "sizes", "heart_button")

        self.heart_btn = ToolButton(self.cover_label)
        self.heart_btn.setFixedSize(hb, hb)
        self.heart_btn.move(
            cover_w - AppConfig.heart_offset_x(), AppConfig.heart_offset_y()
        )
        self.heart_btn.setIcon(FIF.HEART.icon())
        self.heart_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.heart_btn.clicked.connect(self._on_heart_clicked)
        self.heart_btn.installEventFilter(_HeartMenuForwarder(self, self.heart_btn))

        sb = AppConfig.get("ui", "sizes", "select_box")
        self.select_box = QLabel(self.cover_label)
        self.select_box.setFixedSize(sb, sb)
        self.select_box.move(AppConfig.select_offset_x(), AppConfig.select_offset_y())
        self.select_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.select_box.setStyleSheet(
            f"font-size: {AppConfig.get('ui', 'font', 'sizes', 'xl')}px;"
        )
        self.select_box.hide()

    def set_selection_mode(self, enabled: bool) -> None:
        self._selection_mode = enabled
        self.select_box.setVisible(enabled)
        if not enabled:
            self.set_selected(False)
        self.update_status_badge()

    def set_selected(self, selected: bool) -> None:
        super().set_selected(selected)
        self.select_box.setText("\u2612" if selected else "\u2610")

    def set_selectable(self, value: bool) -> None:
        self._selectable = value

    def set_favorite(self, value: bool) -> None:
        self.anime.favorite = value
        self.heart_btn.setIcon(FIF.HEART.icon())

    def refresh_theme(self) -> None:
        super().refresh_theme()
        self.heart_btn.setIcon(FIF.HEART.icon())

    def update_status_badge(self) -> None:
        if getattr(self, "_selection_mode", False):
            self.status_badge.hide()
        else:
            super().update_status_badge()

    def _on_heart_clicked(self) -> None:
        new_value = not self.anime.favorite
        self.set_favorite(new_value)
        self.favoriteToggled.emit(self.anime, new_value)

    def _remove_from_library(self) -> None:
        get_library().remove(self.anime.mal_id)
        signalBus.libraryRemoved.emit(self.anime)
        signalBus.libraryChanged.emit()

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if self.heart_btn.underMouse():
            super().mousePressEvent(e)
            return
        if self._selection_mode and e.button() == Qt.MouseButton.LeftButton:
            self.set_selected(not self.is_selected())
            self.selectionToggled.emit(self.anime, self.is_selected())
            return
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if self.heart_btn.underMouse() or self._selection_mode:
            return
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.anime)

    def contextMenuEvent(self, a0: QContextMenuEvent | None) -> None:
        if a0 is None:
            return
        menu = RoundMenu(parent=self)
        menu.addAction(
            Action(FIF.INFO, "Open", triggered=lambda: self.clicked.emit(self.anime))
        )
        menu.addAction(
            Action(
                FIF.GLOBE,
                "Open in browser",
                triggered=lambda: QDesktopServices.openUrl(
                    QUrl(f"https://myanimelist.net/anime/{self.anime.mal_id}")
                ),
            )
        )
        if get_library().get(self.anime.mal_id):
            menu.addSeparator()
            menu.addAction(
                Action(
                    FIF.DELETE,
                    "Remove from library",
                    triggered=self._remove_from_library,
                )
            )
        menu.addSeparator()
        menu.addAction(
            Action(
                FIF.HEART,
                "Remove from favorites" if self.anime.favorite else "Add to favorites",
                triggered=self._on_heart_clicked,
            )
        )
        if self._selectable:
            menu.addSeparator()
            menu.addAction(
                Action(
                    FIF.CHECKBOX,
                    "Select",
                    triggered=lambda: self.selectRequested.emit(self.anime),
                )
            )
        menu.exec(a0.globalPos())
