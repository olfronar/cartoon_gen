from __future__ import annotations

from datetime import date
from pathlib import Path

from shared.utils import find_script_videos


def find_publishable_videos(
    target_date: date | None = None,
    video_dir: Path | None = None,
) -> list[tuple[int, Path]]:
    """Find publishable videos for a given date.

    Prefers script_video_captioned.mp4, falls back to script_video.mp4.
    Returns list of (index, path) sorted by index.
    Auto-detects latest date if none specified.
    """
    return find_script_videos(
        target_date,
        video_dir or Path("output/videos"),
        prefer_captioned=True,
    )
