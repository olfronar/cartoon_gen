from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from static_shots_maker.pipeline.image_generator import generate_image

MODEL = "gemini-3.1-flash-image-preview"


def _mock_client_with_image(data: bytes) -> MagicMock:
    """Create a mock client that streams back one chunk with inline image data."""
    inline_data = MagicMock()
    inline_data.data = data
    inline_data.mime_type = "image/png"

    part = MagicMock()
    part.inline_data = inline_data

    chunk = MagicMock()
    chunk.parts = [part]

    client = MagicMock()
    client.models.generate_content_stream.return_value = [chunk]
    return client


def _mock_client_no_image() -> MagicMock:
    """Create a mock client that streams back no image data."""
    chunk = MagicMock()
    chunk.parts = None

    client = MagicMock()
    client.models.generate_content_stream.return_value = [chunk]
    return client


class TestGenerateImage:
    def test_saves_png(self, tmp_path):
        """Saves raw bytes to the specified path."""
        output_path = tmp_path / "scene_1.png"
        data = b"\x89PNG\r\n\x1a\nfake"
        client = _mock_client_with_image(data)

        result = generate_image("a robot", output_path, client, MODEL)

        assert result == output_path
        assert output_path.read_bytes() == data
        client.models.generate_content_stream.assert_called_once()

    def test_reference_images_as_parts(self, tmp_path):
        """Prepends reference image Parts before text Part when provided."""
        output_path = tmp_path / "scene_1.png"
        data = b"\x89PNG\r\n\x1a\nfake"
        client = _mock_client_with_image(data)

        ref1 = tmp_path / "ref1.png"
        ref2 = tmp_path / "ref2.png"
        ref1.write_bytes(b"\x89PNG\r\n\x1a\nref1")
        ref2.write_bytes(b"\x89PNG\r\n\x1a\nref2")

        result = generate_image(
            "a robot", output_path, client, MODEL, reference_images=[ref1, ref2]
        )

        assert result == output_path
        call_args = client.models.generate_content_stream.call_args
        contents = call_args[1]["contents"]
        # Should have 2 ref image parts + 1 text part = 3 parts
        assert len(contents[0].parts) == 3

    def test_raises_on_no_image(self, tmp_path):
        """Raises RuntimeError when Gemini returns no image data."""
        output_path = tmp_path / "scene_1.png"
        client = _mock_client_no_image()

        with pytest.raises(RuntimeError, match="no image data"):
            generate_image("prompt", output_path, client, MODEL)
