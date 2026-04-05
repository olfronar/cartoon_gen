from __future__ import annotations

import asyncio
import contextlib
import logging

import anthropic

from shared.config import Settings, load_settings
from shared.models import ComedyBrief, RawItem

from .alerts import alert_failure, alert_success
from .brief import generate_brief
from .dedup import dedup_and_filter, filter_already_covered
from .delivery import deliver_brief
from .prefilter import prefilter_items
from .scorer import score_items
from .sources import get_active_sources

logger = logging.getLogger(__name__)

MAX_ITEMS_PER_SOURCE = 30


async def run(settings: Settings | None = None) -> ComedyBrief:
    settings = settings or load_settings()

    try:
        brief = await _pipeline(settings)
    except Exception as exc:
        alert_failure(exc, settings)
        raise

    # Deliver to all configured destinations
    deliveries = deliver_brief(brief, settings)
    for d in deliveries:
        print(f"  Delivered: {d}")

    alert_success(brief, deliveries, settings)
    print(f"Brief: {len(brief.items)} items")

    return brief


async def _pipeline(settings: Settings) -> ComedyBrief:
    sources = get_active_sources(settings)
    logger.info("Active sources: %s", [s.name for s in sources])

    # Parallel fetch
    results = await asyncio.gather(
        *[asyncio.to_thread(source.fetch) for source in sources],
        return_exceptions=True,
    )

    # Flatten, logging any exceptions; cap each source at MAX_ITEMS_PER_SOURCE
    raw_items: list[RawItem] = []
    for source, result in zip(sources, results, strict=True):
        if isinstance(result, BaseException):
            logger.warning("Source %s failed: %s", source.name, result)
        else:
            if len(result) > MAX_ITEMS_PER_SOURCE:
                logger.info(
                    "Source %s returned %d items, capping to %d",
                    source.name,
                    len(result),
                    MAX_ITEMS_PER_SOURCE,
                )
                result = result[:MAX_ITEMS_PER_SOURCE]
            raw_items.extend(result)

    logger.info("Total raw items: %d", len(raw_items))

    # Filter out items with empty URLs (safety net for all sources)
    before_url_filter = len(raw_items)
    raw_items = [item for item in raw_items if item.url.strip()]
    if len(raw_items) < before_url_filter:
        logger.warning(
            "Dropped %d items with empty URLs",
            before_url_filter - len(raw_items),
        )

    # Dedup + freshness filter
    filtered = dedup_and_filter(raw_items)
    logger.info("After dedup/filter: %d items", len(filtered))

    # Cross-day history filter
    with contextlib.suppress(OSError):
        filtered = filter_already_covered(filtered, settings.output_dir)

    # Single Anthropic client shared by prefilter and scorer
    llm_client = (
        anthropic.Anthropic(api_key=settings.anthropic_api_key)
        if settings.anthropic_api_key
        else None
    )

    # LLM pre-filter (Sonnet — fast ranking)
    filtered = await asyncio.to_thread(prefilter_items, filtered, settings, llm_client)
    logger.info("After prefilter: %d items", len(filtered))

    # LLM scoring (Opus — deep analysis)
    scored = await asyncio.to_thread(score_items, filtered, settings, llm_client)

    # Generate brief
    return generate_brief(scored)
