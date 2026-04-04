import json
from unittest.mock import MagicMock, patch

from agent_researcher.prefilter import (
    PREFILTER_TOP_N,
    _fallback_prefilter,
    prefilter_items,
)
from shared.config import Settings
from tests.conftest import make_raw_item


class TestFallbackPrefilter:
    def test_returns_top_n_by_score(self):
        items = [
            make_raw_item(title=f"Item {i}", url=f"https://ex.com/{i}", score=i) for i in range(80)
        ]
        result = _fallback_prefilter(items)
        assert len(result) == PREFILTER_TOP_N
        scores = [r.score for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_returns_all_when_fewer_than_top_n(self):
        items = [make_raw_item(title=f"Item {i}", url=f"https://ex.com/{i}") for i in range(10)]
        result = _fallback_prefilter(items)
        assert len(result) == 10


class TestPrefilterNoKey:
    def test_falls_back_without_api_key(self):
        settings = Settings()
        items = [
            make_raw_item(title=f"Item {i}", url=f"https://ex.com/{i}", score=i) for i in range(80)
        ]
        result = prefilter_items(items, settings)
        assert len(result) == PREFILTER_TOP_N


class TestPrefilterWithMockedAPI:
    def _mock_sonnet_response(
        self, scored_data: list[dict], *, stop_reason: str = "end_turn"
    ) -> MagicMock:
        """Build a mock streaming context manager returning scored_data as JSON."""
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = json.dumps(scored_data)

        message = MagicMock()
        message.content = [text_block]
        message.stop_reason = stop_reason

        stream_ctx = MagicMock()
        stream_ctx.__enter__ = lambda s: s
        stream_ctx.__exit__ = MagicMock(return_value=False)
        stream_ctx.get_final_message.return_value = message
        return stream_ctx

    def test_successful_prefilter(self):
        settings = Settings(anthropic_api_key="test-key")
        items = [
            make_raw_item(title=f"Item {i}", url=f"https://ex.com/{i}", score=1) for i in range(10)
        ]

        # Sonnet scores: items 0,2,4 get high scores, rest get low
        scores = [{"index": i, "score": 9.0 if i % 2 == 0 else 1.0} for i in range(10)]
        stream_ctx = self._mock_sonnet_response(scores)

        with patch("agent_researcher.prefilter.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.stream.return_value = stream_ctx

            result = prefilter_items(items, settings)

        # All 10 returned (fewer than PREFILTER_TOP_N)
        assert len(result) == 10
        # High-scored items come first
        assert result[0].title == "Item 0"
        assert result[1].title == "Item 2"

    def test_api_failure_falls_back(self):
        settings = Settings(anthropic_api_key="test-key")
        items = [
            make_raw_item(title=f"Item {i}", url=f"https://ex.com/{i}", score=i) for i in range(80)
        ]

        with patch("agent_researcher.prefilter.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.stream.side_effect = Exception("API down")

            result = prefilter_items(items, settings)

        assert len(result) == PREFILTER_TOP_N
        # Fallback sorts by raw score
        scores = [r.score for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_invalid_indices_ignored(self):
        settings = Settings(anthropic_api_key="test-key")
        items = [make_raw_item(title="Only item", score=5)]

        scores = [
            {"index": 0, "score": 8.0},
            {"index": 999, "score": 10.0},  # invalid
            {"index": -1, "score": 10.0},  # invalid
        ]
        stream_ctx = self._mock_sonnet_response(scores)

        with patch("agent_researcher.prefilter.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.stream.return_value = stream_ctx

            result = prefilter_items(items, settings)

        assert len(result) == 1
        assert result[0].title == "Only item"

    def test_uses_sonnet_model(self):
        settings = Settings(anthropic_api_key="test-key")
        items = [make_raw_item()]

        scores = [{"index": 0, "score": 5.0}]
        stream_ctx = self._mock_sonnet_response(scores)

        with patch("agent_researcher.prefilter.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.stream.return_value = stream_ctx

            prefilter_items(items, settings)

        call_kwargs = mock_client.messages.stream.call_args[1]
        assert "sonnet" in call_kwargs["model"]
