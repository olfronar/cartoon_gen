from __future__ import annotations

import logging
from pathlib import Path

from google import genai

from shared.context_loader import ART_MATERIAL_NAMES, load_art_style, load_characters
from static_shots_maker.pipeline.image_generator import generate_image

logger = logging.getLogger(__name__)

CHARACTER_SHEET_PROMPT = """\
All characters standing together on a plain white background, \
9:16 vertical portrait format.

{characters_block}

Art style: {art_style_summary}

Draw each character full-body, facing the viewer, in a neutral standing pose. \
Plain white background with no text, labels, or annotations. \
Consistent proportions and art style across all characters.
"""


def create_art_materials(
    google_api_key: str,
    characters_dir: Path,
    art_style_path: Path,
    art_materials_dir: Path,
    model: str = "gemini-3.1-flash-image-preview",
) -> list[Path]:
    """Generate canonical reference images for characters.

    Reads existing character profiles and art style doc, then generates:
    - canonical_characters.png: all characters in one reference sheet

    Returns list of generated file paths.
    """
    characters = load_characters(characters_dir)
    art_style = load_art_style(art_style_path)

    if not characters:
        print("No character profiles found. Run character setup first.")
        return []
    if not art_style:
        print("No art style found. Run art style setup first.")
        return []

    art_materials_dir.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=google_api_key)
    generated: list[Path] = []

    # 1. Canonical character sheet
    characters_block = "\n\n".join(
        f"**{name}**:\n{profile}" for name, profile in characters.items()
    )
    art_style_first_line = art_style.strip().split("\n")[0].strip("# ")
    char_prompt = CHARACTER_SHEET_PROMPT.format(
        characters_block=characters_block,
        art_style_summary=art_style_first_line,
    )
    char_path = art_materials_dir / f"{ART_MATERIAL_NAMES[0]}.png"
    print("Generating canonical character sheet...")
    generate_image(char_prompt, char_path, client, model)
    generated.append(char_path)
    print(f"  Saved: {char_path}")

    print(f"\nDone! {len(generated)} art materials generated in {art_materials_dir}")
    return generated
