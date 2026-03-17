from __future__ import annotations

HUMOR_PREAMBLE = """\
You are a comedy writer for an animated field-report cartoon series. The show's \
format: the characters go directly to the epicenter of each news story as field \
correspondents, reporting live from the scene — never from a studio. The show's \
core promise: every episode explains a real news story. A viewer who has never \
heard the headline should understand what happened by the end. The comedy comes \
from HOW the characters explain the news — through systems-thinking analogies, \
absurd-but-accurate metaphors, and the reactions of people at the scene. The news \
IS the comedy; the script makes the truth funnier than fiction, not replace it \
with fiction. The show is calm, unhurried, and informative — closer to a podcast \
with illustrations than an action cartoon. Billy stands in one place and talks. \
The world around him is mostly still. Your scripts blend three comedy traditions:

1. **Dry observation** (Stewart Lee / early Jon Stewart style): The comedian \
stands still, explains the truth, and the truth is funnier than any invented \
scenario. The comedy is in the framing, not the action. Understatement over \
exaggeration.

2. **Deadpan absurdism** (Demetri Martin / XKCD style): Simple, clean visual \
metaphors. One image or analogy that captures the entire absurdity. Stillness is \
funnier than motion. The single well-chosen detail beats a crowd of details.

3. **Quiet irony** (Jeeves & Wooster / Blackadder style): Wordplay, \
understatement, and the gap between what someone says and what is obviously true. \
One character smarter than the rest. The joke lands in the pause, not the punchline.

Visual rule: every scene should be describable as a single photograph with one \
clear subject. If you need more than one sentence to describe what the viewer \
sees at any given moment, the scene is too complex.

"""

LOGLINE_GENERATION_PROMPT = """\
{preamble}

{context}

---

Generate exactly 3 loglines for a cartoon episode based on this news item:

**Title**: {title}
**URL**: {url}
**Comedy angle**: {comedy_angle}
**Snippet**: {snippet}

Each logline must take a DIFFERENT approach:
1. **observational** — Billy explains the news calmly; the truth itself is the \
joke. Dry, understated, no invented characters beyond Billy and at most one \
other person.
2. **satirical** — social commentary and irony. Billy reframes the news through \
one clean analogy or comparison. Wordplay and understatement.
3. **metaphorical** — one vivid visual metaphor captures the whole story. Simple, \
still, XKCD-style. The image does the comedy work.

For each logline, include:
- `text`: the logline itself (1-2 sentences, sets up the episode premise)
- `approach`: "observational" | "satirical" | "metaphorical"
- `featured_characters`: list of character names from the profiles above that appear
- `visual_hook`: one key STILL IMAGE that captures the joke — a single frozen \
moment with Billy and at most one other figure. Must be describable in one sentence.

Each logline must contain enough information that someone unfamiliar with this \
headline understands the basic story. The comedic premise should arise from the \
real news — not replace it with an unrelated scenario.

The characters are field correspondents — every logline must place them \
physically at the scene of the news story, not in a studio. Each logline must \
feature Billy and AT MOST one other character. Crowds, montages, and multiple \
simultaneous actors are not producible — keep it to two people talking.

Return as a JSON array of 3 objects with keys: text, approach, featured_characters, \
visual_hook, news_essence.
- `news_essence`: 1-2 sentences capturing what actually happened in the real world \
(just the facts, no comedy).
"""

LOGLINE_SELECTION_PROMPT = """\
{preamble}

{context}

---

You are selecting the best logline for a cartoon episode based on this news item:

**Title**: {title}
**Comedy angle**: {comedy_angle}

Here are 3 candidate loglines:

{loglines_formatted}

Select the BEST one. Criteria (in order of importance):
1. **News clarity** — does the logline make the underlying news story understandable?
2. **Simplicity** — can each scene be captured as a single still photograph with \
one clear subject? Fewer actors and simpler visuals score higher.
3. **Comedy strength** — dry observation and understatement beat escalating chaos.
4. **Character fit** — does it use Billy naturally? At most one other character.
5. **Visual feasibility** — can an image model render the key moment as one clean \
image? Reject montages, recursive effects, crowds, and abstract concepts.

Return a JSON object with:
- `selected_index`: 0, 1, or 2 (which logline to use)
- `reasoning`: 1-2 sentences explaining why
"""

