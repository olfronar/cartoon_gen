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
- MOTION VERBS: Use specific, vigorous verbs: lunges, collapses, erupts, \
shatters, buckles, swells, warps, wilts, inflates, crumbles, snaps, peels, \
bloats, fractures, oozes, spasms. NEVER use generic verbs: moves, goes, \
changes, happens, appears, transitions, becomes. Generic motion = static video.
- MOTION TRAJECTORY: For every moving element, specify: FROM what state \
TO what state, at what SPEED (sudden/gradual/accelerating). \
"The phone swells from palm-sized to cinder-block in 3 seconds" not \
"the phone transforms." "Billy's wrist buckles under sudden weight" not \
"Billy reacts."
- SINGLE FOCUS: Describe ONE primary motion in full mechanical detail — \
the viewer's eye follows this. All other motion is ambient texture described \
in 2-3 words each ("shadows pulse," "dust drifts," "surface ripples").
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

DYNAMICS_CHECK_PROMPT = """\
You are checking whether a video generation prompt describes enough specific \
physical motion to produce a dynamic (not static) video.

## Video prompt to evaluate
{video_prompt}

## Format type
{format_type}

## Rate motion specificity (1-5)

1 = No motion described at all — reads like a still image description
2 = Vague motion ("things move," "changes occur," "transforms")
3 = Some specifics but missing trajectories or speeds
4 = Clear motion trajectories with FROM/TO states and timing
5 = Vivid physical detail — you can visualize the exact motion frame by frame

## Output format

Return JSON:
{{
  "motion_score": 1-5,
  "has_vigorous_verbs": true or false,
  "has_trajectory": true or false,
  "suggested_motion": "If score < 3, describe ONE specific physical motion to \
add that would make the video dynamic. Otherwise empty string."
}}\
"""

DYNAMICS_REWRITE_PROMPT = """\
Rewrite this video prompt to include more dynamic motion.

Original prompt:
{video_prompt}

Motion to add:
{suggestion}

Rules:
- 80-150 words max
- Use vigorous verbs (lunges, collapses, erupts) not generic (moves, goes)
- Specify FROM/TO state and SPEED for the new motion
- Keep all existing dialogue, audio, and camera direction
- Output ONLY the rewritten prompt, no commentary\
"""
