# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cartoon Maker is an AI-powered pipeline that automatically discovers trending topics from social media, writes comedy scripts, generates static shots, produces final cartoon videos, and adds whisper-based captions. The pipeline is composed of five independent agents that run sequentially.

## Architecture

The project follows a modular agent-based architecture. Each agent is a self-contained module with its own directory, logic, and dependencies:

```
cartoon_maker/
├── shared/              # Cross-agent utilities: data contracts, config, logging
├── agent_researcher/    # Stage 1: Trend discovery & filtering  [IMPLEMENTED]
├── script_writer/       # Stage 2: Script creation pipeline     [IMPLEMENTED]
├── static_shots_maker/  # Stage 3: Static shot generation       [IMPLEMENTED]
├── video_designer/      # Stage 4: Video assembly & final output [IMPLEMENTED]
├── caption_maker/       # Stage 5: Whisper-based video captions  [IMPLEMENTED]
```

### Agent Pipeline (sequential flow)

1. **agent_researcher** — Scans 7 sources across 3 tiers, deduplicates, scores via Claude Opus for comedy potential, and outputs a ranked daily brief.

2. **script_writer** — Reads the daily brief JSON sidecar, generates 3 loglines per item (absurdist/satirical/surreal), selects the best, expands to synopsis + full script with scene-by-scene breakdown. Requires character profiles and art style (created via interactive setup tool).

3. **static_shots_maker** — Reads script JSONs, uses Claude to rewrite video prompts into image-optimized prompts, generates 9:16 PNGs via Gemini, outputs shots + manifest per script.

4. **video_designer** — Reads static shots + script JSONs, uses Claude to compose video prompts, generates 15s clips via xAI grok-imagine-video (with native audio), assembles with glitch transitions into final cartoon videos.

5. **caption_maker** — Transcribes spoken audio from generated videos via OpenAI Whisper API, generates ASS subtitles with cumulative word reveal, and burns styled captions into videos via ffmpeg. Requires `OPENAI_API_KEY`.

### Design Principles

- Each agent is developed and configured independently
- Agents communicate through well-defined data contracts (output of one feeds into the next)
- Each agent directory should contain its own README, configuration, and tests

## Development

### Package Manager

