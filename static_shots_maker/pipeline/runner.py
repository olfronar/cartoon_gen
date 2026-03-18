from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from datetime import date
from pathlib import Path

import anthropic
from google import genai

from shared.config import Settings, load_settings
from shared.context_loader import (
    build_context_block,
    build_reference_image_list,
    load_art_materials,
    load_art_style,
    load_characters,
)
from shared.models import CartoonScript, ShotResult, ShotsManifest

from .image_generator import generate_image
from .prompt_generator import generate_scene_prompt
from .script_reader import read_scripts

logger = logging.getLogger(__name__)


async def run(
    settings: Settings | None = None,
    target_date: date | None = None,
) -> list[ShotsManifest]:
    """Run the full static shots pipeline."""
    settings = settings or load_settings()

    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY required for image generation")

    has_anthropic = bool(settings.anthropic_api_key)
    if not has_anthropic:
        logger.warning("ANTHROPIC_API_KEY not set — will use original prompts with regex fallback")

    # Clients
    anthropic_client = (
        anthropic.Anthropic(api_key=settings.anthropic_api_key) if has_anthropic else None
    )
    gemini_client = genai.Client(api_key=settings.google_api_key)

    # Load context
    characters = load_characters(settings.characters_dir)
    art_style = load_art_style(settings.art_style_path)
    context_block = build_context_block(characters, art_style)

    # Load art materials (reference images for consistency)
    art_materials = load_art_materials(settings.art_materials_dir)
    reference_images = build_reference_image_list(art_materials)

    # Read scripts
    scripts = read_scripts(target_date=target_date, scripts_dir=settings.scripts_output_dir)
    logger.info("Processing %d scripts", len(scripts))

    # Semaphore for Gemini rate limiting
    semaphore = asyncio.Semaphore(settings.shots_max_concurrency)

    # Level 1: parallel across scripts
    manifests = await asyncio.gather(
        *[
            _process_script(
                index=index,
                script=script,
                context_block=context_block,
                anthropic_client=anthropic_client,
                gemini_client=gemini_client,
                semaphore=semaphore,
                settings=settings,
                reference_images=reference_images,
            )
            for index, script in scripts
        ]
    )

    print(f"\nDone! {len(manifests)} shot sets generated to {settings.shots_output_dir}")
    return list(manifests)


async def _process_script(
    index: int,
    script: CartoonScript,
    context_block: str,
    anthropic_client,
    gemini_client,
    semaphore: asyncio.Semaphore,
    settings: Settings,
    reference_images: list[Path] | None = None,
) -> ShotsManifest:
    """Process a single script: generate shots for all scenes + end card.

    Scenes are processed sequentially so each scene's output can serve
    as a reference for the next scene (visual continuity). Script-level
    parallelism is preserved.
    """
    output_dir = settings.shots_output_dir / f"{script.date.isoformat()}_{index}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"  Script {index}: {script.title}")

    # Process scenes sequentially for visual continuity
    shots: list[ShotResult] = []
    prev_scene_path: Path | None = None
    for scene in script.scenes:
        # Build reference list: art materials + previous scene
        scene_refs = list(reference_images or [])
        if prev_scene_path:
            scene_refs.append(prev_scene_path)

        shot = await _process_shot(
            label=f"Scene {scene.scene_number}",
            scene_number=scene.scene_number,
            script_index=index,
            output_path=output_dir / f"scene_{scene.scene_number}.png",
            prompt_fn=lambda s=scene: generate_scene_prompt(
                s,
                script,
                context_block,
                anthropic_client,
                settings.shots_prompt_model,
                settings.shots_prompt_max_tokens,
            ),
            gemini_client=gemini_client,
            semaphore=semaphore,
            model=settings.shots_model,
            reference_images=scene_refs if scene_refs else None,
        )
        shots.append(shot)
        if shot.success and shot.output_path:
            prev_scene_path = shot.output_path

    manifest = ShotsManifest(
        script_title=script.title,
        script_index=index,
        date=script.date,
        shots=shots,
    )

    # Write manifest
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Manifest written: %s", manifest_path)

    return manifest


async def _process_shot(
    label: str,
    scene_number: int,
    script_index: int,
    output_path: Path,
    prompt_fn: Callable[[], str],
    gemini_client,
    semaphore: asyncio.Semaphore,
    model: str,
    reference_images: list[Path] | None = None,
) -> ShotResult:
    """Generate a single shot (scene or end card)."""
    try:
        # Step 1: Rewrite prompt via Claude (falls back to regex internally)
        image_prompt = await asyncio.to_thread(prompt_fn)

        # Step 2: Generate image via Gemini (with semaphore)
        async with semaphore:
            await asyncio.to_thread(
                generate_image,
                image_prompt,
                output_path,
                gemini_client,
                model,
                reference_images,
            )

        print(f"    {label}: OK")
        return ShotResult(
            script_index=script_index,
            scene_number=scene_number,
            success=True,
            output_path=output_path,
            error=None,
        )
    except Exception as e:
        logger.exception("Failed to generate %s for script %d", label, script_index)
        print(f"    {label}: FAILED ({e})")
        return ShotResult(
            script_index=script_index,
            scene_number=scene_number,
            success=False,
            output_path=None,
            error=str(e),
        )
