"""Recommendations card routing to the anime detail page on click."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent

from ...models.anime import Anime, jpg_url_from_jikan
from ..signal_bus import signalBus
from .base_card import BaseCard


class RecommendationCard(BaseCard):
    def __init__(self, entry: dict, parent=None) -> None:
        if not isinstance(entry, dict):
            raise TypeError(f"Expected dict, got {type(entry).__name__}")
        anime = Anime(
            mal_id=entry.get("mal_id", 0),
            title=entry.get("title", ""),
            image_url=jpg_url_from_jikan(entry),
        )
        super().__init__(anime, content_h=195, card_w=130, parent=parent)

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if self.anime.mal_id and e.button() == Qt.MouseButton.LeftButton:
            signalBus.openAnimeDetail.emit(self.anime)
