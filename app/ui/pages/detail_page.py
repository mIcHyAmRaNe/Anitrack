from __future__ import annotations

from loguru import logger
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QWheelEvent
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    HyperlinkLabel,
    IndeterminateProgressRing,
    ScrollArea,
    SingleDirectionScrollArea,
    StrongBodyLabel,
    TitleLabel,
    ToggleToolButton,
    ToolTipFilter,
    TransparentToolButton,
)
from qfluentwidgets import FluentIcon as FIF

from ...config.app_config import AppConfig
from ...models.anime import STATUS_FLUENT_ICONS, Anime, AnimeStatus
from ...models.library import get_library
from ...services.image_cache import image_loader, placeholder_pixmap, rounded_pixmap
from ..signal_bus import signalBus
from ..widgets.character_card import CharacterCard
from ..widgets.recommendation_card import RecommendationCard
from ..widgets.relation_card import RelationCard
from ..widgets.trailer_widget import TrailerWidget
from ..workers import FetchDetailWorker


def build_horizontal_section(
    title: str, card_height: int
) -> tuple[QWidget, QHBoxLayout, StrongBodyLabel, SingleDirectionScrollArea]:
    section = QWidget()
    section.setVisible(False)
    layout = QVBoxLayout(section)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    title_label = StrongBodyLabel(title)
    title_label.setObjectName(f"sectionTitle_{title}")
    layout.addWidget(title_label)

    scroll = SingleDirectionScrollArea(orient=Qt.Orientation.Horizontal)
    scroll.setFixedHeight(card_height + 8)
    scroll.enableTransparentBackground()

    host = QWidget()
    host_layout = QHBoxLayout(host)
    host_layout.setContentsMargins(0, 0, 0, 0)
    host_layout.setSpacing(4)
    host_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
    scroll.setWidget(host)
    layout.addWidget(scroll)
    return section, host_layout, title_label, scroll


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item:
            w = item.widget()
            if w:
                w.hide()
                w.deleteLater()


