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

        # Mock streaming download
        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.iter_bytes.return_value = [b"fake ", b"mp4 data"]
        mock_httpx.stream.return_value = mock_stream

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
