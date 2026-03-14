from __future__ import annotations

import json
import logging
import urllib.request

from shared.models import RawItem
from shared.utils import parse_iso_utc

logger = logging.getLogger(__name__)

HN_API_URL = "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=30"


class HackerNewsSource:
    name = "hackernews"

    def fetch(self) -> list[RawItem]:
        try:
            with urllib.request.urlopen(HN_API_URL, timeout=15) as resp:
                data = json.loads(resp.read())
        except Exception:
            logger.exception("Failed to fetch Hacker News")
            return []

        items: list[RawItem] = []
        for hit in data.get("hits", []):
            title = hit.get("title", "")
            if not title:
                continue

            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"

            timestamp = parse_iso_utc(hit.get("created_at", ""))

            snippet = (hit.get("story_text") or "")[:200]

            items.append(
                RawItem(
                    title=title,
                    url=url,
                    sources=["hackernews"],
                    tier="validation",
                    score=hit.get("points", 0) or 0,
                    timestamp=timestamp,
                    snippet=snippet,
                    comment_count=hit.get("num_comments", 0) or 0,
                )
            )

        logger.info("HackerNews: fetched %d items", len(items))
        return items
