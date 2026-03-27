import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from agent_researcher.dedup import (
    _merge_items,
    _normalize_url,
    dedup_and_filter,
    filter_already_covered,
)
from tests.conftest import make_raw_item


class TestNormalizeUrl:
    def test_strips_utm_params(self):
        url = "https://example.com/page?utm_source=twitter&id=123"
        result = _normalize_url(url)
        assert "utm_source" not in result
        assert "id=123" in result

    def test_strips_trailing_slash(self):
        assert _normalize_url("https://example.com/page/") == "https://example.com/page"

    def test_strips_fragment(self):
        result = _normalize_url("https://example.com/page#section")
        assert "#" not in result

    def test_preserves_path(self):
        url = "https://example.com/a/b/c"
        assert _normalize_url(url) == url


class TestMergeItems:
    def test_combines_sources(self):
        a = make_raw_item(sources=["hackernews"], score=100)
        b = make_raw_item(sources=["reddit"], score=50)
        merged = _merge_items(a, b)
        assert set(merged.sources) == {"hackernews", "reddit"}

    def test_keeps_higher_score(self):
        a = make_raw_item(score=100)
        b = make_raw_item(score=200)
        merged = _merge_items(a, b)
        assert merged.score == 200

    def test_keeps_earlier_timestamp(self):
        t1 = datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 3, 14, 12, 0, tzinfo=timezone.utc)
        a = make_raw_item(timestamp=t1)
        b = make_raw_item(timestamp=t2)
        merged = _merge_items(a, b)
        assert merged.timestamp == t1


class TestDedupAndFilter:
    def test_empty_list(self):
        assert dedup_and_filter([]) == []

    def test_freshness_filter_drops_old(self):
        now = datetime(2026, 3, 14, 14, 0, tzinfo=timezone.utc)
        old = make_raw_item(
            title="Old item",
            tier="discovery",
            timestamp=now - timedelta(hours=30),
        )
        fresh = make_raw_item(
            title="Fresh item",
            url="https://example.com/fresh",
            tier="discovery",
            timestamp=now - timedelta(hours=2),
        )
        result = dedup_and_filter([old, fresh], now=now)
        assert len(result) == 1
        assert result[0].title == "Fresh item"

    def test_context_tier_48h_cutoff(self):
        now = datetime(2026, 3, 14, 14, 0, tzinfo=timezone.utc)
        item = make_raw_item(
            tier="context",
            timestamp=now - timedelta(hours=30),
        )
        result = dedup_and_filter([item], now=now)
        assert len(result) == 1

    def test_url_dedup_merges_sources(self):
        now = datetime(2026, 3, 14, 14, 0, tzinfo=timezone.utc)
        a = make_raw_item(
            title="Same story",
            url="https://example.com/story",
            sources=["hackernews"],
            score=100,
            timestamp=now - timedelta(hours=1),
        )
        b = make_raw_item(
            title="Same story",
            url="https://example.com/story",
            sources=["reddit"],
            score=50,
            timestamp=now - timedelta(hours=1),
        )
        result = dedup_and_filter([a, b], now=now)
        assert len(result) == 1
        assert set(result[0].sources) == {"hackernews", "reddit"}

    def test_title_dedup_near_duplicates(self):
        now = datetime(2026, 3, 14, 14, 0, tzinfo=timezone.utc)
        a = make_raw_item(
            title="OpenAI Releases GPT-5",
            url="https://a.com",
            sources=["hackernews"],
            timestamp=now - timedelta(hours=1),
        )
        b = make_raw_item(
            title="GPT-5 Released by OpenAI",
            url="https://b.com",
            sources=["reddit"],
            timestamp=now - timedelta(hours=1),
        )
        result = dedup_and_filter([a, b], now=now)
        assert len(result) == 1
        assert len(result[0].sources) == 2

    def test_different_items_preserved(self):
        now = datetime(2026, 3, 14, 14, 0, tzinfo=timezone.utc)
        titles = [
            "Tesla launches new self-driving car",
            "Congress debates cryptocurrency regulation bill",
            "Scientists discover high-temperature superconductor",
            "Apple releases augmented reality headset update",
            "Amazon warehouse workers vote to unionize",
        ]
        items = [
            make_raw_item(
                title=t,
                url=f"https://example.com/{i}",
                timestamp=now - timedelta(hours=1),
            )
            for i, t in enumerate(titles)
        ]
        result = dedup_and_filter(items, now=now)
        assert len(result) == 5

    def test_naive_timestamp_handled(self):
        now = datetime(2026, 3, 14, 14, 0, tzinfo=timezone.utc)
        # Naive datetime (no tzinfo)
        naive_ts = datetime(2026, 3, 14, 13, 0)
        item = make_raw_item(timestamp=naive_ts)
        result = dedup_and_filter([item], now=now)
        assert len(result) == 1

    def test_unknown_tier_uses_24h_default(self):
        now = datetime(2026, 3, 14, 14, 0, tzinfo=timezone.utc)
        # 20h old item with unknown tier — should pass 24h default
        item = make_raw_item(
            tier="unknown_tier",
            timestamp=now - timedelta(hours=20),
        )
        result = dedup_and_filter([item], now=now)
        assert len(result) == 1

        # 30h old item with unknown tier — should be dropped
        old = make_raw_item(
            title="Old unknown",
            url="https://example.com/old",
            tier="unknown_tier",
            timestamp=now - timedelta(hours=30),
        )
        result = dedup_and_filter([old], now=now)
        assert len(result) == 0

    def test_empty_urls_not_merged(self):
        """Two items with empty URLs but different titles should NOT be merged."""
        now = datetime(2026, 3, 14, 14, 0, tzinfo=timezone.utc)
        a = make_raw_item(
            title="Story about cats",
            url="",
            sources=["xai"],
            timestamp=now - timedelta(hours=1),
        )
        b = make_raw_item(
            title="Story about dogs",
            url="",
            sources=["xai"],
            timestamp=now - timedelta(hours=1),
        )
        result = dedup_and_filter([a, b], now=now)
        assert len(result) == 2
        titles = {r.title for r in result}
        assert titles == {"Story about cats", "Story about dogs"}


