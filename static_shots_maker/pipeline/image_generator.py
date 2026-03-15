from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_image(prompt: str, output_path: Path, client, model: str) -> Path:
    """Generate a 9:16 PNG image via Gemini and save to output_path.

    Uses generate_content_stream with IMAGE response modality.

    Args:
        prompt: Image generation prompt text.
        output_path: Where to save the PNG file.
        client: google.genai.Client instance.
        model: Gemini model name (e.g. "gemini-3.1-flash-image-preview").

    Returns:
        The output_path on success.

    Raises:
        RuntimeError: If image generation fails or returns no image data.
    """
    from google.genai import types

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_data)

    logger.info("Saved image: %s", output_path)
    return output_path
