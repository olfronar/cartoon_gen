from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    # Required
    anthropic_api_key: str = ""

    # Reddit (optional — source skipped if missing)
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "CartoonMakerBot/0.1"

    # xAI (Phase 2)
    xai_api_key: str = ""

    # Product Hunt (Phase 2)
    product_hunt_api_key: str = ""

    # Bluesky (Phase 2 — requires app password)
    bluesky_handle: str = ""
    bluesky_app_password: str = ""

    # Notion (Phase 3)
    notion_api_key: str = ""
    notion_page_id: str = ""

    # Slack (Phase 3)
    slack_webhook_url: str = ""

    # Output
    output_dir: Path = field(default_factory=lambda: Path("output/briefs"))


def load_settings(env_path: str = ".env") -> Settings:
    values = dotenv_values(env_path)

    settings = Settings(
        anthropic_api_key=values.get("ANTHROPIC_API_KEY", ""),
        reddit_client_id=values.get("REDDIT_CLIENT_ID", ""),
        reddit_client_secret=values.get("REDDIT_CLIENT_SECRET", ""),
        reddit_user_agent=values.get("REDDIT_USER_AGENT", "CartoonMakerBot/0.1"),
        xai_api_key=values.get("XAI_API_KEY", ""),
        product_hunt_api_key=values.get("PRODUCT_HUNT_API_KEY", ""),
        bluesky_handle=values.get("BLUESKY_HANDLE", ""),
        bluesky_app_password=values.get("BLUESKY_APP_PASSWORD", ""),
        notion_api_key=values.get("NOTION_API_KEY", ""),
        notion_page_id=values.get("NOTION_PAGE_ID", ""),
        slack_webhook_url=values.get("SLACK_WEBHOOK_URL", ""),
    )

    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set — LLM scoring will be unavailable")

    if not settings.reddit_client_id:
        logger.info("Reddit credentials not found — Reddit source will be skipped")

    return settings
