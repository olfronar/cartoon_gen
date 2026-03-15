from __future__ import annotations

from unittest.mock import MagicMock, patch

from tests.conftest import make_scene, make_script
from video_designer.pipeline.prompt_generator import (
    _format_dialogue,
    generate_end_card_video_prompt,
    generate_video_prompt,
)


class TestGenerateVideoPrompt:
    @patch("video_designer.pipeline.prompt_generator.call_llm_text")
    def test_calls_claude(self, mock_llm):
        mock_llm.return_value = "  A robot slowly turns its head  "
        scene = make_scene()
        script = make_script()

        result = generate_video_prompt(
            scene, script, "context", MagicMock(), "claude-opus-4-6", 4096
        )
        assert result == "A robot slowly turns its head"
        mock_llm.assert_called_once()

    @patch("video_designer.pipeline.prompt_generator.call_llm_text")
    def test_fallback_on_error(self, mock_llm):
        mock_llm.side_effect = RuntimeError("API error")
        scene = make_scene(scene_prompt="A robot chef in a kitchen.")
        script = make_script()

        result = generate_video_prompt(
            scene, script, "context", MagicMock(), "claude-opus-4-6", 4096
        )
        assert result == "A robot chef in a kitchen."


class TestGenerateEndCardVideoPrompt:
    @patch("video_designer.pipeline.prompt_generator.call_llm_text")
    def test_calls_claude(self, mock_llm):
        mock_llm.return_value = "Logo gently shimmers"
        script = make_script()

        result = generate_end_card_video_prompt(
            script, "context", MagicMock(), "claude-opus-4-6", 4096
        )
        assert result == "Logo gently shimmers"

    @patch("video_designer.pipeline.prompt_generator.call_llm_text")
    def test_fallback_on_error(self, mock_llm):
        mock_llm.side_effect = RuntimeError("API error")
        script = make_script(end_card_prompt="Show the logo.")

        result = generate_end_card_video_prompt(
            script, "context", MagicMock(), "claude-opus-4-6", 4096
        )
        assert result == "Show the logo."


class TestFormatDialogue:
    def test_formats_lines(self):
        dialogue = [
            {"character": "Bot", "line": "Hello!"},
            {"character": "Human", "line": "Hi there."},
        ]
        result = _format_dialogue(dialogue)
        assert '[Bot] says: "Hello!"' in result
        assert '[Human] says: "Hi there."' in result

    def test_empty_dialogue(self):
        assert _format_dialogue([]) == "None"

    def test_missing_keys(self):
        result = _format_dialogue([{"character": "Bot"}])
        assert "[Bot]" in result
