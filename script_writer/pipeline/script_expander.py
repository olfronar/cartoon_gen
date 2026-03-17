from __future__ import annotations

import logging
from datetime import date

from script_writer.prompts import HUMOR_PREAMBLE, SCRIPT_EXPANSION_PROMPT, SYNOPSIS_PROMPT
from shared.models import (
    CartoonScript,
    Logline,
    SceneScript,
    ScoredItem,
    Synopsis,
)
from shared.utils import call_llm_json

logger = logging.getLogger(__name__)


def generate_synopsis(
    logline: Logline,
    item: ScoredItem,
    context_block: str,
    client,
    model: str = "claude-opus-4-6",
    max_tokens: int = 64000,
) -> Synopsis:
    """Generate a three-act synopsis for a logline."""
    prompt = SYNOPSIS_PROMPT.format(
        preamble=HUMOR_PREAMBLE,
        context=context_block,
        logline=logline.text,
        title=item.item.title,
        comedy_angle=item.comedy_angle,
        snippet=item.item.snippet,
    )

    data = call_llm_json(client, prompt, model, max_tokens)

    return Synopsis(
        setup=data["setup"],
        development=data.get("development", data.get("escalation", "")),
        punchline=data["punchline"],
        estimated_scenes=int(data.get("estimated_scenes", 3)),
        key_visual_gags=data.get("key_visual_gags", []),
        news_explanation=data.get("news_explanation", ""),
    )


def expand_script(
    logline: Logline,
    synopsis: Synopsis,
    item: ScoredItem,
    script_date: date,
    context_block: str,
    client,
    model: str = "claude-opus-4-6",
    max_tokens: int = 64000,
) -> CartoonScript:
    """Expand a synopsis into a full script with scene-by-scene breakdown."""
    prompt = SCRIPT_EXPANSION_PROMPT.format(
        preamble=HUMOR_PREAMBLE,
        context=context_block,
        title=item.item.title,
        logline=logline.text,
        setup=synopsis.setup,
        development=synopsis.development,
        punchline=synopsis.punchline,
        visual_gags=", ".join(synopsis.key_visual_gags),
        comedy_angle=item.comedy_angle,
        snippet=item.item.snippet,
        news_explanation=synopsis.news_explanation,
    )

    data = call_llm_json(client, prompt, model, max_tokens)

    scenes = [
        SceneScript(
            scene_number=s["scene_number"],
            scene_title=s["scene_title"],
            setting=s["setting"],
            scene_prompt=s["scene_prompt"],
            dialogue=s.get("dialogue", []),
            visual_gag=s.get("visual_gag"),
            audio_direction=s.get("audio_direction", ""),
            duration_seconds=int(s.get("duration_seconds", 5)),
            camera_movement=s.get("camera_movement", ""),
        )
        for s in data["scenes"]
    ]

    return CartoonScript(
        title=data["title"],
        date=script_date,
        source_item=item,
        logline=logline.text,
        synopsis=synopsis,
        scenes=scenes,
        end_card_prompt=data.get("end_card_prompt", ""),
        characters_used=data.get("characters_used", []),
    )
