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
The world around him is mostly still.

**CRITICAL visual rule**: every scene must be describable as a single photograph \
with one clear subject — but that photograph should make someone feel something. \
Compose for feeling, not framing: one subject, one emotional detail, one mood. A \
phone-scrolling stranger should feel something they were trying not to feel. If you \
need more than one sentence to describe what the viewer sees at any given moment, \
the scene is too complex. If text appears in the image (a sign, a label, a \
headline), it must be ONE short phrase — five words maximum, large enough to read \
on a phone thumbnail. Text is an anchor into the story, not decoration.

Your scripts blend three comedy traditions:

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

The gold standard: the viewer genuinely cannot tell if this is real or a joke \
until they look it up. When reality is indistinguishable from satire, you've \
found the richest vein.

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

**STEP 1 — SHARPEN YOUR ANGLE**

Before writing any loglines, analyze the story. A topic is not an angle. \
"AI regulation" is a topic. "The committee regulating AI can't open a PDF" is \
an angle. Find the angle.

Output a `story_hook` object with:
- `topic`: the broad subject area
- `angle`: the specific absurd detail or tension that makes this story funny
- `conflict`: who/what vs who/what — every funny story has a tension
- `stakes`: who loses, what breaks, what's absurd about the outcome
- `surprise`: what most people don't realize or won't say out loud about this

**STEP 2 — WRITE THREE LOGLINES**

Each logline must take a DIFFERENT approach. Each approach must identify the \
*specific feeling people are avoiding* about this news and build the comedy \
around naming that feeling:

1. **observational** — Find the uncomfortable truth everyone's politely ignoring. \
What's the thing people feel but won't say out loud? The embarrassment, the guilt, \
the quiet dread? Billy states it flatly and the audience laughs because they've been \
caught. The comedy is in the relief of finally hearing it said. Dry, understated, \
no invented characters beyond Billy and at most one other person.
2. **satirical** — Expose the hypocrisy or contradiction that a powerful entity \
would prefer you didn't notice. What's the gap between what's being said and what's \
actually happening? Billy reframes it through one clean analogy that makes the \
contradiction undeniable. The laugh comes from the catharsis of seeing the lie named.
3. **metaphorical** — Find the one image that's almost offensive in how accurate \
it is. What visual captures the feeling people are swallowing — the absurdity, the \
futility, the cognitive dissonance? The image should trigger recognition: "oh god, \
that's exactly what this is." Simple, still, XKCD-style.

**ANTI-PATTERNS** (if you catch yourself doing these, start over):
- Writing a vague observation about a broad topic instead of a pointed take on a \
specific detail (information dump)
- Describing "a thing that happened" without stakes or conflict (no-stakes pitch)
- Hedging or being balanced — take a position on why the news is absurd
- Being so inside-baseball that a normal person wouldn't get it

**THE DINNER TABLE TEST**: Each logline should work as a one-sentence pitch at a \
dinner party that makes someone snort-laugh and say "wait, really?"

For each logline, include:
- `news_essence`: 1-2 sentences capturing what actually happened in the real world \
(just the facts, no comedy). This grounds the episode — without it, the comedy \
disconnects from reality.
- `text`: the logline itself (1-2 sentences, sets up the episode premise)
- `approach`: "observational" | "satirical" | "metaphorical"
- `featured_characters`: list of character names from the profiles above that appear
- `visual_hook`: one key STILL IMAGE that works as a poster — a single frozen \
moment with Billy and at most one other figure that contains a visual riddle \
(scale distortion, impossible juxtaposition, symmetry break, frame-within-frame, \
or material contradiction). THREE elements maximum: subject, context, one detail. \
Must be instantly readable at phone size and describable in one sentence.

Each logline must contain enough information that someone unfamiliar with this \
headline understands the basic story. The comedic premise should arise from the \
real news — not replace it with an unrelated scenario.

The characters are field correspondents — every logline must place them \
physically at the scene of the news story, not in a studio. Each logline must \
feature Billy and AT MOST one other character. Crowds, montages, and multiple \
simultaneous actors are not producible — keep it to two people talking.

