# Script Writer

Transforms the daily comedy brief (5 top-scored news items) into production-ready cartoon scripts. Each script is formatted for xAI video generation, with every scene doubling as a video generation prompt.

## Setup

Before generating scripts, define your characters and art style:

```bash
PYTHONPATH=. python -m script_writer.setup              # Both characters + art style
PYTHONPATH=. python -m script_writer.setup characters    # Characters only
PYTHONPATH=. python -m script_writer.setup art-style     # Art style only
```

The setup tool runs an interactive interview via Claude to build character profiles (`output/characters/*.md`) and an art style guide (`output/art_style.md`).

## Usage

```bash
PYTHONPATH=. python -m script_writer                      # Auto-detect latest brief
PYTHONPATH=. python -m script_writer --date 2026-03-14    # Specific date
```

## Pipeline

1. **Brief ingestion** — Read `output/briefs/YYYY-MM-DD.json` + character/art style files
2. **Logline generation** — 3 loglines per news item (absurdist / satirical / surreal)
3. **Logline selection** — Pick the best 1 of 3 per item
4. **Script expansion** — Synopsis + full script with scene breakdown (5 items in parallel)
5. **Output** — Write `output/scripts/<date>_<N>.md` + `.json` per script

## Output

- `output/scripts/<YYYY-MM-DD>_<N>.md` — Human-readable script
- `output/scripts/<YYYY-MM-DD>_<N>.json` — Machine-readable for static_shots_maker

Each script contains 5-8 scenes with scene prompts (50-150 words each, xAI golden formula), dialogue, visual gags, audio direction, and camera movements.
