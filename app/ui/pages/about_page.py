from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    ElevatedCardWidget,
    IconWidget,
    StrongBodyLabel,
    isDarkTheme,
)
from qfluentwidgets import FluentIcon as FIF

from ...config.app_config import AppConfig


class AboutPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("aboutInterface")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        c = _colors()

        self._icon = IconWidget(FIF.VIDEO, self)
        s = AppConfig.about_icon_size()
        self._icon.setFixedSize(s, s)

        self._app_name = StrongBodyLabel(AppConfig.app_name(), self)
        self._app_name.setStyleSheet(
            f"font-size:{AppConfig.get('ui', 'font', 'sizes', 'title')}px;font-weight:{AppConfig.get('ui', 'font', 'weights', 'extrabold')};color:{c['title']};"
        )
        self._app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._tagline = CaptionLabel(
            "Track what you watch, mark what you've finished, and discover your next favourite.",
            self,
        )
        self._tagline.setWordWrap(True)
        self._tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tagline.setStyleSheet(
            f"font-size:{AppConfig.get('ui', 'font', 'sizes', 'base')}px;color:{c['muted']};padding:{AppConfig.about_tagline_padding()};"
        )

        self._version_pill = QLabel(f"v{AppConfig.app_version()}", self)
        self._version_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._version_pill.setStyleSheet(
            f"background:{c['pill_bg']};color:{c['pill_text']};"
            f"padding:{AppConfig.get('ui', 'padding', 'version_pill')};"
            f"border-radius:{AppConfig.get('ui', 'radius', 'about_card')}px;"
            f"font-size:{AppConfig.get('ui', 'font', 'sizes', 'xs')}px;font-weight:{AppConfig.get('ui', 'font', 'weights', 'bold')};"
        )

        self._info_card = ElevatedCardWidget(self)
        self._info_card.setBorderRadius(AppConfig.about_card_radius())
        info_layout = QVBoxLayout(self._info_card)
        info_layout.setContentsMargins(
            *AppConfig.get("ui", "margins", "about_card_inner")
        )
        info_layout.setSpacing(AppConfig.get("ui", "spacing", "md"))

        about_title = StrongBodyLabel("About", self._info_card)
        about_title.setStyleSheet(
            f"font-size:{AppConfig.get('ui', 'font', 'sizes', 'lg')}px;font-weight:{AppConfig.get('ui', 'font', 'weights', 'bold')};color:{c['text']};"
        )
        info_layout.addWidget(about_title, 0, Qt.AlignmentFlag.AlignLeft)

        about_body = BodyLabel(
            "Anitrack is a desktop application that helps you manage your anime library: keep track of what you're watching, mark series as completed or dropped, rate them, and explore recommendations and related shows.",
            self._info_card,
        )
        about_body.setWordWrap(True)
        about_body.setAlignment(Qt.AlignmentFlag.AlignLeft)
        about_body.setStyleSheet(
            f"font-size:{AppConfig.get('ui', 'font', 'sizes', 'md')}px;color:{c['muted']};"
        )
        info_layout.addWidget(about_body)
        info_layout.addSpacing(AppConfig.about_body_after_spacing())

        tech_title = StrongBodyLabel("Built with", self._info_card)
        tech_title.setStyleSheet(
            f"font-size:{AppConfig.get('ui', 'font', 'sizes', 'lg')}px;font-weight:{AppConfig.get('ui', 'font', 'weights', 'bold')};color:{c['text']};"
        )
        info_layout.addWidget(tech_title, 0, Qt.AlignmentFlag.AlignLeft)

        tech_row = QHBoxLayout()
        tech_row.setSpacing(AppConfig.get("ui", "spacing", "sm"))
        tech_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for icon, name in (
            (FIF.CODE, "Python"),
            (FIF.APPLICATION, "PyQt6"),
            (FIF.BRUSH, "qfluentwidgets"),
            (FIF.CLOUD, "Jikan API"),
        ):
            chip = _TechChip(icon, name, self._info_card, c)
            tech_row.addWidget(chip)
        tech_row.addStretch(1)
        info_layout.addLayout(tech_row)

        self._dev_label = BodyLabel(
            "Developed with \u2764 by mIcHyAmRaNe \u2764 T.B", self
        )
        self._dev_label.setStyleSheet(
            f"font-size:{AppConfig.get('ui', 'font', 'sizes', 'sm')}px;color:{c['muted']};"
        )
        self._dev_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._powered_label = CaptionLabel(
            "Powered by the Jikan API (MyAnimeList)", self
        )
        self._powered_label.setStyleSheet(
            f"font-size:{AppConfig.get('ui', 'font', 'sizes', 'sm')}px;color:{c['muted']};"
        )
        self._powered_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.setSpacing(AppConfig.get("ui", "spacing", "sm"))
        layout.setContentsMargins(*AppConfig.get("ui", "margins", "about_page"))
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        layout.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(AppConfig.about_icon_spacing())
        layout.addWidget(self._app_name, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._version_pill, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(AppConfig.about_version_spacing())
        layout.addWidget(self._tagline, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(AppConfig.about_before_info_spacing())
        self._info_card.setMinimumWidth(
            AppConfig.get("ui", "sizes", "about_card_min_width")
        )
        layout.addWidget(self._info_card, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        layout.addWidget(self._dev_label, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._powered_label, 0, Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def refresh_theme(self) -> None:
        c = _colors()
        fs = AppConfig.get("ui", "font", "sizes")
        fw = AppConfig.get("ui", "font", "weights")
        self._app_name.setStyleSheet(
            f"font-size:{fs['title']}px;font-weight:{fw['extrabold']};color:{c['title']};"
        )
        self._tagline.setStyleSheet(
            f"font-size:{fs['base']}px;color:{c['muted']};padding:{AppConfig.about_tagline_padding()};"
        )
        self._version_pill.setStyleSheet(
            f"background:{c['pill_bg']};color:{c['pill_text']};"
            f"padding:{AppConfig.get('ui', 'padding', 'version_pill')};"
            f"border-radius:{AppConfig.get('ui', 'radius', 'about_card')}px;"
            f"font-size:{fs['xs']}px;font-weight:{fw['bold']};"
        )
        self._dev_label.setStyleSheet(f"font-size:{fs['sm']}px;color:{c['muted']};")
        self._powered_label.setStyleSheet(f"font-size:{fs['sm']}px;color:{c['muted']};")
        for chip in self._info_card.findChildren(_TechChip):
            chip.refresh(c)


class _TechChip(ElevatedCardWidget):
    def __init__(self, icon, name: str, parent: QWidget, c: dict) -> None:
        super().__init__(parent)
        self.setBorderRadius(AppConfig.about_chip_radius())
        self._c = c
        self._name = name
        icon_w = IconWidget(icon, self)
        icon_w.setFixedSize(
            AppConfig.about_chip_icon_size(), AppConfig.about_chip_icon_size()
        )
        label = BodyLabel(name, self)
        label.setStyleSheet(
            f"font-size:{AppConfig.get('ui', 'font', 'sizes', 'sm')}px;font-weight:{AppConfig.get('ui', 'font', 'weights', 'semibold')};color:{c['text']};background:transparent;"
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(*AppConfig.get("ui", "margins", "about_chip_row"))
        row.setSpacing(AppConfig.get("ui", "spacing", "xs"))
        row.addWidget(icon_w)
        row.addWidget(label)

    def refresh(self, c: dict) -> None:
        self._c = c
        for child in self.findChildren(BodyLabel):
            if child.text() == self._name:
                child.setStyleSheet(
                    f"font-size:{AppConfig.get('ui', 'font', 'sizes', 'sm')}px;font-weight:{AppConfig.get('ui', 'font', 'weights', 'semibold')};color:{self._c['text']};background:transparent;"
                )


def _colors() -> dict:
    dark = isDarkTheme()
    return {
        "title": AppConfig.title_color(dark),
        "text": AppConfig.text_color(dark),
        "muted": AppConfig.muted_color(dark),
        "pill_bg": AppConfig.pill_bg(dark),
        "pill_text": AppConfig.pill_text(dark),
    }
