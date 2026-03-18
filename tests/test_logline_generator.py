from __future__ import annotations

import json
from unittest.mock import MagicMock

from script_writer.pipeline.logline_generator import generate_loglines
from tests.conftest import make_scored_item


def _mock_stream_response(json_data):
    """Create a mock streaming response context manager."""
    mock_message = MagicMock()
    mock_message.content = [
        MagicMock(type="text", text=json.dumps(json_data)),
    ]
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_stream.get_final_message.return_value = mock_message
    return mock_stream


MOCK_LOGLINES_ARRAY = [
    {
        "text": "Robot starts cooking show",
        "approach": "absurdist",
        "featured_characters": ["Chef Bot"],
        "visual_hook": "robot on fire",
    },
    {
        "text": "AI chef reviewed by food critic AI",
        "approach": "satirical",
        "featured_characters": ["Chef Bot", "Critic"],
        "visual_hook": "monocle falls off",
    },
    {
        "text": "Kitchen becomes sentient",
        "approach": "surreal",
        "featured_characters": ["Chef Bot"],
        "visual_hook": "oven walks away",
    },
]

MOCK_LOGLINES = {
    "story_hook": {
        "topic": "AI cooking",
        "angle": "Robot trusted to cook but can't taste food",
        "conflict": "efficiency vs sensory experience",
        "stakes": "humans lose the last thing that made dinner personal",
        "surprise": "the robot's recipes are just scraped from Reddit",
    },
    "loglines": MOCK_LOGLINES_ARRAY,
}


class TestGenerateLoglines:
    def test_generates_three_loglines(self):
        mock_client = MagicMock()
        mock_client.messages.stream.return_value = _mock_stream_response(MOCK_LOGLINES)

        result = generate_loglines(
            item=make_scored_item(),
            context_block="test context",
            client=mock_client,
        )

        assert len(result) == 3
        assert result[0].approach == "absurdist"
        assert result[1].approach == "satirical"
        assert result[2].approach == "surreal"

    def test_returns_empty_on_api_failure(self):
        mock_client = MagicMock()
        mock_client.messages.stream.side_effect = Exception("API error")

        result = generate_loglines(
            item=make_scored_item(),
            context_block="test context",
            client=mock_client,
        )

        assert result == []

    def test_returns_empty_on_bad_json(self):
        mock_client = MagicMock()

        mock_message = MagicMock()
        mock_message.content = [MagicMock(type="text", text="not json")]
        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.get_final_message.return_value = mock_message
        mock_client.messages.stream.return_value = mock_stream

        result = generate_loglines(
            item=make_scored_item(),
            context_block="test context",
            client=mock_client,
        )

        assert result == []
