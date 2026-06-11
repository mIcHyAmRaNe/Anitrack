from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QMouseEvent, QPixmap
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import AvatarWidget, CaptionLabel, ElevatedCardWidget, isDarkTheme

from ...config.app_config import AppConfig
from ...services.image_cache import image_loader


class CharacterCard(ElevatedCardWidget):
    def __init__(self, char_data: dict, parent: QWidget | None = None) -> None:
        if not isinstance(char_data, dict):
            raise TypeError(f"Expected dict, got {type(char_data).__name__}")
        super().__init__(parent)
        char_card_w = AppConfig.char_card_w()
        char_card_h = AppConfig.char_card_h()
        self.setFixedSize(char_card_w, char_card_h)
        self.setBorderRadius(AppConfig.char_radius())
        self.setClickEnabled(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        char = char_data.get("character", {})
        self._page_url = char.get("url", "")
        self._image_url = ""

        self.avatar = AvatarWidget(self)
        self.avatar.setRadius(AppConfig.char_avatar_radius())
        self.avatar.setStyleSheet("background: transparent;")

        self.name_label = CaptionLabel(char.get("name", "")[:24], self)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*AppConfig.get("ui", "margins", "char_card"))
        layout.setSpacing(AppConfig.get("ui", "spacing", "xs"))
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.avatar, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.name_label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)

        jpg_url = (char.get("images") or {}).get("jpg", {}).get("image_url", "")
        if jpg_url:
            self._image_url = jpg_url
            image_loader().load(jpg_url, callback=self._on_image)

        self.refresh_theme()

    def _on_image(self, url: str, pix: QPixmap) -> None:
        if url == self._image_url:
            s = AppConfig.char_img_size()
            self.avatar.setImage(
                pix.scaled(
                    s,
                    s,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def refresh_theme(self) -> None:
        self.name_label.setStyleSheet(
            f"background: transparent; color: {AppConfig.text_color(isDarkTheme())};"
        )

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if self._page_url and e.button() == Qt.MouseButton.LeftButton:
            QDesktopServices.openUrl(QUrl(self._page_url))
        super().mousePressEvent(e)
