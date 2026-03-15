from __future__ import annotations

import json
from datetime import date

import pytest

from shared.models import CartoonScript, SceneScript, Synopsis
from static_shots_maker.pipeline.script_reader import read_scripts
from tests.conftest import make_scored_item


def _write_script_json(tmp_path, date_str: str, index: int, title: str = "Test") -> None:
    script = CartoonScript(
        title=title,
        date=date.fromisoformat(date_str),
        source_item=make_scored_item(),
        logline="test logline",
        synopsis=Synopsis(
            setup="s",
            escalation="e",
            punchline="p",
            estimated_scenes=1,
            key_visual_gags=[],
        ),
        scenes=[
            SceneScript(
                scene_number=1,
                scene_title="S1",
                setting="Lab",
                scene_prompt="A robot in a lab.",
                dialogue=[],
                visual_gag=None,
                audio_direction="silence",
                duration_seconds=5,
                camera_movement="static",
            ),
        ],
        end_card_prompt="logo",
        characters_used=["Bot"],
    )
    path = tmp_path / f"{date_str}_{index}.json"
    path.write_text(json.dumps(script.to_dict()), encoding="utf-8")


class TestScriptReader:
    def test_read_by_date(self, tmp_path):
        _write_script_json(tmp_path, "2026-03-15", 1, title="Episode 1")
        _write_script_json(tmp_path, "2026-03-15", 2, title="Episode 2")

        results = read_scripts(target_date=date(2026, 3, 15), scripts_dir=tmp_path)
        assert len(results) == 2
        assert results[0][0] == 1
        assert results[1][0] == 2
        assert results[0][1].title == "Episode 1"

    def test_auto_detect_latest(self, tmp_path):
        _write_script_json(tmp_path, "2026-03-13", 1)
        _write_script_json(tmp_path, "2026-03-15", 1)
        _write_script_json(tmp_path, "2026-03-14", 1)

        results = read_scripts(scripts_dir=tmp_path)
        assert results[0][1].date == date(2026, 3, 15)

    def test_missing_directory(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_scripts(scripts_dir=tmp_path / "nonexistent")

    def test_no_scripts(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_scripts(scripts_dir=tmp_path)

    def test_corrupt_json_skipped(self, tmp_path):
        _write_script_json(tmp_path, "2026-03-15", 1, title="Good")
        (tmp_path / "2026-03-15_2.json").write_text("{bad json", encoding="utf-8")

        results = read_scripts(target_date=date(2026, 3, 15), scripts_dir=tmp_path)
        assert len(results) == 1
        assert results[0][1].title == "Good"
