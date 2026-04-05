from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from caption_maker.pipeline.runner import run
from caption_maker.pipeline.transcriber import Segment, Transcription, WordTiming


def _make_transcription(has_speech: bool = True) -> Transcription:
    if not has_speech:
        return Transcription(segments=[], language="en", duration=15.0)
    return Transcription(
        segments=[
            Segment(
                text="Hello world",
                start=0.0,
                end=1.5,
                words=[
                    WordTiming("Hello", 0.0, 0.5),
                    WordTiming("world", 0.6, 1.0),
                ],
            )
        ],
        language="en",
        duration=15.0,
    )


def _make_settings(tmp_path: Path) -> MagicMock:
    settings = MagicMock()
    settings.video_output_dir = tmp_path
    settings.openai_api_key = "test-key"
    settings.whisper_model = "whisper-1"
    font_path = tmp_path / "fonts" / "Inter-Bold.ttf"
    font_path.parent.mkdir(parents=True, exist_ok=True)
    font_path.write_bytes(b"fake font")
    settings.caption_font_path = font_path
    return settings


class TestCaptionRunner:
    @pytest.mark.asyncio
    @patch("shared.assembler.assemble_final_video")
    @patch("caption_maker.pipeline.runner.burn_subtitles")
    @patch("caption_maker.pipeline.runner.probe_video", return_value=(270, 480, 30.0))
    @patch("caption_maker.pipeline.runner.transcribe")
    @patch("caption_maker.pipeline.runner.find_script_videos")
    async def test_full_pipeline(
        self,
        mock_find,
        mock_transcribe,
        mock_probe,
        mock_burn,
        mock_assemble,
        tmp_path,
    ):
        vid_dir = tmp_path / "2026-03-21_1"
        vid_dir.mkdir()
        vid_path = vid_dir / "script_video.mp4"
        vid_path.write_bytes(b"fake")

        mock_find.return_value = [(1, vid_path)]
        mock_transcribe.return_value = _make_transcription(has_speech=True)
        mock_burn.return_value = vid_dir / "script_video_captioned.mp4"

        settings = _make_settings(tmp_path)
        await run(settings=settings, target_date=None, compile=True)

        mock_transcribe.assert_called_once()
        mock_burn.assert_called_once()
        mock_assemble.assert_called_once()

    @pytest.mark.asyncio
    @patch("shared.assembler.assemble_final_video")
    @patch("caption_maker.pipeline.runner.burn_subtitles")
    @patch("caption_maker.pipeline.runner.probe_video", return_value=(270, 480, 30.0))
    @patch("caption_maker.pipeline.runner.transcribe")
    @patch("caption_maker.pipeline.runner.find_script_videos")
    async def test_skips_silent_videos(
        self,
        mock_find,
        mock_transcribe,
        mock_probe,
        mock_burn,
        mock_assemble,
        tmp_path,
    ):
        vid1_dir = tmp_path / "2026-03-21_1"
        vid1_dir.mkdir()
        vid1 = vid1_dir / "script_video.mp4"
        vid1.write_bytes(b"fake")

        vid2_dir = tmp_path / "2026-03-21_2"
        vid2_dir.mkdir()
        vid2 = vid2_dir / "script_video.mp4"
        vid2.write_bytes(b"fake")

        mock_find.return_value = [(1, vid1), (2, vid2)]
        # First video silent, second has speech
        mock_transcribe.side_effect = [
            _make_transcription(has_speech=False),
            _make_transcription(has_speech=True),
        ]
        mock_burn.return_value = vid2_dir / "script_video_captioned.mp4"

        settings = _make_settings(tmp_path)
        await run(settings=settings, target_date=None, compile=True)

        # Only one video should be burned (the one with speech)
        mock_burn.assert_called_once()
        mock_assemble.assert_called_once()

    @pytest.mark.asyncio
    @patch("caption_maker.pipeline.runner.find_script_videos")
    async def test_no_videos_found(self, mock_find, tmp_path):
        mock_find.side_effect = FileNotFoundError("No videos")

        settings = _make_settings(tmp_path)
        with pytest.raises(FileNotFoundError):
            await run(settings=settings, target_date=None)
