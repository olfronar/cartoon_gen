from __future__ import annotations

import logging
from pathlib import Path

from shared.models import CartoonScript, SceneScript
from shared.utils import call_llm_json, call_llm_text
from video_designer.prompts import DYNAMICS_CHECK_PROMPT, SCENE_TO_VIDEO_PROMPT

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
        video_prompt = call_llm_text(client, prompt, model, max_tokens, images=images).strip()
    except Exception:
        logger.exception(
            "Claude video prompt failed for scene %d, using original scene_prompt",
            scene.scene_number,
        )
        return scene.scene_prompt

    return _check_dynamics(video_prompt, scene, script, client)


_DYNAMICS_CHECK_MAX_TOKENS = 2048


def _check_dynamics(
    video_prompt: str,
    scene: SceneScript,
    script: CartoonScript,
    client,
) -> str:
    """Check if video prompt describes specific physical motion. Fail-open."""
    try:
        check_prompt = DYNAMICS_CHECK_PROMPT.format(
            video_prompt=video_prompt,
            format_type=script.format_type or "demonstration",
        )
        data = call_llm_json(client, check_prompt, "claude-sonnet-4-6", _DYNAMICS_CHECK_MAX_TOKENS)
        if not isinstance(data, dict):
            return video_prompt
        score = data.get("motion_score", 5)
        if score >= 3:
            logger.info(
                "Video dynamics check passed (score=%d) for scene %d",
                score,
                scene.scene_number,
            )
            return video_prompt
        suggestion = data.get("suggested_motion", "")
        if not suggestion:
            logger.warning(
                "Video dynamics check failed (score=%d) but no suggestion for scene %d",
                score,
                scene.scene_number,
            )
            return video_prompt
        # Rewrite the prompt incorporating the motion suggestion
        rewrite_prompt = (
            f"Rewrite this video prompt to include more dynamic motion.\n\n"
            f"Original prompt:\n{video_prompt}\n\n"
            f"Motion to add:\n{suggestion}\n\n"
            f"Rules:\n"
            f"- 80-150 words max\n"
            f"- Use vigorous verbs (lunges, collapses, erupts) not generic (moves, goes)\n"
            f"- Specify FROM/TO state and SPEED for the new motion\n"
            f"- Keep all existing dialogue, audio, and camera direction\n"
            f"- Output ONLY the rewritten prompt, no commentary"
        )
        revised = call_llm_text(
            client, rewrite_prompt, "claude-sonnet-4-6", _DYNAMICS_CHECK_MAX_TOKENS
        ).strip()
        logger.info(
            "Video dynamics check: rewrote prompt for scene %d (score=%d)",
            scene.scene_number,
            score,
        )
        return revised
    except Exception:
        logger.exception("Video dynamics check failed — keeping original prompt")
        return video_prompt