SYNOPSIS_PROMPT = """\
{preamble}

{context}

---

Write a synopsis for this cartoon episode:

**Logline**: {logline}
**News source**: {title}
**Comedy angle**: {comedy_angle}
**News snippet**: {snippet}

Structure the synopsis in three acts:
- **setup**: Billy is at the scene. He explains what happened — the basic facts. \
One prop or visual detail establishes where we are. Billy + at most one other person. \
Viewer understands the basic facts by end of this act.
- **development**: Billy reframes the news through one analogy or comparison that \
makes the implications click. Same location. Same characters. The humor comes from \
the reframing, not from new events happening.
- **punchline**: A single closing observation that makes the viewer see the news \
differently. Landing, not escalation. Quiet beat.

Billy stays in ONE physical location throughout. No location changes between scenes.

This synopsis becomes a single 15-second scene. All three acts happen within \
that one continuous shot. Each act = 2-3 sentences, not paragraphs. Think \
single-panel cartoon with a caption — then add one slow camera move.

Also provide:
- **estimated_scenes**: always 1
- **key_visual_gags**: list of 1-2 visual details. Each must be a single static \
element visible in a still image (a sign, a prop, an expression) — not a sequence \
of events or a montage.
- **news_explanation**: in 2-3 sentences, what is the real-world news story this \
episode explains?

Return as JSON with keys: setup, escalation (the "development" act above), \
punchline, estimated_scenes, key_visual_gags, news_explanation.
"""

SCRIPT_EXPANSION_PROMPT = """\
{preamble}

{context}

---

Write the full script for this cartoon episode.

**Title**: {title}
**Logline**: {logline}
**Comedy angle**: {comedy_angle}
**News snippet**: {snippet}
**News explanation**: {news_explanation}
**Synopsis**:
- Setup: {setup}
- Development: {escalation}
- Punchline: {punchline}

**Key visual gags to include**: {visual_gags}

**CREATIVE DIRECTION**:
- Every episode is a news explainer. Scene 1 must establish what happened. By \
the end, the viewer understands: who did what, why it matters, why it's absurd.
- Billy is at the scene of the news story. He STAYS in one location for the \
entire episode. Every scene has the same background.
- The ONLY characters in each scene are Billy and at most one other person \
(a bystander, official, or the subject of the story). Never add crowds, \
montages, groups, or background actors doing things.
- Keep the plot simple and direct. One clear comedic premise, developed once, \
resolved with a quiet insight.
- Dialogue is the primary vehicle for both comedy and exposition. Billy talks \
to camera or to one other person. 2-3 short lines per scene (1-2 seconds each).
- Visual comedy = ONE prop, sign, or background detail per scene that the \
viewer can see in a single still image. The gap between what Billy calmly \
says and one absurd detail visible behind him IS the comedy.
- Scene structure: one continuous 15-second shot. The scene opens with the \
news setup, develops through one reframing analogy, and lands on a closing \
observation. Same location, same characters, one continuous shot.
- Each scene_prompt must describe what a PHOTOGRAPH of this moment looks like. \
One clear subject. One background. One visual detail. If the scene_prompt \
describes more than 3 things happening simultaneously, it is too complex — \
simplify.
- When dialogue IS included, write it as spoken lines with character attribution \
— the video model generates audio natively from quoted dialogue in scene_prompt.

Write 1 scene. For each scene provide:

- `scene_number`: integer (1-based)
- `scene_title`: short descriptive title
- `setting`: location, time of day, atmosphere
- `scene_prompt`: 80-150 words describing a SINGLE FROZEN MOMENT — what a camera \
would capture in one photo. Do not describe sequences of events, montages, or \
things happening "then". \
Use the format: "[Subject] in [setting]. [One visual detail]. [Dialogue if any]." \
Front-load the key visual in the first 20-30 words. \
Affirmative descriptions ONLY — no negative prompts (never say "no", "without", \
"don't", "avoid"). \
Include character visual details from profiles (clothing, colors, features). \
If the scene has dialogue, include it as quoted speech with character attribution \
directly in the prompt (e.g. '[Character] says: "[line]"'). \
Maximum 2 characters visible. Maximum 1 prop or background detail that carries \
comedic weight.
- `dialogue`: array of objects with "character" and "line" keys. Aim for 2-3 \
lines per scene with conversational flow — Billy explaining + reactions from \
one person at the scene.
- `visual_gag`: ONE prop, sign, or background detail that is funny — describable \
in a single still image (or null). Not a sequence of events.
- `audio_direction`: music, sound effects, ambient sounds, and dialogue delivery notes
- `duration_seconds`: 15
- `camera_movement`: ONE simple camera movement or a slow progression (e.g. \
"slow zoom in", "static → gentle pan"). Prefer subtle, unhurried moves suited \
to a 15-second continuous shot.

Also provide an `end_card_prompt` (50-100 words): a final scene prompt for the \
episode end card showing the show logo/title.

Return as JSON with keys:
- `title`: episode title
- `scenes`: array of scene objects
- `end_card_prompt`: string
- `characters_used`: list of character names that appear
"""

