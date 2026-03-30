from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from agent_researcher.sources.hackernews import HackerNewsSource


class TestHackerNewsSource:
    def _mock_hn_response(self, hits: list[dict]) -> bytes:
        return json.dumps({"hits": hits}).encode()

    def test_parses_hits(self):
        hits = [
            {
                "title": "Test HN Post",
                "url": "https://example.com",
                "objectID": "123",
                "points": 42,
                "num_comments": 10,
                "created_at": "2026-03-14T12:00:00Z",
                "story_text": "Some story text here",
            }
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = self._mock_hn_response(hits)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            source = HackerNewsSource()
            items = source.fetch()

        assert len(items) == 1
        assert items[0].title == "Test HN Post"
        assert items[0].score == 42
        assert items[0].comment_count == 10
        assert items[0].sources == ["hackernews"]
        assert items[0].tier == "validation"

    def test_skips_empty_titles(self):
        hits = [{"title": "", "objectID": "123"}, {"title": None, "objectID": "456"}]
        mock_resp = MagicMock()
        mock_resp.read.return_value = self._mock_hn_response(hits)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            items = HackerNewsSource().fetch()

        assert len(items) == 0

    def test_fallback_url_for_ask_hn(self):
        hits = [
            {
                "title": "Ask HN: Something",
                "url": None,
                "objectID": "999",
                "points": 10,
                "num_comments": 5,
                "created_at": "2026-03-14T12:00:00Z",
            }
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = self._mock_hn_response(hits)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            items = HackerNewsSource().fetch()

        assert items[0].url == "https://news.ycombinator.com/item?id=999"

    def test_handles_network_error(self):
        with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
            items = HackerNewsSource().fetch()

        assert items == []


class TestLobstersSource:
    def _mock_response(self, stories: list[dict]) -> bytes:
        return json.dumps(stories).encode()

    def test_parses_stories(self):
        from agent_researcher.sources.lobsters import LobstersSource

        stories = [
            {
                "title": "Test Lobsters Story",
                "url": "https://example.com/story",
                "short_id_url": "https://lobste.rs/s/abc123",
                "score": 25,
                "comment_count": 8,
                "created_at": "2026-03-14T12:00:00.000-05:00",
                "description_plain": "A test description",
            }
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = self._mock_response(stories)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            items = LobstersSource().fetch()

        assert len(items) == 1
        assert items[0].title == "Test Lobsters Story"
        assert items[0].score == 25
        assert items[0].comment_count == 8
        assert items[0].sources == ["lobsters"]
        assert items[0].tier == "validation"

    def test_falls_back_to_short_id_url(self):
        from agent_researcher.sources.lobsters import LobstersSource

        stories = [
            {
                "title": "Discussion Post",
                "url": "",
                "short_id_url": "https://lobste.rs/s/xyz789",
                "score": 10,
                "created_at": "2026-03-14T12:00:00.000-05:00",
            }
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = self._mock_response(stories)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            items = LobstersSource().fetch()

        assert items[0].url == "https://lobste.rs/s/xyz789"

    def test_handles_network_error(self):
        from agent_researcher.sources.lobsters import LobstersSource

        with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
            items = LobstersSource().fetch()

        assert items == []


class TestNewsRSSSource:
    def test_parses_feeds(self):
        from agent_researcher.sources.news_rss import NewsRSSSource

        mock_entry = MagicMock()
        mock_entry.get = lambda key, default="": {
            "title": "Major World Event Happens",
            "link": "https://bbc.co.uk/news/12345",
            "summary": "<p>Breaking news about a major event...</p>",
        }.get(key, default)

        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]

        with patch("feedparser.parse", return_value=mock_feed):
            items = NewsRSSSource().fetch()

        assert len(items) > 0
        assert items[0].tier == "discovery"
        assert "<p>" not in items[0].snippet

    def test_handles_parse_error(self):
        from agent_researcher.sources.news_rss import NewsRSSSource

        with patch("feedparser.parse", side_effect=Exception("parse error")):
            items = NewsRSSSource().fetch()

        assert items == []


class TestRSSSource:
    def test_parses_feeds(self):
        from agent_researcher.sources.rss import RSSSource

        mock_entry = MagicMock()
        mock_entry.get = lambda key, default="": {
            "title": "Test Paper: A Novel Approach",
            "link": "https://arxiv.org/abs/1234",
            "summary": "<p>This paper presents...</p>",
        }.get(key, default)
        mock_entry.__contains__ = lambda s, k: k in {"title", "link", "summary"}

        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]

        with patch("feedparser.parse", return_value=mock_feed):
            source = RSSSource()
            items = source.fetch()

        assert len(items) > 0
        # HTML should be stripped from snippet
        assert "<p>" not in items[0].snippet

    def test_handles_parse_error(self):
        from agent_researcher.sources.rss import RSSSource

        with patch("feedparser.parse", side_effect=Exception("parse error")):
            items = RSSSource().fetch()

        assert items == []
