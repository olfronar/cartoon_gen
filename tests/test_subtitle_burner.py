from __future__ import annotations

from unittest.mock import patch

from caption_maker.pipeline.subtitle_burner import burn_subtitles


class TestBurnSubtitles:
    @patch("caption_maker.pipeline.subtitle_burner.run_ffmpeg")
    def test_calls_ffmpeg_with_filter_script(self, mock_ffmpeg, tmp_path):
        video = tmp_path / "input.mp4"
        filter_script = tmp_path / "captions_filter.txt"
        output = tmp_path / "output.mp4"

        burn_subtitles(video, filter_script, output)

        mock_ffmpeg.assert_called_once()
        cmd = mock_ffmpeg.call_args[0][0]
        assert "-filter_script:v" in cmd
        assert "-c:v" in cmd
        assert "libx264" in cmd

    @patch("caption_maker.pipeline.subtitle_burner.run_ffmpeg")
    def test_returns_output_path(self, mock_ffmpeg, tmp_path):
        result = burn_subtitles(
            tmp_path / "in.mp4",
            tmp_path / "filter.txt",
            tmp_path / "out.mp4",
        )
        assert result == tmp_path / "out.mp4"
