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
**Transformation**: {transformation}

**CRITICAL** (pipeline breaks if violated):
- Billy is the calm center AND has ONE deliberate transformation gesture — touch, \
point, or sweep. Under his hand, objects change: material shifts, lines redraw, \
ink technique transforms. Rendered casually, as if this is how explanation works \
when Billy does it. The WORLD also moves impossibly around the transformation — \
shadows shift independently, ink lines crawl, things breathe that shouldn't. \
These ambient motions complement the transformation, not compete with it.
- Transformation timing synced to dialogue:
  - Seconds 1-5 (Line 1): Static hold. Objects in starting state. Billy surveys.
  - Seconds 5-10 (Line 2): Billy gestures. Transformation unfolds. Ink techniques shift.
  - Seconds 10-15 (Line 3): Transformed state holds. Punchline lands. Beat of stillness.
- If no transformation is provided (field is empty or "None"), fall back to \
original behavior: Billy barely moves, the WORLD moves in ways that shouldn't \
happen. Motion has RHYTHM: stillness, then one unexpected motion, then stillness \
again. Not constant drift — punctuated moments.
- Maximum 2 characters moving on screen. All other elements are static background.
- Use ONLY affirmative descriptions — never say "no", "without", "don't", "avoid".

**REQUIRED** (standard quality):
- Describe MOTION starting from the static shot — what moves, how, and when.
- For dialogue, write spoken lines with character attribution: \
"[Character] says: '[line]'". The model generates audio natively from these cues.
- Include AUDIO direction — sound effects, ambient sounds, and mood music.
- Enforce the art style from the style guide above.
- Maintain 9:16 vertical composition throughout.
- Motion hierarchy over 15 seconds — Billy: his transformation gesture IS his \
primary motion (1 deliberate gesture + 1 optional subtle motion). Other character: \
2-3 natural motions. Environment: 2-3 uncanny motions that complement the \
transformation (shadows shifting around the changed object, ink redrawing itself, \
background elements breathing or pulsing in response). These are not effects — \
they are rendered as natural parts of the world.

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
