"""Application constants and platform-specific path resolution.

All values returned here are computed on demand and may create directories on
disk. AppConfig is intentionally a class-of-classmethods: there is no global
state to mutate, and tests can override individual values by monkeypatching.
"""

from __future__ import annotations

import os
from pathlib import Path

_APP_NAME = "anitrack"


def _platform_base(env_var: str, *fallback: Path) -> Path:
    """Resolve a platform base directory from an env var, with a fallback."""
    value = os.environ.get(env_var)
    if value:
        return Path(value)
    for option in fallback:
        return option
    return Path.home()


def _local_app_data_dir() -> Path:
    """Stable, writable per-user data directory (used for logs, library)."""
    if os.name == "nt":
        return (
            _platform_base("LOCALAPPDATA", Path.home() / "AppData" / "Local")
            / _APP_NAME
        )
    return _platform_base("XDG_DATA_HOME", Path.home() / ".local" / "share") / _APP_NAME


def _cache_base_dir() -> Path:
    """Writable per-user cache directory."""
    if os.name == "nt":
        return (
            _platform_base("LOCALAPPDATA", Path.home() / "AppData" / "Local")
            / _APP_NAME
            / "cache"
        )
    return _platform_base("XDG_CACHE_HOME", Path.home() / ".cache") / _APP_NAME


class AppConfig:
    # ---- Metadata --------------------------------------------------------------

    @classmethod
    def load(cls) -> None:
        """Compatibility hook invoked at startup. Reserved for future use."""

    @classmethod
    def app_name(cls) -> str:
        return "Anitrack"

    @classmethod
    def app_version(cls) -> str:
        return "0.1.0"

    # ---- Typography ------------------------------------------------------------

    @classmethod
    def font_family(cls) -> str:
        return "Segoe UI"

    @classmethod
    def font_size(cls) -> int:
        return 10

    # ---- API -------------------------------------------------------------------

    @classmethod
    def search_results_limit(cls) -> int:
        return 24

    @classmethod
    def suggestions_limit(cls) -> int:
        return 14

    @classmethod
    def characters_limit(cls) -> int:
        return 20

    @classmethod
    def api_base_url(cls) -> str:
        return "https://api.jikan.moe/v4"

    @classmethod
    def api_timeout(cls) -> float:
        return 15.0

    @classmethod
    def api_max_retries(cls) -> int:
        return 3

    @classmethod
    def api_min_interval(cls) -> float:
        return 0.4

    # ---- Paths -----------------------------------------------------------------

    @classmethod
    def data_dir(cls) -> Path:
        path = _local_app_data_dir()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def cache_dir(cls) -> Path:
        path = _cache_base_dir()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def api_cache_dir(cls) -> Path:
        path = cls.cache_dir() / "api_responses"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def logs_dir(cls) -> Path:
        path = cls.data_dir() / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path
