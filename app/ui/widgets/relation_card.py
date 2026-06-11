from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QMouseEvent
from PyQt6.QtWidgets import QWidget

from ...config.app_config import AppConfig
from ...models.anime import Anime
from .base_card import BaseCard


class RelationCard(BaseCard):
    def __init__(
        self, entry: dict, relation_type: str, parent: QWidget | None = None
    ) -> None:
        if not isinstance(entry, dict):
            raise TypeError(f"Expected dict, got {type(entry).__name__}")
        if not isinstance(relation_type, str):
            raise TypeError(f"Expected str, got {type(relation_type).__name__}")
        name = entry.get("name", "")
        title = f"{relation_type}: {name}" if relation_type else name
        jpg = (entry.get("images") or {}).get("jpg") or {}
        anime = Anime(
            mal_id=entry.get("mal_id", 0),
            title=title,
            image_url=jpg.get("large_image_url") or jpg.get("image_url", ""),
        )
        super().__init__(
            anime,
            content_h=AppConfig.small_card_h(),
            card_w=AppConfig.small_card_w(),
            parent=parent,
        )
        self._page_url = entry.get("url", "")

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if self._page_url and e.button() == Qt.MouseButton.LeftButton:
            QDesktopServices.openUrl(QUrl(self._page_url))
