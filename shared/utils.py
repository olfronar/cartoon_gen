from __future__ import annotations

import re
from datetime import datetime, timezone

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def strip_code_fences(text: str) -> str:
    """Strip markdown code fences (```json ... ```) from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0].strip()
    return text


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


def call_llm_json(client, prompt: str, model: str, max_tokens: int) -> dict | list:
    """Call Claude with streaming + adaptive thinking, return parsed JSON.

    Raises on API or parse failure (caller decides fallback policy).
    """
    import json

    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        temperature=1,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        response = stream.get_final_message()

    text = strip_code_fences(extract_text(response))
    return json.loads(text)
