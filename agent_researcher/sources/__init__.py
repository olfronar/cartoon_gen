from __future__ import annotations

import logging

from shared.config import Settings

from .base import Source
from .hackernews import HackerNewsSource
from .reddit import RedditSource
from .rss import RSSSource

logger = logging.getLogger(__name__)


def get_active_sources(settings: Settings) -> list[Source]:
    sources: list[Source] = [HackerNewsSource(), RSSSource()]

    if settings.reddit_client_id and settings.reddit_client_secret:
        sources.append(RedditSource(settings))
    else:
        logger.info("Reddit credentials not configured — skipping Reddit source")

    return sources
