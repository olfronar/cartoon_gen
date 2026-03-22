from __future__ import annotations

from pathlib import Path

from .transcriber import Transcription

MAX_WORDS_PER_CHUNK = 3
MIN_DURATION = 0.08  # seconds — floor for zero-duration timing gaps


def _escape_drawtext_text(text: str) -> str:
    """Escape text for unquoted drawtext text= value.

    ASCII apostrophe (') is replaced with Unicode right single quote (U+2019)
    which renders identically but doesn't trigger ffmpeg's quote parser.
    Filter-graph special chars are backslash-escaped.
    """
    text = text.replace("'", "\u2019")
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace(",", "\\,")
    text = text.replace(";", "\\;")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    return text


def _escape_path(path: str) -> str:
    """Escape a file path for single-quoted filter value (no apostrophes in paths)."""
    return path.replace("\\", "\\\\")


def generate_drawtext_filter(
    transcription: Transcription,
    video_height: int,
    font_path: Path,
) -> str:
    """Generate a drawtext filter chain for cumulative word reveal.

    Words are grouped into chunks of MAX_WORDS_PER_CHUNK. Within each chunk,
    words appear one by one (cumulative). When a chunk fills, the next chunk
    starts fresh. This prevents text from overflowing the screen.

    Returns empty string if transcription has no segments.
    """
    if not transcription.segments:
        return ""

    font_size = int(video_height * 48 / 1280)
    font_abs = _escape_path(str(font_path.resolve()))

    filters: list[str] = []
    for seg in transcription.segments:
        words = seg.words
        for chunk_start in range(0, len(words), MAX_WORDS_PER_CHUNK):
            chunk_end = min(chunk_start + MAX_WORDS_PER_CHUNK, len(words))
            chunk = words[chunk_start:chunk_end]

            for i in range(len(chunk)):
                cumulative = " ".join(w.word for w in chunk[: i + 1])
                text_escaped = _escape_drawtext_text(cumulative)

                start = chunk[i].start
                if i + 1 < len(chunk):
                    end = chunk[i + 1].start
                elif chunk_end < len(words):
                    end = words[chunk_end].start
                else:
                    end = seg.end

                if end - start < MIN_DURATION:
                    end = start + MIN_DURATION

                # text= unquoted (apostrophes safe), enable= quoted (commas)
                filters.append(
                    f"drawtext=fontfile='{font_abs}'"
                    f":text={text_escaped}"
                    f":fontsize={font_size}"
                    f":fontcolor=white"
                    f":borderw=3:bordercolor=black"
                    f":shadowx=1:shadowy=1:shadowcolor=black@0.5"
                    f":x=(w-text_w)/2:y=h-th-h*0.05"
                    f":enable='between(t,{start:.3f},{end:.3f})'"
                )

    return ",".join(filters)


def write_filter_script(content: str, output_path: Path) -> Path:
    """Write filter script to file for ffmpeg -filter_script:v."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path
