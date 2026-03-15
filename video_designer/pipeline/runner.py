from __future__ import annotations

import asyncio
import json
import logging
import shutil
from collections.abc import Callable
from datetime import date
from pathlib import Path

import anthropic
import xai_sdk

from shared.config import Settings, load_settings
from shared.context_loader import build_context_block, load_art_style, load_characters
from shared.models import ClipResult, VideoManifest

from .assembler import assemble_final_video, assemble_script_video
from .manifest_reader import ScriptWithShots, read_manifests
from .prompt_generator import generate_end_card_video_prompt, generate_video_prompt
from .video_generator import generate_video

logger = logging.getLogger(__name__)


async def run(
    settings: Settings | None = None,
    target_date: date | None = None,
) -> Path:
    """Run the full video designer pipeline. Returns path to final video."""
    settings = settings or load_settings()

    if not settings.xai_api_key:
        raise RuntimeError("XAI_API_KEY required for video generation")

    has_anthropic = bool(settings.anthropic_api_key)
    if not has_anthropic:
        logger.warning("ANTHROPIC_API_KEY not set — will use original scene prompts directly")

    # Clients
    anthropic_client = (
        anthropic.Anthropic(api_key=settings.anthropic_api_key) if has_anthropic else None
    )
    xai_client = xai_sdk.Client(api_key=settings.xai_api_key)

    # Load context
    characters = load_characters(settings.characters_dir)
    art_style = load_art_style(settings.art_style_path)
    context_block = build_context_block(characters, art_style)

    # Read manifests + scripts
    data = read_manifests(
        target_date=target_date,
        shots_dir=settings.shots_output_dir,
        scripts_dir=settings.scripts_output_dir,
    )
    logger.info("Processing %d scripts", len(data))

    semaphore = asyncio.Semaphore(settings.video_max_concurrency)

    # Level 1: parallel across scripts
    results = await asyncio.gather(
        *[
            _process_script(
                entry=entry,
                context_block=context_block,
                anthropic_client=anthropic_client,
                xai_client=xai_client,
                semaphore=semaphore,
                settings=settings,
            )
            for entry in data
        ]
    )

    # Filter to scripts that produced a video
    script_videos = [(manifest, path) for manifest, path in results if path is not None]

    if not script_videos:
        logger.warning("No script videos produced")
        print("No script videos were produced.")
        return settings.video_output_dir

    # Assemble final video
    date_str = data[0].script.date.isoformat()
    final_path = settings.video_output_dir / f"final_{date_str}.mp4"

    if len(script_videos) > 1:
        await asyncio.to_thread(
            assemble_final_video,
            [path for _, path in script_videos],
            final_path,
        )
    else:
        _, src = script_videos[0]
        shutil.copy2(src, final_path)

    print(f"\nDone! Final video: {final_path}")
    return final_path


async def _process_script(
    entry: ScriptWithShots,
    context_block: str,
    anthropic_client,
    xai_client,
    semaphore: asyncio.Semaphore,
    settings: Settings,
) -> tuple[VideoManifest, Path | None]:
    """Process a single script: generate clips + assemble script video."""
    output_dir = settings.video_output_dir / (f"{entry.script.date.isoformat()}_{entry.index}")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"  Script {entry.index}: {entry.script.title}")

    # Map scene_number -> shot output_path for successful shots
    shot_paths = {
        shot.scene_number: shot.output_path
        for shot in entry.manifest.shots
        if shot.success and shot.output_path
    }

    # Build tasks for each scene + end card
    tasks = []
    for scene in entry.script.scenes:
        image_path = shot_paths.get(scene.scene_number)
        if not image_path:
            logger.warning("No shot for scene %d, skipping", scene.scene_number)
            continue
        tasks.append(
            _process_clip(
                label=f"Scene {scene.scene_number}",
                scene_number=scene.scene_number,
                script_index=entry.index,
                output_path=output_dir / f"scene_{scene.scene_number}.mp4",
                image_path=Path(image_path),
                prompt_fn=lambda s=scene: generate_video_prompt(
                    s,
                    entry.script,
                    context_block,
                    anthropic_client,
                    settings.video_prompt_model,
                    settings.video_prompt_max_tokens,
                ),
                xai_client=xai_client,
                semaphore=semaphore,
                settings=settings,
            )
        )

    # End card
    end_card_path = shot_paths.get(0)
    if end_card_path:
        tasks.append(
            _process_clip(
                label="End card",
                scene_number=0,
                script_index=entry.index,
                output_path=output_dir / "end_card.mp4",
                image_path=Path(end_card_path),
                prompt_fn=lambda: generate_end_card_video_prompt(
                    entry.script,
                    context_block,
                    anthropic_client,
                    settings.video_prompt_model,
                    settings.video_prompt_max_tokens,
                ),
                xai_client=xai_client,
                semaphore=semaphore,
                settings=settings,
            )
        )

    # Level 2: parallel across scenes
    clips = list(await asyncio.gather(*tasks))

    # Assemble script video from successful clips
    successful = [c for c in clips if c.success and c.output_path]
    # Sort: scenes first (by number), end card (0) last
    successful.sort(key=lambda c: (c.scene_number == 0, c.scene_number))
    clip_paths = [Path(c.output_path) for c in successful]

    script_video_path = None
    if clip_paths:
        script_video_path = output_dir / "script_video.mp4"
        try:
            await asyncio.to_thread(assemble_script_video, clip_paths, script_video_path)
        except Exception:
            logger.exception("Failed to assemble script video for %d", entry.index)
            script_video_path = None

    manifest = VideoManifest(
        script_title=entry.script.title,
        script_index=entry.index,
        date=entry.script.date,
        clips=clips,
        script_video_path=script_video_path,
    )

    manifest_path = output_dir / "video_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return manifest, script_video_path


async def _process_clip(
    label: str,
    scene_number: int,
    script_index: int,
    output_path: Path,
    image_path: Path,
    prompt_fn: Callable[[], str],
    xai_client,
    semaphore: asyncio.Semaphore,
    settings: Settings,
) -> ClipResult:
    """Generate a single video clip (scene or end card)."""
    try:
        video_prompt = await asyncio.to_thread(prompt_fn)

        async with semaphore:
            await asyncio.to_thread(
                generate_video,
                video_prompt,
                image_path,
                output_path,
                xai_client,
                settings.video_model,
                settings.video_duration,
                settings.video_resolution,
            )

        print(f"    {label}: OK")
        return ClipResult(
            script_index=script_index,
            scene_number=scene_number,
            success=True,
            output_path=output_path,
            duration_seconds=float(settings.video_duration),
            error=None,
        )
    except Exception as e:
        logger.exception("Failed to generate %s for script %d", label, script_index)
        print(f"    {label}: FAILED ({e})")
        return ClipResult(
            script_index=script_index,
            scene_number=scene_number,
            success=False,
            output_path=None,
            duration_seconds=None,
            error=str(e),
        )
