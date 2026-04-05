from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from shared.config import Settings
from tests.conftest import write_script_json
from tiktok_publisher.pipeline.runner import run


def _setup_fixtures(tmp_path: Path) -> Settings:
    """Create video dirs + script JSONs for testing."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    write_script_json(scripts_dir, "2026-04-01", 1, title="Episode 1")
    write_script_json(scripts_dir, "2026-04-01", 2, title="Episode 2")

    videos_dir = tmp_path / "videos"
    for i in (1, 2):
        d = videos_dir / f"2026-04-01_{i}"
        d.mkdir(parents=True)
        (d / "script_video_captioned.mp4").write_bytes(b"fake video")

    tokens_path = tmp_path / "tokens.json"
    tokens_path.write_text(
        json.dumps(
            {
                "access_token": "act.test",
                "refresh_token": "rft.test",
                "open_id": "user-1",
                "expires_at": 9999999999.0,
            }
        )
    )

    return Settings(
        tiktok_client_key="test-key",
        tiktok_client_secret="test-secret",
        tiktok_tokens_path=tokens_path,
        scripts_output_dir=scripts_dir,
        video_output_dir=videos_dir,
    )


class TestTikTokRunner:
    @pytest.mark.asyncio
    @patch("tiktok_publisher.pipeline.runner.upload_video")
    async def test_uploads_all_videos(self, mock_upload, tmp_path):
        settings = _setup_fixtures(tmp_path)
        mock_upload.return_value = "pub_123"

        await run(settings=settings, target_date=date(2026, 4, 1))

        assert mock_upload.call_count == 2

    @pytest.mark.asyncio
    @patch("tiktok_publisher.pipeline.runner.upload_video")
    async def test_continues_on_upload_failure(self, mock_upload, tmp_path):
        settings = _setup_fixtures(tmp_path)
        mock_upload.side_effect = [RuntimeError("API error"), "pub_456"]

        await run(settings=settings, target_date=date(2026, 4, 1))

        # Both uploads attempted despite first failing
        assert mock_upload.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_without_credentials(self):
        settings = Settings(tiktok_client_key="", tiktok_client_secret="")
        with pytest.raises(RuntimeError, match="TIKTOK_CLIENT_KEY"):
            await run(settings=settings)

    @pytest.mark.asyncio
    @patch("tiktok_publisher.pipeline.runner.upload_video")
    async def test_uses_privacy_level(self, mock_upload, tmp_path):
        settings = _setup_fixtures(tmp_path)
        mock_upload.return_value = "pub_123"

        await run(
            settings=settings,
            target_date=date(2026, 4, 1),
            privacy_level="PUBLIC_TO_EVERYONE",
        )

        # Check privacy level passed to upload_video
        for call_args in mock_upload.call_args_list:
            assert call_args[0][3] == "PUBLIC_TO_EVERYONE"