Return as a JSON object with keys:
- `story_hook`: object with keys: topic, angle, conflict, stakes, surprise
- `loglines`: array of 3 objects with keys: text, approach, featured_characters, \
visual_hook, news_essence
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
1. **News clarity** — does the logline make the underlying news story understandable? \
The news must land for the comedy to land.
2. **Comedy punch** — does it make you laugh or at least exhale sharply? Would you \
share it? Does it name a feeling people are avoiding? A logline that makes you feel \
something beats one that merely informs.
3. **Point of view** — does it take a stance? Edgy > safe. A pointed observation \
that names what people are thinking but not saying beats a neutral summary.
4. **Specificity** — concrete details over abstractions. A specific number, name, \
or detail beats a generality. "The committee" < "the 74-year-old senator."
5. **Simplicity** — can each scene be captured as a single still photograph with \
one clear subject? Fewer actors and simpler visuals score higher.
6. **Character fit + visual feasibility** — does it use Billy naturally? At most \
one other character, with three or fewer visual elements. Can an image model render \
the key moment as one clean image? Reject montages, recursive effects, crowds, and \
abstract concepts.

Return a JSON object with:
- `selected_index`: 0, 1, or 2 (which logline to use)
- `reasoning`: 1-2 sentences explaining why

If none of the three loglines passes visual feasibility (criterion 5), \
select the closest and note the issue in reasoning.
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
- **setup**: Don't just establish facts — establish *stakes*. Who's losing? What's \
broken? What's the uncomfortable question nobody's asking? The viewer should \
immediately feel "oh no" or "wait, what?" One prop or visual detail establishes \
where we are. Billy + at most one other person. Viewer understands both the basic \
facts AND why they should care by end of this act.
- **development**: The reframing should make the viewer slightly uncomfortable \
because it's *too accurate*. Not a gentle analogy — a pointed comparison that \
exposes the absurdity. Think: the angle that turns a topic into a story. Frame \
the reframing around a MACRO CONTRADICTION — tradition vs progress, individual \
vs collective, stated values vs revealed preferences, aspiration vs capability. \
The best comedy comes from tensions that existed before this news story and will \
exist after it. The news item is just the latest symptom. Same \
location. Same characters. The humor comes from naming what everyone's thinking \
but nobody's saying.
- **punchline**: Should land like a gut punch, not a gentle observation. The \
viewer should wince and laugh simultaneously. Aim for the line people quote to \
their friends the next day. Landing, not escalation — but a landing that stings. \
Then pull back 20%. The viewer's own projection fills the gap, and their version \
is always worse. A half-stated implication lands harder than a fully spelled-out \
shock. If the last line explains the joke, cut the explanation.

Billy stays in ONE physical location throughout. No location changes between scenes.

This synopsis becomes a single 15-second scene. All three acts happen within \
that one continuous shot. Each act = 2-3 sentences, not paragraphs. Think \
single-panel cartoon with a caption — then add one slow camera move.

Also provide:
- **estimated_scenes**: always 1
- **key_visual_gags**: list of 1-2 VISUAL RIDDLES — paradoxical, impossible, or \
contradictory details that reward a second look. Each must be a single static \
element visible in a still image (a prop, a scale distortion, a short label, an \
expression) — not a sequence of events or a montage. If the gag uses text, five \
words maximum. Think "this image would work as a poster" at phone size — identify \
the joke from shapes alone.
- **news_explanation**: in 2-3 sentences, what is the real-world news story this \
episode explains?

Return as JSON with keys: setup, development, \
punchline, estimated_scenes, key_visual_gags, news_explanation, \
news_explanation_check.
- `news_explanation_check`: boolean — true if your news_explanation would let \
someone who never heard this headline understand the basic story.
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
- Development: {development}
- Punchline: {punchline}

**Key visual gags to include**: {visual_gags}

**CREATIVE DIRECTION**:

**NON-NEGOTIABLE** (pipeline breaks if violated):
- scene_prompt describes a SINGLE PHOTOGRAPH — one subject, one background, one \
visual detail. THREE distinct visual elements total, no more. Count them before \
writing. If you count 4+, remove the weakest.
- If text appears in the scene (a sign, label, headline), ONE phrase maximum, five \
words or fewer, positioned prominently and large enough to read on a phone.
- Maximum 2 characters visible in the scene. Never add crowds, montages, groups, \
or background actors doing things.
- Billy stays in ONE location for the entire episode. Every scene has the same background.

**CORE** (standard quality):
- Every episode is a news explainer. The scene must establish what happened. By \
the end, the viewer understands: who did what, why it matters, why it's absurd.
- Dialogue is the primary vehicle for both comedy and exposition. Billy talks \
to camera or to one other person. 2-3 short lines per scene (1-2 seconds each).
- Scene structure: one continuous 15-second shot. The scene opens with the \
news setup, develops through one reframing analogy, and lands on a closing observation.

