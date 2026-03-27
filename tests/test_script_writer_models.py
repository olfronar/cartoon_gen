from __future__ import annotations

import json
from datetime import date

from shared.models import (
    CartoonScript,
    Logline,
    SceneScript,
    Synopsis,
)
from tests.conftest import make_brief, make_scored_item


class TestComedyBriefSerialization:
    def test_roundtrip(self):
        """ComedyBrief serializes to dict and back."""
        brief = make_brief(
            items=[make_scored_item(), make_scored_item(), make_scored_item()],
        )
        data = brief.to_dict()
        restored = type(brief).from_dict(data)

        assert restored.date == brief.date
        assert len(restored.items) == 3
        assert restored.items[0].comedy_angle == brief.items[0].comedy_angle
        assert restored.items[0].item.title == brief.items[0].item.title

    def test_json_roundtrip(self):
        """ComedyBrief survives JSON serialization."""
        brief = make_brief(items=[make_scored_item()])
        json_str = json.dumps(brief.to_dict())
        data = json.loads(json_str)
        restored = type(brief).from_dict(data)

        assert restored.date == brief.date
        assert restored.items[0].total_score == brief.items[0].total_score

    def test_backward_compat_from_dict(self):
        """ComedyBrief.from_dict handles old top_picks + also_notable format."""
        brief = make_brief(items=[make_scored_item(), make_scored_item()])
        data = brief.to_dict()
        # Simulate old format
        old_data = {
            "date": data["date"],
            "top_picks": data["items"][:1],
            "also_notable": data["items"][1:],
        }
        restored = type(brief).from_dict(old_data)
        assert len(restored.items) == 2


class TestLogline:
    def test_creation(self):
        ll = Logline(
            text="A robot learns to cook",
            approach="the_quiet_part",
            featured_characters=["Chef Bot"],
            visual_hook="robot on fire",
        )
        assert ll.approach == "the_quiet_part"
        assert len(ll.featured_characters) == 1


class TestSynopsis:
    def test_creation(self):
        syn = Synopsis(
            setup="Robot opens restaurant",
            development="Health inspector arrives, is also a robot",
            punchline="They merge into one super-robot",
            estimated_scenes=6,
            key_visual_gags=["robot melting cheese with laser eyes"],
        )
        assert syn.estimated_scenes == 6
        assert len(syn.key_visual_gags) == 1


class TestCartoonScript:
    def test_to_dict(self):
        script = CartoonScript(
            title="Test Episode",
            date=date(2026, 3, 14),
            source_item=make_scored_item(),
            logline="A robot learns to cook",
            synopsis=Synopsis(
                setup="s",
                development="e",
                punchline="p",
                estimated_scenes=2,
                key_visual_gags=["gag"],
            ),
            scenes=[
                SceneScript(
                    scene_number=1,
                    scene_title="Opening",
                    setting="Kitchen",
                    scene_prompt="A robot chef stands in a modern kitchen.",
                    dialogue=[{"character": "Bot", "line": "Hello!"}],
                    visual_gag="robot drops pan",
                    audio_direction="upbeat music",
                    duration_seconds=5,
                    camera_movement="slow zoom in",
                ),
            ],
            end_card_prompt="Show logo",
            characters_used=["Bot"],
        )
        data = script.to_dict()
        assert data["date"] == "2026-03-14"
        assert data["title"] == "Test Episode"
        assert len(data["scenes"]) == 1
        assert data["scenes"][0]["scene_title"] == "Opening"

    def test_to_dict_is_json_serializable(self):
        script = CartoonScript(
            title="Test",
            date=date(2026, 3, 14),
            source_item=make_scored_item(),
            logline="test",
            synopsis=Synopsis(
                setup="s",
                development="e",
                punchline="p",
                estimated_scenes=2,
                key_visual_gags=[],
            ),
            scenes=[],
            end_card_prompt="logo",
            characters_used=[],
        )
        json_str = json.dumps(script.to_dict())
        assert isinstance(json_str, str)
