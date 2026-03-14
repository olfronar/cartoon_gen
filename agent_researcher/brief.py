from __future__ import annotations

from datetime import date

from shared.models import ComedyBrief, ScoredItem

TOP_PICKS_COUNT = 5
ALSO_NOTABLE_COUNT = 10


def generate_brief(scored_items: list[ScoredItem]) -> ComedyBrief:
    return ComedyBrief(
        date=date.today(),
        top_picks=scored_items[:TOP_PICKS_COUNT],
        also_notable=scored_items[TOP_PICKS_COUNT : TOP_PICKS_COUNT + ALSO_NOTABLE_COUNT],
    )
