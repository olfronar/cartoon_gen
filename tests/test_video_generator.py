from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from video_designer.pipeline.video_generator import generate_video


def _mock_genai_client(video_data: bytes = b"fake mp4 data") -> MagicMock:
    """Create a mock genai client that returns a completed video operation."""
    # Mock the video in the response
    mock_video = MagicMock()

    # Mock the operation response
    mock_operation = MagicMock()
    mock_operation.done = True
    mock_operation.response.generated_videos = [mock_video]

    # Mock client.files.download
    client = MagicMock()
    client.models.generate_videos.return_value = mock_operation
    client.files.download.return_value = video_data
    return client


class TestGenerateVideo:
    @patch("video_designer.pipeline.video_generator.types")
    def test_generates_and_saves(self, mock_types, tmp_path):
        image_path = tmp_path / "scene_1.png"
        image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        output_path = tmp_path / "scene_1.mp4"

        client = _mock_genai_client(b"fake mp4 data")

        result = generate_video(
            prompt="A robot moves",
            image_path=image_path,
            output_path=output_path,
            client=client,
            model="veo-3.1-fast-generate-preview",
            duration=8,
        )

        assert result == output_path
        assert output_path.read_bytes() == b"fake mp4 data"
        client.models.generate_videos.assert_called_once()

    @patch("video_designer.pipeline.video_generator.types")
    def test_raises_on_missing_image(self, mock_types, tmp_path):
        output_path = tmp_path / "scene_1.mp4"
        client = MagicMock()

        with pytest.raises(FileNotFoundError):
            generate_video(
                prompt="test",
                image_path=tmp_path / "nonexistent.png",
                output_path=output_path,
                client=client,
                model="veo-3.1-fast-generate-preview",
                duration=8,
            )

    @patch("video_designer.pipeline.video_generator.types")
    def test_with_reference_images(self, mock_types, tmp_path):
        image_path = tmp_path / "scene_1.png"
        image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        ref_path = tmp_path / "ref.png"
        ref_path.write_bytes(b"ref image")
        output_path = tmp_path / "scene_1.mp4"

        client = _mock_genai_client()

        result = generate_video(
            prompt="A robot moves",
            image_path=image_path,
            output_path=output_path,
            client=client,
            model="veo-3.1-fast-generate-preview",
            duration=8,
            reference_images=[ref_path],
        )

        assert result == output_path
        client.models.generate_videos.assert_called_once()

    @patch("video_designer.pipeline.video_generator.types")
    def test_with_next_scene_image(self, mock_types, tmp_path):
        image_path = tmp_path / "scene_1.png"
        image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        next_path = tmp_path / "scene_2.png"
        next_path.write_bytes(b"next scene")
        output_path = tmp_path / "scene_1.mp4"

        client = _mock_genai_client()

        result = generate_video(
            prompt="A robot moves",
            image_path=image_path,
            output_path=output_path,
            client=client,
            model="veo-3.1-fast-generate-preview",
            duration=8,
            next_scene_image=next_path,
        )

        assert result == output_path

    @patch("video_designer.pipeline.video_generator.types")
    def test_raises_on_no_video(self, mock_types, tmp_path):
        image_path = tmp_path / "scene_1.png"
        image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        output_path = tmp_path / "scene_1.mp4"

        mock_operation = MagicMock()
        mock_operation.done = True
        mock_operation.response = None

        client = MagicMock()
        client.models.generate_videos.return_value = mock_operation

        with pytest.raises(RuntimeError, match="no video data"):
            generate_video(
                prompt="test",
                image_path=image_path,
                output_path=output_path,
                client=client,
                model="veo-3.1-fast-generate-preview",
                duration=8,
            )
