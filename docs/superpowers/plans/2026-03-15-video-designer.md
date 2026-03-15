# Video Designer Agent Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Animate static shots into 15-second video clips via xAI grok-imagine-video, then assemble them into final cartoon videos with glitch transitions.

**Architecture:** Two-level async pipeline (parallel across scripts, parallel across scenes within each script). Claude rewrites scene prompts into video-generation prompts. xAI generates image-to-video clips from static shot PNGs. ffmpeg concatenates clips with glitch transitions (short between scenes, long with beep between scripts).

**Tech Stack:** Python 3.10+, xai_sdk (image-to-video), anthropic (prompt composition), ffmpeg (video assembly), asyncio (concurrency)

**PRD:** `video_designer/PRD.md`

---

## File Structure

| File | Responsibility |
|------|----------------|
| `shared/models.py` | Add `ClipResult`, `VideoManifest` dataclasses |
| `shared/config.py` | Add `video_*` config fields + `load_settings()` wiring |
| `pyproject.toml` | Add `video_designer` to isort known-first-party |
| `.env.example` | Comment noting XAI_API_KEY also used for video |
| `video_designer/pipeline/__init__.py` | Empty package init |
| `video_designer/prompts.py` | `SCENE_TO_VIDEO_PROMPT`, `END_CARD_TO_VIDEO_PROMPT` templates |
| `video_designer/pipeline/manifest_reader.py` | Read shots manifests + pair with script JSONs |
| `video_designer/pipeline/prompt_generator.py` | Claude scene→video prompt composition |
| `video_designer/pipeline/video_generator.py` | xAI grok-imagine-video wrapper |
| `video_designer/pipeline/assembler.py` | ffmpeg glitch transitions + final assembly |
| `video_designer/pipeline/runner.py` | Async orchestrator |
| `video_designer/__main__.py` | CLI entry point |
| `video_designer/README.md` | Agent documentation |
| `tests/test_video_models.py` | ClipResult/VideoManifest serialization tests |
| `tests/test_manifest_reader.py` | Manifest + script pairing tests |
| `tests/test_video_prompt_generator.py` | Prompt composition + fallback tests |
| `tests/test_video_generator.py` | xAI wrapper tests (mocked) |
| `tests/test_assembler.py` | ffmpeg assembly tests (mocked subprocess) |
| `tests/test_video_runner.py` | Full pipeline integration tests (all mocked) |
| `CLAUDE.md` | Add Video Designer Internals section |

---

## Chunk 1: Shared Layer + Data Contracts

### Task 1: Add ClipResult and VideoManifest to shared/models.py

**Files:**
- Modify: `shared/models.py:139-163` (append after ShotsManifest)
- Test: `tests/test_video_models.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_video_models.py`:

```python
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from shared.models import ClipResult, VideoManifest


class TestClipResult:
    def test_creation(self):
        clip = ClipResult(
            script_index=1,
            scene_number=1,
            success=True,
            output_path=Path("output/videos/2026-03-15_1/scene_1.mp4"),
            duration_seconds=15.0,
            error=None,
        )
        assert clip.success is True
        assert clip.duration_seconds == 15.0

    def test_failed_clip(self):
        clip = ClipResult(
            script_index=1,
            scene_number=2,
            success=False,
            output_path=None,
            duration_seconds=None,
            error="xAI timeout",
        )
        assert clip.success is False
        assert clip.error == "xAI timeout"


class TestVideoManifest:
    def test_to_dict(self):
        manifest = VideoManifest(
            script_title="Test Episode",
            script_index=1,
            date=date(2026, 3, 15),
            clips=[
                ClipResult(
                    script_index=1,
                    scene_number=1,
                    success=True,
                    output_path=Path("scene_1.mp4"),
                    duration_seconds=15.0,
                    error=None,
                ),
            ],
            script_video_path=Path("script_video.mp4"),
        )
        data = manifest.to_dict()
        assert data["date"] == "2026-03-15"
        assert data["clips"][0]["output_path"] == "scene_1.mp4"
        assert data["script_video_path"] == "script_video.mp4"

    def test_to_dict_json_serializable(self):
        manifest = VideoManifest(
            script_title="Test",
            script_index=1,
            date=date(2026, 3, 15),
            clips=[],
            script_video_path=None,
        )
        json_str = json.dumps(manifest.to_dict())
        assert isinstance(json_str, str)

    def test_to_dict_none_paths(self):
        manifest = VideoManifest(
            script_title="Test",
            script_index=1,
            date=date(2026, 3, 15),
            clips=[
                ClipResult(
                    script_index=1,
                    scene_number=1,
                    success=False,
                    output_path=None,
                    duration_seconds=None,
                    error="failed",
                ),
            ],
            script_video_path=None,
        )
        data = manifest.to_dict()
        assert data["clips"][0]["output_path"] is None
        assert data["script_video_path"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_video_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'ClipResult'`

- [ ] **Step 3: Write minimal implementation**

Append to `shared/models.py` after the `ShotsManifest` class (after line 163):

```python


# --- Video Designer models ---


@dataclass(slots=True)
class ClipResult:
    script_index: int
    scene_number: int  # 0 = end_card
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
    script_video_path: Path | None

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        data = asdict(self)
        data["date"] = self.date.isoformat()
        for clip in data["clips"]:
            path = clip["output_path"]
            clip["output_path"] = str(path) if path else None
        svp = data["script_video_path"]
        data["script_video_path"] = str(svp) if svp else None
        return data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_video_models.py -v`
Expected: PASS (all 5 tests)

- [ ] **Step 5: Commit**

```bash
git add shared/models.py tests/test_video_models.py
git commit -m "Add ClipResult and VideoManifest data contracts for video_designer"
```

---

### Task 2: Add video config fields to shared/config.py

