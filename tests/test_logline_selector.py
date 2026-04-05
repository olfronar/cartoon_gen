from __future__ import annotations

from unittest.mock import MagicMock

from script_writer.pipeline.logline_selector import select_logline
from shared.models import Logline
from tests.conftest import make_scored_item, mock_stream_response

LOGLINES = [
    Logline(
        text="Option A", approach="the_quiet_part", featured_characters=["A"], visual_hook="ha"
    ),
    Logline(text="Option B", approach="the_betrayal", featured_characters=["B"], visual_hook="hb"),
    Logline(
        text="Option C",
        approach="the_image_you_cant_unsee",
        featured_characters=["C"],
        visual_hook="hc",
    ),
]


class TestSelectLogline:
    def test_selects_by_index(self):
        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream_response(
            {"selected_index": 1, "reasoning": "Best comedy"}
        )

        result = select_logline(
            loglines=LOGLINES,
            item=make_scored_item(),
            context_block="ctx",
            client=mock_client,
        )

        assert result.text == "Option B"

    def test_single_logline_returns_immediately(self):
        result = select_logline(
            loglines=[LOGLINES[0]],
            item=make_scored_item(),
            context_block="ctx",
            client=MagicMock(),
        )
        assert result.text == "Option A"

    def test_falls_back_on_error(self):
        mock_client = MagicMock()
        mock_client.messages.stream.side_effect = Exception("fail")

        result = select_logline(
            loglines=LOGLINES,
            item=make_scored_item(),
            context_block="ctx",
            client=mock_client,
        )

        assert result.text == "Option A"
