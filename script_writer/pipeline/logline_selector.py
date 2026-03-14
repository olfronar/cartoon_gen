from __future__ import annotations

import json
import logging

import anthropic

from script_writer.prompts import HUMOR_PREAMBLE, LOGLINE_SELECTION_PROMPT
from shared.models import Logline
from shared.utils import strip_code_fences

logger = logging.getLogger(__name__)


def select_logline(
    loglines: list[Logline],
    title: str,
    comedy_angle: str,
    context_block: str,
    api_key: str,
    model: str = "claude-opus-4-6",
    max_tokens: int = 64000,
) -> Logline:
    """Select the best logline from 3 candidates."""
    if len(loglines) == 1:
        return loglines[0]

    loglines_formatted = ""
    for i, ll in enumerate(loglines):
        loglines_formatted += (
            f"\n**Option {i + 1}** ({ll.approach}):\n"
            f"  Logline: {ll.text}\n"
            f"  Characters: {', '.join(ll.featured_characters)}\n"
            f"  Visual hook: {ll.visual_hook}\n"
        )

    prompt = LOGLINE_SELECTION_PROMPT.format(
        preamble=HUMOR_PREAMBLE,
        context=context_block,
        title=title,
        comedy_angle=comedy_angle,
        loglines_formatted=loglines_formatted,
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
        logger.exception("Logline selection failed, defaulting to first")
        return loglines[0]

    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text

    text = strip_code_fences(text)

    try:
        data = json.loads(text)
        idx = int(data["selected_index"])
        logger.info("Selected logline %d: %s", idx, data.get("reasoning", ""))
        return loglines[idx]
    except (json.JSONDecodeError, KeyError, IndexError):
        logger.error("Failed to parse selection, defaulting to first:\n%s", text[:500])
        return loglines[0]
