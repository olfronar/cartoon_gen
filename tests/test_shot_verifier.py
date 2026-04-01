from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from shared.models import SceneScript
from static_shots_maker.pipeline.shot_verifier import (
    compare_candidates,
    verify_shot,
)
from tests.conftest import make_scene, make_script


def _make_scene() -> SceneScript:
    return make_scene(
        scene_title="Test Scene",
        setting="A test setting",
        scene_prompt="Billy standing in a room with a giant rubber duck",
        dialogue=[{"character": "Billy", "line": "That's a big duck."}],
        visual_gag="The duck is wearing a tiny hat",
    )


class TestVerifyShot:
    @patch("static_shots_maker.pipeline.shot_verifier.call_llm_json")
    def test_passes(self, mock_llm):
        mock_llm.return_value = {
            "passed": True,
            "score": 8.5,
            "issues": [],
            "prompt_refinements": "",
        }
        scene = _make_scene()
        script = make_script()
        result = verify_shot(Path("/fake/image.png"), scene, script, None, "model", 100)
        assert result.passed is True
        assert result.score == 8.5
        assert result.issues == []

    @patch("static_shots_maker.pipeline.shot_verifier.call_llm_json")
    def test_fails(self, mock_llm):
        mock_llm.return_value = {
            "passed": False,
            "score": 3.0,
            "issues": ["missing rubber duck", "Billy not visible"],
            "prompt_refinements": "Add a giant rubber duck in the center",
        }
        scene = _make_scene()
        script = make_script()
        result = verify_shot(Path("/fake/image.png"), scene, script, None, "model", 100)
        assert result.passed is False
        assert result.score == 3.0
        assert len(result.issues) == 2
        assert result.prompt_refinements != ""

    def test_llm_failure_returns_pass(self):
        """Fail-open: LLM error should not block pipeline."""
        scene = _make_scene()
        script = make_script()
        # No mock — call_llm_json will fail with None client
        result = verify_shot(Path("/fake/image.png"), scene, script, None, "model", 100)
        assert result.passed is True
        assert result.score == 5.0


class TestCompareCandidates:
    @patch("static_shots_maker.pipeline.shot_verifier.call_llm_json")
    def test_picks_winner(self, mock_llm):
        mock_llm.return_value = {"winner": "b", "reasoning": "better composition"}
        scene = _make_scene()
        script = make_script()
        result = compare_candidates(
            Path("/fake/a.png"), Path("/fake/b.png"), scene, script, None, "model", 100
        )
        assert result == "b"

    def test_llm_failure_returns_a(self):
        """Fail-open: defaults to candidate A."""
        scene = _make_scene()
        script = make_script()
        result = compare_candidates(
            Path("/fake/a.png"), Path("/fake/b.png"), scene, script, None, "model", 100
        )
        assert result == "a"
