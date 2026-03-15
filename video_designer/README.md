# Video Designer

Stage 4 of the cartoon_maker pipeline. Reads static shots and script JSONs, uses Claude to compose video-generation prompts, generates 15-second 9:16 video clips via xAI grok-imagine-video, then assembles them into final cartoon videos with glitch transitions.

## Usage

```bash
# Generate videos from latest static shots
PYTHONPATH=. python -m video_designer

# Generate videos for a specific date
PYTHONPATH=. python -m video_designer --date 2026-03-15
```

## Requirements

- `XAI_API_KEY` — required for xAI grok-imagine-video generation
- `ANTHROPIC_API_KEY` — optional, enables Claude video prompt composition (falls back to original scene prompts)
- `ffmpeg` — required for video assembly with glitch transitions

## Pipeline

1. Read shots manifests from `output/static_shots/<date>_<N>/manifest.json`
2. Pair with script JSONs from `output/scripts/<date>_<N>.json`
3. Load character profiles + art style for context
4. For each script (parallel):
   - For each scene + end card (parallel):
     - Claude composes video prompt from scene details + character profiles + art style
     - xAI generates 15s clip from static shot PNG + prompt
     - Save to `output/videos/<date>_<N>/scene_<M>.mp4`
   - Concatenate clips with short glitch transitions → `script_video.mp4`
   - Write `video_manifest.json`
5. Concatenate all script videos with longer glitch + beep → `final_<date>.mp4`

Semaphore caps concurrent xAI calls (default 5).

## Output

```
output/videos/
├── 2026-03-15_1/
│   ├── scene_1.mp4
│   ├── scene_2.mp4
│   ├── end_card.mp4
│   ├── script_video.mp4
│   └── video_manifest.json
├── 2026-03-15_2/
│   └── ...
└── final_2026-03-15.mp4
```