**STYLE** (creative polish):
- Visual comedy = ONE prop, short sign, or background detail per scene — this \
IS the visual riddle, not an addition. The gap between what Billy calmly \
says and one absurd detail visible behind him IS the comedy.
- Keep the plot simple and direct. One clear comedic premise, developed once, \
resolved with a quiet insight.
- When dialogue IS included, write it as spoken lines with character attribution \
— the video model generates audio natively from quoted dialogue in scene_prompt.

**VISUAL PHILOSOPHY** (what makes someone feel the suppressed emotion):
- Every scene must surface a feeling the viewer is already carrying but hasn't \
named — unease, guilty amusement, quiet dread, reluctant recognition. The image \
alone, with zero context about the news story, should make someone feel something \
they were trying not to feel.
- Test: would a stranger scrolling past this image on a phone feel a flicker of \
unwanted recognition, even without knowing the headline?
- Every scene must contain a **VISUAL RIDDLE** — one detail that contradicts, \
distorts, or recontextualizes the main subject. The visual riddle IS the "one \
visual detail" from the NON-NEGOTIABLE rules, not a separate element. The viewer \
should look twice. The riddle must be identifiable from shapes and scale alone — \
fine details that vanish at phone size don't count. Strategies (pick ONE per scene):
  - **Scale paradox**: the subject is impossibly large or small relative to its \
context (a twelve-meter-tall rubber duck, a CEO dwarfed by his own signature)
  - **Wrong context**: the subject plainly does not belong in its setting — one \
figure or object in a place that makes the viewer double-take. The riddle is the \
*relationship* between subject and context, not a third element.
  - **Symmetry break**: near-perfect visual order disrupted by one element \
(a pristine row of identical suits with one on fire)
  - **Frame-within-frame**: a screen, window, or mirror that comments on the main \
scene. If using text inside the frame, five words maximum. The frame is the context \
layer, not a third element.
  - **Material contradiction**: an object made of the wrong substance or in the \
