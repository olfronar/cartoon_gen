from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ART_MATERIAL_NAMES = ("canonical_characters",)


def load_characters(characters_dir: Path) -> dict[str, str]:
    """Load all character profile files. Returns {name: content}."""
    if not characters_dir.exists():
        logger.warning("Characters directory not found: %s", characters_dir)
        return {}

    characters: dict[str, str] = {}
    for path in sorted(characters_dir.glob("*.md")):
        characters[path.stem] = path.read_text(encoding="utf-8")

    logger.info("Loaded %d character profiles", len(characters))
    return characters


def load_art_style(art_style_path: Path) -> str:
    """Load the art style document. Returns empty string if not found."""
    if not art_style_path.exists():
        logger.warning("Art style file not found: %s", art_style_path)
        return ""

    content = art_style_path.read_text(encoding="utf-8")
    logger.info("Loaded art style from %s", art_style_path)
    return content


def load_art_materials(art_materials_dir: Path) -> dict[str, Path]:
    """Load art material image paths. Returns {name: Path} for existing PNGs."""
    if not art_materials_dir.exists():
        logger.info("Art materials directory not found: %s", art_materials_dir)
        return {}

    materials: dict[str, Path] = {}
    for name in ART_MATERIAL_NAMES:
        path = art_materials_dir / f"{name}.png"
        if path.exists():
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
