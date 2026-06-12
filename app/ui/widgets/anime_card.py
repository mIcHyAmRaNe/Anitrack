"""Anime card with selection modes, favorite toggle, and context menu."""

from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QContextMenuEvent, QDesktopServices, QMouseEvent
from PyQt6.QtWidgets import QLabel
from qfluentwidgets import Action, RoundMenu, ToolButton
from qfluentwidgets import FluentIcon as FIF

from ...models.anime import Anime
from ...models.library import get_library
from ..signal_bus import signalBus
from .base_card import BaseCard

SELECTED_GLYPH = "\u2612"  # ☒
UNSELECTED_GLYPH = "\u2610"  # ☐


class _HeartMenuForwarder(QObject):
    """Forward right-clicks on the heart button to the parent card's menu."""

    def __init__(self, card: "AnimeCard", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._card = card

    def eventFilter(self, a0: QObject | None, a1: QEvent | None) -> bool:
        if a1 is not None and a1.type() == QEvent.Type.MouseButtonPress:
            mouse_event = a1
            if mouse_event.button() == Qt.MouseButton.RightButton:
                pos = a0.mapTo(self._card, mouse_event.position().toPoint())
                wrapped = QContextMenuEvent(
                    QContextMenuEvent.Reason.Mouse,
                    pos,
                    mouse_event.globalPosition().toPoint(),
                )
                self._card.contextMenuEvent(wrapped)
                return True
        return False


class AnimeCard(BaseCard):
    favoriteToggled = pyqtSignal(object, bool)
    selectionToggled = pyqtSignal(object, bool)
    selectRequested = pyqtSignal(object)

    def __init__(self, anime: Anime, parent=None) -> None:
        if not isinstance(anime, Anime):
            raise TypeError(f"Expected Anime, got {type(anime).__name__}")
        # Initialise before super().__init__ runs update_status_badge via BaseCard.
        self._selection_mode = False
        self._selectable = False
        super().__init__(anime, content_h=283, parent=parent)

        self.heart_btn = ToolButton(self.cover_label)
        self.heart_btn.setFixedSize(32, 32)
        self.heart_btn.move(self.CARD_W - 38, 6)
        self.heart_btn.setIcon(FIF.HEART.icon())
        self.heart_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.heart_btn.clicked.connect(self._on_heart_clicked)
        self.heart_btn.installEventFilter(_HeartMenuForwarder(self, self.heart_btn))

        self.select_box = QLabel(self.cover_label)
        self.select_box.setFixedSize(28, 28)
        self.select_box.move(6, 6)
        self.select_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.select_box.hide()

    def set_selection_mode(self, enabled: bool) -> None:
        self._selection_mode = enabled
        self.select_box.setVisible(enabled)
        if not enabled:
            self.set_selected(False)
        self.update_status_badge()

    def set_selected(self, selected: bool) -> None:
        super().set_selected(selected)
        self.select_box.setText(SELECTED_GLYPH if selected else UNSELECTED_GLYPH)

    def set_selectable(self, value: bool) -> None:
        self._selectable = value

    def set_favorite(self, value: bool) -> None:
        self.anime.favorite = value
        self.heart_btn.setIcon(FIF.HEART.icon())

    def update_status_badge(self) -> None:
        if self._selection_mode:
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
        mal_url = f"https://myanimelist.net/anime/{self.anime.mal_id}"
        menu.addAction(
            Action(
                FIF.GLOBE,
                "Open in browser",
                triggered=lambda: QDesktopServices.openUrl(QUrl(mal_url)),
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
