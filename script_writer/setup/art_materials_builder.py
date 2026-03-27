from __future__ import annotations

import logging
from pathlib import Path

from google import genai

from shared.context_loader import ART_MATERIAL_NAMES, load_art_style, load_characters
from static_shots_maker.pipeline.image_generator import generate_image

logger = logging.getLogger(__name__)

CHARACTER_SHEET_PROMPT = """\
9:16 vertical portrait format.

**Characters**:
{characters_block}

Draw each character full-body, facing the viewer, in a neutral standing pose. \
Simple muted background wash, no text or labels. Consistent proportions \
across all characters. Characters should have clean silhouettes \
with understated expressions — minimal facial detail, the comedy lives in \
posture.
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
    char_prompt = CHARACTER_SHEET_PROMPT.format(
        characters_block=characters_block,
    )
    char_path = art_materials_dir / f"{ART_MATERIAL_NAMES[0]}.png"
    print("Generating canonical character sheet...")
    generate_image(char_prompt, char_path, client, model, art_style=art_style)
    generated.append(char_path)
    print(f"  Saved: {char_path}")

    print(f"\nDone! {len(generated)} art materials generated in {art_materials_dir}")
    return generated
