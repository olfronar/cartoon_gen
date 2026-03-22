from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from shared.ffmpeg import probe_video, run_ffmpeg

logger = logging.getLogger(__name__)

_ENCODE_ARGS = ["-c:v", "libx264", "-preset", "fast", "-c:a", "aac"]


def assemble_script_video(
    clip_paths: list[Path],
    output_path: Path,
) -> Path:
    """Concatenate scene clips with re-encoding for audio normalization.

    Re-encodes with libx264 + aac to normalize audio streams from Veo clips
    (which may have varying audio formats/sample rates).

    Args:
        clip_paths: Ordered list of scene MP4 paths.
        output_path: Where to save the concatenated video.

    Returns:
        The output_path on success.
    """
    if not clip_paths:
        raise ValueError("assemble_script_video requires at least 1 clip")

    _concat_clips(clip_paths, output_path)
    logger.info("Script video assembled: %s", output_path)
    return output_path


def assemble_final_video(
    script_video_paths: list[Path],
    output_path: Path,
    transition_duration: float = 0.5,
) -> Path:
    """Concatenate script videos with glitch interstitials + silence.

    Args:
        script_video_paths: Ordered list of script video MP4 paths.
        output_path: Where to save the final cartoon.
        transition_duration: Glitch interstitial duration in seconds.

    Returns:
        The output_path on success.
    """
    if not script_video_paths:
        raise ValueError("assemble_final_video requires at least 1 script video")

    if len(script_video_paths) == 1:
        _concat_clips(script_video_paths, output_path)
    else:
        _concat_with_glitch(script_video_paths, output_path, transition_duration)

    logger.info("Final video assembled: %s", output_path)
    return output_path


def _concat_clips(paths: list[Path], output_path: Path) -> None:
    """Concatenate clips with re-encoding for audio normalization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        concat_file = Path(tmpdir) / "concat.txt"
        lines = [f"file '{clip.resolve()}'" for clip in paths]
        concat_file.write_text("\n".join(lines), encoding="utf-8")

        run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                *_ENCODE_ARGS,
                "-movflags",
                "+faststart",
                str(output_path),
            ]
        )


def _concat_with_glitch(
    paths: list[Path],
    output_path: Path,
    glitch_duration: float,
) -> None:
    """Concatenate clips with glitch + silence interstitials using concat demuxer."""
    width, height, fps = probe_video(paths[0])

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        glitch_path = tmp / "glitch.mp4"
        _generate_glitch_clip(glitch_path, glitch_duration, width, height, fps)

        concat_file = tmp / "concat.txt"
        lines = []
        for i, clip in enumerate(paths):
            lines.append(f"file '{clip.resolve()}'")
            if i < len(paths) - 1:
                lines.append(f"file '{glitch_path.resolve()}'")
        concat_file.write_text("\n".join(lines), encoding="utf-8")

        run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                *_ENCODE_ARGS,
                "-movflags",
                "+faststart",
                str(output_path),
            ]
        )


def _generate_glitch_clip(
    output_path: Path,
    duration: float,
    width: int,
    height: int,
    fps: float,
) -> None:
    """Generate a short glitch clip with color noise + silence."""
    video_src = (
        f"color=c=black:s={width}x{height}:r={fps}:d={duration},"
        f"noise=alls=80:allf=t,hue=H=random(1)*360:s=2"
    )
    audio_src = f"anullsrc=r=44100:cl=stereo,atrim=duration={duration}"

    run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            video_src,
            "-f",
            "lavfi",
            "-i",
            audio_src,
            *_ENCODE_ARGS,
            "-shortest",
            str(output_path),
        ]
    )
