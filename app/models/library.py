from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from loguru import logger

from .anime import Anime, AnimeStatus


def _data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / "anitrack"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _library_path() -> Path:
    return _data_dir() / "library.json"


def library_path() -> Path:
    return _library_path()


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _parse_iso_timestamp(iso: str) -> float:
    if not iso:
        return 0.0
    try:
        return datetime.fromisoformat(iso).timestamp()
    except (ValueError, TypeError):
        return 0.0


class Library:
    def __init__(self) -> None:
        self._items: dict[int, Anime] = {}
        self._load()

    def _load(self) -> None:
        path = _library_path()
        if not path.exists():
            logger.debug("Library file not found at {}, starting empty", path)
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Failed to load library from {}: {}", path, e)
            return
        items = raw.get("items", [])
        if not isinstance(items, list):
            logger.warning("Library file has invalid 'items' field, expected list")
            return
        for entry in items:
            try:
                anime = Anime.from_dict(entry)
            except (KeyError, TypeError, ValueError) as e:
                logger.debug("Skipping invalid library entry: {}", e)
                continue
            self._items[anime.mal_id] = anime
        logger.info("Loaded {} entries from {}", len(self._items), path)

    def save(self) -> None:
        path = _library_path()
        payload = {"version": 1, "items": [a.to_dict() for a in self._items.values()]}
        fd, tmp = tempfile.mkstemp(
            prefix="library_", suffix=".json", dir=str(path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except Exception:
            logger.error("Failed to save library to {}", path)
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        logger.debug("Saved library ({} items) to {}", len(self._items), path)

    def all(self) -> list[Anime]:
        return self._sort(list(self._items.values()))

    def get(self, mal_id: int) -> Anime | None:
        if not isinstance(mal_id, int) or isinstance(mal_id, bool):
            raise TypeError(f"mal_id must be an int, got {type(mal_id).__name__}")
        return self._items.get(mal_id)

    def in_status(self, status: AnimeStatus) -> list[Anime]:
        if not isinstance(status, AnimeStatus):
            raise TypeError(
                f"status must be an AnimeStatus, got {type(status).__name__}"
            )
        items = [a for a in self._items.values() if a.tracking_status == status.value]
        return self._sort(items)

    def favorites(self) -> list[Anime]:
        return self._sort([a for a in self._items.values() if a.favorite])

    def count(self) -> int:
        return len(self._items)

    def path(self) -> Path:
        return _library_path()

    def load_from(self, path: str | Path) -> int:
        path = Path(path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = raw.get("items", [])
        if not isinstance(items, list):
            raise ValueError("Invalid library file: 'items' must be a list")
        loaded: dict[int, Anime] = {}
        for entry in items:
            anime = Anime.from_dict(entry)
            loaded[anime.mal_id] = anime
        self._items = loaded
        self.save()
        logger.info("Loaded {} entries from {}", len(loaded), path)
        return len(loaded)

    @staticmethod
    def _sort(items: list[Anime]) -> list[Anime]:
        return sorted(
            items, key=lambda a: (not a.favorite, -_parse_iso_timestamp(a.added_at))
        )

    def add(
        self, anime: Anime, status: AnimeStatus, *, favorite: bool = False
    ) -> Anime:
        if not isinstance(anime, Anime):
            raise TypeError(
                f"anime must be an Anime instance, got {type(anime).__name__}"
            )
        if not isinstance(status, AnimeStatus):
            raise TypeError(
                f"status must be an AnimeStatus, got {type(status).__name__}"
            )
        existing = self._items.get(anime.mal_id)
        if existing is None:
            anime.added_at = _now_iso()
            anime.tracking_status = status.value
            anime.favorite = favorite
            anime.updated_at = anime.added_at
            self._items[anime.mal_id] = anime
            logger.info(
                "Added '{}' (mal_id={}) as {}", anime.title, anime.mal_id, status.value
            )
        else:
            existing.tracking_status = status.value
            existing.favorite = existing.favorite or favorite
            existing.updated_at = _now_iso()
            anime = existing
            logger.info(
                "Updated '{}' (mal_id={}) to {}",
                anime.title,
                anime.mal_id,
                status.value,
            )
        self.save()
        return anime

    def remove(self, mal_id: int) -> bool:
        if not isinstance(mal_id, int) or isinstance(mal_id, bool):
            raise TypeError(f"mal_id must be an int, got {type(mal_id).__name__}")
        if mal_id in self._items:
            title = self._items[mal_id].title
            del self._items[mal_id]
            self.save()
            logger.info("Removed '{}' (mal_id={})", title, mal_id)
            return True
        logger.debug("remove() called for mal_id={} not in library", mal_id)
        return False

    def set_status(self, mal_id: int, status: AnimeStatus) -> None:
        if not isinstance(mal_id, int) or isinstance(mal_id, bool):
            raise TypeError(f"mal_id must be an int, got {type(mal_id).__name__}")
        if not isinstance(status, AnimeStatus):
            raise TypeError(
                f"status must be an AnimeStatus, got {type(status).__name__}"
            )
        anime = self._items.get(mal_id)
        if anime is None:
            logger.debug("set_status() called for mal_id={} not in library", mal_id)
            return
        anime.tracking_status = status.value
        anime.updated_at = _now_iso()
        self.save()
        logger.info(
            "Set '{}' (mal_id={}) status to {}", anime.title, mal_id, status.value
        )

    def toggle_favorite(self, mal_id: int) -> bool:
        if not isinstance(mal_id, int) or isinstance(mal_id, bool):
            raise TypeError(f"mal_id must be an int, got {type(mal_id).__name__}")
        anime = self._items.get(mal_id)
        if anime is None:
            logger.debug(
                "toggle_favorite() called for mal_id={} not in library", mal_id
            )
            return False
        anime.favorite = not anime.favorite
        anime.updated_at = _now_iso()
        self.save()
        logger.info(
            "Toggled favorite for '{}' (mal_id={}) to {}",
            anime.title,
            mal_id,
            anime.favorite,
        )
        return anime.favorite

    def set_favorite(self, mal_id: int, value: bool) -> None:
        if not isinstance(mal_id, int) or isinstance(mal_id, bool):
            raise TypeError(f"mal_id must be an int, got {type(mal_id).__name__}")
        if not isinstance(value, bool):
            raise TypeError(f"value must be a bool, got {type(value).__name__}")
        anime = self._items.get(mal_id)
        if anime is None:
            logger.debug("set_favorite() called for mal_id={} not in library", mal_id)
            return
        anime.favorite = value
        anime.updated_at = _now_iso()
        self.save()
        logger.info(
            "Set favorite for '{}' (mal_id={}) to {}", anime.title, mal_id, value
        )

    def update(self, anime: Anime) -> None:
        if not isinstance(anime, Anime):
            raise TypeError(
                f"anime must be an Anime instance, got {type(anime).__name__}"
            )
        if anime.mal_id not in self._items:
            logger.debug("update() called for mal_id={} not in library", anime.mal_id)
            return
        anime.updated_at = _now_iso()
        self._items[anime.mal_id] = anime
        self.save()
        logger.info("Updated '{}' (mal_id={})", anime.title, anime.mal_id)


_library: Library | None = None


def get_library() -> Library:
    global _library
    if _library is None:
        _library = Library()
    return _library
