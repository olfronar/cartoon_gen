from __future__ import annotations

import json
import logging
import urllib.request

from shared.models import RawItem
from shared.utils import parse_iso_utc

logger = logging.getLogger(__name__)

LOBSTERS_API_URL = "https://lobste.rs/hottest.json"
MAX_ITEMS = 30


class LobstersSource:
    name = "lobsters"

    def fetch(self) -> list[RawItem]:
        try:
            req = urllib.request.Request(
                LOBSTERS_API_URL,
                headers={"User-Agent": "CartoonMakerBot/0.1"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
        except Exception:
            logger.exception("Failed to fetch Lobsters")
            return []

        items: list[RawItem] = []
        for story in data[:MAX_ITEMS]:
            title = story.get("title", "")
            if not title:
                continue

            url = story.get("url") or story.get("short_id_url", "")
            if not url:
                continue

            items.append(
                RawItem(
                    title=title,
                    url=url,
                    sources=["lobsters"],
                    tier="validation",
                    score=story.get("score", 0) or 0,
                    timestamp=parse_iso_utc(story.get("created_at", "")),
                    snippet=(story.get("description_plain") or "")[:200],
                    comment_count=story.get("comment_count", 0) or 0,
                )
            )

        logger.info("Lobsters: fetched %d items", len(items))
        return items
