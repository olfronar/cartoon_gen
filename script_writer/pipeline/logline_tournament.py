from __future__ import annotations

import logging

from shared.models import Logline, ScoredItem
from shared.utils import call_llm_json

from ..prompts import LOGLINE_PAIRWISE_PROMPT

logger = logging.getLogger(__name__)


def compare_pair(
    a: Logline,
    b: Logline,
    item: ScoredItem,
    context_block: str,
    client,
    model: str = "claude-opus-4-6",
    max_tokens: int = 64000,
) -> tuple[Logline, str]:
    """Compare two loglines head-to-head. Returns (winner, feedback_for_loser)."""
    prompt = LOGLINE_PAIRWISE_PROMPT.format(
        context=context_block,
        title=item.item.title,
        comedy_angle=item.comedy_angle or "(discover the comedy angle from scratch)",
        logline_a=_format_logline(a, "A"),
        logline_b=_format_logline(b, "B"),
    )
    data = call_llm_json(client, prompt, model, max_tokens)
    winner_key = data.get("winner", "a").lower()
    feedback = data.get("loser_feedback", "")
    winner = a if winner_key == "a" else b
    return winner, feedback


def run_tournament(
    loglines: list[Logline],
    item: ScoredItem,
    context_block: str,
    client,
    model: str = "claude-opus-4-6",
    max_tokens: int = 64000,
) -> Logline:
    """Run a single-elimination tournament. Returns the winning logline."""
    if not loglines:
        raise ValueError("No loglines to tournament")
    if len(loglines) == 1:
        return loglines[0]

    # Single elimination: pair up, winners advance, odd one gets bye
    current = list(loglines)
    while len(current) > 1:
        next_round: list[Logline] = []
        i = 0
        while i + 1 < len(current):
            try:
                winner, _ = compare_pair(
                    current[i], current[i + 1], item, context_block, client, model, max_tokens
                )
                next_round.append(winner)
            except Exception:
                logger.exception("Pairwise comparison failed — advancing first candidate")
                next_round.append(current[i])
            i += 2
        if i < len(current):  # odd one out gets bye
            next_round.append(current[i])
        current = next_round

    return current[0]


def _format_logline(logline: Logline, label: str) -> str:
    """Format a logline for display in the pairwise prompt."""
    return (
        f"Logline {label}:\n"
        f"  Approach: {logline.approach}\n"
        f"  Format: {logline.format_type}\n"
        f"  Text: {logline.text}\n"
        f"  Visual hook: {logline.visual_hook}\n"
        f"  News essence: {logline.news_essence}\n"
        f"  Characters: {', '.join(logline.featured_characters)}"
    )
