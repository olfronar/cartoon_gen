from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from shared.config import Settings
from tests.conftest import make_brief, make_scored_item


@pytest.fixture()
def settings(tmp_path):
    briefs_dir = tmp_path / "briefs"
    briefs_dir.mkdir()
    scripts_dir = tmp_path / "scripts"
    chars_dir = tmp_path / "characters"
    chars_dir.mkdir()
    art_path = tmp_path / "art_style.md"
    art_path.write_text("# Style\nCartoon", encoding="utf-8")

    # Write a brief
    brief = make_brief(top_picks=[make_scored_item(), make_scored_item()])
    (briefs_dir / "2026-03-14.json").write_text(json.dumps(brief.to_dict()), encoding="utf-8")

    # Write a character
    (chars_dir / "bot.md").write_text("# Bot\nA robot", encoding="utf-8")

    return Settings(
        anthropic_api_key="test-key",
        output_dir=briefs_dir,
        characters_dir=chars_dir,
        art_style_path=art_path,
        scripts_output_dir=scripts_dir,
    )


MOCK_LOGLINES = [
    {"text": "L1", "approach": "absurdist", "featured_characters": ["Bot"], "visual_hook": "v1"},
    {"text": "L2", "approach": "satirical", "featured_characters": ["Bot"], "visual_hook": "v2"},
    {"text": "L3", "approach": "surreal", "featured_characters": ["Bot"], "visual_hook": "v3"},
]

MOCK_SELECTION = {"selected_index": 0, "reasoning": "Best"}

MOCK_SYNOPSIS = {
    "setup": "s",
    "escalation": "e",
    "punchline": "p",
    "estimated_scenes": 2,
    "key_visual_gags": ["gag"],
}

MOCK_SCRIPT = {
    "title": "Test Episode",
    "scenes": [
        {
            "scene_number": 1,
            "scene_title": "Scene One",
            "setting": "Lab",
            "scene_prompt": "A robot stands in a laboratory surrounded by blinking screens "
            "and colorful wires. Camera slowly pans right. Bold cartoon style. "
            "Electronic ambient music plays softly. Duration: 5 seconds.",
            "dialogue": [],
            "visual_gag": None,
            "audio_direction": "ambient",
            "duration_seconds": 5,
            "camera_movement": "pan right",
        },
    ],
    "end_card_prompt": "Logo",
    "characters_used": ["Bot"],
}


def _mock_stream(json_data):
    mock_message = MagicMock()
    mock_message.content = [MagicMock(type="text", text=json.dumps(json_data))]
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_stream.get_final_message.return_value = mock_message
    return mock_stream


@pytest.mark.asyncio
async def test_full_pipeline(settings):
    """Integration test: full pipeline with mocked LLM calls."""

    def _route_by_prompt(**kwargs):
        """Return the right mock stream based on prompt content."""
        content = kwargs.get("messages", [{}])[0].get("content", "")
        if "Generate exactly 3 loglines" in content:
            return _mock_stream(MOCK_LOGLINES)
        if "selecting the best logline" in content:
            return _mock_stream(MOCK_SELECTION)
        if "Write a synopsis" in content:
            return _mock_stream(MOCK_SYNOPSIS)
        # Script expansion
        return _mock_stream(MOCK_SCRIPT)

    with patch("anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.stream.side_effect = _route_by_prompt

        from script_writer.pipeline.runner import run

        scripts = await run(settings=settings, target_date=date(2026, 3, 14))

    assert len(scripts) == 2
    assert scripts[0].title == "Test Episode"
    assert settings.scripts_output_dir.exists()


@pytest.mark.asyncio
async def test_pipeline_no_api_key(settings):
    """Pipeline raises without API key."""
    settings = Settings(anthropic_api_key="")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        from script_writer.pipeline.runner import run

        await run(settings=settings)
