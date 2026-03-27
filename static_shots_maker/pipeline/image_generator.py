from __future__ import annotations

import logging
from pathlib import Path

from google.genai import types

from shared.context_loader import apply_style_enforcement
from shared.utils import detect_image_media_type

logger = logging.getLogger(__name__)


def generate_image(
    prompt: str,
    output_path: Path,
    client,
    model: str,
    reference_images: list[Path] | None = None,
    art_style: str = "",
) -> Path:
    """Generate a 9:16 PNG image via Gemini and save to output_path.

    Uses generate_content_stream with IMAGE response modality.
    Caller must ensure output_path's parent directory exists.

    Args:
        prompt: Image generation prompt text.
        output_path: Where to save the PNG file.
        client: google.genai.Client instance.
        model: Gemini model name (e.g. "gemini-3.1-flash-image-preview").
        reference_images: Optional list of image Paths to prepend as visual context.
        art_style: Art style guide text to prepend for style enforcement.

    Returns:
        The output_path on success.

    Raises:
        RuntimeError: If image generation fails or returns no image data.
    """
    parts: list = []
    if reference_images:
        for img_path in reference_images:
            img_bytes = img_path.read_bytes()
            mime = detect_image_media_type(img_bytes)
            parts.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))

    parts.append(types.Part.from_text(text=apply_style_enforcement(prompt, art_style)))

    contents = [
        types.Content(
            role="user",
            parts=parts,
        ),
    ]
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
        image_config=types.ImageConfig(aspect_ratio="9:16"),
        response_modalities=["IMAGE"],
    )

    image_data = None
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=config,
    ):
        if chunk.parts is None:
            continue
        part = chunk.parts[0]
        if part.inline_data and part.inline_data.data:
            image_data = part.inline_data.data
            break

    if not image_data:
        raise RuntimeError("Gemini returned no image data")

    output_path.write_bytes(image_data)
    logger.info("Saved image: %s", output_path)
    return output_path
