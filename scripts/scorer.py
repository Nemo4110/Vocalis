"""
Speech scoring engine with configurable weights and thresholds.

Dimensions:
  - accuracy: WER-based content accuracy
  - fluency: speed, pauses, filler words
  - rhythm: timing consistency vs reference audio
  - clarity: Whisper confidence scores
  - completeness: did user read all words?
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher

from transcriber import TranscriptionResult, WordTimestamp


@dataclass
class WordAlignment:
    """Alignment result for a single word."""
    ref_word: str           # Reference word
    user_word: Optional[str] = None
    user_start: Optional[float] = None
    user_end: Optional[float] = None
    ref_start: Optional[float] = None
    ref_end: Optional[float] = None
    status: str = "ok"      # ok, missing, extra, wrong, swapped
    duration_diff_pct: Optional[float] = None  # vs reference
    clarity_logprob: Optional[float] = None


@dataclass
class ScoringResult:
    """Complete scoring result for a practice session."""
    # Dimension scores (0-100)
    accuracy: float = 0.0
    fluency: float = 0.0
    rhythm: float = 0.0
    clarity: float = 0.0
    completeness: float = 0.0
    overall: float = 0.0

    # Raw metrics
    wer: float = 0.0
    wpm: float = 0.0
    pause_count: int = 0
    avg_pause_duration: float = 0.0
    rhythm_similarity: float = 0.0
    avg_logprob: float = 0.0
    word_count: int = 0
    missing_words: int = 0
    extra_words: int = 0

    # Word-level alignments
    word_alignments: List[WordAlignment] = field(default_factory=list)

    # Pause details
    pauses: List[Tuple[float, float, float]] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "scores": {
                "overall": round(self.overall, 1),
                "accuracy": round(self.accuracy, 1),
                "fluency": round(self.fluency, 1),
                "rhythm": round(self.rhythm, 1),
                "clarity": round(self.clarity, 1),
                "completeness": round(self.completeness, 1),
            },
            "metrics": {
                "wer": round(self.wer, 3),
                "wpm": round(self.wpm, 1),
                "pause_count": self.pause_count,
                "avg_pause_duration": round(self.avg_pause_duration, 2),
                "rhythm_similarity": round(self.rhythm_similarity, 3),
                "avg_logprob": round(self.avg_logprob, 3),
                "word_count": self.word_count,
                "missing_words": self.missing_words,
                "extra_words": self.extra_words,
            },
        }


class WordAligner:
    """Align reference words with user-spoken words using sequence matching."""

    @staticmethod
    def normalize(word: str) -> str:
        """Normalize word for comparison (lowercase, strip punctuation)."""
        return re.sub(r'[^\w\s]', '', word.lower().strip())

    @classmethod
    def align(
        cls,
        ref_words: List[str],
        user_words: List[WordTimestamp],
        ref_timestamps: Optional[List[Tuple[float, float]]] = None,
    ) -> List[WordAlignment]:
        """Align reference words with user words.

        Returns a list of WordAlignment, one per reference word.
        """
        ref_norm = [cls.normalize(w) for w in ref_words]
        user_norm = [cls.normalize(w.word) for w in user_words]

        # Use SequenceMatcher for alignment
        sm = SequenceMatcher(None, ref_norm, user_norm)

        alignments = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                # Matched words
                for i, j in zip(range(i1, i2), range(j1, j2)):
                    user_w = user_words[j]
                    alignment = WordAlignment(
                        ref_word=ref_words[i],
                        user_word=user_w.word,
                        user_start=user_w.start,
                        user_end=user_w.end,
                        status="ok",
                    )
                    if ref_timestamps and i < len(ref_timestamps):
                        alignment.ref_start = ref_timestamps[i][0]
                        alignment.ref_end = ref_timestamps[i][1]
                    alignments.append(alignment)

            elif tag == "replace":
                # Words replaced (wrong or swapped)
                max_len = max(i2 - i1, j2 - j1)
                for k in range(max_len):
                    i = i1 + k if k < (i2 - i1) else None
                    j = j1 + k if k < (j2 - j1) else None

                    alignment = WordAlignment(ref_word=ref_words[i] if i is not None else "")
                    if i is not None and ref_timestamps and i < len(ref_timestamps):
                        alignment.ref_start = ref_timestamps[i][0]
                        alignment.ref_end = ref_timestamps[i][1]

                    if j is not None:
                        user_w = user_words[j]
                        alignment.user_word = user_w.word
                        alignment.user_start = user_w.start
                        alignment.user_end = user_w.end

                    if i is not None and j is not None:
                        # Both exist - word was wrong
                        alignment.status = "wrong"
                    elif i is not None:
                        # Only reference - word missing
                        alignment.status = "missing"
                    else:
                        # Only user - extra word
                        alignment.status = "extra"

                    alignments.append(alignment)

            elif tag == "delete":
                # Words in reference but not in user (missing)
                for i in range(i1, i2):
                    alignment = WordAlignment(ref_word=ref_words[i])
                    if ref_timestamps and i < len(ref_timestamps):
                        alignment.ref_start = ref_timestamps[i][0]
                        alignment.ref_end = ref_timestamps[i][1]
                    alignment.status = "missing"
                    alignments.append(alignment)

            elif tag == "insert":
                # Words in user but not in reference (extra)
                for j in range(j1, j2):
                    user_w = user_words[j]
                    alignment = WordAlignment(
                        ref_word="",
                        user_word=user_w.word,
                        user_start=user_w.start,
                        user_end=user_w.end,
                        status="extra",
                    )
                    alignments.append(alignment)

        # Compute duration differences for aligned words
        for a in alignments:
            if (a.ref_start is not None and a.ref_end is not None
                    and a.user_start is not None and a.user_end is not None):
                ref_dur = a.ref_end - a.ref_start
                user_dur = a.user_end - a.user_start
                if ref_dur > 0:
                    a.duration_diff_pct = (user_dur - ref_dur) / ref_dur

        return alignments


class ScoringEngine:
    """Main scoring engine with configurable weights and thresholds."""

    def __init__(self, config: Dict):
        self.weights = config.get("scoring", {}).get("weights", {})
        self.thresholds = config.get("scoring", {}).get("thresholds", {})

    def score(
        self,
        reference_text: str,
        user_transcription: TranscriptionResult,
        reference_transcription: Optional[TranscriptionResult] = None,
    ) -> ScoringResult:
        """Score a user practice session.

        Args:
            reference_text: The text the user was supposed to read.
            user_transcription: TranscriptionResult from user's audio.
            reference_transcription: Optional TranscriptionResult from reference TTS audio.

        Returns:
            ScoringResult with all dimension scores.
        """
        # Split reference text into words
        ref_words = reference_text.split()

        # Build reference timestamps if available
        ref_timestamps = None
        if reference_transcription:
            ref_timestamps = [
                (w.start, w.end) for w in reference_transcription.words
            ]

        # Align words
        alignments = WordAligner.align(
            ref_words,
            user_transcription.words,
            ref_timestamps,
        )

        # Score each dimension
        accuracy = self._score_accuracy(alignments, ref_words)
        fluency = self._score_fluency(user_transcription)
        rhythm = self._score_rhythm(alignments)
        clarity = self._score_clarity(user_transcription)
        completeness = self._score_completeness(alignments, ref_words)

        # Compute weighted overall score
        overall = (
            accuracy * self.weights.get("accuracy", 0.30)
            + fluency * self.weights.get("fluency", 0.25)
            + rhythm * self.weights.get("rhythm", 0.25)
            + clarity * self.weights.get("clarity", 0.15)
            + completeness * self.weights.get("completeness", 0.05)
        )

        # Count stats
        missing_count = sum(1 for a in alignments if a.status == "missing")
        extra_count = sum(1 for a in alignments if a.status == "extra")

        # WER
        wer = self._compute_wer(alignments, ref_words)

        # Pauses
        pauses = user_transcription.get_pauses(threshold=0.3)

        return ScoringResult(
            accuracy=accuracy,
            fluency=fluency,
            rhythm=rhythm,
            clarity=clarity,
            completeness=completeness,
            overall=min(100, overall),
            wer=wer,
            wpm=user_transcription.wpm,
            pause_count=len(pauses),
            avg_pause_duration=sum(p[2] for p in pauses) / len(pauses) if pauses else 0,
            rhythm_similarity=sum(
                1.0 - abs(a.duration_diff_pct or 1.0)
                for a in alignments if a.duration_diff_pct is not None
            ) / max(1, sum(1 for a in alignments if a.duration_diff_pct is not None)),
            avg_logprob=user_transcription.avg_logprob,
            word_count=len(ref_words),
            missing_words=missing_count,
            extra_words=extra_count,
            word_alignments=alignments,
            pauses=pauses,
        )

    def _compute_wer(self, alignments: List[WordAlignment], ref_words: List[str]) -> float:
        """Compute Word Error Rate from alignments."""
        substitutions = sum(1 for a in alignments if a.status == "wrong")
        deletions = sum(1 for a in alignments if a.status == "missing")
        insertions = sum(1 for a in alignments if a.status == "extra")
        ref_len = len(ref_words)
        if ref_len == 0:
            return 0.0
        return (substitutions + deletions + insertions) / ref_len

    def _score_accuracy(self, alignments: List[WordAlignment], ref_words: List[str]) -> float:
        """Score content accuracy based on WER."""
        wer = self._compute_wer(alignments, ref_words)

        t = self.thresholds
        wer_ex = t.get("wer_excellent", 0.05)
        wer_good = t.get("wer_good", 0.15)
        wer_fair = t.get("wer_fair", 0.30)
        wer_poor = t.get("wer_poor", 0.50)

        if wer <= wer_ex:
            # Linear from 100 to 90
            return 100 - (wer / wer_ex) * 10
        elif wer <= wer_good:
            return 90 - ((wer - wer_ex) / (wer_good - wer_ex)) * 15
        elif wer <= wer_fair:
            return 75 - ((wer - wer_good) / (wer_fair - wer_good)) * 25
        elif wer <= wer_poor:
            return 50 - ((wer - wer_fair) / (wer_poor - wer_fair)) * 30
        else:
            return max(0, 20 - (wer - wer_poor) * 40)

    def _score_fluency(self, transcription: TranscriptionResult) -> float:
        """Score fluency based on speed and pauses."""
        wpm = transcription.wpm
        t = self.thresholds
        ideal_wpm = t.get("wpm_ideal", 150)
        tolerance = t.get("wpm_tolerance", 30)

        # Speed score (peak at ideal, taper off)
        speed_deviation = abs(wpm - ideal_wpm)
        if speed_deviation <= tolerance:
            speed_score = 100 - (speed_deviation / tolerance) * 20
        elif speed_deviation <= tolerance * 2:
            speed_score = 80 - ((speed_deviation - tolerance) / tolerance) * 30
        else:
            speed_score = max(30, 50 - (speed_deviation - tolerance * 2) * 0.5)

        # Pause score
        pauses = transcription.get_pauses(threshold=0.3)
        if not pauses:
            pause_score = 100
        else:
            # Check for pauses within sentences (bad) vs between sentences (ok)
            # For simplicity: penalize based on pause frequency and duration
            avg_pause = sum(p[2] for p in pauses) / len(pauses)
            pause_freq = len(pauses) / max(1, transcription.word_count)

            # Ideal: few short pauses
            if avg_pause <= 0.5 and pause_freq <= 0.1:
                pause_score = 100
            elif avg_pause <= 1.0 and pause_freq <= 0.2:
                pause_score = 85
            elif avg_pause <= 1.5 and pause_freq <= 0.3:
                pause_score = 70
            else:
                pause_score = max(40, 70 - (avg_pause - 1.0) * 10 - (pause_freq - 0.3) * 50)

        return speed_score * 0.6 + pause_score * 0.4

    def _score_rhythm(self, alignments: List[WordAlignment]) -> float:
        """Score rhythm consistency vs reference audio.

        Compares word durations between user and reference.
        """
        scored_words = [a for a in alignments if a.duration_diff_pct is not None]
        if not scored_words:
            return 50.0  # No reference available

        t = self.thresholds
        ex = t.get("duration_diff_excellent", 0.10)
        good = t.get("duration_diff_good", 0.25)
        fair = t.get("duration_diff_fair", 0.50)

        scores = []
        for a in scored_words:
            diff = abs(a.duration_diff_pct)
            if diff <= ex:
                s = 100 - (diff / ex) * 10
            elif diff <= good:
                s = 90 - ((diff - ex) / (good - ex)) * 20
            elif diff <= fair:
                s = 70 - ((diff - good) / (fair - good)) * 30
            else:
                s = max(20, 40 - (diff - fair) * 40)
            scores.append(s)

        return sum(scores) / len(scores)

    def _score_clarity(self, transcription: TranscriptionResult) -> float:
        """Score pronunciation clarity based on Whisper confidence."""
        avg_lp = transcription.avg_logprob

        t = self.thresholds
        ex = t.get("clarity_excellent", -0.3)
        good = t.get("clarity_good", -0.5)
        fair = t.get("clarity_fair", -0.8)

        # Higher logprob = better (less negative)
        if avg_lp >= ex:
            return 100 - (ex - avg_lp) / (ex + 0.1) * 10
        elif avg_lp >= good:
            return 90 - (ex - avg_lp) / (ex - good) * 20
        elif avg_lp >= fair:
            return 70 - (good - avg_lp) / (good - fair) * 30
        else:
            return max(20, 40 - (fair - avg_lp) * 30)

    def _score_completeness(self, alignments: List[WordAlignment], ref_words: List[str]) -> float:
        """Score completeness (did user read all words?)."""
        ref_len = len(ref_words)
        if ref_len == 0:
            return 100.0

        missing = sum(1 for a in alignments if a.status == "missing")
        return max(0, 100 - (missing / ref_len) * 100)