**Files:**
- Modify: `shared/config.py:50-56` (append after Static Shots section)
- Modify: `shared/config.py:80-86` (append in load_settings)
- Modify: `pyproject.toml:39` (isort known-first-party)
- Modify: `.env.example:28` (comment)

- [ ] **Step 1: Add config fields to Settings dataclass**

Add after line 56 (after `shots_output_dir`) in `shared/config.py`:

```python

    # Video Designer
    video_model: str = "grok-imagine-video"
    video_prompt_model: str = "claude-opus-4-6"
    video_prompt_max_tokens: int = 4096
    video_max_concurrency: int = 5
    video_output_dir: Path = field(default_factory=lambda: Path("output/videos"))
    video_duration: int = 15
    video_resolution: str = "480p"
```

- [ ] **Step 2: Wire fields in load_settings()**

Add after line 85 (`shots_output_dir=...`) in `shared/config.py`:

```python
        video_model=values.get("VIDEO_MODEL", "grok-imagine-video"),
        video_prompt_model=values.get("VIDEO_PROMPT_MODEL", "claude-opus-4-6"),
        video_prompt_max_tokens=int(values.get("VIDEO_PROMPT_MAX_TOKENS", "4096")),
        video_max_concurrency=int(values.get("VIDEO_MAX_CONCURRENCY", "5")),
        video_output_dir=Path(values.get("VIDEO_OUTPUT_DIR", "output/videos")),
        video_duration=int(values.get("VIDEO_DURATION", "15")),
        video_resolution=values.get("VIDEO_RESOLUTION", "480p"),
```

- [ ] **Step 3: Update pyproject.toml isort**

Change line 39 in `pyproject.toml`:

```toml
known-first-party = ["shared", "agent_researcher", "script_writer", "static_shots_maker", "video_designer"]
```

- [ ] **Step 4: Update .env.example**

Add after the `GOOGLE_API_KEY=` line in `.env.example`:

```
# xAI API key (used by agent_researcher for trends + video_designer for video generation)
# XAI_API_KEY is already defined above — no duplicate needed
```

Wait — `XAI_API_KEY` is NOT in `.env.example`. Check `agent_researcher` section. It IS there on line 10 as `XAI_API_KEY=`. Add a comment next to it:

Change line 10 of `.env.example` from:
```
XAI_API_KEY=
```
to:
```
XAI_API_KEY=
# ^ Also used by video_designer for grok-imagine-video generation
```

- [ ] **Step 5: Run existing tests to verify no regressions**

Run: `uv run pytest tests/test_config.py tests/test_video_models.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add shared/config.py pyproject.toml .env.example
git commit -m "Add video_designer config fields and update isort/env"
```

---

## Chunk 2: Core Modules — Prompts, Manifest Reader, Prompt Generator

### Task 3: Create prompt templates

**Files:**
- Create: `video_designer/prompts.py`

- [ ] **Step 1: Write prompt templates**

Create `video_designer/prompts.py`:

```python
from __future__ import annotations

SCENE_TO_VIDEO_PROMPT = """\
You are an expert at composing video generation prompts that animate a static \
image into a 15-second video clip. Your output will be fed directly to an \
image-to-video AI model along with the static shot.

{context}

---

Compose a video generation prompt to animate this static scene shot.

**Episode title**: {title}
**Scene {scene_number}**: {scene_title}
**Setting**: {setting}
**Original scene prompt**: {scene_prompt}
**Camera movement**: {camera_movement}
**Visual gag**: {visual_gag}
**Audio direction**: {audio_direction}
**Duration**: {duration_seconds} seconds

Rules:
1. Describe MOTION starting from the static shot — what moves, how, and when.
2. Include camera movement: {camera_movement}.
3. Reference character animations using their visual details from profiles above.
4. Enforce the art style from the style guide above.
5. Maintain 9:16 vertical composition throughout.
6. Include mood, atmosphere, and audio direction.
7. Use ONLY affirmative descriptions — never say "no", "without", "don't", "avoid".
8. Front-load the key motion in the first 20-30 words.
9. Output ONLY the video prompt text, 80-200 words. No commentary.
"""

END_CARD_TO_VIDEO_PROMPT = """\
You are an expert at composing video generation prompts that animate a static \
end card image into a short video clip. Your output will be fed directly to an \
image-to-video AI model along with the static end card.

{context}

---

Compose a video generation prompt to subtly animate this end card.

**Episode title**: {title}
**Original end-card prompt**: {end_card_prompt}

Rules:
1. Keep animation subtle — logo shimmer, gentle particle effects, credits fade-in.
2. Enforce the art style from the style guide above.
3. Maintain 9:16 vertical composition.
4. Use ONLY affirmative descriptions — never say "no", "without", "don't", "avoid".
5. Output ONLY the video prompt text, 50-120 words. No commentary.
"""
```

- [ ] **Step 2: Commit**

```bash
git add video_designer/prompts.py
git commit -m "Add video_designer prompt templates"
```

---

### Task 4: Create manifest_reader.py

**Files:**
- Create: `video_designer/pipeline/__init__.py`
- Create: `video_designer/pipeline/manifest_reader.py`
- Test: `tests/test_manifest_reader.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_manifest_reader.py`:

