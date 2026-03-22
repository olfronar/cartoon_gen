from __future__ import annotations

from unittest.mock import MagicMock, patch

from caption_maker.pipeline.transcriber import transcribe


def _make_api_word(word, start, end):
    w = MagicMock()
    w.word = word
    w.start = start
    w.end = end
    return w


def _make_api_segment(text, start, end):
    seg = MagicMock()
    seg.text = text
    seg.start = start
    seg.end = end
    return seg


class TestTranscribe:
    @patch("openai.OpenAI")
    def test_transcribes_video(self, MockOpenAI, tmp_path):
        video = tmp_path / "test.mp4"
        video.write_bytes(b"fake video")

        words = [
            _make_api_word("Hello", 0.0, 0.5),
            _make_api_word("world", 0.6, 1.0),
        ]
        segments = [_make_api_segment("Hello world", 0.0, 1.0)]

        response = MagicMock()
        response.words = words
        response.segments = segments
        response.text = "Hello world"
        response.language = "en"

        client = MagicMock()
        client.audio.transcriptions.create.return_value = response
        MockOpenAI.return_value = client

        result = transcribe(video, api_key="test-key")

        assert len(result.segments) == 1
        assert result.language == "en"
        assert len(result.segments[0].words) == 2
        assert result.segments[0].words[0].word == "Hello"
        MockOpenAI.assert_called_once_with(api_key="test-key")
        call_kwargs = client.audio.transcriptions.create.call_args[1]
        assert call_kwargs["model"] == "whisper-1"
        assert call_kwargs["response_format"] == "verbose_json"

    @patch("openai.OpenAI")
    def test_empty_on_silence(self, MockOpenAI, tmp_path):
        video = tmp_path / "silent.mp4"
        video.write_bytes(b"fake")

        response = MagicMock()
        response.words = []
        response.segments = []
        response.text = ""
        response.language = "en"

        client = MagicMock()
        client.audio.transcriptions.create.return_value = response
        MockOpenAI.return_value = client

        result = transcribe(video, api_key="test-key")
        assert result.segments == []

    @patch("openai.OpenAI")
    def test_words_only_no_segments(self, MockOpenAI, tmp_path):
        """When API returns words but no segments, all words go in one segment."""
        video = tmp_path / "test.mp4"
        video.write_bytes(b"fake")

        words = [
            _make_api_word("Hi", 0.0, 0.3),
            _make_api_word("there", 0.4, 0.7),
        ]

        response = MagicMock()
        response.words = words
        response.segments = []
        response.text = "Hi there"
        response.language = "en"

        client = MagicMock()
        client.audio.transcriptions.create.return_value = response
        MockOpenAI.return_value = client

        result = transcribe(video, api_key="test-key")
        assert len(result.segments) == 1
        assert result.segments[0].text == "Hi there"
        assert len(result.segments[0].words) == 2

    @patch("openai.OpenAI")
    def test_custom_model(self, MockOpenAI, tmp_path):
        video = tmp_path / "test.mp4"
        video.write_bytes(b"fake")

        response = MagicMock()
        response.words = []
        response.segments = []
        response.text = ""
        response.language = "en"

        client = MagicMock()
        client.audio.transcriptions.create.return_value = response
        MockOpenAI.return_value = client

        transcribe(video, api_key="test-key", model="gpt-4o-transcribe")
        call_kwargs = client.audio.transcriptions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-transcribe"
