from __future__ import annotations

import json
import logging

from shared.models import CartoonScript, SceneScript, ScoredItem
from shared.utils import call_llm_json

from ..prompts import SCRIPT_REVIEW_PROMPT, SCRIPT_REVISION_PROMPT

logger = logging.getLogger(__name__)


def review_script(
    script: CartoonScript,
    item: ScoredItem,
    context_block: str,
    client,
    model: str = "claude-opus-4-6",
    max_tokens: int = 64000,
) -> dict:
    """Evaluate a CartoonScript against comedy criteria. Returns structured feedback."""
    script_json = json.dumps(script.to_dict(), indent=2, ensure_ascii=False)
    prompt = SCRIPT_REVIEW_PROMPT.format(
        context=context_block,
        title=item.item.title,
        format_type=script.format_type or "visual_punchline",
        script_json=script_json,
    )
    return call_llm_json(client, prompt, model, max_tokens)


def revise_script(
    script: CartoonScript,
    feedback: dict,
    item: ScoredItem,
    context_block: str,
    client,
    model: str = "claude-opus-4-6",
    max_tokens: int = 64000,
) -> CartoonScript:
    """Revise a CartoonScript based on editor feedback. Returns revised CartoonScript."""
    script_json = json.dumps(script.to_dict(), indent=2, ensure_ascii=False)
    feedback_json = json.dumps(feedback, indent=2, ensure_ascii=False)
    revision_notes = feedback.get("revision_notes", "")

    prompt = SCRIPT_REVISION_PROMPT.format(
        context=context_block,
        title=item.item.title,
        format_type=script.format_type or "visual_punchline",
        original_script_json=script_json,
        feedback_json=feedback_json,
        revision_notes=revision_notes,
    )
    data = call_llm_json(client, prompt, model, max_tokens)

    scenes = [SceneScript.from_dict(s) for s in data.get("scenes", [])]
    return CartoonScript(
        title=data.get("title", script.title),
        date=script.date,
        source_item=script.source_item,
        logline=script.logline,
        synopsis=script.synopsis,
        scenes=scenes if scenes else script.scenes,
        end_card_prompt=data.get("end_card_prompt", script.end_card_prompt),
        characters_used=data.get("characters_used", script.characters_used),
        format_type=script.format_type,
    )


def review_and_revise(
    script: CartoonScript,
    item: ScoredItem,
    context_block: str,
    client,
    model: str = "claude-opus-4-6",
    max_tokens: int = 64000,
) -> CartoonScript:
    """Review then revise. Returns original on error or if review passes."""
    try:
        feedback = review_script(script, item, context_block, client, model, max_tokens)
    except Exception:
        logger.exception("Script review failed — keeping original")
        return script

    verdict = feedback.get("overall_verdict", "pass")
    if verdict == "pass":
        logger.info("Script '%s' passed review — no revision needed", script.title)
        return script

    logger.info("Script '%s' needs revision — revising", script.title)
    try:
        return revise_script(script, feedback, item, context_block, client, model, max_tokens)
    except Exception:
        logger.exception("Script revision failed — keeping original")
        return script
