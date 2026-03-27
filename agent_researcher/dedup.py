from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

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


def dedup_and_filter(items: list[RawItem], now: datetime | None = None) -> list[RawItem]:
    if not items:
        return []

    now = now or datetime.now(timezone.utc)

    # 1. Freshness filter
    fresh: list[RawItem] = []
    for item in items:
        cutoff = FRESHNESS_CUTOFFS.get(item.tier, timedelta(hours=24))
        ts = item.timestamp
        if not ts.tzinfo:
            ts = ts.replace(tzinfo=timezone.utc)
        age = now - ts
        if age <= cutoff:
            fresh.append(item)

    logger.info("Freshness filter: %d -> %d items", len(items), len(fresh))

    # 2. Sort by score descending (best version wins in dedup)
    fresh.sort(key=lambda x: x.score, reverse=True)

    # 3. URL dedup with source merging (skip empty URLs — they'd all collide)
    url_map: dict[str, RawItem] = {}
    no_url: list[RawItem] = []
    for item in fresh:
        key = _normalize_url(item.url)
        if not key:
            no_url.append(item)
            continue
        if key in url_map:
            url_map[key] = _merge_items(url_map[key], item)
        else:
            url_map[key] = item

    url_deduped = list(url_map.values()) + no_url
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


def filter_already_covered(
    items: list[RawItem],
    briefs_dir: Path,
    lookback_days: int = 7,
    today: date | None = None,
) -> list[RawItem]:
    """Remove items that already appeared in previous briefs (cross-day dedup)."""
    today = today or date.today()
    cutoff = today - timedelta(days=lookback_days)

    # Collect URLs and titles from previous briefs
    prev_urls: set[str] = set()
    prev_titles: list[str] = []

    for json_path in sorted(briefs_dir.glob("*.json")):
        try:
            brief_date = date.fromisoformat(json_path.stem)
        except ValueError:
            continue
        if brief_date >= today or brief_date < cutoff:
            continue

        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Failed to read brief: %s", json_path)
            continue

        # Support both new ("items") and old ("top_picks"/"also_notable") formats
        entries = data.get("items", [])
        if not entries:
            entries = data.get("top_picks", []) + data.get("also_notable", [])
        for entry in entries:
            raw = entry.get("item", {})
            url = raw.get("url", "")
            normalized = _normalize_url(url)
            if normalized:
                prev_urls.add(normalized)
            title = raw.get("title", "")
            if title:
                prev_titles.append(title)

    if not prev_urls and not prev_titles:
        return items

    kept: list[RawItem] = []
    for item in items:
        normalized_url = _normalize_url(item.url)
        if normalized_url and normalized_url in prev_urls:
            logger.info("Cross-day dedup (URL): dropping %r", item.title)
            continue

        title_match = any(
            fuzz.token_sort_ratio(item.title, prev) >= TITLE_SIMILARITY_THRESHOLD
            for prev in prev_titles
        )
        if title_match:
            logger.info("Cross-day dedup (title): dropping %r", item.title)
            continue

        kept.append(item)

    logger.info("Cross-day history filter: %d -> %d items", len(items), len(kept))
    return kept
