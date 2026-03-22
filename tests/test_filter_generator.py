from __future__ import annotations

from pathlib import Path

from caption_maker.pipeline.filter_generator import (
    _escape_drawtext_text,
    generate_drawtext_filter,
)
from caption_maker.pipeline.transcriber import Segment, Transcription, WordTiming


class TestEscapeDrawtextText:
    def test_escapes_backslash(self):
        assert _escape_drawtext_text("a\\b") == "a\\\\b"

    def test_escapes_colon(self):
        assert _escape_drawtext_text("a:b") == "a\\:b"

    def test_escapes_comma(self):
        assert _escape_drawtext_text("a,b") == "a\\,b"

    def test_apostrophe_replaced_with_unicode(self):
        """ASCII apostrophe replaced with Unicode curly quote to avoid parser issues."""
        assert _escape_drawtext_text("can't") == "can\u2019t"

    def test_plain_text_unchanged(self):
        assert _escape_drawtext_text("Hello world") == "Hello world"


class TestCumulativeWordReveal:
    def test_three_word_segment(self):
        words = [
            WordTiming("Hello", 0.0, 0.4),
            WordTiming("beautiful", 0.5, 0.9),
            WordTiming("world", 1.0, 1.4),
        ]
        seg = Segment(text="Hello beautiful world", start=0.0, end=1.5, words=words)
        transcription = Transcription(segments=[seg], language="en", duration=5.0)

        result = generate_drawtext_filter(transcription, 1280, Path("/tmp/font.ttf"))
        parts = result.split(",drawtext=")

        # 3 words = MAX_WORDS_PER_CHUNK(3), so one chunk with 3 cumulative entries
        assert len(parts) == 3
        assert ":text=Hello:" in parts[0]
        assert ":text=Hello beautiful:" in parts[1]
        assert ":text=Hello beautiful world:" in parts[2]

    def test_chunking_resets_at_max_words(self):
        """After MAX_WORDS_PER_CHUNK words, text resets for next chunk."""
        words = [
            WordTiming("one", 0.0, 0.2),
            WordTiming("two", 0.3, 0.5),
            WordTiming("three", 0.6, 0.8),
            WordTiming("four", 0.9, 1.1),
            WordTiming("five", 1.2, 1.4),
            WordTiming("six", 1.5, 1.7),
        ]
        seg = Segment(text="one two three four five six", start=0.0, end=2.0, words=words)
        transcription = Transcription(segments=[seg], language="en", duration=3.0)

        result = generate_drawtext_filter(transcription, 1280, Path("/tmp/font.ttf"))
        parts = result.split(",drawtext=")

        # 3 entries for chunk 1 + 3 entries for chunk 2 = 6
        assert len(parts) == 6
        assert ":text=one two three:" in parts[2]
        # Chunk 2 resets
        assert ":text=four:" in parts[3]
        assert "one" not in parts[3]

    def test_multi_segment_resets(self):
        seg1 = Segment(
            text="One two",
            start=0.0,
            end=1.0,
            words=[WordTiming("One", 0.0, 0.4), WordTiming("two", 0.5, 0.9)],
        )
        seg2 = Segment(
            text="Three four",
            start=2.0,
            end=3.0,
            words=[WordTiming("Three", 2.0, 2.4), WordTiming("four", 2.5, 2.9)],
        )
        transcription = Transcription(segments=[seg1, seg2], language="en", duration=5.0)

        result = generate_drawtext_filter(transcription, 1280, Path("/tmp/font.ttf"))
        parts = result.split(",drawtext=")

        assert len(parts) == 4
        assert ":text=Three:" in parts[2]
        assert "One" not in parts[2]

    def test_apostrophe_in_text(self):
        """Apostrophes don't use single-quote escaping — unquoted text value."""
        words = [
            WordTiming("can't", 0.0, 0.5),
            WordTiming("stop", 0.6, 1.0),
        ]
        seg = Segment(text="can't stop", start=0.0, end=1.0, words=words)
        transcription = Transcription(segments=[seg], language="en", duration=1.0)

        result = generate_drawtext_filter(transcription, 1280, Path("/tmp/font.ttf"))
        # ASCII apostrophe replaced with Unicode curly quote
        assert ":text=can\u2019t:" in result
        assert ":text=can't:" not in result


class TestMinDuration:
    def test_zero_duration_expanded(self):
        words = [
            WordTiming("Hello", 0.0, 0.5),
            WordTiming("world", 0.5, 0.5),
        ]
        seg = Segment(text="Hello world", start=0.0, end=1.0, words=words)
        transcription = Transcription(segments=[seg], language="en", duration=1.0)

        result = generate_drawtext_filter(transcription, 1280, Path("/tmp/font.ttf"))
        assert "between(t,0.500,0.500)" not in result


class TestFontSizeScaling:
    def test_1280_height(self):
        words = [WordTiming("Hi", 0.0, 0.5)]
        seg = Segment(text="Hi", start=0.0, end=0.5, words=words)
        transcription = Transcription(segments=[seg], language="en", duration=1.0)

        result = generate_drawtext_filter(transcription, 1280, Path("/tmp/font.ttf"))
        assert ":fontsize=48:" in result


class TestEmptyTranscription:
    def test_returns_empty_string(self):
        transcription = Transcription(segments=[], language="en", duration=0.0)
        result = generate_drawtext_filter(transcription, 1280, Path("/tmp/font.ttf"))
        assert result == ""


class TestPositioning:
    def test_bottom_position_with_clamp(self):
        words = [WordTiming("Hi", 0.0, 0.5)]
        seg = Segment(text="Hi", start=0.0, end=0.5, words=words)
        transcription = Transcription(segments=[seg], language="en", duration=1.0)

        result = generate_drawtext_filter(transcription, 1280, Path("/tmp/font.ttf"))
        assert "y=h-th-h*0.05" in result
        assert "x=(w-text_w)/2" in result
