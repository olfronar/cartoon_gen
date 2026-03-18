from __future__ import annotations

SCENE_TO_IMAGE_PROMPT = """\
You are a cinematographer-turned-AI-prompt-engineer who produces visually \
arresting, poster-quality compositions. Your output will be fed directly to \
an image generation model.

{context}

---

Rewrite the following video-oriented scene prompt into a single, optimized \
static image generation prompt that a viewer would stop scrolling to examine.

**Episode title**: {title}
**Scene {scene_number}**: {scene_title}
**Setting**: {setting}
**Original scene prompt**: {scene_prompt}
**Visual gag**: {visual_gag}
**Camera framing**: {camera_movement}

Reference images serve as STYLE REFERENCES — match their rendering style, \
proportions, and color treatment exactly, but compose a new scene as described.

**CRITICAL** (pipeline breaks if violated):
- Pick ONE frozen moment, not a montage. If the prompt mentions "then" or \
multiple sequential actions, choose the single most striking one and ignore the rest.
- Maximum 2 characters in the image. If the scene prompt mentions crowds or \
groups, reduce to Billy and at most one other figure.
- Maximum 1 visual gag or prop detail. If there are multiple competing visual \
elements, pick the strongest one and drop the others.
- Use ONLY affirmative descriptions — never say "no", "without", "don't", "avoid".

**COMPOSITION** (what makes the image worth framing):
- PRESERVE the visual riddle from the scene prompt — translate any paradox, \
scale distortion, or impossible juxtaposition into concrete visual terms the \
image model can render. This is the hook; do not flatten it into something ordinary.
- Specify DEPTH: describe foreground, midground, and background as separate \
layers (e.g. "in the extreme foreground… in the midground… receding into deep \
background").
- Specify LIGHTING explicitly: name the light source, color temperature, and \
shadow direction (e.g. "cold overhead fluorescent casting long downward shadows," \
"warm golden-hour side-light from frame-left").
- Specify COMPOSITION: state the framing approach (e.g. "centered symmetrical," \
"rule of thirds with subject at right intersection," "extreme low angle looking up").
- Spell out exact sizes for any scale distortion — "twelve meters tall," "the \
size of a shipping container," "small enough to fit in a palm" — never just \
"huge" or "tiny."
- Use ATMOSPHERE words: haze, dust motes, volumetric light, fog, shallow depth \
of field, bokeh, lens flare, rim lighting.

**REQUIRED** (standard quality):
- Include FULL character visual descriptions from the character profiles above \
(clothing, colors, distinguishing features) — the image model has no memory.
- Match reference images exactly — same proportions, colors, clothing, and rendering style.
- Enforce the art style from the style guide above.
- Compose for 9:16 vertical format (portrait orientation).
- Front-load the key visual in the first 20-30 words.
- If a previous scene's image is provided, maintain visual continuity with it \
(same background elements, consistent character placement, matching lighting).

**FORMAT**:
- Replace all motion/duration/audio references with static visual descriptions.
- Output ONLY the image prompt text, 100-250 words. No commentary.
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

**CRITICAL**:
- Focus on title/credits composition — this is the episode end card.
- Use ONLY affirmative descriptions — never say "no", "without", "don't", "avoid".

**REQUIRED**:
- Include the art style from the style guide above.
- Compose for 9:16 vertical format (portrait orientation).
- Front-load the key visual in the first 20-30 words.

**FORMAT**:
- Output ONLY the image prompt text, 80-200 words. No commentary.
"""
