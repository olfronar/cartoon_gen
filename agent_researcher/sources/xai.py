from __future__ import annotations

import logging
from datetime import datetime, timezone

from xai_sdk import Client
from xai_sdk.chat import system, user
from xai_sdk.tools import web_search

from shared.config import Settings
from shared.models import RawItem
from shared.utils import extract_json, strip_code_fences

logger = logging.getLogger(__name__)

MODEL = "grok-4.20-beta-latest-non-reasoning"
ENGAGEMENT_SCORES = {"viral": 100, "high": 50, "moderate": 20}

SYSTEM_PROMPT = """\
You are a trend research assistant. Use your web search tool to find \
trending content on X (Twitter). Search multiple times to get broad coverage. \
Return only valid JSON, no commentary."""

PROMPT = """\
Search X (x.com) for trending and notable posts from the last 24 hours \
in tech, science, medicine, and engineering. Do five separate searches:

Search 1: "AI trending on X today"
Search 2: "tech news trending on X today"
Search 3: "robotics OR biotech trending on X today"
Search 4: "medicine OR medical breakthrough trending on X today"
Search 5: "engineering OR science discovery trending on X today"

After each search, collect every post you find with a real x.com URL. \
Include anything that got notable engagement — it does not need to be \
mega-viral. Cast a wide net: announcements, hot takes, demos, failures, \
drama, controversy, absurd claims, product launches, benchmarks, layoffs, \
acquisitions, policy debates, open-source releases, clinical trials, \
infrastructure projects, scientific discoveries.

For each post, return:
- "title": what the post is about (1–2 sentences)
- "url": the x.com post URL
- "why_trending": why it's getting attention (1 sentence)
- "engagement": "viral", "high", or "moderate"

Skip any item where you do not have a real x.com URL. Do not invent URLs. \
Return as many items as you found across all five searches. More is better — \
I deduplicate downstream.

Return ONLY a JSON array.
"""


class XAISource:
    name = "xai"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch(self) -> list[RawItem]:
        if not self._settings.xai_api_key:
            return []

        try:
            client = Client(api_key=self._settings.xai_api_key)
            chat = client.chat.create(
                model=MODEL,
                tools=[web_search(allowed_domains=["x.com"])],
            )
            chat.append(system(SYSTEM_PROMPT))
            chat.append(user(PROMPT))
            response = chat.sample()
            text = response.content
        except Exception:
            logger.exception("xAI API call failed")
            return []

        # Parse JSON from response — Grok may wrap the array in commentary
        text = strip_code_fences(text)
        try:
            posts = extract_json(text, expect=list)
        except ValueError:
            logger.error("Failed to parse xAI response as JSON:\n%s", text[:500])
            return []

        items: list[RawItem] = []

        for post in posts:
            title = post.get("title", "")
            if not title:
                continue

            url = post.get("url", "").strip()
            if not url:
                logger.debug("xAI: skipping item with empty URL: %s", title[:80])
                continue

            engagement = post.get("engagement", "moderate").lower()
            score = ENGAGEMENT_SCORES.get(engagement, 20)

            items.append(
                RawItem(
                    title=title,
                    url=url,
                    sources=["xai:x.com"],
                    tier="discovery",
                    score=score,
                    timestamp=datetime.now(timezone.utc),
                    snippet=post.get("why_trending", ""),
                )
            )

        logger.info("xAI/X: fetched %d items", len(items))
        return items
