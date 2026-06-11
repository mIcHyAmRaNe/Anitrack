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
    isDarkTheme,
    themeColor,
)
from qfluentwidgets import FluentIcon as FIF

from ...config.app_config import AppConfig
from ...models.anime import Anime, AnimeStatus
from ...models.library import get_library
from ...services.image_cache import image_loader
from ...theme import text_color
from ..signal_bus import signalBus


def pill(label: StrongBodyLabel) -> None:
    label.setStyleSheet(
        f"StrongBodyLabel{{background:{themeColor().name()}22;color:{text_color()};"
        f"padding:{AppConfig.get('ui', 'padding', 'pill')};border-radius:{AppConfig.get('ui', 'radius', 'pill')}px;"
        f"font-size:{AppConfig.get('ui', 'font', 'sizes', 'xs')}px;font-weight:{AppConfig.get('ui', 'font', 'weights', 'semibold')};}}"
    )


class _ThumbLabel(QLabel):
    def __init__(self, url: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._url = url
        self.setFixedSize(AppConfig.thumb_w(), AppConfig.thumb_h())
        r = AppConfig.get("ui", "radius", "thumbnail")
        self.setStyleSheet(f"border-radius: {r}px; background: transparent;")
        self.setScaledContents(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if url:
            image_loader().load(url, callback=self._on_image)

    def _on_image(self, url: str, pix) -> None:
        if url == self._url:
            scaled_pix = pix.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setPixmap(scaled_pix)


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
        self.setObjectName(f"listInterface_{status.value}")

        headerRow = QHBoxLayout()
        self.titleLabel = TitleLabel(status.label, self)
        self.countLabel = StrongBodyLabel("", self)
        headerRow.addWidget(self.titleLabel)
        headerRow.addStretch(1)
        headerRow.addWidget(self.countLabel)

        self.searchEdit = SearchLineEdit(self)
        self.searchEdit.setPlaceholderText("Search in library...")
        self.searchEdit.setFixedWidth(AppConfig.get("ui", "sizes", "search_edit_list"))
        self.searchEdit.setClearButtonEnabled(True)
        self.searchEdit.textChanged.connect(self._apply_filters)

        self.typeCombo = ComboBox(self)
        self.typeCombo.setPlaceholderText("Type")
        self.typeCombo.addItem("All Types", userData="")
        self.typeCombo.setMinimumWidth(
            AppConfig.get("ui", "sizes", "combo_min_width_narrow")
        )
        self.typeCombo.currentIndexChanged.connect(self._apply_filters)

        self.genreCombo = ComboBox(self)
        self.genreCombo.setPlaceholderText("Genre")
        self.genreCombo.addItem("All Genres", userData="")
        self.genreCombo.setMinimumWidth(
            AppConfig.get("ui", "sizes", "combo_min_width_wide")
        )
        self.genreCombo.currentIndexChanged.connect(self._apply_filters)

        self.statusFilterCombo = ComboBox(self)
        self.statusFilterCombo.setPlaceholderText("Status")
        self.statusFilterCombo.addItem("Any Status", userData="")
        for s in ["Airing", "Finished Airing", "Currently Airing", "Not yet aired"]:
            self.statusFilterCombo.addItem(s, userData=s)
        self.statusFilterCombo.setMinimumWidth(
            AppConfig.get("ui", "sizes", "combo_min_width_wide")
        )
        self.statusFilterCombo.currentIndexChanged.connect(self._apply_filters)

        self.scoreCombo = ComboBox(self)
        self.scoreCombo.setPlaceholderText("Min Score")
        self.scoreCombo.addItem("Any Score", userData="")
        for s in [9, 8, 7, 6, 5]:
            self.scoreCombo.addItem(f"{s}+", userData=str(s))
        self.scoreCombo.setMinimumWidth(
            AppConfig.get("ui", "sizes", "combo_min_width_narrow")
        )
        self.scoreCombo.currentIndexChanged.connect(self._apply_filters)

        self.resetBtn = TransparentToolButton(FIF.CANCEL, self)
        self.resetBtn.setToolTip("Reset filters")
        self.resetBtn.installEventFilter(
            ToolTipFilter(self.resetBtn, AppConfig.tooltip_filter_ms())
        )
        self.resetBtn.clicked.connect(self._reset_filters)

        self.toggleFilterBtn = TransparentToolButton(FIF.FILTER, self)
        self.toggleFilterBtn.setToolTip("Toggle filters")
        self.toggleFilterBtn.installEventFilter(
            ToolTipFilter(self.toggleFilterBtn, AppConfig.tooltip_filter_ms())
        )
        self.toggleFilterBtn.clicked.connect(self._toggle_filters)

        self.selectBtn = TransparentToolButton(FIF.CHECKBOX, self)
        self.selectBtn.setToolTip("Select anime")
        self.selectBtn.installEventFilter(
            ToolTipFilter(self.selectBtn, AppConfig.tooltip_filter_ms())
        )
        self.selectBtn.clicked.connect(self._toggle_selection_mode)

        filterRow = QHBoxLayout()
        filterRow.setSpacing(AppConfig.get("ui", "spacing", "sm"))
        filterRow.addWidget(self.searchEdit)
        filterRow.addSpacing(AppConfig.list_filter_row_spacing())
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
        st_layout.setSpacing(AppConfig.get("ui", "spacing", "sm"))

        self.cancelSelectBtn = TransparentToolButton(FIF.CANCEL, self.selectionToolbar)
        self.cancelSelectBtn.setToolTip("Exit selection mode")
        self.cancelSelectBtn.installEventFilter(
            ToolTipFilter(self.cancelSelectBtn, AppConfig.tooltip_filter_ms())
        )
        self.cancelSelectBtn.clicked.connect(self._toggle_selection_mode)
        st_layout.addWidget(self.cancelSelectBtn)
        st_layout.addSpacing(AppConfig.list_selection_toolbar_spacing())

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
        self.deleteSelectedBtn.setStyleSheet(f"color: {AppConfig.danger_color()};")
        self.deleteSelectedBtn.clicked.connect(self._delete_selected)
        st_layout.addWidget(self.deleteSelectedBtn)

        self.table = TableWidget(self)
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(AppConfig.get("ui", "radius", "table"))
        self.table.setWordWrap(False)
        self.table.setRowCount(0)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["", "Title", "Type", "Score", "Airing", "Progress", "", ""]
        )
        cw = AppConfig.table_column_widths()
        title_col_w = AppConfig.thumb_w() + AppConfig.table_title_col_extra()
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
            cw = AppConfig.table_column_widths()
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
        v.setContentsMargins(*AppConfig.get("ui", "margins", "page"))
        v.setSpacing(AppConfig.get("ui", "spacing", "md"))
        v.addLayout(headerRow)
        v.addLayout(filterRow)
        v.addWidget(self.selectionToolbar)
        v.addWidget(self.table, 1)

        signalBus.libraryChanged.connect(self.refresh)
        self.refresh()

    def showEvent(self, a0) -> None:
        super().showEvent(a0)
        self.refresh()

    def refresh_theme(self) -> None:
        self._populate_table(self._table_items)

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
            if query:
                self.emptyLabel.setText("No matches found.")
            else:
                self.emptyLabel.setText(
                    {
                        AnimeStatus.WATCHING: "You're not watching anything yet.",
                        AnimeStatus.COMPLETED: "No completed anime yet.",
                        AnimeStatus.ON_HOLD: "Nothing on hold.",
                        AnimeStatus.PLAN: "No anime in your plan.",
                        AnimeStatus.DROPPED: "No dropped anime.",
                    }[self._status]
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
        self._filter_visible = getattr(self, "_filter_visible", True)
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
        self.table.setColumnWidth(0, AppConfig.table_column_widths()[0])
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
                body_top = (
                    hdr.height()
                    if hdr is not None and hdr.isVisible()
                    else AppConfig.table_header_fallback_height()
                )
                self.emptyLabel.setGeometry(
                    0, body_top, self.table.width(), self.table.height() - body_top
                )
        return super().eventFilter(a0, a1)

    def _populate_table(self, items: list[Anime]) -> None:
        self.table.setRowCount(0)
        self.table.setRowCount(len(items))
        dark = isDarkTheme()
        tc = AppConfig.text_color(dark)
        fs = AppConfig.get("ui", "font", "sizes")
        sel_color = AppConfig.selection_color()

        for row, anime in enumerate(items):
            is_selected = anime.mal_id in self._selected_ids
            row_bg = f"background: {sel_color}44;" if is_selected else ""

            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_label = QLabel("\u2611" if is_selected else "\u2610")
            if is_selected:
                cb_label.setStyleSheet(f"color: {sel_color};")
            cb_layout.addWidget(cb_label)
            self.table.setCellWidget(row, 0, cb_widget)

            thumb_host = QWidget()
            thumb_host.setStyleSheet(row_bg)
            thumb_layout = QHBoxLayout(thumb_host)
            thumb_layout.setContentsMargins(
                *AppConfig.get("ui", "margins", "list_thumbnail")
            )
            thumb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumb_layout.addWidget(_ThumbLabel(anime.image_url))
            self.table.setCellWidget(row, 1, thumb_host)
            self.table.setRowHeight(row, AppConfig.table_row_height())

            title_widget = QWidget()
            title_widget.setStyleSheet(row_bg)
            title_layout = QVBoxLayout(title_widget)
            title_layout.setContentsMargins(
                *AppConfig.get("ui", "margins", "list_title")
            )
            title_layout.setSpacing(AppConfig.list_title_spacing())

            title_label = StrongBodyLabel(anime.title or "Unknown")
            title_label.setStyleSheet(f"font-size:{fs['md']}px;color:{tc};")
            title_label.setWordWrap(False)
            title_layout.addWidget(title_label)

            if anime.favorite:
                fav_label = StrongBodyLabel("\u2665 Favorite")
                fav_label.setStyleSheet(f"font-size:{fs['xs']}px;color:{tc};")
                title_layout.addWidget(fav_label)

            self.table.setCellWidget(row, 2, title_widget)

            type_label = StrongBodyLabel(anime.anime_type or "\u2014")
            pill(type_label)
            type_widget = QWidget()
            type_widget.setStyleSheet(row_bg)
            type_layout = QHBoxLayout(type_widget)
            type_layout.setContentsMargins(*AppConfig.get("ui", "margins", "list_cell"))
            type_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            type_layout.addWidget(type_label)
            self.table.setCellWidget(row, 3, type_widget)

            score_widget = QWidget()
            score_widget.setStyleSheet(row_bg)
            score_layout = QHBoxLayout(score_widget)
            score_layout.setContentsMargins(
                *AppConfig.get("ui", "margins", "list_cell")
            )
            score_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            score_label = StrongBodyLabel(
                f"\u2605 {anime.score:.2f}" if anime.score else "\u2014"
            )
            score_label.setStyleSheet(f"font-size:{fs['sm']}px;color:{tc};")
            score_layout.addWidget(score_label)
            self.table.setCellWidget(row, 4, score_widget)

            airing_label = StrongBodyLabel(anime.status or "\u2014")
            pill(airing_label)
            status_widget = QWidget()
            status_widget.setStyleSheet(row_bg)
            status_layout = QHBoxLayout(status_widget)
            status_layout.setContentsMargins(
                *AppConfig.get("ui", "margins", "list_cell")
            )
            status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_layout.addWidget(airing_label)
            self.table.setCellWidget(row, 5, status_widget)

            prog_text = f"{anime.progress}"
            if anime.episodes:
                prog_text += f" / {anime.episodes}"
            prog_label = StrongBodyLabel(prog_text)
            prog_label.setStyleSheet(f"font-size:{fs['sm']}px;color:{tc};")
            progress_widget = QWidget()
            progress_widget.setStyleSheet(row_bg)
            progress_layout = QHBoxLayout(progress_widget)
            progress_layout.setContentsMargins(
                *AppConfig.get("ui", "margins", "list_cell")
            )
            progress_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            progress_layout.addWidget(prog_label)
            self.table.setCellWidget(row, 6, progress_widget)

            menu_btn = TransparentToolButton(FIF.MORE, self)
            menu_btn.setFixedSize(
                AppConfig.get("ui", "sizes", "menu_button"),
                AppConfig.get("ui", "sizes", "menu_button"),
            )
            menu_btn.clicked.connect(
                lambda *_, a=anime, b=menu_btn: self._show_row_menu(a, b)
            )
            menu_widget = QWidget()
            menu_widget.setStyleSheet(row_bg)
            menu_layout = QHBoxLayout(menu_widget)
            menu_layout.setContentsMargins(0, 0, 0, 0)
            menu_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            menu_layout.addWidget(menu_btn)
            self.table.setCellWidget(row, 7, menu_widget)

        if self._selection_mode:
            self.table.setColumnHidden(0, False)
        else:
            self.table.setColumnHidden(0, True)

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
        if existing:
            lib.add(anime, new_status)
            signalBus.libraryStatusChanged.emit(anime, new_status.value)
        else:
            lib.add(anime, new_status)
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
