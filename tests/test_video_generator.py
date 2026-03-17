from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from video_designer.pipeline.video_generator import generate_video


def _mock_xai_client(
    url: str = "https://example.com/video.mp4",
    respect_moderation: bool = True,
) -> AsyncMock:
    """Create a mock xai_sdk.AsyncClient that returns a completed video."""
    response = MagicMock()
    response.url = url
    response.respect_moderation = respect_moderation

    client = AsyncMock()
    client.video.generate.return_value = response
    return client


class TestGenerateVideo:
    @pytest.mark.asyncio
    @patch("video_designer.pipeline.video_generator.urllib.request.urlopen")
    async def test_generates_and_saves(self, mock_urlopen, tmp_path):
        image_path = tmp_path / "scene_1.png"
        image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        output_path = tmp_path / "scene_1.mp4"

        mock_resp = MagicMock()
        mock_resp.read.return_value = b"fake mp4 data"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client = _mock_xai_client()

        result = await generate_video(
            prompt="A robot moves",
            image_path=image_path,
            output_path=output_path,
            client=client,
            model="grok-imagine-video",
            duration=15,
        )

        assert result == output_path
        assert output_path.read_bytes() == b"fake mp4 data"
        client.video.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_on_missing_image(self, tmp_path):
        output_path = tmp_path / "scene_1.mp4"
        client = AsyncMock()

        with pytest.raises(FileNotFoundError):
            await generate_video(
                prompt="test",
                image_path=tmp_path / "nonexistent.png",
                output_path=output_path,
                client=client,
                model="grok-imagine-video",
                duration=15,
            )

    @pytest.mark.asyncio
    async def test_moderation_failure(self, tmp_path):
        image_path = tmp_path / "scene_1.png"
        image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        output_path = tmp_path / "scene_1.mp4"

        client = _mock_xai_client(respect_moderation=False)

        with pytest.raises(RuntimeError, match="blocked by moderation"):
            await generate_video(
                prompt="test",
                image_path=image_path,
                output_path=output_path,
                client=client,
                model="grok-imagine-video",
                duration=15,
            )

    @pytest.mark.asyncio
    async def test_raises_on_no_url(self, tmp_path):
        image_path = tmp_path / "scene_1.png"
        image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        output_path = tmp_path / "scene_1.mp4"

        client = _mock_xai_client(url="")

        with pytest.raises(RuntimeError, match="no video URL"):
            await generate_video(
                prompt="test",
                image_path=image_path,
                output_path=output_path,
                client=client,
                model="grok-imagine-video",
                duration=15,
            )
