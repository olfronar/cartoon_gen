from __future__ import annotations

SCENE_TO_IMAGE_PROMPT = """\
You are an expert at converting video scene descriptions into optimized \
static image generation prompts. Your output will be fed directly to an \
image generation model.

{context}

---

Rewrite the following video-oriented scene prompt into a single, optimized \
static image generation prompt.

**Episode title**: {title}
**Scene {scene_number}**: {scene_title}
**Setting**: {setting}
**Original scene prompt**: {scene_prompt}
**Visual gag**: {visual_gag}
**Camera framing**: {camera_movement}

Rules:
1. Pick the single most visually striking frozen moment from this scene.
2. Replace all motion/duration/audio references with static visual descriptions.
3. Include FULL character visual descriptions from the character profiles above \
(clothing, colors, distinguishing features) — the image model has no memory.
4. Enforce the art style from the style guide above.
5. Compose for 9:16 vertical format (portrait orientation).
6. Use ONLY affirmative descriptions — never say "no", "without", "don't", "avoid".
7. Front-load the key visual in the first 20-30 words.
8. Output ONLY the image prompt text, 80-200 words. No commentary.
"""

END_CARD_TO_IMAGE_PROMPT = """\
You are an expert at converting video end-card descriptions into optimized \
static image generation prompts. Your output will be fed directly to an \
image generation model.

{context}

---

Rewrite the following end-card prompt into a single, optimized static image \
generation prompt.

**Episode title**: {title}
**Original end-card prompt**: {end_card_prompt}

Rules:
1. Focus on title/credits composition — this is the episode end card.
2. Include the art style from the style guide above.
3. Compose for 9:16 vertical format (portrait orientation).
4. Use ONLY affirmative descriptions — never say "no", "without", "don't", "avoid".
5. Front-load the key visual in the first 20-30 words.
6. Output ONLY the image prompt text, 80-200 words. No commentary.
"""
