from __future__ import annotations

from loguru import logger
from PyQt6.QtCore import QCoreApplication, Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
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
from ..signal_bus import signalBus
from ..widgets.suggestion_card import SuggestionCard
from ..workers import SearchWorker, SuggestionsWorker

EMPTY_STATE_HINT = "Search an anime by title to get started."


class HomePage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("homeInterface")

        self.titleLabel = TitleLabel("Anitrack", self)
        sf = QFont(AppConfig.font_family())
        sf.setPointSize(11)
        self.subtitleLabel = CaptionLabel("Search and add anime to your library.", self)
        self.subtitleLabel.setFont(sf)

        self.searchEdit = SearchLineEdit(self)
        self.searchEdit.setPlaceholderText(
            "Search anime on MyAnimeList\u2026  (Ctrl+F)"
        )
        self.searchEdit.setClearButtonEnabled(True)
        self.searchEdit.setFixedWidth(520)

        self.progressRing = IndeterminateProgressRing(self)
        self.progressRing.setFixedSize(20, 20)
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
        self.scrollArea.enableTransparentBackground()
        self.scrollArea.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
        )
        viewport = self.scrollArea.viewport()
        if viewport is not None:
            viewport.setStyleSheet("background:transparent;")

        self.gridHost = QWidget(self.scrollArea)
        self.gridLayout = FlowLayout(self.gridHost, needAni=False)
        self.gridLayout.setContentsMargins(20, 20, 20, 20)
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
        self.vBoxLayout.setContentsMargins(36, 28, 36, 28)
        self.vBoxLayout.setSpacing(8)
        self.vBoxLayout.addWidget(self.titleLabel)
        self.vBoxLayout.addWidget(self.subtitleLabel)
        self.vBoxLayout.addSpacing(6)
        self.vBoxLayout.addLayout(searchRow)
        self.vBoxLayout.addSpacing(12)
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
        self._debounce.setInterval(350)
        self._debounce.timeout.connect(self._run_search)

        self.searchEdit.textChanged.connect(self._on_query_changed)
        self.searchEdit.returnPressed.connect(self._run_search)

    def showEvent(self, a0) -> None:
        super().showEvent(a0)
        if not self._load_triggered:
            self._load_triggered = True
            QTimer.singleShot(200, self._load_suggestions)

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
        self.progressRing.start()
        self.progressRing.show()
        self._stop_worker("_suggestions_worker")
        self._suggestions_worker = SuggestionsWorker(
            limit=AppConfig.suggestions_limit(), parent=self
        )
        self._suggestions_worker.finished_with_results.connect(self._on_suggestions)
        self._suggestions_worker.failed.connect(self._on_suggestions_failed)
        self._suggestions_worker.start()

    def _on_suggestions(self, items: list) -> None:
        self.progressRing.stop()
        self.progressRing.hide()
        self._clear_cards()
        self.stack.setCurrentWidget(self.scrollArea)
        for anime in items:
            self._add_card(anime)
        self._suggestions_loaded = True

    def _on_suggestions_failed(self, error: str) -> None:
        self.progressRing.stop()
        self.progressRing.hide()
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
        self.progressRing.start()
        self.progressRing.show()
        self._stop_worker("_search_worker")
        self._search_worker = SearchWorker(query, parent=self)
        self._search_worker.finished_with_results.connect(self._on_search_results)
        self._search_worker.failed.connect(self._on_search_failed)
        self._search_worker.start()

    def _on_search_results(self, query: str, items: list) -> None:
        if query != self._last_query:
            return
        self.progressRing.stop()
        self.progressRing.hide()
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
        self.progressRing.stop()
        self.progressRing.hide()
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
