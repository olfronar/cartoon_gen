from __future__ import annotations

from unittest.mock import MagicMock, patch

from static_shots_maker.pipeline.prompt_generator import (
    _fallback_strip,
    generate_scene_prompt,
)
from tests.conftest import make_scene, make_script


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

    def test_strips_dialogue(self):
        result = _fallback_strip("A robot stands. Billy says: 'Hello world.' Standing tall.")
        assert "says" not in result.lower()
        assert "hello" not in result.lower()
        assert "robot" in result.lower()

    def test_preserves_content(self):
        result = _fallback_strip("A bright red robot in a green kitchen.")
        assert "bright red robot" in result
        assert "green kitchen" in result


class TestGenerateScenePrompt:
    @patch("static_shots_maker.pipeline.prompt_generator.call_llm_text")
    def test_calls_claude(self, mock_llm):
        mock_llm.return_value = "  A frozen moment of a robot chef  "
        scene = make_scene(
            scene_prompt=(
                "A robot chef in a modern kitchen. Pan left to right. "
                "Upbeat music. Duration: 5 seconds."
            ),
            camera_movement="pan left to right",
        )
        script = make_script()

        result = generate_scene_prompt(
            scene, script, "context", MagicMock(), "claude-opus-4-6", 4096
        )
        assert result == "A frozen moment of a robot chef"
        mock_llm.assert_called_once()

    @patch("static_shots_maker.pipeline.prompt_generator.call_llm_text")
    def test_fallback_on_error(self, mock_llm):
        mock_llm.side_effect = RuntimeError("API error")
        scene = make_scene(
            scene_prompt=(
                "A robot chef in a modern kitchen. Pan left to right. "
                "Upbeat music. Duration: 5 seconds."
            ),
            camera_movement="pan left to right",
        )
        script = make_script()

        result = generate_scene_prompt(
            scene, script, "context", MagicMock(), "claude-opus-4-6", 4096
        )
        # Should use fallback — no audio/duration
        assert "audio" not in result.lower()
        assert "duration" not in result.lower()
