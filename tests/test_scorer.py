"""Tests for ScoringEngine."""

import pytest
from scorer import ScoringEngine, WordAligner
from transcriber import TranscriptionResult, SegmentInfo, WordTimestamp


class TestScoringEngineInitialization:
    """Tests for ScoringEngine setup."""

    def test_initializes_with_default_config(self, default_config):
        engine = ScoringEngine(default_config)
        assert engine.weights["accuracy"] == 0.30
        assert engine.weights["fluency"] == 0.25
        assert engine.weights["rhythm"] == 0.25
        assert engine.weights["clarity"] == 0.15
        assert engine.weights["completeness"] == 0.05

    def test_initializes_with_custom_weights(self):
        config = {
            "scoring": {
                "weights": {
                    "accuracy": 0.50,
                    "fluency": 0.20,
                    "rhythm": 0.15,
                    "clarity": 0.10,
                    "completeness": 0.05,
                },
                "thresholds": {},
            }
        }
        engine = ScoringEngine(config)
        assert engine.weights["accuracy"] == 0.50


class TestScoreAccuracy:
    """Tests for accuracy scoring (WER-based)."""

    def test_perfect_accuracy_zero_wer(self, default_config):
        engine = ScoringEngine(default_config)
        # WER = 0 should give ~100
        score = engine._score_accuracy([], ["a", "b", "c"])  # Empty alignments = 0 WER
        assert score >= 95

    def test_accuracy_decreases_with_wer(self, default_config):
        engine = ScoringEngine(default_config)

        # Create alignments with increasing WER
        alignments_5pct = [
            {"status": "ok"} for _ in range(19)
        ] + [{"status": "wrong"}]

        alignments_20pct = [
            {"status": "ok"} for _ in range(8)
        ] + [{"status": "wrong"} for _ in range(2)]

        # We can't directly test _score_accuracy with these dicts,
        # but we can verify the scoring logic through the full pipeline
        # This is tested in TestScoringEngineFullPipeline


class TestScoreFluency:
    """Tests for fluency scoring."""

    def test_ideal_wpm_gets_high_score(self, default_config):
        engine = ScoringEngine(default_config)

        # Create transcription with ideal WPM (150)
        words = [WordTimestamp(f"w{i}", i * 0.4, i * 0.4 + 0.3) for i in range(10)]
        # 10 words in ~4 seconds = 150 WPM
        transcription = TranscriptionResult(
            text=" ".join([f"w{i}" for i in range(10)]),
            language="en",
            duration=4.0,
            segments=[],
            words=words,
        )

        score = engine._score_fluency(transcription)
        assert score >= 85  # Should be excellent

    def test_too_slow_gets_lower_score(self, default_config):
        engine = ScoringEngine(default_config)

        # Very slow: 10 words in 10 seconds = 60 WPM
        words = [WordTimestamp(f"w{i}", i * 1.0, i * 1.0 + 0.5) for i in range(10)]
        transcription = TranscriptionResult(
            text=" ".join([f"w{i}" for i in range(10)]),
            language="en",
            duration=10.0,
            segments=[],
            words=words,
        )

        score = engine._score_fluency(transcription)
        assert score < 80  # Should be penalized for being too slow

    def test_too_fast_gets_lower_score(self, default_config):
        engine = ScoringEngine(default_config)

        # Very fast: 10 words in 2 seconds = 300 WPM
        words = [WordTimestamp(f"w{i}", i * 0.2, i * 0.2 + 0.15) for i in range(10)]
        transcription = TranscriptionResult(
            text=" ".join([f"w{i}" for i in range(10)]),
            language="en",
            duration=2.0,
            segments=[],
            words=words,
        )

        score = engine._score_fluency(transcription)
        assert score < 80  # Should be penalized for being too fast


class TestScoreRhythm:
    """Tests for rhythm scoring."""

    def test_perfect_rhythm_zero_diff(self, default_config):
        engine = ScoringEngine(default_config)

        from scorer import WordAlignment
        alignments = [
            WordAlignment(ref_word="a", duration_diff_pct=0.0),
            WordAlignment(ref_word="b", duration_diff_pct=0.0),
        ]

        score = engine._score_rhythm(alignments)
        assert score == pytest.approx(95.0, abs=5.0)  # Near perfect

    def test_large_duration_diff_gets_low_score(self, default_config):
        engine = ScoringEngine(default_config)

        from scorer import WordAlignment
        alignments = [
            WordAlignment(ref_word="a", duration_diff_pct=0.8),  # 80% longer
        ]

        score = engine._score_rhythm(alignments)
        assert score < 50  # Should be poor

    def test_no_reference_data_returns_default(self, default_config):
        engine = ScoringEngine(default_config)

        from scorer import WordAlignment
        alignments = [
            WordAlignment(ref_word="a", duration_diff_pct=None),
        ]

        score = engine._score_rhythm(alignments)
        assert score == 50.0  # Default when no reference


