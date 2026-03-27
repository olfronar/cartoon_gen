from __future__ import annotations

from datetime import date

from shared.models import ComedyBrief, ScoredItem

BRIEF_SIZE = 20


def generate_brief(scored_items: list[ScoredItem]) -> ComedyBrief:
    return ComedyBrief(
        date=date.today(),
        items=scored_items[:BRIEF_SIZE],
    )
