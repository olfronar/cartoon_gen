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
├── static_shots_maker/  # Stage 3: Static shot generation       [STUB]
├── video_designer/      # Stage 4: Video assembly & final output [STUB]
```

### Agent Pipeline (sequential flow)

1. **agent_researcher** — Scans 7 sources across 3 tiers, deduplicates, scores via Claude Opus for comedy potential, and outputs a ranked daily brief.

2. **script_writer** — Reads the daily brief JSON sidecar, generates 3 loglines per item (absurdist/satirical/surreal), selects the best, expands to synopsis + full script with scene-by-scene breakdown. Requires character profiles and art style (created via interactive setup tool).

3. **static_shots_maker** — Analyzes the script and generates static shots (images) for each scene that will be used as keyframes for video generation.

4. **video_designer** — Takes static shots, generates video for each scene, and assembles the final cartoon.

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

```bash
# Run all tests (121 tests)
pytest

# Run a single test file
pytest tests/test_dedup.py

# Run a single test
pytest tests/test_dedup.py::TestDedupAndFilter::test_url_dedup_merges_sources -v

# Lint
ruff check .

# Format
ruff format .
```

Pre-commit hooks run ruff (lint + format) and pytest on every commit.

### Running Agents

```bash
# Agent Researcher — one-shot run (from project root)
PYTHONPATH=. python -m agent_researcher

# Agent Researcher — scheduled daily run (default 07:30)
PYTHONPATH=. python -m agent_researcher --scheduled

# Script Writer — character & art style setup (interactive, run once)
PYTHONPATH=. python -m script_writer.setup

# Script Writer — generate scripts from latest brief
PYTHONPATH=. python -m script_writer

# Script Writer — generate scripts from specific date
PYTHONPATH=. python -m script_writer --date 2026-03-14
```

### Config

Environment variables loaded from `.env` (see `.env.example` for template). Missing optional credentials cause graceful source skipping, not crashes.

Required: `ANTHROPIC_API_KEY` (without it, scorer falls back to raw score sorting — no comedy angles).

## Code Conventions

- Cross-module utilities (parsing, formatting, HTTP helpers) go in `shared/utils.py` — never duplicate logic across agent modules
- LLM JSON responses may be wrapped in code fences: use `strip_code_fences()` from `shared/utils.py`
- ISO timestamps with `Z` suffix: use `parse_iso_utc()` from `shared/utils.py`
- Constants, lookup dicts, and compiled regexes belong at module level, not inside functions
- Each piece of logic has one owner module — if a second copy appears, extract to `shared/`
- LLM calls: use `call_llm_json(client, prompt, model, max_tokens)` from `shared/utils.py` — handles streaming, text extraction, code fence stripping, and JSON parsing. Create a single `anthropic.Anthropic` client per pipeline run and pass it through.
- LLM response text extraction: use `extract_text(response)` from `shared/utils.py` for non-JSON responses

## Agent Researcher Internals

Pipeline: parallel source fetch → dedup/freshness filter → LLM scoring (Claude Opus with adaptive thinking) → Markdown brief + optional Notion delivery.

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

### Key modules

- **Source Protocol** (`sources/base.py`): synchronous `fetch() -> list[RawItem]`. Runner parallelizes via `asyncio.to_thread()`.
- **Dedup** (`dedup.py`): URL normalization + `rapidfuzz` title similarity (threshold 85). Merges multi-source items rather than discarding.
- **Scorer** (`scorer.py`): streams to `claude-opus-4-6` with adaptive thinking, 32k max tokens. Rewrites titles for clarity, generates comedy explanations for every item. Falls back to raw score sorting if API key missing or call fails.
- **xAI source** (`sources/xai.py`): uses `grok-4.20-beta-latest-non-reasoning` with `web_search(allowed_domains=["x.com"])` tool for live X data.
- **Data contracts** (`shared/models.py`): `RawItem` → `ScoredItem` → `ComedyBrief` → `Logline` → `Synopsis` → `SceneScript` → `CartoonScript`. All agents share these.
- **Shared utilities** (`shared/utils.py`): `strip_code_fences()`, `parse_iso_utc()`, `strip_html()`, `extract_text()`, `call_llm_json()`.
- **Delivery** (`delivery/`): local `.md` file (always) + Notion page (if `NOTION_API_KEY` configured).
- **Alerts** (`alerts.py`): Slack webhook notifications on success/failure. Gated on `SLACK_WEBHOOK_URL`.
- **Scheduler** (`scheduler.py`): APScheduler `CronTrigger` for daily runs. Activated via `--scheduled` flag.
- **Output**: `output/briefs/YYYY-MM-DD.md` + `.json` sidecar + optional Notion page.

## Script Writer Internals

Pipeline: brief JSON ingestion → parallel logline generation + selection (all items concurrent) → parallel script expansion (synopsis + full script) → .md + .json output. Single `anthropic.Anthropic` client shared across all LLM calls.

### Pipeline stages

- **Brief reader** (`pipeline/brief_reader.py`): Reads `output/briefs/YYYY-MM-DD.json` sidecar. Auto-detects latest date if none specified.
- **Context loader** (`pipeline/context_loader.py`): Loads `output/characters/*.md` and `output/art_style.md` into a shared prompt context block.
- **Logline generator** (`pipeline/logline_generator.py`): 3 loglines per news item (absurdist / satirical / surreal). Uses Claude Opus with adaptive thinking.
- **Logline selector** (`pipeline/logline_selector.py`): Selects best 1 of 3 per item. Falls back to first logline on error.
- **Script expander** (`pipeline/script_expander.py`): Two-step: synopsis → full script. All 5 items run in parallel via `asyncio.gather()`.
- **Renderer** (`pipeline/renderer.py`): `CartoonScript` → `.md` (human-readable) + `.json` (machine-readable for static_shots_maker).
- **Prompts** (`prompts.py`): All prompt templates. Shared humor preamble establishes three comedy traditions.
- **Runner** (`pipeline/runner.py`): Async orchestrator for the full pipeline.

### Setup tool

- **Interviewer** (`setup/interviewer.py`): Generic multi-turn LLM conversation engine. Detects `INTERVIEW_COMPLETE` marker.
- **Character builder** (`setup/character_builder.py`): Interactive character design interview → `output/characters/<name>.md`.
- **Art style builder** (`setup/art_style_builder.py`): Interactive art style interview → `output/art_style.md`.

### Output

- `output/scripts/<YYYY-MM-DD>_<N>.md` + `.json` — one pair per top pick (N = 1-5).
- Scene prompts follow xAI golden formula: 50-150 words, affirmative only, front-loaded key visuals.
