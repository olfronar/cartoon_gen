from __future__ import annotations

import json
import logging
import time

import anthropic

from shared.config import Settings
from shared.models import RawItem
from shared.utils import extract_json, extract_text

logger = logging.getLogger(__name__)

PREFILTER_MODEL = "claude-sonnet-4-6"
MAX_PREFILTER_ITEMS = 200
PREFILTER_TOP_N = 50
MAX_RETRIES = 2
RETRY_BACKOFF_BASE = 3  # seconds

PREFILTER_PROMPT = """\
You are pre-screening news items for a comedy cartoon show that explains \
tech and science news to a broad audience.

Quickly rate each item's potential as cartoon material on a 0-10 scale \
considering:
- Comedy potential: irony, absurdity, hubris, structural contradictions
- Broad appeal: would a non-technical adult find this funny or interesting?
- Visual comedy: can you SEE the joke in a single image + 15-second video?

Be brutal — most items should score low. Only genuinely funny/absurd ones \
deserve high scores.

Return a JSON array with one object per item:
[{"index": 0, "score": 7.5}, {"index": 1, "score": 3.0}, ...]

Every item must appear exactly once. No other keys needed.

Output ONLY the JSON array, no commentary or explanation.

Items:
"""


def _call_prefilter(client, items_json: str) -> list[dict]:
    """Call Sonnet for fast pre-filtering. Returns parsed list or raises."""
    response = client.messages.create(
        model=PREFILTER_MODEL,
        max_tokens=4096,
        temperature=0,
        messages=[{"role": "user", "content": PREFILTER_PROMPT + items_json}],
    )
    text = extract_text(response)
    return extract_json(text, expect=list)


def _call_prefilter_with_retry(client, items_json: str) -> list[dict] | None:
    """Call prefilter with retries. Returns parsed scores or None."""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return _call_prefilter(client, items_json)
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Prefilter failed (attempt %d/%d): %s",
                attempt,
                MAX_RETRIES,
                exc,
            )
            if attempt < MAX_RETRIES:
                backoff = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                logger.info("Retrying in %ds...", backoff)
                time.sleep(backoff)

    logger.error("Prefilter failed after %d attempts: %s", MAX_RETRIES, last_error)
    return None


def prefilter_items(
    items: list[RawItem],
    settings: Settings,
    client: anthropic.Anthropic | None = None,
) -> list[RawItem]:
    """Fast pre-filter using Sonnet. Returns top N items ranked by comedy potential.

    Falls back to raw-score sorting if LLM unavailable.
    """
    if not settings.anthropic_api_key:
        logger.warning("No ANTHROPIC_API_KEY — skipping prefilter")
        return _fallback_prefilter(items)

    to_filter = items[:MAX_PREFILTER_ITEMS]

    serializable = [
        {
            "index": i,
            "title": item.title,
            "url": item.url,
            "sources": item.sources,
            "score": item.score,
            "snippet": item.snippet,
        }
        for i, item in enumerate(to_filter)
    ]

    if client is None:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    scores = _call_prefilter_with_retry(client, json.dumps(serializable))

    if not scores:
        logger.warning("Prefilter failed — falling back to raw score sorting")
        return _fallback_prefilter(to_filter)

    # Map index -> score
    score_map: dict[int, float] = {}
    for entry in scores:
        idx = entry.get("index")
        sc = entry.get("score", 0)
        if idx is not None and isinstance(idx, int) and 0 <= idx < len(to_filter):
            score_map[idx] = float(sc)

    # Rank by prefilter score, take top N
    ranked = sorted(score_map.items(), key=lambda x: x[1], reverse=True)
    top_indices = [idx for idx, _ in ranked[:PREFILTER_TOP_N]]

    result = [to_filter[i] for i in top_indices]
    logger.info(
        "Prefilter: %d items -> top %d (scores %.1f-%.1f)",
        len(to_filter),
        len(result),
        ranked[0][1] if ranked else 0,
        ranked[min(len(ranked) - 1, PREFILTER_TOP_N - 1)][1] if ranked else 0,
    )
    return result


def _fallback_prefilter(items: list[RawItem]) -> list[RawItem]:
    """Sort by raw score and return top N when LLM is unavailable."""
    sorted_items = sorted(items, key=lambda x: x.score, reverse=True)
    return sorted_items[:PREFILTER_TOP_N]
