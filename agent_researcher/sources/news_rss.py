from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import mktime

import feedparser

from shared.models import RawItem
from shared.utils import strip_html

logger = logging.getLogger(__name__)

NEWS_FEEDS: dict[str, list[str]] = {
    "news:bbc": [
        "http://feeds.bbci.co.uk/news/rss.xml",
    ],
    "news:reuters": [
        "https://www.reutersagency.com/feed/?best-topics=world",
    ],
    "news:guardian": [
        "https://www.theguardian.com/world/rss",
    ],
    "news:npr": [
        "https://feeds.npr.org/1001/rss.xml",
    ],
    "news:ap": [
        "https://rsshub.app/apnews/topics/apf-topnews",
    ],
    "news:arstechnica": [
        "https://feeds.arstechnica.com/arstechnica/index",
    ],
}

MAX_ITEMS_PER_FEED = 30


def _parse_timestamp(entry: dict) -> datetime:
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)
        if parsed:
            try:
                return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
            except (ValueError, OverflowError):
                pass
    return datetime.now(timezone.utc)


class NewsRSSSource:
    name = "news_rss"

    def fetch(self) -> list[RawItem]:
        items: list[RawItem] = []

        for source_name, feed_urls in NEWS_FEEDS.items():
            for url in feed_urls:
                try:
                    feed = feedparser.parse(url)
                except Exception:
                    logger.exception("Failed to parse news RSS feed: %s", url)
                    continue

                for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
                    title = entry.get("title", "").strip()
                    if not title:
                        continue

                    link = entry.get("link", "").strip()
                    if not link:
                        continue

                    summary = strip_html(entry.get("summary", ""))[:200]

                    items.append(
                        RawItem(
                            title=title,
                            url=link,
                            sources=[source_name],
                            tier="discovery",
                            score=0,
                            timestamp=_parse_timestamp(entry),
                            snippet=summary,
                        )
                    )

        logger.info("News RSS: fetched %d items", len(items))
        return items
