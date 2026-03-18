# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cartoon Maker is an AI-powered pipeline that automatically discovers trending topics from social media, writes comedy scripts, generates static shots, and produces final cartoon videos. The pipeline is composed of four independent agents that run sequentially.

## Architecture

The project follows a modular agent-based architecture. Each agent is a self-contained module with its own directory, logic, and dependencies:

```
cartoon_maker/
├── shared/              # Cross-agent utilities: data contracts, config, logging
├── agent_researcher/    # Stage 1: Trend discovery & filtering  [IMPLEMENTED]
├── script_writer/       # Stage 2: Script creation pipeline     [IMPLEMENTED]
├── static_shots_maker/  # Stage 3: Static shot generation       [IMPLEMENTED]
├── video_designer/      # Stage 4: Video assembly & final output [IMPLEMENTED]
```

### Agent Pipeline (sequential flow)

1. **agent_researcher** — Scans 7 sources across 3 tiers, deduplicates, scores via Claude Opus for comedy potential, and outputs a ranked daily brief.

2. **script_writer** — Reads the daily brief JSON sidecar, generates 3 loglines per item (absurdist/satirical/surreal), selects the best, expands to synopsis + full script with scene-by-scene breakdown. Requires character profiles and art style (created via interactive setup tool).

3. **static_shots_maker** — Reads script JSONs, uses Claude to rewrite video prompts into image-optimized prompts, generates 9:16 PNGs via Gemini, outputs shots + manifest per script.

4. **video_designer** — Reads static shots + script JSONs, uses Claude to compose video prompts, generates 15s clips via xAI grok-imagine-video (with native audio), assembles with glitch transitions into final cartoon videos.

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
# Run all tests (189 tests)
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
# Agent Researcher — one-shot run (from project root)
PYTHONPATH=. python -m agent_researcher

# Agent Researcher — scheduled daily run (default 07:30)
PYTHONPATH=. python -m agent_researcher --scheduled

# Script Writer — character & art style setup (interactive, run once)
PYTHONPATH=. python -m script_writer.setup

# Script Writer — generate art materials (run after characters + art style exist)
PYTHONPATH=. python -m script_writer.setup art-materials

# Script Writer — generate scripts from latest brief
PYTHONPATH=. python -m script_writer

# Script Writer — generate scripts from specific date
PYTHONPATH=. python -m script_writer --date 2026-03-14

# Static Shots Maker — generate shots from latest scripts
PYTHONPATH=. python -m static_shots_maker

# Static Shots Maker — generate shots from specific date
PYTHONPATH=. python -m static_shots_maker --date 2026-03-15

# Video Designer — generate videos from latest static shots
PYTHONPATH=. python -m video_designer

