from agent_researcher.scorer import _fallback_scoring, _prepare_items_json, score_items
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
        assert result[0].comedy_angle == ""


class TestPrepareItemsJson:
    def test_returns_valid_json(self):
        import json

        items = [make_raw_item(title="Test", score=42)]
        result = _prepare_items_json(items)
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["title"] == "Test"
        assert parsed[0]["score"] == 42
        assert parsed[0]["index"] == 0

    def test_no_indent(self):
        items = [make_raw_item()]
        result = _prepare_items_json(items)
        assert "\n" not in result


class TestScoreItemsNoKey:
    def test_falls_back_without_api_key(self):
        settings = Settings()
        items = [make_raw_item(score=50)]
        result = score_items(items, settings)
        assert len(result) == 1
        assert result[0].total_score == 50.0
