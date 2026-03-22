from __future__ import annotations

import asyncio
import logging
from datetime import date
from pathlib import Path

from shared.config import Settings, load_settings
from shared.ffmpeg import probe_video

from .filter_generator import generate_drawtext_filter, write_filter_script
from .subtitle_burner import burn_subtitles
from .transcriber import transcribe
from .video_finder import find_script_videos

logger = logging.getLogger(__name__)


async def run(
    settings: Settings | None = None,
    target_date: date | None = None,
) -> Path:
    """Run the full caption maker pipeline. Returns path to final captioned video."""
    settings = settings or load_settings()

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY required for whisper transcription")

    font_path = settings.caption_font_path
    if not font_path.is_file():
        raise FileNotFoundError(
            f"Caption font not found: {font_path}. Ensure assets/fonts/Inter-Bold.ttf exists."
        )

    videos = find_script_videos(target_date, settings.video_output_dir)
    logger.info("Captioning %d script videos", len(videos))

    results = await asyncio.gather(
        *[_process_video(index, video_path, font_path, settings) for index, video_path in videos]
    )

    # Collect successful captioned paths, sorted by index
    captioned: list[tuple[int, Path]] = [(idx, path) for idx, path in results if path is not None]
    captioned.sort(key=lambda x: x[0])

    if not captioned:
        logger.warning("No videos were captioned")
        print("No videos were captioned.")
        return settings.video_output_dir

    # Assemble final captioned video
    from video_designer.pipeline.assembler import assemble_final_video

    date_str = videos[0][1].parent.name.rsplit("_", 1)[0]
    final_path = settings.video_output_dir / f"final_{date_str}_captioned.mp4"

    await asyncio.to_thread(
        assemble_final_video,
        [path for _, path in captioned],
        final_path,
    )

    print(f"\nDone! Captioned video: {final_path}")
    return final_path


async def _process_video(
    index: int,
    video_path: Path,
    font_path: Path,
    settings: Settings,
) -> tuple[int, Path | None]:
    """Transcribe, generate subtitles, and burn into a single video."""
    try:
        print(f"  Script {index}: Transcribing...")
        transcription = await asyncio.to_thread(
            transcribe, video_path, settings.openai_api_key, settings.whisper_model
        )

        if not transcription.segments:
            logger.warning("Script %d: No speech detected, skipping captions", index)
            print(f"  Script {index}: No speech detected, skipping")
            return index, None

        _width, height, _fps = probe_video(video_path)

        filter_content = generate_drawtext_filter(transcription, height, font_path)
        filter_path = video_path.parent / "captions_filter.txt"
        write_filter_script(filter_content, filter_path)

        output_path = video_path.parent / "script_video_captioned.mp4"
        print(f"  Script {index}: Burning subtitles...")
        await asyncio.to_thread(burn_subtitles, video_path, filter_path, output_path)

        print(f"  Script {index}: Done")
        return index, output_path
    except Exception:
        logger.exception("Failed to caption script %d", index)
        print(f"  Script {index}: FAILED")
        return index, None
