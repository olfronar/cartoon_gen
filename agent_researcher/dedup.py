from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

from rapidfuzz import fuzz

from shared.models import RawItem

logger = logging.getLogger(__name__)

TITLE_SIMILARITY_THRESHOLD = 85

FRESHNESS_CUTOFFS = {
    "discovery": timedelta(hours=24),
    "validation": timedelta(hours=24),
    "context": timedelta(hours=48),
}


def _normalize_url(url: str) -> str:
    """Strip tracking params and trailing slashes for dedup comparison."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    # Remove common tracking params
    cleaned = {k: v for k, v in params.items() if not k.startswith("utm_")}
    normalized = parsed._replace(
        query=urlencode(cleaned, doseq=True),
        fragment="",
    )
    result = urlunparse(normalized).rstrip("/")
    return result


def _merge_items(keep: RawItem, discard: RawItem) -> RawItem:
    """Merge discard into keep: combine sources, take higher score."""
    merged_sources = list(set(keep.sources + discard.sources))
    return RawItem(
        title=keep.title,
        url=keep.url,
        sources=merged_sources,
        tier=keep.tier if keep.score >= discard.score else discard.tier,
        score=max(keep.score, discard.score),
        timestamp=min(keep.timestamp, discard.timestamp),
        snippet=keep.snippet if keep.snippet else discard.snippet,
        comment_count=max(keep.comment_count, discard.comment_count),
    )


def dedup_and_filter(
    items: list[RawItem], now: datetime | None = None
) -> list[RawItem]:
    if not items:
        return []

    now = now or datetime.now(timezone.utc)

    # 1. Freshness filter
    fresh: list[RawItem] = []
    for item in items:
        cutoff = FRESHNESS_CUTOFFS.get(item.tier, timedelta(hours=24))
        age = now - item.timestamp.replace(tzinfo=timezone.utc) if item.timestamp.tzinfo is None else now - item.timestamp
        if age <= cutoff:
            fresh.append(item)

    logger.info("Freshness filter: %d -> %d items", len(items), len(fresh))

    # 2. Sort by score descending (best version wins in dedup)
    fresh.sort(key=lambda x: x.score, reverse=True)

    # 3. URL dedup with source merging
    url_map: dict[str, RawItem] = {}
    for item in fresh:
        key = _normalize_url(item.url)
        if key in url_map:
            url_map[key] = _merge_items(url_map[key], item)
        else:
            url_map[key] = item

    url_deduped = list(url_map.values())
    logger.info("URL dedup: %d -> %d items", len(fresh), len(url_deduped))

    # 4. Near-title dedup with source merging
    result: list[RawItem] = []
    used = [False] * len(url_deduped)

    for i, item_a in enumerate(url_deduped):
        if used[i]:
            continue
        merged = item_a
        for j in range(i + 1, len(url_deduped)):
            if used[j]:
                continue
            ratio = fuzz.token_sort_ratio(merged.title, url_deduped[j].title)
            if ratio >= TITLE_SIMILARITY_THRESHOLD:
                merged = _merge_items(merged, url_deduped[j])
                used[j] = True
        result.append(merged)

    logger.info("Title dedup: %d -> %d items", len(url_deduped), len(result))
    return result
