from __future__ import annotations

import json

from shared.models import CartoonScript
from tests.conftest import make_scene, make_script


class TestCartoonScriptFromDict:
    def test_roundtrip(self):
        """CartoonScript survives to_dict -> from_dict."""
        original = make_script(
            scenes=[
                make_scene(scene_number=1, scene_title="Opening"),
                make_scene(
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
            characters_used=["Bot", "Chef"],
        )
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
        original = make_script()
        json_str = json.dumps(original.to_dict())
        data = json.loads(json_str)
        restored = CartoonScript.from_dict(data)

        assert restored.title == original.title
        assert restored.date == original.date
        assert restored.source_item.comedy_angle == original.source_item.comedy_angle
        assert restored.source_item.item.title == original.source_item.item.title

    def test_synopsis_preserved(self):
        """Synopsis fields survive roundtrip."""
        original = make_script()
        restored = CartoonScript.from_dict(original.to_dict())

        assert restored.synopsis.setup == "s"
        assert restored.synopsis.development == "e"
        assert restored.synopsis.punchline == "p"
        assert restored.synopsis.estimated_scenes == 1
        assert restored.synopsis.key_visual_gags == ["gag"]

    def test_scene_details_preserved(self):
        """Scene-level details survive roundtrip."""
        original = make_script()
        restored = CartoonScript.from_dict(original.to_dict())

        scene = restored.scenes[0]
        assert scene.scene_number == 1
        assert scene.dialogue == [{"character": "Bot", "line": "Hello!"}]
        assert scene.visual_gag == "robot drops pan"
        assert scene.duration_seconds == 15

    def test_empty_scenes(self):
        """Script with no scenes roundtrips."""
        original = make_script(scenes=[])
        restored = CartoonScript.from_dict(original.to_dict())
        assert restored.scenes == []
