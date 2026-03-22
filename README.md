# Cartoon Maker

AI-powered pipeline that discovers trending topics, writes comedy scripts, generates static shot keyframes, assembles final cartoon videos with native audio, and adds whisper-based captions.

Free to use, modify, and distribute — [MIT License](LICENSE).

## Architecture

```
trending news ──▶ Agent Researcher ──▶ daily brief (.md + .json)
                                            │
                                            ▼
                  Script Writer ──▶ 5 scripts with scene prompts
                                            │
                                            ▼
                  Static Shots Maker ──▶ 9:16 PNGs per scene
                                            │
                                            ▼
                  Video Designer ──▶ 15s clips ──▶ final video
                                            │
                                            ▼
                  Caption Maker ──▶ captioned video with subtitles
```

Each agent is a self-contained module. Agents communicate through JSON sidecars — the output of one feeds into the next. Cross-agent utilities (data contracts, config, shared helpers) live in `shared/`.

## Setup

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv and install dependencies
uv venv && source .venv/bin/activate
uv sync

# Copy and fill in API keys
cp .env.example .env
```

### Dev setup

```bash
uv sync --extra dev     # pytest, ruff, pre-commit
pre-commit install      # runs ruff + pytest on every commit
```

## Quickstart

```bash
# One-time: set up characters and art style (interactive)
PYTHONPATH=. python -m script_writer.setup
PYTHONPATH=. python -m script_writer.setup art-materials

# Daily pipeline (run in order):
PYTHONPATH=. python -m agent_researcher           # 1. Discover & score trends
PYTHONPATH=. python -m script_writer              # 2. Write comedy scripts
PYTHONPATH=. python -m static_shots_maker         # 3. Generate keyframe images
PYTHONPATH=. python -m video_designer             # 4. Produce final video
PYTHONPATH=. python -m caption_maker              # 5. Add captions

# Each agent auto-detects the latest output from the previous stage.
# To target a specific date, pass --date YYYY-MM-DD to any agent.
```

## Agent Researcher

Scans 7 sources across 3 tiers, deduplicates by URL and fuzzy title similarity, filters against 7-day history of previous briefs, and scores each item via Claude Opus with adaptive thinking.

| Source | Tier | Auth required |
|--------|------|---------------|
| Hacker News | validation | None |
| arXiv / bioRxiv (RSS) | context | None |
| Manifold Markets | validation | None |
| X/Twitter (via xAI Grok) | discovery | `XAI_API_KEY` |
| Reddit (r/LocalLLaMA) | discovery | `REDDIT_CLIENT_ID` + `SECRET` |
| Product Hunt | discovery | `PRODUCT_HUNT_API_KEY` + `SECRET` |
| Bluesky | discovery | `BLUESKY_HANDLE` + `APP_PASSWORD` |

**Output**: `output/briefs/YYYY-MM-DD.md` + `.json` sidecar — top 5 picks + 10 notable items, each with comedy explanation and joke angle. Optional Notion delivery.

**Scheduled mode**: `PYTHONPATH=. python -m agent_researcher --scheduled` runs daily at 07:30.

## Script Writer

Reads the daily brief, generates 3 loglines per item (observational / satirical / metaphorical), selects the best, and expands to full scripts with synopsis and scene-by-scene breakdown — all items processed in parallel.

### First-time setup

```bash
PYTHONPATH=. python -m script_writer.setup              # Characters + art style (interactive)
PYTHONPATH=. python -m script_writer.setup characters    # Characters only
PYTHONPATH=. python -m script_writer.setup art-style     # Art style only
PYTHONPATH=. python -m script_writer.setup art-materials # Generate reference images (requires GOOGLE_API_KEY)
```

Creates `output/characters/<name>.md`, `output/art_style.md`, and `output/art_materials/canonical_characters.png`.

**Output**: `output/scripts/<YYYY-MM-DD>_<N>.md` + `.json` (N = 1-5). Each script has 1 scene with a cinematographic scene prompt (80-150 words), a visual riddle, dialogue (2-3 lines), and audio direction. Duration fixed at 15 seconds.

## Static Shots Maker

Rewrites video-oriented scene prompts into image-optimized prompts via Claude (cinematographic composition: depth layering, explicit lighting, atmosphere), then generates 9:16 PNGs via Gemini. Scenes within each script are processed sequentially so each shot can serve as a visual reference for the next; scripts run in parallel.

**Output**: `output/static_shots/<YYYY-MM-DD>_<N>/scene_<M>.png` + `manifest.json` per script.

## Video Designer

Composes video prompts from scene details + character profiles via Claude, generates 15s clips with native audio (dialogue, sound effects, ambient) via xAI grok-imagine-video, then assembles per-script videos and a final concatenated video with glitch transitions.

**Output**:
- `output/videos/<YYYY-MM-DD>_<N>/scene_<M>.mp4` — individual clips
- `output/videos/<YYYY-MM-DD>_<N>/script_video.mp4` — per-script assembly
- `output/videos/final_<YYYY-MM-DD>.mp4` — all scripts concatenated

## Caption Maker

Transcribes spoken audio from generated videos via the OpenAI Whisper API, generates ASS subtitles with cumulative word reveal (words appear one by one as spoken), and burns styled captions into videos via ffmpeg. Clean minimal white style — Inter Bold, black outline, drop shadow, bottom 20%.

**Output**:
- `output/videos/<YYYY-MM-DD>_<N>/script_video_captioned.mp4` — captioned per-script video
- `output/videos/final_<YYYY-MM-DD>_captioned.mp4` — all scripts captioned and concatenated
- Original uncaptioned files are untouched

## Project Structure

```
cartoon_maker/
├── agent_researcher/    # Stage 1: trend discovery & scoring
├── script_writer/       # Stage 2: script creation pipeline + setup tools
├── static_shots_maker/  # Stage 3: static shot generation
├── video_designer/      # Stage 4: video assembly & final output
├── caption_maker/       # Stage 5: whisper-based video captions
├── shared/              # Data contracts, config, LLM helpers, context loader
├── tests/               # 217 tests (pytest)
└── output/              # All generated artifacts (gitignored)
```

## Testing

```bash
.venv/bin/pytest tests/ -v       # Run all 217 tests
.venv/bin/pytest tests/test_dedup.py  # Single file
.venv/bin/ruff check .           # Lint
```

Pre-commit hooks run ruff (lint + format) and pytest automatically on every commit.

## Environment Variables

See `.env.example` for the full list.

| Variable | Required for | Fallback |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | All agents | Scorer falls back to raw score sorting |
| `GOOGLE_API_KEY` | Static shots, art materials | None (pipeline fails) |
| `XAI_API_KEY` | Video generation, X/Twitter source | Video fails; X source skipped |
| `OPENAI_API_KEY` | Captions | Caption pipeline fails |
| Source credentials | Individual sources | Source skipped gracefully |
