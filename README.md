# Cartoon Maker

AI-powered pipeline that discovers trending topics, writes comedy scripts, generates static shot keyframes, assembles final cartoon videos with native audio, adds whisper-based captions, and publishes to TikTok.

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
                                            │
                                            ▼
                  TikTok Publisher ──▶ individual posts per script
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
uv run python -m script_writer.setup
uv run python -m script_writer.setup art-materials

# Daily pipeline (run in order):
uv run python -m agent_researcher           # 1. Discover & score trends
uv run python -m script_writer              # 2. Write comedy scripts
uv run python -m static_shots_maker         # 3. Generate keyframe images
uv run python -m video_designer             # 4. Produce per-script videos
uv run python -m caption_maker              # 5. Add captions
uv run python -m tiktok_publisher upload    # 6. Publish to TikTok

# Each agent auto-detects the latest output from the previous stage.
# To target a specific date, pass --date YYYY-MM-DD to any agent.
# To pick specific news items: --pick 1,3,7 (1-based brief numbers)
# To compile all scripts into one video: --compile (video_designer, caption_maker)
```

## Agent Researcher

Scans 7 sources (50-item cap per source) across 3 tiers, deduplicates by URL and fuzzy title similarity, filters against 7-day history of previous briefs, and scores each item via Claude Opus with adaptive thinking (3 retries with exponential backoff).

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

**Scheduled mode**: `uv run python -m agent_researcher --scheduled` runs daily at 07:30.

## Script Writer

Reads the daily brief, generates 3 loglines per item (quiet part / betrayal / image you can't unsee), selects the best, and expands to full scripts with world-building synopsis and scene-by-scene breakdown — all items processed in parallel.

### First-time setup

```bash
uv run python -m script_writer.setup              # Characters + art style (interactive)
uv run python -m script_writer.setup characters    # Characters only
uv run python -m script_writer.setup art-style     # Art style only
uv run python -m script_writer.setup art-materials # Generate reference images (requires GOOGLE_API_KEY)
```

Creates `output/characters/<name>.md`, `output/art_style.md`, and `output/art_materials/canonical_characters.png`.

### Item selection

```bash
uv run python -m script_writer                     # Default: top 5 from brief
uv run python -m script_writer --pick 1,3,7        # Pick specific items (1-based)
uv run python -m script_writer --date 2026-03-14   # From specific date
```

Numbers 1-5 are top picks, 6-15 are also-notable items from the brief.

**Output**: `output/scripts/<YYYY-MM-DD>_<N>.md` + `.json` (N = 1-5). Each script has 1 scene with a cinematographic scene prompt (60-100 words), a visual riddle, dialogue, and audio direction. Duration fixed at 15 seconds.

## Static Shots Maker

Rewrites video-oriented scene prompts into image-optimized prompts via Claude (cinematographic composition: depth layering, explicit lighting, atmosphere), then generates 9:16 PNGs via Gemini. Scenes within each script are processed sequentially so each shot can serve as a visual reference for the next; scripts run in parallel.

**Output**: `output/static_shots/<YYYY-MM-DD>_<N>/scene_<M>.png` + `manifest.json` per script.

## Video Designer

Composes video prompts from scene details + character profiles via Claude, generates 15s clips with native audio (dialogue, sound effects, ambient) via xAI grok-imagine-video, then assembles per-script videos. Optionally compiles all scripts into one video with glitch transitions (`--compile`).

**Output**:
- `output/videos/<YYYY-MM-DD>_<N>/scene_<M>.mp4` — individual clips
- `output/videos/<YYYY-MM-DD>_<N>/script_video.mp4` — per-script assembly
- `output/videos/final_<YYYY-MM-DD>.mp4` — all scripts concatenated (only with `--compile`)

## Caption Maker

Transcribes spoken audio from generated videos via the OpenAI Whisper API, generates ASS subtitles with cumulative word reveal (words appear one by one as spoken), and burns styled captions into videos via ffmpeg. Clean minimal white style — Inter Bold, black outline, drop shadow, bottom 20%.

**Output**:
- `output/videos/<YYYY-MM-DD>_<N>/script_video_captioned.mp4` — captioned per-script video
- `output/videos/final_<YYYY-MM-DD>_captioned.mp4` — all scripts captioned and concatenated (only with `--compile`)
- Original uncaptioned files are untouched

## TikTok Publisher

Uploads each per-script video as a separate TikTok post. Prefers captioned videos, falls back to uncaptioned. Uses TikTok's Direct Post API with chunked file upload. Content is flagged as AI-generated.

```bash
# One-time: authenticate (opens browser)
uv run python -m tiktok_publisher auth

# Upload latest videos
uv run python -m tiktok_publisher upload

# Upload with options
uv run python -m tiktok_publisher upload --date 2026-04-02
uv run python -m tiktok_publisher upload --privacy PUBLIC_TO_EVERYONE
```

Requires `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, and `TIKTOK_REDIRECT_URI` from the [TikTok Developer portal](https://developers.tiktok.com/). The redirect URI must exactly match what's registered in your app settings. During auth, you'll be prompted to paste the callback URL from your browser.

## Project Structure

```
cartoon_maker/
├── agent_researcher/    # Stage 1: trend discovery & scoring
├── script_writer/       # Stage 2: script creation pipeline + setup tools
├── static_shots_maker/  # Stage 3: static shot generation
├── video_designer/      # Stage 4: video assembly & final output
├── caption_maker/       # Stage 5: whisper-based video captions
├── tiktok_publisher/    # Stage 6: TikTok video publishing
├── shared/              # Data contracts, config, LLM helpers, context loader
├── tests/               # 287 tests (pytest)
└── output/              # All generated artifacts (gitignored)
```

## Testing

```bash
uv run pytest tests/ -v             # Run all 287 tests
uv run pytest tests/test_dedup.py   # Single file
uv run ruff check .                 # Lint
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
| `TIKTOK_CLIENT_KEY` + `SECRET` | TikTok publishing | Publisher fails |
| Source credentials | Individual sources | Source skipped gracefully |