wrong state (a gavel made of rubber, a server rack built from cardboard, a trophy \
that's melting)
  - The strongest riddles IMPLY rather than SHOW. Smoke is funnier than fire. An \
empty chair at a full table is funnier than a missing person. A shadow that's the \
wrong shape is funnier than a misshapen figure. If you can replace a direct \
depiction with a trace, consequence, or residue of the thing, do it — the \
viewer's imagination fills the gap, and their version is always worse.
- **Instant-read test**: blur the image to 100×100 pixels in your mind. Can you \
still identify the subject, the context, and the riddle? If not, simplify.
- Use simple **spatial language**: "centered," "standing small against," "towering \
above," "filling the frame." Avoid film jargon.
- Design for **9:16 vertical format**: strong vertical lines, overhead elements \
that use the tall frame, one subject clearly readable at phone size.

**DIALOGUE PACING** (the exponential curve):
- Dialogue follows an exponential curve: slow and accessible at the start, sharp \
and quotable at the end. Three lines, three gears:
  - **Line 1 — Context**: what happened, stated simply. A viewer who missed the \
headline catches up here. Calm, factual, almost dry.
  - **Line 2 — Reframing**: the angle that makes the viewer see the story \
differently. An analogy, a comparison, a quiet observation that shifts the ground.
  - **Line 3 — Punchline**: the line people text to friends. Short, edgy, lands \
like a gut punch — then pull back 20%. Let the viewer's mind complete the thought. \
An implication stings harder than a declaration. If the punchline explains itself, \
cut the explanation. The pause after the line IS the punchline.
- Each line must be independently understandable — no callbacks to previous lines \
that fail without context.
- Test: read only line 3. Does it work as a standalone caption? If not, sharpen it.

Write 1 scene. For each scene provide:

- `scene_number`: integer (1-based)
- `scene_title`: short descriptive title
- `setting`: location, time of day, atmosphere
- `scene_prompt`: 60-100 words describing a SINGLE FROZEN MOMENT — what a camera \
would capture in one photo. Do not describe sequences of events, montages, or \
things happening "then". \
Front-load the KEY VISUAL (most striking element) in the first 20-30 words, \
then layer: subject position in frame → context → visual riddle (which IS the one \
detail) → lighting/atmosphere → dialogue. \
Affirmative descriptions ONLY — no negative prompts (never say "no", "without", \
"don't", "avoid"). \
If text appears on a sign or label, write it in ALL CAPS in the prompt and keep \
it to five words. \
Include character visual details from profiles (clothing, colors, features). \
If the scene has dialogue, include it as quoted speech with character attribution \
directly in the prompt (e.g. '[Character] says: "[line]"'). \
Maximum 2 characters visible. Maximum 1 prop or background detail that carries \
comedic weight — the visual riddle counts as this one detail.
- `dialogue`: array of 3 objects with "character" and "line" keys. Line 1 = \
context (what happened), Line 2 = reframing (the angle), Line 3 = punchline \
(quotable standalone). Each line gets shorter and sharper.
- `visual_gag`: ONE paradoxical, contradictory, or impossible-yet-meaningful \
detail that rewards a second look — visually striking AND conceptually connected \
to the news story. Describable in a single still image (or null). Not a sequence \
of events.
- `audio_direction`: music, sound effects, ambient sounds, and dialogue delivery notes
- `duration_seconds`: 15
- `camera_movement`: ONE simple camera movement or a slow progression (e.g. \
"slow zoom in", "static → gentle pan"). Prefer subtle, unhurried moves suited \
to a 15-second continuous shot.

**Example output** (fictional topic — adapt structure, not content):
{{
  "title": "The Rubber Gavel",
  "scenes": [{{
    "scene_number": 1,
    "scene_title": "Order in the Sandbox",
    "setting": "Children's playground, overcast afternoon, muted grey light",
    "scene_prompt": "A three-meter-tall rubber gavel towers over a small \
playground sandbox where Billy in his beige suit stands looking up at it, \
dwarfed. Behind the sandbox, a chain-link fence stretches across the frame. \
A hand-painted sign on the fence reads 'COURT IN SESSION' in large block \
letters. Overcast grey sky. Billy says: 'The Supreme Court just ruled that \
AI-generated evidence is admissible.' A young judge in an oversized black \
robe sits cross-legged in the sandbox, stamping documents with a toy hammer. \
The judge says: 'The precedent was set by a chatbot.' Billy says: 'Justice \
is blind. Now it's also imaginary.'",
    "dialogue": [
      {{"character": "Billy", \
"line": "The Supreme Court just ruled that AI-generated evidence is admissible."}},
      {{"character": "Judge", \
"line": "The precedent was set by a chatbot."}},
      {{"character": "Billy", \
"line": "Justice is blind. Now it's also imaginary."}}
    ],
    "visual_gag": "a three-meter rubber gavel looming over a sandbox courtroom \
— the scales of justice rendered in playground proportions",
    "audio_direction": "distant playground ambience, slow gavel thud, deadpan delivery",
    "duration_seconds": 15,
    "camera_movement": "slow zoom in from gavel top to sandbox level"
  }}],
  "end_card_prompt": "Show logo over faded playground asphalt texture",
  "characters_used": ["Billy"],
  "compliance_check": {{
    "single_scene": true,
    "max_two_characters": true,
    "photograph_test": true,
    "news_explained": true,
    "word_count_ok": true,
    "visual_riddle_present": true,
    "instant_read": true,
    "no_text_overflow": true,
    "dialogue_curve": true
  }}
}}

Also provide an `end_card_prompt` (50-100 words): a final scene prompt for the \
episode end card showing the show logo/title.

Before returning, verify your output against this checklist:
- `single_scene`: exactly 1 scene in the scenes array
- `max_two_characters`: at most 2 characters visible in scene_prompt
- `photograph_test`: scene_prompt describes one frozen moment, not a sequence
- `news_explained`: a viewer would understand what happened in the real world
- `word_count_ok`: scene_prompt is 60-100 words
- `visual_riddle_present`: visual_gag contains a scale paradox, wrong context, \
symmetry break, frame-within-frame, or material contradiction — not just a funny prop
- `instant_read`: blur to 100×100 pixels — identify subject, context, riddle from \
shapes alone
- `no_text_overflow`: any text in the scene is one phrase, five words max, \
positioned prominently
- `dialogue_curve`: line 1 sets context, line 2 reframes, line 3 is quotable standalone

If any check fails, revise the scene before returning.

Return as JSON with keys:
- `title`: episode title
- `scenes`: array of scene objects
- `end_card_prompt`: string
- `characters_used`: list of character names that appear
- `compliance_check`: object with boolean keys: single_scene, max_two_characters, \
photograph_test, news_explained, word_count_ok, visual_riddle_present, instant_read, \
no_text_overflow, dialogue_curve
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
