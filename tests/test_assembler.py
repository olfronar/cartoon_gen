from __future__ import annotations

from unittest.mock import patch

import pytest

from video_designer.pipeline.assembler import assemble_final_video, assemble_script_video


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
        mock_concat.assert_called_once_with(scripts, output, 1.0)

    @patch("video_designer.pipeline.assembler._concat_clips")
    def test_single_uses_plain_concat(self, mock_concat, tmp_path):
        scripts = [tmp_path / "s1.mp4"]
        output = tmp_path / "final.mp4"

        assemble_final_video(scripts, output)
        mock_concat.assert_called_once_with(scripts, output)

    def test_raises_on_empty(self, tmp_path):
        with pytest.raises(ValueError, match="at least 1"):
            assemble_final_video([], tmp_path / "out.mp4")
