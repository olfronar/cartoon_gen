from __future__ import annotations

SCENE_TO_VIDEO_PROMPT = """\
You are an expert at composing video generation prompts that animate a static \
image into an 8-second video clip. Your output will be fed directly to a \
video AI model (Veo 3.1) that generates both video AND audio natively.

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

Rules:
1. Describe MOTION starting from the static shot — what moves, how, and when.
2. Include camera movement: {camera_movement}.
3. Reference character animations using their visual details from profiles above.
4. Enforce the art style from the style guide above.
5. Maintain 9:16 vertical composition throughout.
6. Include AUDIO direction — sound effects, ambient sounds, and mood music.
7. For dialogue, write spoken lines with character attribution: \
"[Character] says: '[line]'". The model generates audio natively from these cues.
8. Use ONLY affirmative descriptions — never say "no", "without", "don't", "avoid".
9. Front-load the key motion in the first 20-30 words.
10. Output ONLY the video prompt text, 80-200 words. No commentary.
"""

END_CARD_TO_VIDEO_PROMPT = """\
You are an expert at composing video generation prompts that animate a static \
end card image into a short video clip. Your output will be fed directly to a \
video AI model (Veo 3.1) that generates both video AND audio natively.

{context}

---

Compose a video generation prompt to subtly animate this end card.

**Episode title**: {title}
**Original end-card prompt**: {end_card_prompt}

Rules:
1. Keep animation subtle — logo shimmer, gentle particle effects, credits fade-in.
2. Enforce the art style from the style guide above.
3. Maintain 9:16 vertical composition.
4. Include ambient audio — a short musical sting or gentle outro sound.
5. Use ONLY affirmative descriptions — never say "no", "without", "don't", "avoid".
6. Output ONLY the video prompt text, 50-120 words. No commentary.
"""
