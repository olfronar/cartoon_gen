from __future__ import annotations

import logging
from datetime import datetime, timezone

import praw

from shared.config import Settings
from shared.models import RawItem

logger = logging.getLogger(__name__)

SUBREDDITS = [
    "LocalLLaMA",
    "technology",
    "engineering",
    "medicine",
    "science",
    "Futurology",
    "worldnews",
    "nottheonion",
    "news",
]
POST_LIMIT = 30


class RedditSource:
    name = "reddit"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch(self) -> list[RawItem]:
        if not self._settings.reddit_client_id:
            return []

        try:
            reddit = praw.Reddit(
                client_id=self._settings.reddit_client_id,
                client_secret=self._settings.reddit_client_secret,
                user_agent=self._settings.reddit_user_agent,
            )
        except Exception:
            logger.exception("Failed to initialize Reddit client")
            return []

        items: list[RawItem] = []

        for sub_name in SUBREDDITS:
            try:
                subreddit = reddit.subreddit(sub_name)
                for post in subreddit.hot(limit=POST_LIMIT):
                    items.append(
                        RawItem(
                            title=post.title,
                            url=f"https://reddit.com{post.permalink}",
                            sources=[f"reddit:r/{sub_name}"],
                            tier="discovery",
                            score=post.score,
                            timestamp=datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
                            snippet=(post.selftext or "")[:200],
                            comment_count=post.num_comments,
                        )
                    )
            except Exception:
                logger.exception("Failed to fetch r/%s", sub_name)

        logger.info("Reddit: fetched %d items", len(items))
        return items
