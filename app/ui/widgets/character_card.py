"""Character card with avatar and click-to-open MAL page."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QMouseEvent, QPixmap
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import AvatarWidget, CaptionLabel, ElevatedCardWidget

from ...services.image_cache import image_loader


class CharacterCard(ElevatedCardWidget):
    def __init__(self, char_data: dict, parent: QWidget | None = None) -> None:
        if not isinstance(char_data, dict):
            raise TypeError(f"Expected dict, got {type(char_data).__name__}")
        super().__init__(parent)
        self.setFixedSize(100, 140)
        self.setBorderRadius(8)
        self.setClickEnabled(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        char = char_data.get("character") or {}
        self._page_url = char.get("url", "")
        self._image_url = ""

        self.avatar = AvatarWidget(self)
        self.avatar.setRadius(42)

        self.name_label = CaptionLabel(char.get("name", "")[:24], self)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.avatar, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.name_label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)

        jpg_url = (char.get("images") or {}).get("jpg", {}).get("image_url", "")
        if jpg_url:
            self._image_url = jpg_url
            image_loader().load(jpg_url, callback=self._on_image)

    def _on_image(self, url: str, pix: QPixmap) -> None:
        if url != self._image_url:
            return
        self.avatar.setImage(
            pix.scaled(
                80,
                80,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if self._page_url and e.button() == Qt.MouseButton.LeftButton:
            QDesktopServices.openUrl(QUrl(self._page_url))
        super().mousePressEvent(e)
