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

    # Product Hunt (needs both for OAuth token exchange)
    product_hunt_api_key: str = ""
    product_hunt_api_secret: str = ""

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

    # Script Writer
    script_writer_model: str = "claude-opus-4-6"
    script_writer_max_tokens: int = 64000
    characters_dir: Path = field(default_factory=lambda: Path("output/characters"))
    art_style_path: Path = field(default_factory=lambda: Path("output/art_style.md"))
    scripts_output_dir: Path = field(default_factory=lambda: Path("output/scripts"))

    # Static Shots Maker
    google_api_key: str = ""
    shots_model: str = "gemini-3.1-flash-image-preview"
    shots_prompt_model: str = "claude-opus-4-6"
    shots_prompt_max_tokens: int = 4096
    shots_max_concurrency: int = 10
    shots_output_dir: Path = field(default_factory=lambda: Path("output/static_shots"))

    # Video Designer
    video_model: str = "grok-imagine-video"
    video_prompt_model: str = "claude-opus-4-6"
    video_prompt_max_tokens: int = 4096
    video_max_concurrency: int = 5
    video_output_dir: Path = field(default_factory=lambda: Path("output/videos"))
    video_duration: int = 15
    video_resolution: str = "480p"


def load_settings(env_path: str = ".env") -> Settings:
    values = dotenv_values(env_path)

    settings = Settings(
        anthropic_api_key=values.get("ANTHROPIC_API_KEY", ""),
        reddit_client_id=values.get("REDDIT_CLIENT_ID", ""),
        reddit_client_secret=values.get("REDDIT_CLIENT_SECRET", ""),
        reddit_user_agent=values.get("REDDIT_USER_AGENT", "CartoonMakerBot/0.1"),
        xai_api_key=values.get("XAI_API_KEY", ""),
        product_hunt_api_key=values.get("PRODUCT_HUNT_API_KEY", ""),
        product_hunt_api_secret=values.get("PRODUCT_HUNT_API_SECRET", ""),
        bluesky_handle=values.get("BLUESKY_HANDLE", ""),
        bluesky_app_password=values.get("BLUESKY_APP_PASSWORD", ""),
        notion_api_key=values.get("NOTION_API_KEY", ""),
        notion_page_id=values.get("NOTION_PAGE_ID", ""),
        slack_webhook_url=values.get("SLACK_WEBHOOK_URL", ""),
        script_writer_model=values.get("SCRIPT_WRITER_MODEL", "claude-opus-4-6"),
        script_writer_max_tokens=int(values.get("SCRIPT_WRITER_MAX_TOKENS", "64000")),
        characters_dir=Path(values.get("CHARACTERS_DIR", "output/characters")),
        art_style_path=Path(values.get("ART_STYLE_PATH", "output/art_style.md")),
        scripts_output_dir=Path(values.get("SCRIPTS_OUTPUT_DIR", "output/scripts")),
        google_api_key=values.get("GOOGLE_API_KEY", ""),
        shots_model=values.get("SHOTS_MODEL", "gemini-3.1-flash-image-preview"),
        shots_prompt_model=values.get("SHOTS_PROMPT_MODEL", "claude-opus-4-6"),
        shots_prompt_max_tokens=int(values.get("SHOTS_PROMPT_MAX_TOKENS", "4096")),
        shots_max_concurrency=int(values.get("SHOTS_MAX_CONCURRENCY", "10")),
        shots_output_dir=Path(values.get("SHOTS_OUTPUT_DIR", "output/static_shots")),
        video_model=values.get("VIDEO_MODEL", "grok-imagine-video"),
        video_prompt_model=values.get("VIDEO_PROMPT_MODEL", "claude-opus-4-6"),
        video_prompt_max_tokens=int(values.get("VIDEO_PROMPT_MAX_TOKENS", "4096")),
        video_max_concurrency=int(values.get("VIDEO_MAX_CONCURRENCY", "5")),
        video_output_dir=Path(values.get("VIDEO_OUTPUT_DIR", "output/videos")),
        video_duration=int(values.get("VIDEO_DURATION", "15")),
        video_resolution=values.get("VIDEO_RESOLUTION", "480p"),
    )

    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set — LLM scoring will be unavailable")

    if not settings.reddit_client_id:
        logger.info("Reddit credentials not found — Reddit source will be skipped")

    return settings
