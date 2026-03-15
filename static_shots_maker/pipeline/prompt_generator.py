from __future__ import annotations

import logging
import re

from shared.models import CartoonScript, SceneScript
from shared.utils import call_llm_text
from static_shots_maker.prompts import END_CARD_TO_IMAGE_PROMPT, SCENE_TO_IMAGE_PROMPT

logger = logging.getLogger(__name__)

_STRIP_AUDIO_RE = re.compile(
    r"(?:audio[:\s].*?[.\n]|sound[:\s].*?[.\n]|music[:\s].*?[.\n]|duration[:\s].*?[.\n])",
    re.IGNORECASE,
)
_STRIP_MOTION_RE = re.compile(
    r"(?:pan(?:ning|s)?\s|zoom(?:ing|s)?\s|tracking\s|dolly\s|tilt(?:ing|s)?\s)",
    re.IGNORECASE,
)


def generate_scene_prompt(
    scene: SceneScript,
    script: CartoonScript,
    context_block: str,
    client,
    model: str,
    max_tokens: int,
) -> str:
    """Rewrite a video scene prompt into an optimized image generation prompt."""
    prompt = SCENE_TO_IMAGE_PROMPT.format(
        context=context_block,
        title=script.title,
        scene_number=scene.scene_number,
        scene_title=scene.scene_title,
        setting=scene.setting,
        scene_prompt=scene.scene_prompt,
        visual_gag=scene.visual_gag or "None",
        camera_movement=scene.camera_movement,
    )
    try:
        return call_llm_text(client, prompt, model, max_tokens).strip()
    except Exception:
        logger.exception(
            "Claude prompt rewrite failed for scene %d, using fallback",
            scene.scene_number,
        )
        return _fallback_strip(scene.scene_prompt)


def generate_end_card_prompt(
    script: CartoonScript,
    context_block: str,
    client,
    model: str,
    max_tokens: int,
) -> str:
    """Rewrite an end-card prompt into an optimized image generation prompt."""
    prompt = END_CARD_TO_IMAGE_PROMPT.format(
        context=context_block,
        title=script.title,
        end_card_prompt=script.end_card_prompt,
    )
    try:
        return call_llm_text(client, prompt, model, max_tokens).strip()
    except Exception:
        logger.exception("Claude prompt rewrite failed for end card, using fallback")
        return _fallback_strip(script.end_card_prompt)


def _fallback_strip(prompt: str) -> str:
    """Strip audio/duration/motion references from an original prompt via regex."""
    text = _STRIP_AUDIO_RE.sub("", prompt)
    text = _STRIP_MOTION_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()