```python
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from shared.models import ShotResult, ShotsManifest
from tests.conftest import make_script, write_script_json
from video_designer.pipeline.manifest_reader import read_manifests


def _write_manifest(shots_dir: Path, date_str: str, index: int, success: bool = True) -> None:
    """Write a shots manifest with one successful scene + end card."""
    scene_path = shots_dir / f"{date_str}_{index}" / "scene_1.png"
    end_card_path = shots_dir / f"{date_str}_{index}" / "end_card.png"
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    scene_path.write_bytes(b"fake png")
    end_card_path.write_bytes(b"fake png")

    manifest = ShotsManifest(
        script_title="Test",
        script_index=index,
        date=date.fromisoformat(date_str),
        shots=[
            ShotResult(
                script_index=index,
                scene_number=1,
                success=success,
                output_path=scene_path if success else None,
                error=None if success else "failed",
            ),
            ShotResult(
                script_index=index,
                scene_number=0,
                success=success,
                output_path=end_card_path if success else None,
                error=None if success else "failed",
            ),
        ],
    )
    manifest_path = shots_dir / f"{date_str}_{index}" / "manifest.json"
    manifest_path.write_text(json.dumps(manifest.to_dict()), encoding="utf-8")


class TestManifestReader:
    def test_reads_paired_data(self, tmp_path):
        shots_dir = tmp_path / "static_shots"
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()

        write_script_json(scripts_dir, "2026-03-15", 1, title="Ep 1")
        _write_manifest(shots_dir, "2026-03-15", 1)

        results = read_manifests(
            target_date=date(2026, 3, 15),
            shots_dir=shots_dir,
            scripts_dir=scripts_dir,
        )
        assert len(results) == 1
        assert results[0].index == 1
        assert results[0].script.title == "Ep 1"
        assert len(results[0].manifest.shots) == 2

    def test_auto_detect_latest(self, tmp_path):
        shots_dir = tmp_path / "static_shots"
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()

        write_script_json(scripts_dir, "2026-03-14", 1)
        _write_manifest(shots_dir, "2026-03-14", 1)
        write_script_json(scripts_dir, "2026-03-15", 1)
        _write_manifest(shots_dir, "2026-03-15", 1)

        results = read_manifests(shots_dir=shots_dir, scripts_dir=scripts_dir)
        assert results[0].script.date == date(2026, 3, 15)

    def test_skips_no_successful_shots(self, tmp_path):
        shots_dir = tmp_path / "static_shots"
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()

        write_script_json(scripts_dir, "2026-03-15", 1)
        _write_manifest(shots_dir, "2026-03-15", 1, success=False)

        results = read_manifests(
            target_date=date(2026, 3, 15),
            shots_dir=shots_dir,
            scripts_dir=scripts_dir,
        )
        assert len(results) == 0

    def test_missing_shots_dir(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_manifests(
                shots_dir=tmp_path / "nonexistent",
                scripts_dir=tmp_path,
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_manifest_reader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'video_designer.pipeline'`

- [ ] **Step 3: Create pipeline package init**

Create empty `video_designer/pipeline/__init__.py`.

- [ ] **Step 4: Write manifest_reader implementation**

Create `video_designer/pipeline/manifest_reader.py`:

```python
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from shared.models import CartoonScript, ShotsManifest, ShotResult

logger = logging.getLogger(__name__)

_INDEX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_(\d+)$")


@dataclass(slots=True)
class ScriptWithShots:
    index: int
    script: CartoonScript
    manifest: ShotsManifest


def read_manifests(
    target_date: date | None = None,
    shots_dir: Path | None = None,
    scripts_dir: Path | None = None,
) -> list[ScriptWithShots]:
    """Read shots manifests paired with their script JSONs.

    Returns list of ScriptWithShots sorted by index.
    Skips scripts where manifest has no successful shots.
    """
    shots_dir = shots_dir or Path("output/static_shots")
    scripts_dir = scripts_dir or Path("output/scripts")

    if not shots_dir.exists():
        raise FileNotFoundError(f"Shots directory not found: {shots_dir}")

    if target_date is None:
        target_date = _find_latest_date(shots_dir)

    date_str = target_date.isoformat()
    results: list[ScriptWithShots] = []

    for manifest_dir in sorted(shots_dir.glob(f"{date_str}_*")):
        if not manifest_dir.is_dir():
            continue
        match = _INDEX_RE.match(manifest_dir.name)
        if not match:
            continue
        index = int(match.group(1))

        manifest_path = manifest_dir / "manifest.json"
        script_path = scripts_dir / f"{date_str}_{index}.json"

        if not manifest_path.exists() or not script_path.exists():
            logger.warning("Missing manifest or script for index %d, skipping", index)
            continue

        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = _parse_manifest(manifest_data)

            script_data = json.loads(script_path.read_text(encoding="utf-8"))
            script = CartoonScript.from_dict(script_data)
        except Exception:
            logger.exception("Failed to parse manifest/script for index %d, skipping", index)
            continue

        # Skip if no successful shots
        if not any(s.success for s in manifest.shots):
            logger.warning("No successful shots for script %d, skipping", index)
            continue

        results.append(ScriptWithShots(index=index, script=script, manifest=manifest))

    if not results:
        raise FileNotFoundError(
            f"No valid manifests with successful shots for {date_str} in {shots_dir}"
        )

    return results


def _find_latest_date(shots_dir: Path) -> date:
    """Find the most recent date by scanning subdirectory names."""
    dates: set[str] = set()
    for path in shots_dir.iterdir():
        if path.is_dir() and _INDEX_RE.match(path.name):
            dates.add(path.name.rsplit("_", 1)[0])
    if not dates:
        raise FileNotFoundError(f"No shot directories found in {shots_dir}")
    return date.fromisoformat(max(dates))


def _parse_manifest(data: dict) -> ShotsManifest:
    """Parse a manifest dict into a ShotsManifest."""
    return ShotsManifest(
        script_title=data["script_title"],
        script_index=data["script_index"],
        date=date.fromisoformat(data["date"]),
        shots=[
            ShotResult(
                script_index=s["script_index"],
                scene_number=s["scene_number"],
                success=s["success"],
                output_path=Path(s["output_path"]) if s["output_path"] else None,
                error=s["error"],
            )
            for s in data["shots"]
        ],
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_manifest_reader.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 6: Commit**

```bash
git add video_designer/pipeline/__init__.py video_designer/pipeline/manifest_reader.py tests/test_manifest_reader.py
git commit -m "Add manifest_reader: pairs shots manifests with script JSONs"
```

---

### Task 5: Create prompt_generator.py

**Files:**
- Create: `video_designer/pipeline/prompt_generator.py`
- Test: `tests/test_video_prompt_generator.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_video_prompt_generator.py`:

```python
from __future__ import annotations

