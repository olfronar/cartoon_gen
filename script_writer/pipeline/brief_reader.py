from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

from shared.models import ComedyBrief

logger = logging.getLogger(__name__)


def read_brief(brief_date: date | None = None, briefs_dir: Path | None = None) -> ComedyBrief:
    """Read a comedy brief from the JSON sidecar file.

    If no date is given, auto-detects the latest available brief.
    """
    briefs_dir = briefs_dir or Path("output/briefs")

    if brief_date is None:
        brief_date = _find_latest_brief_date(briefs_dir)

    json_path = briefs_dir / f"{brief_date.isoformat()}.json"

    if not json_path.exists():
        raise FileNotFoundError(f"No brief found at {json_path}")

    data = json.loads(json_path.read_text(encoding="utf-8"))
    brief = ComedyBrief.from_dict(data)

    logger.info("Loaded brief for %s: %d top picks", brief.date, len(brief.top_picks))
    return brief


def _find_latest_brief_date(briefs_dir: Path) -> date:
    """Find the most recent brief date by scanning JSON sidecar files."""
    if not briefs_dir.exists():
        raise FileNotFoundError(f"Briefs directory not found: {briefs_dir}")

    json_files = sorted(briefs_dir.glob("*.json"), reverse=True)
    if not json_files:
        raise FileNotFoundError(f"No brief JSON files found in {briefs_dir}")

    # Filenames are YYYY-MM-DD.json
    return date.fromisoformat(json_files[0].stem)
