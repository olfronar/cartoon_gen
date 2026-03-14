from __future__ import annotations

import json
from datetime import date

from script_writer.pipeline.renderer import render_script_markdown, write_script
from shared.models import CartoonScript, SceneScript, Synopsis
from tests.conftest import make_scored_item


def _make_script() -> CartoonScript:
    return CartoonScript(
        title="Robot Chef Disaster",
        date=date(2026, 3, 14),
        source_item=make_scored_item(),
        logline="A robot tries to cook dinner",
        synopsis=Synopsis(
            setup="Robot opens kitchen",
            escalation="Everything catches fire",
            punchline="Robot orders pizza",
            estimated_scenes=2,
            key_visual_gags=["fire", "pizza"],
        ),
        scenes=[
            SceneScript(
                scene_number=1,
                scene_title="The Kitchen",
                setting="Modern kitchen, morning",
                scene_prompt="A chrome robot stands in a bright modern kitchen holding a spatula. "
                "Slow zoom in. Cartoon style with bold outlines. Upbeat jazz music. "
                "Duration: 5 seconds.",
                dialogue=[
                    {"character": "RoboChef", "line": "Time to cook!"},
                    {"character": "Cat", "line": "Meow."},
                ],
                visual_gag="Robot flips pancake into ceiling",
                audio_direction="Jazz, sizzle sfx",
                duration_seconds=5,
                camera_movement="slow zoom in",
            ),
            SceneScript(
                scene_number=2,
                scene_title="The Fire",
                setting="Same kitchen, now on fire",
                scene_prompt="Kitchen engulfed in colorful cartoon flames. Robot looking confused. "
                "Wide shot. Bold colors. Fire crackling. Duration: 4 seconds.",
                dialogue=[],
                visual_gag=None,
                audio_direction="Fire crackling, alarm",
                duration_seconds=4,
                camera_movement="static wide shot",
            ),
        ],
        end_card_prompt="Show logo with robot chef hat on top",
        characters_used=["RoboChef", "Cat"],
    )


class TestRenderMarkdown:
    def test_contains_title(self):
        md = render_script_markdown(_make_script())
        assert "# Script: Robot Chef Disaster" in md

    def test_contains_metadata(self):
        md = render_script_markdown(_make_script())
        assert "**Date**: 2026-03-14" in md
        assert "**Logline**:" in md

    def test_contains_scenes(self):
        md = render_script_markdown(_make_script())
        assert "### Scene 1: The Kitchen" in md
        assert "### Scene 2: The Fire" in md

    def test_contains_dialogue(self):
        md = render_script_markdown(_make_script())
        assert "**RoboChef**: Time to cook!" in md

    def test_contains_end_card(self):
        md = render_script_markdown(_make_script())
        assert "## End card" in md
        assert "robot chef hat" in md

    def test_contains_visual_gag(self):
        md = render_script_markdown(_make_script())
        assert "pancake into ceiling" in md


class TestWriteScript:
    def test_writes_both_files(self, tmp_path):
        script = _make_script()
        md_path, json_path = write_script(script, 1, tmp_path)

        assert md_path.exists()
        assert json_path.exists()
        assert md_path.name == "2026-03-14_1.md"
        assert json_path.name == "2026-03-14_1.json"

    def test_json_is_valid(self, tmp_path):
        script = _make_script()
        _, json_path = write_script(script, 1, tmp_path)

        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["title"] == "Robot Chef Disaster"
        assert len(data["scenes"]) == 2

    def test_creates_output_dir(self, tmp_path):
        script = _make_script()
        out = tmp_path / "new_dir"
        write_script(script, 1, out)
        assert out.exists()
