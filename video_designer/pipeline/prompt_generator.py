from __future__ import annotations

import logging
from pathlib import Path

from shared.models import CartoonScript, SceneScript
from shared.utils import call_llm_text
from video_designer.prompts import END_CARD_TO_VIDEO_PROMPT, SCENE_TO_VIDEO_PROMPT

logger = logging.getLogger(__name__)


def _format_dialogue(dialogue: list[dict]) -> str:
    """Format dialogue list into prompt-friendly text."""
    if not dialogue:
        return "None"
    lines = []
    for d in dialogue:
        char = d.get("character", "Unknown")
        line = d.get("line", "")
        lines.append(f'[{char}] says: "{line}"')
    return " ".join(lines)


def generate_video_prompt(
    scene: SceneScript,
    script: CartoonScript,
    context_block: str,
    client,
    model: str,
    max_tokens: int,
    image_path: Path | None = None,
) -> str:
    """Compose a video generation prompt for a scene.

    When *image_path* is provided, the static shot is sent alongside the
    text prompt so Claude can reference the actual rendered frame.
    """
    prompt = SCENE_TO_VIDEO_PROMPT.format(
        context=context_block,
        title=script.title,
        scene_number=scene.scene_number,
        scene_title=scene.scene_title,
        setting=scene.setting,
        scene_prompt=scene.scene_prompt,
        camera_movement=scene.camera_movement,
        visual_gag=scene.visual_gag or "None",
        audio_direction=scene.audio_direction,
        duration_seconds=scene.duration_seconds,
        dialogue_formatted=_format_dialogue(scene.dialogue),
        transformation=scene.transformation or "None",
        format_type=script.format_type or "demonstration",
        billy_emotion=scene.billy_emotion or "deadpan",
    )
    images = [image_path] if image_path else None
    try:
        return call_llm_text(client, prompt, model, max_tokens, images=images).strip()
    except Exception:
        logger.exception(
            "Claude video prompt failed for scene %d, using original scene_prompt",
            scene.scene_number,
        )
        return scene.scene_prompt


def generate_end_card_video_prompt(
    script: CartoonScript,
    context_block: str,
    client,
    model: str,
    max_tokens: int,
) -> str:
    """Compose a video generation prompt for an end card."""
    prompt = END_CARD_TO_VIDEO_PROMPT.format(
        context=context_block,
        title=script.title,
        end_card_prompt=script.end_card_prompt,
    )
    try:
        return call_llm_text(client, prompt, model, max_tokens).strip()
    except Exception:
        logger.exception("Claude video prompt failed for end card, using original")
        return script.end_card_prompt
