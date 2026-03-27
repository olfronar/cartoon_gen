from __future__ import annotations

import logging

from notion_client import Client as NotionClient

from shared.config import Settings
from shared.models import ComedyBrief

logger = logging.getLogger(__name__)


def _build_notion_blocks(brief: ComedyBrief) -> list[dict]:
    """Convert ComedyBrief into Notion block objects."""
    blocks: list[dict] = []

    for i, scored in enumerate(brief.items, 1):
        item = scored.item
        sources_str = " / ".join(item.sources)

        # Numbered item as a heading
        blocks.append(
            {
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": f"{i}. {item.title}"}}]
                },
            }
        )

        # Details as bullet points
        details = [f"Source: {sources_str}"]
        if scored.comedy_angle:
            details.append(f"Why it's funny: {scored.comedy_angle}")
        details.append(
            f"Score: {scored.total_score:.1f} "
            f"(comedy={scored.comedy_potential:.0f}, "
            f"resonance={scored.cultural_resonance:.0f}, "
            f"fresh={scored.freshness:.0f})"
        )
        if item.url:
            details.append(f"URL: {item.url}")

        for detail in details:
            blocks.append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": detail}}]
                    },
                }
            )

    return blocks


def write_brief_notion(brief: ComedyBrief, settings: Settings) -> str:
    """Create a Notion page with the brief. Returns the page URL."""
    client = NotionClient(auth=settings.notion_api_key)

    title = f"Comedy Brief — {brief.date.isoformat()}"
    blocks = _build_notion_blocks(brief)

    page = client.pages.create(
        parent={"page_id": settings.notion_page_id},
        properties={
            "title": [{"type": "text", "text": {"content": title}}],
        },
        children=blocks,
    )

    url = page.get("url", "")
    logger.info("Notion page created: %s", url)
    return url
