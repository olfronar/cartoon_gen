from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime, timezone
from urllib.parse import quote

from shared.models import RawItem

logger = logging.getLogger(__name__)

# Manifold Markets API
MANIFOLD_URL = "https://api.manifold.markets/v0/search-markets"
MANIFOLD_QUERIES = [
    "AI",
    "machine learning",
    "robotics",
    "biotech",
    "tech",
    "medicine",
    "engineering",
    "healthcare",
]


class PredictionMarketsSource:
    name = "prediction_markets"

    def fetch(self) -> list[RawItem]:
        items = self._fetch_manifold()
        logger.info("Prediction markets: fetched %d items", len(items))
        return items

    def _fetch_manifold(self) -> list[RawItem]:
        items: list[RawItem] = []
        seen_ids: set[str] = set()

        for query in MANIFOLD_QUERIES:
            try:
                url = f"{MANIFOLD_URL}?term={quote(query)}&sort=liquidity&limit=10"
                with urllib.request.urlopen(url, timeout=15) as resp:
                    markets = json.loads(resp.read())
            except Exception:
                logger.warning("Manifold fetch failed for query: %s", query)
                continue

            for market in markets:
                market_id = market.get("id", "")
                if market_id in seen_ids:
                    continue
                seen_ids.add(market_id)

                title = market.get("question", "")
                if not title:
                    continue

                volume = market.get("volume", 0) or 0
                volume_24h = market.get("volume24Hours", 0) or 0

                try:
                    created = datetime.fromtimestamp(market["createdTime"] / 1000, tz=timezone.utc)
                except (KeyError, ValueError, TypeError):
                    created = datetime.now(timezone.utc)

                slug = market.get("slug", "")
                if not slug:
                    continue
                creator = market.get("creatorUsername", "")
                market_url = f"https://manifold.markets/{creator}/{slug}"

                # Volume spike indicator: high 24h volume relative to total
                is_spike = volume_24h > 0 and volume > 0 and (volume_24h / volume) > 0.3

                items.append(
                    RawItem(
                        title=title,
                        url=market_url,
                        sources=["manifold"],
                        tier="validation",
                        score=int(volume_24h) if is_spike else int(volume_24h // 2),
                        timestamp=created,
                        snippet=f"Volume: ${volume:.0f} total, ${volume_24h:.0f} 24h"
                        + (" [SPIKE]" if is_spike else ""),
                    )
                )

        return items
