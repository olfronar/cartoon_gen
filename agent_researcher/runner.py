from __future__ import annotations

import asyncio
import logging

from shared.config import Settings, load_settings
from shared.models import ComedyBrief, RawItem

from .alerts import alert_failure, alert_success
from .brief import generate_brief
from .dedup import dedup_and_filter
from .delivery import deliver_brief
from .scorer import score_items
from .sources import get_active_sources

logger = logging.getLogger(__name__)


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
    print(f"Top picks: {len(brief.top_picks)}, Also notable: {len(brief.also_notable)}")

    return brief


async def _pipeline(settings: Settings) -> ComedyBrief:
    sources = get_active_sources(settings)
    logger.info("Active sources: %s", [s.name for s in sources])

    # Parallel fetch
    results = await asyncio.gather(
        *[asyncio.to_thread(source.fetch) for source in sources],
        return_exceptions=True,
    )

    # Flatten, logging any exceptions
    raw_items: list[RawItem] = []
    for source, result in zip(sources, results, strict=True):
        if isinstance(result, BaseException):
            logger.warning("Source %s failed: %s", source.name, result)
        else:
            raw_items.extend(result)

    logger.info("Total raw items: %d", len(raw_items))

    # Dedup + freshness filter
    filtered = dedup_and_filter(raw_items)
    logger.info("After dedup/filter: %d items", len(filtered))

    # LLM scoring
    scored = await asyncio.to_thread(score_items, filtered, settings)

    # Generate brief
    return generate_brief(scored)
