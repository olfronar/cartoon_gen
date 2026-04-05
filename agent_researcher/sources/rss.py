from __future__ import annotations

import logging

import feedparser

from shared.models import RawItem
from shared.utils import parse_feed_timestamp, strip_html

logger = logging.getLogger(__name__)

RSS_FEEDS: dict[str, list[str]] = {
    "rss:arxiv": [
        "http://export.arxiv.org/rss/cs.AI",
        "http://export.arxiv.org/rss/cs.RO",
        "http://export.arxiv.org/rss/cs.CE",
        "http://export.arxiv.org/rss/eess",
        "http://export.arxiv.org/rss/q-bio",
    ],
    "rss:biorxiv": [
        "https://connect.biorxiv.org/biorxiv_xml.php?subject=all",
    ],
    "rss:medrxiv": [
        "https://connect.medrxiv.org/medrxiv_xml.php?subject=all",
    ],
}

MAX_ITEMS_PER_FEED = 30


class RSSSource:
    name = "rss"

    def fetch(self) -> list[RawItem]:
        items: list[RawItem] = []

        for source_name, feed_urls in RSS_FEEDS.items():
            for url in feed_urls:
                try:
                    feed = feedparser.parse(url)
                except Exception:
                    logger.exception("Failed to parse RSS feed: %s", url)
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
                            tier="context",
                            score=0,
                            timestamp=parse_feed_timestamp(entry),
                            snippet=summary,
                        )
                    )

        logger.info("RSS: fetched %d items", len(items))
        return items
