from agent_researcher.sources import get_active_sources
from shared.config import Settings


class TestGetActiveSources:
    def test_always_includes_hn_rss_predictions_lobsters_news(self):
        settings = Settings()
        sources = get_active_sources(settings)
        names = [s.name for s in sources]
        assert "hackernews" in names
        assert "lobsters" in names
        assert "rss" in names
        assert "news_rss" in names
        assert "prediction_markets" in names

    def test_skips_reddit_without_credentials(self):
        settings = Settings()
        sources = get_active_sources(settings)
        names = [s.name for s in sources]
        assert "reddit" not in names

    def test_includes_reddit_with_credentials(self):
        settings = Settings(reddit_client_id="id", reddit_client_secret="secret")
        sources = get_active_sources(settings)
        names = [s.name for s in sources]
        assert "reddit" in names

    def test_skips_xai_without_key(self):
        settings = Settings()
        names = [s.name for s in get_active_sources(settings)]
        assert "xai" not in names

    def test_includes_xai_with_key(self):
        settings = Settings(xai_api_key="key")
        names = [s.name for s in get_active_sources(settings)]
        assert "xai" in names

    def test_skips_bluesky_without_credentials(self):
        settings = Settings()
        names = [s.name for s in get_active_sources(settings)]
        assert "bluesky" not in names

    def test_includes_bluesky_with_credentials(self):
        settings = Settings(bluesky_handle="user.bsky.social", bluesky_app_password="pass")
        names = [s.name for s in get_active_sources(settings)]
        assert "bluesky" in names

    def test_skips_producthunt_without_both_keys(self):
        settings = Settings(product_hunt_api_key="key")
        names = [s.name for s in get_active_sources(settings)]
        assert "producthunt" not in names

    def test_includes_producthunt_with_both_keys(self):
        settings = Settings(product_hunt_api_key="key", product_hunt_api_secret="secret")
        names = [s.name for s in get_active_sources(settings)]
        assert "producthunt" in names
