from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from video_designer.pipeline.assembler import assemble_final_video, assemble_script_video


class TestAssembleScriptVideo:
    @patch("video_designer.pipeline.assembler.subprocess")
    def test_calls_ffmpeg(self, mock_subprocess, tmp_path):
        mock_subprocess.run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

        clips = [tmp_path / "scene_1.mp4", tmp_path / "scene_2.mp4"]
        output = tmp_path / "script_video.mp4"

        result = assemble_script_video(clips, output)
        assert result == output
        mock_subprocess.run.assert_called_once()

        cmd = mock_subprocess.run.call_args[0][0]
        assert cmd[0] == "ffmpeg"
        assert "-y" in cmd

    def test_raises_on_empty_clips(self, tmp_path):
        with pytest.raises(ValueError, match="at least 1"):
            assemble_script_video([], tmp_path / "out.mp4")

    @patch("video_designer.pipeline.assembler.subprocess")
    def test_single_clip_copies(self, mock_subprocess, tmp_path):
        mock_subprocess.run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

        clips = [tmp_path / "scene_1.mp4"]
        output = tmp_path / "script_video.mp4"

        assemble_script_video(clips, output)
        mock_subprocess.run.assert_called_once()

    @patch("video_designer.pipeline.assembler.subprocess")
    def test_raises_on_ffmpeg_failure(self, mock_subprocess, tmp_path):
        mock_subprocess.run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stderr="error"
        )

        clips = [tmp_path / "a.mp4", tmp_path / "b.mp4"]
        with pytest.raises(RuntimeError, match="ffmpeg"):
            assemble_script_video(clips, tmp_path / "out.mp4")


class TestAssembleFinalVideo:
    @patch("video_designer.pipeline.assembler.subprocess")
    def test_calls_ffmpeg(self, mock_subprocess, tmp_path):
        mock_subprocess.run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

        scripts = [tmp_path / "s1.mp4", tmp_path / "s2.mp4"]
        output = tmp_path / "final.mp4"

        result = assemble_final_video(scripts, output)
        assert result == output
        mock_subprocess.run.assert_called_once()

    def test_raises_on_empty(self, tmp_path):
        with pytest.raises(ValueError, match="at least 1"):
            assemble_final_video([], tmp_path / "out.mp4")
