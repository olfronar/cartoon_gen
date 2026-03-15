from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shared.config import Settings
from shared.models import CartoonScript, SceneScript, Synopsis
from static_shots_maker.pipeline.runner import run
from tests.conftest import make_scored_item


def _make_script(title: str = "Test", d: date = date(2026, 3, 15)) -> CartoonScript:
    return CartoonScript(
        title=title,
        date=d,
        source_item=make_scored_item(),
        logline="test",
        synopsis=Synopsis(
            setup="s",
            escalation="e",
            punchline="p",
            estimated_scenes=1,
            key_visual_gags=[],
        ),
        scenes=[
            SceneScript(
                scene_number=1,
                scene_title="S1",
                setting="Lab",
                scene_prompt="A robot.",
                dialogue=[],
                visual_gag=None,
                audio_direction="silence",
                duration_seconds=5,
                camera_movement="static",
            ),
        ],
        end_card_prompt="logo",
        characters_used=["Bot"],
    )


def _write_script(scripts_dir: Path, d: str, index: int, title: str = "Test") -> None:
    script = _make_script(title=title, d=date.fromisoformat(d))
    path = scripts_dir / f"{d}_{index}.json"
    path.write_text(json.dumps(script.to_dict()), encoding="utf-8")


@pytest.fixture
def mock_settings(tmp_path):
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    _write_script(scripts_dir, "2026-03-15", 1, title="Episode 1")

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
    @patch("static_shots_maker.pipeline.runner.generate_end_card_prompt")
    @patch("static_shots_maker.pipeline.runner.anthropic")
    @patch("static_shots_maker.pipeline.runner.genai")
    async def test_generates_manifest(
        self, mock_genai, mock_anthropic_mod, mock_end_card, mock_scene, mock_img, mock_settings
    ):
        mock_anthropic_mod.Anthropic.return_value = MagicMock()
        mock_genai.Client.return_value = MagicMock()
        mock_scene.return_value = "optimized scene prompt"
        mock_end_card.return_value = "optimized end card prompt"

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
        assert len(manifest.shots) == 2  # 1 scene + 1 end card

        # Check manifest file written
        manifest_path = mock_settings.shots_output_dir / "2026-03-15_1" / "manifest.json"
        assert manifest_path.exists()

        data = json.loads(manifest_path.read_text())
        assert data["script_title"] == "Episode 1"
        assert len(data["shots"]) == 2

    @pytest.mark.asyncio
    async def test_requires_google_api_key(self):
        settings = Settings(google_api_key="")
        with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
            await run(settings=settings)

    @pytest.mark.asyncio
    @patch("static_shots_maker.pipeline.runner.generate_image")
    @patch("static_shots_maker.pipeline.runner.generate_scene_prompt")
    @patch("static_shots_maker.pipeline.runner.generate_end_card_prompt")
    @patch("static_shots_maker.pipeline.runner.anthropic")
    @patch("static_shots_maker.pipeline.runner.genai")
    async def test_image_failure_recorded(
        self, mock_genai, mock_anthropic_mod, mock_end_card, mock_scene, mock_img, mock_settings
    ):
        mock_anthropic_mod.Anthropic.return_value = MagicMock()
        mock_genai.Client.return_value = MagicMock()
        mock_scene.return_value = "prompt"
        mock_end_card.return_value = "prompt"
        mock_img.side_effect = RuntimeError("Gemini failed")

        manifests = await run(settings=mock_settings, target_date=date(2026, 3, 15))

        assert len(manifests) == 1
        failed = [s for s in manifests[0].shots if not s.success]
        assert len(failed) == 2  # both scene and end card failed
        assert "Gemini failed" in failed[0].error
