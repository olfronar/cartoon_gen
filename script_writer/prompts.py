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
with fiction. Your scripts blend three comedy traditions:

1. **Absurdist character comedy** (Каламбур style): Recurring characters with \
exaggerated fixed traits. Physical comedy. Characters oblivious to their own \
ridiculousness.

2. **Witty social satire** (Jeeves & Wooster style): Elaborate misunderstandings \
that escalate through social propriety. One character smarter than the rest. \
Wordplay and understatement.

3. **Surreal escalation** (Monty Python style): Situations start normal, become \
increasingly absurd. Fourth-wall breaks. Deadpan delivery. Unexpected endings \
that subvert the setup.

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
1. **absurdist** — exaggerated character reactions, physical comedy, oblivious behavior
2. **satirical** — social commentary, misunderstandings, witty wordplay
3. **surreal** — escalating absurdity, fourth-wall breaks, unexpected twists

For each logline, include:
- `text`: the logline itself (1-2 sentences, sets up the episode premise)
- `approach`: "absurdist" | "satirical" | "surreal"
- `featured_characters`: list of character names from the profiles above that appear
- `visual_hook`: one key visual moment that would make a great video scene

Each logline must contain enough information that someone unfamiliar with this \
headline understands the basic story. The comedic premise should arise from the \
real news — not replace it with an unrelated scenario.

The characters are field correspondents — every logline must place them \
physically at the scene of the news story, not in a studio.

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
2. **Comedy strength** — is it genuinely funny? Does it have a clear comedic engine?
3. **Character fit** — does it use the characters naturally, leveraging their traits?
4. **Visual potential** — can this be made into compelling video scenes?
5. **Originality** — does it avoid obvious/cliché approaches?

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
- **setup**: Establish the news — what happened, who's involved. Billy arrives and \
begins explaining the situation through dialogue with people at the scene. Viewer \
understands the basic facts by end of this act.
- **escalation**: Now that the viewer understands, push the real implications to their \
logical-but-absurd extreme. One escalating beat.
- **punchline**: Land a comedic insight that reframes how the viewer thinks about the news.

This synopsis becomes 2-3 scenes of 8 seconds each (16-24 total). Each act = \
2-3 sentences, not paragraphs. Think sketch-comedy cold open.

Also provide:
- **estimated_scenes**: how many scenes (2-3) this needs
- **key_visual_gags**: list of 2-3 specific visual comedy moments
- **news_explanation**: in 2-3 sentences, what is the real-world news story this \
episode explains?

Return as JSON with keys: setup, escalation, punchline, estimated_scenes, \
key_visual_gags, news_explanation.
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
- Escalation: {escalation}
- Punchline: {punchline}

**Key visual gags to include**: {visual_gags}

**CREATIVE DIRECTION**:
- Every episode is a news explainer. Scene 1 must establish what happened. By \
the end, the viewer understands: who did what, why it matters, why it's absurd.
- The characters are field correspondents reporting from the scene. Every scene \
is set AT the location of the news story — streets, labs, server rooms, launch \
pads, conference halls, etc.
- Keep the plot simple and direct. One clear comedic premise, escalated once, \
resolved with an insight that reframes the news.
- Dialogue is the primary vehicle for both comedy and exposition. Billy explains \
through conversation — with bystanders, officials, confused participants, or to \
camera. His systems-thinking analogies make complex stories accessible. People at \
the scene react, push back, misunderstand.
- Aim for 2-3 dialogue lines per scene. Each line must be short enough to speak \
in 1-2 seconds (8-second scenes). Dialogue should feel like actual people talking \
— reactions, interruptions — not standalone aphorisms.
- Visual comedy enhances dialogue, doesn't replace it. The gap between what Billy \
calmly explains and what the viewer sees behind him IS the comedy.
- Scene structure: Scene 1 = news setup (what happened), Scene 2 = absurd \
escalation (real implications pushed to extreme), Scene 3 = comedic reframe \
(Billy's closing insight).
- When dialogue IS included, write it as spoken lines with character attribution \
— the video model generates audio natively from quoted dialogue in scene_prompt.

Write {num_scenes} scenes. For each scene provide:

- `scene_number`: integer (1-based)
- `scene_title`: short descriptive title
- `setting`: location, time of day, atmosphere
- `scene_prompt`: 50-150 words describing the scene. \
Front-load the key visual in the first 20-30 words. \
Use the format: "[Subject performing action] in [setting]. [Camera movement]. \
[Visual style]. [Audio/dialogue cues]." \
Affirmative descriptions ONLY — no negative prompts (never say "no", "without", \
"don't", "avoid"). \
Include character visual details from profiles (clothing, colors, features). \
If the scene has dialogue, include it as quoted speech with character attribution \
directly in the prompt (e.g. '[Character] says: "[line]"').
- `dialogue`: array of objects with "character" and "line" keys. Aim for 2-3 \
lines per scene with conversational flow — Billy explaining + reactions from \
people at the scene.
- `visual_gag`: description of the comedy beat (or null if none)
- `audio_direction`: music, sound effects, ambient sounds, and dialogue delivery notes
- `duration_seconds`: 8
- `camera_movement`: e.g. "slow zoom in", "pan left to right", "static wide shot"

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
