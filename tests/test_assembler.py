from __future__ import annotations

from unittest.mock import patch

import pytest

from video_designer.pipeline.assembler import (
    _generate_glitch_clip,
    assemble_final_video,
    assemble_script_video,
)


class TestAssembleScriptVideo:
    @patch("video_designer.pipeline.assembler._concat_clips")
    def test_calls_concat(self, mock_concat, tmp_path):
        clips = [tmp_path / "scene_1.mp4", tmp_path / "scene_2.mp4"]
        output = tmp_path / "script_video.mp4"

        result = assemble_script_video(clips, output)
        assert result == output
        mock_concat.assert_called_once_with(clips, output)

    def test_raises_on_empty_clips(self, tmp_path):
        with pytest.raises(ValueError, match="at least 1"):
            assemble_script_video([], tmp_path / "out.mp4")


class TestAssembleFinalVideo:
    @patch("video_designer.pipeline.assembler._concat_with_glitch")
    def test_multi_calls_glitch_concat(self, mock_concat, tmp_path):
        scripts = [tmp_path / "s1.mp4", tmp_path / "s2.mp4"]
        output = tmp_path / "final.mp4"

        result = assemble_final_video(scripts, output)
        assert result == output
        mock_concat.assert_called_once_with(scripts, output, 0.5)

    @patch("video_designer.pipeline.assembler._concat_clips")
    def test_single_uses_plain_concat(self, mock_concat, tmp_path):
        scripts = [tmp_path / "s1.mp4"]
        output = tmp_path / "final.mp4"

        assemble_final_video(scripts, output)
        mock_concat.assert_called_once_with(scripts, output)

    def test_raises_on_empty(self, tmp_path):
        with pytest.raises(ValueError, match="at least 1"):
            assemble_final_video([], tmp_path / "out.mp4")


class TestGlitchClip:
    @patch("video_designer.pipeline.assembler._run_ffmpeg")
    def test_uses_silence_not_beep(self, mock_ffmpeg, tmp_path):
        """Glitch clip uses anullsrc (silence) instead of 200Hz sine beep."""
        output = tmp_path / "glitch.mp4"
        _generate_glitch_clip(output, 1.0, 270, 480, 30.0)

        mock_ffmpeg.assert_called_once()
        cmd = mock_ffmpeg.call_args[0][0]
        cmd_str = " ".join(cmd)
        assert "anullsrc" in cmd_str
        assert "sine" not in cmd_str
