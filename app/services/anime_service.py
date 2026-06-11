from __future__ import annotations

from typing import Any

from loguru import logger

from .api_client import client


def _validate_mal_id(mal_id: int) -> None:
    if not isinstance(mal_id, int) or mal_id <= 0:
        raise ValueError(f"mal_id must be a positive integer, got {mal_id!r}")


def fetch_detail(mal_id: int) -> tuple[dict[str, Any], list, list, list]:
    _validate_mal_id(mal_id)
    full_data: dict[str, Any] = {}
    chars: list = []
    rels: list = []
    recs: list = []

    try:
        result = client().get_anime_full(mal_id)
        full_data = result.get("data", {})
        logger.info("Fetched full data for mal_id={}", mal_id)
    except Exception as exc:
        logger.error("Failed to fetch anime full [{}]: {}", mal_id, exc)

    try:
        chars = client().get_anime_characters(mal_id)
        logger.info("Fetched {} characters for mal_id={}", len(chars), mal_id)
    except Exception as exc:
        logger.error("Failed to fetch characters [{}]: {}", mal_id, exc)

    try:
        rels = client().get_anime_relations(mal_id)
        logger.info("Fetched {} relations for mal_id={}", len(rels), mal_id)
    except Exception as exc:
        logger.error("Failed to fetch relations [{}]: {}", mal_id, exc)

    try:
        recs = client().get_recommendations(mal_id)
        logger.info("Fetched {} recommendations for mal_id={}", len(recs), mal_id)
    except Exception as exc:
        logger.error("Failed to fetch recommendations [{}]: {}", mal_id, exc)

    return full_data, chars, rels, recs
