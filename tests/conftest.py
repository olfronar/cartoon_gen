from __future__ import annotations

from datetime import date, datetime, timezone

from shared.models import ComedyBrief, RawItem, ScoredItem


def make_raw_item(
    title: str = "Test Item",
    url: str = "https://example.com/test",
    sources: list[str] | None = None,
    tier: str = "discovery",
    score: int = 100,
    timestamp: datetime | None = None,
    snippet: str = "test snippet",
    comment_count: int = 0,
) -> RawItem:
    return RawItem(
        title=title,
        url=url,
        sources=sources or ["test_source"],
        tier=tier,
        score=score,
        timestamp=timestamp or datetime(2026, 3, 14, 12, 0, tzinfo=timezone.utc),
        snippet=snippet,
        comment_count=comment_count,
    )


def make_scored_item(
    raw_item: RawItem | None = None,
    comedy_potential: float = 5.0,
    cultural_resonance: float = 5.0,
    freshness: float = 5.0,
    comedy_angle: str = "test angle",
) -> ScoredItem:
    item = raw_item or make_raw_item()
    multi_bonus = 1.0 if len(item.sources) > 1 else 0.0
    return ScoredItem(
        item=item,
        comedy_potential=comedy_potential,
        cultural_resonance=cultural_resonance,
        freshness=freshness,
        multi_source_bonus=multi_bonus,
        total_score=comedy_potential + cultural_resonance + freshness + multi_bonus,
        comedy_angle=comedy_angle,
    )


def make_brief(
    top_picks: list[ScoredItem] | None = None,
    also_notable: list[ScoredItem] | None = None,
) -> ComedyBrief:
    return ComedyBrief(
        date=date(2026, 3, 14),
        top_picks=top_picks or [],
        also_notable=also_notable or [],
    )
