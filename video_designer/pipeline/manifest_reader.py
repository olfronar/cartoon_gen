from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from shared.models import CartoonScript, ShotsManifest
from shared.utils import OUTPUT_INDEX_RE, find_latest_output_date

logger = logging.getLogger(__name__)


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

    if target_date is None:
        target_date = find_latest_output_date(shots_dir)

    date_str = target_date.isoformat()
    results: list[ScriptWithShots] = []

    for manifest_dir in sorted(shots_dir.glob(f"{date_str}_*")):
        if not manifest_dir.is_dir():
            continue
        match = OUTPUT_INDEX_RE.match(manifest_dir.name)
        if not match:
            continue
        index = int(match.group(1))

        manifest_path = manifest_dir / "manifest.json"
        script_path = scripts_dir / f"{date_str}_{index}.json"

        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = ShotsManifest.from_dict(manifest_data)

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