from unittest.mock import MagicMock, patch

from tests.conftest import make_scene, make_script
from video_designer.pipeline.prompt_generator import (
    generate_end_card_video_prompt,
    generate_video_prompt,
)


class TestGenerateVideoPrompt:
    @patch("video_designer.pipeline.prompt_generator.call_llm_text")
    def test_calls_claude(self, mock_llm):
        mock_llm.return_value = "  A robot slowly turns its head  "
        scene = make_scene()
        script = make_script()

        result = generate_video_prompt(
            scene, script, "context", MagicMock(), "claude-opus-4-6", 4096
        )
        assert result == "A robot slowly turns its head"
        mock_llm.assert_called_once()

    @patch("video_designer.pipeline.prompt_generator.call_llm_text")
    def test_fallback_on_error(self, mock_llm):
        mock_llm.side_effect = RuntimeError("API error")
        scene = make_scene(scene_prompt="A robot chef in a kitchen.")
        script = make_script()

        result = generate_video_prompt(
            scene, script, "context", MagicMock(), "claude-opus-4-6", 4096
        )
        assert result == "A robot chef in a kitchen."


class TestGenerateEndCardVideoPrompt:
    @patch("video_designer.pipeline.prompt_generator.call_llm_text")
    def test_calls_claude(self, mock_llm):
        mock_llm.return_value = "Logo gently shimmers"
        script = make_script()

        result = generate_end_card_video_prompt(
            script, "context", MagicMock(), "claude-opus-4-6", 4096
        )
        assert result == "Logo gently shimmers"

    @patch("video_designer.pipeline.prompt_generator.call_llm_text")
    def test_fallback_on_error(self, mock_llm):
        mock_llm.side_effect = RuntimeError("API error")
        script = make_script(end_card_prompt="Show the logo.")

        result = generate_end_card_video_prompt(
            script, "context", MagicMock(), "claude-opus-4-6", 4096
        )
        assert result == "Show the logo."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_video_prompt_generator.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

Create `video_designer/pipeline/prompt_generator.py`:

```python
from __future__ import annotations

import logging

from shared.models import CartoonScript, SceneScript
from shared.utils import call_llm_text
from video_designer.prompts import END_CARD_TO_VIDEO_PROMPT, SCENE_TO_VIDEO_PROMPT

logger = logging.getLogger(__name__)


def generate_video_prompt(
    scene: SceneScript,
    script: CartoonScript,
    context_block: str,
    client,
    model: str,
    max_tokens: int,
) -> str:
    """Compose a video generation prompt for a scene."""
    prompt = SCENE_TO_VIDEO_PROMPT.format(
        context=context_block,
        title=script.title,
        scene_number=scene.scene_number,
        scene_title=scene.scene_title,
        setting=scene.setting,
        scene_prompt=scene.scene_prompt,
        camera_movement=scene.camera_movement,
        visual_gag=scene.visual_gag or "None",
        audio_direction=scene.audio_direction,
        duration_seconds=scene.duration_seconds,
    )
    try:
        return call_llm_text(client, prompt, model, max_tokens).strip()
    except Exception:
        logger.exception(
            "Claude video prompt failed for scene %d, using original scene_prompt",
            scene.scene_number,
        )
        return scene.scene_prompt


def generate_end_card_video_prompt(
    script: CartoonScript,
    context_block: str,
    client,
    model: str,
    max_tokens: int,
) -> str:
    """Compose a video generation prompt for an end card."""
    prompt = END_CARD_TO_VIDEO_PROMPT.format(
        context=context_block,
        title=script.title,
        end_card_prompt=script.end_card_prompt,
    )
    try:
        return call_llm_text(client, prompt, model, max_tokens).strip()
    except Exception:
        logger.exception("Claude video prompt failed for end card, using original")
        return script.end_card_prompt
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_video_prompt_generator.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 5: Commit**

```bash
git add video_designer/pipeline/prompt_generator.py tests/test_video_prompt_generator.py
git commit -m "Add video prompt generator with Claude composition + fallback"
```

---

## Chunk 3: Video Generator + Assembler

### Task 6: Create video_generator.py (xAI wrapper)

**Files:**
- Create: `video_designer/pipeline/video_generator.py`
- Test: `tests/test_video_generator.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_video_generator.py`:

```python
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from video_designer.pipeline.video_generator import generate_video


