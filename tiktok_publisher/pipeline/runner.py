from __future__ import annotations

import asyncio
import logging
from datetime import date

from shared.config import Settings, load_settings

from ..auth import load_tokens
from .uploader import upload_video
from .video_finder import find_publishable_videos

logger = logging.getLogger(__name__)


async def run(
    settings: Settings | None = None,
    target_date: date | None = None,
) -> None:
    """Upload per-script videos to TikTok inbox as drafts."""
    settings = settings or load_settings()

    if not settings.tiktok_client_key or not settings.tiktok_client_secret:
        raise RuntimeError("TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET must be set in .env")

    tokens = load_tokens(settings)
    access_token = tokens["access_token"]

    videos = find_publishable_videos(target_date, settings.video_output_dir)
    logger.info("Uploading %d videos to TikTok inbox", len(videos))

    uploaded = 0
    for index, video_path in videos:
        print(f"  Script {index}: Uploading {video_path.name}...")
        try:
            publish_id = await asyncio.to_thread(upload_video, access_token, video_path)
            print(f"  Script {index}: Sent to inbox (ID: {publish_id})")
            uploaded += 1
        except Exception:
            logger.exception("Failed to upload script %d", index)
            print(f"  Script {index}: FAILED")

    print(f"\nDone! {uploaded}/{len(videos)} videos sent to TikTok inbox.")
    if uploaded:
        print("Open TikTok app to review and publish the drafts.")
