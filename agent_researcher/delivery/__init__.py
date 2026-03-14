from __future__ import annotations

import logging

from shared.config import Settings
from shared.models import ComedyBrief

from .local import write_brief_local
from .notion import write_brief_notion

logger = logging.getLogger(__name__)


def deliver_brief(brief: ComedyBrief, settings: Settings) -> list[str]:
    """Deliver brief to all configured destinations. Returns list of delivery descriptions."""
    deliveries: list[str] = []

    # Always write local file
    path = write_brief_local(brief, settings.output_dir)
    deliveries.append(f"Local: {path}")

    # Notion if configured
    if settings.notion_api_key and settings.notion_page_id:
        try:
            url = write_brief_notion(brief, settings)
            deliveries.append(f"Notion: {url}")
        except Exception:
            logger.exception("Notion delivery failed")

    return deliveries
