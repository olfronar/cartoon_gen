from __future__ import annotations

import json
import logging
import re
from datetime import date
from pathlib import Path

from shared.models import CartoonScript

logger = logging.getLogger(__name__)

_SCRIPT_FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d+)\.json$")


def read_scripts(
    target_date: date | None = None,
    scripts_dir: Path | None = None,
) -> list[tuple[int, CartoonScript]]:
    """Read script JSON sidecars for a given date.

    Returns list of (index, CartoonScript) sorted by index.
    If no date is given, auto-detects the latest available date.
    """
    scripts_dir = scripts_dir or Path("output/scripts")

    if target_date is None:
        target_date = _find_latest_script_date(scripts_dir)

    date_str = target_date.isoformat()
    results: list[tuple[int, CartoonScript]] = []

    for path in sorted(scripts_dir.glob(f"{date_str}_*.json")):
        match = _SCRIPT_FILENAME_RE.match(path.name)
        if not match:
            continue
        index = int(match.group(2))
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            script = CartoonScript.from_dict(data)
            results.append((index, script))
            logger.info("Loaded script %d: %s", index, script.title)
        except Exception:
            logger.exception("Failed to parse script %s, skipping", path)

    if not results:
        raise FileNotFoundError(f"No valid script JSONs found for {date_str} in {scripts_dir}")

    return results


def _find_latest_script_date(scripts_dir: Path) -> date:
    """Find the most recent script date by scanning JSON filenames."""
    if not scripts_dir.exists():
        raise FileNotFoundError(f"Scripts directory not found: {scripts_dir}")

    dates: set[str] = set()
    for path in scripts_dir.glob("*.json"):
        match = _SCRIPT_FILENAME_RE.match(path.name)
        if match:
            dates.add(match.group(1))

    if not dates:
        raise FileNotFoundError(f"No script JSON files found in {scripts_dir}")

    return date.fromisoformat(max(dates))