This project uses [uv](https://docs.astral.sh/uv/) for Python package management.

```bash
# Create/activate venv
uv venv
source .venv/bin/activate

# Add a dependency
uv add <package>

# Sync dependencies (runtime only)
uv sync

# Sync with dev tools (pytest, ruff, pre-commit)
uv sync --extra dev
```

Dependencies are managed in `pyproject.toml` (not requirements.txt).

### Testing & Linting

Always use `.venv/bin/` prefixed commands (not `source .venv/bin/activate && ...`) — the direct binary paths are pre-approved in permission settings and won't prompt for approval.

```bash
# Run all tests (221 tests)
.venv/bin/pytest tests/ -v

# Run a single test file
.venv/bin/pytest tests/test_dedup.py

# Run a single test
.venv/bin/pytest tests/test_dedup.py::TestDedupAndFilter::test_url_dedup_merges_sources -v

# Lint
.venv/bin/ruff check .

# Format
.venv/bin/ruff format .
```

Pre-commit hooks run ruff (lint + format) and pytest on every commit.

Test object factories (`make_raw_item`, `make_scored_item`, `make_script`, etc.) live in `tests/conftest.py` — never duplicate these across test files.

### Running Agents

```bash
# Agent Researcher — one-shot run
uv run python -m agent_researcher

# Agent Researcher — scheduled daily run (default 07:30)
uv run python -m agent_researcher --scheduled

# Script Writer — character & art style setup (interactive, run once)
uv run python -m script_writer.setup

# Script Writer — generate art materials (run after characters + art style exist)
uv run python -m script_writer.setup art-materials

# Script Writer — generate scripts from latest brief
uv run python -m script_writer

# Script Writer — generate scripts from specific date
uv run python -m script_writer --date 2026-03-14

# Script Writer — generate scripts for specific news items from brief (1-based numbers)
uv run python -m script_writer --pick 1,3,7

# Static Shots Maker — generate shots from latest scripts
uv run python -m static_shots_maker

# Static Shots Maker — generate shots from specific date
uv run python -m static_shots_maker --date 2026-03-15

# Video Designer — generate videos from latest static shots
uv run python -m video_designer

# Video Designer — generate videos from specific date
uv run python -m video_designer --date 2026-03-15

# Caption Maker — add captions to latest videos
uv run python -m caption_maker

# Caption Maker — add captions for specific date
uv run python -m caption_maker --date 2026-03-15
```

### Config

Environment variables loaded from `.env` (see `.env.example` for template). Missing optional credentials cause graceful source skipping, not crashes.

Required: `ANTHROPIC_API_KEY` (without it, scorer falls back to raw score sorting — no comedy angles).

Required for static shots: `GOOGLE_API_KEY` (Gemini image generation). Required for video: `XAI_API_KEY` (xAI grok-imagine-video). Optional: `ANTHROPIC_API_KEY` enables Claude prompt rewriting (falls back to regex stripping for shots, original prompts for video). Required for captions: `OPENAI_API_KEY` (OpenAI Whisper API). Optional: `WHISPER_MODEL` (default: `whisper-1`).

## Code Conventions

- Cross-module utilities (parsing, formatting, HTTP helpers) go in `shared/utils.py` — never duplicate logic across agent modules
- Image media type: use `detect_image_media_type()` from `shared/utils.py` — detects format from file magic bytes. Never hardcode `image/png` or other MIME types based on file extension
- LLM JSON responses may be wrapped in code fences: use `strip_code_fences()` from `shared/utils.py`
- ISO timestamps with `Z` suffix: use `parse_iso_utc()` from `shared/utils.py`
- Constants, lookup dicts, and compiled regexes belong at module level, not inside functions
- Each piece of logic has one owner module — if a second copy appears, extract to `shared/`
- Error handling and resource setup (fallback logic, directory creation) belong in the module that owns the operation — callers should not duplicate these concerns
- Avoid pre-checking file/resource existence before operating (TOCTOU anti-pattern) — call the operation directly and handle the error
- LLM calls: use `call_llm_json(client, prompt, model, max_tokens)` from `shared/utils.py` — handles streaming, text extraction, code fence stripping, and JSON parsing. Use `call_llm_text()` for raw text responses. Both support optional `images` kwarg (`list[Path]`) for multimodal inputs. Create a single `anthropic.Anthropic` client per pipeline run and pass it through.
- LLM response text extraction: use `extract_text(response)` from `shared/utils.py` for non-JSON responses
- Context loading: use `shared/context_loader.py` for loading characters + art style (shared by script_writer and static_shots_maker)
- Dataclass serialization: use `asdict()` with post-processing for non-serializable fields (dates, Paths). Never hand-build the dict — fields added later would be silently dropped. Add a `from_dict()` classmethod for any dataclass that is serialized to JSON — consumers should not hand-parse

## Agent Researcher Internals

Pipeline: parallel source fetch (50-item cap per source) → URL validation → dedup/freshness filter → cross-day history filter → LLM scoring (Claude Opus with adaptive thinking, 3 retries with exponential backoff) → Markdown brief + optional Notion delivery.

### Sources (7 total, 3 tiers)

| Source | Tier | Auth | Module |
|--------|------|------|--------|
| Hacker News (Algolia API) | validation | None | `sources/hackernews.py` |
| RSS (arXiv cs.AI/cs.RO/q-bio, bioRxiv) | context | None | `sources/rss.py` |
| Manifold Markets (prediction markets) | validation | None | `sources/prediction_markets.py` |
| X/Twitter (xAI Grok with `web_search`) | discovery | `XAI_API_KEY` | `sources/xai.py` |
| Reddit (r/LocalLLaMA via PRAW) | discovery | `REDDIT_CLIENT_ID` + `SECRET` | `sources/reddit.py` |
| Product Hunt (GraphQL + OAuth) | discovery | `PRODUCT_HUNT_API_KEY` + `SECRET` | `sources/producthunt.py` |
| Bluesky (AT Protocol search) | discovery | `BLUESKY_HANDLE` + `APP_PASSWORD` | `sources/bluesky.py` |

Tier freshness cutoffs: discovery/validation = 24h, context = 48h.

All sources must return items with valid URLs. Items with empty URLs are filtered out at source level and as a safety net in the runner before dedup.

### Key modules

- **Source Protocol** (`sources/base.py`): synchronous `fetch() -> list[RawItem]`. Runner parallelizes via `asyncio.to_thread()`.
- **Dedup** (`dedup.py`): URL normalization + `rapidfuzz` title similarity (threshold 85). Merges multi-source items rather than discarding. Empty URLs are excluded from URL dedup to prevent false collisions. `filter_already_covered()` provides cross-day dedup by scanning previous brief JSON sidecars (7-day lookback) and dropping items that match by normalized URL or fuzzy title.
- **Scorer** (`scorer.py`): streams to `claude-opus-4-6` with adaptive thinking, 32k max tokens. Retries up to 3 times with exponential backoff (5s, 10s, 20s) on API or JSON parse failures. Rewrites titles for clarity, generates comedy explanations for every item. Falls back to raw score sorting (with visible warning) if all retries exhausted or API key missing. `comedy_angle` uses enriched three-part format: structural contradiction (what's said vs what's happening), double emotional hit (two contradictory emotions), and one-liner joke seed. This propagates to all downstream script prompts. Scoring uses `broad resonance` (replaces `cultural_resonance`) to favor stories accessible to non-technical audiences. Semantic dedup via `duplicate_of` field: Claude flags items covering the same event, Python code merges sources into the canonical item and drops duplicates before ranking.
- **xAI source** (`sources/xai.py`): uses `grok-4.20-beta-latest-non-reasoning` with `web_search(allowed_domains=["x.com"])` tool for live X data.
- **Data contracts** (`shared/models.py`): `RawItem` → `ScoredItem` → `ComedyBrief` → `Logline` (includes `format_type`) → `Synopsis` (includes `world_seed: str = ""` for place history/sensory detail) → `SceneScript` (11 fields, includes `transformation: str = ""`, `billy_emotion: str = ""`) → `CartoonScript` (includes `format_type`) → `ShotResult` → `ShotsManifest` → `ClipResult` → `VideoManifest`. All agents share these. `Synopsis.from_dict()` accepts both `development` and legacy `escalation` keys for backward compatibility. `SceneScript.from_dict()` handles missing optional fields with backward compat defaults. `Logline.format_type` and `CartoonScript.format_type` default to `""` for backward compatibility.
- **Shared ffmpeg** (`shared/ffmpeg.py`): `run_ffmpeg()`, `probe_video()`. Extracted from video_designer assembler for reuse by caption_maker.
- **Shared utilities** (`shared/utils.py`): `strip_code_fences()`, `parse_iso_utc()`, `strip_html()`, `extract_text()`, `extract_json()`, `call_llm_json()`, `call_llm_text()`. `extract_json(text, expect=dict|list)` handles LLM responses with surrounding commentary by trying direct parse then bracket extraction.
- **Context loader** (`shared/context_loader.py`): `load_characters()`, `load_art_style()`, `load_art_materials()`, `build_context_block()`, `build_reference_image_list()`. Used by script_writer, static_shots_maker, and video_designer.
- **Delivery** (`delivery/`): local `.md` file (always) + Notion page (if `NOTION_API_KEY` configured).
- **Alerts** (`alerts.py`): Slack webhook notifications on success/failure. Gated on `SLACK_WEBHOOK_URL`.
- **Scheduler** (`scheduler.py`): APScheduler `CronTrigger` for daily runs. Activated via `--scheduled` flag.
- **Output**: `output/briefs/YYYY-MM-DD.md` + `.json` sidecar + optional Notion page.

## Script Writer Internals

Pipeline: brief JSON ingestion → parallel logline generation + selection (all items concurrent) → parallel script expansion (synopsis + full script) → .md + .json output. Single `anthropic.Anthropic` client shared across all LLM calls.

### Pipeline stages

- **Brief reader** (`pipeline/brief_reader.py`): Reads `output/briefs/YYYY-MM-DD.json` sidecar. Auto-detects latest date if none specified.
- **Context loader** (`shared/context_loader.py`): Loads `output/characters/*.md` and `output/art_style.md` into a shared prompt context block.
- **Logline generator** (`pipeline/logline_generator.py`): Structured "angle sharpening" (`story_hook` analysis, including `avoided_feeling`) before generating 3 loglines per news item. Three approaches produce different comedic rhythms: (1) the_quiet_part — the uncomfortable truth nobody is saying, confession comedy; (2) the_betrayal — the audacious lie exposed, recognition comedy; (3) the_image_you_cant_unsee — one visual that permanently reframes the story, New Yorker cartoon energy. Comedy_angle from scorer is treated as a starting point, not the answer — loglines must find a sharper take. TASTE section enforces: wit over spectacle, implication over statement, one idea perfectly executed, New Yorker single-panel test. `text` field must be ONE sentence sharp enough to be a tweet. `visual_hook` is one image, one idea, one sentence — not a shot list. Each logline specifies a `format_type` (visual_punchline / exchange / cold_reveal / demonstration). Uses Claude Opus with adaptive thinking. Response format: `{"story_hook": {...}, "loglines": [...]}` — parser extracts `loglines` array with `format_type`, `story_hook` exists only to improve quality.
- **Logline selector** (`pipeline/logline_selector.py`): Selects best 1 of 3 per item. Prioritizes funny AND clear (both required), then emotional hit, emotional hit, specificity, format fit, and visual feasibility. Displays `format_type` in formatted output. Falls back to first logline on error.
- **Script expander** (`pipeline/script_expander.py`): Two-step: synopsis (with `world_seed` for place/atmosphere) → full script. All 5 items run in parallel via `asyncio.gather()`. `world_seed` threads from synopsis into script expansion prompt for richer settings.
- **Renderer** (`pipeline/renderer.py`): `CartoonScript` → `.md` (human-readable) + `.json` (machine-readable for static_shots_maker).
- **Prompts** (`prompts.py`): All prompt templates. Core rules: (1) Billy SAYS the news fact in PLAIN LANGUAGE — no jargon, no assumed knowledge; (2) dialogue must be FUNNY, not just factual — every line does double duty (information + comedy). WHAT MAKES DIALOGUE FUNNY section teaches three tools: the reframe (framing the fact so its absurdity is undeniable), the turn (conversation goes somewhere unexpected), the committed position (other character earnestly believes something absurd). Anti-patterns: dialogue that only states facts, both characters agreeing, Billy sounding like a news anchor, last line explaining the joke, using jargon. Last line test: does the final line land as a punchline? Could you put it on a t-shirt? Logline selection #1 criterion: "Funny AND clear — both required, neither optional." Gold standard: Billy says one line and you laugh, then you see the image and laugh harder — both independently funny, together devastating. Shared humor preamble establishes 4 episode formats: (1) Visual Punchline — 1-2 lines, Billy frames fact as comedy, image amplifies; (2) Exchange — 2-4 lines, other character commits earnestly to absurd position; (3) Cold Reveal — 1 line at end names the news fact AND lands as punchline; (4) Demonstration — Billy states fact, transformation illustrates absurdity. Billy's emotional range: NOT always "quiet" — frustrated, amused, alarmed, delighted, angry, giddy, genuinely surprised. Other characters must COMMIT to their position — the more earnestly they believe, the funnier. They should never sound like they know they're in a comedy. Three comedy traditions (dry observation, deadpan absurdism, quiet irony) preserved. Material specificity preserved (in painterly muted world, not B&W stickman). CRITICAL visual rule: `scene_prompt` = starting state photograph, NO art technique words. Scene prompt rules: OBJECTS, SCALE, MATERIALS, WRONGNESS, BILLY'S STATE. `news_essence` must be plain language. NEWS DELIVERY: dialogue AND image both deliver comedy. Mute test: can't understand news on mute, unmute delivers news AND laughs. Compliance_check includes `dialogue_is_funny`, `news_delivered`, `plain_language`, `format_consistency`, `visual_specificity_check`, `emotion_specified`. 4 format-specific examples. `comedy_angle`, `snippet`, `news_explanation`, `format_type` passed through.
- **Runner** (`pipeline/runner.py`): Async orchestrator for the full pipeline. Supports `--pick` flag to select specific items by 1-based brief number (top_picks + also_notable). When `comedy_angle` is empty (scorer fallback), downstream prompts instruct the LLM to discover the comedy angle from scratch.

### Setup tool

- **Interviewer** (`setup/interviewer.py`): Generic multi-turn LLM conversation engine. Detects `INTERVIEW_COMPLETE` marker.
- **Character builder** (`setup/character_builder.py`): Interactive character design interview → `output/characters/<name>.md`.
- **Art style builder** (`setup/art_style_builder.py`): Interactive art style interview → `output/art_style.md`.
- **Art materials builder** (`setup/art_materials_builder.py`): Automated (non-interactive) generation of canonical reference images via Gemini → `output/art_materials/canonical_characters.png`. Requires `GOOGLE_API_KEY`. Run separately after characters + art style exist.

### Output

- `output/scripts/<YYYY-MM-DD>_<N>.md` + `.json` — one pair per top pick (N = 1-5).
- Scene prompts: 60-100 words describing the STARTING STATE — one frozen photograph composed for emotional impact. NO art technique words (crosshatching, ink-wash, etc. banned). Describes OBJECTS (specific names), SCALE, MATERIALS, THE WRONGNESS, BILLY'S STATE. Affirmative only, front-loaded key visuals. 4-5 visual elements (subject, context, 2-3 detail elements). `transformation` field (30-60 words) used for demonstration format only, empty string for others. `billy_emotion` specifies Billy's emotional state per scene (not always deadpan). Dialogue count varies by `format_type`: 1-2 for visual_punchline, 2-4 for exchange, 1 for cold_reveal, 1-2 for demonstration. Billy must state the news fact in at least one line across all formats. Each scene must surface a suppressed feeling and contain a VISUAL RIDDLE. Duration fixed at 15 seconds. 1 scene per script. Maximum 2 characters per scene. Billy stays in one location throughout.

## Static Shots Maker Internals

Pipeline: script JSON ingestion → sequential prompt rewriting + image generation per script (for visual continuity) → PNG output + manifest. Script-level parallelism preserved, scene-level is sequential (each scene uses previous scene's output as reference).

### Pipeline stages

- **Script reader** (`pipeline/script_reader.py`): Reads `output/scripts/<date>_<N>.json` sidecars. Auto-detects latest date if none specified. Uses `CartoonScript.from_dict()`.
- **Prompt generator** (`pipeline/prompt_generator.py`): Claude rewrites video-oriented scene prompts into static image prompts (strips motion/audio/duration, picks peak visual moment, weaves in character details + art style). Falls back to regex stripping if Claude unavailable.
- **Image generator** (`pipeline/image_generator.py`): Gemini `gemini-3.1-flash-image-preview` generates 9:16 PNGs. Accepts optional `reference_images` (art materials + previous scene) for visual consistency.
- **Prompts** (`prompts.py`): `SCENE_TO_IMAGE_PROMPT` and `END_CARD_TO_IMAGE_PROMPT` templates. Rules tiered as CRITICAL/COMPOSITION/REQUIRED/FORMAT. `SCENE_TO_IMAGE_PROMPT` accepts `{format_type}` placeholder (passed as `script.format_type or "standard"`). Editorial illustrator role focused on emotional distillation for phone screens. Includes comedy-awareness context and starting-state directive: scene prompt = pre-transformation state, render objects in original untransformed form. Texture preservation rule: hyper-detailed focal object against painterly atmospheric world is deliberate comedy. CRITICAL section enforces text constraint (one phrase, five words max). COMPOSITION section: composition hierarchy (eye path design), 4-5 elements (subject, context, 2-3 detail elements — extra objects are transformation targets in original form, load-bearing for video stage), object specificity (preserve exact names), scale relationships (preserve exact measurements), THE WRONGNESS (absurd element must be visually prominent at phone size), format awareness (visual_punchline/cold_reveal need extra clarity for zero-dialogue jokes), VISUAL HIERARCHY (one element with more detail/weight than surroundings). Two-layer depth, simple framing language. FORMAT: 70-100 word output range. Cuts generic adjectives but preserves material adjectives. Strips dialogue. References art materials and previous scene for consistency.
- **Runner** (`pipeline/runner.py`): Async orchestrator. Level 1 parallel across scripts, scenes sequential within each script (visual continuity chain). Loads art materials as reference images.

### Output

- `output/static_shots/<YYYY-MM-DD>_<N>/scene_<M>.png` + `end_card.png` + `manifest.json` per script.
- `manifest.json` records success/failure per shot for `video_designer` to consume.

## Video Designer Internals

Pipeline: manifest + script ingestion → parallel video prompt composition (Claude, includes dialogue formatting) → parallel video generation (xAI grok-imagine-video with native audio) → ffmpeg assembly with glitch transitions. Two-level `asyncio.gather()` with semaphore for rate limiting.

### Pipeline stages

- **Manifest reader** (`pipeline/manifest_reader.py`): Reads `output/static_shots/<date>_<N>/manifest.json` + pairs with `output/scripts/<date>_<N>.json`. Auto-detects latest date. Skips scripts with no successful shots.
- **Prompt generator** (`pipeline/prompt_generator.py`): Claude composes video-generation prompts from scene details + character profiles + art style + formatted dialogue. Sends the static shot image alongside the text prompt (multimodal) so Claude can reference the actual rendered frame. Falls back to original scene_prompt if Claude unavailable.
- **Video generator** (`pipeline/video_generator.py`): xAI grok-imagine-video (`grok-imagine-video`) image-to-video with native audio generation. Uses static shot as source image via base64 data URI. SDK handles polling internally.
- **Assembler** (`pipeline/assembler.py`): ffmpeg concatenation with re-encoding (`libx264 + aac`) for audio normalization. Glitch transitions (0.5s) with silence between scripts. Uses `run_ffmpeg()` and `probe_video()` from `shared/ffmpeg.py`.
- **Prompts** (`prompts.py`): `SCENE_TO_VIDEO_PROMPT` and `END_CARD_TO_VIDEO_PROMPT` templates. Rules tiered as CRITICAL/REQUIRED/FORMAT. Include audio/dialogue direction, `{transformation}`, `{format_type}`, and `{billy_emotion}` inputs. CRITICAL section: format-aware motion direction — `visual_punchline` (environment moves, Billy still, accumulation is comedy), `exchange` (character body language drives motion, dialogue timing primary), `cold_reveal` (camera movement IS the story, slow reveal), `demonstration` (one deliberate gesture, casual gesture / impossible result). Timing follows the format's rhythm, not a rigid 5-5-5 split. Ambient world wrongness complements primary motion. REQUIRED section: Billy's body language matches his emotion (not always "barely moves"), other character: 2-3 natural motions, environment: 2-3 uncanny motions complementing the scene.
- **Runner** (`pipeline/runner.py`): Async orchestrator. Level 1 parallel across scripts, Level 2 parallel across scenes. Uses `xai_sdk.AsyncClient` (requires `XAI_API_KEY`).

### Output

- `output/videos/<YYYY-MM-DD>_<N>/scene_<M>.mp4` + `end_card.mp4` + `script_video.mp4` + `video_manifest.json` per script.
- `output/videos/final_<YYYY-MM-DD>.mp4` — all scripts concatenated with glitch transitions + silence.
- Video clips include native audio (dialogue, sound effects, ambient) generated by grok-imagine-video.

## Caption Maker Internals

Pipeline: find script_video.mp4 files → transcribe via OpenAI Whisper API (word-level timestamps) → generate drawtext filter chain (cumulative word reveal) → burn subtitles via ffmpeg drawtext → reassemble final captioned video. No LLM calls.

### Pipeline stages

- **Video finder** (`pipeline/video_finder.py`): Globs for `script_video.mp4` files by date in `output/videos/`. Auto-detects latest date if none specified.
- **Transcriber** (`pipeline/transcriber.py`): Uses OpenAI Whisper API (`whisper-1`) with word-level timestamps via `verbose_json` response format. Requires `OPENAI_API_KEY`. Internal dataclasses (`WordTiming`, `Segment`, `Transcription`) — not in `shared/models.py` as they don't participate in the inter-agent data contract.
- **Filter generator** (`pipeline/filter_generator.py`): Generates ffmpeg `drawtext` filter chain for cumulative word reveal — each word appears one by one as spoken via timed `enable='between(t,...)'` expressions. Font size scales proportionally with video height. Clean minimal white style (Inter Bold, 3px black outline, drop shadow, bottom 20%). Writes filter to `captions_filter.txt` for debugging.
- **Subtitle burner** (`pipeline/subtitle_burner.py`): Burns subtitles into video via ffmpeg `-filter_script:v` with the drawtext filter chain. Uses `run_ffmpeg()` from `shared/ffmpeg.py`.
- **Runner** (`pipeline/runner.py`): Async orchestrator. Parallel across scripts via `asyncio.gather()`. Skips silent/instrumental videos gracefully. Reuses `assemble_final_video` from `video_designer.pipeline.assembler` for final assembly.

### Output

- `output/videos/<YYYY-MM-DD>_<N>/captions_filter.txt` — intermediate drawtext filter script (kept for debugging).
- `output/videos/<YYYY-MM-DD>_<N>/script_video_captioned.mp4` — captioned per-script video.
- `output/videos/final_<YYYY-MM-DD>_captioned.mp4` — all captioned scripts assembled with glitch transitions.
- Original uncaptioned files are untouched (non-destructive).

