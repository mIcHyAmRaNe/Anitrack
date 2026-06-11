from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QMouseEvent, QPixmap
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import CaptionLabel, ImageLabel

from ...config.app_config import AppConfig
from ...services.image_cache import image_loader


class TrailerWidget(QWidget):
    def __init__(self, trailer_data: dict, parent: QWidget | None = None) -> None:
        if not isinstance(trailer_data, dict):
            raise TypeError(f"Expected dict, got {type(trailer_data).__name__}")
        super().__init__(parent)
        self._youtube_url = trailer_data.get("url", "")
        self._thumb_url = ""
        thumb_h = AppConfig.trailer_thumb_h()
        self.setFixedHeight(
            thumb_h + AppConfig.get("ui", "sizes", "trailer_thumb_height_offset")
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.thumb = ImageLabel(self)
        r = AppConfig.get("ui", "radius", "trailer")
        self.thumb.setBorderRadius(r, r, r, r)
        self.thumb.setFixedHeight(thumb_h)

        self.hint = CaptionLabel("Click to play trailer on YouTube", self)
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(AppConfig.get("ui", "spacing", "xs"))
        layout.addWidget(self.thumb)
        layout.addWidget(self.hint)

        images = trailer_data.get("images", {}) or {}
        thumb_url = (
            images.get("maximum_image_url")
            or images.get("large_image_url")
            or images.get("medium_image_url")
            or ""
        )
        if thumb_url:
            self._thumb_url = thumb_url
            image_loader().load(thumb_url, callback=self._on_image)

    def _on_image(self, url: str, pix: QPixmap) -> None:
        if url == self._thumb_url:
            self.thumb.setImage(pix)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._youtube_url:
            QDesktopServices.openUrl(QUrl(self._youtube_url))
        super().mousePressEvent(event)
