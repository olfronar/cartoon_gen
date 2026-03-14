# Cartoon Maker

AI-powered pipeline that discovers trending topics from social media, writes comedy scripts, generates visual keyframes, and produces cartoon videos.

## Architecture

The pipeline consists of four sequential agents:

1. **Agent Researcher** (`agent_researcher/`) — Scans social media and tech sources, scores trends for comedy potential via Claude, outputs a daily brief. **Fully implemented.**

2. **Script Writer** (`script_writer/`) — Reads daily brief, generates loglines (3 per item), selects best, expands to full scripts with scene-by-scene breakdown formatted for xAI video generation. Includes interactive setup tool for character/art style design. **Fully implemented.**

3. **Static Shots Maker** (`static_shots_maker/`) — Generates static shots (images) as keyframes for each scene.

4. **Video Designer** (`video_designer/`) — Generates video for each scene from static shots and assembles the final cartoon.

Cross-agent utilities (data contracts, config, shared helpers) live in `shared/`.

## Agent Researcher

Scans 7 sources across 3 tiers, deduplicates by URL and title similarity, scores each item via Claude Opus for comedy potential, and generates a ranked daily brief.

### Sources

| Source | Tier | Auth required |
|--------|------|---------------|
| Hacker News | validation | None |
| arXiv / bioRxiv (RSS) | context | None |
| Manifold Markets | validation | None |
| X/Twitter (via xAI Grok) | discovery | `XAI_API_KEY` |
| Reddit (r/LocalLLaMA) | discovery | `REDDIT_CLIENT_ID` + `SECRET` |
| Product Hunt | discovery | `PRODUCT_HUNT_API_KEY` + `SECRET` |
| Bluesky | discovery | `BLUESKY_HANDLE` + `APP_PASSWORD` |

### Output

Daily markdown brief at `output/briefs/YYYY-MM-DD.md` + JSON sidecar (`.json`) with top 5 picks + 10 notable items, each with comedy explanation and joke angle. Optional Notion page delivery.

## Setup

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv and install dependencies
uv venv
source .venv/bin/activate
uv sync

# Copy and fill in API keys
cp .env.example .env
# Edit .env with your keys (at minimum ANTHROPIC_API_KEY)
```

### Dev setup

```bash
# Install dev dependencies (pytest, ruff, pre-commit)
uv sync --extra dev

# Install pre-commit hooks
pre-commit install
```

## Script Writer

Transforms the daily comedy brief into 5 production-ready cartoon scripts formatted for xAI video generation (`grok-imagine-video`).

### Setup (run once)

```bash
# Define characters and art style via interactive interview
PYTHONPATH=. python -m script_writer.setup              # Both
PYTHONPATH=. python -m script_writer.setup characters    # Characters only
PYTHONPATH=. python -m script_writer.setup art-style     # Art style only
```

Creates `output/characters/<name>.md` and `output/art_style.md`.

### Output

- `output/scripts/<YYYY-MM-DD>_<N>.md` — Human-readable script (N = 1-5)
- `output/scripts/<YYYY-MM-DD>_<N>.json` — Machine-readable for static_shots_maker

Each script has 5-8 scenes with scene prompts (50-150 words, xAI golden formula), dialogue, visual gags, and audio direction.

## Usage

```bash
# Agent Researcher — one-shot run
PYTHONPATH=. python -m agent_researcher

# Agent Researcher — scheduled daily run (default 07:30)
PYTHONPATH=. python -m agent_researcher --scheduled

# Script Writer — generate scripts from latest brief
PYTHONPATH=. python -m script_writer

# Script Writer — generate scripts from specific date
PYTHONPATH=. python -m script_writer --date 2026-03-14
```

## Testing

```bash
# Run all tests (121 tests)
pytest

# Run with verbose output
pytest -v

# Run a single test file
pytest tests/test_dedup.py
```

## Environment Variables

See `.env.example` for the full list. Only `ANTHROPIC_API_KEY` is required — all other sources degrade gracefully when credentials are missing.
