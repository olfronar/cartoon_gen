# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cartoon Maker is an AI-powered pipeline that automatically discovers trending topics from social media, writes comedy scripts, generates static shots, produces final cartoon videos, adds whisper-based captions, and publishes to TikTok. The pipeline is composed of six independent agents that run sequentially.

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
├── tiktok_publisher/    # Stage 6: TikTok video publishing       [IMPLEMENTED]
```

### Agent Pipeline (sequential flow)

1. **agent_researcher** — Scans 9 sources across 3 tiers, deduplicates, pre-filters via Claude Sonnet (fast ranking to top 50), then deep-scores via Claude Opus for comedy potential, and outputs a unified numbered prioritized list of 20 news items.

2. **script_writer** — Reads the daily brief JSON sidecar, generates 3 loglines per item (absurdist/satirical/surreal), selects the best, expands to synopsis + full script with scene-by-scene breakdown. Requires character profiles and art style (created via interactive setup tool).

3. **static_shots_maker** — Reads script JSONs, uses Claude to rewrite video prompts into image-optimized prompts, generates 9:16 PNGs via Gemini, outputs shots + manifest per script.

4. **video_designer** — Reads static shots + script JSONs, uses Claude to compose video prompts, generates 15s clips via xAI grok-imagine-video (with native audio), assembles with glitch transitions into final cartoon videos.

5. **caption_maker** — Transcribes spoken audio from generated videos via OpenAI Whisper API, generates ASS subtitles with cumulative word reveal, and burns styled captions into videos via ffmpeg. Requires `OPENAI_API_KEY`.

6. **tiktok_publisher** — Authenticates via TikTok OAuth, finds captioned (preferred) or raw per-script videos, reads script JSON for title/description, uploads videos as drafts to the creator's TikTok inbox via the inbox API (chunked FILE_UPLOAD); user publishes manually. Requires `TIKTOK_CLIENT_KEY` + `TIKTOK_CLIENT_SECRET`.

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
# Run all tests (250 tests)
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

Test object factories (`make_raw_item`, `make_scored_item`, `make_script`, `mock_stream_response`, etc.) live in `tests/conftest.py` — never duplicate these across test files.

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

# Script Writer — generate scripts for specific news items from brief (1-based, 1-20)
uv run python -m script_writer --pick 1,3,7

# Script Writer — use Grok instead of Claude Opus
uv run python -m script_writer --model grok

# Script Writer — skip editor review/revision pass (also skips punch-up)
uv run python -m script_writer --no-editor

# Script Writer — disable pairwise tournament (simple 3-candidate selection)
uv run python -m script_writer --no-tournament

# Static Shots Maker — generate shots from latest scripts
uv run python -m static_shots_maker

# Static Shots Maker — generate shots from specific date
uv run python -m static_shots_maker --date 2026-03-15

# Static Shots Maker — use Grok for prompt rewriting
uv run python -m static_shots_maker --model grok

# Static Shots Maker — verify shots via Claude vision after generation
uv run python -m static_shots_maker --verify

# Static Shots Maker — generate 2 candidates per scene, verify, pick best
uv run python -m static_shots_maker --candidates 2

# Video Designer — generate videos from latest static shots
uv run python -m video_designer

# Video Designer — generate videos from specific date
uv run python -m video_designer --date 2026-03-15

# Video Designer — also compile final video from all scripts
uv run python -m video_designer --compile

# Caption Maker — add captions to latest videos
uv run python -m caption_maker

# Caption Maker — add captions for specific date
uv run python -m caption_maker --date 2026-03-15

# Caption Maker — also compile final captioned video
uv run python -m caption_maker --compile

# TikTok Publisher — authenticate (opens browser for OAuth)
uv run python -m tiktok_publisher auth

# TikTok Publisher — force refresh tokens
uv run python -m tiktok_publisher auth --refresh

# TikTok Publisher — upload latest videos
uv run python -m tiktok_publisher upload

# TikTok Publisher — upload specific date
uv run python -m tiktok_publisher upload --date 2026-04-02
```

### Config

Environment variables loaded from `.env` (see `.env.example` for template). Missing optional credentials cause graceful source skipping, not crashes.

Required: `ANTHROPIC_API_KEY` (without it, scorer falls back to raw score sorting — no comedy angles).

Required for static shots: `GOOGLE_API_KEY` (Gemini image generation). Required for video: `XAI_API_KEY` (xAI grok-imagine-video). Optional: `ANTHROPIC_API_KEY` enables Claude prompt rewriting (falls back to regex stripping for shots, original prompts for video). Required for captions: `OPENAI_API_KEY` (OpenAI Whisper API). Optional: `WHISPER_MODEL` (default: `whisper-1`). Optional shot verification: `SHOTS_VERIFY` (enable visual verification, default: false), `SHOTS_CANDIDATES` (candidates per scene, default: 1), `SHOTS_VERIFY_MODEL` (default: `claude-opus-4-6`), `SHOTS_VERIFY_MAX_TOKENS` (default: 4096). Required for TikTok publishing: `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET` (from TikTok Developer portal). Requires `cloudflared` CLI installed. Optional: `TIKTOK_REDIRECT_PORT` (default: 8585). Required scope: `video.upload`.

## Documentation Maintenance

After completing any plan or significant update (new module, architectural change, new CLI flag, config change):
- Update root `CLAUDE.md` for cross-cutting changes (architecture, CLI commands, config, conventions)
- Update the relevant `<agent>/CLAUDE.md` for agent-specific internals (pipeline stages, prompts, output)
- Update `README.md` if it exists, to keep user-facing documentation accurate

These files are the primary context for agents and users. Stale docs cause incorrect assumptions and wasted effort.

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
- Generation API style enforcement: use `apply_style_enforcement(prompt, art_style)` from `shared/context_loader.py` — prepends art style to prompts sent to image/video generation APIs (Gemini, xAI). For APIs with prompt length limits, use `build_style_directive(art_style)` to condense the art style first
- Dataclass serialization: use `asdict()` with post-processing for non-serializable fields (dates, Paths). Never hand-build the dict — fields added later would be silently dropped. Add a `from_dict()` classmethod for any dataclass that is serialized to JSON — consumers should not hand-parse

