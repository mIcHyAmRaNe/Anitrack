"""Library list pages — one per AnimeStatus filter."""

from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    Action,
    CaptionLabel,
    ComboBox,
    MessageBox,
    RoundMenu,
    SearchLineEdit,
    StrongBodyLabel,
    TableWidget,
    TitleLabel,
    ToolTipFilter,
    TransparentToolButton,
)
from qfluentwidgets import FluentIcon as FIF

from ...models.anime import Anime, AnimeStatus
from ...models.library import get_library
from ...services.image_cache import image_loader
from ..signal_bus import signalBus

_SELECTED = "\u2611"  # ☑
_UNSELECTED = "\u2610"  # ☐
_EMPTY_FILTERS: dict[AnimeStatus, str] = {
    AnimeStatus.WATCHING: "You're not watching anything yet.",
    AnimeStatus.COMPLETED: "No completed anime yet.",
    AnimeStatus.ON_HOLD: "Nothing on hold.",
    AnimeStatus.PLAN: "No anime in your plan.",
    AnimeStatus.DROPPED: "No dropped anime.",
}


def _centered_widget(child: QWidget, margins=(8, 0, 8, 0)) -> QWidget:
    """Wrap ``child`` in a QWidget whose layout centres it horizontally."""
    holder = QWidget()
    layout = QHBoxLayout(holder)
    layout.setContentsMargins(*margins)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(child)
    return holder


