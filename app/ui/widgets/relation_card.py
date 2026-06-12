"""Relations card opening MAL page on click."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QMouseEvent

from ...models.anime import Anime, jpg_url_from_jikan
from .base_card import BaseCard


class RelationCard(BaseCard):
    def __init__(self, entry: dict, relation_type: str, parent=None) -> None:
        if not isinstance(entry, dict):
            raise TypeError(f"Expected dict, got {type(entry).__name__}")
        if not isinstance(relation_type, str):
            raise TypeError(f"Expected str, got {type(relation_type).__name__}")
        name = entry.get("name", "")
        title = f"{relation_type}: {name}" if relation_type else name
        anime = Anime(
            mal_id=entry.get("mal_id", 0),
            title=title,
            image_url=jpg_url_from_jikan(entry),
        )
        super().__init__(anime, content_h=195, card_w=130, parent=parent)
        self._page_url = entry.get("url", "")

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if self._page_url and e.button() == Qt.MouseButton.LeftButton:
            QDesktopServices.openUrl(QUrl(self._page_url))
