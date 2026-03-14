from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime, timezone

from shared.config import Settings
from shared.models import RawItem

logger = logging.getLogger(__name__)

PH_API_URL = "https://api.producthunt.com/v2/api/graphql"

QUERY = """\
{
  posts(order: VOTES, first: 20) {
    edges {
      node {
        name
        tagline
        url
        votesCount
        createdAt
        topics {
          edges {
            node {
              name
            }
          }
        }
      }
    }
  }
}
"""

# Filter to tech/AI related topics
AI_TECH_TOPICS = {
    "artificial intelligence",
    "machine learning",
    "developer tools",
    "tech",
    "saas",
    "productivity",
    "api",
    "open source",
    "robotics",
    "automation",
    "data science",
    "chatgpt",
    "llm",
    "generative ai",
}


class ProductHuntSource:
    name = "producthunt"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch(self) -> list[RawItem]:
        if not self._settings.product_hunt_api_key:
            return []

        headers = {
            "Authorization": f"Bearer {self._settings.product_hunt_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        body = json.dumps({"query": QUERY}).encode("utf-8")
        req = urllib.request.Request(PH_API_URL, data=body, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
        except Exception:
            logger.exception("Failed to fetch Product Hunt")
            return []

        items: list[RawItem] = []
        edges = data.get("data", {}).get("posts", {}).get("edges", [])

        for edge in edges:
            node = edge.get("node", {})
            name = node.get("name", "")
            if not name:
                continue

            # Check if any topic matches AI/tech
            topics = {
                t["node"]["name"].lower()
                for t in node.get("topics", {}).get("edges", [])
            }
            if not topics & AI_TECH_TOPICS:
                # Keep it anyway — comedy potential isn't limited to AI topics
                pass

            try:
                timestamp = datetime.fromisoformat(
                    node["createdAt"].replace("Z", "+00:00")
                )
            except (KeyError, ValueError):
                timestamp = datetime.now(timezone.utc)

            tagline = node.get("tagline", "")

            items.append(
                RawItem(
                    title=f"{name}: {tagline}" if tagline else name,
                    url=node.get("url", ""),
                    sources=["producthunt"],
                    tier="discovery",
                    score=node.get("votesCount", 0),
                    timestamp=timestamp,
                    snippet=tagline,
                )
            )

        logger.info("ProductHunt: fetched %d items", len(items))
        return items
