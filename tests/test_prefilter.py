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
    def _mock_sonnet_response(self, scored_data: list[dict]) -> MagicMock:
        """Build a mock response for client.messages.create()."""
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = json.dumps(scored_data)

        message = MagicMock()
        message.content = [text_block]
        message.stop_reason = "end_turn"
        return message

    def test_successful_prefilter(self):
        settings = Settings(anthropic_api_key="test-key")
        items = [
            make_raw_item(title=f"Item {i}", url=f"https://ex.com/{i}", score=1) for i in range(10)
        ]

        scores = [{"index": i, "score": 9.0 if i % 2 == 0 else 1.0} for i in range(10)]
        mock_response = self._mock_sonnet_response(scores)

        with patch("agent_researcher.prefilter.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = mock_response

            result = prefilter_items(items, settings)

        assert len(result) == 10
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
            mock_client.messages.create.side_effect = Exception("API down")

            result = prefilter_items(items, settings)

        assert len(result) == PREFILTER_TOP_N
        scores = [r.score for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_invalid_indices_ignored(self):
        settings = Settings(anthropic_api_key="test-key")
        items = [make_raw_item(title="Only item", score=5)]

        scores = [
            {"index": 0, "score": 8.0},
            {"index": 999, "score": 10.0},
            {"index": -1, "score": 10.0},
        ]
        mock_response = self._mock_sonnet_response(scores)

        with patch("agent_researcher.prefilter.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = mock_response

            result = prefilter_items(items, settings)

        assert len(result) == 1
        assert result[0].title == "Only item"

    def test_uses_prefilter_model(self):
        settings = Settings(anthropic_api_key="test-key")
        items = [make_raw_item()]

        scores = [{"index": 0, "score": 5.0}]
        mock_response = self._mock_sonnet_response(scores)

        with patch("agent_researcher.prefilter.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = mock_response

            prefilter_items(items, settings)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-opus-4-7"

    def test_no_thinking_enabled(self):
        """Prefilter uses effort=medium without thinking for reliable JSON."""
        settings = Settings(anthropic_api_key="test-key")
        items = [make_raw_item()]

        scores = [{"index": 0, "score": 5.0}]
        mock_response = self._mock_sonnet_response(scores)

        with patch("agent_researcher.prefilter.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = mock_response

            prefilter_items(items, settings)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["output_config"] == {"effort": "medium"}
        assert "thinking" not in call_kwargs
        assert "temperature" not in call_kwargs