class DetailPage(QWidget):
    def hideEvent(self, a0) -> None:
        self._stop_worker()
        super().hideEvent(a0)

    def __init__(self, parent: QWidget | None) -> None:
        super().__init__(parent)
        self.setObjectName("animeDetailInterface")
        self._library = get_library()
        self._anime_model: Anime | None = None
        self._ready = False
        self._worker: FetchDetailWorker | None = None
        self._current_mal_id: int = 0
        self._section_titles: list[StrongBodyLabel] = []

        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)

        self._header_widget = QWidget(self)
        self._header_widget.setFixedHeight(56)
        headerLayout = QHBoxLayout(self._header_widget)
        headerLayout.setContentsMargins(28, 8, 28, 8)

        self.backBtn = TransparentToolButton(FIF.LEFT_ARROW, self)
        self.backBtn.setToolTip("Go Back")
        self.backBtn.clicked.connect(signalBus.goBack.emit)

        self.titleLabel = TitleLabel("Loading...", self)
        self.titleLabel.setWordWrap(True)

        headerLayout.addWidget(self.backBtn)
        headerLayout.addSpacing(8)
        headerLayout.addWidget(self.titleLabel, 1)
        self.vBoxLayout.addWidget(self._header_widget)

        self.scrollArea = ScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scrollArea.enableTransparentBackground()
        self.scrollArea.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
        )
        viewport = self.scrollArea.viewport()
        if viewport is not None:
            viewport.setStyleSheet("background:transparent;")

        self.scrollWidget = QWidget()
        self.scrollLayout = QVBoxLayout(self.scrollWidget)
        self.scrollLayout.setContentsMargins(28, 24, 28, 40)
        self.scrollLayout.setSpacing(24)

        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(32)

        left_panel = QVBoxLayout()
        left_panel.setSpacing(16)
        left_panel.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.coverLabel = QLabel()
        self.coverLabel.setFixedSize(260, 370)
        self.coverLabel.setPixmap(rounded_pixmap(placeholder_pixmap(260, 370), 10))
        self.coverLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_panel.addWidget(self.coverLabel, 0, Qt.AlignmentFlag.AlignTop)

        self.statusButtonGroup = QHBoxLayout()
        self.statusButtonGroup.setSpacing(8)
        self.statusButtonGroup.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._status_btns: dict[AnimeStatus, ToggleToolButton] = {}
        for status in AnimeStatus:
            btn = ToggleToolButton(self)
            btn.setFixedSize(42, 42)
            btn.setIcon(STATUS_FLUENT_ICONS[status.value].icon())
            btn.setToolTip(status.label)
            btn.installEventFilter(ToolTipFilter(btn, 300))
            btn.clicked.connect(lambda checked, s=status: self._on_status_clicked(s))
            self._status_btns[status] = btn
            self.statusButtonGroup.addWidget(btn)

        left_panel.addLayout(self.statusButtonGroup)
        left_panel.addStretch(1)
        top_layout.addLayout(left_panel)

        right_panel = QVBoxLayout()
        right_panel.setSpacing(12)

        self.badgesRow = QHBoxLayout()
        self.badgesRow.setSpacing(4)
        self.badgesRow.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.typeBadge = QLabel()
        self.epsBadge = QLabel()
        self.statusBadge = QLabel()
        self.yearBadge = QLabel()
        for badge in (self.typeBadge, self.epsBadge, self.statusBadge, self.yearBadge):
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.hide()
            self.badgesRow.addWidget(badge)
        self.badgesRow.addStretch(1)

        self.scoreRankRow = QHBoxLayout()
        self.scoreRankRow.setSpacing(16)
        self.scoreLabel = StrongBodyLabel("")
        self.scoreLabel.hide()
        self.rankLabel = CaptionLabel("")
        self.rankLabel.hide()
        self.scoreRankRow.addWidget(self.scoreLabel)
        self.scoreRankRow.addWidget(self.rankLabel)
        self.scoreRankRow.addStretch(1)

        self.genresRow = QHBoxLayout()
        self.genresRow.setSpacing(4)
        self.genresRow.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.synopsisLabel = BodyLabel("Loading details...")
        self.synopsisLabel.setWordWrap(True)
        self.synopsisLabel.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.loadingSpinner = IndeterminateProgressRing(self)
        self.loadingSpinner.setFixedSize(24, 24)
        self.loadingSpinner.hide()

        self.urlLabel = HyperlinkLabel("")

        right_panel.addLayout(self.badgesRow)
        right_panel.addLayout(self.scoreRankRow)
        right_panel.addLayout(self.genresRow)
        right_panel.addSpacing(8)
        right_panel.addWidget(self.synopsisLabel)

        spinnerRow = QHBoxLayout()
        spinnerRow.setContentsMargins(0, 2, 0, 0)
        spinnerRow.addWidget(self.loadingSpinner)
        spinnerRow.addStretch(1)
        right_panel.addLayout(spinnerRow)

        right_panel.addSpacing(4)
        right_panel.addWidget(self.urlLabel)
        right_panel.addStretch(1)

        top_layout.addLayout(right_panel, 1)
        self.scrollLayout.addWidget(top_widget)

        (self.charSection, self.charHostLayout, _title, self._charScroll) = (
            build_horizontal_section("Characters", 140)
        )
        self._section_titles.append(_title)
        self._install_inner_scroll_filter(self._charScroll)
        self.scrollLayout.addWidget(self.charSection)

        (self.relSection, self.relHostLayout, _title, self._relScroll) = (
            build_horizontal_section("Relations", 195)
        )
        self._section_titles.append(_title)
        self._install_inner_scroll_filter(self._relScroll)
        self.scrollLayout.addWidget(self.relSection)

        (self.recSection, self.recHostLayout, _title, self._recScroll) = (
            build_horizontal_section("Recommendations", 195)
        )
        self.recHostLayout.setSpacing(12)
        self._section_titles.append(_title)
        self._install_inner_scroll_filter(self._recScroll)
        self.scrollLayout.addWidget(self.recSection)

        self.trailerSection = QWidget()
        self.trailerSection.setVisible(False)
        trailer_section_layout = QVBoxLayout(self.trailerSection)
        trailer_section_layout.setContentsMargins(0, 0, 0, 0)
        trailer_section_layout.setSpacing(8)

        self._trailer_title = StrongBodyLabel("Trailer")
        trailer_section_layout.addWidget(self._trailer_title)

        self.trailerWidget = TrailerWidget({})
        trailer_section_layout.addWidget(self.trailerWidget)
        self.scrollLayout.addWidget(self.trailerSection)

        self.scrollLayout.addStretch(1)
        self.scrollArea.setWidget(self.scrollWidget)
        self.vBoxLayout.addWidget(self.scrollArea, 1)

        image_loader().loaded.connect(self._on_cover)

    def _install_inner_scroll_filter(self, scroll_area) -> None:
        scroll_area.installEventFilter(self)
        viewport = scroll_area.viewport()
        if viewport is not None:
            viewport.installEventFilter(self)
        host = scroll_area.widget()
        if host is not None:
            host.installEventFilter(self)

    def eventFilter(self, a0, a1) -> bool:
        if isinstance(a1, QWheelEvent):
            delta = a1.angleDelta()
            if delta.x() != 0 or (a1.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                return False
            vbar = self.scrollArea.verticalScrollBar()
            if vbar is not None and vbar.isVisible() and delta.y() != 0:
                pixel_delta = a1.pixelDelta()
                if not pixel_delta.isNull():
                    vbar.setValue(vbar.value() - pixel_delta.y())
                else:
                    notches = delta.y() / 120
                    vbar.setValue(int(vbar.value() - notches * vbar.singleStep() * 3))
                return True
        return super().eventFilter(a0, a1)

    def load_anime(self, anime: Anime) -> None:
        if not isinstance(anime, Anime):
            logger.warning("load_anime received non-Anime object")
            return
        self._ready = False
        self._anime_model = anime
        self.titleLabel.setText(anime.title)
        self.charSection.hide()
        self.relSection.hide()
        self.recSection.hide()
        self.trailerSection.hide()

        if anime.image_url:
            image_loader().load(anime.image_url)

        for btn in self._status_btns.values():
            btn.blockSignals(True)
            btn.setChecked(False)
            btn.blockSignals(False)

        existing = self._library.get(anime.mal_id)
        if existing:
            try:
                status = AnimeStatus(existing.tracking_status)
                if status in self._status_btns:
                    btn = self._status_btns[status]
                    btn.blockSignals(True)
                    btn.setChecked(True)
                    btn.blockSignals(False)
            except ValueError:
                pass

        self._setup_badge(anime.anime_type, self.typeBadge)
        self._setup_badge(
            f"{anime.episodes} eps" if anime.episodes else "", self.epsBadge
        )
        self._setup_badge(anime.status, self.statusBadge)
        self._setup_badge(str(anime.year) if anime.year else "", self.yearBadge)

        if anime.score:
            self.scoreLabel.setText(f"\u2605 {anime.score:.2f}")
            self.scoreLabel.show()

        self._update_genres(anime.genres)
        self.synopsisLabel.setText(anime.synopsis or "No synopsis available.")
        self._ready = True
        self._start_fetch(anime.mal_id)

    def _stop_worker(self) -> None:
        if self._worker is not None:
            try:
                self._worker.finished_ok.disconnect()
            except TypeError:
                pass
            self._worker.quit()
            self._worker.wait()
            self._worker.deleteLater()
            self._worker = None

    def _start_fetch(self, mal_id: int) -> None:
        self._current_mal_id = mal_id
        self._stop_worker()
        self.loadingSpinner.show()
        self._worker = FetchDetailWorker(mal_id)
        self._worker.finished_ok.connect(self._on_fetched)
        self._worker.start()

    def _on_cover(self, url: str, pix: QPixmap) -> None:
        if self._anime_model and url == self._anime_model.image_url:
            if isinstance(pix, QPixmap):
                scaled = pix.scaled(
                    260,
                    370,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.coverLabel.setPixmap(rounded_pixmap(scaled, 10))

    def _on_status_clicked(self, status: AnimeStatus) -> None:
        if not self._ready or not self._anime_model:
            return
        btn = self._status_btns[status]
        is_checked = btn.isChecked()
        if not is_checked:
            if self._library.get(self._anime_model.mal_id):
                self._library.remove(self._anime_model.mal_id)
                signalBus.libraryRemoved.emit(self._anime_model)
        else:
            was_tracked = self._library.get(self._anime_model.mal_id) is not None
            for s, b in self._status_btns.items():
                if s != status:
                    b.blockSignals(True)
                    b.setChecked(False)
                    b.blockSignals(False)
            self._library.add(self._anime_model, status)
            signalBus.libraryStatusChanged.emit(
                self._anime_model, status.value
            ) if was_tracked else signalBus.libraryAdded.emit(self._anime_model)
        signalBus.libraryChanged.emit()

    def _setup_badge(self, text: str, badge: QLabel) -> None:
        if text and text != "?":
            badge.setText(text)
            badge.show()
        else:
            badge.hide()

    def _update_genres(self, genres: list[str]) -> None:
        _clear_layout(self.genresRow)
        if not genres:
            return
        for g in genres:
            label = CaptionLabel(g)
            self.genresRow.addWidget(label)
        self.genresRow.addStretch(1)

    def _on_fetched(
        self,
        mal_id: int,
        full_data: dict,
        characters: list,
        relations: list,
        recommendations: list,
    ) -> None:
        if mal_id != self._current_mal_id:
            logger.debug("Ignoring stale fetch response for mal_id={}", mal_id)
            return
        self.loadingSpinner.hide()
        logger.info(
            "Fetched detail for mal_id={}: chars={}, rels={}, recs={}",
            mal_id,
            len(characters),
            len(relations),
            len(recommendations),
        )

        if full_data:
            anime = Anime.from_jikan(full_data)
            self._anime_model = anime
            self._setup_badge(anime.anime_type, self.typeBadge)
            self._setup_badge(
                f"{anime.episodes} eps" if anime.episodes else "", self.epsBadge
            )
            self._setup_badge(anime.status, self.statusBadge)
            self._setup_badge(str(anime.year) if anime.year else "", self.yearBadge)
            if anime.score:
                self.scoreLabel.setText(f"\u2605 {anime.score:.2f}")
                self.scoreLabel.show()
            else:
                self.scoreLabel.hide()
            rank = full_data.get("rank")
            if rank:
                self.rankLabel.setText(f"Rank #{rank}")
                self.rankLabel.show()
            else:
                self.rankLabel.hide()
            self._update_genres(anime.genres)
            self.synopsisLabel.setText(anime.synopsis or "No synopsis available.")
            if full_data.get("url"):
                self.urlLabel.setUrl(full_data["url"])
                self.urlLabel.setText("Open on MyAnimeList \u2192")
            trailer = full_data.get("trailer") or {}
            if trailer.get("youtube_id"):
                old = self.trailerWidget
                layout = self.trailerSection.layout()
                idx = layout.indexOf(old) if layout is not None else -1
                self.trailerWidget = TrailerWidget(trailer)
                if idx >= 0 and isinstance(layout, QVBoxLayout):
                    layout.insertWidget(idx, self.trailerWidget)
                old.deleteLater()
                self.trailerSection.setVisible(True)

        self._populate_characters(characters)
        self._populate_relations(relations)
        self._populate_recommendations(recommendations)

    def _populate_characters(self, characters: list) -> None:
        self._populate_section(
            self.charHostLayout,
            self.charSection,
            characters[: AppConfig.characters_limit()],
            lambda c: CharacterCard(c),
        )

    def _populate_relations(self, relations: list) -> None:
        cards: list = []
        for rel in relations:
            rel_type = rel.get("relation", "")
            for entry in rel.get("entry") or []:
                if isinstance(entry, dict) and entry.get("mal_id"):
                    cards.append(RelationCard(entry, rel_type))
        self._populate_section(self.relHostLayout, self.relSection, cards, lambda c: c)

    def _populate_recommendations(self, recommendations: list) -> None:
        cards: list = []
        for rec in recommendations:
            entry = rec.get("entry")
            if isinstance(entry, dict) and entry.get("mal_id"):
                cards.append(RecommendationCard(entry))
        self._populate_section(self.recHostLayout, self.recSection, cards, lambda c: c)

    def _populate_section(
        self,
        layout: QHBoxLayout,
        section: QWidget,
        items: list,
        factory,
    ) -> None:
        _clear_layout(layout)
        if not items:
            section.setVisible(False)
            return
        for item in items:
            card = factory(item)
            card.installEventFilter(self)
            layout.addWidget(card)
        layout.addStretch(1)
        parent = layout.parentWidget()
        if parent is not None:
            parent.adjustSize()
        section.setVisible(True)
