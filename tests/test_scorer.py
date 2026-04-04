import json
from unittest.mock import MagicMock, patch

from agent_researcher.scorer import (
    SCORE_WEIGHTS,
    _fallback_scoring,
    _prepare_items_list,
    score_items,
)
from shared.config import Settings
from tests.conftest import make_raw_item


class TestFallbackScoring:
    def test_sorted_by_score_descending(self):
        items = [
            make_raw_item(title="Low", score=10),
            make_raw_item(title="High", score=500, url="https://example.com/high"),
            make_raw_item(title="Mid", score=100, url="https://example.com/mid"),
        ]
        result = _fallback_scoring(items)
        scores = [s.total_score for s in result]
        assert scores == sorted(scores, reverse=True)

    def test_multi_source_bonus(self):
        item = make_raw_item(sources=["hackernews", "reddit"], score=100)
        result = _fallback_scoring([item])
        assert result[0].multi_source_bonus == 1.0
        assert result[0].total_score == 101.0

    def test_single_source_no_bonus(self):
        item = make_raw_item(sources=["hackernews"], score=100)
        result = _fallback_scoring([item])
        assert result[0].multi_source_bonus == 0.0
        assert result[0].total_score == 100.0

    def test_comedy_fields_zeroed(self):
        result = _fallback_scoring([make_raw_item()])
        assert result[0].comedy_potential == 0
        assert result[0].cultural_resonance == 0
        assert result[0].freshness == 0
        assert result[0].visual_comedy_potential == 0
        assert result[0].emotional_range == 0
        assert result[0].comedy_angle == ""


class TestPrepareItemsList:
    def test_returns_valid_list(self):
        items = [make_raw_item(title="Test", score=42)]
        result = _prepare_items_list(items)
        assert len(result) == 1
        assert result[0]["title"] == "Test"
        assert result[0]["score"] == 42
        assert result[0]["index"] == 0

    def test_serializable_to_json(self):
        items = [make_raw_item()]
        result = _prepare_items_list(items)
        serialized = json.dumps(result)
        assert "\n" not in serialized


class TestScoreItemsNoKey:
    def test_falls_back_without_api_key(self):
        settings = Settings()
        items = [make_raw_item(score=50)]
        result = score_items(items, settings)
        assert len(result) == 1
        assert result[0].total_score == 50.0


