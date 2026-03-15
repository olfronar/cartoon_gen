from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from video_designer.pipeline.assembler import assemble_final_video, assemble_script_video


class TestAssembleScriptVideo:
    @patch("video_designer.pipeline.assembler._concat_with_glitch")
    def test_multi_clip_calls_concat(self, mock_concat, tmp_path):
        clips = [tmp_path / "scene_1.mp4", tmp_path / "scene_2.mp4"]
        output = tmp_path / "script_video.mp4"

        result = assemble_script_video(clips, output)
        assert result == output
        mock_concat.assert_called_once_with(clips, output, 0.3, add_beep=False)

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
        cmd = mock_subprocess.run.call_args[0][0]
        assert "-c" in cmd and "copy" in cmd

    @patch("video_designer.pipeline.assembler.subprocess")
    def test_single_clip_raises_on_ffmpeg_failure(self, mock_subprocess, tmp_path):
        mock_subprocess.run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stderr="error"
        )

        clips = [tmp_path / "a.mp4"]
        with pytest.raises(RuntimeError, match="ffmpeg"):
            assemble_script_video(clips, tmp_path / "out.mp4")


class TestAssembleFinalVideo:
    @patch("video_designer.pipeline.assembler._concat_with_glitch")
    def test_multi_calls_concat_with_beep(self, mock_concat, tmp_path):
        scripts = [tmp_path / "s1.mp4", tmp_path / "s2.mp4"]
        output = tmp_path / "final.mp4"

        result = assemble_final_video(scripts, output)
        assert result == output
        mock_concat.assert_called_once_with(scripts, output, 1.0, add_beep=True)

    def test_raises_on_empty(self, tmp_path):
        with pytest.raises(ValueError, match="at least 1"):
            assemble_final_video([], tmp_path / "out.mp4")

    @patch("video_designer.pipeline.assembler.subprocess")
    def test_single_copies(self, mock_subprocess, tmp_path):
        mock_subprocess.run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

        scripts = [tmp_path / "s1.mp4"]
        output = tmp_path / "final.mp4"

        assemble_final_video(scripts, output)
        mock_subprocess.run.assert_called_once()
