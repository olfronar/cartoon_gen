from __future__ import annotations

import json
import logging

import anthropic

from script_writer.prompts import HUMOR_PREAMBLE, LOGLINE_GENERATION_PROMPT
from shared.models import Logline, ScoredItem
from shared.utils import strip_code_fences

logger = logging.getLogger(__name__)


def generate_loglines(
    item: ScoredItem,
    context_block: str,
    api_key: str,
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

    client = anthropic.Anthropic(api_key=api_key)

    try:
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            temperature=1,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            response = stream.get_final_message()
    except Exception:
        logger.exception("Logline generation failed for: %s", item.item.title)
        return []

    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text

    text = strip_code_fences(text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse logline JSON:\n%s", text[:500])
        return []

    loglines = []
    for entry in data:
        loglines.append(
            Logline(
                text=entry["text"],
                approach=entry["approach"],
                featured_characters=entry.get("featured_characters", []),
                visual_hook=entry.get("visual_hook", ""),
            )
        )

    logger.info("Generated %d loglines for: %s", len(loglines), item.item.title)
    return loglines
