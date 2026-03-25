from __future__ import annotations

import asyncio
import base64
import logging
import urllib.request
from pathlib import Path

from shared.utils import detect_image_media_type

logger = logging.getLogger(__name__)

_DOWNLOAD_TIMEOUT = 120  # seconds


def _download(url: str) -> bytes:
    """Download a URL with a timeout. Runs in a thread pool."""
    with urllib.request.urlopen(url, timeout=_DOWNLOAD_TIMEOUT) as resp:  # noqa: S310
        return resp.read()


async def generate_video(
    prompt: str,
    image_path: Path,
    output_path: Path,
    client,
    model: str,
    duration: int,
    resolution: str = "720p",
) -> Path:
    """Generate a video from a static shot via xAI grok-imagine-video.

    Uses image-to-video generation with the static shot as the source image.
    The xAI SDK handles polling internally.

    Args:
        prompt: Video generation prompt text.
        image_path: Path to the source PNG static shot.
        output_path: Where to save the MP4 file.
        client: xai_sdk.AsyncClient instance.
        model: xAI model name (e.g. "grok-imagine-video").
        duration: Video duration in seconds.
        resolution: Video resolution (e.g. "720p").

    Returns:
        The output_path on success.

    Raises:
        FileNotFoundError: If image_path does not exist.
        RuntimeError: If video generation fails or is blocked by moderation.
    """
    image_bytes = await asyncio.to_thread(image_path.read_bytes)
    media_type = detect_image_media_type(image_bytes)
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_uri = f"data:{media_type};base64,{b64}"

    response = await client.video.generate(
        prompt=prompt,
        model=model,
        image_url=data_uri,
        duration=duration,
        aspect_ratio="9:16",
        resolution=resolution,
    )

    if not response.respect_moderation:
        raise RuntimeError("Video generation blocked by moderation")

    if not response.url:
        raise RuntimeError("xAI returned no video URL")

    video_data = await asyncio.to_thread(_download, response.url)

    await asyncio.to_thread(output_path.write_bytes, video_data)
    logger.info("Saved video: %s", output_path)
    return output_path
