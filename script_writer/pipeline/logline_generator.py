from __future__ import annotations

import logging

from script_writer.prompts import (
    HUMOR_PREAMBLE,
    LOGLINE_GENERATION_PROMPT,
    LOGLINE_GENERATION_ROUND2_PROMPT,
)
from shared.models import Logline, ScoredItem
from shared.utils import call_llm_json

logger = logging.getLogger(__name__)


def generate_loglines(
    item: ScoredItem,
    context_block: str,
    client,
    model: str = "claude-opus-4-7",
    max_tokens: int = 64000,
) -> list[Logline]:
    """Generate 3 loglines (quiet part, betrayal, image) for a single news item."""
    comedy_angle = item.comedy_angle or (
        "[Not provided — you must discover the comedy angle yourself. "
        "Read the title and snippet, find the structural contradiction, "
        "the irony, or the absurdity. What is the uncomfortable truth "
        "nobody is saying? What makes this story funny to a non-expert?]"
    )
    prompt = LOGLINE_GENERATION_PROMPT.format(
        preamble=HUMOR_PREAMBLE,
        context=context_block,
        title=item.item.title,
        url=item.item.url,
        comedy_angle=comedy_angle,
        snippet=item.item.snippet,
    )

    try:
        data = call_llm_json(client, prompt, model, max_tokens)
    except Exception:
        logger.exception("Logline generation failed for: %s", item.item.title)
        return []

    entries = data["loglines"] if isinstance(data, dict) else data

    loglines = [
        Logline(
            text=entry["text"],
            approach=entry["approach"],
            featured_characters=entry.get("featured_characters", []),
            visual_hook=entry.get("visual_hook", ""),
            news_essence=entry.get("news_essence", ""),
            format_type=entry.get("format_type", ""),
        )
        for entry in entries
    ]

    logger.info("Generated %d loglines for: %s", len(loglines), item.item.title)
    return loglines


def generate_additional_loglines(
    item: ScoredItem,
    existing: list[Logline],
    context_block: str,
    client,
    model: str = "claude-opus-4-7",
    max_tokens: int = 64000,
) -> list[Logline]:
    """Generate 2 additional loglines that take different angles from existing ones."""
    existing_formatted = "\n\n".join(
        f"Logline {i + 1} ({lg.approach}, {lg.format_type}):\n"
        f"  {lg.text}\n  Visual: {lg.visual_hook}"
        for i, lg in enumerate(existing)
    )
    comedy_angle = item.comedy_angle or "(discover the comedy angle from scratch)"

    prompt = LOGLINE_GENERATION_ROUND2_PROMPT.format(
        preamble=HUMOR_PREAMBLE,
        context=context_block,
        title=item.item.title,
        url=item.item.url,
        comedy_angle=comedy_angle,
        snippet=item.item.snippet,
        existing_loglines=existing_formatted,
    )
    data = call_llm_json(client, prompt, model, max_tokens)

    loglines_data = data if isinstance(data, list) else data.get("loglines", [])
    return [
        Logline(
            text=entry.get("text", ""),
            approach=entry.get("approach", "fresh_angle"),
            featured_characters=entry.get("featured_characters", []),
            visual_hook=entry.get("visual_hook", ""),
            news_essence=entry.get("news_essence", ""),
            format_type=entry.get("format_type", ""),
        )
        for entry in loglines_data
        if entry.get("text")
    ]
