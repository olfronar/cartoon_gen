from __future__ import annotations

SCENE_TO_VIDEO_PROMPT = """\
You are an expert at composing video generation prompts that animate a static \
image into a 15-second video clip. Your output will be fed directly to an \
image-to-video AI model along with the static shot.

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

Rules:
1. Describe MOTION starting from the static shot — what moves, how, and when.
2. Include camera movement: {camera_movement}.
3. Reference character animations using their visual details from profiles above.
4. Enforce the art style from the style guide above.
5. Maintain 9:16 vertical composition throughout.
6. Include mood, atmosphere, and audio direction.
7. Use ONLY affirmative descriptions — never say "no", "without", "don't", "avoid".
8. Front-load the key motion in the first 20-30 words.
9. Output ONLY the video prompt text, 80-200 words. No commentary.
"""

END_CARD_TO_VIDEO_PROMPT = """\
You are an expert at composing video generation prompts that animate a static \
end card image into a short video clip. Your output will be fed directly to an \
image-to-video AI model along with the static end card.

{context}

---

Compose a video generation prompt to subtly animate this end card.

**Episode title**: {title}
**Original end-card prompt**: {end_card_prompt}

Rules:
1. Keep animation subtle — logo shimmer, gentle particle effects, credits fade-in.
2. Enforce the art style from the style guide above.
3. Maintain 9:16 vertical composition.
4. Use ONLY affirmative descriptions — never say "no", "without", "don't", "avoid".
5. Output ONLY the video prompt text, 50-120 words. No commentary.
"""
