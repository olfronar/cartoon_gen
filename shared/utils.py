from __future__ import annotations

import base64
import json
import logging
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def strip_code_fences(text: str) -> str:
    """Strip markdown code fences (```json ... ```) from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0].strip()
    return text


def extract_json(text: str, *, expect: type = dict):
    """Parse JSON from LLM text, falling back to bracket extraction.

    Tries ``json.loads`` on the full text first.  On failure, locates the
    outermost ``{…}`` (for *expect=dict*) or ``[…]`` (for *expect=list*)
    and parses that substring.

    Returns the parsed object or raises ``ValueError`` on failure.
    """
    text = text.strip()
    try:
        result = json.loads(text)
        if isinstance(result, expect):
            return result
    except json.JSONDecodeError:
        pass

    open_br, close_br = ("{", "}") if expect is dict else ("[", "]")
    start = text.find(open_br)
    end = text.rfind(close_br)
    if start != -1 and end > start:
        try:
            result = json.loads(text[start : end + 1])
            if isinstance(result, expect):
                return result
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract {expect.__name__} JSON from text:\n{text[:500]}")


def parse_iso_utc(value: str) -> datetime:
    """Parse an ISO 8601 timestamp, handling 'Z' suffix. Returns UTC datetime."""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc)


def strip_html(text: str) -> str:
    """Strip HTML tags from text."""
    return _HTML_TAG_RE.sub("", text)


def extract_text(response) -> str:
    """Extract concatenated text from an Anthropic response's content blocks."""
    return "".join(block.text for block in response.content if block.type == "text")


def detect_image_media_type(data: bytes) -> str:
    """Detect image media type from file magic bytes."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:2] == b"\xff\xd8":
        return "image/jpeg"
    if data[:4] == b"GIF8":
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    raise ValueError(f"Unrecognized image format (first 12 bytes: {data[:12]!r})")


OUTPUT_INDEX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_(\d+)$")


def find_latest_output_date(directory: Path) -> date:
    """Find the most recent date by scanning subdirectory names matching YYYY-MM-DD_N."""
    dates: set[str] = set()
    for path in directory.iterdir():
        if path.is_dir() and OUTPUT_INDEX_RE.match(path.name):
            dates.add(path.name.rsplit("_", 1)[0])
    if not dates:
        raise FileNotFoundError(f"No output directories found in {directory}")
    return date.fromisoformat(max(dates))


def find_script_videos(
    target_date: date | None,
    video_dir: Path,
    prefer_captioned: bool = False,
) -> list[tuple[int, Path]]:
    """Find script video files for a date. Returns (index, path) sorted by index."""
    video_dir = video_dir or Path("output/videos")
    if target_date is None:
        target_date = find_latest_output_date(video_dir)
    date_str = target_date.isoformat()
    results: list[tuple[int, Path]] = []
    for subdir in sorted(video_dir.glob(f"{date_str}_*")):
        if not subdir.is_dir():
            continue
        match = OUTPUT_INDEX_RE.match(subdir.name)
        if not match:
            continue
        if prefer_captioned:
            captioned = subdir / "script_video_captioned.mp4"
            raw = subdir / "script_video.mp4"
            if captioned.is_file():
                results.append((int(match.group(1)), captioned))
            elif raw.is_file():
                results.append((int(match.group(1)), raw))
        else:
            video_path = subdir / "script_video.mp4"
            if video_path.is_file():
                results.append((int(match.group(1)), video_path))
    if not results:
        raise FileNotFoundError(f"No script videos found for {date_str} in {video_dir}")
    logger.info("Found %d script videos for %s", len(results), date_str)
    return results


def parse_feed_timestamp(entry) -> datetime:
    """Parse a feedparser entry's timestamp. Falls back to now(UTC)."""
    from time import mktime

    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field) if isinstance(entry, dict) else getattr(entry, field, None)
        if parsed and isinstance(parsed, (tuple, time.struct_time)):
            try:
                return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
            except (ValueError, OverflowError):
                pass
    return datetime.now(timezone.utc)


def _call_anthropic(
    client,
    prompt: str,
    model: str,
    max_tokens: int,
    *,
    images: list[Path] | None = None,
) -> str:
    """Call Claude with streaming + adaptive thinking, return raw text.

    When *images* is provided, sends a multimodal message with image blocks
    before the text prompt.  Raises on API failure (caller decides fallback).
    """
    if images:
        content: list[dict] | str = []
        for img_path in images:
            raw = img_path.read_bytes()
            media_type = detect_image_media_type(raw)
            b64 = base64.b64encode(raw).decode("ascii")
            content.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": b64},
                }
            )
        content.append({"type": "text", "text": prompt})
    else:
        content = prompt

    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        temperature=1,
        messages=[{"role": "user", "content": content}],
    ) as stream:
        return extract_text(stream.get_final_message())


def _call_xai(client, prompt: str, model: str, max_tokens: int) -> str:
    """Call xAI Grok with reasoning, return raw text.

    Uses xai_sdk.Client synchronously.  Raises on API failure.
    """
    from xai_sdk.chat import user

    chat = client.chat.create(model=model, max_tokens=max_tokens)
    chat.append(user(prompt))
    response = chat.sample()
    return response.content


def _call_llm(
    client,
    prompt: str,
    model: str,
    max_tokens: int,
    *,
    images: list[Path] | None = None,
) -> str:
    """Dispatch to Anthropic or xAI based on model name. Returns raw text."""
    if model.startswith("grok"):
        return _call_xai(client, prompt, model, max_tokens)
    return _call_anthropic(client, prompt, model, max_tokens, images=images)


def call_llm_json(
    client,
    prompt: str,
    model: str,
    max_tokens: int,
    *,
    images: list[Path] | None = None,
) -> dict | list:
    """Call LLM with adaptive thinking, return parsed JSON.

    Dispatches to Anthropic or xAI based on model name.
    When *images* is provided, sends image blocks alongside the prompt (Anthropic only).
    Raises on API or parse failure (caller decides fallback policy).
    """
    text = strip_code_fences(_call_llm(client, prompt, model, max_tokens, images=images))
    text = text.strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        for expect in (dict, list):
            try:
                return extract_json(text, expect=expect)
            except ValueError:
                continue
        raise ValueError(f"Could not parse JSON from LLM response:\n{text[:500]}") from None


def call_llm_text(
    client,
    prompt: str,
    model: str,
    max_tokens: int,
    *,
    images: list[Path] | None = None,
) -> str:
    """Call LLM with adaptive thinking, return raw text.

    Dispatches to Anthropic or xAI based on model name.
    When *images* is provided, sends image blocks alongside the prompt (Anthropic only).
    Raises on API failure (caller decides fallback policy).
    """
    return _call_llm(client, prompt, model, max_tokens, images=images)
