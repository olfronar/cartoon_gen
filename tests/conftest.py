from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from shared.models import CartoonScript, ComedyBrief, RawItem, SceneScript, ScoredItem, Synopsis


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
        timestamp=timestamp or datetime.now(timezone.utc),
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
    items: list[ScoredItem] | None = None,
) -> ComedyBrief:
    return ComedyBrief(
        date=date(2026, 3, 14),
        items=items or [],
    )


def make_scene(**overrides) -> SceneScript:
    defaults = dict(
        scene_number=1,
        scene_title="Opening",
        setting="Kitchen",
        scene_prompt="A robot chef stands in a modern kitchen.",
        dialogue=[{"character": "Bot", "line": "Hello!"}],
        visual_gag="robot drops pan",
        audio_direction="upbeat music",
        duration_seconds=15,
        camera_movement="slow zoom in",
        transformation="",
        billy_emotion="",
    )
    defaults.update(overrides)
    return SceneScript(**defaults)


def make_script(**overrides) -> CartoonScript:
    defaults = dict(
        title="Test Episode",
        date=date(2026, 3, 14),
        source_item=make_scored_item(),
        logline="A robot learns to cook",
        synopsis=Synopsis(
            setup="s",
            development="e",
            punchline="p",
            estimated_scenes=1,
            key_visual_gags=["gag"],
        ),
        scenes=[make_scene()],
        end_card_prompt="Show logo with confetti",
        characters_used=["Bot"],
        format_type="",
    )
    defaults.update(overrides)
    return CartoonScript(**defaults)


def write_script_json(directory: Path, date_str: str, index: int, title: str = "Test") -> None:
    script = make_script(title=title, date=date.fromisoformat(date_str))
    path = directory / f"{date_str}_{index}.json"
    path.write_text(json.dumps(script.to_dict()), encoding="utf-8")