class TestGenerateVideo:
    @patch("video_designer.pipeline.video_generator.httpx")
    def test_generates_and_saves(self, mock_httpx, tmp_path):
        image_path = tmp_path / "scene_1.png"
        image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        output_path = tmp_path / "scene_1.mp4"

        mock_response = MagicMock()
        mock_response.url = "https://example.com/video.mp4"

        mock_client = MagicMock()
        mock_client.video.generate.return_value = mock_response

        mock_http_response = MagicMock()
        mock_http_response.content = b"fake mp4 data"
        mock_httpx.get.return_value = mock_http_response

        result = generate_video(
            prompt="A robot moves",
            image_path=image_path,
            output_path=output_path,
            client=mock_client,
            model="grok-imagine-video",
            duration=15,
            resolution="480p",
        )

        assert result == output_path
        assert output_path.read_bytes() == b"fake mp4 data"
        mock_client.video.generate.assert_called_once()

        # Verify image_url was base64 encoded
        call_kwargs = mock_client.video.generate.call_args[1]
        assert call_kwargs["image_url"].startswith("data:image/png;base64,")
        assert call_kwargs["duration"] == 15
        assert call_kwargs["aspect_ratio"] == "9:16"

    def test_raises_on_missing_image(self, tmp_path):
        output_path = tmp_path / "scene_1.mp4"
        mock_client = MagicMock()

        with pytest.raises(FileNotFoundError):
            generate_video(
                prompt="test",
                image_path=tmp_path / "nonexistent.png",
                output_path=output_path,
                client=mock_client,
                model="grok-imagine-video",
                duration=15,
                resolution="480p",
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_video_generator.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

Create `video_designer/pipeline/video_generator.py`:

```python
from __future__ import annotations

import base64
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


def generate_video(
    prompt: str,
    image_path: Path,
    output_path: Path,
    client,
    model: str,
    duration: int,
    resolution: str,
) -> Path:
    """Generate a video from a static shot via xAI grok-imagine-video.

    Reads the PNG at image_path, encodes as base64 data URI, sends to xAI
    image-to-video API. Downloads the resulting video and saves as MP4.
    Caller must ensure output_path's parent directory exists.

    Args:
        prompt: Video generation prompt text.
        image_path: Path to the source PNG static shot.
        output_path: Where to save the MP4 file.
        client: xai_sdk.Client instance.
        model: xAI model name (e.g. "grok-imagine-video").
        duration: Video duration in seconds (1-15).
        resolution: Video resolution (e.g. "480p", "720p").

    Returns:
        The output_path on success.

    Raises:
        FileNotFoundError: If image_path does not exist.
        RuntimeError: If video generation or download fails.
    """
    if not image_path.exists():
        raise FileNotFoundError(f"Static shot not found: {image_path}")

    # Encode image as base64 data URI
    image_bytes = image_path.read_bytes()
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_uri = f"data:image/png;base64,{b64}"

    # Call xAI image-to-video (SDK handles polling)
    response = client.video.generate(
        prompt=prompt,
        model=model,
        image_url=data_uri,
        duration=duration,
        resolution=resolution,
        aspect_ratio="9:16",
    )

    if not response.url:
        raise RuntimeError("xAI returned no video URL")

    # Download video
    http_response = httpx.get(response.url)
    output_path.write_bytes(http_response.content)

    logger.info("Saved video: %s", output_path)
    return output_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_video_generator.py -v`
Expected: PASS (all 2 tests)

- [ ] **Step 5: Commit**

```bash
git add video_designer/pipeline/video_generator.py tests/test_video_generator.py
git commit -m "Add video_generator: xAI image-to-video wrapper"
```

---

### Task 7: Create assembler.py (ffmpeg glitch transitions)

**Files:**
- Create: `video_designer/pipeline/assembler.py`
- Test: `tests/test_assembler.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_assembler.py`:

```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from video_designer.pipeline.assembler import assemble_final_video, assemble_script_video


class TestAssembleScriptVideo:
    @patch("video_designer.pipeline.assembler.subprocess")
    def test_calls_ffmpeg(self, mock_subprocess, tmp_path):
        mock_subprocess.run.return_value = mock_subprocess.CompletedProcess(
            args=[], returncode=0
        )

        clips = [tmp_path / "scene_1.mp4", tmp_path / "scene_2.mp4"]
        output = tmp_path / "script_video.mp4"

        result = assemble_script_video(clips, output)
        assert result == output
        mock_subprocess.run.assert_called_once()

        cmd = mock_subprocess.run.call_args[0][0]
        assert cmd[0] == "ffmpeg"
        assert "-y" in cmd

    def test_raises_on_empty_clips(self, tmp_path):
        with pytest.raises(ValueError, match="at least 1"):
            assemble_script_video([], tmp_path / "out.mp4")

    @patch("video_designer.pipeline.assembler.subprocess")
    def test_single_clip_copies(self, mock_subprocess, tmp_path):
        """Single clip: just copy, no transitions."""
        mock_subprocess.run.return_value = mock_subprocess.CompletedProcess(
            args=[], returncode=0
        )

        clips = [tmp_path / "scene_1.mp4"]
        output = tmp_path / "script_video.mp4"

        assemble_script_video(clips, output)
        mock_subprocess.run.assert_called_once()

    @patch("video_designer.pipeline.assembler.subprocess")
    def test_raises_on_ffmpeg_failure(self, mock_subprocess, tmp_path):
        mock_subprocess.run.return_value = mock_subprocess.CompletedProcess(
            args=[], returncode=1, stderr="error"
        )
        mock_subprocess.CalledProcessError = Exception

        clips = [tmp_path / "a.mp4", tmp_path / "b.mp4"]
        with pytest.raises(RuntimeError, match="ffmpeg"):
            assemble_script_video(clips, tmp_path / "out.mp4")


class TestAssembleFinalVideo:
    @patch("video_designer.pipeline.assembler.subprocess")
    def test_calls_ffmpeg_with_beep(self, mock_subprocess, tmp_path):
        mock_subprocess.run.return_value = mock_subprocess.CompletedProcess(
            args=[], returncode=0
        )

        scripts = [tmp_path / "s1.mp4", tmp_path / "s2.mp4"]
        output = tmp_path / "final.mp4"

        result = assemble_final_video(scripts, output)
        assert result == output
        mock_subprocess.run.assert_called_once()

    def test_raises_on_empty(self, tmp_path):
        with pytest.raises(ValueError, match="at least 1"):
            assemble_final_video([], tmp_path / "out.mp4")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_assembler.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

Create `video_designer/pipeline/assembler.py`:

```python
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def assemble_script_video(
    clip_paths: list[Path],
    output_path: Path,
    transition_duration: float = 0.3,
) -> Path:
    """Concatenate scene clips with short glitch transitions.

    Uses ffmpeg xfade filter with RGB shift + noise for glitch effect.
    For a single clip, copies without transition.

    Args:
        clip_paths: Ordered list of scene MP4 paths.
        output_path: Where to save the concatenated video.
        transition_duration: Glitch transition duration in seconds.

    Returns:
        The output_path on success.
    """
    if not clip_paths:
        raise ValueError("assemble_script_video requires at least 1 clip")

    if len(clip_paths) == 1:
        # Single clip: just re-mux
        cmd = [
            "ffmpeg", "-y",
            "-i", str(clip_paths[0]),
            "-c", "copy",
            str(output_path),
        ]
    else:
        cmd = _build_glitch_concat_cmd(clip_paths, output_path, transition_duration)

    _run_ffmpeg(cmd)
    logger.info("Script video assembled: %s", output_path)
    return output_path


def assemble_final_video(
    script_video_paths: list[Path],
    output_path: Path,
    transition_duration: float = 1.0,
) -> Path:
    """Concatenate script videos with longer glitch transitions + beep sound.

    Uses ffmpeg with:
    - xfade glitch transitions (1.0s default)
    - 200Hz sine wave beep (-20dB, 0.5s) during each transition

    Args:
        script_video_paths: Ordered list of script video MP4 paths.
        output_path: Where to save the final cartoon.
        transition_duration: Glitch transition duration in seconds.

    Returns:
        The output_path on success.
    """
    if not script_video_paths:
        raise ValueError("assemble_final_video requires at least 1 script video")

    if len(script_video_paths) == 1:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(script_video_paths[0]),
            "-c", "copy",
            str(output_path),
        ]
    else:
        cmd = _build_final_concat_cmd(
            script_video_paths, output_path, transition_duration
        )

    _run_ffmpeg(cmd)
    logger.info("Final video assembled: %s", output_path)
    return output_path


