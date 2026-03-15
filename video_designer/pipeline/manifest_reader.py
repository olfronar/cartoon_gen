from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from shared.models import CartoonScript, ShotResult, ShotsManifest

logger = logging.getLogger(__name__)

_INDEX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_(\d+)$")


@dataclass(slots=True)
class ScriptWithShots:
    index: int
    script: CartoonScript
    manifest: ShotsManifest


def read_manifests(
    target_date: date | None = None,
    shots_dir: Path | None = None,
    scripts_dir: Path | None = None,
) -> list[ScriptWithShots]:
    """Read shots manifests paired with their script JSONs.

    Returns list of ScriptWithShots sorted by index.
    Skips scripts where manifest has no successful shots.
    """
    shots_dir = shots_dir or Path("output/static_shots")
    scripts_dir = scripts_dir or Path("output/scripts")

    if not shots_dir.exists():
        raise FileNotFoundError(f"Shots directory not found: {shots_dir}")

    if target_date is None:
        target_date = _find_latest_date(shots_dir)

    date_str = target_date.isoformat()
    results: list[ScriptWithShots] = []

    for manifest_dir in sorted(shots_dir.glob(f"{date_str}_*")):
        if not manifest_dir.is_dir():
            continue
        match = _INDEX_RE.match(manifest_dir.name)
        if not match:
            continue
        index = int(match.group(1))

        manifest_path = manifest_dir / "manifest.json"
        script_path = scripts_dir / f"{date_str}_{index}.json"

        if not manifest_path.exists() or not script_path.exists():
            logger.warning("Missing manifest or script for index %d, skipping", index)
            continue

        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = _parse_manifest(manifest_data)

            script_data = json.loads(script_path.read_text(encoding="utf-8"))
            script = CartoonScript.from_dict(script_data)
        except Exception:
            logger.exception("Failed to parse manifest/script for index %d, skipping", index)
            continue

        # Skip if no successful shots
        if not any(s.success for s in manifest.shots):
            logger.warning("No successful shots for script %d, skipping", index)
            continue

        results.append(ScriptWithShots(index=index, script=script, manifest=manifest))

    return results


def _find_latest_date(shots_dir: Path) -> date:
    """Find the most recent date by scanning subdirectory names."""
    dates: set[str] = set()
    for path in shots_dir.iterdir():
        if path.is_dir() and _INDEX_RE.match(path.name):
            dates.add(path.name.rsplit("_", 1)[0])
    if not dates:
        raise FileNotFoundError(f"No shot directories found in {shots_dir}")
    return date.fromisoformat(max(dates))


def _parse_manifest(data: dict) -> ShotsManifest:
    """Parse a manifest dict into a ShotsManifest."""
    return ShotsManifest(
        script_title=data["script_title"],
        script_index=data["script_index"],
        date=date.fromisoformat(data["date"]),
        shots=[
            ShotResult(
                script_index=s["script_index"],
                scene_number=s["scene_number"],
                success=s["success"],
                output_path=Path(s["output_path"]) if s["output_path"] else None,
                error=s["error"],
            )
            for s in data["shots"]
        ],
    )
