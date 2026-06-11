from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from loguru import logger


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


def _validate_mal_id(mal_id: Any) -> int:
    if not isinstance(mal_id, int) or isinstance(mal_id, bool):
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


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        result = int(value)
        return result if result >= 0 else None
    except (ValueError, TypeError):
        return None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
        return result if result >= 0 else None
    except (ValueError, TypeError):
        return None


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _safe_str_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(v) for v in value if v is not None and str(v).strip()]


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
        self.mal_id = _validate_mal_id(self.mal_id)
        self.title = _validate_title(self.title)

    @classmethod
    def from_jikan(cls, data: dict[str, Any]) -> Anime:
        if not isinstance(data, dict):
            raise TypeError(f"from_jikan expects a dict, got {type(data).__name__}")
        mal_id = data.get("mal_id")
        if mal_id is None:
            raise ValueError("Jikan data missing required field 'mal_id'")
        mal_id = _validate_mal_id(mal_id)

        images = data.get("images") or {}
        jpg = images.get("jpg") if isinstance(images, dict) else {}
        image_url = ""
        if isinstance(jpg, dict):
            image_url = jpg.get("large_image_url") or jpg.get("image_url") or ""

        raw_genres = data.get("genres") or []
        genres = [
            g["name"] for g in raw_genres if isinstance(g, dict) and g.get("name")
        ]

        year = None
        aired = data.get("aired") or {}
        if isinstance(aired, dict):
            aired_from = aired.get("from") or ""
            if (
                isinstance(aired_from, str)
                and len(aired_from) >= 4
                and aired_from[:4].isdigit()
            ):
                year = int(aired_from[:4])

        title = data.get("title_english") or data.get("title") or ""
        if not title:
            titles = data.get("titles") or []
            if isinstance(titles, list) and titles:
                first = titles[0]
                if isinstance(first, dict):
                    title = first.get("title") or ""
        if not title:
            logger.warning("Jikan entry mal_id={} has no usable title", mal_id)
            title = "Unknown"

        return cls(
            mal_id=mal_id,
            title=title,
            image_url=image_url,
            url=_safe_str(data.get("url")),
            episodes=_safe_int(data.get("episodes")),
            anime_type=_safe_str(data.get("type")),
            status=_safe_str(data.get("status")),
            score=_safe_float(data.get("score")),
            synopsis=_safe_str(data.get("synopsis")),
            genres=genres,
            year=year,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Anime:
        if not isinstance(data, dict):
            raise TypeError(f"from_dict expects a dict, got {type(data).__name__}")
        required = ("mal_id", "title")
        for field_name in required:
            if field_name not in data:
                raise KeyError(f"Missing required field '{field_name}'")
        mal_id = _validate_mal_id(data["mal_id"])
        title = _validate_title(data["title"])
        return cls(
            mal_id=mal_id,
            title=title,
            image_url=_safe_str(data.get("image_url")),
            url=_safe_str(data.get("url")),
            episodes=_safe_int(data.get("episodes")),
            anime_type=_safe_str(data.get("anime_type")),
            status=_safe_str(data.get("status")),
            score=_safe_float(data.get("score")),
            synopsis=_safe_str(data.get("synopsis")),
            genres=_safe_str_list(data.get("genres")),
            year=_safe_int(data.get("year")),
            tracking_status=_safe_str(data.get("tracking_status"))
            or AnimeStatus.PLAN.value,
            favorite=bool(data.get("favorite", False)),
            progress=_safe_int(data.get("progress")) or 0,
            user_score=_safe_float(data.get("user_score")),
            notes=_safe_str(data.get("notes")),
            added_at=_safe_str(data.get("added_at")),
            updated_at=_safe_str(data.get("updated_at")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
