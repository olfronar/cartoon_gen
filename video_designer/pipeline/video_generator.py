from __future__ import annotations

import base64
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


def generate_video(
    prompt: str,
    image_path: Path,
    output_path: Path,
    client,
    model: str,
    duration: int,
    resolution: str,
) -> Path:
    """Generate a video from a static shot via xAI grok-imagine-video.

    Reads the PNG at image_path, encodes as base64 data URI, sends to xAI
    image-to-video API. Downloads the resulting video and saves as MP4.
    Caller must ensure output_path's parent directory exists.

    Args:
        prompt: Video generation prompt text.
        image_path: Path to the source PNG static shot.
        output_path: Where to save the MP4 file.
        client: xai_sdk.Client instance.
        model: xAI model name (e.g. "grok-imagine-video").
        duration: Video duration in seconds (1-15).
        resolution: Video resolution (e.g. "480p", "720p").

    Returns:
        The output_path on success.

    Raises:
        RuntimeError: If video generation or download fails.
    """
    # Encode image as base64 data URI
    image_bytes = image_path.read_bytes()
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_uri = f"data:image/png;base64,{b64}"

    # Call xAI image-to-video (SDK handles polling)
    response = client.video.generate(
        prompt=prompt,
        model=model,
        image_url=data_uri,
        duration=duration,
        resolution=resolution,
        aspect_ratio="9:16",
    )

    if not response.url:
        raise RuntimeError("xAI returned no video URL")

    # Download video with streaming to avoid buffering entire file in memory
    with httpx.stream("GET", response.url) as stream, open(output_path, "wb") as f:
        for chunk in stream.iter_bytes():
            f.write(chunk)

    logger.info("Saved video: %s", output_path)
    return output_path
