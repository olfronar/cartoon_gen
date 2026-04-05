from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from script_writer.pipeline.script_expander import expand_script, generate_synopsis
from shared.models import Logline, Synopsis
from tests.conftest import make_scored_item, mock_stream_response

MOCK_SYNOPSIS = {
    "setup": "Robot opens restaurant",
    "development": "Health inspector arrives",
    "punchline": "Inspector is also a robot",
    "estimated_scenes": 6,
    "key_visual_gags": ["robot cooking", "inspector gasping"],
}

MOCK_SCRIPT = {
    "title": "Robot Restaurant",
    "scenes": [
        {
            "scene_number": 1,
            "scene_title": "Opening",
            "setting": "Restaurant kitchen",
            "scene_prompt": "A chrome robot stands in a restaurant kitchen chopping vegetables "
            "with lightning speed. Camera slowly zooms in. Bright cartoon style "
            "with bold outlines. Upbeat jazz music plays. Duration: 5 seconds.",
            "dialogue": [{"character": "Bot", "line": "Welcome!"}],
            "visual_gag": "knife juggling",
            "audio_direction": "jazz",
            "duration_seconds": 5,
            "camera_movement": "slow zoom in",
        },
    ],
    "end_card_prompt": "Show logo",
    "characters_used": ["Bot"],
}

LOGLINE = Logline(
    text="Robot opens restaurant",
    approach="the_quiet_part",
    featured_characters=["Bot"],
    visual_hook="robot cooking",
)


class TestGenerateSynopsis:
    def test_generates_synopsis(self):
        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream_response(MOCK_SYNOPSIS)

        result = generate_synopsis(
            logline=LOGLINE,
            item=make_scored_item(),
            context_block="ctx",
            client=mock_client,
        )

        assert result.setup == "Robot opens restaurant"
        assert result.estimated_scenes == 6
        assert len(result.key_visual_gags) == 2

    def test_raises_on_api_failure(self):
        mock_client = MagicMock()
        mock_client.messages.stream.side_effect = Exception("API error")

        with pytest.raises(Exception):  # noqa: B017
            generate_synopsis(
                logline=LOGLINE,
                item=make_scored_item(),
                context_block="ctx",
                client=mock_client,
            )


class TestExpandScript:
    def test_expands_to_script(self):
        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream_response(MOCK_SCRIPT)

        synopsis = Synopsis(**MOCK_SYNOPSIS)

        result = expand_script(
            logline=LOGLINE,
            synopsis=synopsis,
            item=make_scored_item(),
            script_date=date(2026, 3, 14),
            context_block="ctx",
            client=mock_client,
        )

        assert result.title == "Robot Restaurant"
        assert len(result.scenes) == 1
        assert result.scenes[0].scene_title == "Opening"
        assert result.date == date(2026, 3, 14)
