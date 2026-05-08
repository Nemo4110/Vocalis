"""Tests for WordAligner."""

import pytest
from scorer import WordAligner, WordAlignment
from transcriber import WordTimestamp


class TestWordAlignerNormalize:
    """Tests for word normalization."""

    def test_lowercases(self):
        assert WordAligner.normalize("Hello") == "hello"

    def test_removes_punctuation(self):
        assert WordAligner.normalize("dog.") == "dog"
        assert WordAligner.normalize("hello!") == "hello"
        assert WordAligner.normalize("what's") == "whats"

    def test_strips_whitespace(self):
        assert WordAligner.normalize("  word  ") == "word"


class TestWordAlignerPerfectMatch:
    """Tests for perfect alignment scenarios."""

    def test_perfect_match_all_ok(self, sample_reference_text, sample_user_transcription):
        ref_words = sample_reference_text.split()
        alignments = WordAligner.align(ref_words, sample_user_transcription.words)

        assert len(alignments) == len(ref_words)
        for a in alignments:
            assert a.status == "ok"
            assert a.user_word is not None

    def test_perfect_match_with_reference_timestamps(
        self, sample_reference_text, sample_user_transcription, sample_reference_transcription
    ):
        ref_words = sample_reference_text.split()
        ref_timestamps = [(w.start, w.end) for w in sample_reference_transcription.words]

        alignments = WordAligner.align(
            ref_words, sample_user_transcription.words, ref_timestamps
        )

        assert len(alignments) == len(ref_words)
        for a in alignments:
            assert a.ref_start is not None
            assert a.ref_end is not None
            assert a.duration_diff_pct is not None

    def test_duration_diff_computed_correctly(self):
        """When user word is 25% longer than reference, diff should be +0.25."""
        ref_words = ["test"]
        user_words = [WordTimestamp("test", 0.0, 1.25)]  # 1.25s duration
        ref_timestamps = [(0.0, 1.0)]  # 1.0s reference duration

        alignments = WordAligner.align(ref_words, user_words, ref_timestamps)
        assert len(alignments) == 1
        assert alignments[0].duration_diff_pct == pytest.approx(0.25, abs=0.01)


class TestWordAlignerMissingWords:
    """Tests for missing word detection."""

    def test_detects_missing_word_at_end(self):
        ref_words = ["hello", "world", "today"]
        user_words = [WordTimestamp("hello", 0.0, 0.5), WordTimestamp("world", 0.6, 1.0)]

        alignments = WordAligner.align(ref_words, user_words)

        statuses = [a.status for a in alignments]
        assert "missing" in statuses
        assert alignments[-1].status == "missing"
        assert alignments[-1].ref_word == "today"

    def test_detects_missing_word_at_start(self):
        ref_words = ["hello", "world", "today"]
        user_words = [WordTimestamp("world", 0.0, 0.5), WordTimestamp("today", 0.6, 1.0)]

        alignments = WordAligner.align(ref_words, user_words)

        assert alignments[0].status == "missing"
        assert alignments[0].ref_word == "hello"

    def test_detects_missing_word_in_middle(self):
        ref_words = ["the", "quick", "brown", "fox"]
        user_words = [
            WordTimestamp("the", 0.0, 0.2),
            WordTimestamp("brown", 0.5, 0.8),
            WordTimestamp("fox", 0.9, 1.2),
        ]

        alignments = WordAligner.align(ref_words, user_words)

        statuses = [a.status for a in alignments]
        assert statuses.count("missing") == 1
        missing = [a for a in alignments if a.status == "missing"]
        assert missing[0].ref_word == "quick"


class TestWordAlignerExtraWords:
    """Tests for extra word detection."""

    def test_detects_extra_word(self):
        ref_words = ["hello", "world"]
        user_words = [
            WordTimestamp("hello", 0.0, 0.5),
            WordTimestamp("um", 0.6, 0.8),
            WordTimestamp("world", 0.9, 1.3),
        ]

        alignments = WordAligner.align(ref_words, user_words)

        statuses = [a.status for a in alignments]
        assert "extra" in statuses
        extra = [a for a in alignments if a.status == "extra"]
        assert extra[0].user_word == "um"


class TestWordAlignerWrongWords:
    """Tests for wrong word detection."""

    def test_detects_wrong_word(self):
        ref_words = ["hello", "world"]
        user_words = [WordTimestamp("hello", 0.0, 0.5), WordTimestamp("earth", 0.6, 1.0)]

        alignments = WordAligner.align(ref_words, user_words)

        assert alignments[1].status == "wrong"
        assert alignments[1].ref_word == "world"
        assert alignments[1].user_word == "earth"


class TestWordAlignerPunctuation:
    """Tests for punctuation handling."""

    def test_punctuation_does_not_cause_mismatch(self):
        ref_words = ["dog."]
        user_words = [WordTimestamp("dog", 0.0, 0.5)]

        alignments = WordAligner.align(ref_words, user_words)

        assert alignments[0].status == "ok"
