from __future__ import annotations

import logging

from shared.models import Logline, ScoredItem
from shared.utils import call_llm_json

from ..prompts import HUMOR_PREAMBLE, LOGLINE_PAIRWISE_PROMPT, LOGLINE_REVISION_PROMPT

logger = logging.getLogger(__name__)

_MAX_REVISIONS = 2


def compare_pair(
    a: Logline,
    b: Logline,
    item: ScoredItem,
    context_block: str,
    client,
    model: str = "claude-opus-4-6",
    max_tokens: int = 64000,
) -> tuple[Logline, Logline, str]:
    """Compare two loglines head-to-head. Returns (winner, loser, feedback_for_loser)."""
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
    if winner_key == "a":
        return a, b, feedback
    return b, a, feedback


def revise_logline(
    loser: Logline,
    winner: Logline,
    feedback: str,
    item: ScoredItem,
    context_block: str,
    client,
    model: str = "claude-opus-4-6",
    max_tokens: int = 64000,
) -> Logline:
    """Revise a losing logline using feedback from its comparison. Returns revised Logline."""
    prompt = LOGLINE_REVISION_PROMPT.format(
        preamble=HUMOR_PREAMBLE,
        context=context_block,
        title=item.item.title,
        comedy_angle=item.comedy_angle or "(discover the comedy angle from scratch)",
        loser_logline=_format_logline(loser, "Loser"),
        feedback=feedback,
        winner_logline=_format_logline(winner, "Winner"),
        approach=loser.approach,
        format_type=loser.format_type,
    )
    data = call_llm_json(client, prompt, model, max_tokens)
    return Logline(
        text=data.get("text", loser.text),
        approach=data.get("approach", loser.approach),
        featured_characters=data.get("featured_characters", loser.featured_characters),
        visual_hook=data.get("visual_hook", loser.visual_hook),
        news_essence=data.get("news_essence", loser.news_essence),
        format_type=data.get("format_type", loser.format_type),
    )


def run_tournament(
    loglines: list[Logline],
    item: ScoredItem,
    context_block: str,
    client,
    model: str = "claude-opus-4-6",
    max_tokens: int = 64000,
) -> Logline:
    """Run a single-elimination tournament with feedback-driven revision.

    After the first elimination round, up to _MAX_REVISIONS losers are revised
    using feedback from their comparisons and re-entered for one more round.
    """
    if not loglines:
        raise ValueError("No loglines to tournament")
    if len(loglines) == 1:
        return loglines[0]

    # Round 1: single elimination with feedback collection
    current = list(loglines)
    next_round: list[Logline] = []
    revision_candidates: list[tuple[Logline, Logline, str]] = []  # (loser, winner, feedback)
    i = 0
    while i + 1 < len(current):
        try:
            winner, loser, feedback = compare_pair(
                current[i], current[i + 1], item, context_block, client, model, max_tokens
            )
            next_round.append(winner)
            if feedback:
                revision_candidates.append((loser, winner, feedback))
        except Exception:
            logger.exception("Pairwise comparison failed — advancing first candidate")
            next_round.append(current[i])
        i += 2
    if i < len(current):  # odd one out gets bye
        next_round.append(current[i])

    # Revise up to _MAX_REVISIONS losers and re-enter them
    revised_count = 0
    for loser, winner, feedback in revision_candidates[:_MAX_REVISIONS]:
        try:
            revised = revise_logline(
                loser, winner, feedback, item, context_block, client, model, max_tokens
            )
            next_round.append(revised)
            revised_count += 1
            logger.info("Revised logline '%s' using feedback", loser.approach)
        except Exception:
            logger.exception("Logline revision failed — dropping loser '%s'", loser.approach)

    if revised_count:
        logger.info("Re-entered %d revised loglines into tournament", revised_count)

    # Continue standard elimination for remaining rounds
    current = next_round
    while len(current) > 1:
        next_round = []
        i = 0
        while i + 1 < len(current):
            try:
                winner, _, _ = compare_pair(
                    current[i], current[i + 1], item, context_block, client, model, max_tokens
                )
                next_round.append(winner)
            except Exception:
                logger.exception("Pairwise comparison failed — advancing first candidate")
                next_round.append(current[i])
            i += 2
        if i < len(current):
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
