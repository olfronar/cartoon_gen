from __future__ import annotations

import logging
import re

from shared.models import CartoonScript, SceneScript
from shared.utils import call_llm_json, call_llm_text
from static_shots_maker.prompts import (
    COMEDY_REWRITE_PROMPT,
    IMAGE_COMEDY_CHECK_PROMPT,
    SCENE_TO_IMAGE_PROMPT,
)

logger = logging.getLogger(__name__)

_STRIP_AUDIO_RE = re.compile(
    r"(?:audio[:\s].*?[.\n]|sound[:\s].*?[.\n]|music[:\s].*?[.\n]|duration[:\s].*?[.\n])",
    re.IGNORECASE,
)
_STRIP_MOTION_RE = re.compile(
    r"(?:pan(?:ning|s)?\s|zoom(?:ing|s)?\s|tracking\s|dolly\s|tilt(?:ing|s)?\s)",
    re.IGNORECASE,
)
_STRIP_DIALOGUE_RE = re.compile(
    r"\b\w+ says:\s*['\"].+?['\"]\.?",
    re.IGNORECASE,
)


def generate_scene_prompt(
    scene: SceneScript,
    script: CartoonScript,
    context_block: str,
    client,
    model: str,
    max_tokens: int,
    comedy_check: bool = True,
) -> str:
    """Rewrite a video scene prompt into an optimized image generation prompt.

    If comedy_check is True, verifies the rewritten prompt is independently funny
    using a fast Sonnet call. If it fails, applies the suggested revision once.
    """
    prompt = SCENE_TO_IMAGE_PROMPT.format(
        context=context_block,
        title=script.title,
        scene_number=scene.scene_number,
        scene_title=scene.scene_title,
        setting=scene.setting,
        scene_prompt=scene.scene_prompt,
        visual_gag=scene.visual_gag or "None",
        camera_movement=scene.camera_movement,
        format_type=script.format_type or "demonstration",
    )
    try:
        image_prompt = call_llm_text(client, prompt, model, max_tokens).strip()
    except Exception:
        logger.exception(
            "Claude prompt rewrite failed for scene %d, using fallback",
            scene.scene_number,
        )
        return _fallback_strip(scene.scene_prompt)

    if comedy_check:
        image_prompt = _check_comedy(image_prompt, scene, script, client)

    return image_prompt


_COMEDY_CHECK_MAX_TOKENS = 4096


_COMEDY_REWRITE_MAX_TOKENS = 1024


def _check_comedy(
    image_prompt: str,
    scene: SceneScript,
    script: CartoonScript,
    client,
) -> str:
    """Check if an image prompt is independently funny. Rewrite once if not. Fail-open."""
    try:
        check_prompt = IMAGE_COMEDY_CHECK_PROMPT.format(
            title=script.title,
            scene_prompt=scene.scene_prompt,
            visual_gag=scene.visual_gag or "None",
            image_prompt=image_prompt,
        )
        # Use Sonnet with a small token budget for fast, cheap evaluation
        data = call_llm_json(client, check_prompt, "claude-sonnet-4-6", _COMEDY_CHECK_MAX_TOKENS)
        if not isinstance(data, dict):
            return image_prompt
        if not data.get("revision_needed", False):
            logger.info("Image comedy check passed for scene %d", scene.scene_number)
            return image_prompt
        suggestion = data.get("suggested_revision", "")
        if not suggestion:
            return image_prompt
        # Rewrite the full prompt incorporating the comedy suggestion
        rewrite_prompt = COMEDY_REWRITE_PROMPT.format(
            image_prompt=image_prompt,
            suggestion=suggestion,
        )
        revised = call_llm_text(
            client, rewrite_prompt, "claude-sonnet-4-6", _COMEDY_REWRITE_MAX_TOKENS
        ).strip()
        logger.info("Image comedy check: rewrote prompt for scene %d", scene.scene_number)
        return revised
    except Exception:
        logger.exception("Image comedy check failed — keeping original prompt")
        return image_prompt


def _fallback_strip(prompt: str) -> str:
    """Strip audio/duration/motion/dialogue references from an original prompt via regex."""
    text = _STRIP_AUDIO_RE.sub("", prompt)
    text = _STRIP_MOTION_RE.sub("", text)
    text = _STRIP_DIALOGUE_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()
