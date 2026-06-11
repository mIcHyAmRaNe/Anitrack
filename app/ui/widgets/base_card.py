from __future__ import annotations

from loguru import logger
from PyQt6.QtCore import QEvent, QPointF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QEnterEvent, QHideEvent, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    ElevatedCardWidget,
    FlyoutViewBase,
    InfoBadge,
    TeachingTip,
    TeachingTipTailPosition,
    isDarkTheme,
    themeColor,
)

from ...config.app_config import AppConfig
from ...models.anime import Anime, AnimeStatus
from ...models.library import get_library
from ...services.image_cache import image_loader, placeholder_pixmap, rounded_pixmap
from ...theme.theme import STATUS_FLUENT_ICONS

_BADGE_STYLE = (
    "InfoBadge{{padding:{badge_padding};font-size:{badge_font_size}px;"
    "font-weight:{badge_font_weight};color:white;}}"
)
_TIP_STYLE = "padding:2px 0;"

_hovered_card: BaseCard | None = None


def _badge_style() -> str:
    return _BADGE_STYLE.format(
        badge_padding=AppConfig.badge_padding(),
        badge_font_size=AppConfig.badge_font_size(),
        badge_font_weight=AppConfig.badge_font_weight(),
    )


def sync_hover_after_scroll() -> None:
    global _hovered_card
    pos = QCursor.pos()
    widget = QApplication.widgetAt(pos)
    new_card: BaseCard | None = None
    w = widget
    while w is not None:
        if isinstance(w, BaseCard):
            new_card = w
            break
        w = w.parentWidget()
    if new_card is _hovered_card:
        return
    if _hovered_card is not None:
        old = _hovered_card
        _hovered_card = None
        QApplication.sendEvent(old, QEvent(QEvent.Type.Leave))
    if new_card is not None:
        _hovered_card = new_card
        local = new_card.mapFromGlobal(pos)
        QApplication.sendEvent(
            new_card, QEnterEvent(QPointF(local), QPointF(local), QPointF(pos))
        )


def _tip_colors() -> dict[str, str]:
    dark = isDarkTheme()
    return {
        "text": AppConfig.text_color(dark),
        "muted": AppConfig.muted_color(dark),
        "tag_bg": AppConfig.surface_color(dark),
        "tag_text": AppConfig.text_color(dark),
    }


def _status_badge_icon(status: AnimeStatus, size: int | None = None) -> QPixmap:
    if size is None:
        size = AppConfig.badge_size()
    s = int(size * 0.8)
    return STATUS_FLUENT_ICONS[status.value].icon().pixmap(s, s)


class _HoverTipView(FlyoutViewBase):
    def __init__(self, anime: Anime, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(AppConfig.get("ui", "sizes", "card_width"))
        c = _tip_colors()
        fs = AppConfig.get("ui", "font", "sizes")
        fw = AppConfig.get("ui", "font", "weights")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*AppConfig.get("ui", "margins", "hover_tip"))
        layout.setSpacing(AppConfig.get("ui", "spacing", "sm"))

        if anime.anime_type or anime.episodes is not None or anime.score is not None:
            info_row = QHBoxLayout()
            info_row.setContentsMargins(0, 0, 0, 0)
            left_parts = []
            if anime.anime_type:
                left_parts.append(anime.anime_type)
            if anime.episodes is not None:
                left_parts.append(f"{anime.episodes} eps")
            left_lbl = QLabel("  |  ".join(left_parts))
            left_lbl.setStyleSheet(
                f"font-size:{fs['sm']}px;font-weight:{fw['semibold']};color:{c['text']};{_TIP_STYLE}"
            )
            right_lbl = QLabel(
                f"\u2605 {anime.score:.1f}" if anime.score is not None else ""
            )
            right_lbl.setStyleSheet(
                f"font-size:{fs['sm']}px;font-weight:{fw['semibold']};color:{c['text']};{_TIP_STYLE}"
            )
            if anime.score is None:
                right_lbl.hide()
            info_row.addWidget(left_lbl)
            info_row.addStretch(1)
            info_row.addWidget(right_lbl)
            layout.addLayout(info_row)

        if anime.genres:
            genre_row = QHBoxLayout()
            genre_row.setSpacing(AppConfig.get("ui", "spacing", "xs"))
            genre_row.setContentsMargins(0, 0, 0, 0)
            for g in anime.genres:
                tag = QLabel(g)
                tag.setStyleSheet(
                    f"padding:{AppConfig.get('ui', 'padding', 'pill')};border-radius:{AppConfig.get('ui', 'radius', 'tag')}px;font-size:{fs['xs']}px;font-weight:{fw['semibold']};color:{c['tag_text']};background:{c['tag_bg']};"
                )
                tag.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
                genre_row.addWidget(tag)
            genre_row.addStretch(1)
            layout.addLayout(genre_row)

        synopsis = anime.synopsis or "No synopsis available."
        if len(synopsis) > 160:
            synopsis = synopsis[:160] + "..."
        synopsis_lbl = QLabel(synopsis)
        synopsis_lbl.setWordWrap(True)
        synopsis_lbl.setFixedWidth(AppConfig.get("ui", "sizes", "synopsis_width"))
        synopsis_lbl.setStyleSheet(
            f"font-size:{fs['sm']}px;color:{c['muted']};{_TIP_STYLE}"
        )
        layout.addWidget(synopsis_lbl)


