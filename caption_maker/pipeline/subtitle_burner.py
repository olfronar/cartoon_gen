from __future__ import annotations

import logging
from pathlib import Path

from shared.ffmpeg import run_ffmpeg

logger = logging.getLogger(__name__)


def burn_subtitles(
    video_path: Path,
    filter_script_path: Path,
    output_path: Path,
) -> Path:
    """Burn subtitles into a video using ffmpeg drawtext filter script.

    Args:
        video_path: Source video file.
        filter_script_path: File containing the drawtext filter chain.
        output_path: Where to write the captioned video.

    Returns:
        The output_path on success.
    """
    run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-filter_script:v",
            str(filter_script_path.resolve()),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )

    logger.info("Burned subtitles: %s", output_path)
    return output_path
