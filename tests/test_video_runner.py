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

    manifest = ShotsManifest(
        script_title="Episode 1",
        script_index=1,
        date=date(2026, 3, 15),
        shots=[
            ShotResult(
                script_index=1,
                scene_number=1,
                success=True,
                output_path=shot_dir / "scene_1.png",
                error=None,
            ),
        ],
    )
    (shot_dir / "manifest.json").write_text(json.dumps(manifest.to_dict()), encoding="utf-8")

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
    @patch("video_designer.pipeline.runner.xai_sdk")
    @patch("video_designer.pipeline.runner.anthropic")
    async def test_produces_manifest(
        self,
        mock_anthropic,
        mock_xai,
        mock_scene_prompt,
        mock_gen_video,
        mock_assemble_script,
        mock_assemble_final,
        tmp_path,
    ):
        settings = _setup_fixtures(tmp_path)

        mock_anthropic.Anthropic.return_value = MagicMock()
        mock_xai.Client.return_value = MagicMock()
        mock_scene_prompt.return_value = "video prompt"

        def fake_generate_video(_prompt, _image_path, output_path, *_rest):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"fake mp4")
            return output_path

        mock_gen_video.side_effect = fake_generate_video

        def fake_assemble(*args):
            out = args[1]
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"assembled mp4")
            return out

        mock_assemble_script.side_effect = fake_assemble
        mock_assemble_final.side_effect = fake_assemble

        await run(settings=settings, target_date=date(2026, 3, 15))

        # Check video manifest was written
        manifest_path = settings.video_output_dir / "2026-03-15_1" / "video_manifest.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert data["script_title"] == "Episode 1"
        assert len(data["clips"]) == 1  # 1 scene (no end card)

    @pytest.mark.asyncio
    async def test_requires_xai_api_key(self):
        settings = Settings(xai_api_key="")
        with pytest.raises(RuntimeError, match="XAI_API_KEY"):
            await run(settings=settings)