class TestScoreItemsWithMockedAPI:
    def _mock_claude_response(
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

    def test_successful_scoring(self):
        settings = Settings(anthropic_api_key="test-key")
        items = [make_raw_item(title="Test", score=50)]

        scored_data = [
            {
                "index": 0,
                "title": "Rewritten: Test Event Happens",
                "comedy_potential": 8.0,
                "cultural_resonance": 7.0,
                "freshness": 9.0,
                "visual_comedy_potential": 6.0,
                "emotional_range": 7.0,
                "comedy_angle": "It's funny because reasons. 'One-liner here.'",
            }
        ]

        stream_ctx = self._mock_claude_response(scored_data)

        with patch("agent_researcher.scorer.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.stream.return_value = stream_ctx

            result = score_items(items, settings)

        assert len(result) == 1
        assert result[0].comedy_potential == 8.0
        assert result[0].cultural_resonance == 7.0
        assert result[0].freshness == 9.0
        assert result[0].visual_comedy_potential == 6.0
        assert result[0].emotional_range == 7.0
        expected = (
            8.0 * SCORE_WEIGHTS["comedy_potential"]
            + 7.0 * SCORE_WEIGHTS["cultural_resonance"]
            + 9.0 * SCORE_WEIGHTS["freshness"]
            + 6.0 * SCORE_WEIGHTS["visual_comedy_potential"]
            + 7.0 * SCORE_WEIGHTS["emotional_range"]
        )
        assert result[0].total_score == expected
        assert result[0].comedy_angle == "It's funny because reasons. 'One-liner here.'"
        # Title should be rewritten
        assert result[0].item.title == "Rewritten: Test Event Happens"

    def test_title_not_rewritten_when_empty(self):
        settings = Settings(anthropic_api_key="test-key")
        items = [make_raw_item(title="Original Title")]

        scored_data = [
            {
                "index": 0,
                "title": "",
                "comedy_potential": 5.0,
                "cultural_resonance": 5.0,
                "freshness": 5.0,
                "visual_comedy_potential": 5.0,
                "emotional_range": 5.0,
                "comedy_angle": "angle",
            }
        ]

        stream_ctx = self._mock_claude_response(scored_data)

        with patch("agent_researcher.scorer.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.stream.return_value = stream_ctx

            result = score_items(items, settings)

        assert result[0].item.title == "Original Title"

    def test_json_parse_failure_falls_back(self):
        settings = Settings(anthropic_api_key="test-key")
        items = [make_raw_item(score=42)]

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "This is not JSON at all"

        message = MagicMock()
        message.content = [text_block]

        stream_ctx = MagicMock()
        stream_ctx.__enter__ = lambda s: s
        stream_ctx.__exit__ = MagicMock(return_value=False)
        stream_ctx.get_final_message.return_value = message

        with patch("agent_researcher.scorer.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.stream.return_value = stream_ctx

            result = score_items(items, settings)

        # Should fall back to raw score
        assert len(result) == 1
        assert result[0].total_score == 42.0
        assert result[0].comedy_potential == 0

    def test_max_tokens_triggers_split_not_retry(self):
        """When response is truncated (max_tokens), split immediately instead of retrying."""
        settings = Settings(anthropic_api_key="test-key")
        items = [
            make_raw_item(title=f"Item {i}", url=f"https://ex.com/{i}", score=10) for i in range(6)
        ]

        # First call: truncated response (max_tokens) for full batch
        truncated_ctx = self._mock_claude_response([], stop_reason="max_tokens")
        truncated_ctx.get_final_message.return_value.content[
            0
        ].text = '[{"index": 0, "comedy_potential": 5.0, "comedy_angle": "truncat'

        # Second + third calls: successful halves
        left_data = [
            {
                "index": i,
                "comedy_potential": 7.0,
                "cultural_resonance": 5.0,
                "freshness": 5.0,
                "comedy_angle": "angle",
            }
            for i in range(3)
        ]
        right_data = [
            {
                "index": i,
                "comedy_potential": 6.0,
                "cultural_resonance": 4.0,
                "freshness": 4.0,
                "comedy_angle": "angle",
            }
            for i in range(3, 6)
        ]
        left_ctx = self._mock_claude_response(left_data)
        right_ctx = self._mock_claude_response(right_data)

        with patch("agent_researcher.scorer.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.stream.side_effect = [
                truncated_ctx,
                left_ctx,
                right_ctx,
            ]

            result = score_items(items, settings)

        assert len(result) == 6
        # Only 3 calls: 1 truncated + 2 halves (no wasted retries)
        assert mock_client.messages.stream.call_count == 3

    def test_api_exception_falls_back(self):
        settings = Settings(anthropic_api_key="test-key")
        items = [make_raw_item(score=77)]

        with patch("agent_researcher.scorer.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.stream.side_effect = Exception("API down")

            result = score_items(items, settings)

        assert len(result) == 1
        assert result[0].total_score == 77.0

    def test_semantic_dedup_merges_and_removes(self):
        settings = Settings(anthropic_api_key="test-key")
        items = [
            make_raw_item(title="Event A", sources=["hackernews"], url="https://a.com"),
            make_raw_item(title="Event A reworded", sources=["reddit"], url="https://b.com"),
        ]

        scored_data = [
            {
                "index": 0,
                "comedy_potential": 8.0,
                "cultural_resonance": 7.0,
                "freshness": 9.0,
                "visual_comedy_potential": 6.0,
                "emotional_range": 7.0,
                "comedy_angle": "angle-a",
                "duplicate_of": None,
            },
            {
                "index": 1,
                "comedy_potential": 5.0,
                "cultural_resonance": 4.0,
                "freshness": 6.0,
                "visual_comedy_potential": 3.0,
                "emotional_range": 4.0,
                "comedy_angle": "angle-b",
                "duplicate_of": 0,
            },
        ]

        stream_ctx = self._mock_claude_response(scored_data)

        with patch("agent_researcher.scorer.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.stream.return_value = stream_ctx

            result = score_items(items, settings)

        # Only canonical item remains
        assert len(result) == 1
        # Sources merged from both items
        assert set(result[0].item.sources) == {"hackernews", "reddit"}

    def test_duplicate_of_invalid_index_ignored(self):
        settings = Settings(anthropic_api_key="test-key")
        items = [make_raw_item(title="Solo item")]

        scored_data = [
            {
                "index": 0,
                "comedy_potential": 5.0,
                "cultural_resonance": 5.0,
                "freshness": 5.0,
                "visual_comedy_potential": 5.0,
                "emotional_range": 5.0,
                "comedy_angle": "angle",
                "duplicate_of": 999,
            },
        ]

        stream_ctx = self._mock_claude_response(scored_data)

        with patch("agent_researcher.scorer.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.stream.return_value = stream_ctx

            result = score_items(items, settings)

        assert len(result) == 1

    def test_duplicate_of_null_keeps_item(self):
        settings = Settings(anthropic_api_key="test-key")
        items = [make_raw_item(title="Unique item")]

        scored_data = [
            {
                "index": 0,
                "comedy_potential": 6.0,
                "cultural_resonance": 6.0,
                "freshness": 6.0,
                "visual_comedy_potential": 6.0,
                "emotional_range": 6.0,
                "comedy_angle": "angle",
                "duplicate_of": None,
            },
        ]

        stream_ctx = self._mock_claude_response(scored_data)

        with patch("agent_researcher.scorer.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.stream.return_value = stream_ctx

            result = score_items(items, settings)

        assert len(result) == 1
        assert result[0].comedy_potential == 6.0

    def test_max_items_truncation(self):
        settings = Settings(anthropic_api_key="test-key")
        items = [make_raw_item(title=f"Item {i}", url=f"https://ex.com/{i}") for i in range(80)]

        scored_data = [
            {
                "index": i,
                "comedy_potential": 1.0,
                "cultural_resonance": 1.0,
                "freshness": 1.0,
                "comedy_angle": "angle",
            }
            for i in range(50)
        ]

        stream_ctx = self._mock_claude_response(scored_data)

        with patch("agent_researcher.scorer.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.stream.return_value = stream_ctx

            result = score_items(items, settings)

        # Should only score first 50
        assert len(result) == 50

    def test_weighted_scoring_calculation(self):
        settings = Settings(anthropic_api_key="test-key")
        items = [make_raw_item(title="Weighted", sources=["hackernews", "reddit"])]

        scored_data = [
            {
                "index": 0,
                "comedy_potential": 10.0,
                "cultural_resonance": 5.0,
                "freshness": 5.0,
                "visual_comedy_potential": 10.0,
                "emotional_range": 5.0,
                "comedy_angle": "angle",
            }
        ]

        stream_ctx = self._mock_claude_response(scored_data)

        with patch("agent_researcher.scorer.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.stream.return_value = stream_ctx

            result = score_items(items, settings)

        expected = (
            10.0 * SCORE_WEIGHTS["comedy_potential"]
            + 5.0 * SCORE_WEIGHTS["cultural_resonance"]
            + 5.0 * SCORE_WEIGHTS["freshness"]
            + 10.0 * SCORE_WEIGHTS["visual_comedy_potential"]
            + 5.0 * SCORE_WEIGHTS["emotional_range"]
            + 1.0  # multi-source bonus
        )
        assert result[0].total_score == expected

    def test_backward_compat_missing_new_fields(self):
        settings = Settings(anthropic_api_key="test-key")
        items = [make_raw_item(title="Old format")]

        scored_data = [
            {
                "index": 0,
                "comedy_potential": 7.0,
                "cultural_resonance": 6.0,
                "freshness": 8.0,
                "comedy_angle": "angle",
            }
        ]

        stream_ctx = self._mock_claude_response(scored_data)

        with patch("agent_researcher.scorer.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.stream.return_value = stream_ctx

            result = score_items(items, settings)

        assert result[0].visual_comedy_potential == 0.0
        assert result[0].emotional_range == 0.0
        expected = (
            7.0 * SCORE_WEIGHTS["comedy_potential"]
            + 6.0 * SCORE_WEIGHTS["cultural_resonance"]
            + 8.0 * SCORE_WEIGHTS["freshness"]
            + 0.0 * SCORE_WEIGHTS["visual_comedy_potential"]
            + 0.0 * SCORE_WEIGHTS["emotional_range"]
        )
        assert result[0].total_score == expected