class _ThumbLabel(QLabel):
    def __init__(self, url: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._url = url
        self.setFixedSize(50, 70)
        self.setScaledContents(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if url:
            image_loader().load(url, callback=self._on_image)

    def _on_image(self, url: str, pix) -> None:
        if url == self._url:
            self.setPixmap(
                pix.scaled(
                    self.size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )


class ListPage(QWidget):
    def __init__(self, status: AnimeStatus, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        if not isinstance(status, AnimeStatus):
            raise ValueError("status must be an AnimeStatus enum value")
        self._status = status
        self._all_items: list[Anime] = []
        self._table_items: list[Anime] = []
        self._selection_mode = False
        self._selected_ids: set[int] = set()
        self._filter_visible = True
        self.setObjectName(f"listInterface_{status.value}")

        headerRow = QHBoxLayout()
        self.titleLabel = TitleLabel(status.label, self)
        self.countLabel = StrongBodyLabel("", self)
        headerRow.addWidget(self.titleLabel)
        headerRow.addStretch(1)
        headerRow.addWidget(self.countLabel)

        self.searchEdit = SearchLineEdit(self)
        self.searchEdit.setPlaceholderText("Search in library...")
        self.searchEdit.setFixedWidth(260)
        self.searchEdit.setClearButtonEnabled(True)
        self.searchEdit.textChanged.connect(self._apply_filters)

        self.typeCombo = ComboBox(self)
        self.typeCombo.setPlaceholderText("Type")
        self.typeCombo.addItem("All Types", userData="")
        self.typeCombo.setMinimumWidth(110)
        self.typeCombo.currentIndexChanged.connect(self._apply_filters)

        self.genreCombo = ComboBox(self)
        self.genreCombo.setPlaceholderText("Genre")
        self.genreCombo.addItem("All Genres", userData="")
        self.genreCombo.setMinimumWidth(120)
        self.genreCombo.currentIndexChanged.connect(self._apply_filters)

        self.statusFilterCombo = ComboBox(self)
        self.statusFilterCombo.setPlaceholderText("Status")
        self.statusFilterCombo.addItem("Any Status", userData="")
        for s in ["Airing", "Finished Airing", "Currently Airing", "Not yet aired"]:
            self.statusFilterCombo.addItem(s, userData=s)
        self.statusFilterCombo.setMinimumWidth(120)
        self.statusFilterCombo.currentIndexChanged.connect(self._apply_filters)

        self.scoreCombo = ComboBox(self)
        self.scoreCombo.setPlaceholderText("Min Score")
        self.scoreCombo.addItem("Any Score", userData="")
        for s in [9, 8, 7, 6, 5]:
            self.scoreCombo.addItem(f"{s}+", userData=str(s))
        self.scoreCombo.setMinimumWidth(110)
        self.scoreCombo.currentIndexChanged.connect(self._apply_filters)

        self.resetBtn = TransparentToolButton(FIF.CANCEL, self)
        self.resetBtn.setToolTip("Reset filters")
        self.resetBtn.installEventFilter(ToolTipFilter(self.resetBtn, 300))
        self.resetBtn.clicked.connect(self._reset_filters)

        self.toggleFilterBtn = TransparentToolButton(FIF.FILTER, self)
        self.toggleFilterBtn.setToolTip("Toggle filters")
        self.toggleFilterBtn.installEventFilter(
            ToolTipFilter(self.toggleFilterBtn, 300)
        )
        self.toggleFilterBtn.clicked.connect(self._toggle_filters)

        self.selectBtn = TransparentToolButton(FIF.CHECKBOX, self)
        self.selectBtn.setToolTip("Select anime")
        self.selectBtn.installEventFilter(ToolTipFilter(self.selectBtn, 300))
        self.selectBtn.clicked.connect(self._toggle_selection_mode)

        filterRow = QHBoxLayout()
        filterRow.setSpacing(8)
        filterRow.addWidget(self.searchEdit)
        filterRow.addSpacing(4)
        filterRow.addWidget(self.typeCombo)
        filterRow.addWidget(self.genreCombo)
        filterRow.addWidget(self.statusFilterCombo)
        filterRow.addWidget(self.scoreCombo)
        filterRow.addWidget(self.resetBtn)
        filterRow.addStretch(1)
        filterRow.addWidget(self.toggleFilterBtn)
        filterRow.addWidget(self.selectBtn)

        self.selectionToolbar = QWidget(self)
        self.selectionToolbar.setVisible(False)
        st_layout = QHBoxLayout(self.selectionToolbar)
        st_layout.setContentsMargins(0, 0, 0, 0)
        st_layout.setSpacing(8)

        self.cancelSelectBtn = TransparentToolButton(FIF.CANCEL, self.selectionToolbar)
        self.cancelSelectBtn.setToolTip("Exit selection mode")
        self.cancelSelectBtn.installEventFilter(
            ToolTipFilter(self.cancelSelectBtn, 300)
        )
        self.cancelSelectBtn.clicked.connect(self._toggle_selection_mode)
        st_layout.addWidget(self.cancelSelectBtn)
        st_layout.addSpacing(8)

        self.selectAllBtn = QPushButton("Select All", self.selectionToolbar)
        self.selectAllBtn.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.selectAllBtn.clicked.connect(self._select_all)
        st_layout.addWidget(self.selectAllBtn)

        self.deselectAllBtn = QPushButton("Deselect All", self.selectionToolbar)
        self.deselectAllBtn.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.deselectAllBtn.clicked.connect(self._deselect_all)
        st_layout.addWidget(self.deselectAllBtn)

        st_layout.addStretch(1)

        self.deleteSelectedBtn = QPushButton("Delete Selected", self.selectionToolbar)
        self.deleteSelectedBtn.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.deleteSelectedBtn.clicked.connect(self._delete_selected)
        st_layout.addWidget(self.deleteSelectedBtn)

        self.table = TableWidget(self)
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)
        self.table.setWordWrap(False)
        self.table.setRowCount(0)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["", "Title", "Type", "Score", "Airing", "Progress", "", ""]
        )
        cw = [32, 0, 260, 80, 70, 120, 100, 50]
        title_col_w = 50 + 20
        self.table.setColumnWidth(0, cw[0])
        self.table.setColumnWidth(1, title_col_w)
        self.table.setColumnWidth(2, cw[2])
        self.table.setColumnWidth(3, cw[3])
        self.table.setColumnWidth(4, cw[4])
        self.table.setColumnWidth(5, cw[5])
        self.table.setColumnWidth(6, cw[6])
        self.table.setColumnWidth(7, cw[7])
        self.table.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(TableWidget.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        hdr = self.table.horizontalHeader()
        if hdr is not None:
            hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            for col, width in [
                (3, cw[3]),
                (4, cw[4]),
                (5, cw[5]),
                (6, cw[6]),
                (7, cw[7]),
            ]:
                hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            hdr.setDefaultAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )

        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.installEventFilter(self)

        self.emptyLabel = CaptionLabel("", self.table)
        self.emptyLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.emptyLabel.hide()

        v = QVBoxLayout(self)
        v.setContentsMargins(36, 28, 36, 28)
        v.setSpacing(12)
        v.addLayout(headerRow)
        v.addLayout(filterRow)
        v.addWidget(self.selectionToolbar)
        v.addWidget(self.table, 1)

        signalBus.libraryChanged.connect(self.refresh)
        self.refresh()

    def showEvent(self, a0) -> None:
        super().showEvent(a0)
        self.refresh()

    def refresh(self) -> None:
        self._selected_ids.clear()
        if self._selection_mode:
            self._exit_selection_mode()
        self._all_items = get_library().in_status(self._status)
        self._populate_filter_options()
        self._apply_filters()

    def _populate_filter_options(self) -> None:
        types = sorted({a.anime_type for a in self._all_items if a.anime_type})
        genres = sorted({g for a in self._all_items for g in a.genres})
        current_type = self.typeCombo.currentData()
        current_genre = self.genreCombo.currentData()

        self.typeCombo.blockSignals(True)
        self.typeCombo.clear()
        self.typeCombo.addItem("All Types", userData="")
        for t in types:
            self.typeCombo.addItem(t, userData=t)
        if current_type:
            idx = self.typeCombo.findData(current_type)
            if idx >= 0:
                self.typeCombo.setCurrentIndex(idx)
        self.typeCombo.blockSignals(False)

        self.genreCombo.blockSignals(True)
        self.genreCombo.clear()
        self.genreCombo.addItem("All Genres", userData="")
        for g in genres:
            self.genreCombo.addItem(g, userData=g)
        if current_genre:
            idx = self.genreCombo.findData(current_genre)
            if idx >= 0:
                self.genreCombo.setCurrentIndex(idx)
        self.genreCombo.blockSignals(False)

    def _apply_filters(self) -> None:
        query = self.searchEdit.text().strip().lower()
        selected_type = self.typeCombo.currentData()
        selected_genre = self.genreCombo.currentData()
        selected_status = self.statusFilterCombo.currentData()
        min_score = self.scoreCombo.currentData()

        items = self._all_items
        if query:
            items = [a for a in items if query in (a.title or "").lower()]
        if selected_type:
            items = [a for a in items if a.anime_type == selected_type]
        if selected_genre:
            items = [a for a in items if selected_genre in a.genres]
        if selected_status:
            items = [a for a in items if a.status == selected_status]
        if min_score:
            try:
                threshold = int(min_score)
                items = [
                    a for a in items if a.score is not None and a.score >= threshold
                ]
            except ValueError:
                pass

        items.sort(key=lambda a: (not a.favorite, -(a.score or 0)))
        self._table_items = items
        self._populate_table(items)

        n = len(items)
        self.countLabel.setText(f"{n} anime{'s' if n != 1 else ''}")
        if n == 0:
            self.emptyLabel.setText(
                "No matches found." if query else _EMPTY_FILTERS[self._status]
            )
            self.emptyLabel.resize(self.table.size())
            self.emptyLabel.show()
        else:
            self.emptyLabel.hide()

    def _reset_filters(self) -> None:
        self.searchEdit.clear()
        self.typeCombo.setCurrentIndex(0)
        self.genreCombo.setCurrentIndex(0)
        self.statusFilterCombo.setCurrentIndex(0)
        self.scoreCombo.setCurrentIndex(0)

    def _toggle_filters(self) -> None:
        self._filter_visible = not self._filter_visible
        for w in (
            self.typeCombo,
            self.genreCombo,
            self.statusFilterCombo,
            self.scoreCombo,
            self.resetBtn,
        ):
            w.setVisible(self._filter_visible)

    def _toggle_selection_mode(self) -> None:
        if self._selection_mode:
            self._exit_selection_mode()
        else:
            self._enter_selection_mode()

    def _enter_selection_mode(self) -> None:
        self._selection_mode = True
        self.selectBtn.setIcon(FIF.CANCEL.icon())
        self.selectionToolbar.setVisible(True)
        self.table.setColumnWidth(0, 32)
        self._update_delete_button()
        self._populate_table(self._table_items)

    def _exit_selection_mode(self) -> None:
        self._selection_mode = False
        self._selected_ids.clear()
        self.selectBtn.setIcon(FIF.CHECKBOX.icon())
        self.selectionToolbar.setVisible(False)
        self._populate_table(self._table_items)

    def _select_all(self) -> None:
        self._selected_ids = {a.mal_id for a in self._table_items}
        self._update_delete_button()
        self._populate_table(self._table_items)

    def _deselect_all(self) -> None:
        self._selected_ids.clear()
        self._update_delete_button()
        self._populate_table(self._table_items)

    def _update_delete_button(self) -> None:
        self.deleteSelectedBtn.setEnabled(len(self._selected_ids) > 0)

    def _delete_selected(self) -> None:
        if not self._selected_ids:
            return
        n = len(self._selected_ids)
        msgBox = MessageBox(
            "Remove Anime?",
            f"Remove {n} anime{'s' if n != 1 else ''} from your library?\n\nThis cannot be undone.",
            self,
        )
        msgBox.yesSignal.connect(self._do_delete_selected)
        msgBox.exec()

    def _do_delete_selected(self) -> None:
        lib = get_library()
        for mal_id in list(self._selected_ids):
            anime = lib.get(mal_id)
            lib.remove(mal_id)
            if anime is not None:
                signalBus.libraryRemoved.emit(anime)
        self._selected_ids.clear()
        signalBus.libraryChanged.emit()

    def eventFilter(self, a0, a1) -> bool:
        if a0 is self.table and a1 is not None and a1.type() == QEvent.Type.Resize:
            if self.emptyLabel.isVisible():
                hdr = self.table.horizontalHeader()
                body_top = hdr.height() if hdr is not None and hdr.isVisible() else 30
                self.emptyLabel.setGeometry(
                    0, body_top, self.table.width(), self.table.height() - body_top
                )
        return super().eventFilter(a0, a1)

    def _populate_table(self, items: list[Anime]) -> None:
        self.table.setRowCount(len(items))

        for row, anime in enumerate(items):
            is_selected = anime.mal_id in self._selected_ids

            cb_label = QLabel(_SELECTED if is_selected else _UNSELECTED)
            self.table.setCellWidget(
                row, 0, _centered_widget(cb_label, margins=(0, 0, 0, 0))
            )

            thumb_host = QWidget()
            thumb_layout = QHBoxLayout(thumb_host)
            thumb_layout.setContentsMargins(6, 4, 6, 4)
            thumb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumb_layout.addWidget(_ThumbLabel(anime.image_url))
            self.table.setCellWidget(row, 1, thumb_host)
            self.table.setRowHeight(row, 82)

            title_widget = QWidget()
            title_layout = QVBoxLayout(title_widget)
            title_layout.setContentsMargins(12, 6, 12, 6)
            title_layout.setSpacing(2)

            title_label = StrongBodyLabel(anime.title or "Unknown")
            title_label.setWordWrap(False)
            title_layout.addWidget(title_label)

            if anime.favorite:
                fav_label = StrongBodyLabel("\u2665 Favorite")
                title_layout.addWidget(fav_label)

            self.table.setCellWidget(row, 2, title_widget)

            type_label = StrongBodyLabel(anime.anime_type or "\u2014")
            self.table.setCellWidget(row, 3, _centered_widget(type_label))

            score_label = StrongBodyLabel(
                f"\u2605 {anime.score:.2f}" if anime.score else "\u2014"
            )
            self.table.setCellWidget(row, 4, _centered_widget(score_label))

            airing_label = StrongBodyLabel(anime.status or "\u2014")
            self.table.setCellWidget(row, 5, _centered_widget(airing_label))

            prog_text = f"{anime.progress}"
            if anime.episodes:
                prog_text += f" / {anime.episodes}"
            progress_label = StrongBodyLabel(prog_text)
            self.table.setCellWidget(row, 6, _centered_widget(progress_label))

            menu_btn = TransparentToolButton(FIF.MORE, self)
            menu_btn.setFixedSize(32, 32)
            menu_btn.clicked.connect(
                lambda *_, a=anime, b=menu_btn: self._show_row_menu(a, b)
            )
            self.table.setCellWidget(
                row, 7, _centered_widget(menu_btn, margins=(0, 0, 0, 0))
            )

        self.table.setColumnHidden(0, not self._selection_mode)

    def _on_cell_clicked(self, row: int, col: int) -> None:
        if not (0 <= row < len(self._table_items)):
            return
        anime = self._table_items[row]
        if self._selection_mode:
            if anime.mal_id in self._selected_ids:
                self._selected_ids.discard(anime.mal_id)
            else:
                self._selected_ids.add(anime.mal_id)
            self._update_delete_button()
            self._populate_table(self._table_items)
        elif col in (1, 2):
            signalBus.openAnimeDetail.emit(anime)

    def _show_row_menu(self, anime: Anime, btn) -> None:
        menu = RoundMenu(parent=self)
        if self._selection_mode:
            menu.addAction(
                Action(
                    FIF.CHECKBOX,
                    "Deselect" if anime.mal_id in self._selected_ids else "Select",
                    triggered=lambda: self._toggle_row_selection(anime),
                )
            )
            menu.addSeparator()
        status_menu = RoundMenu("Change status", self)
        for s in AnimeStatus:
            status_menu.addAction(
                Action(
                    s.label,
                    triggered=lambda checked, st=s: self._change_status(anime, st),
                )
            )
        menu.addMenu(status_menu)
        menu.addSeparator()
        menu.addAction(
            Action(
                "Remove from library",
                triggered=lambda: self._remove_from_library(anime),
            )
        )
        menu.addAction(
            Action(
                "Unfavorited" if anime.favorite else "Favorite",
                triggered=lambda: self._toggle_favorite(anime),
            )
        )
        if anime.url:
            menu.addSeparator()
            menu.addAction(
                Action(
                    "Open on MyAnimeList",
                    triggered=lambda: QDesktopServices.openUrl(QUrl(anime.url)),
                )
            )
        menu.exec(btn.mapToGlobal(btn.rect().center()))

    def _toggle_row_selection(self, anime: Anime) -> None:
        if anime.mal_id in self._selected_ids:
            self._selected_ids.discard(anime.mal_id)
        else:
            self._selected_ids.add(anime.mal_id)
        self._update_delete_button()
        self._populate_table(self._table_items)

    def _change_status(self, anime: Anime, new_status: AnimeStatus) -> None:
        lib = get_library()
        existing = lib.get(anime.mal_id)
        lib.add(anime, new_status)
        if existing:
            signalBus.libraryStatusChanged.emit(anime, new_status.value)
        else:
            signalBus.libraryAdded.emit(anime)
        signalBus.libraryChanged.emit()

    def _remove_from_library(self, anime: Anime) -> None:
        get_library().remove(anime.mal_id)
        signalBus.libraryRemoved.emit(anime)
        signalBus.libraryChanged.emit()

    def _toggle_favorite(self, anime: Anime) -> None:
        lib = get_library()
        existing = lib.get(anime.mal_id)
        if existing:
            new_val = not existing.favorite
            lib.set_favorite(anime.mal_id, new_val)
            signalBus.libraryFavoriteToggled.emit(anime, new_val)
            signalBus.libraryChanged.emit()
