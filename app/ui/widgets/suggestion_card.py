from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QWidget

from ...models.anime import Anime
from ..signal_bus import signalBus
from .base_card import BaseCard


class SuggestionCard(BaseCard):
    def __init__(self, anime: Anime, parent: QWidget | None = None) -> None:
        if not isinstance(anime, Anime):
            raise TypeError(f"Expected Anime, got {type(anime).__name__}")
        super().__init__(anime, content_h=283, parent=parent)
        signalBus.libraryChanged.connect(self.update_status_badge)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.anime)
