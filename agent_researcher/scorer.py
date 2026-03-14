from __future__ import annotations

import json
import logging

import anthropic

from shared.config import Settings
from shared.models import RawItem, ScoredItem

logger = logging.getLogger(__name__)

SCORING_MODEL = "claude-opus-4-6"
MAX_ITEMS_TO_SCORE = 100

SCORING_PROMPT = """\
You are a comedy writer's assistant for a tech-themed cartoon series.

Below is a list of today's trending events in AI, robotics, biotech, and technology.

For each item, score it from 0–10 on THREE criteria:
1. Comedy potential — does it have irony, hubris, absurdity, or a clear "villain"?
2. Cultural resonance — will a tech-aware audience instantly recognize the reference?
3. Freshness — is this breaking today, or already a stale meme?

Bonus: if an item appears across multiple sources, add +1 to its total.

Then suggest a one-line comedy angle (the "joke seed") for the top candidates.

Return as JSON array. Each element must have these exact keys:
- "index": the item's index from the input list (0-based)
- "comedy_potential": float 0-10
- "cultural_resonance": float 0-10
- "freshness": float 0-10
- "comedy_angle": string (one-liner joke seed, or empty string if score is low)

Be brutal — most items will score low. That's the point.

Items:
"""


def _prepare_items_json(items: list[RawItem]) -> str:
    serializable = []
    for i, item in enumerate(items):
        serializable.append(
            {
                "index": i,
                "title": item.title,
                "url": item.url,
                "sources": item.sources,
                "score": item.score,
                "snippet": item.snippet,
            }
        )
    return json.dumps(serializable, indent=2)


def score_items(items: list[RawItem], settings: Settings) -> list[ScoredItem]:
    if not settings.anthropic_api_key:
        logger.warning("No ANTHROPIC_API_KEY — returning items with default scores")
        return _fallback_scoring(items)

    # Cap items to avoid huge prompts
    to_score = items[:MAX_ITEMS_TO_SCORE]
    items_json = _prepare_items_json(to_score)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    try:
        response = client.messages.create(
            model=SCORING_MODEL,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": SCORING_PROMPT + items_json}
            ],
        )
    except Exception:
        logger.exception("Claude API call failed")
        return _fallback_scoring(items)

    # Extract text content
    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text

    # Parse JSON from response (handle markdown code blocks)
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
        text = text.strip()

    try:
        scored_data = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse scorer JSON response:\n%s", text[:500])
        return _fallback_scoring(items)

    # Map scored data back to items
    scored_map: dict[int, dict] = {}
    for entry in scored_data:
        idx = entry.get("index")
        if idx is not None:
            scored_map[idx] = entry

    result: list[ScoredItem] = []
    for i, item in enumerate(to_score):
        data = scored_map.get(i, {})
        comedy = float(data.get("comedy_potential", 0))
        resonance = float(data.get("cultural_resonance", 0))
        fresh = float(data.get("freshness", 0))
        multi_bonus = 1.0 if len(item.sources) > 1 else 0.0
        total = comedy + resonance + fresh + multi_bonus

        result.append(
            ScoredItem(
                item=item,
                comedy_potential=comedy,
                cultural_resonance=resonance,
                freshness=fresh,
                multi_source_bonus=multi_bonus,
                total_score=total,
                comedy_angle=data.get("comedy_angle", ""),
            )
        )

    result.sort(key=lambda x: x.total_score, reverse=True)
    logger.info("Scored %d items via Claude", len(result))
    return result


def _fallback_scoring(items: list[RawItem]) -> list[ScoredItem]:
    """Score by raw score only when LLM is unavailable."""
    result = []
    for item in items:
        multi_bonus = 1.0 if len(item.sources) > 1 else 0.0
        result.append(
            ScoredItem(
                item=item,
                comedy_potential=0,
                cultural_resonance=0,
                freshness=0,
                multi_source_bonus=multi_bonus,
                total_score=float(item.score) + multi_bonus,
                comedy_angle="",
            )
        )
    result.sort(key=lambda x: x.total_score, reverse=True)
    return result
