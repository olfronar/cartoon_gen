from __future__ import annotations

import asyncio
import json
import logging
from datetime import date
from pathlib import Path

from shared.config import Settings, load_settings
from shared.models import CartoonScript

from ..auth import load_tokens
from .uploader import upload_video
from .video_finder import find_publishable_videos

logger = logging.getLogger(__name__)


async def run(
    settings: Settings | None = None,
    target_date: date | None = None,
    privacy_level: str = "SELF_ONLY",
) -> None:
    """Upload per-script videos to TikTok."""
    settings = settings or load_settings()

    if not settings.tiktok_client_key or not settings.tiktok_client_secret:
        raise RuntimeError("TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET must be set in .env")

    tokens = load_tokens(settings)
    access_token = tokens["access_token"]

    videos = find_publishable_videos(target_date, settings.video_output_dir)
    logger.info("Uploading %d videos to TikTok", len(videos))

    uploaded = 0
    for index, video_path in videos:
        # Read the corresponding script JSON for title/description
        date_str = video_path.parent.name.rsplit("_", 1)[0]
        script_path = settings.scripts_output_dir / f"{date_str}_{index}.json"

        title = _build_title(script_path, index)

        print(f"  Script {index}: Uploading {video_path.name}...")
        try:
            publish_id = await asyncio.to_thread(
                upload_video, access_token, video_path, title, privacy_level
            )
            print(f"  Script {index}: Published (ID: {publish_id})")
            uploaded += 1
        except Exception:
            logger.exception("Failed to upload script %d", index)
            print(f"  Script {index}: FAILED")

    print(f"\nDone! {uploaded}/{len(videos)} videos uploaded to TikTok.")


def _build_title(script_path: Path, index: int) -> str:
    """Build a TikTok title from the script JSON."""
    if not script_path.is_file():
        return f"Cartoon #{index}"

    data = json.loads(script_path.read_text(encoding="utf-8"))
    script = CartoonScript.from_dict(data)

    parts = [script.title]
    if script.logline:
        parts.append(script.logline)

    return "\n\n".join(parts)[:2200]
