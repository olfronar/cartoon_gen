from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ART_MATERIAL_NAMES = ("canonical_characters",)


def load_characters(characters_dir: Path) -> dict[str, str]:
    """Load all character profile files. Returns {name: content}."""
    characters: dict[str, str] = {}
    try:
        paths = sorted(characters_dir.glob("*.md"))
    except OSError:
        logger.warning("Characters directory not found: %s", characters_dir)
        return {}

    for path in paths:
        characters[path.stem] = path.read_text(encoding="utf-8")

    logger.info("Loaded %d character profiles", len(characters))
    return characters


def load_art_style(art_style_path: Path) -> str:
    """Load the art style document. Returns empty string if not found."""
    try:
        content = art_style_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("Art style file not found: %s", art_style_path)
        return ""

    logger.info("Loaded art style from %s", art_style_path)
    return content


def load_art_materials(art_materials_dir: Path) -> dict[str, Path]:
    """Load art material image paths. Returns {name: Path} for existing PNGs."""
    materials: dict[str, Path] = {}
    for name in ART_MATERIAL_NAMES:
        path = art_materials_dir / f"{name}.png"
        try:
            path.stat()
        except FileNotFoundError:
            continue
        materials[name] = path
        logger.info("Loaded art material: %s", path)

    return materials


def build_reference_image_list(art_materials: dict[str, Path]) -> list[Path]:
    """Build ordered list of reference image paths from art materials."""
    paths: list[Path] = []
    for name in ART_MATERIAL_NAMES:
        if name in art_materials:
            paths.append(art_materials[name])
    return paths


def build_style_directive(art_style: str, max_chars: int = 3000) -> str:
    """Extract a condensed style directive from the full art style document.

    Keeps complete sections (split on '## ' headers) until the budget is
    reached, prioritising sections in document order (Animation Style, Color
    Palette, Mood & Tone, etc.).  Returns empty string if art_style is empty.
    """
    if not art_style:
        return ""

    # Split into sections on '## ' markdown headers
    parts = art_style.split("\n## ")
    sections: list[str] = []
    for i, part in enumerate(parts):
        section = ("## " + part) if i > 0 else part
        sections.append(section.strip())

    # Accumulate sections up to budget
    kept: list[str] = []
    total = 0
    for section in sections:
        if total + len(section) + 1 > max_chars and kept:
            break
        kept.append(section)
        total += len(section) + 1  # +1 for joining newline

    return "\n\n".join(kept)


def build_context_block(characters: dict[str, str], art_style: str) -> str:
    """Build the shared context block injected into all LLM prompts."""
    parts: list[str] = []

    if art_style:
        parts.append("## Art Style\n\n" + art_style)

    if characters:
        parts.append("## Characters\n")
        for name, profile in characters.items():
            parts.append(f"### {name}\n\n{profile}")

    return "\n\n".join(parts)
