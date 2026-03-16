from __future__ import annotations

import logging
import time
from pathlib import Path

from google.genai import types

logger = logging.getLogger(__name__)


def generate_video(
    prompt: str,
    image_path: Path,
    output_path: Path,
    client,
    model: str,
    duration: int,
    next_scene_image: Path | None = None,
    reference_images: list[Path] | None = None,
) -> Path:
    """Generate a video from a static shot via Veo 3.1 (google-genai).

    Uses image-to-video generation with the static shot as the first frame.
    Optionally provides next scene's static shot as last_frame for interpolation,
    and reference images for character/style consistency.

    Falls back gracefully if features are mutually exclusive in the API.

    Args:
        prompt: Video generation prompt text.
        image_path: Path to the source PNG static shot (first frame).
        output_path: Where to save the MP4 file.
        client: google.genai.Client instance.
        model: Veo model name (e.g. "veo-3.1-fast-generate-preview").
        duration: Video duration in seconds.
        next_scene_image: Optional path to next scene's static shot (last frame).
        reference_images: Optional list of reference image Paths (characters, style).

    Returns:
        The output_path on success.

    Raises:
        RuntimeError: If video generation fails.
    """
    source_image_bytes = image_path.read_bytes()
    source_image = types.Image.from_bytes(data=source_image_bytes, mime_type="image/png")

    last_frame = None
    if next_scene_image:
        try:
            last_frame_bytes = next_scene_image.read_bytes()
            last_frame = types.Image.from_bytes(data=last_frame_bytes, mime_type="image/png")
        except FileNotFoundError:
            logger.warning("Next scene image not found: %s", next_scene_image)

    ref_images = None
    if reference_images:
        ref_images = []
        for ref_path in reference_images:
            ref_bytes = ref_path.read_bytes()
            ref_images.append(
                types.RawReferenceImage(
                    reference_image=types.Image.from_bytes(data=ref_bytes, mime_type="image/png"),
                    reference_id=ref_path.stem,
                )
            )

    # Fallback chain: try most features first, degrade if API rejects
    strategies = _build_strategies(source_image, last_frame, ref_images, prompt, duration, model)

    operation = None
    for strategy_name, config_kwargs in strategies:
        try:
            operation = client.models.generate_videos(**config_kwargs)
            logger.info("Video generation started with strategy: %s", strategy_name)
            break
        except Exception:
            logger.warning("Strategy '%s' failed, trying next fallback", strategy_name)
            continue

    if operation is None:
        raise RuntimeError("All video generation strategies failed")

    # Poll until complete
    while not operation.done:
        time.sleep(10)
        operation = client.operations.get(operation)

    if not operation.response or not operation.response.generated_videos:
        raise RuntimeError("Veo returned no video data")

    video = operation.response.generated_videos[0]
    video_data = client.files.download(file=video.video)

    output_path.write_bytes(video_data)
    logger.info("Saved video: %s", output_path)
    return output_path


def _build_strategies(
    source_image, last_frame, ref_images, prompt, duration, model
) -> list[tuple[str, dict]]:
    """Build ordered list of generation strategies with decreasing feature richness."""
    base_video_config = {
        "aspect_ratio": "9:16",
        "duration_seconds": duration,
    }

    # (name, condition, extra config fields)
    candidates = [
        (
            "full",
            last_frame and ref_images,
            {
                "last_frame": last_frame,
                "reference_images": ref_images,
            },
        ),
        ("source+last_frame", last_frame, {"last_frame": last_frame}),
        ("source+refs", ref_images, {"reference_images": ref_images}),
        ("source_only", True, {}),
    ]

    strategies = []
    for name, condition, extras in candidates:
        if not condition:
            continue
        strategies.append(
            (
                name,
                {
                    "model": model,
                    "prompt": prompt,
                    "source": {"image": source_image},
                    "config": {**base_video_config, **extras},
                },
            )
        )

    return strategies
