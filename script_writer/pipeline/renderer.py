from __future__ import annotations

import json
import logging
from pathlib import Path

from shared.models import CartoonScript

logger = logging.getLogger(__name__)


def render_script_markdown(script: CartoonScript) -> str:
    """Render a CartoonScript to human-readable markdown."""
    lines = [f"# Script: {script.title}", ""]

    # Metadata
    lines.append("## Metadata")
    lines.append(f"- **Date**: {script.date.isoformat()}")
    lines.append(f"- **Source news**: {script.source_item.item.title}")
    lines.append(f"- **Source URL**: {script.source_item.item.url}")
    lines.append(f"- **Comedy angle**: {script.source_item.comedy_angle}")
    lines.append(f"- **Logline**: {script.logline}")
    if script.format_type:
        lines.append(f"- **Format**: {script.format_type}")

    # Synopsis
    lines.append(
        f"- **Synopsis**: {script.synopsis.setup} {script.synopsis.development} "
        f"{script.synopsis.punchline}"
    )
    lines.append("")

    # Characters
    lines.append("## Characters in this episode")
    for char in script.characters_used:
        lines.append(f"- **{char}**")
    lines.append("")

    # Scenes
    lines.append("## Script")
    lines.append("")

    for scene in script.scenes:
        lines.append(f"### Scene {scene.scene_number}: {scene.scene_title}")
        lines.append("")
        lines.append(f"**Setting**: {scene.setting}")
        if scene.billy_emotion:
            lines.append(f"**Billy's emotion**: {scene.billy_emotion}")
        lines.append(f"**Camera**: {scene.camera_movement}")
        lines.append("")
        lines.append(f"**Scene prompt**: {scene.scene_prompt}")
        lines.append("")

        if scene.transformation:
            lines.append(f"**Transformation**: {scene.transformation}")
            lines.append("")

        if scene.dialogue:
            lines.append("**Dialogue**:")
            for d in scene.dialogue:
                lines.append(f"> **{d['character']}**: {d['line']}")
            lines.append("")

        if scene.visual_gag:
            lines.append(f"**Visual gag**: {scene.visual_gag}")

        lines.append(f"**Audio direction**: {scene.audio_direction}")
        lines.append(f"**Duration**: {scene.duration_seconds} seconds")
        lines.append("")
        lines.append("---")
        lines.append("")

    # End card
    lines.append("## End card")
    lines.append(f"**Scene prompt**: {script.end_card_prompt}")
    lines.append("")

    return "\n".join(lines)


def write_script(
    script: CartoonScript,
    index: int,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Write a script as both .md and .json files. Returns (md_path, json_path)."""
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = script.date.isoformat()

    # Markdown
    md_path = output_dir / f"{date_str}_{index}.md"
    md_content = render_script_markdown(script)
    md_path.write_text(md_content, encoding="utf-8")

    # JSON sidecar
    json_path = output_dir / f"{date_str}_{index}.json"
    json_path.write_text(
        json.dumps(script.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info("Script %d written: %s", index, md_path)
    return md_path, json_path
