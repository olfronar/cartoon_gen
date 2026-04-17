from __future__ import annotations

import asyncio
import json
import logging
import shutil
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
from shared.models import CartoonScript, SceneScript, ShotResult, ShotsManifest

from .image_generator import generate_image
from .prompt_generator import generate_scene_prompt
from .script_reader import read_scripts
from .shot_verifier import VerificationResult, compare_candidates, verify_shot

logger = logging.getLogger(__name__)


async def run(
    settings: Settings | None = None,
    target_date: date | None = None,
    model_override: str | None = None,
    verify: bool = False,
    candidates: int | None = None,
) -> list[ShotsManifest]:
    """Run the full static shots pipeline."""
    settings = settings or load_settings()

    if not settings.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY required for image generation")

    prompt_model = model_override or settings.shots_prompt_model

    # Create prompt-rewriting client based on model
    if prompt_model.startswith("grok"):
        if not settings.xai_api_key:
            raise RuntimeError("XAI_API_KEY required for Grok model")
        from xai_sdk import Client as XAIClient

        prompt_client = XAIClient(api_key=settings.xai_api_key)
        print(f"Prompt rewriting: {prompt_model} (xAI)")
    elif settings.anthropic_api_key:
        prompt_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        print(f"Prompt rewriting: {prompt_model} (Anthropic)")
    else:
        prompt_client = None
        logger.warning("No LLM API key — will use original prompts with regex fallback")

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

    # Resolve verification settings
    do_verify = verify or settings.shots_verify
    num_candidates = candidates or settings.shots_candidates
    if num_candidates > 1:
        do_verify = True

    # Semaphore for Gemini rate limiting
    semaphore = asyncio.Semaphore(settings.shots_max_concurrency)

    # Level 1: parallel across scripts
    manifests = await asyncio.gather(
        *[
            _process_script(
                index=index,
                script=script,
                context_block=context_block,
                prompt_client=prompt_client,
                prompt_model=prompt_model,
                gemini_client=gemini_client,
                semaphore=semaphore,
                settings=settings,
                reference_images=reference_images,
                art_style=art_style,
                do_verify=do_verify,
                num_candidates=num_candidates,
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
    prompt_client,
    prompt_model: str,
    gemini_client,
    semaphore: asyncio.Semaphore,
    settings: Settings,
    reference_images: list[Path] | None = None,
    art_style: str = "",
    do_verify: bool = False,
    num_candidates: int = 1,
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
                prompt_client,
                prompt_model,
                settings.shots_prompt_max_tokens,
            ),
            gemini_client=gemini_client,
            semaphore=semaphore,
            model=settings.shots_model,
            reference_images=scene_refs if scene_refs else None,
            art_style=art_style,
            scene=scene,
            script=script,
            prompt_client=prompt_client,
            do_verify=do_verify,
            num_candidates=num_candidates,
            verify_model=settings.shots_verify_model,
            verify_max_tokens=settings.shots_verify_max_tokens,
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


async def _generate_with_retries(
    image_prompt: str,
    output_path: Path,
    gemini_client,
    semaphore: asyncio.Semaphore,
    model: str,
    reference_images: list[Path] | None,
    art_style: str,
    label: str,
    max_retries: int = 5,
) -> Path:
    """Generate an image with retry logic. Returns output_path on success, raises on failure."""
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            async with semaphore:
                await asyncio.to_thread(
                    generate_image,
                    image_prompt,
                    output_path,
                    gemini_client,
                    model,
                    reference_images,
                    art_style,
                )
            return output_path
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(
                    "%s attempt %d/%d failed: %s — retrying",
                    label,
                    attempt,
                    max_retries,
                    e,
                )
                await asyncio.sleep(2 * attempt)
    raise last_error  # type: ignore[misc]


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
    art_style: str = "",
    scene: SceneScript | None = None,
    script: CartoonScript | None = None,
    prompt_client=None,
    do_verify: bool = False,
    num_candidates: int = 1,
    verify_model: str = "claude-opus-4-7",
    verify_max_tokens: int = 4096,
) -> ShotResult:
    """Generate a single shot (scene or end card). Retries image generation up to 5 times."""
    max_retries = 5
    try:
        # Step 1: Rewrite prompt via Claude (falls back to regex internally)
        image_prompt = await asyncio.to_thread(prompt_fn)

        if not do_verify or not scene or not script or not prompt_client:
            # Original behavior: generate and return
            await _generate_with_retries(
                image_prompt,
                output_path,
                gemini_client,
                semaphore,
                model,
                reference_images,
                art_style,
                label,
                max_retries,
            )
            print(f"    {label}: OK")
            return ShotResult(
                script_index=script_index,
                scene_number=scene_number,
                success=True,
                output_path=output_path,
                error=None,
            )

        if num_candidates >= 2:
            return await _process_shot_with_candidates(
                label=label,
                scene_number=scene_number,
                script_index=script_index,
                output_path=output_path,
                image_prompt=image_prompt,
                gemini_client=gemini_client,
                semaphore=semaphore,
                model=model,
                reference_images=reference_images,
                art_style=art_style,
                scene=scene,
                script=script,
                prompt_client=prompt_client,
                num_candidates=num_candidates,
                verify_model=verify_model,
                verify_max_tokens=verify_max_tokens,
                max_retries=max_retries,
            )

        # Single candidate with verification
        await _generate_with_retries(
            image_prompt,
            output_path,
            gemini_client,
            semaphore,
            model,
            reference_images,
            art_style,
            label,
            max_retries,
        )
        result = await asyncio.to_thread(
            verify_shot,
            output_path,
            scene,
            script,
            prompt_client,
            verify_model,
            verify_max_tokens,
        )
        if result.passed:
            print(f"    {label}: OK (verified, score={result.score:.1f})")
        elif result.prompt_refinements:
            logger.info("%s failed verification — refining prompt", label)
            refined_prompt = image_prompt + "\n\nREFINEMENT: " + result.prompt_refinements
            try:
                await _generate_with_retries(
                    refined_prompt,
                    output_path,
                    gemini_client,
                    semaphore,
                    model,
                    reference_images,
                    art_style,
                    label,
                    max_retries,
                )
                print(f"    {label}: OK (refined after verification)")
            except Exception:
                logger.warning("%s refinement failed — using original", label)
                print(f"    {label}: OK (verification issues: {'; '.join(result.issues)})")
        else:
            print(f"    {label}: OK (verification issues: {'; '.join(result.issues)})")

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


async def _process_shot_with_candidates(
    label: str,
    scene_number: int,
    script_index: int,
    output_path: Path,
    image_prompt: str,
    gemini_client,
    semaphore: asyncio.Semaphore,
    model: str,
    reference_images: list[Path] | None,
    art_style: str,
    scene: SceneScript,
    script: CartoonScript,
    prompt_client,
    num_candidates: int,
    verify_model: str,
    verify_max_tokens: int,
    max_retries: int,
) -> ShotResult:
    """Generate multiple candidates, verify each, pick the best."""
    candidates: list[tuple[Path, VerificationResult | None]] = []
    stem = output_path.stem
    suffix = output_path.suffix

    for ci in range(num_candidates):
        tag = chr(ord("a") + ci)
        candidate_path = output_path.parent / f"{stem}_candidate_{tag}{suffix}"

        try:
            await _generate_with_retries(
                image_prompt,
                candidate_path,
                gemini_client,
                semaphore,
                model,
                reference_images,
                art_style,
                f"{label} candidate {tag}",
                max_retries,
            )
        except Exception:
            logger.warning("%s candidate %s generation failed", label, tag)
            continue

        vr = await asyncio.to_thread(
            verify_shot,
            candidate_path,
            scene,
            script,
            prompt_client,
            verify_model,
            verify_max_tokens,
        )
        candidates.append((candidate_path, vr))

        # Early exit: first candidate with high score
        if vr.score >= 8.0:
            logger.info("%s candidate %s scored %.1f — early exit", label, tag, vr.score)
            break

    if not candidates:
        raise RuntimeError(f"All {num_candidates} candidates failed for {label}")

    # Pick the best candidate
    if len(candidates) == 1:
        winner_path = candidates[0][0]
    else:
        # Filter to passed candidates
        passed = [(p, vr) for p, vr in candidates if vr and vr.passed]
        if len(passed) >= 2:
            # Compare via VLM
            choice = await asyncio.to_thread(
                compare_candidates,
                passed[0][0],
                passed[1][0],
                scene,
                script,
                prompt_client,
                verify_model,
                verify_max_tokens,
            )
            winner_path = passed[0][0] if choice == "a" else passed[1][0]
        elif len(passed) == 1:
            winner_path = passed[0][0]
        else:
            # Neither passed — pick highest scorer
            best = max(candidates, key=lambda x: x[1].score if x[1] else 0)
            winner_path = best[0]

    # Rename winner to final output path, clean up others
    if winner_path != output_path:
        shutil.move(str(winner_path), str(output_path))

    # Delete loser candidates
    for path, _ in candidates:
        if path != winner_path and path.exists():
            path.unlink()

    best_score = max((vr.score for _, vr in candidates if vr), default=0)
    print(f"    {label}: OK ({len(candidates)} candidates, best score={best_score:.1f})")

    return ShotResult(
        script_index=script_index,
        scene_number=scene_number,
        success=True,
        output_path=output_path,
        error=None,
    )
