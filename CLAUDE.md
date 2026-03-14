# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cartoon Maker is an AI-powered pipeline that automatically discovers trending topics from social media, writes comedy scripts, generates static shots, and produces final cartoon videos. The pipeline is composed of four independent agents that run sequentially.

## Architecture

The project follows a modular agent-based architecture. Each agent is a self-contained module with its own directory, logic, and dependencies:

```
cartoon_maker/
├── shared/              # Cross-agent utilities: data contracts, config, logging
├── agent_researcher/    # Stage 1: Trend discovery & filtering
├── script_writer/       # Stage 2: Script creation pipeline
├── static_shots_maker/  # Stage 3: Static shot generation
├── video_designer/      # Stage 4: Video assembly & final output
```

### Agent Pipeline (sequential flow)

1. **agent_researcher** — Parses social media sources (X/Twitter via xAI API, Reddit, Hacker News, etc.) and filters for AI/tech trends suitable for comedy cartoons.

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

# Sync dependencies
uv sync
```

Dependencies are managed in `pyproject.toml` (not requirements.txt).
