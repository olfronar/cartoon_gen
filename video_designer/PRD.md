# PRD: Video Designer Agent (Stage 4)

## Context

Stage 4 of the cartoon_maker pipeline. Reads static shots (PNGs) and script JSONs, loads character profiles and art style, uses Claude to compose an image-to-video prompt per scene, calls xAI `grok-imagine-video` to animate each static shot into a 15-second clip, then concatenates scene clips with glitch transitions and assembles the final cartoon video per script.

**Upstream**: `static_shots_maker` → `output/static_shots/<date>_<N>/` (PNGs + `manifest.json`) and `script_writer` → `output/scripts/<date>_<N>.json`
**Downstream**: Final cartoon videos ready for distribution

---

## Pipeline Architecture

```
output/static_shots/<date>_<N>/manifest.json  ──┐
output/static_shots/<date>_<N>/scene_*.png      │
output/scripts/<date>_<N>.json                  ├──▶ runner.run()
output/characters/*.md                          │
output/art_style.md                           ──┘
                                                     │
            ┌────────────────────────────────────────┘
            ▼
      For each script (Level 1 parallel via asyncio.gather):
        1. Read manifest.json → filter successful shots
        2. Read script JSON → get SceneScript details
        3. For each scene (Level 2 parallel via asyncio.gather):
           a. Claude composes image-to-video prompt from:
              scene_prompt + character profiles + art style + static shot reference
           b. xAI grok-imagine-video: image_url=base64(scene PNG) + prompt → 15s clip
           c. Save to output/videos/<date>_<N>/scene_<M>.mp4
        4. Generate end card video (same flow, scene_number=0)
        5. Concatenate scene clips with short glitch transitions → script video
        6. Write video_manifest.json

      Concatenate all script videos with longer glitch + low beep → final cartoon
      Write final_manifest.json
```

Semaphore caps total concurrent xAI video calls (default 5) to avoid rate limits.

---

## Module Structure

```
video_designer/
├── __init__.py              # (exists, empty)
├── __main__.py              # CLI: python -m video_designer [--date]
├── prompts.py               # SCENE_TO_VIDEO_PROMPT, END_CARD_TO_VIDEO_PROMPT
├── README.md                # (exists, update)
└── pipeline/
    ├── __init__.py
    ├── runner.py             # Async orchestrator (2-level gather + semaphore + concat)
    ├── manifest_reader.py    # Reads shots manifests + script JSONs → paired data
    ├── prompt_generator.py   # Claude scene→video prompt composition
    ├── video_generator.py    # xAI grok-imagine-video wrapper (image-to-video)
    └── assembler.py          # ffmpeg: concat clips with glitch transitions
```

---

## Output Structure

```
output/videos/
├── 2026-03-15_1/
│   ├── scene_1.mp4              # Individual scene clip (15s)
│   ├── scene_2.mp4
│   ├── scene_3.mp4
│   ├── end_card.mp4
│   ├── script_video.mp4         # Concatenated with short glitch transitions
│   └── video_manifest.json
├── 2026-03-15_2/
│   └── ...
├── final_2026-03-15.mp4         # All script videos concatenated with long glitch + beep
└── final_manifest.json
```

---

## Data Contracts (new in `shared/models.py`)

```python
@dataclass(slots=True)
class ClipResult:
    script_index: int
    scene_number: int        # 0 = end_card
    success: bool
    output_path: Path | None
    duration_seconds: float | None
    error: str | None

@dataclass(slots=True)
class VideoManifest:
    script_title: str
    script_index: int
    date: date
    clips: list[ClipResult]
    script_video_path: Path | None  # path to concatenated script video
    # to_dict() / from_dict() for JSON serialization
```

---

## Shared Layer Changes

### `shared/models.py`
- Add `ClipResult`, `VideoManifest` dataclasses

### `shared/config.py`
- Add fields: `video_model` (`grok-imagine-video`), `video_prompt_model` (`claude-opus-4-6`), `video_prompt_max_tokens` (4096), `video_max_concurrency` (5), `video_output_dir` (`output/videos`), `video_duration` (15), `video_resolution` (`480p`)

### `pyproject.toml`
- Add `video_designer` to `known-first-party`

### `.env.example`
- Already has `XAI_API_KEY` (used by agent_researcher) — add comment noting video_designer uses it too

---

## Key Modules

### `pipeline/manifest_reader.py`
- `read_manifests(target_date, shots_dir, scripts_dir) -> list[ScriptWithShots]`
- `ScriptWithShots` is a simple dataclass bundling `(index, CartoonScript, ShotsManifest)`
- Auto-detects latest date if none given
- Pairs each `manifest.json` with its corresponding `<date>_<N>.json` script
- Skips scripts where manifest has no successful shots

### `pipeline/prompt_generator.py`
- `generate_video_prompt(scene, script, context_block, client, model, max_tokens) -> str`
- Calls Claude with `SCENE_TO_VIDEO_PROMPT` template
- Composes a video generation prompt that combines: the original `scene_prompt`, `camera_movement`, `audio_direction`, `visual_gag`, character visual details from profiles, and art style
- The prompt instructs the video model to animate the static shot: what moves, camera motion, mood/atmosphere, pacing
- Fallback: if Claude fails, use the original `scene_prompt` directly (it was already written for video generation by script_writer)
- `generate_end_card_video_prompt(script, context_block, client, model, max_tokens) -> str` — same for end cards

