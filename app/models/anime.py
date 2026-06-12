"""Anime data model and validation helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from loguru import logger
from qfluentwidgets import FluentIcon as FIF


class AnimeStatus(str, Enum):
    WATCHING = "watching"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    DROPPED = "dropped"
    PLAN = "plan_to_watch"

    @property
    def label(self) -> str:
        return _STATUS_LABELS[self]


_STATUS_LABELS: dict[AnimeStatus, str] = {
    AnimeStatus.WATCHING: "Watching",
    AnimeStatus.COMPLETED: "Completed",
    AnimeStatus.ON_HOLD: "On Hold",
    AnimeStatus.DROPPED: "Dropped",
    AnimeStatus.PLAN: "Plan to Watch",
}

STATUS_FLUENT_ICONS: dict[str, FIF] = {
    AnimeStatus.WATCHING.value: FIF.VIEW,
    AnimeStatus.COMPLETED.value: FIF.COMPLETED,
    AnimeStatus.ON_HOLD.value: FIF.PAUSE,
    AnimeStatus.DROPPED.value: FIF.DELETE,
    AnimeStatus.PLAN.value: FIF.CALENDAR,
}


# ---------------------------------------------------------------------------
# Validators / coercers
# ---------------------------------------------------------------------------


def validate_mal_id(mal_id: Any) -> int:
    """Validate that a value is an int-coercible positive integer.

    `bool` is rejected explicitly because in Python ``bool`` is a subclass of
    ``int`` (i.e. ``True == 1``), which is almost never what callers want.
    """
    if isinstance(mal_id, bool) or not isinstance(mal_id, int):
        raise TypeError(f"mal_id must be an int, got {type(mal_id).__name__}")
    if mal_id <= 0:
        raise ValueError(f"mal_id must be positive, got {mal_id}")
    return mal_id


def _validate_title(title: Any) -> str:
    if not isinstance(title, str):
        raise TypeError(f"title must be a str, got {type(title).__name__}")
    if not title.strip():
        raise ValueError("title must not be empty")
    return title


def _coerce_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        result = int(value)
    except (ValueError, TypeError):
        return None
    return result if result >= 0 else None


def _coerce_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    return result if result >= 0 else None


def _coerce_str(value: Any) -> str:
    return "" if value is None else str(value)


def _coerce_str_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(v) for v in value if v is not None and str(v).strip()]


# ---------------------------------------------------------------------------
# Jikan payload helpers
# ---------------------------------------------------------------------------


def jpg_url_from_jikan(data: dict[str, Any]) -> str:
    """Pick the best available JPG URL from a Jikan image container."""
    images = data.get("images") if isinstance(data, dict) else None
    jpg = (images or {}).get("jpg") if isinstance(images, dict) else {}
    if not isinstance(jpg, dict):
        return ""
    return jpg.get("large_image_url") or jpg.get("image_url") or ""


def _year_from_jikan(data: dict[str, Any]) -> int | None:
    aired = data.get("aired") if isinstance(data, dict) else None
    if not isinstance(aired, dict):
        return None
    aired_from = aired.get("from") or ""
    if (
        not isinstance(aired_from, str)
        or len(aired_from) < 4
        or not aired_from[:4].isdigit()
    ):
        return None
    return int(aired_from[:4])


def _title_from_jikan(data: dict[str, Any]) -> str:
    title = data.get("title_english") or data.get("title") or ""
    if title:
        return title
    for entry in data.get("titles") or []:
        if isinstance(entry, dict) and entry.get("title"):
            title = entry["title"]
            break
    return title


def _genres_from_jikan(data: dict[str, Any]) -> list[str]:
    return [
        g.get("name")
        for g in (data.get("genres") or [])
        if isinstance(g, dict) and g.get("name")
    ]


# ---------------------------------------------------------------------------
# Anime dataclass
# ---------------------------------------------------------------------------


@dataclass
class Anime:
    mal_id: int
    title: str
    image_url: str = ""
    url: str = ""
    episodes: int | None = None
    anime_type: str = ""
    status: str = ""
    score: float | None = None
    synopsis: str = ""
    genres: list[str] = field(default_factory=list)
    year: int | None = None
    tracking_status: str = AnimeStatus.PLAN.value
    favorite: bool = False
    progress: int = 0
    user_score: float | None = None
    notes: str = ""
    added_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        self.mal_id = validate_mal_id(self.mal_id)
        self.title = _validate_title(self.title)

    @classmethod
    def from_jikan(cls, data: dict[str, Any]) -> Anime:
        if not isinstance(data, dict):
            raise TypeError(f"from_jikan expects a dict, got {type(data).__name__}")
        mal_id = data.get("mal_id")
        if mal_id is None:
            raise ValueError("Jikan data missing required field 'mal_id'")
        title = _title_from_jikan(data)
        if not title:
            logger.warning("Jikan entry mal_id={} has no usable title", mal_id)
            title = "Unknown"
        return cls(
            mal_id=validate_mal_id(mal_id),
            title=title,
            image_url=jpg_url_from_jikan(data),
            url=_coerce_str(data.get("url")),
            episodes=_coerce_optional_int(data.get("episodes")),
            anime_type=_coerce_str(data.get("type")),
            status=_coerce_str(data.get("status")),
            score=_coerce_optional_float(data.get("score")),
            synopsis=_coerce_str(data.get("synopsis")),
            genres=_genres_from_jikan(data),
            year=_year_from_jikan(data),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Anime:
        if not isinstance(data, dict):
            raise TypeError(f"from_dict expects a dict, got {type(data).__name__}")
        for field_name in ("mal_id", "title"):
            if field_name not in data:
                raise KeyError(f"Missing required field '{field_name}'")
        return cls(
            mal_id=validate_mal_id(data["mal_id"]),
            title=_validate_title(data["title"]),
            image_url=_coerce_str(data.get("image_url")),
            url=_coerce_str(data.get("url")),
            episodes=_coerce_optional_int(data.get("episodes")),
            anime_type=_coerce_str(data.get("anime_type")),
            status=_coerce_str(data.get("status")),
            score=_coerce_optional_float(data.get("score")),
            synopsis=_coerce_str(data.get("synopsis")),
            genres=_coerce_str_list(data.get("genres")),
            year=_coerce_optional_int(data.get("year")),
            tracking_status=_coerce_str(data.get("tracking_status"))
            or AnimeStatus.PLAN.value,
            favorite=bool(data.get("favorite", False)),
            progress=_coerce_optional_int(data.get("progress")) or 0,
            user_score=_coerce_optional_float(data.get("user_score")),
            notes=_coerce_str(data.get("notes")),
            added_at=_coerce_str(data.get("added_at")),
            updated_at=_coerce_str(data.get("updated_at")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
