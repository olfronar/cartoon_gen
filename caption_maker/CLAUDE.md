# Caption Maker Internals

Pipeline: find script_video.mp4 files -> transcribe via OpenAI Whisper API (word-level timestamps) -> generate drawtext filter chain (cumulative word reveal) -> burn subtitles via ffmpeg drawtext -> reassemble final captioned video. No LLM calls.

## Pipeline stages

- **Video finder** (`pipeline/video_finder.py`): Thin wrapper re-exporting `find_script_videos()` from `shared/utils.py`. Finds `script_video.mp4` files by date in `output/videos/`. Auto-detects latest date if none specified.
- **Transcriber** (`pipeline/transcriber.py`): Uses OpenAI Whisper API (`whisper-1`) with word-level timestamps via `verbose_json` response format. Requires `OPENAI_API_KEY`. Internal dataclasses (`WordTiming`, `Segment`, `Transcription`) -- not in `shared/models.py` as they don't participate in the inter-agent data contract.
- **Filter generator** (`pipeline/filter_generator.py`): Generates ffmpeg `drawtext` filter chain for cumulative word reveal -- each word appears one by one as spoken via timed `enable='between(t,...)'` expressions. Font size scales proportionally with video height. Clean minimal white style (Inter Bold, 3px black outline, drop shadow, bottom 20%). Writes filter to `captions_filter.txt` for debugging.
- **Subtitle burner** (`pipeline/subtitle_burner.py`): Burns subtitles into video via ffmpeg `-filter_script:v` with the drawtext filter chain. Uses `run_ffmpeg()` and `ENCODE_ARGS` from `shared/ffmpeg.py`.
- **Runner** (`pipeline/runner.py`): Async orchestrator. Parallel across scripts via `asyncio.gather()`. Skips silent/instrumental videos gracefully. Reuses `assemble_final_video` from `shared.assembler` for final assembly.

## Output

- `output/videos/<YYYY-MM-DD>_<N>/captions_filter.txt` -- intermediate drawtext filter script (kept for debugging).
- `output/videos/<YYYY-MM-DD>_<N>/script_video_captioned.mp4` -- captioned per-script video.
- `output/videos/final_<YYYY-MM-DD>_captioned.mp4` -- all captioned scripts assembled with glitch transitions (only with `--compile` flag).
- Original uncaptioned files are untouched (non-destructive).
