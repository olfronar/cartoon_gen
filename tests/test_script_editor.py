from __future__ import annotations

from unittest.mock import patch

from script_writer.pipeline.script_editor import review_and_revise, review_script, revise_script
from tests.conftest import make_scored_item, make_script

MOCK_REVIEW_PASS = {
    "dialogue_funny": {"pass": True, "reason": "Last line lands."},
    "news_clear": {"pass": True, "reason": "Billy states the fact plainly."},
    "format_consistent": {"pass": True, "reason": "Dialogue count matches."},
    "visual_specific": {"pass": True, "reason": "Objects named with materials."},
    "emotion_match": {"pass": True, "reason": "Emotion fits the story."},
    "overall_verdict": "pass",
    "revision_notes": "",
}

MOCK_REVIEW_FAIL = {
    "dialogue_funny": {"pass": False, "reason": "Dialogue only states facts."},
    "news_clear": {"pass": True, "reason": "Billy states the fact plainly."},
    "format_consistent": {"pass": True, "reason": "Dialogue count matches."},
    "visual_specific": {"pass": True, "reason": "Objects named with materials."},
    "emotion_match": {"pass": True, "reason": "Emotion fits the story."},
    "overall_verdict": "needs_revision",
    "revision_notes": "Reframe Billy's opening line as a joke.",
}

MOCK_REVISED_SCRIPT = {
    "title": "Revised Episode",
    "scenes": [
        {
            "scene_number": 1,
            "scene_title": "Opening",
            "setting": "Kitchen",
            "scene_prompt": "A robot chef stands in a modern kitchen.",
            "dialogue": [{"character": "Bot", "line": "Well that's new."}],
            "visual_gag": "robot drops pan",
            "audio_direction": "upbeat music",
            "duration_seconds": 15,
            "camera_movement": "slow zoom in",
            "transformation": "",
            "billy_emotion": "amused",
        }
    ],
    "end_card_prompt": "Show logo with confetti",
    "characters_used": ["Bot"],
}


class TestReviewScript:
    @patch("script_writer.pipeline.script_editor.call_llm_json")
    def test_review_returns_structured_feedback(self, mock_llm):
        mock_llm.return_value = MOCK_REVIEW_PASS
        script = make_script()
        item = make_scored_item()

        result = review_script(script, item, "context", client=None)

        assert result["overall_verdict"] == "pass"
        assert result["dialogue_funny"]["pass"] is True
        assert result["news_clear"]["pass"] is True
        assert result["format_consistent"]["pass"] is True
        assert result["visual_specific"]["pass"] is True
        assert result["emotion_match"]["pass"] is True
        assert result["revision_notes"] == ""
        mock_llm.assert_called_once()


class TestReviseScript:
    @patch("script_writer.pipeline.script_editor.call_llm_json")
    def test_revision_produces_valid_script(self, mock_llm):
        mock_llm.return_value = MOCK_REVISED_SCRIPT
        script = make_script()
        item = make_scored_item()

        result = revise_script(script, MOCK_REVIEW_FAIL, item, "context", client=None)

        assert result.title == "Revised Episode"
        assert len(result.scenes) == 1
        assert result.scenes[0].billy_emotion == "amused"
        assert result.date == script.date
        assert result.source_item is script.source_item
        assert result.logline == script.logline
        assert result.synopsis is script.synopsis
        assert result.format_type == script.format_type
        mock_llm.assert_called_once()


class TestReviewAndRevise:
    @patch("script_writer.pipeline.script_editor.call_llm_json")
    def test_review_pass_skips_revision(self, mock_llm):
        mock_llm.return_value = MOCK_REVIEW_PASS
        script = make_script()
        item = make_scored_item()

        result = review_and_revise(script, item, "context", client=None)

        assert result is script
        mock_llm.assert_called_once()

    @patch("script_writer.pipeline.script_editor.call_llm_json")
    def test_review_failure_returns_original(self, mock_llm):
        mock_llm.side_effect = RuntimeError("API down")
        script = make_script()
        item = make_scored_item()

        result = review_and_revise(script, item, "context", client=None)

        assert result is script

    @patch("script_writer.pipeline.script_editor.call_llm_json")
    def test_revision_failure_returns_original(self, mock_llm):
        mock_llm.side_effect = [MOCK_REVIEW_FAIL, RuntimeError("API down")]
        script = make_script()
        item = make_scored_item()

        result = review_and_revise(script, item, "context", client=None)

        assert result is script
        assert mock_llm.call_count == 2
