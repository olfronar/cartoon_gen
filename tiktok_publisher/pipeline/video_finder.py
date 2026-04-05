from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

_INDEX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_(\d+)$")


def find_publishable_videos(
    target_date: date | None = None,
    video_dir: Path | None = None,
) -> list[tuple[int, Path]]:
    """Find publishable videos for a given date.

    Prefers script_video_captioned.mp4, falls back to script_video.mp4.
    Returns list of (index, path) sorted by index.
    Auto-detects latest date if none specified.
    """
    video_dir = video_dir or Path("output/videos")

    if target_date is None:
        target_date = _find_latest_date(video_dir)

    date_str = target_date.isoformat()
    results: list[tuple[int, Path]] = []

    for subdir in sorted(video_dir.glob(f"{date_str}_*")):
        if not subdir.is_dir():
            continue
        match = _INDEX_RE.match(subdir.name)
        if not match:
            continue

        # Prefer captioned, fall back to raw
        captioned = subdir / "script_video_captioned.mp4"
        raw = subdir / "script_video.mp4"

        if captioned.is_file():
            results.append((int(match.group(1)), captioned))
        elif raw.is_file():
            results.append((int(match.group(1)), raw))

    if not results:
        raise FileNotFoundError(f"No publishable videos found for {date_str} in {video_dir}")

    logger.info("Found %d publishable videos for %s", len(results), date_str)
    return results


def _find_latest_date(video_dir: Path) -> date:
    """Find the most recent date by scanning subdirectory names."""
    dates: set[str] = set()
    for path in video_dir.iterdir():
        if path.is_dir() and _INDEX_RE.match(path.name):
            dates.add(path.name.rsplit("_", 1)[0])
    if not dates:
        raise FileNotFoundError(f"No video directories found in {video_dir}")
    return date.fromisoformat(max(dates))