class BaseCard(ElevatedCardWidget):
    clicked = pyqtSignal(object)

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
        if card_w is not None and card_w <= 0:
            raise ValueError(f"card_w must be positive, got {card_w}")

        super().__init__(parent)
        self.anime = anime
        self._w = card_w if card_w is not None else AppConfig.card_cover_w()
        self._h = content_h
        self._is_selected = False
        self._hovered = False
        self._tip: TeachingTip | None = None

        radius = AppConfig.card_radius()
        badge_sz = AppConfig.badge_size()
        dim_opacity = AppConfig.dim_opacity()
        hover_deb = AppConfig.hover_debounce_ms()
        overlay_h = AppConfig.get("ui", "sizes", "card_overlay_height")
        badge_h = AppConfig.get("ui", "sizes", "badge_height")
        gs = AppConfig.get("ui", "opacity")

        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(hover_deb)
        self._hover_timer.timeout.connect(self._show_tip)

        self.setFixedSize(self._w, self._h)
        self.setBorderRadius(radius)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.cover_label = QLabel(self)
        self.cover_label.setFixedSize(self._w, self._h)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setPixmap(
            rounded_pixmap(placeholder_pixmap(self._w, self._h), radius)
        )

        self.dim_overlay = QLabel(self.cover_label)
        self.dim_overlay.setFixedSize(self._w, self._h)
        self.dim_overlay.setStyleSheet(
            f"background-color:black;border-radius:{radius}px;"
        )
        self._dim_effect = QGraphicsOpacityEffect(self.dim_overlay)
        self._dim_effect.setOpacity(dim_opacity)
        self.dim_overlay.setGraphicsEffect(self._dim_effect)

        self._bottom_overlay = QWidget(self.cover_label)
        self._bottom_overlay.setFixedSize(self._w, overlay_h)
        self._bottom_overlay.move(0, self._h - overlay_h)
        self._bottom_overlay.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"stop:0 rgba(0,0,0,{gs['gradient_stop_0']}),"
            f"stop:0.4 rgba(0,0,0,{gs['gradient_stop_4']}),"
            f"stop:0.7 rgba(0,0,0,{gs['gradient_stop_7']}),"
            f"stop:1 rgba(0,0,0,{gs['gradient_stop_1']}));"
            f"border-bottom-left-radius:{radius}px;border-bottom-right-radius:{radius}px;"
        )
        self._bottom_overlay.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

        bottom_layout = QVBoxLayout(self._bottom_overlay)
        bottom_layout.setContentsMargins(
            *AppConfig.get("ui", "margins", "bottom_overlay")
        )

        self.title = InfoBadge.custom("", QColor(0, 0, 0, 0), QColor(0, 0, 0, 0))
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.title.setWordWrap(True)
        self.title.setFixedHeight(badge_h)
        self.title.setStyleSheet(_badge_style())
        bottom_layout.addWidget(self.title)

        self.status_badge = QLabel(self.cover_label)
        self.status_badge.setFixedSize(badge_sz, badge_sz)
        self.status_badge.move(
            AppConfig.status_badge_offset_x(), AppConfig.status_badge_offset_y()
        )
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._selection_border = QLabel(self.cover_label)
        self._selection_border.setFixedSize(self._w, self._h)
        self._selection_border.setStyleSheet("background:transparent;")

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
        badge_sz = AppConfig.badge_size()
        self.status_badge.setPixmap(_status_badge_icon(status))
        self.status_badge.setStyleSheet(
            f"background:{AppConfig.badge_bg_color()};border-radius:{badge_sz // 2}px;"
        )
        self.status_badge.setToolTip(f"Status: {status.label}")
        self.status_badge.show()

    def set_selected(self, selected: bool) -> None:
        self._is_selected = selected
        self._update_selection_border()
        self._set_dim(
            AppConfig.hover_opacity()
            if (selected or self._hovered)
            else AppConfig.dim_opacity()
        )

    def is_selected(self) -> bool:
        return self._is_selected

    def refresh_theme(self) -> None:
        self.update_status_badge()
        self.title.setStyleSheet(_badge_style())

    def close_tip(self) -> None:
        self._close_tip()

    def _close_tip(self) -> None:
        if self._tip:
            self._tip.close()
            self._tip = None

    def _show_tip(self) -> None:
        if not self._hovered or not self.isVisible():
            return
        self._close_tip()
        try:
            self._tip = TeachingTip.make(
                view=_HoverTipView(self.anime),
                target=self.cover_label,
                duration=-1,
                tailPosition=TeachingTipTailPosition.LEFT,
                parent=self.window() or self,
            )
        except Exception as e:
            logger.warning("Failed to show hover tip: {}", e)

    def _update_selection_border(self) -> None:
        radius = AppConfig.card_radius()
        if self._is_selected:
            self._selection_border.setStyleSheet(
                f"background:{AppConfig.selection_color()};border:2px solid {themeColor().name()};border-radius:{radius}px;"
            )
        else:
            self._selection_border.setStyleSheet(
                f"background:{AppConfig.selection_color()};border:none;"
            )

    def _setup_texts(self) -> None:
        title = self.anime.title or "Unknown"
        self.title.setText(title)
        self.title.setToolTip(title)

    def _load_image(self) -> None:
        if self.anime.image_url:
            image_loader().load(self.anime.image_url, callback=self._on_image)

    def _on_image(self, url: str, pix: QPixmap) -> None:
        if url == self.anime.image_url:
            scaled = pix.scaled(
                self._w,
                self._h,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.cover_label.setPixmap(rounded_pixmap(scaled, AppConfig.card_radius()))

    def _set_dim(self, opacity: float) -> None:
        self._dim_effect.setOpacity(opacity)

    @property
    def is_hovered(self) -> bool:
        return self._hovered

    def enterEvent(self, e: QEnterEvent | None) -> None:
        global _hovered_card
        _hovered_card = self
        self._hovered = True
        self._set_dim(AppConfig.hover_opacity())
        self._hover_timer.start()
        super().enterEvent(e)

    def leaveEvent(self, e: QEvent) -> None:
        global _hovered_card
        _hovered_card = None
        self._hovered = False
        self._hover_timer.stop()
        self._close_tip()
        if not self._is_selected:
            self._set_dim(AppConfig.dim_opacity())
        super().leaveEvent(e)

    def hideEvent(self, a0: QHideEvent | None) -> None:
        global _hovered_card
        if _hovered_card is self:
            _hovered_card = None
        self._hover_timer.stop()
        self._close_tip()
        self._hovered = False
        self._dim_effect.setOpacity(AppConfig.dim_opacity())
        super().hideEvent(a0)
