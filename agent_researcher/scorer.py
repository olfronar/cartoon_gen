from __future__ import annotations

import json
import logging
from dataclasses import replace

import anthropic

from shared.config import Settings
from shared.models import RawItem, ScoredItem
from shared.utils import strip_code_fences

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

For EVERY item (not just top ones), provide:
- A clear, informative title that explains WHAT happened (not vague — a reader \
should understand the event from the title alone)
- A comedy explanation: identify the specific irony, absurdity, or hubris, then \
pitch a one-line joke angle. This is required for all items.

Return as JSON array. Each element must have these exact keys:
- "index": the item's index from the input list (0-based)
- "title": string — rewritten informative title (what happened, who, why it matters)
- "comedy_potential": float 0-10
- "cultural_resonance": float 0-10
- "freshness": float 0-10
- "comedy_angle": string — REQUIRED. Format: "[Why it's funny in 1 sentence]. \
[One-liner joke seed.]" Example: "CEO claims AI will replace all jobs while his \
own AI can't schedule a meeting. 'Our product will automate everything except \
working correctly.'"

Be brutal with scores — most items will score low. That's the point.

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
    return json.dumps(serializable)


def score_items(items: list[RawItem], settings: Settings) -> list[ScoredItem]:
    if not settings.anthropic_api_key:
        logger.warning("No ANTHROPIC_API_KEY — returning items with default scores")
        return _fallback_scoring(items)

    # Cap items to avoid huge prompts
    to_score = items[:MAX_ITEMS_TO_SCORE]
    items_json = _prepare_items_json(to_score)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    try:
        with client.messages.stream(
            model=SCORING_MODEL,
            max_tokens=32768,
            thinking={"type": "adaptive"},
            temperature=1,  # required when thinking is enabled
            messages=[{"role": "user", "content": SCORING_PROMPT + items_json}],
        ) as stream:
            response = stream.get_final_message()
    except Exception:
        logger.exception("Claude API call failed")
        return _fallback_scoring(items)

    # Extract text content
    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text

    # Parse JSON from response (handle markdown code blocks)
    text = strip_code_fences(text)

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

        # Use LLM-rewritten title if provided
        rewritten_title = data.get("title", "")
        if rewritten_title:
            item = replace(item, title=rewritten_title)

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
