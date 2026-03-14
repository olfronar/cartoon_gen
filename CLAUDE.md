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
├── script_writer/       # Stage 2: Script creation pipeline     [STUB]
├── static_shots_maker/  # Stage 3: Static shot generation       [STUB]
├── video_designer/      # Stage 4: Video assembly & final output [STUB]
```

### Agent Pipeline (sequential flow)

1. **agent_researcher** — Scans 7 sources across 3 tiers, deduplicates, scores via Claude Opus for comedy potential, and outputs a ranked daily brief.

2. **script_writer** — Analyzes filtered trends, writes loglines, selects the best one, develops a synopsis, then writes the full script.

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
# Run all tests (82 tests)
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
# One-shot run (from project root)
PYTHONPATH=. python -m agent_researcher

# Scheduled daily run (default 07:30)
PYTHONPATH=. python -m agent_researcher --scheduled

# Custom schedule time
PYTHONPATH=. python -m agent_researcher --scheduled --hour 9 --minute 0
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
- **Data contracts** (`shared/models.py`): `RawItem` → `ScoredItem` → `ComedyBrief`. All agents share these.
- **Shared utilities** (`shared/utils.py`): `strip_code_fences()`, `parse_iso_utc()`, `strip_html()`.
- **Delivery** (`delivery/`): local `.md` file (always) + Notion page (if `NOTION_API_KEY` configured).
- **Alerts** (`alerts.py`): Slack webhook notifications on success/failure. Gated on `SLACK_WEBHOOK_URL`.
- **Scheduler** (`scheduler.py`): APScheduler `CronTrigger` for daily runs. Activated via `--scheduled` flag.
- **Output**: `output/briefs/YYYY-MM-DD.md` + optional Notion page.
