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
- Prefer subtle, unhurried motion — slow zooms, gentle pans, measured gestures — \
over complex choreography. The static shot is already composed well; animate it gently. \
When motion IS added, favor the physically impossible rendered casually: an \
object that drifts upward instead of falling, a shadow that moves independently \
of its source, a gentle breathing motion in something that should not breathe. \
AI video excels at showing things that could never exist, delivered with the calm \
of things that always have.
- Maximum 2 characters moving on screen. All other elements are static background.
- Use ONLY affirmative descriptions — never say "no", "without", "don't", "avoid".

**REQUIRED** (standard quality):
- Describe MOTION starting from the static shot — what moves, how, and when.
- For dialogue, write spoken lines with character attribution: \
"[Character] says: '[line]'". The model generates audio natively from these cues.
- Include AUDIO direction — sound effects, ambient sounds, and mood music.
- Enforce the art style from the style guide above.
- Maintain 9:16 vertical composition throughout.
- Over the 15-second duration, allow 2-3 subtle motions per character — a head \
turn, then an arm gesture, then a shift in stance. Not rapid action, but a gentle \
progression that fills the time.

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
