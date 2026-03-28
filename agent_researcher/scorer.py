from __future__ import annotations

import json
import logging
import time
from dataclasses import replace

import anthropic

from shared.config import Settings
from shared.models import RawItem, ScoredItem
from shared.utils import extract_text, strip_code_fences

logger = logging.getLogger(__name__)

SCORING_MODEL = "claude-opus-4-6"
MAX_ITEMS_TO_SCORE = 100
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 5  # seconds

SCORING_PROMPT = """\
You are a comedy writer's assistant for a cartoon series that explains tech \
and science news to a BROAD audience — not insiders. The viewer is a curious \
adult who reads the news but doesn't know what a "benchmark" or "fine-tuning" \
means.

Below is a list of today's trending events in AI, robotics, biotech, \
technology, medicine, and engineering.

For each item, score it from 0–10 on THREE criteria:
1. Comedy potential — does it create simultaneous contradictory emotions (humor \
AND anxiety, admiration AND absurdity)? Look for structural contradictions: \
stated reason vs actual constraint, public position vs private reality. Irony, \
hubris, absurdity, or a clear "villain" count too, but the best items make you \
laugh AND wince.
2. Broad resonance — would a non-technical adult immediately grasp why this \
matters or why it's absurd? Stories requiring insider knowledge (benchmark \
drama, model architecture debates, open-source governance) score LOW. Stories \
where the comedy lands for anyone who reads a newspaper score HIGH. Test: \
would your non-tech friend find this interesting at dinner?
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
- "comedy_angle": string — REQUIRED. Three-part format: "[STRUCTURAL \
CONTRADICTION: what's said vs what's actually happening — the gap that makes it \
funny]. [DOUBLE HIT: the two contradictory emotions this creates — e.g., \
admiration AND absurdity, hope AND dread]. [One-liner joke seed that names the \
contradiction.]" Example: "A company spending $10B on AI safety ships a chatbot \
that recommends bleach recipes — stated goal (protect humanity) vs actual \
capability (can't protect a lunch order). Admiration for the ambition AND dread \
at the incompetence. 'They're building God. God currently can't count to ten.'"
- "duplicate_of": int or null — if this item covers the same event as another, \
the index of the better version; null otherwise

DUPLICATE DETECTION: Some items describe the same underlying news event from \
different sources or angles. For each item, if it covers the SAME core event \
as another item in the list, set "duplicate_of" to the index of the BEST \
version (strongest comedy angle). The best version itself gets "duplicate_of": \
null. Items about the same broad TOPIC but different specific events are NOT \
duplicates.

Be brutal with scores — most items will score low. That's the point.

Items:
"""


def _call_scorer_with_retry(client, items_json: str) -> list[dict] | None:
    """Call Claude scorer with retries. Returns parsed JSON array or None on failure."""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with client.messages.stream(
                model=SCORING_MODEL,
                max_tokens=32768,
                thinking={"type": "adaptive"},
                temperature=1,  # required when thinking is enabled
                messages=[{"role": "user", "content": SCORING_PROMPT + items_json}],
            ) as stream:
                response = stream.get_final_message()
        except Exception as exc:
            last_error = exc
            logger.warning("Scorer API call failed (attempt %d/%d): %s", attempt, MAX_RETRIES, exc)
            if attempt < MAX_RETRIES:
                backoff = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                logger.info("Retrying in %ds...", backoff)
                time.sleep(backoff)
            continue

        text = strip_code_fences(extract_text(response))

        try:
            scored_data = json.loads(text)
            if isinstance(scored_data, list):
                return scored_data
            logger.warning("Scorer returned non-array JSON (attempt %d/%d)", attempt, MAX_RETRIES)
        except json.JSONDecodeError as exc:
            last_error = exc
            logger.warning(
                "Failed to parse scorer JSON (attempt %d/%d):\n%s",
                attempt,
                MAX_RETRIES,
                text[:500],
            )

        if attempt < MAX_RETRIES:
            backoff = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
            logger.info("Retrying in %ds...", backoff)
            time.sleep(backoff)

    logger.error("Scorer failed after %d attempts. Last error: %s", MAX_RETRIES, last_error)
    return None


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
        print("⚠ WARNING: No ANTHROPIC_API_KEY — using fallback scoring (no comedy angles)")
        return _fallback_scoring(items)

    # Cap items to avoid huge prompts
    to_score = items[:MAX_ITEMS_TO_SCORE]
    items_json = _prepare_items_json(to_score)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    scored_data = _call_scorer_with_retry(client, items_json)
    if scored_data is None:
        print(
            "⚠ WARNING: LLM scoring failed after retries"
            " — using fallback scoring (no comedy angles)"
        )
        return _fallback_scoring(items)

    # Map scored data back to items
    scored_map: dict[int, dict] = {}
    for entry in scored_data:
        idx = entry.get("index")
        if idx is not None:
            scored_map[idx] = entry

    # Resolve semantic duplicates flagged by Claude
    duplicate_targets: set[int] = set()
    for idx, data in scored_map.items():
        dup_of = data.get("duplicate_of")
        if (
            dup_of is not None
            and isinstance(dup_of, int)
            and dup_of != idx
            and 0 <= dup_of < len(to_score)
            and 0 <= idx < len(to_score)
            and dup_of in scored_map
            and dup_of not in duplicate_targets
        ):
            duplicate_targets.add(idx)
            canon = to_score[dup_of]
            merged = list(set(canon.sources + to_score[idx].sources))
            to_score[dup_of] = replace(canon, sources=merged)
            logger.info(
                "Semantic dedup: %r merged into %r",
                to_score[idx].title,
                to_score[dup_of].title,
            )

    result: list[ScoredItem] = []
    for i, item in enumerate(to_score):
        if i in duplicate_targets:
            continue
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
