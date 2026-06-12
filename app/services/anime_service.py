"""High-level anime data fetchers used by the detail-page background worker."""

from __future__ import annotations

from typing import Any

from loguru import logger

from ..models.anime import validate_mal_id
from .api_client import client


def fetch_detail(mal_id: int) -> tuple[dict[str, Any], list, list, list]:
    """Fetch everything needed to render the anime-detail page.

    Each sub-request is independent: a failure in one (network blip, 404 on
    relations, etc.) does not abort the others. Returns empty containers for
    the parts that failed so the UI can degrade gracefully.
    """
    validate_mal_id(mal_id)
    requests: list[tuple[str, Any, str]] = [
        ("full", lambda: client().get_anime_full(mal_id), ""),
        (
            "characters",
            lambda: client().get_anime_characters(mal_id),
            "characters",
        ),
        (
            "relations",
            lambda: client().get_anime_relations(mal_id),
            "relations",
        ),
        (
            "recommendations",
            lambda: client().get_recommendations(mal_id),
            "recommendations",
        ),
    ]
    results: dict[str, Any] = {
        "full": {},
        "characters": [],
        "relations": [],
        "recommendations": [],
    }
    for label, op, _ in requests:
        try:
            data = op()
            results[label] = data.get("data") if label == "full" else data
            logger.info("Fetched {} for mal_id={}", label, mal_id)
        except Exception as exc:
            logger.error("Failed to fetch {} [{}]: {}", label, mal_id, exc)
    return (
        results["full"],
        results["characters"],
        results["relations"],
        results["recommendations"],
    )
