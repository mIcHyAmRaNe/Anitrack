from __future__ import annotations

from loguru import logger
from PyQt6.QtCore import QCoreApplication, Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    FlowLayout,
    IndeterminateProgressRing,
    ScrollArea,
    SearchLineEdit,
    StrongBodyLabel,
    TitleLabel,
)

from ...config.app_config import AppConfig
from ...models.anime import Anime
from ...theme.theme import interface_background
from ..signal_bus import signalBus
from ..widgets.base_card import sync_hover_after_scroll
from ..widgets.suggestion_card import SuggestionCard
from ..workers import SearchWorker, SuggestionsWorker

EMPTY_STATE_HINT = "Search an anime by title to get started."


class HomePage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("homeInterface")

        self.titleLabel = TitleLabel("Anitrack", self)
        sf = QFont(AppConfig.font_family())
        sf.setPointSize(AppConfig.subtitle_font_size())
        self.subtitleLabel = CaptionLabel("Search and add anime to your library.", self)
        self.subtitleLabel.setFont(sf)

        self.searchEdit = SearchLineEdit(self)
        self.searchEdit.setPlaceholderText(
            "Search anime on MyAnimeList\u2026  (Ctrl+F)"
        )
        self.searchEdit.setClearButtonEnabled(True)
        self.searchEdit.setFixedWidth(AppConfig.get("ui", "sizes", "search_edit_home"))

        self.progressRing = IndeterminateProgressRing(self)
        ps = AppConfig.get("ui", "sizes", "progress_ring")
        self.progressRing.setFixedSize(ps, ps)
        self.progressRing.hide()

        searchRow = QHBoxLayout()
        searchRow.addWidget(self.searchEdit)
        searchRow.addWidget(self.progressRing)
        searchRow.addStretch(1)

        self.sectionTitle = StrongBodyLabel("Suggestions", self)
        self.statusLabel = CaptionLabel("", self)
        self.statusLabel.setVisible(False)

        sectionRow = QHBoxLayout()
        sectionRow.addWidget(self.sectionTitle)
        sectionRow.addStretch(1)
        sectionRow.addWidget(self.statusLabel)

        self.scrollArea = ScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        # self.scrollArea.viewport().setStyleSheet(
        #     f"background: {interface_background()};"
        # )

        self.gridHost = QWidget(self.scrollArea)
        self.gridHost.setStyleSheet(f"background: {interface_background()};")
        self.gridLayout = FlowLayout(self.gridHost, needAni=False)
        self.gridLayout.setContentsMargins(*AppConfig.get("ui", "margins", "home_grid"))
        self.gridLayout.setSpacing(0)
        self.gridHost.setLayout(self.gridLayout)
        self.scrollArea.setWidget(self.gridHost)

        self.emptyLabel = BodyLabel(EMPTY_STATE_HINT, self)
        self.emptyLabel.setObjectName("emptyState")
        self.emptyLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.emptyLabel.setWordWrap(True)

        self.stack = QStackedWidget(self)
        self.stack.addWidget(self.scrollArea)
        self.stack.addWidget(self.emptyLabel)
        self.stack.setCurrentWidget(self.emptyLabel)

        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(*AppConfig.get("ui", "margins", "page"))
        self.vBoxLayout.setSpacing(AppConfig.get("ui", "spacing", "sm"))
        self.vBoxLayout.addWidget(self.titleLabel)
        self.vBoxLayout.addWidget(self.subtitleLabel)
        self.vBoxLayout.addSpacing(AppConfig.home_subtitle_spacing())
        self.vBoxLayout.addLayout(searchRow)
        self.vBoxLayout.addSpacing(AppConfig.home_search_spacing())
        self.vBoxLayout.addLayout(sectionRow)
        self.vBoxLayout.addWidget(self.stack, 1)

        self._search_worker: SearchWorker | None = None
        self._suggestions_worker: SuggestionsWorker | None = None
        self._last_query = ""
        self._show_suggestions = True
        self._cards: list[SuggestionCard] = []
        self._suggestions_loaded = False
        self._load_triggered = False

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(AppConfig.search_debounce_ms())
        self._debounce.timeout.connect(self._run_search)

        self._scroll_hover_timer = QTimer(self)
        self._scroll_hover_timer.setSingleShot(True)
        self._scroll_hover_timer.setInterval(
            AppConfig.get("ui", "timing", "scroll_hover_ms")
        )
        self._scroll_hover_timer.timeout.connect(self._sync_hover_after_scroll)
        sb = self.scrollArea.verticalScrollBar()
        if sb is not None:
            sb.valueChanged.connect(lambda _: self._scroll_hover_timer.start())

        self.searchEdit.textChanged.connect(self._on_query_changed)
        self.searchEdit.returnPressed.connect(self._run_search)

    def showEvent(self, a0) -> None:
        super().showEvent(a0)
        if not self._load_triggered:
            self._load_triggered = True
            QTimer.singleShot(AppConfig.suggestions_delay_ms(), self._load_suggestions)

    def _fade_grid(self, active: bool) -> None:
        if active:
            effect = QGraphicsOpacityEffect(self.gridHost)
            effect.setOpacity(AppConfig.get("ui", "opacity", "grid_fade"))
            self.gridHost.setGraphicsEffect(effect)
            self.progressRing.start()
            self.progressRing.show()
        else:
            self.gridHost.setGraphicsEffect(None)
            self.progressRing.stop()
            self.progressRing.hide()

    def _sync_hover_after_scroll(self) -> None:
        sync_hover_after_scroll()

    def _stop_worker(self, attr: str) -> None:
        worker = getattr(self, attr, None)
        if worker is not None:
            try:
                worker.finished_with_results.disconnect()
            except TypeError:
                pass
            try:
                worker.failed.disconnect()
            except TypeError:
                pass
            worker.quit()
            worker.wait()
            worker.deleteLater()
            setattr(self, attr, None)

    def _load_suggestions(self) -> None:
        self._show_suggestions = True
        self.sectionTitle.setText("Suggestions")
        self._fade_grid(True)
        self._stop_worker("_suggestions_worker")
        self._suggestions_worker = SuggestionsWorker(
            limit=AppConfig.suggestions_limit(), parent=self
        )
        self._suggestions_worker.finished_with_results.connect(self._on_suggestions)
        self._suggestions_worker.failed.connect(self._on_suggestions_failed)
        self._suggestions_worker.start()

    def _on_suggestions(self, items: list) -> None:
        self._fade_grid(False)
        self._clear_cards()
        self.stack.setCurrentWidget(self.scrollArea)
        for anime in items:
            self._add_card(anime)
        self._suggestions_loaded = True

    def _on_suggestions_failed(self, error: str) -> None:
        self._fade_grid(False)
        self.sectionTitle.setText("Suggestions unavailable")
        self.statusLabel.setText(f"Error: {error}")
        self.statusLabel.setVisible(True)
        logger.warning("Suggestions failed: {}", error)

    def _on_query_changed(self, text: str) -> None:
        text = text.strip()
        if not text:
            if not self._show_suggestions:
                self._show_suggestions = True
                self._restore_suggestions_view()
            return
        self._show_suggestions = False
        self._last_query = text
        self._debounce.start()

    def _run_search(self) -> None:
        query = self.searchEdit.text().strip()
        if not query:
            return
        self._last_query = query
        self._start_search_worker(query)

    def _start_search_worker(self, query: str) -> None:
        self._show_suggestions = False
        self.sectionTitle.setText(f"Searching '{query}'...")
        self.statusLabel.setVisible(False)
        self._fade_grid(True)
        self._stop_worker("_search_worker")
        self._search_worker = SearchWorker(query, parent=self)
        self._search_worker.finished_with_results.connect(self._on_search_results)
        self._search_worker.failed.connect(self._on_search_failed)
        self._search_worker.start()

    def _on_search_results(self, query: str, items: list) -> None:
        if query != self._last_query:
            return
        self._fade_grid(False)
        self._clear_cards()
        self.sectionTitle.setText("Search results")
        if not items:
            self.emptyLabel.setText(f'No results for "{query}".')
            self.stack.setCurrentWidget(self.emptyLabel)
            return
        self.stack.setCurrentWidget(self.scrollArea)
        self.statusLabel.setText(f"{len(items)} results")
        self.statusLabel.setVisible(True)
        for anime in items:
            self._add_card(anime)

    def _on_search_failed(self, query: str, error: str) -> None:
        if query != self._last_query:
            return
        self._fade_grid(False)
        self.sectionTitle.setText("Search failed")
        self.statusLabel.setText(f"Error: {error}")
        self.statusLabel.setVisible(True)
        logger.warning("Search failed for '{}': {}", query, error)

    def _restore_suggestions_view(self) -> None:
        self._clear_cards()
        self.sectionTitle.setText("Suggestions")
        self.statusLabel.setVisible(False)
        if self._suggestions_loaded:
            self._load_suggestions()

    def _add_card(self, anime: Anime) -> None:
        card = SuggestionCard(anime, self.gridHost)
        card.clicked.connect(signalBus.openAnimeDetail.emit)
        self.gridLayout.addWidget(card)
        self._cards.append(card)

    def _clear_cards(self) -> None:
        for card in self._cards:
            try:
                card.clicked.disconnect()
            except TypeError:
                pass
            card.hide()
            self.gridLayout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        QCoreApplication.processEvents()

    def refresh_theme(self) -> None:
        bg = interface_background()
        vp = self.scrollArea.viewport()
        if vp is not None:
            vp.setStyleSheet(f"background: {bg};")  # type: ignore[union-attr]
        self.gridHost.setStyleSheet(f"background: {bg};")