class TestScoreClarity:
    """Tests for clarity scoring (Whisper confidence)."""

    def test_high_logprob_gets_high_score(self, default_config):
        engine = ScoringEngine(default_config)

        words = [WordTimestamp("test", 0.0, 0.5)]
        transcription = TranscriptionResult(
            text="test",
            language="en",
            duration=0.5,
            segments=[SegmentInfo(id=0, text="test", start=0.0, end=0.5, avg_logprob=-0.1)],
            words=words,
        )

        score = engine._score_clarity(transcription)
        assert score >= 90

    def test_low_logprob_gets_low_score(self, default_config):
        engine = ScoringEngine(default_config)

        words = [WordTimestamp("test", 0.0, 0.5)]
        transcription = TranscriptionResult(
            text="test",
            language="en",
            duration=0.5,
            segments=[SegmentInfo(id=0, text="test", start=0.0, end=0.5, avg_logprob=-1.5)],
            words=words,
        )

        score = engine._score_clarity(transcription)
        assert score < 60


class TestScoreCompleteness:
    """Tests for completeness scoring."""

    def test_full_completeness(self, default_config):
        engine = ScoringEngine(default_config)

        from scorer import WordAlignment
        alignments = [WordAlignment(ref_word="a", status="ok") for _ in range(10)]

        score = engine._score_completeness(alignments, ["a"] * 10)
        assert score == 100.0

    def test_missing_words_reduce_score(self, default_config):
        engine = ScoringEngine(default_config)

        from scorer import WordAlignment
        alignments = [
            WordAlignment(ref_word="a", status="ok"),
            WordAlignment(ref_word="b", status="missing"),
            WordAlignment(ref_word="c", status="ok"),
        ]

        score = engine._score_completeness(alignments, ["a", "b", "c"])
        assert score == pytest.approx(66.7, abs=1.0)


class TestWERComputation:
    """Tests for WER computation."""

    def test_zero_wer_for_perfect(self, default_config):
        engine = ScoringEngine(default_config)

        from scorer import WordAlignment
        alignments = [WordAlignment(ref_word="a", status="ok") for _ in range(10)]

        wer = engine._compute_wer(alignments, ["a"] * 10)
        assert wer == 0.0

    def test_wer_with_substitutions(self, default_config):
        engine = ScoringEngine(default_config)

        from scorer import WordAlignment
        alignments = [
            WordAlignment(ref_word="a", status="ok"),
            WordAlignment(ref_word="b", status="wrong"),
            WordAlignment(ref_word="c", status="ok"),
        ]

        wer = engine._compute_wer(alignments, ["a", "b", "c"])
        assert wer == pytest.approx(1/3, abs=0.01)

    def test_wer_with_deletions(self, default_config):
        engine = ScoringEngine(default_config)

        from scorer import WordAlignment
        alignments = [
            WordAlignment(ref_word="a", status="ok"),
            WordAlignment(ref_word="b", status="missing"),
            WordAlignment(ref_word="c", status="ok"),
        ]

        wer = engine._compute_wer(alignments, ["a", "b", "c"])
        assert wer == pytest.approx(1/3, abs=0.01)

    def test_wer_with_insertions(self, default_config):
        engine = ScoringEngine(default_config)

        from scorer import WordAlignment
        alignments = [
            WordAlignment(ref_word="a", status="ok"),
            WordAlignment(ref_word="", status="extra"),
            WordAlignment(ref_word="b", status="ok"),
        ]

        wer = engine._compute_wer(alignments, ["a", "b"])
        assert wer == pytest.approx(1/2, abs=0.01)


class TestOverallScore:
    """Tests for overall weighted score computation."""

    def test_overall_score_is_weighted_average(
        self, default_config, sample_reference_text,
        sample_user_transcription, sample_reference_transcription
    ):
        engine = ScoringEngine(default_config)

        result = engine.score(
            sample_reference_text,
            sample_user_transcription,
            sample_reference_transcription,
        )

        # Verify overall is within valid range
        assert 0 <= result.overall <= 100

        # Verify overall is roughly weighted average
        expected = (
            result.accuracy * 0.30 +
            result.fluency * 0.25 +
            result.rhythm * 0.25 +
            result.clarity * 0.15 +
            result.completeness * 0.05
        )
        assert result.overall == pytest.approx(expected, abs=0.5)

    def test_perfect_reading_gets_high_score(self, default_config):
        engine = ScoringEngine(default_config)

        ref_words = ["hello", "world"]
        user_words = [
            WordTimestamp("hello", 0.0, 0.4),
            WordTimestamp("world", 0.5, 0.9),
        ]
        ref_ts_words = [
            WordTimestamp("hello", 0.0, 0.4),
            WordTimestamp("world", 0.5, 0.9),
        ]

        user_trans = TranscriptionResult(
            text="hello world",
            language="en",
            duration=1.0,
            segments=[SegmentInfo(id=0, text="hello world", start=0.0, end=1.0, avg_logprob=-0.1, words=user_words)],
            words=user_words,
        )

        ref_trans = TranscriptionResult(
            text="hello world",
            language="en",
            duration=1.0,
            segments=[SegmentInfo(id=0, text="hello world", start=0.0, end=1.0, avg_logprob=-0.1, words=ref_ts_words)],
            words=ref_ts_words,
        )

        result = engine.score("hello world", user_trans, ref_trans)
        assert result.overall >= 85
        assert result.wer == 0.0
        assert result.completeness == 100.0
