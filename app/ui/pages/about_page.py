from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ElevatedCardWidget,
    IconWidget,
    StrongBodyLabel,
)
from qfluentwidgets import FluentIcon as FIF

from ...config.app_config import AppConfig


class AboutPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("aboutInterface")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._icon = IconWidget(FIF.VIDEO, self)
        self._icon.setFixedSize(72, 72)

        self._app_name = StrongBodyLabel(AppConfig.app_name(), self)
        self._app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._tagline = CaptionLabel(
            "Track what you watch, mark what you've finished, and discover your next favourite.",
            self,
        )
        self._tagline.setWordWrap(True)
        self._tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._version_pill = QLabel(f"v{AppConfig.app_version()}", self)
        self._version_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._info_card = ElevatedCardWidget(self)
        self._info_card.setBorderRadius(12)
        info_layout = QVBoxLayout(self._info_card)
        info_layout.setContentsMargins(24, 20, 24, 20)
        info_layout.setSpacing(12)

        about_title = StrongBodyLabel("About", self._info_card)
        info_layout.addWidget(about_title, 0, Qt.AlignmentFlag.AlignLeft)

        about_body = BodyLabel(
            "Anitrack is a desktop application that helps you manage your anime library: keep track of what you're watching, mark series as completed or dropped, rate them, and explore recommendations and related shows.",
            self._info_card,
        )
        about_body.setWordWrap(True)
        about_body.setAlignment(Qt.AlignmentFlag.AlignLeft)
        info_layout.addWidget(about_body)
        info_layout.addSpacing(4)

        tech_title = StrongBodyLabel("Built with", self._info_card)
        info_layout.addWidget(tech_title, 0, Qt.AlignmentFlag.AlignLeft)

        tech_row = QHBoxLayout()
        tech_row.setSpacing(8)
        tech_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for icon, name in (
            (FIF.CODE, "Python"),
            (FIF.APPLICATION, "PyQt6"),
            (FIF.BRUSH, "qfluentwidgets"),
            (FIF.CLOUD, "Jikan API"),
        ):
            chip = _TechChip(icon, name, self._info_card)
            tech_row.addWidget(chip)
        tech_row.addStretch(1)
        info_layout.addLayout(tech_row)

        self._dev_label = BodyLabel(
            "Developed with \u2764 by mIcHyAmRaNe \u2764 T.B", self
        )
        self._dev_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._powered_label = CaptionLabel(
            "Powered by the Jikan API (MyAnimeList)", self
        )
        self._powered_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(64, 24, 64, 24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        layout.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(8)
        layout.addWidget(self._app_name, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._version_pill, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(4)
        layout.addWidget(self._tagline, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(24)
        self._info_card.setMinimumWidth(500)
        layout.addWidget(self._info_card, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        layout.addWidget(self._dev_label, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._powered_label, 0, Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)


class _TechChip(ElevatedCardWidget):
    def __init__(self, icon, name: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setBorderRadius(8)
        icon_w = IconWidget(icon, self)
        icon_w.setFixedSize(16, 16)
        label = BodyLabel(name, self)
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 6, 12, 6)
        row.setSpacing(4)
        row.addWidget(icon_w)
        row.addWidget(label)
