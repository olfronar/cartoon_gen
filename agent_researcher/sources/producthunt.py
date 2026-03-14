from __future__ import annotations

import json
import logging
import urllib.request

from shared.config import Settings
from shared.models import RawItem
from shared.utils import parse_iso_utc

logger = logging.getLogger(__name__)

PH_API_URL = "https://api.producthunt.com/v2/api/graphql"
PH_OAUTH_URL = "https://api.producthunt.com/v2/oauth/token"

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


def _get_access_token(client_id: str, client_secret: str) -> str:
    """Exchange client credentials for an OAuth access token."""
    payload = json.dumps({
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }).encode("utf-8")

    req = urllib.request.Request(
        PH_OAUTH_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())

    return data["access_token"]


class ProductHuntSource:
    name = "producthunt"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch(self) -> list[RawItem]:
        if not self._settings.product_hunt_api_key or not self._settings.product_hunt_api_secret:
            return []

        # OAuth token exchange
        try:
            token = _get_access_token(
                self._settings.product_hunt_api_key,
                self._settings.product_hunt_api_secret,
            )
        except Exception:
            logger.exception("Failed to get Product Hunt access token")
            return []

        headers = {
            "Authorization": f"Bearer {token}",
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

            timestamp = parse_iso_utc(node.get("createdAt", ""))

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
