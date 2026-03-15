from __future__ import annotations

import asyncio
import json
import logging
from datetime import date
from pathlib import Path

import anthropic
from google import genai

from shared.config import Settings, load_settings
from shared.context_loader import build_context_block, load_art_style, load_characters
from shared.models import CartoonScript, ShotResult, ShotsManifest

from .image_generator import generate_image
from .prompt_generator import generate_end_card_prompt, generate_scene_prompt
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
) -> ShotsManifest:
    """Process a single script: generate shots for all scenes + end card."""
    output_dir = settings.shots_output_dir / f"{script.date.isoformat()}_{index}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"  Script {index}: {script.title}")

    # Build tasks for all scenes + end card
    tasks = []
    for scene in script.scenes:
        tasks.append(
            _process_scene(
                scene_number=scene.scene_number,
                script=script,
                script_index=index,
                scene=scene,
                context_block=context_block,
                anthropic_client=anthropic_client,
                gemini_client=gemini_client,
                semaphore=semaphore,
                output_dir=output_dir,
                settings=settings,
            )
        )

    # End card (scene_number=0)
    tasks.append(
        _process_end_card(
            script=script,
            script_index=index,
            context_block=context_block,
            anthropic_client=anthropic_client,
            gemini_client=gemini_client,
            semaphore=semaphore,
            output_dir=output_dir,
            settings=settings,
        )
    )

    # Level 2: parallel across scenes within a script
    shots = await asyncio.gather(*tasks)

    manifest = ShotsManifest(
        script_title=script.title,
        script_index=index,
        date=script.date,
        shots=list(shots),
    )

    # Write manifest
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Manifest written: %s", manifest_path)

    return manifest


async def _process_scene(
    scene_number: int,
    script: CartoonScript,
    script_index: int,
    scene,
    context_block: str,
    anthropic_client,
    gemini_client,
    semaphore: asyncio.Semaphore,
    output_dir: Path,
    settings: Settings,
) -> ShotResult:
    """Generate a single scene shot."""
    output_path = output_dir / f"scene_{scene_number}.png"

    try:
        # Step 1: Rewrite prompt via Claude (or fallback)
        if anthropic_client:
            image_prompt = await asyncio.to_thread(
                generate_scene_prompt,
                scene,
                script,
                context_block,
                anthropic_client,
                settings.shots_prompt_model,
                settings.shots_prompt_max_tokens,
            )
        else:
            from .prompt_generator import _fallback_strip

            image_prompt = _fallback_strip(scene.scene_prompt)

        # Step 2: Generate image via Imagen (with semaphore)
        async with semaphore:
            await asyncio.to_thread(
                generate_image, image_prompt, output_path, gemini_client, settings.shots_model
            )

        print(f"    Scene {scene_number}: OK")
        return ShotResult(
            script_index=script_index,
            scene_number=scene_number,
            success=True,
            output_path=output_path,
            error=None,
        )
    except Exception as e:
        logger.exception("Failed to generate scene %d for script %d", scene_number, script_index)
        print(f"    Scene {scene_number}: FAILED ({e})")
        return ShotResult(
            script_index=script_index,
            scene_number=scene_number,
            success=False,
            output_path=None,
            error=str(e),
        )


async def _process_end_card(
    script: CartoonScript,
    script_index: int,
    context_block: str,
    anthropic_client,
    gemini_client,
    semaphore: asyncio.Semaphore,
    output_dir: Path,
    settings: Settings,
) -> ShotResult:
    """Generate the end card shot."""
    output_path = output_dir / "end_card.png"

    try:
        if anthropic_client:
            image_prompt = await asyncio.to_thread(
                generate_end_card_prompt,
                script,
                context_block,
                anthropic_client,
                settings.shots_prompt_model,
                settings.shots_prompt_max_tokens,
            )
        else:
            from .prompt_generator import _fallback_strip

            image_prompt = _fallback_strip(script.end_card_prompt)

        async with semaphore:
            await asyncio.to_thread(
                generate_image, image_prompt, output_path, gemini_client, settings.shots_model
            )

        print("    End card: OK")
        return ShotResult(
            script_index=script_index,
            scene_number=0,
            success=True,
            output_path=output_path,
            error=None,
        )
    except Exception as e:
        logger.exception("Failed to generate end card for script %d", script_index)
        print(f"    End card: FAILED ({e})")
        return ShotResult(
            script_index=script_index,
            scene_number=0,
            success=False,
            output_path=None,
            error=str(e),
        )
