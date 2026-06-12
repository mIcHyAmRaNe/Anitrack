"""QThread workers that run API calls off the main thread."""

from __future__ import annotations

from loguru import logger
from PyQt6.QtCore import QThread, pyqtSignal

from ..config.app_config import AppConfig
from ..models.anime import Anime
from ..services.api_client import JikanError
from ..services.api_client import client as jikan_client


def _emit_run_result(
    worker: QThread,
    op_label: str,
    fn,
    *,
    on_success,
    on_error,
) -> None:
    """Run ``fn`` in a worker thread, mapping errors and interruption to signals.

    ``on_success(data)`` and ``on_error(message)`` are callbacks because the
    SearchWorker and SuggestionsWorker signals carry slightly different payloads.
    """
    try:
        data = fn()
    except JikanError as exc:
        if not worker.isInterruptionRequested():
            logger.warning("{} failed: {}", op_label, exc)
            on_error(str(exc))
        return
    except Exception as exc:
        if not worker.isInterruptionRequested():
            logger.error("Unexpected {} error: {}", op_label, exc)
            on_error(str(exc))
        return
    if worker.isInterruptionRequested():
        return
    on_success(data)


class SearchWorker(QThread):
    finished_with_results = pyqtSignal(str, list)
    failed = pyqtSignal(str, str)

    def __init__(
        self,
        query: str,
        limit: int = AppConfig.search_results_limit(),
        parent=None,
    ) -> None:
        super().__init__(parent)
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if not isinstance(limit, int) or limit < 1 or limit > 50:
            raise ValueError("limit must be an int between 1 and 50")
        self._query = query.strip()
        self._limit = limit

    @property
    def query(self) -> str:
        return self._query

    def run(self) -> None:
        def on_success(data):
            items = [Anime.from_jikan(d) for d in (data.get("data") or [])]
            logger.info("Search '{}' returned {} results", self._query, len(items))
            self.finished_with_results.emit(self._query, items)

        _emit_run_result(
            self,
            f"Search for '{self._query}'",
            lambda: jikan_client().search_anime(self._query, limit=self._limit),
            on_success=on_success,
            on_error=lambda msg: self.failed.emit(self._query, msg),
        )


class SuggestionsWorker(QThread):
    finished_with_results = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, limit: int = AppConfig.suggestions_limit(), parent=None) -> None:
        super().__init__(parent)
        if not isinstance(limit, int) or limit < 1 or limit > 50:
            raise ValueError("limit must be an int between 1 and 50")
        self._limit = limit

    def run(self) -> None:
        def on_success(data):
            items = [Anime.from_jikan(d) for d in data]
            logger.info("Fetched {} suggestions", len(items))
            self.finished_with_results.emit(items)

        _emit_run_result(
            self,
            "Suggestions fetch",
            lambda: jikan_client().get_top_anime(limit=self._limit),
            on_success=on_success,
            on_error=lambda msg: self.failed.emit(msg),
        )


class FetchDetailWorker(QThread):
    finished_ok = pyqtSignal(int, dict, list, list, list)

    def __init__(self, mal_id: int, parent=None) -> None:
        super().__init__(parent)
        if not isinstance(mal_id, int) or isinstance(mal_id, bool) or mal_id <= 0:
            raise ValueError("mal_id must be a positive int")
        self._mal_id = mal_id

    @property
    def mal_id(self) -> int:
        return self._mal_id

    def run(self) -> None:
        from ..services.anime_service import fetch_detail

        result = fetch_detail(self._mal_id)
        if self.isInterruptionRequested():
            return
        self.finished_ok.emit(self._mal_id, *result)
