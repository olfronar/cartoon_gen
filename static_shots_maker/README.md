# Static Shots Maker

Stage 3 of the cartoon_maker pipeline. Reads script JSON sidecars from `script_writer`, loads character profiles and art style, uses Claude to rewrite each scene's video-oriented prompt into an optimized image-generation prompt, then calls Gemini to produce 9:16 static shots (PNGs).

## Usage

```bash
# Generate shots from latest scripts
PYTHONPATH=. python -m static_shots_maker

# Generate shots for a specific date
PYTHONPATH=. python -m static_shots_maker --date 2026-03-15
```

## Requirements

- `GOOGLE_API_KEY` — required for Gemini image generation
- `ANTHROPIC_API_KEY` — optional, enables Claude prompt rewriting (falls back to regex stripping)

## Pipeline

1. Read script JSONs from `output/scripts/<date>_<N>.json`
2. Load character profiles + art style for context
3. For each script (parallel):
   - For each scene + end card (parallel):
     - Claude rewrites scene_prompt → image-optimized prompt
     - Gemini generates 9:16 PNG
     - Save to `output/static_shots/<date>_<N>/scene_<M>.png`
   - Write `manifest.json`

Semaphore caps concurrent Gemini calls (default 10).

## Output

```
output/static_shots/
├── 2026-03-15_1/
│   ├── scene_1.png
│   ├── scene_2.png
│   ├── scene_3.png
│   ├── end_card.png
│   └── manifest.json
```
