from __future__ import annotations

import logging

from script_writer.prompts import HUMOR_PREAMBLE, LOGLINE_SELECTION_PROMPT
from shared.models import Logline, ScoredItem
from shared.utils import call_llm_json

logger = logging.getLogger(__name__)


def select_logline(
    loglines: list[Logline],
    item: ScoredItem,
    context_block: str,
    client,
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
        title=item.item.title,
        comedy_angle=item.comedy_angle,
        loglines_formatted=loglines_formatted,
    )

    try:
        data = call_llm_json(client, prompt, model, max_tokens)
        idx = int(data["selected_index"])
        logger.info("Selected logline %d: %s", idx, data.get("reasoning", ""))
        return loglines[idx]
    except Exception:
        logger.exception("Logline selection failed, defaulting to first")
        return loglines[0]
