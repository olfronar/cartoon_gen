from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from tiktok_publisher.pipeline.uploader import (
    _compute_chunk_size,
    init_upload,
    poll_status,
    upload_chunks,
)


def _mock_urlopen(response_data: bytes, status: int = 200):
    mock_resp = MagicMock()
    mock_resp.read.return_value = response_data
    mock_resp.status = status
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestComputeChunkSize:
    def test_small_file(self):
        assert _compute_chunk_size(1024) == 1024  # < 5MB

    def test_medium_file(self):
        assert _compute_chunk_size(50 * 1024 * 1024) == 10 * 1024 * 1024  # 10MB default

    def test_at_boundary(self):
        assert _compute_chunk_size(5 * 1024 * 1024) == 5 * 1024 * 1024  # Exactly 5MB


class TestInitUpload:
    @patch("tiktok_publisher.pipeline.uploader.urllib.request.urlopen")
    def test_sends_correct_payload(self, mock_urlopen_fn):
        resp_data = json.dumps(
            {
                "data": {"publish_id": "pub123", "upload_url": "https://upload.example.com"},
                "error": {"code": "ok"},
            }
        ).encode()
        mock_urlopen_fn.return_value = _mock_urlopen(resp_data)

        pub_id, url = init_upload("token123", 1000, 1000)

        assert pub_id == "pub123"
        assert url == "https://upload.example.com"

        # Verify request body — inbox mode has no post_info
        req = mock_urlopen_fn.call_args[0][0]
        body = json.loads(req.data.decode())
        assert "post_info" not in body
        assert body["source_info"]["source"] == "FILE_UPLOAD"
        assert body["source_info"]["video_size"] == 1000


class TestUploadChunks:
    @patch("tiktok_publisher.pipeline.uploader.urllib.request.urlopen")
    def test_correct_content_range(self, mock_urlopen_fn, tmp_path):
        video = tmp_path / "test.mp4"
        video.write_bytes(b"A" * 100)

        mock_urlopen_fn.return_value = _mock_urlopen(b"", status=201)

        upload_chunks("https://upload.example.com", video, chunk_size=40)

        # 100 bytes / 40 byte chunks = 3 chunks (40 + 40 + 20)
        assert mock_urlopen_fn.call_count == 3

        reqs = [c[0][0] for c in mock_urlopen_fn.call_args_list]
        assert reqs[0].get_header("Content-range") == "bytes 0-39/100"
        assert reqs[1].get_header("Content-range") == "bytes 40-79/100"
        assert reqs[2].get_header("Content-range") == "bytes 80-99/100"


class TestPollStatus:
    @patch("tiktok_publisher.pipeline.uploader.time.sleep")
    @patch("tiktok_publisher.pipeline.uploader.urllib.request.urlopen")
    def test_returns_on_complete(self, mock_urlopen_fn, mock_sleep):
        resp = json.dumps({"data": {"status": "PUBLISH_COMPLETE"}}).encode()
        mock_urlopen_fn.return_value = _mock_urlopen(resp)

        result = poll_status("token", "pub123")
        assert result["status"] == "PUBLISH_COMPLETE"
        mock_sleep.assert_not_called()

    @patch("tiktok_publisher.pipeline.uploader.time.sleep")
    @patch("tiktok_publisher.pipeline.uploader.urllib.request.urlopen")
    def test_raises_on_failure(self, mock_urlopen_fn, mock_sleep):
        resp = json.dumps(
            {"data": {"status": "FAILED", "fail_reason": "file_format_check_failed"}}
        ).encode()
        mock_urlopen_fn.return_value = _mock_urlopen(resp)

        with pytest.raises(RuntimeError, match="file_format_check_failed"):
            poll_status("token", "pub123")

    @patch("tiktok_publisher.pipeline.uploader.time.sleep")
    @patch("tiktok_publisher.pipeline.uploader.urllib.request.urlopen")
    def test_polls_until_complete(self, mock_urlopen_fn, mock_sleep):
        processing = json.dumps({"data": {"status": "PROCESSING_UPLOAD"}}).encode()
        complete = json.dumps({"data": {"status": "PUBLISH_COMPLETE"}}).encode()

        mock_urlopen_fn.side_effect = [
            _mock_urlopen(processing),
            _mock_urlopen(processing),
            _mock_urlopen(complete),
        ]

        result = poll_status("token", "pub123", max_attempts=5, interval=1)
        assert result["status"] == "PUBLISH_COMPLETE"
        assert mock_sleep.call_count == 2

    @patch("tiktok_publisher.pipeline.uploader.time.sleep")
    @patch("tiktok_publisher.pipeline.uploader.urllib.request.urlopen")
    def test_timeout(self, mock_urlopen_fn, mock_sleep):
        processing = json.dumps({"data": {"status": "PROCESSING_UPLOAD"}}).encode()
        mock_urlopen_fn.return_value = _mock_urlopen(processing)

        with pytest.raises(TimeoutError, match="did not complete"):
            poll_status("token", "pub123", max_attempts=2, interval=1)