# Video Designer — generate videos from specific date
PYTHONPATH=. python -m video_designer --date 2026-03-15
```

### Config

Environment variables loaded from `.env` (see `.env.example` for template). Missing optional credentials cause graceful source skipping, not crashes.

Required: `ANTHROPIC_API_KEY` (without it, scorer falls back to raw score sorting — no comedy angles).

Required for static shots: `GOOGLE_API_KEY` (Gemini image generation). Required for video: `XAI_API_KEY` (xAI grok-imagine-video). Optional: `ANTHROPIC_API_KEY` enables Claude prompt rewriting (falls back to regex stripping for shots, original prompts for video).

## Code Conventions

- Cross-module utilities (parsing, formatting, HTTP helpers) go in `shared/utils.py` — never duplicate logic across agent modules
- LLM JSON responses may be wrapped in code fences: use `strip_code_fences()` from `shared/utils.py`
- ISO timestamps with `Z` suffix: use `parse_iso_utc()` from `shared/utils.py`
- Constants, lookup dicts, and compiled regexes belong at module level, not inside functions
- Each piece of logic has one owner module — if a second copy appears, extract to `shared/`
- Error handling and resource setup (fallback logic, directory creation) belong in the module that owns the operation — callers should not duplicate these concerns
- Avoid pre-checking file/resource existence before operating (TOCTOU anti-pattern) — call the operation directly and handle the error
- LLM calls: use `call_llm_json(client, prompt, model, max_tokens)` from `shared/utils.py` — handles streaming, text extraction, code fence stripping, and JSON parsing. Use `call_llm_text()` for raw text responses. Create a single `anthropic.Anthropic` client per pipeline run and pass it through.
- LLM response text extraction: use `extract_text(response)` from `shared/utils.py` for non-JSON responses
- Context loading: use `shared/context_loader.py` for loading characters + art style (shared by script_writer and static_shots_maker)
- Dataclass serialization: use `asdict()` with post-processing for non-serializable fields (dates, Paths). Never hand-build the dict — fields added later would be silently dropped. Add a `from_dict()` classmethod for any dataclass that is serialized to JSON — consumers should not hand-parse

## Agent Researcher Internals

Pipeline: parallel source fetch → URL validation → dedup/freshness filter → cross-day history filter → LLM scoring (Claude Opus with adaptive thinking) → Markdown brief + optional Notion delivery.

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
- **Scorer** (`scorer.py`): streams to `claude-opus-4-6` with adaptive thinking, 32k max tokens. Rewrites titles for clarity, generates comedy explanations for every item. Falls back to raw score sorting if API key missing or call fails.
- **xAI source** (`sources/xai.py`): uses `grok-4.20-beta-latest-non-reasoning` with `web_search(allowed_domains=["x.com"])` tool for live X data.
- **Data contracts** (`shared/models.py`): `RawItem` → `ScoredItem` → `ComedyBrief` → `Logline` → `Synopsis` → `SceneScript` → `CartoonScript` → `ShotResult` → `ShotsManifest` → `ClipResult` → `VideoManifest`. All agents share these. `Synopsis.from_dict()` accepts both `development` and legacy `escalation` keys for backward compatibility.
- **Shared utilities** (`shared/utils.py`): `strip_code_fences()`, `parse_iso_utc()`, `strip_html()`, `extract_text()`, `call_llm_json()`, `call_llm_text()`.
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
- **Logline generator** (`pipeline/logline_generator.py`): Structured "angle sharpening" (`story_hook` analysis) before generating 3 loglines per news item (observational / satirical / metaphorical). Each approach targets a specific feeling people are avoiding about the news. Uses Claude Opus with adaptive thinking. Response format: `{"story_hook": {...}, "loglines": [...]}` — parser extracts `loglines` array, `story_hook` exists only to improve quality.
- **Logline selector** (`pipeline/logline_selector.py`): Selects best 1 of 3 per item. Prioritizes news clarity, then comedy punch and point of view over simplicity. Falls back to first logline on error.
- **Script expander** (`pipeline/script_expander.py`): Two-step: synopsis → full script. All 5 items run in parallel via `asyncio.gather()`.
- **Renderer** (`pipeline/renderer.py`): `CartoonScript` → `.md` (human-readable) + `.json` (machine-readable for static_shots_maker).
- **Prompts** (`prompts.py`): All prompt templates. Shared humor preamble establishes the field-correspondent show format, CRITICAL visual rule (single photograph per scene), and three comedy traditions (dry observation, deadpan absurdism, quiet irony). Downstream prompts (script expansion, image, video) use tiered rules: NON-NEGOTIABLE/CRITICAL → REQUIRED → STYLE/FORMAT. Script expansion includes a `compliance_check` validation checklist and a concrete JSON example. `comedy_angle`, `snippet`, and `news_explanation` are passed through to the script expansion stage so the LLM never loses the factual news context.
- **Runner** (`pipeline/runner.py`): Async orchestrator for the full pipeline.

### Setup tool

- **Interviewer** (`setup/interviewer.py`): Generic multi-turn LLM conversation engine. Detects `INTERVIEW_COMPLETE` marker.
- **Character builder** (`setup/character_builder.py`): Interactive character design interview → `output/characters/<name>.md`.
- **Art style builder** (`setup/art_style_builder.py`): Interactive art style interview → `output/art_style.md`.
- **Art materials builder** (`setup/art_materials_builder.py`): Automated (non-interactive) generation of canonical reference images via Gemini → `output/art_materials/canonical_characters.png`. Requires `GOOGLE_API_KEY`. Run separately after characters + art style exist.

### Output

- `output/scripts/<YYYY-MM-DD>_<N>.md` + `.json` — one pair per top pick (N = 1-5).
- Scene prompts: 80-150 words describing a single frozen moment (photograph-style) composed with cinematographic intent — strong vertical lines, deliberate depth layering, explicit composition language ("lower-third," "dead center," "extreme foreground"). Affirmative only, front-loaded key visuals, with dialogue quoted inline for native audio generation. Each scene must contain a VISUAL RIDDLE (scale paradox, impossible coexistence, symmetry break, or frame-within-frame) — not just a funny prop. Duration fixed at 15 seconds. 1 scene per script. Maximum 2 characters per scene, 1 visual gag/prop. Billy stays in one location throughout. Dialogue is the primary vehicle for both comedy and exposition (2-3 lines per scene).

## Static Shots Maker Internals

Pipeline: script JSON ingestion → sequential prompt rewriting + image generation per script (for visual continuity) → PNG output + manifest. Script-level parallelism preserved, scene-level is sequential (each scene uses previous scene's output as reference).

### Pipeline stages

- **Script reader** (`pipeline/script_reader.py`): Reads `output/scripts/<date>_<N>.json` sidecars. Auto-detects latest date if none specified. Uses `CartoonScript.from_dict()`.
- **Prompt generator** (`pipeline/prompt_generator.py`): Claude rewrites video-oriented scene prompts into static image prompts (strips motion/audio/duration, picks peak visual moment, weaves in character details + art style). Falls back to regex stripping if Claude unavailable.
- **Image generator** (`pipeline/image_generator.py`): Gemini `gemini-3.1-flash-image-preview` generates 9:16 PNGs. Accepts optional `reference_images` (art materials + previous scene) for visual consistency.
- **Prompts** (`prompts.py`): `SCENE_TO_IMAGE_PROMPT` and `END_CARD_TO_IMAGE_PROMPT` templates. Rules tiered as CRITICAL/COMPOSITION/REQUIRED/FORMAT. Cinematographer role declaration producing poster-quality compositions. COMPOSITION section preserves visual riddles, specifies depth layering (foreground/midground/background), explicit lighting (source, color temperature, shadows), framing approach, exact scale language, and atmosphere words. 100-250 word output range. References art materials and previous scene for consistency.
- **Runner** (`pipeline/runner.py`): Async orchestrator. Level 1 parallel across scripts, scenes sequential within each script (visual continuity chain). Loads art materials as reference images.

### Output

- `output/static_shots/<YYYY-MM-DD>_<N>/scene_<M>.png` + `end_card.png` + `manifest.json` per script.
- `manifest.json` records success/failure per shot for `video_designer` to consume.

## Video Designer Internals

Pipeline: manifest + script ingestion → parallel video prompt composition (Claude, includes dialogue formatting) → parallel video generation (xAI grok-imagine-video with native audio) → ffmpeg assembly with glitch transitions. Two-level `asyncio.gather()` with semaphore for rate limiting.

### Pipeline stages

- **Manifest reader** (`pipeline/manifest_reader.py`): Reads `output/static_shots/<date>_<N>/manifest.json` + pairs with `output/scripts/<date>_<N>.json`. Auto-detects latest date. Skips scripts with no successful shots.
- **Prompt generator** (`pipeline/prompt_generator.py`): Claude composes video-generation prompts from scene details + character profiles + art style + formatted dialogue. Falls back to original scene_prompt if Claude unavailable.
- **Video generator** (`pipeline/video_generator.py`): xAI grok-imagine-video (`grok-imagine-video`) image-to-video with native audio generation. Uses static shot as source image via base64 data URI. SDK handles polling internally.
- **Assembler** (`pipeline/assembler.py`): ffmpeg concatenation with re-encoding (`libx264 + aac`) for audio normalization. Glitch transitions (1.0s) with silence between scripts.
- **Prompts** (`prompts.py`): `SCENE_TO_VIDEO_PROMPT` and `END_CARD_TO_VIDEO_PROMPT` templates. Rules tiered as CRITICAL/REQUIRED/FORMAT. Include audio/dialogue direction for native audio generation.
- **Runner** (`pipeline/runner.py`): Async orchestrator. Level 1 parallel across scripts, Level 2 parallel across scenes. Uses `xai_sdk.AsyncClient` (requires `XAI_API_KEY`).

### Output

- `output/videos/<YYYY-MM-DD>_<N>/scene_<M>.mp4` + `end_card.mp4` + `script_video.mp4` + `video_manifest.json` per script.
- `output/videos/final_<YYYY-MM-DD>.mp4` — all scripts concatenated with glitch transitions + silence.
- Video clips include native audio (dialogue, sound effects, ambient) generated by grok-imagine-video.
