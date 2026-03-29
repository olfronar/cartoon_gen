from __future__ import annotations

SCENE_TO_VIDEO_PROMPT = """\
You are an expert at composing video generation prompts that animate a static \
image into a 15-second video clip. Your output will be fed directly to a \
video AI model that generates both video AND audio natively.

{context}

---

Compose a video generation prompt to animate this static scene shot. \
If an image is attached, that is the ACTUAL RENDERED STATIC SHOT — use it as your \
visual ground truth. Reference what you SEE in the image (composition, colors, \
lighting, character positions, object placement) rather than relying solely on the \
text descriptions below. The video should start from exactly this frame.

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
**Format type**: {format_type}
**Billy's emotion**: {billy_emotion}

**CRITICAL** (pipeline breaks if violated):
- **Format-aware motion direction** (adapt to format type):
  - **visual_punchline**: Environment moves, Billy is still. Wrongness grows \
visibly — start the motion immediately, don't wait. The accumulation IS the comedy.
  - **exchange**: Character body language drives motion. Dialogue starts within \
the first 2-3 seconds. Characters react physically — posture shifts, gestures, head \
turns. Billy's emotion ({billy_emotion}) is visible in his body language.
  - **cold_reveal**: Camera movement IS the story. Purposeful reveal that changes \
what the viewer understands. Start moving early — the payoff needs time to land.
  - **demonstration**: One deliberate gesture from Billy. Object transforms. The \
gesture is casual, the result is impossible.
- PACING: hit the action fast. Start motion or dialogue within the first 2-3 \
seconds. Don't waste the opening on a static establishing shot — the static \
image already established the scene. The viewer is scrolling on a phone.
- The WORLD also moves impossibly around the action — \
shadows shift independently, textures ripple, things breathe that shouldn't. \
These ambient motions complement the primary motion, not compete with it.
- Maximum 2 characters moving on screen. All other elements are static background.
- Use ONLY affirmative descriptions — never say "no", "without", "don't", "avoid".

**REQUIRED** (standard quality):
- Describe MOTION starting from the static shot — what moves, how, and when.
- For dialogue, write spoken lines with character attribution: \
"[Character] says: '[line]'". The model generates audio natively from these cues.
- Include AUDIO direction — sound effects, ambient sounds, and mood music.
- Enforce the art style from the style guide above.
- Maintain 9:16 vertical composition throughout.
- Billy's body language matches his emotion ({billy_emotion}) — not always "barely moves." \
A frustrated Billy shifts weight. An amused Billy tilts his head. An alarmed Billy takes \
a half-step back.
- Other character: 2-3 natural motions. Environment: 2-3 uncanny motions that complement \
the scene (shadows shifting, textures subtly rippling, background elements breathing \
or pulsing in response). These are not effects — they are rendered as natural parts \
of the world.

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
