from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def assemble_script_video(
    clip_paths: list[Path],
    output_path: Path,
    transition_duration: float = 0.3,
) -> Path:
    """Concatenate scene clips with short glitch interstitials.

    Generates a brief glitch clip (color noise) and inserts it between each
    scene clip using the ffmpeg concat demuxer.

    Args:
        clip_paths: Ordered list of scene MP4 paths.
        output_path: Where to save the concatenated video.
        transition_duration: Glitch interstitial duration in seconds.

    Returns:
        The output_path on success.
    """
    if not clip_paths:
        raise ValueError("assemble_script_video requires at least 1 clip")

    if len(clip_paths) == 1:
        _run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(clip_paths[0]),
                "-c",
                "copy",
                str(output_path),
            ]
        )
    else:
        _concat_with_glitch(clip_paths, output_path, transition_duration, add_beep=False)

    logger.info("Script video assembled: %s", output_path)
    return output_path


def assemble_final_video(
    script_video_paths: list[Path],
    output_path: Path,
    transition_duration: float = 1.0,
) -> Path:
    """Concatenate script videos with longer glitch interstitials + beep.

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
        _run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(script_video_paths[0]),
                "-c",
                "copy",
                str(output_path),
            ]
        )
    else:
        _concat_with_glitch(script_video_paths, output_path, transition_duration, add_beep=True)

    logger.info("Final video assembled: %s", output_path)
    return output_path


def _concat_with_glitch(
    paths: list[Path],
    output_path: Path,
    glitch_duration: float,
    add_beep: bool,
) -> None:
    """Concatenate clips with glitch interstitials using concat demuxer.

    1. Probe first clip for resolution/fps
    2. Generate a glitch clip (color noise + optional beep)
    3. Build concat file interleaving real clips with glitch clips
    4. Run ffmpeg concat demuxer
    """
    # Probe first clip for format info
    width, height, fps = _probe_video(paths[0])

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Generate glitch interstitial clip
        glitch_path = tmp / "glitch.mp4"
        _generate_glitch_clip(glitch_path, glitch_duration, width, height, fps, add_beep)

        # Build concat list file
        concat_file = tmp / "concat.txt"
        lines = []
        for i, clip in enumerate(paths):
            lines.append(f"file '{clip}'")
            if i < len(paths) - 1:
                lines.append(f"file '{glitch_path}'")
        concat_file.write_text("\n".join(lines), encoding="utf-8")

        # Run concat demuxer
        _run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-c:a",
                "aac",
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
    add_beep: bool,
) -> None:
    """Generate a short glitch interstitial clip with color noise."""
    video_src = (
        f"color=c=black:s={width}x{height}:r={fps}:d={duration},"
        f"noise=alls=80:allf=t,hue=H=random(1)*360:s=2"
    )

    if add_beep:
        audio_src = f"sine=frequency=200:duration={duration},volume=-20dB"
        _run_ffmpeg(
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
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-c:a",
                "aac",
                "-shortest",
                str(output_path),
            ]
        )
    else:
        # Silent audio track so concat demuxer doesn't complain about stream mismatch
        audio_src = f"anullsrc=r=44100:cl=stereo,atrim=0:{duration}"
        _run_ffmpeg(
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
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-c:a",
                "aac",
                "-shortest",
                str(output_path),
            ]
        )


def _probe_video(path: Path) -> tuple[int, int, float]:
    """Probe a video file for width, height, and fps. Returns defaults on failure."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,r_frame_rate",
                "-of",
                "csv=p=0",
                str(path),
            ],
            capture_output=True,
            text=True,
        )
        parts = result.stdout.strip().split(",")
        width = int(parts[0])
        height = int(parts[1])
        # r_frame_rate is like "30/1" or "24000/1001"
        num, den = parts[2].split("/")
        fps = int(num) / int(den)
        return width, height, fps
    except Exception:
        logger.warning("Failed to probe %s, using 480p 9:16 defaults", path)
        return 270, 480, 30.0


def _run_ffmpeg(cmd: list[str]) -> None:
    """Run an ffmpeg command, raising on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(
            "ffmpeg failed: %s",
            result.stderr[-500:] if result.stderr else "unknown",
        )
        raise RuntimeError(f"ffmpeg failed with exit code {result.returncode}")
