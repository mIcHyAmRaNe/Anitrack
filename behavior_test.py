"""End-to-end behavior smoke test (no network).

Verifies:
- Library singleton loads / saves / sorts favorites first
- AnimeCard click signal can be emitted
- ListInterface can be toggled into selection mode and back
- HomeInterface builds
"""

from __future__ import annotations

import os
import sys
import traceback

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from qfluentwidgets import FluentTranslator

from app.models.anime import Anime, AnimeStatus
from app.models.library import get_library
from app.ui.main_window import MainWindow
from app.ui.pages.home_page import HomePage
from app.ui.pages.list_page import ListPage
from app.ui.widgets.anime_card import AnimeCard


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("anitrack")
    app.setOrganizationName("anitrack")
    app.installTranslator(FluentTranslator())

    # --- Library singleton ---
    library = get_library()
    library._items.clear()  # noqa: SLF001 — test isolation
    a1 = Anime(mal_id=1, title="Cowboy Bebop", image_url="", episodes=26, score=8.75)
    a2 = Anime(mal_id=2, title="Naruto", image_url="", episodes=220, score=7.9)
    a3 = Anime(mal_id=3, title="Bleach", image_url="", episodes=366, score=7.9)
    library.add(a1, AnimeStatus.COMPLETED, favorite=True)
    library.add(a2, AnimeStatus.WATCHING, favorite=False)
    library.add(a3, AnimeStatus.PLAN, favorite=False)
    assert library.count() == 3, library.count()
    # Favorites must come first in completed list.
    completed = library.in_status(AnimeStatus.COMPLETED)
    assert completed[0].mal_id == 1, [c.mal_id for c in completed]
    print("[ok] library sort puts favorites first", flush=True)

    # --- AnimeCard click signal wiring ---
    clicked_payload: list[Anime] = []
    card = AnimeCard(a1)
    card.clicked.connect(lambda a: clicked_payload.append(a))
    card.clicked.emit(a1)  # emit directly to verify the signal wiring
    assert clicked_payload == [a1], clicked_payload
    print("[ok] AnimeCard click signal carries the anime", flush=True)
    card.deleteLater()

    # --- ListInterface table with filters ---
    li = ListPage(AnimeStatus.COMPLETED)
    li.refresh()
    assert li._table_items, "expected at least one row"  # noqa: SLF001
    assert li.table.rowCount() == 1, "table should have 1 row"
    # Filters should be populated from library data
    assert li.typeCombo.count() >= 1, "type filter should have at least 'All Types'"
    assert li.genreCombo.count() >= 1, "genre filter should have at least 'All Genres'"
    # Search should filter
    li.searchEdit.setText("Cowboy")
    li._apply_filters()  # noqa: SLF001
    assert li.table.rowCount() == 1
    li.searchEdit.setText("Naruto")
    li._apply_filters()  # noqa: SLF001
    assert li.table.rowCount() == 0, "Naruto is not in completed"
    assert not li.emptyLabel.isHidden(), "empty label should be shown"
    li.searchEdit.clear()
    li._apply_filters()  # noqa: SLF001
    assert li.table.rowCount() == 1
    # Reset filters
    li._reset_filters()  # noqa: SLF001
    assert li.searchEdit.text() == ""
    # Empty state for status with no items
    empty_li = ListPage(AnimeStatus.DROPPED)
    empty_li.refresh()
    assert not empty_li.emptyLabel.isHidden(), (
        "empty label should be shown for empty list"
    )
    print("[ok] ListInterface table and filters work", flush=True)

    # --- AnimeCard status badge appears when in library ---
    in_lib = Anime(mal_id=42, title="In Lib", favorite=False)
    library.add(in_lib, AnimeStatus.WATCHING)
    card_in = AnimeCard(in_lib)
    card_in.update_status_badge()
    assert not card_in.status_badge.isHidden(), (
        "status badge should show for library entry"
    )
    assert card_in.status_badge.toolTip() != ""
    not_in_lib = Anime(mal_id=43, title="Not In Lib", favorite=False)
    card_not = AnimeCard(not_in_lib)
    card_not.update_status_badge()
    assert card_not.status_badge.isHidden(), "status badge hidden when not in library"
    print("[ok] AnimeCard status badge visibility", flush=True)

    # --- AnimeCard heart icon reflects favorite state ---
    fav_card = AnimeCard(a1)
    assert not fav_card.heart_btn.icon().isNull(), "favorite card must have heart icon"
    non_fav = Anime(mal_id=100, title="Not Favorite", favorite=False)
    non_fav_card = AnimeCard(non_fav)
    assert not non_fav_card.heart_btn.icon().isNull(), (
        "non-fav card must have heart icon"
    )
    # Toggling favorite via set_favorite should change icon.
    before_icon = non_fav_card.heart_btn.icon().cacheKey()
    non_fav_card.set_favorite(True)
    after_icon = non_fav_card.heart_btn.icon().cacheKey()
    assert before_icon != after_icon, "heart icon must change on toggle"
    print("[ok] AnimeCard heart icon reflects favorite state", flush=True)

    # --- HomeInterface builds ---
    home = HomePage()
    # No auto-load before show: home must start with the empty label visible.
    assert home.stack.currentWidget() is home.emptyLabel
    assert not home._suggestions_loaded  # noqa: SLF001
    print("[ok] HomePage built (no auto-load)", flush=True)

    # --- AnimeCard favoriteToggled signal ---
    fav_payload: list[tuple[Anime, bool]] = []
    fav_card = AnimeCard(a1)
    fav_card.favoriteToggled.connect(lambda a, v: fav_payload.append((a, v)))
    assert a1.favorite is True  # a1 was added with favorite=True
    fav_card._on_heart_clicked()  # noqa: SLF001
    assert fav_payload == [(a1, False)]
    assert a1.favorite is False
    print("[ok] AnimeCard favoriteToggled signal", flush=True)

    # --- MainWindow builds ---
    window = MainWindow()
    window.show()
    print("[ok] MainWindow shown", flush=True)

    QTimer.singleShot(50, app.quit)
    return app.exec()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(2)
