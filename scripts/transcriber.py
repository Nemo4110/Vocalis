"""
Whisper-based speech transcription with word-level timestamps.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class WordTimestamp:
    """A single word with its timestamp."""
    word: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class SegmentInfo:
    """A segment (sentence/phrase) with metadata."""
    id: int
    text: str
    start: float
    end: float
    avg_logprob: float
    words: List[WordTimestamp] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class TranscriptionResult:
    """Complete transcription result."""
    text: str
    language: str
    duration: float
    segments: List[SegmentInfo]
    words: List[WordTimestamp]

    @property
    def word_count(self) -> int:
        return len(self.words)

    @property
    def avg_word_duration(self) -> float:
        if not self.words:
            return 0.0
        return sum(w.duration for w in self.words) / len(self.words)

    @property
    def avg_logprob(self) -> float:
        if not self.segments:
            return 0.0
        return sum(s.avg_logprob for s in self.segments) / len(self.segments)

    @property
    def wpm(self) -> float:
        """Words per minute."""
        if self.duration <= 0:
            return 0.0
        return self.word_count / self.duration * 60

    def get_pauses(self, threshold: float = 0.3) -> List[tuple]:
        """Detect pauses between words. Returns list of (start, end, duration)."""
        pauses = []
        for i in range(1, len(self.words)):
            prev_end = self.words[i - 1].end
            curr_start = self.words[i].start
            gap = curr_start - prev_end
            if gap >= threshold:
                pauses.append((prev_end, curr_start, gap))
        return pauses


class WhisperTranscriber:
    """Transcribe audio using OpenAI Whisper API with word-level timestamps."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "whisper-1",
        language: str = "en",
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var.")
        self.model = model
        self.language = language

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        """Transcribe an audio file.

        Args:
            audio_path: Path to the audio file.

        Returns:
            TranscriptionResult with word-level timestamps.
        """
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)

        with open(audio_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["word", "segment"],
                language=self.language,
            )

        # Parse response
        return self._parse_response(response)

    def _parse_response(self, response) -> TranscriptionResult:
        """Parse Whisper API response into TranscriptionResult."""
        # Convert response to dict if it's an object
        if hasattr(response, "model_dump"):
            data = response.model_dump()
        elif hasattr(response, "__dict__"):
            data = response.__dict__
        else:
            data = response

        # Parse words
        words = []
        raw_words = data.get("words", [])
        for w in raw_words:
            if isinstance(w, dict):
                words.append(WordTimestamp(
                    word=w.get("word", "").strip(),
                    start=w.get("start", 0.0),
                    end=w.get("end", 0.0),
                ))
            else:
                # Object attribute access
                words.append(WordTimestamp(
                    word=getattr(w, "word", "").strip(),
                    start=getattr(w, "start", 0.0),
                    end=getattr(w, "end", 0.0),
                ))

        # Parse segments
        segments = []
        raw_segments = data.get("segments", [])
        for s in raw_segments:
            if isinstance(s, dict):
                seg = SegmentInfo(
                    id=s.get("id", 0),
                    text=s.get("text", "").strip(),
                    start=s.get("start", 0.0),
                    end=s.get("end", 0.0),
                    avg_logprob=s.get("avg_logprob", 0.0),
                )
            else:
                seg = SegmentInfo(
                    id=getattr(s, "id", 0),
                    text=getattr(s, "text", "").strip(),
                    start=getattr(s, "start", 0.0),
                    end=getattr(s, "end", 0.0),
                    avg_logprob=getattr(s, "avg_logprob", 0.0),
                )

            # Attach words that fall within this segment
            seg.words = [
                w for w in words
                if seg.start - 0.1 <= w.start <= seg.end + 0.1
            ]
            segments.append(seg)

        return TranscriptionResult(
            text=data.get("text", "").strip(),
            language=data.get("language", self.language),
            duration=data.get("duration", 0.0),
            segments=segments,
            words=words,
        )