def _build_glitch_concat_cmd(
    clip_paths: list[Path], output_path: Path, transition_duration: float
) -> list[str]:
    """Build ffmpeg command for glitch-transition concatenation."""
    cmd = ["ffmpeg", "-y"]
    for clip in clip_paths:
        cmd.extend(["-i", str(clip)])

    # Build xfade filter chain between consecutive clips
    filters = []
    prev = "[0:v]"
    for i in range(1, len(clip_paths)):
        out = f"[v{i}]" if i < len(clip_paths) - 1 else "[vout]"
        filters.append(
            f"{prev}[{i}:v]xfade=transition=hlslice:"
            f"duration={transition_duration}:offset=0{out}"
        )
        prev = out

    cmd.extend(["-filter_complex", ";".join(filters), "-map", "[vout]"])
    cmd.extend(["-c:v", "libx264", "-preset", "fast", str(output_path)])
    return cmd


def _build_final_concat_cmd(
    paths: list[Path], output_path: Path, transition_duration: float
) -> list[str]:
    """Build ffmpeg command for final video with glitch + beep."""
    cmd = ["ffmpeg", "-y"]
    for p in paths:
        cmd.extend(["-i", str(p)])

    # Beep audio source
    beep = "sine=frequency=200:duration=0.5,volume=-20dB"

    # Build video xfade chain
    vfilters = []
    prev = "[0:v]"
    for i in range(1, len(paths)):
        out = f"[v{i}]" if i < len(paths) - 1 else "[vout]"
        vfilters.append(
            f"{prev}[{i}:v]xfade=transition=hlslice:"
            f"duration={transition_duration}:offset=0{out}"
        )
        prev = out

    # Audio: concat all audio streams + inject beep between them
    afilters = []
    audio_inputs = []
    for i in range(len(paths)):
        audio_inputs.append(f"[{i}:a]")
    # Generate beep for each transition
    for i in range(len(paths) - 1):
        afilters.append(f"anullsrc=r=44100:cl=stereo,atrim=0:0.01[silence{i}]")
    afilters.append(
        f"{''.join(audio_inputs)}concat=n={len(paths)}:v=0:a=1[aout]"
    )

    all_filters = ";".join(vfilters + afilters)
    cmd.extend([
        "-filter_complex", all_filters,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac",
        str(output_path),
    ])
    return cmd


def _run_ffmpeg(cmd: list[str]) -> None:
    """Run an ffmpeg command, raising on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("ffmpeg failed: %s", result.stderr[:500] if result.stderr else "unknown")
        raise RuntimeError(f"ffmpeg failed with exit code {result.returncode}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_assembler.py -v`
Expected: PASS (all 6 tests)

- [ ] **Step 5: Commit**

```bash
git add video_designer/pipeline/assembler.py tests/test_assembler.py
git commit -m "Add assembler: ffmpeg glitch transitions + beep for final video"
```

---

## Chunk 4: Runner, CLI, Docs

### Task 8: Create runner.py (async orchestrator)

**Files:**
- Create: `video_designer/pipeline/runner.py`
- Test: `tests/test_video_runner.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_video_runner.py`:

```python
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shared.config import Settings
from shared.models import ShotResult, ShotsManifest
from tests.conftest import write_script_json
from video_designer.pipeline.runner import run


def _setup_fixtures(tmp_path: Path) -> Settings:
    """Create script JSON + shots manifest + fake PNGs for testing."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    write_script_json(scripts_dir, "2026-03-15", 1, title="Episode 1")

    shots_dir = tmp_path / "static_shots"
    shot_dir = shots_dir / "2026-03-15_1"
    shot_dir.mkdir(parents=True)
    (shot_dir / "scene_1.png").write_bytes(b"fake png")
    (shot_dir / "end_card.png").write_bytes(b"fake png")

    manifest = ShotsManifest(
        script_title="Episode 1",
        script_index=1,
        date=date(2026, 3, 15),
        shots=[
            ShotResult(
                script_index=1, scene_number=1, success=True,
                output_path=shot_dir / "scene_1.png", error=None,
            ),
            ShotResult(
                script_index=1, scene_number=0, success=True,
                output_path=shot_dir / "end_card.png", error=None,
            ),
        ],
    )
    (shot_dir / "manifest.json").write_text(
        json.dumps(manifest.to_dict()), encoding="utf-8"
    )

    chars_dir = tmp_path / "characters"
    chars_dir.mkdir()

    return Settings(
        anthropic_api_key="test-key",
        xai_api_key="test-xai-key",
        scripts_output_dir=scripts_dir,
        shots_output_dir=shots_dir,
        characters_dir=chars_dir,
        art_style_path=tmp_path / "art_style.md",
        video_output_dir=tmp_path / "videos",
        video_max_concurrency=2,
    )


