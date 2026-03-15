from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def assemble_script_video(
    clip_paths: list[Path],
    output_path: Path,
    transition_duration: float = 0.3,
    clip_duration: float = 15.0,
) -> Path:
    """Concatenate scene clips with short glitch transitions.

    Uses ffmpeg xfade filter with hlslice for glitch effect.
    For a single clip, copies without transition.

    Args:
        clip_paths: Ordered list of scene MP4 paths.
        output_path: Where to save the concatenated video.
        transition_duration: Glitch transition duration in seconds.
        clip_duration: Duration of each clip in seconds (for offset calculation).

    Returns:
        The output_path on success.
    """
    if not clip_paths:
        raise ValueError("assemble_script_video requires at least 1 clip")

    cmd = _build_copy_or_concat_cmd(
        clip_paths, output_path, transition_duration, clip_duration, audio=False
    )
    _run_ffmpeg(cmd)
    logger.info("Script video assembled: %s", output_path)
    return output_path


def assemble_final_video(
    script_video_paths: list[Path],
    output_path: Path,
    transition_duration: float = 1.0,
    clip_duration: float = 0.0,
) -> Path:
    """Concatenate script videos with longer glitch transitions + audio concat.

    Uses ffmpeg with xfade glitch transitions.

    Args:
        script_video_paths: Ordered list of script video MP4 paths.
        output_path: Where to save the final cartoon.
        transition_duration: Glitch transition duration in seconds.
        clip_duration: Duration of each script video (0 = auto-estimate).

    Returns:
        The output_path on success.
    """
    if not script_video_paths:
        raise ValueError("assemble_final_video requires at least 1 script video")

    cmd = _build_copy_or_concat_cmd(
        script_video_paths, output_path, transition_duration, clip_duration, audio=True
    )
    _run_ffmpeg(cmd)
    logger.info("Final video assembled: %s", output_path)
    return output_path


def _build_copy_or_concat_cmd(
    paths: list[Path],
    output_path: Path,
    transition_duration: float,
    clip_duration: float,
    audio: bool,
) -> list[str]:
    """Build ffmpeg command: copy for single input, xfade concat for multiple."""
    if len(paths) == 1:
        return [
            "ffmpeg",
            "-y",
            "-i",
            str(paths[0]),
            "-c",
            "copy",
            str(output_path),
        ]

    return _build_xfade_concat_cmd(paths, output_path, transition_duration, clip_duration, audio)


def _build_xfade_concat_cmd(
    paths: list[Path],
    output_path: Path,
    transition_duration: float,
    clip_duration: float,
    audio: bool,
) -> list[str]:
    """Build ffmpeg command with xfade glitch transitions."""
    cmd: list[str] = ["ffmpeg", "-y"]
    for p in paths:
        cmd.extend(["-i", str(p)])

    # Build xfade filter chain with proper offsets
    vfilters = _build_xfade_chain(len(paths), transition_duration, clip_duration)

    if audio:
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
    else:
        cmd.extend(
            [
                "-filter_complex",
                ";".join(vfilters),
                "-map",
                "[vout]",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                str(output_path),
            ]
        )

    return cmd


def _build_xfade_chain(count: int, transition_duration: float, clip_duration: float) -> list[str]:
    """Build the video xfade filter chain with computed offsets."""
    filters = []
    prev = "[0:v]"
    cumulative = clip_duration  # offset starts at first clip's duration
    for i in range(1, count):
        out = f"[v{i}]" if i < count - 1 else "[vout]"
        offset = max(0, cumulative - transition_duration)
        filters.append(
            f"{prev}[{i}:v]xfade=transition=hlslice:"
            f"duration={transition_duration}:offset={offset}{out}"
        )
        prev = out
        cumulative += clip_duration - transition_duration
    return filters


def _run_ffmpeg(cmd: list[str]) -> None:
    """Run an ffmpeg command, raising on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(
            "ffmpeg failed: %s",
            result.stderr[:500] if result.stderr else "unknown",
        )
        raise RuntimeError(f"ffmpeg failed with exit code {result.returncode}")
