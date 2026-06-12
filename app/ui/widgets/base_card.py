"""Shared base for image-bearing anime cards."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget
from qfluentwidgets import ElevatedCardWidget, InfoBadge

from ...models.anime import (
    STATUS_FLUENT_ICONS,
    Anime,
    AnimeStatus,
)
from ...models.library import get_library
from ...services.image_cache import (
    image_loader,
    placeholder_pixmap,
    rounded_pixmap,
)


class BaseCard(ElevatedCardWidget):
    clicked = pyqtSignal(object)

    CARD_W = 210
    CARD_H = 283

    def __init__(
        self,
        anime: Anime,
        content_h: int,
        card_w: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        if not isinstance(anime, Anime):
            raise TypeError(f"Expected Anime, got {type(anime).__name__}")
        if content_h <= 0:
            raise ValueError(f"content_h must be positive, got {content_h}")

        super().__init__(parent)
        self.anime = anime
        self._w = card_w if card_w is not None else self.CARD_W
        self._h = content_h
        self._is_selected = False

        self.setFixedSize(self._w, self._h)
        self.setBorderRadius(10)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.cover_label = QLabel(self)
        self.cover_label.setFixedSize(self._w, self._h)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setPixmap(
            rounded_pixmap(placeholder_pixmap(self._w, self._h), 10)
        )

        self.title = InfoBadge.custom(
            "", Qt.GlobalColor.transparent, Qt.GlobalColor.transparent
        )
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.title.setWordWrap(True)
        self.title.setFixedHeight(34)

        bottom_layout = QVBoxLayout(self.cover_label)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.title)

        self.status_badge = QLabel(self.cover_label)
        self.status_badge.setFixedSize(32, 32)
        self.status_badge.move(8, 8)
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._setup_texts()
        self._load_image()
        self.update_status_badge()

    def update_status_badge(self) -> None:
        entry = get_library().get(self.anime.mal_id)
        if not entry:
            self.status_badge.hide()
            return
        try:
            status = AnimeStatus(entry.tracking_status)
        except ValueError:
            self.status_badge.hide()
            return
        self.status_badge.setPixmap(
            STATUS_FLUENT_ICONS[status.value].icon().pixmap(26, 26)
        )
        self.status_badge.setToolTip(f"Status: {status.label}")
        self.status_badge.show()

    def set_selected(self, selected: bool) -> None:
        self._is_selected = selected

    def is_selected(self) -> bool:
        return self._is_selected

    def _setup_texts(self) -> None:
        title = self.anime.title or "Unknown"
        self.title.setText(title)
        self.title.setToolTip(title)

    def _load_image(self) -> None:
        self._image_url = self.anime.image_url
        if self._image_url:
            image_loader().load(self._image_url, callback=self._on_image)

    def _on_image(self, url: str, pix: QPixmap) -> None:
        if url == self._image_url:
            scaled = pix.scaled(
                self._w,
                self._h,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.cover_label.setPixmap(rounded_pixmap(scaled, 10))
