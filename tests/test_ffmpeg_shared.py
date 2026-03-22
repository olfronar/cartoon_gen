from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shared.ffmpeg import probe_video, run_ffmpeg


class TestRunFfmpeg:
    @patch("shared.ffmpeg.subprocess.run")
    def test_raises_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="error details")
        with pytest.raises(RuntimeError, match="exit code 1"):
            run_ffmpeg(["ffmpeg", "-y", "-i", "in.mp4", "out.mp4"])


class TestProbeVideo:
    @patch("shared.ffmpeg.subprocess.run")
    def test_parses_output(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="270,480,30/1\n",
            returncode=0,
        )
        w, h, fps = probe_video(Path("test.mp4"))
        assert w == 270
        assert h == 480
        assert fps == 30.0

    @patch("shared.ffmpeg.subprocess.run")
    def test_defaults_on_failure(self, mock_run):
        mock_run.side_effect = Exception("ffprobe not found")
        w, h, fps = probe_video(Path("missing.mp4"))
        assert (w, h, fps) == (270, 480, 30.0)
