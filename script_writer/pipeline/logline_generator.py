from __future__ import annotations

import logging

from script_writer.prompts import HUMOR_PREAMBLE, LOGLINE_GENERATION_PROMPT
from shared.models import Logline, ScoredItem
from shared.utils import call_llm_json

logger = logging.getLogger(__name__)


def generate_loglines(
    item: ScoredItem,
    context_block: str,
    client,
    model: str = "claude-opus-4-6",
    max_tokens: int = 64000,
) -> list[Logline]:
    """Generate 3 loglines (absurdist, satirical, surreal) for a single news item."""
    prompt = LOGLINE_GENERATION_PROMPT.format(
        preamble=HUMOR_PREAMBLE,
        context=context_block,
        title=item.item.title,
        url=item.item.url,
        comedy_angle=item.comedy_angle,
        snippet=item.item.snippet,
    )

    try:
        data = call_llm_json(client, prompt, model, max_tokens)
    except Exception:
        logger.exception("Logline generation failed for: %s", item.item.title)
        return []

    loglines = [
        Logline(
            text=entry["text"],
            approach=entry["approach"],
            featured_characters=entry.get("featured_characters", []),
            visual_hook=entry.get("visual_hook", ""),
            news_essence=entry.get("news_essence", ""),
        )
        for entry in data
    ]

    logger.info("Generated %d loglines for: %s", len(loglines), item.item.title)
    return loglines
