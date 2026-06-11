from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QWidget

from ...config.app_config import AppConfig
from ...models.anime import Anime
from ..signal_bus import signalBus
from .base_card import BaseCard


class RecommendationCard(BaseCard):
    def __init__(self, entry: dict, parent: QWidget | None = None) -> None:
        if not isinstance(entry, dict):
            raise TypeError(f"Expected dict, got {type(entry).__name__}")
        jpg = (entry.get("images") or {}).get("jpg") or {}
        anime = Anime(
            mal_id=entry.get("mal_id", 0),
            title=entry.get("title", ""),
            image_url=jpg.get("large_image_url") or jpg.get("image_url", ""),
        )
        super().__init__(
            anime,
            content_h=AppConfig.small_card_h(),
            card_w=AppConfig.small_card_w(),
            parent=parent,
        )

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if self.anime.mal_id and e.button() == Qt.MouseButton.LeftButton:
            signalBus.openAnimeDetail.emit(self.anime)
