"""Sync HTTP client for the Jikan v4 API with disk caching and rate limiting."""

from __future__ import annotations

import json
import threading
import time
from typing import Any

import diskcache as dc
import httpx
from loguru import logger

from ..config.app_config import AppConfig
from ..models.anime import validate_mal_id


class JikanError(RuntimeError):
    """Raised when the Jikan API returns an error or all retries are exhausted."""


def _validate_query(query: str) -> None:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")


def _validate_limit(limit: int, *, max_limit: int = 100) -> None:
    if not isinstance(limit, int) or not (1 <= limit <= max_limit):
        raise ValueError(
            f"limit must be an integer between 1 and {max_limit}, got {limit!r}"
        )


class JikanClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        min_interval: float | None = None,
    ) -> None:
        self._base_url = base_url if base_url is not None else AppConfig.api_base_url()
        self._max_retries = (
            max_retries if max_retries is not None else AppConfig.api_max_retries()
        )
        self._min_interval = (
            min_interval if min_interval is not None else AppConfig.api_min_interval()
        )
        self._timeout = timeout if timeout is not None else AppConfig.api_timeout()
        self._session = httpx.Client(
            headers={"User-Agent": "anitrack/0.1", "Accept": "application/json"},
            timeout=self._timeout,
        )
        self._lock = threading.Lock()
        self._last_request = 0.0
        self._cache = dc.Cache(AppConfig.api_cache_dir())
        self._offline = False
        self._offline_checked = 0.0

    @staticmethod
    def is_connected() -> bool:
        try:
            httpx.get("https://api.jikan.moe", timeout=5.0)
            return True
        except httpx.RequestError:
            return False

    def _throttle(self) -> None:
        with self._lock:
            wait = self._min_interval - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()

    def _cache_key(self, path: str, params: dict[str, Any] | None) -> str:
        if not params:
            return path
        return "\x00".join((path, json.dumps(params, sort_keys=True)))

    def _check_offline(self) -> None:
        now = time.monotonic()
        if now - self._offline_checked > 30.0:
            self._offline = not self.is_connected()
            self._offline_checked = now

    def _get(
        self, path: str, params: dict[str, Any] | None = None, *, cache_ttl: float = 0
    ) -> Any:
        url = f"{self._base_url}{path}"
        if cache_ttl > 0:
            key = self._cache_key(path, params)
            cached = self._cache.get(key)
            if cached is not None:
                logger.debug("API cache hit: {}", url)
                return cached
        self._check_offline()
        if self._offline:
            raise JikanError("No internet connection")
        logger.debug("API GET {}", url)
        data = self._request_with_retries(url, params)
        if cache_ttl > 0:
            self._cache.set(self._cache_key(path, params), data, expire=cache_ttl)
        return data

    def _request_with_retries(self, url: str, params: dict[str, Any] | None) -> Any:
        """Execute a single request with retry/backoff. Raise ``JikanError`` on failure."""
        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            self._throttle()
            try:
                resp = self._session.get(url, params=params)
            except httpx.RequestError as exc:
                last_error = exc
                delay = 1.5 * (2**attempt)
                logger.warning(
                    "Network error (attempt {}/{}): {}",
                    attempt + 1,
                    self._max_retries,
                    exc,
                )
                time.sleep(delay)
                continue
            if resp.status_code == 429:
                delay = 2.0 * (2**attempt)
                logger.warning(
                    "Rate limited (attempt {}/{}), backing off {}s",
                    attempt + 1,
                    self._max_retries,
                    delay,
                )
                time.sleep(delay)
                continue
            if resp.status_code >= 500:
                last_error = JikanError(f"Server error {resp.status_code}")
                delay = 1.5 * (2**attempt)
                logger.warning(
                    "Server error {} (attempt {}/{}), retrying in {}s",
                    resp.status_code,
                    attempt + 1,
                    self._max_retries,
                    delay,
                )
                time.sleep(delay)
                continue
            if resp.status_code >= 400:
                raise JikanError(f"Client error {resp.status_code}: {url}")
            return resp.json()
        raise JikanError(
            str(last_error) if last_error else "Request failed after all retries"
        )

    def search_anime(
        self,
        query: str,
        *,
        page: int = 1,
        limit: int = 20,
        sfw: bool = True,
        order_by: str | None = None,
    ) -> dict[str, Any]:
        _validate_query(query)
        _validate_limit(limit)
        params: dict[str, Any] = {
            "q": query.strip(),
            "page": page,
            "limit": limit,
            "sfw": str(sfw).lower(),
        }
        if order_by:
            params["order_by"] = order_by
        return self._get("/anime", params, cache_ttl=300)

    def get_anime_full(self, mal_id: int) -> dict[str, Any]:
        validate_mal_id(mal_id)
        return self._get(f"/anime/{mal_id}/full", cache_ttl=3600)

    def get_recommendations(self, mal_id: int) -> list[dict[str, Any]]:
        validate_mal_id(mal_id)
        return self._data(f"/anime/{mal_id}/recommendations", cache_ttl=3600) or []

    def get_anime_characters(self, mal_id: int) -> list[dict[str, Any]]:
        validate_mal_id(mal_id)
        return self._data(f"/anime/{mal_id}/characters", cache_ttl=3600) or []

    def get_anime_relations(self, mal_id: int) -> list[dict[str, Any]]:
        validate_mal_id(mal_id)
        return self._data(f"/anime/{mal_id}/relations", cache_ttl=3600) or []

    def get_anime_videos(self, mal_id: int) -> dict[str, Any]:
        validate_mal_id(mal_id)
        return self._data(f"/anime/{mal_id}/videos", cache_ttl=1800) or {}

    def get_top_anime(self, limit: int = 12) -> list[dict[str, Any]]:
        _validate_limit(limit)
        return self._data("/top/anime", {"limit": limit}, cache_ttl=3600) or []

    def _data(
        self, path: str, params: dict[str, Any] | None = None, *, cache_ttl: float = 0
    ) -> Any:
        """Return ``.get("data")`` (or an empty container) from a Jikan response."""
        return self._get(path, params, cache_ttl=cache_ttl).get("data")


_client: JikanClient | None = None


def client() -> JikanClient:
    global _client
    if _client is None:
        _client = JikanClient()
    return _client
