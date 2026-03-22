from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

_INDEX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_(\d+)$")


def find_script_videos(
    target_date: date | None = None,
    video_dir: Path | None = None,
) -> list[tuple[int, Path]]:
    """Find script_video.mp4 files for a given date.

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

        video_path = subdir / "script_video.mp4"
        if video_path.is_file():
            results.append((int(match.group(1)), video_path))

    if not results:
        raise FileNotFoundError(f"No script_video.mp4 files found for {date_str} in {video_dir}")

    logger.info("Found %d script videos for %s", len(results), date_str)
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
