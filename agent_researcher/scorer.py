from __future__ import annotations

import json
import logging
import time
from dataclasses import replace

import anthropic

from shared.config import Settings
from shared.models import RawItem, ScoredItem
from shared.utils import extract_json, extract_text, strip_code_fences

logger = logging.getLogger(__name__)

SCORING_MODEL = "claude-opus-4-6"
MAX_ITEMS_TO_SCORE = 50
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 5  # seconds

SCORE_WEIGHTS = {
    "comedy_potential": 2.0,
    "cultural_resonance": 1.0,
    "freshness": 1.0,
    "visual_comedy_potential": 1.5,
    "emotional_range": 1.0,
}

SCORING_PROMPT = """\
You are a comedy writer's assistant for a cartoon series that explains tech \
and science news to a BROAD audience — not insiders. The viewer is a curious \
adult who reads the news but doesn't know what a "benchmark" or "fine-tuning" \
means.

Below is a list of today's trending events in AI, robotics, biotech, \
technology, medicine, and engineering.

For each item, score it from 0–10 on FIVE criteria:
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
4. Visual comedy potential — how well does this translate to a single static \
image + a 15-second animated video? Can you SEE the joke? Score higher if the \
absurdity is inherently visual: physical scale mismatch, an unexpected object \
in the wrong context, a recognizable icon doing something wrong, a material \
or texture that shouldn't exist. Score lower if the humor is purely \
verbal/conceptual, requires reading text to understand, or depends on \
abstract knowledge the viewer can't see. The gold standard: a phone-scrolling \
stranger pauses because the image alone is arresting.
5. Emotional range — does this story give the lead character a clear, specific \
emotion beyond "measured observation"? Stories that provoke outrage, wonder, \
betrayal, glee, panic, dark delight, or genuine bafflement score HIGH. \
Generic "tech company does thing" stories where the only possible reaction is \
mild interest score LOW. The more visceral and specific the emotional \
reaction, the higher the score.

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
- "visual_comedy_potential": float 0-10
- "emotional_range": float 0-10
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


_REFUSAL = "refusal"
_MAX_TOKENS = "max_tokens"
_MIN_SPLIT_SIZE = 3  # don't split batches smaller than this


def _call_scorer_once(client, items_json: str):
    """Single scorer API call. Returns (parsed_list, stop_reason) or raises."""
    with client.messages.stream(
        model=SCORING_MODEL,
        max_tokens=32768,
        thinking={"type": "adaptive"},
        temperature=1,  # required when thinking is enabled
        messages=[{"role": "user", "content": SCORING_PROMPT + items_json}],
    ) as stream:
        response = stream.get_final_message()

    if response.stop_reason == _REFUSAL:
        return None, _REFUSAL

    text = strip_code_fences(extract_text(response))

    if not text.strip():
        block_types = [
            f"{b.type}({len(getattr(b, 'thinking', '') or getattr(b, 'text', ''))}ch)"
            for b in response.content
        ]
        raise ValueError(
            f"empty response text. Content blocks: {block_types}, "
            f"stop_reason: {response.stop_reason}"
        )

    if response.stop_reason == _MAX_TOKENS:
        logger.warning("Response hit max_tokens — batch too large for single call")
        return None, _MAX_TOKENS

    scored_data = extract_json(text, expect=list)
    return scored_data, response.stop_reason


def _call_scorer_with_retry(client, items_json: str) -> list[dict] | None:
    """Call Claude scorer with retries. Returns parsed JSON array or None on failure."""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            scored_data, stop_reason = _call_scorer_once(client, items_json)
        except Exception as exc:
            last_error = exc
            logger.warning("Scorer failed (attempt %d/%d): %s", attempt, MAX_RETRIES, exc)
            if attempt < MAX_RETRIES:
                backoff = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                logger.info("Retrying in %ds...", backoff)
                time.sleep(backoff)
            continue

        if stop_reason == _REFUSAL:
            logger.warning("Scorer refused the batch (attempt %d/%d)", attempt, MAX_RETRIES)
            return None  # caller handles refusal via batch splitting

        if stop_reason == _MAX_TOKENS:
            return None  # retrying won't help — trigger batch split

        if scored_data is not None:
            return scored_data

    logger.error("Scorer failed after %d attempts. Last error: %s", MAX_RETRIES, last_error)
    return None


def _score_batch_with_split(client, items: list[dict], *, depth: int = 0) -> list[dict]:
    """Score a batch, splitting on refusal to isolate problematic items.

    Returns scored entries (possibly partial if some sub-batches were refused).
    """
    items_json = json.dumps(items)
    scored = _call_scorer_with_retry(client, items_json)
    if scored is not None:
        return scored

    # Refusal or total failure — try splitting
    if len(items) < _MIN_SPLIT_SIZE:
        titles = [it.get("title", "?")[:60] for it in items]
        logger.warning(
            "Dropping %d items after refusal (too small to split): %s", len(items), titles
        )
        return []

    mid = len(items) // 2
    left, right = items[:mid], items[mid:]
    logger.info(
        "Splitting refused batch (%d items) into halves (%d + %d), depth=%d",
        len(items),
        len(left),
        len(right),
        depth,
    )
    scored_left = _score_batch_with_split(client, left, depth=depth + 1)
    scored_right = _score_batch_with_split(client, right, depth=depth + 1)
    return scored_left + scored_right


def _prepare_items_list(items: list[RawItem]) -> list[dict]:
    """Build serializable item dicts with original indices for scorer prompt."""
    return [
        {
            "index": i,
            "title": item.title,
            "url": item.url,
            "sources": item.sources,
            "score": item.score,
            "snippet": item.snippet,
        }
        for i, item in enumerate(items)
    ]


def score_items(items: list[RawItem], settings: Settings) -> list[ScoredItem]:
    if not settings.anthropic_api_key:
        logger.warning("No ANTHROPIC_API_KEY — returning items with default scores")
        print("⚠ WARNING: No ANTHROPIC_API_KEY — using fallback scoring (no comedy angles)")
        return _fallback_scoring(items)

    # Cap items to avoid huge prompts
    to_score = items[:MAX_ITEMS_TO_SCORE]
    serializable = _prepare_items_list(to_score)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    scored_data = _score_batch_with_split(client, serializable)
    if not scored_data:
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
        visual = float(data.get("visual_comedy_potential", 0))
        emotion = float(data.get("emotional_range", 0))
        multi_bonus = 1.0 if len(item.sources) > 1 else 0.0
        total = (
            comedy * SCORE_WEIGHTS["comedy_potential"]
            + resonance * SCORE_WEIGHTS["cultural_resonance"]
            + fresh * SCORE_WEIGHTS["freshness"]
            + visual * SCORE_WEIGHTS["visual_comedy_potential"]
            + emotion * SCORE_WEIGHTS["emotional_range"]
            + multi_bonus
        )

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
                visual_comedy_potential=visual,
                emotional_range=emotion,
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
                visual_comedy_potential=0,
                emotional_range=0,
            )
        )
    result.sort(key=lambda x: x.total_score, reverse=True)
    return result
