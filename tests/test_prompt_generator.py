from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from shared.models import CartoonScript, SceneScript, Synopsis
from static_shots_maker.pipeline.prompt_generator import (
    _fallback_strip,
    generate_end_card_prompt,
    generate_scene_prompt,
)
from tests.conftest import make_scored_item


def _make_scene(**overrides) -> SceneScript:
    defaults = dict(
        scene_number=1,
        scene_title="Opening",
        setting="Kitchen",
        scene_prompt=(
            "A robot chef in a modern kitchen. Pan left to right. "
            "Upbeat music. Duration: 5 seconds."
        ),
        dialogue=[],
        visual_gag="robot drops pan",
        audio_direction="upbeat music",
        duration_seconds=5,
        camera_movement="pan left to right",
    )
    defaults.update(overrides)
    return SceneScript(**defaults)


def _make_script(**overrides) -> CartoonScript:
    defaults = dict(
        title="Test Episode",
        date=date(2026, 3, 14),
        source_item=make_scored_item(),
        logline="test",
        synopsis=Synopsis(
            setup="s",
            escalation="e",
            punchline="p",
            estimated_scenes=1,
            key_visual_gags=[],
        ),
        scenes=[_make_scene()],
        end_card_prompt="Show the logo. Music: fanfare. Duration: 3 seconds.",
        characters_used=["Bot"],
    )
    defaults.update(overrides)
    return CartoonScript(**defaults)


class TestFallbackStrip:
    def test_strips_audio(self):
        result = _fallback_strip("A robot. Audio: upbeat music. Standing tall.")
        assert "audio" not in result.lower()
        assert "robot" in result.lower()

    def test_strips_duration(self):
        result = _fallback_strip("A robot. Duration: 5 seconds. Standing.")
        assert "duration" not in result.lower()

    def test_strips_motion(self):
        result = _fallback_strip("Pan left. A robot stands. Zoom in on face.")
        assert "pan left" not in result.lower()

    def test_preserves_content(self):
        result = _fallback_strip("A bright red robot in a green kitchen.")
        assert "bright red robot" in result
        assert "green kitchen" in result


class TestGenerateScenePrompt:
    @patch("static_shots_maker.pipeline.prompt_generator.call_llm_text")
    def test_calls_claude(self, mock_llm):
        mock_llm.return_value = "  A frozen moment of a robot chef  "
        scene = _make_scene()
        script = _make_script()

        result = generate_scene_prompt(
            scene, script, "context", MagicMock(), "claude-opus-4-6", 4096
        )
        assert result == "A frozen moment of a robot chef"
        mock_llm.assert_called_once()

    @patch("static_shots_maker.pipeline.prompt_generator.call_llm_text")
    def test_fallback_on_error(self, mock_llm):
        mock_llm.side_effect = RuntimeError("API error")
        scene = _make_scene()
        script = _make_script()

        result = generate_scene_prompt(
            scene, script, "context", MagicMock(), "claude-opus-4-6", 4096
        )
        # Should use fallback — no audio/duration
        assert "audio" not in result.lower()
        assert "duration" not in result.lower()


class TestGenerateEndCardPrompt:
    @patch("static_shots_maker.pipeline.prompt_generator.call_llm_text")
    def test_calls_claude(self, mock_llm):
        mock_llm.return_value = "Logo on gradient background"
        script = _make_script()

        result = generate_end_card_prompt(script, "context", MagicMock(), "claude-opus-4-6", 4096)
        assert result == "Logo on gradient background"

    @patch("static_shots_maker.pipeline.prompt_generator.call_llm_text")
    def test_fallback_on_error(self, mock_llm):
        mock_llm.side_effect = RuntimeError("API error")
        script = _make_script()

        result = generate_end_card_prompt(script, "context", MagicMock(), "claude-opus-4-6", 4096)
        assert "logo" in result.lower()
