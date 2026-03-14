from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(slots=True)
class RawItem:
    title: str
    url: str
    sources: list[str]
    tier: str  # "discovery" | "validation" | "context"
    score: int  # upvotes / points / 0 for RSS
    timestamp: datetime  # UTC
    snippet: str
    comment_count: int = 0


@dataclass(slots=True)
class ScoredItem:
    item: RawItem
    comedy_potential: float  # 0-10
    cultural_resonance: float  # 0-10
    freshness: float  # 0-10
    multi_source_bonus: float  # 0 or 1
    total_score: float
    comedy_angle: str


@dataclass(slots=True)
class ComedyBrief:
    date: date
    top_picks: list[ScoredItem] = field(default_factory=list)
    also_notable: list[ScoredItem] = field(default_factory=list)
