from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timezone
from pathlib import Path

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


def _call_llm(
    client,
    prompt: str,
    model: str,
    max_tokens: int,
    *,
    images: list[Path] | None = None,
):
    """Call Claude with streaming + adaptive thinking, return raw response.

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
        return stream.get_final_message()


def call_llm_json(client, prompt: str, model: str, max_tokens: int) -> dict | list:
    """Call Claude with streaming + adaptive thinking, return parsed JSON.

    Raises on API or parse failure (caller decides fallback policy).
    """
    text = strip_code_fences(extract_text(_call_llm(client, prompt, model, max_tokens)))
    return json.loads(text)


def call_llm_text(
    client,
    prompt: str,
    model: str,
    max_tokens: int,
    *,
    images: list[Path] | None = None,
) -> str:
    """Call Claude with streaming + adaptive thinking, return raw text.

    When *images* is provided, sends image blocks alongside the prompt.
    Raises on API failure (caller decides fallback policy).
    """
    return extract_text(_call_llm(client, prompt, model, max_tokens, images=images))
