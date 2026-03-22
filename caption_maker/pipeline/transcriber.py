from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WordTiming:
    word: str
    start: float  # seconds
    end: float


@dataclass(slots=True)
class Segment:
    text: str
    start: float
    end: float
    words: list[WordTiming]


@dataclass(slots=True)
class Transcription:
    segments: list[Segment]
    language: str
    duration: float


def transcribe(
    video_path: Path,
    api_key: str,
    model: str = "whisper-1",
) -> Transcription:
    """Transcribe a video file using the OpenAI Whisper API.

    Returns a Transcription with word-level timestamps.
    Returns empty Transcription for silent/instrumental clips.
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    with open(video_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model=model,
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"],
        )

    segments: list[Segment] = []

    # Build word list from response
    api_words = getattr(response, "words", None) or []
    api_segments = getattr(response, "segments", None) or []

    if api_segments and api_words:
        # Map words into segments by time overlap
        word_idx = 0
        for seg in api_segments:
            seg_words: list[WordTiming] = []
            while word_idx < len(api_words):
                w = api_words[word_idx]
                if w.start >= seg.end:
                    break
                text = w.word.strip()
                if text:
                    seg_words.append(WordTiming(word=text, start=w.start, end=w.end))
                word_idx += 1

            if seg_words:
                segments.append(
                    Segment(
                        text=seg.text.strip(),
                        start=seg.start,
                        end=seg.end,
                        words=seg_words,
                    )
                )
    elif api_words:
        # No segments returned — put all words in one segment
        words = [
            WordTiming(word=w.word.strip(), start=w.start, end=w.end)
            for w in api_words
            if w.word.strip()
        ]
        if words:
            segments.append(
                Segment(
                    text=response.text.strip(),
                    start=words[0].start,
                    end=words[-1].end,
                    words=words,
                )
            )

    duration = api_segments[-1].end if api_segments else (api_words[-1].end if api_words else 0.0)

    return Transcription(
        segments=segments,
        language=getattr(response, "language", "en") or "en",
        duration=duration,
    )
