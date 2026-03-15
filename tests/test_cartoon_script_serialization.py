from __future__ import annotations

import json
from datetime import date

from shared.models import CartoonScript, SceneScript, Synopsis
from tests.conftest import make_scored_item


def _make_script(**overrides) -> CartoonScript:
    defaults = dict(
        title="Test Episode",
        date=date(2026, 3, 14),
        source_item=make_scored_item(),
        logline="A robot learns to cook",
        synopsis=Synopsis(
            setup="s",
            escalation="e",
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
            SceneScript(
                scene_number=2,
                scene_title="Climax",
                setting="Dining room",
                scene_prompt="Guests arrive to chaos.",
                dialogue=[],
                visual_gag=None,
                audio_direction="dramatic sting",
                duration_seconds=8,
                camera_movement="wide shot",
            ),
        ],
        end_card_prompt="Show logo with confetti",
        characters_used=["Bot", "Chef"],
    )
    defaults.update(overrides)
    return CartoonScript(**defaults)


class TestCartoonScriptFromDict:
    def test_roundtrip(self):
        """CartoonScript survives to_dict -> from_dict."""
        original = _make_script()
        data = original.to_dict()
        restored = CartoonScript.from_dict(data)

        assert restored.title == original.title
        assert restored.date == original.date
        assert restored.logline == original.logline
        assert len(restored.scenes) == 2
        assert restored.scenes[0].scene_title == "Opening"
        assert restored.scenes[1].scene_title == "Climax"
        assert restored.end_card_prompt == original.end_card_prompt
        assert restored.characters_used == original.characters_used

    def test_json_roundtrip(self):
        """CartoonScript survives JSON serialization."""
        original = _make_script()
        json_str = json.dumps(original.to_dict())
        data = json.loads(json_str)
        restored = CartoonScript.from_dict(data)

        assert restored.title == original.title
        assert restored.date == original.date
        assert restored.source_item.comedy_angle == original.source_item.comedy_angle
        assert restored.source_item.item.title == original.source_item.item.title

    def test_synopsis_preserved(self):
        """Synopsis fields survive roundtrip."""
        original = _make_script()
        restored = CartoonScript.from_dict(original.to_dict())

        assert restored.synopsis.setup == "s"
        assert restored.synopsis.escalation == "e"
        assert restored.synopsis.punchline == "p"
        assert restored.synopsis.estimated_scenes == 2
        assert restored.synopsis.key_visual_gags == ["gag"]

    def test_scene_details_preserved(self):
        """Scene-level details survive roundtrip."""
        original = _make_script()
        restored = CartoonScript.from_dict(original.to_dict())

        scene = restored.scenes[0]
        assert scene.scene_number == 1
        assert scene.dialogue == [{"character": "Bot", "line": "Hello!"}]
        assert scene.visual_gag == "robot drops pan"
        assert scene.duration_seconds == 5

    def test_empty_scenes(self):
        """Script with no scenes roundtrips."""
        original = _make_script(scenes=[])
        restored = CartoonScript.from_dict(original.to_dict())
        assert restored.scenes == []