class TestVideoRunner:
    @pytest.mark.asyncio
    @patch("video_designer.pipeline.runner.assemble_final_video")
    @patch("video_designer.pipeline.runner.assemble_script_video")
    @patch("video_designer.pipeline.runner.generate_video")
    @patch("video_designer.pipeline.runner.generate_video_prompt")
    @patch("video_designer.pipeline.runner.generate_end_card_video_prompt")
    @patch("video_designer.pipeline.runner.xai_sdk")
    @patch("video_designer.pipeline.runner.anthropic")
    async def test_produces_manifest(
        self, mock_anthropic, mock_xai, mock_end_prompt, mock_scene_prompt,
        mock_gen_video, mock_assemble_script, mock_assemble_final, tmp_path,
    ):
        settings = _setup_fixtures(tmp_path)

        mock_anthropic.Anthropic.return_value = MagicMock()
        mock_xai.Client.return_value = MagicMock()
        mock_scene_prompt.return_value = "video prompt"
        mock_end_prompt.return_value = "end card prompt"

        def fake_generate_video(*args, **kwargs):
            output_path = kwargs.get("output_path") or args[2]
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"fake mp4")
            return output_path

        mock_gen_video.side_effect = fake_generate_video

        mock_assemble_script.side_effect = lambda clips, out, **kw: (
            out.write_bytes(b"script mp4") or out
        )
        mock_assemble_final.side_effect = lambda scripts, out, **kw: (
            out.write_bytes(b"final mp4") or out
        )

        result = await run(settings=settings, target_date=date(2026, 3, 15))

        assert result.exists() or result == settings.video_output_dir / "final_2026-03-15.mp4"

        manifest_path = settings.video_output_dir / "2026-03-15_1" / "video_manifest.json"
        assert manifest_path.exists()

    @pytest.mark.asyncio
    async def test_requires_xai_api_key(self):
        settings = Settings(xai_api_key="")
        with pytest.raises(RuntimeError, match="XAI_API_KEY"):
            await run(settings=settings)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_video_runner.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

Create `video_designer/pipeline/runner.py`:

```python
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from datetime import date
from pathlib import Path

import anthropic
import xai_sdk

from shared.config import Settings, load_settings
from shared.context_loader import build_context_block, load_art_style, load_characters
from shared.models import CartoonScript, ClipResult, ShotsManifest, VideoManifest

from .assembler import assemble_final_video, assemble_script_video
from .manifest_reader import ScriptWithShots, read_manifests
from .prompt_generator import generate_end_card_video_prompt, generate_video_prompt
from .video_generator import generate_video

logger = logging.getLogger(__name__)


async def run(
    settings: Settings | None = None,
    target_date: date | None = None,
) -> Path:
    """Run the full video designer pipeline. Returns path to final video."""
    settings = settings or load_settings()

    if not settings.xai_api_key:
        raise RuntimeError("XAI_API_KEY required for video generation")

    has_anthropic = bool(settings.anthropic_api_key)
    if not has_anthropic:
        logger.warning(
            "ANTHROPIC_API_KEY not set — will use original scene prompts directly"
        )

    # Clients
    anthropic_client = (
        anthropic.Anthropic(api_key=settings.anthropic_api_key) if has_anthropic else None
    )
    xai_client = xai_sdk.Client(api_key=settings.xai_api_key)

    # Load context
    characters = load_characters(settings.characters_dir)
    art_style = load_art_style(settings.art_style_path)
    context_block = build_context_block(characters, art_style)

    # Read manifests + scripts
    data = read_manifests(
        target_date=target_date,
        shots_dir=settings.shots_output_dir,
        scripts_dir=settings.scripts_output_dir,
    )
    logger.info("Processing %d scripts", len(data))

    semaphore = asyncio.Semaphore(settings.video_max_concurrency)

    # Level 1: parallel across scripts
    results = await asyncio.gather(
        *[
            _process_script(
                entry=entry,
                context_block=context_block,
                anthropic_client=anthropic_client,
                xai_client=xai_client,
                semaphore=semaphore,
                settings=settings,
            )
            for entry in data
        ]
    )

    # Filter to scripts that produced a video
    script_videos = [
        (manifest, path)
        for manifest, path in results
        if path is not None
    ]

    if not script_videos:
        logger.warning("No script videos produced")
        print("No script videos were produced.")
        return settings.video_output_dir

    # Assemble final video
    date_str = data[0].script.date.isoformat()
    final_path = settings.video_output_dir / f"final_{date_str}.mp4"

    if len(script_videos) > 1:
        await asyncio.to_thread(
            assemble_final_video,
            [path for _, path in script_videos],
            final_path,
        )
    else:
        # Single script: copy
        import shutil
        _, src = script_videos[0]
        shutil.copy2(src, final_path)

    print(f"\nDone! Final video: {final_path}")
    return final_path


async def _process_script(
    entry: ScriptWithShots,
    context_block: str,
    anthropic_client,
    xai_client,
    semaphore: asyncio.Semaphore,
    settings: Settings,
) -> tuple[VideoManifest, Path | None]:
    """Process a single script: generate clips + assemble script video."""
    output_dir = settings.video_output_dir / (
        f"{entry.script.date.isoformat()}_{entry.index}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"  Script {entry.index}: {entry.script.title}")

    # Map scene_number -> shot output_path for successful shots
    shot_paths = {
        shot.scene_number: shot.output_path
        for shot in entry.manifest.shots
        if shot.success and shot.output_path
    }

    # Build tasks for each scene + end card
    tasks = []
    for scene in entry.script.scenes:
        image_path = shot_paths.get(scene.scene_number)
        if not image_path:
            logger.warning("No shot for scene %d, skipping", scene.scene_number)
            continue
        tasks.append(
            _process_clip(
                label=f"Scene {scene.scene_number}",
                scene_number=scene.scene_number,
                script_index=entry.index,
                output_path=output_dir / f"scene_{scene.scene_number}.mp4",
                image_path=Path(image_path),
                prompt_fn=lambda s=scene: generate_video_prompt(
                    s, entry.script, context_block, anthropic_client,
                    settings.video_prompt_model, settings.video_prompt_max_tokens,
                ),
                xai_client=xai_client,
                semaphore=semaphore,
                settings=settings,
            )
        )

    # End card
    end_card_path = shot_paths.get(0)
    if end_card_path:
        tasks.append(
            _process_clip(
                label="End card",
                scene_number=0,
                script_index=entry.index,
                output_path=output_dir / "end_card.mp4",
                image_path=Path(end_card_path),
                prompt_fn=lambda: generate_end_card_video_prompt(
                    entry.script, context_block, anthropic_client,
                    settings.video_prompt_model, settings.video_prompt_max_tokens,
                ),
                xai_client=xai_client,
                semaphore=semaphore,
                settings=settings,
            )
        )

    # Level 2: parallel across scenes
    clips = list(await asyncio.gather(*tasks))

    # Assemble script video from successful clips
    successful = [c for c in clips if c.success and c.output_path]
    # Sort: scenes first (by number), end card (0) last
    successful.sort(key=lambda c: (c.scene_number == 0, c.scene_number))
    clip_paths = [Path(c.output_path) for c in successful]

    script_video_path = None
    if clip_paths:
        script_video_path = output_dir / "script_video.mp4"
        try:
            await asyncio.to_thread(
                assemble_script_video, clip_paths, script_video_path
            )
        except Exception:
            logger.exception("Failed to assemble script video for %d", entry.index)
            script_video_path = None

    manifest = VideoManifest(
        script_title=entry.script.title,
        script_index=entry.index,
        date=entry.script.date,
        clips=clips,
        script_video_path=script_video_path,
    )

    manifest_path = output_dir / "video_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return manifest, script_video_path


async def _process_clip(
    label: str,
    scene_number: int,
    script_index: int,
    output_path: Path,
    image_path: Path,
    prompt_fn: Callable[[], str],
    xai_client,
    semaphore: asyncio.Semaphore,
    settings: Settings,
) -> ClipResult:
    """Generate a single video clip (scene or end card)."""
    try:
        # Step 1: Compose video prompt via Claude (or fallback)
        video_prompt = await asyncio.to_thread(prompt_fn)

        # Step 2: Generate video via xAI (with semaphore)
        async with semaphore:
            await asyncio.to_thread(
                generate_video,
                video_prompt,
                image_path,
                output_path,
                xai_client,
                settings.video_model,
                settings.video_duration,
                settings.video_resolution,
            )

        print(f"    {label}: OK")
        return ClipResult(
            script_index=script_index,
            scene_number=scene_number,
            success=True,
            output_path=output_path,
            duration_seconds=float(settings.video_duration),
            error=None,
        )
    except Exception as e:
        logger.exception("Failed to generate %s for script %d", label, script_index)
        print(f"    {label}: FAILED ({e})")
        return ClipResult(
            script_index=script_index,
            scene_number=scene_number,
            success=False,
            output_path=None,
            duration_seconds=None,
            error=str(e),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_video_runner.py -v`
