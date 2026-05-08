"""
Pytest configuration and shared fixtures for Vocalis tests.
"""

import sys
from pathlib import Path

# Add scripts directory to Python path for all tests
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

import pytest
from transcriber import TranscriptionResult, SegmentInfo, WordTimestamp


@pytest.fixture
def sample_reference_text():
    """Sample reference text for testing."""
    return "The quick brown fox jumps over the lazy dog"


@pytest.fixture
def sample_user_transcription():
    """Sample user transcription with word timestamps."""
    words = [
        WordTimestamp("The", 0.0, 0.25),
        WordTimestamp("quick", 0.30, 0.65),
        WordTimestamp("brown", 0.70, 1.05),
        WordTimestamp("fox", 1.10, 1.45),
        WordTimestamp("jumps", 1.55, 2.00),
        WordTimestamp("over", 2.05, 2.40),
        WordTimestamp("the", 2.45, 2.70),
        WordTimestamp("lazy", 2.80, 3.20),
        WordTimestamp("dog", 3.25, 3.60),
    ]
    return TranscriptionResult(
        text="The quick brown fox jumps over the lazy dog",
        language="en",
        duration=3.8,
        segments=[
            SegmentInfo(
                id=0,
                text="The quick brown fox jumps over the lazy dog",
                start=0.0,
                end=3.8,
                avg_logprob=-0.25,
                words=words,
            )
        ],
        words=words,
    )


@pytest.fixture
def sample_reference_transcription():
    """Sample reference (TTS) transcription with word timestamps."""
    words = [
        WordTimestamp("The", 0.0, 0.20),
        WordTimestamp("quick", 0.22, 0.52),
        WordTimestamp("brown", 0.54, 0.84),
        WordTimestamp("fox", 0.86, 1.16),
        WordTimestamp("jumps", 1.20, 1.55),
        WordTimestamp("over", 1.57, 1.87),
        WordTimestamp("the", 1.89, 2.09),
        WordTimestamp("lazy", 2.12, 2.47),
        WordTimestamp("dog", 2.49, 2.79),
    ]
    return TranscriptionResult(
        text="The quick brown fox jumps over the lazy dog",
        language="en",
        duration=2.9,
        segments=[
            SegmentInfo(
                id=0,
                text="The quick brown fox jumps over the lazy dog",
                start=0.0,
                end=2.9,
                avg_logprob=-0.15,
                words=words,
            )
        ],
        words=words,
    )


@pytest.fixture
def default_config():
    """Default configuration for testing."""
    return {
        "scoring": {
            "weights": {
                "accuracy": 0.30,
                "fluency": 0.25,
                "rhythm": 0.25,
                "clarity": 0.15,
                "completeness": 0.05,
            },
            "thresholds": {
                "wer_excellent": 0.05,
                "wer_good": 0.15,
                "wer_fair": 0.30,
                "wer_poor": 0.50,
                "wpm_ideal": 150,
                "wpm_tolerance": 30,
                "duration_diff_excellent": 0.10,
                "duration_diff_good": 0.25,
                "duration_diff_fair": 0.50,
                "clarity_excellent": -0.3,
                "clarity_good": -0.5,
                "clarity_fair": -0.8,
            },
        },
        "tts": {
            "provider": "edge_tts",
            "edge_tts": {
                "voice": "en-US-AvaNeural",
                "rate": "-10%",
            },
        },
        "whisper": {
            "model": "whisper-1",
            "language": "en",
        },
        "paths": {
            "data_dir": "./data",
            "reports_dir": "./reports",
            "history_file": "./data/test_history.json",
        },
    }


@pytest.fixture
def temp_history_file(tmp_path):
    """Provide a temporary history file path."""
    return tmp_path / "test_history.json"
