from __future__ import annotations

import logging
from pathlib import Path

from script_writer.prompts import ART_STYLE_INTERVIEW_SYSTEM, ART_STYLE_TEMPLATE

from .interviewer import run_interview

logger = logging.getLogger(__name__)


def create_art_style(api_key: str, art_style_path: Path, model: str = "claude-opus-4-6") -> Path:
    """Run art style interview and write the style document."""
    context = ""
    if art_style_path.exists():
        context = f"Current art style:\n\n{art_style_path.read_text(encoding='utf-8')}"
        print("\nAn art style document already exists. Starting fresh interview.")
        print("(The existing style will be shown to the AI for context.)\n")

    profile = run_interview(
        api_key=api_key,
        system_prompt=ART_STYLE_INTERVIEW_SYSTEM,
        model=model,
        initial_context=context,
    )

    return _write_art_style(profile, art_style_path)


def _write_art_style(profile: dict, art_style_path: Path) -> Path:
    """Render and write the art style document."""
    art_style_path.parent.mkdir(parents=True, exist_ok=True)

    references = profile.get("visual_references", [])
    references_formatted = "\n".join(f"- {r}" for r in references)

    motifs = profile.get("recurring_motifs", [])
    motifs_formatted = "\n".join(f"- {m}" for m in motifs)

    content = ART_STYLE_TEMPLATE.format(
        style=profile.get("style", ""),
        color_palette=profile.get("color_palette", ""),
        mood_tone=profile.get("mood_tone", ""),
        detail_level=profile.get("detail_level", ""),
        references_formatted=references_formatted or "None specified",
        motifs_formatted=motifs_formatted or "None specified",
        text_conventions=profile.get("text_conventions", ""),
    )

    art_style_path.write_text(content, encoding="utf-8")

    print(f"\nArt style written to {art_style_path}")
    logger.info("Art style written: %s", art_style_path)
    return art_style_path
