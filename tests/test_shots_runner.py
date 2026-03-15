from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from shared.config import Settings
from static_shots_maker.pipeline.runner import run
from tests.conftest import write_script_json


@pytest.fixture
def mock_settings(tmp_path):
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    write_script_json(scripts_dir, "2026-03-15", 1, title="Episode 1")

    chars_dir = tmp_path / "characters"
    chars_dir.mkdir()

    return Settings(
        anthropic_api_key="test-key",
        google_api_key="test-google-key",
        scripts_output_dir=scripts_dir,
        characters_dir=chars_dir,
        art_style_path=tmp_path / "art_style.md",
        shots_output_dir=tmp_path / "static_shots",
        shots_max_concurrency=2,
    )


class TestShotsRunner:
    @pytest.mark.asyncio
    @patch("static_shots_maker.pipeline.runner.generate_image")
    @patch("static_shots_maker.pipeline.runner.generate_scene_prompt")
    @patch("static_shots_maker.pipeline.runner.anthropic")
    @patch("static_shots_maker.pipeline.runner.genai")
    async def test_generates_manifest(
        self, mock_genai, mock_anthropic_mod, mock_scene, mock_img, mock_settings
    ):
        mock_anthropic_mod.Anthropic.return_value = MagicMock()
        mock_genai.Client.return_value = MagicMock()
        mock_scene.return_value = "optimized scene prompt"

        def fake_generate_image(*args):
            output_path = args[1]
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"fake png")
            return output_path

        mock_img.side_effect = fake_generate_image

        manifests = await run(settings=mock_settings, target_date=date(2026, 3, 15))

        assert len(manifests) == 1
        manifest = manifests[0]
        assert manifest.script_title == "Episode 1"
        assert manifest.script_index == 1
        assert len(manifest.shots) == 1  # 1 scene (no end card)

        # Check manifest file written
        manifest_path = mock_settings.shots_output_dir / "2026-03-15_1" / "manifest.json"
        assert manifest_path.exists()

        data = json.loads(manifest_path.read_text())
        assert data["script_title"] == "Episode 1"
        assert len(data["shots"]) == 1

    @pytest.mark.asyncio
    async def test_requires_google_api_key(self):
        settings = Settings(google_api_key="")
        with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
            await run(settings=settings)

    @pytest.mark.asyncio
    @patch("static_shots_maker.pipeline.runner.generate_image")
    @patch("static_shots_maker.pipeline.runner.generate_scene_prompt")
    @patch("static_shots_maker.pipeline.runner.anthropic")
    @patch("static_shots_maker.pipeline.runner.genai")
    async def test_image_failure_recorded(
        self, mock_genai, mock_anthropic_mod, mock_scene, mock_img, mock_settings
    ):
        mock_anthropic_mod.Anthropic.return_value = MagicMock()
        mock_genai.Client.return_value = MagicMock()
        mock_scene.return_value = "prompt"
        mock_img.side_effect = RuntimeError("Gemini failed")

        manifests = await run(settings=mock_settings, target_date=date(2026, 3, 15))

        assert len(manifests) == 1
        failed = [s for s in manifests[0].shots if not s.success]
        assert len(failed) == 1  # 1 scene failed (no end card)
        assert "Gemini failed" in failed[0].error
