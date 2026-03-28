from __future__ import annotations

import logging

from atproto import Client

from shared.config import Settings
from shared.models import RawItem
from shared.utils import parse_iso_utc

logger = logging.getLogger(__name__)

# Search queries to find tech/science/engineering content
SEARCH_QUERIES = [
    "AI artificial intelligence",
    "machine learning LLM",
    "robotics biotech",
    "medicine medical breakthrough",
    "engineering technology innovation",
]

MAX_POSTS_PER_QUERY = 15


class BlueskySource:
    name = "bluesky"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch(self) -> list[RawItem]:
        client = Client()

        # Bluesky search requires authentication
        if not self._settings.bluesky_handle or not self._settings.bluesky_app_password:
            logger.info("Bluesky credentials not configured — skipping")
            return []

        try:
            client.login(
                self._settings.bluesky_handle,
                self._settings.bluesky_app_password,
            )
        except Exception:
            logger.exception("Bluesky login failed")
            return []

        items: list[RawItem] = []

        for query in SEARCH_QUERIES:
            try:
                response = client.app.bsky.feed.search_posts(
                    params={"q": query, "limit": MAX_POSTS_PER_QUERY, "sort": "top"}
                )
            except Exception:
                logger.warning("Bluesky search failed for query: %s", query)
                continue

            for post in response.posts:
                record = post.record
                text = getattr(record, "text", "") or ""
                if not text:
                    continue

                # Build post URL
                handle = post.author.handle
                uri_parts = post.uri.split("/")
                rkey = uri_parts[-1] if uri_parts else ""
                url = f"https://bsky.app/profile/{handle}/post/{rkey}"

                created = parse_iso_utc(getattr(record, "created_at", "") or "")

                like_count = getattr(post, "like_count", 0) or 0
                reply_count = getattr(post, "reply_count", 0) or 0

                # Use first 100 chars as title, full text as snippet
                title = text[:100].replace("\n", " ")
                if len(text) > 100:
                    title += "..."

                items.append(
                    RawItem(
                        title=title,
                        url=url,
                        sources=["bluesky"],
                        tier="discovery",
                        score=like_count,
                        timestamp=created,
                        snippet=text[:200],
                        comment_count=reply_count,
                    )
                )

        logger.info("Bluesky: fetched %d items", len(items))
        return items
