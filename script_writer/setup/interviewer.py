from __future__ import annotations

import json
import logging

import anthropic

from shared.utils import strip_code_fences

logger = logging.getLogger(__name__)

INTERVIEW_COMPLETE_MARKER = "INTERVIEW_COMPLETE"


def run_interview(
    api_key: str,
    system_prompt: str,
    model: str = "claude-opus-4-6",
    initial_context: str = "",
) -> dict:
    """Run a multi-turn interview via Claude, collecting user input from stdin.

    Returns the parsed JSON profile when the LLM signals INTERVIEW_COMPLETE.
    """
    client = anthropic.Anthropic(api_key=api_key)
    messages: list[dict] = []

    # Seed with any initial context (e.g. existing characters)
    first_user_msg = "Let's begin."
    if initial_context:
        first_user_msg = (
            f"Here's context about the show so far:\n\n{initial_context}\n\nLet's begin."
        )

    messages.append({"role": "user", "content": first_user_msg})

    while True:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
        )

        assistant_text = ""
        for block in response.content:
            if block.type == "text":
                assistant_text += block.text

        messages.append({"role": "assistant", "content": assistant_text})

        # Check if interview is complete
        if INTERVIEW_COMPLETE_MARKER in assistant_text:
            # Show the part before the marker
            parts = assistant_text.split(INTERVIEW_COMPLETE_MARKER, 1)
            if parts[0].strip():
                print(f"\n{parts[0].strip()}\n")
            print("\nInterview complete! Generating profile...\n")
            return _extract_profile(parts[1])

        # Show assistant's question and get user's answer
        print(f"\n{assistant_text}\n")
        user_input = input("> ").strip()

        if not user_input:
            user_input = "(no answer)"

        messages.append({"role": "user", "content": user_input})


def _extract_profile(text: str) -> dict:
    """Extract JSON profile from text after INTERVIEW_COMPLETE marker."""
    text = strip_code_fences(text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        # Try to find JSON in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        raise ValueError(
            f"Could not parse profile JSON from interview output:\n{text[:500]}"
        ) from exc
