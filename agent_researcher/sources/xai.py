from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from xai_sdk import Client
from xai_sdk.chat import system, user
from xai_sdk.tools import web_search

from shared.config import Settings
from shared.models import RawItem
from shared.utils import strip_code_fences

logger = logging.getLogger(__name__)

MODEL = "grok-4.20-beta-latest-non-reasoning"
ENGAGEMENT_SCORES = {"viral": 100, "high": 50, "moderate": 20}

SYSTEM_PROMPT = """\
You are a trend research assistant. Use your web search tool to find \
trending content on X (Twitter). Always search before answering. \
Return only valid JSON, no commentary."""

PROMPT = """\
Search X (x.com) for the top 10 most viral or trending posts/threads \
from the last 24 hours in these domains: AI, machine learning, robotics, \
biotechnology, tech industry.

For each, return:
- "title": post summary (1–2 sentences)
- "url": post URL (x.com link), or empty string if unavailable
- "why_trending": why it's getting traction (1 sentence)
- "engagement": one of "viral", "high", "moderate"

Focus on: surprising claims, failures, hype, controversy, absurd announcements.
Exclude: pure news headlines with no reaction, political content.

Return ONLY a JSON array, no other text.
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

        # Parse JSON from response
        text = strip_code_fences(text)

        try:
            posts = json.loads(text)
        except json.JSONDecodeError:
            logger.error("Failed to parse xAI response as JSON:\n%s", text[:500])
            return []

        items: list[RawItem] = []

        for post in posts:
            title = post.get("title", "")
            if not title:
                continue

            engagement = post.get("engagement", "moderate").lower()
            score = ENGAGEMENT_SCORES.get(engagement, 20)

            items.append(
                RawItem(
                    title=title,
                    url=post.get("url", ""),
                    sources=["xai:x.com"],
                    tier="discovery",
                    score=score,
                    timestamp=datetime.now(timezone.utc),
                    snippet=post.get("why_trending", ""),
                )
            )

        logger.info("xAI/X: fetched %d items", len(items))
        return items
