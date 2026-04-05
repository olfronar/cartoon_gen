from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

ENCODE_ARGS = ["-c:v", "libx264", "-preset", "fast", "-c:a", "aac"]


def run_ffmpeg(cmd: list[str]) -> None:
    """Run an ffmpeg command, raising on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(
            "ffmpeg failed: %s",
            result.stderr[-500:] if result.stderr else "unknown",
        )
        raise RuntimeError(f"ffmpeg failed with exit code {result.returncode}")


def probe_video(path: Path) -> tuple[int, int, float]:
    """Probe a video file for width, height, and fps. Returns defaults on failure."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,r_frame_rate",
                "-of",
                "csv=p=0",
                str(path),
            ],
            capture_output=True,
            text=True,
        )
        parts = result.stdout.strip().split(",")
        width = int(parts[0])
        height = int(parts[1])
        num, den = parts[2].split("/")
        fps = int(num) / int(den)
        return width, height, fps
    except Exception:
        logger.warning("Failed to probe %s, using 480p 9:16 defaults", path)
        return 270, 480, 30.0
