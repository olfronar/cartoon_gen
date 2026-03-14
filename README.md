# Cartoon Maker

AI-powered pipeline that discovers trending topics from social media, writes comedy scripts, generates visual keyframes, and produces cartoon videos.

## Architecture

The pipeline consists of four sequential agents:

1. **Agent Researcher** (`agent_researcher/`) — Parses social media (X/Twitter via xAI API, Reddit, Hacker News) and filters AI/tech trends suitable for comedy cartoons.

2. **Script Writer** (`script_writer/`) — Analyzes filtered trends, writes loglines, selects the best one, develops a synopsis, and writes the full script.

3. **Static Shots Maker** (`static_shots_maker/`) — Analyzes the script and generates static shots (images) as keyframes for each scene.

4. **Video Designer** (`video_designer/`) — Generates video for each scene from static shots and assembles the final cartoon.

Cross-agent utilities (data contracts, config, logging) live in `shared/`.

## Setup

```bash
uv venv
source .venv/bin/activate
uv sync
```