Expected: PASS (all 2 tests)

- [ ] **Step 5: Commit**

```bash
git add video_designer/pipeline/runner.py tests/test_video_runner.py
git commit -m "Add video_designer runner: async orchestrator with 2-level parallelism"
```

---

### Task 9: Create __main__.py (CLI)

**Files:**
- Create: `video_designer/__main__.py`

- [ ] **Step 1: Write CLI**

Create `video_designer/__main__.py`:

```python
import argparse
import asyncio
import logging
import sys
from datetime import date
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Add project root to path so shared/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Video Designer — Generate cartoon videos from static shots"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date to process (YYYY-MM-DD). Default: latest available.",
    )
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date) if args.date else None

    from video_designer.pipeline.runner import run

    asyncio.run(run(target_date=target_date))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add video_designer/__main__.py
git commit -m "Add video_designer CLI entry point"
```

---

### Task 10: Update docs (CLAUDE.md, README)

**Files:**
- Modify: `CLAUDE.md`
- Modify: `video_designer/README.md`

- [ ] **Step 1: Update CLAUDE.md**

In the Architecture section, change `[STUB]` to `[IMPLEMENTED]` for `video_designer`.

Update the agent pipeline description for item 4.

Add `## Video Designer Internals` section at end of file, following the pattern of Static Shots Maker Internals.

Add CLI commands to Running Agents section:
```
# Video Designer — generate videos from latest static shots
PYTHONPATH=. python -m video_designer

# Video Designer — generate videos from specific date
PYTHONPATH=. python -m video_designer --date 2026-03-15
```

Update test count.

Update data contracts line to include `ClipResult` → `VideoManifest`.

- [ ] **Step 2: Update video_designer/README.md**

Replace the stub content with full documentation (same pattern as `static_shots_maker/README.md`).

- [ ] **Step 3: Run full test suite + lint**

Run: `uv run pytest tests/ -q && uv run ruff check . && uv run ruff format --check .`
Expected: All pass, no lint errors

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md video_designer/README.md
git commit -m "Update CLAUDE.md and README with video_designer documentation"
```

---

## Execution Checklist

After all tasks complete, verify:

```bash
# All tests pass
uv run pytest tests/ -q

# Lint clean
uv run ruff check . && uv run ruff format --check .

# ffmpeg available
ffmpeg -version

# Manual smoke test (requires API keys)
PYTHONPATH=. python -m video_designer --date 2026-03-15
```
