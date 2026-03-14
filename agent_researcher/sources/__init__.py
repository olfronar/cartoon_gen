from __future__ import annotations

import logging

from shared.config import Settings

from .base import Source
from .bluesky import BlueskySource
from .hackernews import HackerNewsSource
from .prediction_markets import PredictionMarketsSource
from .producthunt import ProductHuntSource
from .reddit import RedditSource
from .rss import RSSSource
from .xai import XAISource

logger = logging.getLogger(__name__)


def get_active_sources(settings: Settings) -> list[Source]:
    # Always-on sources (no auth needed)
    sources: list[Source] = [
        HackerNewsSource(),
        RSSSource(),
        PredictionMarketsSource(),
    ]

    # Credential-gated sources
    if settings.reddit_client_id and settings.reddit_client_secret:
        sources.append(RedditSource(settings))
    else:
        logger.info("Reddit credentials not configured — skipping Reddit source")

    if settings.xai_api_key:
        sources.append(XAISource(settings))
    else:
        logger.info("XAI_API_KEY not configured — skipping X/Twitter source")

    if settings.product_hunt_api_key and settings.product_hunt_api_secret:
        sources.append(ProductHuntSource(settings))
    else:
        logger.info("Product Hunt credentials not configured — skipping Product Hunt source")

    if settings.bluesky_handle and settings.bluesky_app_password:
        sources.append(BlueskySource(settings))
    else:
        logger.info("Bluesky credentials not configured — skipping Bluesky source")

    return sources
