# Cartoon Maker

AI-powered pipeline that discovers trending topics from social media, writes comedy scripts, generates visual keyframes, and produces cartoon videos.

## Architecture

The pipeline consists of four sequential agents:

1. **Agent Researcher** (`agent_researcher/`) — Scans social media and tech sources, scores trends for comedy potential via Claude, outputs a daily brief. **Fully implemented.**

2. **Script Writer** (`script_writer/`) — Analyzes filtered trends, writes loglines, selects the best one, develops a synopsis, and writes the full script.

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

Daily markdown brief at `output/briefs/YYYY-MM-DD.md` with top 5 picks + 10 notable items, each with comedy explanation and joke angle. Optional Notion page delivery.

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

## Usage

```bash
# One-shot run
PYTHONPATH=. python -m agent_researcher

# Scheduled daily run (default 07:30 local time)
PYTHONPATH=. python -m agent_researcher --scheduled

# Custom schedule
PYTHONPATH=. python -m agent_researcher --scheduled --hour 9 --minute 0
```

## Testing

```bash
# Run all tests (82 tests)
pytest

# Run with verbose output
pytest -v

# Run a single test file
pytest tests/test_dedup.py
```

## Environment Variables

See `.env.example` for the full list. Only `ANTHROPIC_API_KEY` is required — all other sources degrade gracefully when credentials are missing.
