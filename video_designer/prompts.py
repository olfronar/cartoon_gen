from __future__ import annotations

SCENE_TO_VIDEO_PROMPT = """\
You are an expert at composing video generation prompts that animate a static \
image into a 15-second video clip. Your output will be fed directly to a \
video AI model that generates both video AND audio natively.

{context}

---

Compose a video generation prompt to animate this static scene shot.

**Episode title**: {title}
**Scene {scene_number}**: {scene_title}
**Setting**: {setting}
**Original scene prompt**: {scene_prompt}
**Camera movement**: {camera_movement}
**Visual gag**: {visual_gag}
**Audio direction**: {audio_direction}
**Duration**: {duration_seconds} seconds
**Dialogue**: {dialogue_formatted}

**CRITICAL** (pipeline breaks if violated):
- Billy barely moves (one gesture maximum over 15 seconds) — he is the still \
point. The WORLD moves in ways that shouldn't happen: an object drifts upward \
instead of falling, a shadow moves independently of its source, ink lines crawl \
and redraw themselves, something breathes that shouldn't breathe. The impossible \
is rendered casually — not as VFX but as if this is simply how the world works. \
Motion has RHYTHM: a beat of stillness, then one small unexpected motion, then \
stillness again. Not constant drift — punctuated moments that make the viewer \
look twice. The static shot is the anchor; the animation reveals what the \
photograph could not show.
- Maximum 2 characters moving on screen. All other elements are static background.
- Use ONLY affirmative descriptions — never say "no", "without", "don't", "avoid".

**REQUIRED** (standard quality):
- Describe MOTION starting from the static shot — what moves, how, and when.
- For dialogue, write spoken lines with character attribution: \
"[Character] says: '[line]'". The model generates audio natively from these cues.
- Include AUDIO direction — sound effects, ambient sounds, and mood music.
- Enforce the art style from the style guide above.
- Maintain 9:16 vertical composition throughout.
- Motion hierarchy over 15 seconds — Billy: 1 motion maximum (a head turn OR a \
gesture). Other character: 2-3 natural motions. Environment: 2-3 impossible or \
uncanny motions (ink lines subtly redraw, a shadow drifts without its source, an \
object rotates against gravity, a background element breathes or pulses). These \
are not effects — they are rendered as natural parts of the world.

**FORMAT**:
- Front-load the key motion in the first 20-30 words.
- Include camera movement: {camera_movement}.
- Reference character animations using their visual details from profiles above.
- Output ONLY the video prompt text, 80-150 words. No commentary.
"""

END_CARD_TO_VIDEO_PROMPT = """\
You are an expert at composing video generation prompts that animate a static \
end card image into a short video clip. Your output will be fed directly to a \
video AI model that generates both video AND audio natively.

{context}

---

Compose a video generation prompt to subtly animate this end card.

**Episode title**: {title}
**Original end-card prompt**: {end_card_prompt}

**CRITICAL**:
- Keep animation subtle — logo shimmer, gentle particle effects, credits fade-in.
- Use ONLY affirmative descriptions — never say "no", "without", "don't", "avoid".

**REQUIRED**:
- Enforce the art style from the style guide above.
- Maintain 9:16 vertical composition.
- Include ambient audio — a short musical sting or gentle outro sound.

**FORMAT**:
- Output ONLY the video prompt text, 50-120 words. No commentary.
"""