def _brief_entry(url: str, title: str, score: int = 5) -> dict:
    return {
        "item": {"url": url, "title": title},
        "comedy_potential": score,
    }


def _write_brief_json(
    briefs_dir: Path,
    brief_date: date,
    items: list[dict],
) -> None:
    """Helper to write a minimal brief JSON for testing."""
    data = {
        "date": brief_date.isoformat(),
        "items": items,
    }
    path = briefs_dir / f"{brief_date.isoformat()}.json"
    path.write_text(json.dumps(data), encoding="utf-8")


class TestFilterAlreadyCovered:
    def test_drops_items_matching_previous_url(self, tmp_path):
        briefs_dir = tmp_path / "briefs"
        briefs_dir.mkdir()
        _write_brief_json(
            briefs_dir,
            date(2026, 3, 16),
            [
                _brief_entry("https://example.com/old-story", "Old Story"),
            ],
        )

        items = [
            make_raw_item(title="Old Story Reappears", url="https://example.com/old-story"),
            make_raw_item(title="Brand New Story", url="https://example.com/new-story"),
        ]
        result = filter_already_covered(items, briefs_dir, today=date(2026, 3, 17))
        assert len(result) == 1
        assert result[0].title == "Brand New Story"

    def test_drops_items_matching_previous_title_fuzzy(self, tmp_path):
        briefs_dir = tmp_path / "briefs"
        briefs_dir.mkdir()
        _write_brief_json(
            briefs_dir,
            date(2026, 3, 16),
            [
                _brief_entry("https://a.com/1", "OpenAI Releases GPT-5 Model"),
            ],
        )

        items = [
            make_raw_item(title="GPT-5 Model Released by OpenAI", url="https://b.com/2"),
            make_raw_item(title="Completely Different Topic", url="https://c.com/3"),
        ]
        result = filter_already_covered(items, briefs_dir, today=date(2026, 3, 17))
        assert len(result) == 1
        assert result[0].title == "Completely Different Topic"

    def test_no_match_passes_through(self, tmp_path):
        briefs_dir = tmp_path / "briefs"
        briefs_dir.mkdir()
        _write_brief_json(
            briefs_dir,
            date(2026, 3, 16),
            [
                _brief_entry("https://example.com/covered", "Covered Story"),
            ],
        )

        items = [
            make_raw_item(title="Unrelated Story A", url="https://a.com"),
            make_raw_item(title="Unrelated Story B", url="https://b.com"),
        ]
        result = filter_already_covered(items, briefs_dir, today=date(2026, 3, 17))
        assert len(result) == 2

    def test_empty_briefs_directory(self, tmp_path):
        briefs_dir = tmp_path / "briefs"
        briefs_dir.mkdir()

        items = [make_raw_item(title="Story", url="https://example.com")]
        result = filter_already_covered(items, briefs_dir, today=date(2026, 3, 17))
        assert len(result) == 1

    def test_lookback_window_respected(self, tmp_path):
        briefs_dir = tmp_path / "briefs"
        briefs_dir.mkdir()
        # Brief from 10 days ago — outside default 7-day lookback
        _write_brief_json(
            briefs_dir,
            date(2026, 3, 7),
            [
                _brief_entry("https://example.com/ancient", "Ancient Story"),
            ],
        )

        items = [make_raw_item(title="Ancient Story", url="https://example.com/ancient")]
        result = filter_already_covered(items, briefs_dir, today=date(2026, 3, 17))
        assert len(result) == 1  # Not dropped — too old to be in lookback

    def test_skips_today_brief(self, tmp_path):
        briefs_dir = tmp_path / "briefs"
        briefs_dir.mkdir()
        # Brief from today — should be skipped (it's the one we're generating)
        _write_brief_json(
            briefs_dir,
            date(2026, 3, 17),
            [
                _brief_entry("https://example.com/today", "Today Story"),
            ],
        )

        items = [make_raw_item(title="Today Story", url="https://example.com/today")]
        result = filter_already_covered(items, briefs_dir, today=date(2026, 3, 17))
        assert len(result) == 1  # Not dropped — today's brief is excluded

    def test_empty_url_in_previous_brief_not_matched(self, tmp_path):
        briefs_dir = tmp_path / "briefs"
        briefs_dir.mkdir()
        _write_brief_json(
            briefs_dir,
            date(2026, 3, 16),
            [
                _brief_entry("", "Story With No URL"),
            ],
        )

        # Item with empty URL should NOT match previous empty URL
        items = [make_raw_item(title="Different Story", url="")]
        result = filter_already_covered(items, briefs_dir, today=date(2026, 3, 17))
        assert len(result) == 1

    def test_old_format_backward_compat(self, tmp_path):
        """Old briefs with top_picks/also_notable are still read for cross-day dedup."""
        briefs_dir = tmp_path / "briefs"
        briefs_dir.mkdir()
        entry = _brief_entry(
            "https://example.com/notable",
            "Notable Story",
            3,
        )
        data = {
            "date": "2026-03-16",
            "top_picks": [],
            "also_notable": [entry],
        }
        path = briefs_dir / "2026-03-16.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        items = [make_raw_item(title="Notable Story", url="https://example.com/notable")]
        result = filter_already_covered(items, briefs_dir, today=date(2026, 3, 17))
        assert len(result) == 0