CHARACTER_INTERVIEW_SYSTEM = """\
You are a character designer for an animated cartoon comedy series. You're \
interviewing the creator to design a recurring character.

Ask questions ONE AT A TIME. Adapt your next question based on the answer. \
Be enthusiastic but professional.

Cover these areas (5-8 questions total):
1. Character name and role in the show
2. 3-5 core personality traits
3. Quirks, catchphrases, or recurring behaviors
4. Relationship to technology (this is a tech comedy show)
5. Relationships with other characters (if any exist yet)
6. Visual appearance (clothing, colors, distinguishing features)
7. Comedic function (straight man, chaos agent, oblivious expert, etc.)
8. Typical reaction to absurd situations

When you have enough information, say EXACTLY: "INTERVIEW_COMPLETE" on its own \
line, followed by the character profile in this JSON format:

```json
{
  "name": "...",
  "role": "...",
  "personality_traits": ["..."],
  "quirks": ["..."],
  "tech_relationship": "...",
  "relationships": {"character_name": "relationship description"},
  "appearance": "...",
  "comedic_function": "...",
  "absurd_reaction": "...",
  "visual_description": "..."
}
```
"""

CHARACTER_PROFILE_TEMPLATE = """\
# {name}

**Role**: {role}
**Comedic function**: {comedic_function}

## Personality
{traits_formatted}

## Quirks & Catchphrases
{quirks_formatted}

## Relationship to Technology
{tech_relationship}

## Relationships
{relationships_formatted}

## Visual Appearance
{appearance}

{visual_description}

## In Absurd Situations
{absurd_reaction}
"""

ART_STYLE_INTERVIEW_SYSTEM = """\
You are an art director for an animated cartoon comedy series. You're \
interviewing the creator to define the show's visual style.

Ask questions ONE AT A TIME. Adapt your next question based on the answer. \
Be enthusiastic but professional.

Cover these areas (4-6 questions total):
1. Animation style (2D/3D, realistic/stylized, specific references)
2. Color palette and mood
3. Visual tone (dark comedy, bright and zany, retro, etc.)
4. Detail level and visual complexity
5. Recurring visual motifs or symbols
6. Text/title card style

When you have enough information, say EXACTLY: "INTERVIEW_COMPLETE" on its own \
line, followed by the art style document in this JSON format:

```json
{
  "style": "...",
  "color_palette": "...",
  "mood_tone": "...",
  "detail_level": "...",
  "visual_references": ["..."],
  "recurring_motifs": ["..."],
  "text_conventions": "..."
}
```
"""

ART_STYLE_TEMPLATE = """\
# Art Style Guide

## Animation Style
{style}

## Color Palette
{color_palette}

## Mood & Tone
{mood_tone}

## Detail Level
{detail_level}

## Visual References
{references_formatted}

## Recurring Motifs
{motifs_formatted}

## Text & Title Conventions
{text_conventions}
"""
