from __future__ import annotations

import json
import logging

from shared.models import CartoonScript, SceneScript, ScoredItem
from shared.utils import call_llm_json

from ..prompts import COMEDY_PUNCHUP_PROMPT, SCRIPT_REVIEW_PROMPT, SCRIPT_REVISION_PROMPT

logger = logging.getLogger(__name__)


def punchup_script(
    script: CartoonScript,
    item: ScoredItem,
    context_block: str,
    client,
    model: str = "claude-opus-4-6",
    max_tokens: int = 64000,
) -> CartoonScript:
    """Comedy punch-up pass: generate funnier alternatives for key elements.

    Returns a modified CartoonScript with punch-up suggestions applied,
    or the original script on error.
    """
    if not script.scenes:
        return script

    scene = script.scenes[0]
    # Get last dialogue line for the prompt
    last_line = ""
    if scene.dialogue:
        entry = scene.dialogue[-1]
        last_line = entry.get("line", "") if isinstance(entry, dict) else ""

    script_json = json.dumps(script.to_dict(), indent=2, ensure_ascii=False)
    prompt = COMEDY_PUNCHUP_PROMPT.format(
        context=context_block,
        title=item.item.title,
        format_type=script.format_type or "visual_punchline",
        script_json=script_json,
        last_line=last_line,
        visual_gag=scene.visual_gag,
    )

    try:
        data = call_llm_json(client, prompt, model, max_tokens)
    except Exception:
        logger.exception("Comedy punch-up failed — keeping original")
        return script

    # Apply punch-up suggestions
    modified = False

    # 1. Replace last line if suggested
    last_line_data = data.get("last_line", {}) if isinstance(data, dict) else {}
    if isinstance(last_line_data, dict) and last_line_data.get("action") == "replace":
        new_line = last_line_data.get("new_line", "")
        if new_line and scene.dialogue:
            scene.dialogue[-1] = {**scene.dialogue[-1], "line": new_line}
            modified = True
            logger.info("Punch-up: replaced last line")

    # 2. Replace visual_gag if suggested
    gag_data = data.get("visual_gag", {}) if isinstance(data, dict) else {}
    if isinstance(gag_data, dict) and gag_data.get("action") == "replace":
        new_gag = gag_data.get("new_gag", "")
        if new_gag:
            scene.visual_gag = new_gag
            modified = True
            logger.info("Punch-up: replaced visual gag")

    # 3. Add background detail to scene_prompt if suggested
    detail_data = data.get("background_detail", {}) if isinstance(data, dict) else {}
    if isinstance(detail_data, dict) and detail_data.get("action") == "add":
        detail = detail_data.get("detail", "")
        if detail and scene.scene_prompt:
            scene.scene_prompt = f"{scene.scene_prompt.rstrip('.')}. {detail}"
            modified = True
            logger.info("Punch-up: added background detail")

    # 4. Revise scene_prompt for comedy if suggested
    comedy_data = data.get("scene_prompt_comedy", {}) if isinstance(data, dict) else {}
    if isinstance(comedy_data, dict) and comedy_data.get("action") == "revise":
        suggestion = comedy_data.get("suggestion", "")
        if suggestion and scene.scene_prompt:
            # Append the comedy suggestion rather than replacing (preserves existing content)
            scene.scene_prompt = f"{scene.scene_prompt.rstrip('.')}. {suggestion}"
            modified = True
            logger.info("Punch-up: revised scene_prompt for comedy")

    if modified:
        logger.info("Punch-up applied changes to '%s'", script.title)
    else:
        logger.info("Punch-up: no changes needed for '%s'", script.title)

    return script


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
