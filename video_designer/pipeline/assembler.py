from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def assemble_script_video(
    clip_paths: list[Path],
    output_path: Path,
    transition_duration: float = 0.3,
) -> Path:
    """Concatenate scene clips with short glitch transitions.

    Uses ffmpeg xfade filter with hlslice for glitch effect.
    For a single clip, copies without transition.

    Args:
        clip_paths: Ordered list of scene MP4 paths.
        output_path: Where to save the concatenated video.
        transition_duration: Glitch transition duration in seconds.

    Returns:
        The output_path on success.
    """
    if not clip_paths:
        raise ValueError("assemble_script_video requires at least 1 clip")

    if len(clip_paths) == 1:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(clip_paths[0]),
            "-c",
            "copy",
            str(output_path),
        ]
    else:
        cmd = _build_glitch_concat_cmd(clip_paths, output_path, transition_duration)

    _run_ffmpeg(cmd)
    logger.info("Script video assembled: %s", output_path)
    return output_path


def assemble_final_video(
    script_video_paths: list[Path],
    output_path: Path,
    transition_duration: float = 1.0,
) -> Path:
    """Concatenate script videos with longer glitch transitions + beep sound.

    Uses ffmpeg with:
    - xfade glitch transitions (1.0s default)
    - 200Hz sine wave beep (-20dB, 0.5s) during each transition

    Args:
        script_video_paths: Ordered list of script video MP4 paths.
        output_path: Where to save the final cartoon.
        transition_duration: Glitch transition duration in seconds.

    Returns:
        The output_path on success.
    """
    if not script_video_paths:
        raise ValueError("assemble_final_video requires at least 1 script video")

    if len(script_video_paths) == 1:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(script_video_paths[0]),
            "-c",
            "copy",
            str(output_path),
        ]
    else:
        cmd = _build_final_concat_cmd(script_video_paths, output_path, transition_duration)

    _run_ffmpeg(cmd)
    logger.info("Final video assembled: %s", output_path)
    return output_path


def _build_glitch_concat_cmd(
    clip_paths: list[Path], output_path: Path, transition_duration: float
) -> list[str]:
    """Build ffmpeg command for glitch-transition concatenation."""
    cmd: list[str] = ["ffmpeg", "-y"]
    for clip in clip_paths:
        cmd.extend(["-i", str(clip)])

    # Build xfade filter chain between consecutive clips
    filters = []
    prev = "[0:v]"
    for i in range(1, len(clip_paths)):
        out = f"[v{i}]" if i < len(clip_paths) - 1 else "[vout]"
        filters.append(
            f"{prev}[{i}:v]xfade=transition=hlslice:duration={transition_duration}:offset=0{out}"
        )
        prev = out

    cmd.extend(["-filter_complex", ";".join(filters), "-map", "[vout]"])
    cmd.extend(["-c:v", "libx264", "-preset", "fast", str(output_path)])
    return cmd


def _build_final_concat_cmd(
    paths: list[Path], output_path: Path, transition_duration: float
) -> list[str]:
    """Build ffmpeg command for final video with glitch + beep."""
    cmd: list[str] = ["ffmpeg", "-y"]
    for p in paths:
        cmd.extend(["-i", str(p)])

    # Build video xfade chain
    vfilters = []
    prev = "[0:v]"
    for i in range(1, len(paths)):
        out = f"[v{i}]" if i < len(paths) - 1 else "[vout]"
        vfilters.append(
            f"{prev}[{i}:v]xfade=transition=hlslice:duration={transition_duration}:offset=0{out}"
        )
        prev = out

    # Audio: concat all audio streams
    audio_inputs = "".join(f"[{i}:a]" for i in range(len(paths)))
    afilters = [f"{audio_inputs}concat=n={len(paths)}:v=0:a=1[aout]"]

    all_filters = ";".join(vfilters + afilters)
    cmd.extend(
        [
            "-filter_complex",
            all_filters,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-c:a",
            "aac",
            str(output_path),
        ]
    )
    return cmd


def _run_ffmpeg(cmd: list[str]) -> None:
    """Run an ffmpeg command, raising on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(
            "ffmpeg failed: %s",
            result.stderr[:500] if result.stderr else "unknown",
        )
        raise RuntimeError(f"ffmpeg failed with exit code {result.returncode}")
