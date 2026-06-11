from __future__ import annotations

from loguru import logger
from PyQt6.QtCore import QThread, pyqtSignal

from ..config.app_config import AppConfig
from ..models.anime import Anime
from ..services.api_client import JikanError
from ..services.api_client import client as jikan_client


class SearchWorker(QThread):
    finished_with_results = pyqtSignal(str, list)
    failed = pyqtSignal(str, str)

    def __init__(
        self, query: str, limit: int = AppConfig.search_results_limit(), parent=None
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
        try:
            data = jikan_client().search_anime(self._query, limit=self._limit)
        except JikanError as exc:
            if not self.isInterruptionRequested():
                logger.warning("Search failed for '{}': {}", self._query, exc)
                self.failed.emit(self._query, str(exc))
            return
        except Exception as exc:
            if not self.isInterruptionRequested():
                logger.error("Unexpected search error for '{}': {}", self._query, exc)
                self.failed.emit(self._query, str(exc))
            return
        if self.isInterruptionRequested():
            return
        items = [Anime.from_jikan(d) for d in (data.get("data") or [])]
        logger.info("Search '{}' returned {} results", self._query, len(items))
        self.finished_with_results.emit(self._query, items)


class SuggestionsWorker(QThread):
    finished_with_results = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, limit: int = AppConfig.suggestions_limit(), parent=None) -> None:
        super().__init__(parent)
        if not isinstance(limit, int) or limit < 1 or limit > 50:
            raise ValueError("limit must be an int between 1 and 50")
        self._limit = limit

    def run(self) -> None:
        try:
            data = jikan_client().get_top_anime(limit=self._limit)
        except JikanError as exc:
            if not self.isInterruptionRequested():
                logger.warning("Suggestions fetch failed: {}", exc)
                self.failed.emit(str(exc))
            return
        except Exception as exc:
            if not self.isInterruptionRequested():
                logger.error("Unexpected suggestions error: {}", exc)
                self.failed.emit(str(exc))
            return
        if self.isInterruptionRequested():
            return
        items = [Anime.from_jikan(d) for d in data]
        logger.info("Fetched {} suggestions", len(items))
        self.finished_with_results.emit(items)


class FetchDetailWorker(QThread):
    finished_ok = pyqtSignal(int, dict, list, list, list)

    def __init__(self, mal_id: int, parent=None) -> None:
        super().__init__(parent)
        if not isinstance(mal_id, int) or mal_id <= 0:
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