### `pipeline/video_generator.py`
- `generate_video(prompt, image_path, output_path, client, model, duration, resolution) -> Path`
- Reads `image_path` PNG, encodes as base64 data URI
- Calls `client.video.generate(prompt=..., model=..., image_url=data_uri, duration=..., resolution=..., aspect_ratio="9:16")`
- The SDK handles polling internally and returns when done
- Downloads video from `response.url`, saves as MP4
- Uses `xai_sdk.Client` (sync) — wrapped in `asyncio.to_thread()` by runner

### `pipeline/assembler.py`
- `assemble_script_video(clip_paths, output_path, transition_duration) -> Path`
  - Takes ordered list of scene MP4 paths + end_card MP4
  - Concatenates with short glitch transition effect between scenes (default 0.3s)
  - Uses ffmpeg via subprocess: crossfade filter with `hlslice`/`glitch` overlay
- `assemble_final_video(script_video_paths, output_path, transition_duration) -> Path`
  - Concatenates script videos with longer glitch transition (default 1.0s)
  - Adds low beep sound effect during each transition
  - Beep audio: generated programmatically via ffmpeg `sine` audio source (200Hz, 0.5s, low volume)
- Both functions raise on ffmpeg failure

### `pipeline/runner.py`
- `run(settings, target_date) -> Path` (returns path to final video)
- Creates xAI client (`xai_sdk.Client`) + Anthropic client
- Loads context via `shared.context_loader`
- Reads manifests + scripts via `manifest_reader`
- Level 1: `asyncio.gather()` over all scripts → generates clips + script videos
- Level 2: `asyncio.gather()` over all scenes per script → generates individual clips
- Semaphore limits total concurrent xAI video calls
- After all scripts done: calls `assemble_final_video()` to produce the final cartoon
- Writes `video_manifest.json` per script directory + `final_manifest.json` at top level

### `prompts.py`
Two templates:
- **`SCENE_TO_VIDEO_PROMPT`**: Takes scene details + context, outputs video generation prompt. Rules: describe motion starting from the static shot (what moves, how camera travels), reference character animations, enforce art style, maintain 9:16 composition, include audio/mood direction, 80-200 words, affirmative only
- **`END_CARD_TO_VIDEO_PROMPT`**: Same for end cards (subtle animation: logo shimmer, credits scroll, etc.)

---

## Glitch Transition Effects

### Short glitch (between scenes within a script)
- Duration: 0.3 seconds
- Effect: RGB channel split + horizontal slice displacement
- ffmpeg filter: `rgbashift` + `noise` overlay during crossfade
- No audio effect

### Long glitch (between script videos)
- Duration: 1.0 seconds
- Effect: Same RGB split + slice displacement, more intense
- Audio: low-frequency beep (200Hz sine wave, 0.5s, -20dB)
- ffmpeg: `sine=frequency=200:duration=0.5` audio source mixed into transition

---

## Error Handling

| Failure | Behavior |
|---------|----------|
| `XAI_API_KEY` missing | RuntimeError at startup |
| `ANTHROPIC_API_KEY` missing | Warning, use original scene_prompt directly |
| Manifest not found for date | FileNotFoundError |
| No successful shots in manifest | Log, skip that script |
| Static shot PNG missing | Log, skip that scene, record `success: false` |
| Claude prompt composition fails | Log, fallback to original scene_prompt |
| xAI video generation fails | Log, record `success: false` in manifest |
| xAI video generation times out | Log, record `success: false` (SDK handles polling) |
| ffmpeg not installed | RuntimeError at assembly step |
| ffmpeg concat fails | Log, skip script video assembly, individual clips remain |
| All scene clips failed for a script | Log, skip script video + exclude from final |
| `< 1 script video produced` | Skip final assembly, return individual script videos |

---

## Implementation Phases

### Phase 1 — Shared layer
- New models: `ClipResult`, `VideoManifest`
- Config fields, dependency updates, env var comment
- Verify `xai_sdk` is already in dependencies (it is — used by agent_researcher)

### Phase 2 — Core modules
- `prompts.py` (templates)
- `manifest_reader.py` (reads shots manifests + pairs with scripts)
- `prompt_generator.py` (Claude video prompt composition)
- `video_generator.py` (xAI image-to-video wrapper)

### Phase 3 — Assembly
- `assembler.py` (ffmpeg glitch transitions + beep sound)

### Phase 4 — Orchestration
- `runner.py` (async orchestrator)
- `__main__.py` (CLI)

### Phase 5 — Tests
- `test_video_manifest_serialization.py`
- `test_manifest_reader.py`
- `test_video_prompt_generator.py`
- `test_video_generator.py`
- `test_assembler.py`
- `test_video_runner.py`

### Phase 6 — Docs
- Update README.md, CLAUDE.md, video_designer/README.md

---

## Verification

```bash
# All tests pass
pytest

# Lint clean
ruff check . && ruff format --check .

# Check ffmpeg is available
ffmpeg -version

# Manual smoke test
PYTHONPATH=. python -m video_designer --date 2026-03-15

# Check output
ls output/videos/2026-03-15_1/
cat output/videos/2026-03-15_1/video_manifest.json
ffprobe output/videos/final_2026-03-15.mp4
```

---

## Critical Files

| File | Action |
|------|--------|
| `shared/models.py` | Add `ClipResult`, `VideoManifest` |
| `shared/config.py` | Add `video_*` config fields |
| `pyproject.toml` | Update isort known-first-party |
| `.env.example` | Add comment about XAI_API_KEY for video |
| `video_designer/` (all new) | Full agent implementation |
