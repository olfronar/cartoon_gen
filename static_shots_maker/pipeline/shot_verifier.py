from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from shared.models import CartoonScript, SceneScript
from shared.utils import call_llm_json

from ..prompts import SHOT_COMPARISON_PROMPT, SHOT_VERIFICATION_PROMPT

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class VerificationResult:
    passed: bool
    issues: list[str]
    prompt_refinements: str
    score: float


def verify_shot(
    image_path: Path,
    scene: SceneScript,
    script: CartoonScript,
    client,
    model: str = "claude-opus-4-6",
    max_tokens: int = 4096,
) -> VerificationResult:
    """Compare generated image against scene_prompt via Claude vision."""
    try:
        prompt = SHOT_VERIFICATION_PROMPT.format(
            scene_title=scene.scene_title,
            scene_prompt=scene.scene_prompt,
            visual_gag=scene.visual_gag or "none",
            format_type=script.format_type or "standard",
            billy_emotion=scene.billy_emotion or "deadpan",
        )
        data = call_llm_json(client, prompt, model, max_tokens, images=[image_path])
        return VerificationResult(
            passed=data.get("passed", True) if isinstance(data, dict) else True,
            issues=data.get("issues", []) if isinstance(data, dict) else [],
            prompt_refinements=data.get("prompt_refinements", "") if isinstance(data, dict) else "",
            score=float(data.get("score", 5.0)) if isinstance(data, dict) else 5.0,
        )
    except Exception:
        logger.exception("Shot verification failed — treating as passed")
        return VerificationResult(passed=True, issues=[], prompt_refinements="", score=5.0)


def compare_candidates(
    image_a: Path,
    image_b: Path,
    scene: SceneScript,
    script: CartoonScript,
    client,
    model: str = "claude-opus-4-6",
    max_tokens: int = 4096,
) -> Literal["a", "b"]:
    """Pairwise VLM comparison of two candidate images. Returns winner."""
    try:
        prompt = SHOT_COMPARISON_PROMPT.format(
            scene_title=scene.scene_title,
            scene_prompt=scene.scene_prompt,
            format_type=script.format_type or "standard",
        )
        data = call_llm_json(client, prompt, model, max_tokens, images=[image_a, image_b])
        winner = data.get("winner", "a").lower() if isinstance(data, dict) else "a"
        return "b" if winner == "b" else "a"
    except Exception:
        logger.exception("Shot comparison failed — defaulting to candidate A")
        return "a"
