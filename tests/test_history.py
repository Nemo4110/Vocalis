"""Tests for HistoryManager."""

import pytest
from history import HistoryManager, SessionRecord


class TestHistoryManagerInitialization:
    """Tests for HistoryManager setup."""

    def test_creates_history_file_if_not_exists(self, temp_history_file):
        manager = HistoryManager(str(temp_history_file))
        assert temp_history_file.exists()
        assert manager.get_all_sessions() == []

    def test_loads_existing_history(self, temp_history_file):
        import json

        data = {
            "total_sessions": 1,
            "sessions": [
                {
                    "session_id": 1,
                    "timestamp": "2026-05-08T10:00:00",
                    "text_id": "test",
                    "text_title": "Test",
                    "text_category": "test",
                    "difficulty": "beginner",
                    "reference_text": "hello",
                    "overall": 80.0,
                    "accuracy": 85.0,
                    "fluency": 75.0,
                    "rhythm": 80.0,
                    "clarity": 90.0,
                    "completeness": 100.0,
                    "wer": 0.1,
                    "wpm": 140.0,
                    "pause_count": 2,
                    "avg_pause_duration": 0.5,
                    "rhythm_similarity": 0.8,
                    "word_count": 10,
                    "duration_seconds": 30.0,
                    "avg_logprob": -0.3,
                    "word_details": [],
                    "notes": "",
                }
            ],
        }
        temp_history_file.write_text(json.dumps(data), encoding="utf-8")

        manager = HistoryManager(str(temp_history_file))
        sessions = manager.get_all_sessions()
        assert len(sessions) == 1
        assert sessions[0].overall == 80.0


class TestAddSession:
    """Tests for adding sessions."""

    def test_adds_session_with_auto_id(self, temp_history_file):
        manager = HistoryManager(str(temp_history_file))

        record = SessionRecord(
            session_id=0,
            timestamp="2026-05-08T10:00:00",
            text_id="test",
            text_title="Test",
            text_category="test",
            difficulty="beginner",
            reference_text="hello",
            overall=85.0,
        )
        manager.add_session(record)

        sessions = manager.get_all_sessions()
        assert len(sessions) == 1
        assert sessions[0].session_id == 1  # Auto-assigned

    def test_adds_multiple_sessions(self, temp_history_file):
        manager = HistoryManager(str(temp_history_file))

        for i in range(5):
            record = SessionRecord(
                session_id=0,
                timestamp=f"2026-05-08T10:0{i}:00",
                text_id="test",
                text_title="Test",
                text_category="test",
                difficulty="beginner",
                reference_text="hello",
                overall=70.0 + i * 5,
            )
            manager.add_session(record)

        sessions = manager.get_all_sessions()
        assert len(sessions) == 5
        assert [s.session_id for s in sessions] == [1, 2, 3, 4, 5]


class TestPersonalBest:
    """Tests for personal best tracking."""

    def test_returns_none_when_empty(self, temp_history_file):
        manager = HistoryManager(str(temp_history_file))
        assert manager.get_personal_best() is None

    def test_finds_overall_best(self, temp_history_file):
        manager = HistoryManager(str(temp_history_file))

        scores = [75.0, 85.0, 80.0, 90.0, 82.0]
        for i, score in enumerate(scores):
            record = SessionRecord(
                session_id=0,
                timestamp=f"2026-05-08T10:0{i}:00",
                text_id="test",
                text_title="Test",
                text_category="test",
                difficulty="beginner",
                reference_text="hello",
                overall=score,
            )
            manager.add_session(record)

        best = manager.get_personal_best()
        assert best.overall == 90.0
        assert best.session_id == 4

    def test_finds_best_per_text(self, temp_history_file):
        manager = HistoryManager(str(temp_history_file))

        for text_id, score in [("text_a", 80.0), ("text_b", 90.0), ("text_a", 85.0)]:
            record = SessionRecord(
                session_id=0,
                timestamp="2026-05-08T10:00:00",
                text_id=text_id,
                text_title="Test",
                text_category="test",
                difficulty="beginner",
                reference_text="hello",
                overall=score,
            )
            manager.add_session(record)

        best_a = manager.get_personal_best("text_a")
        best_b = manager.get_personal_best("text_b")

        assert best_a.overall == 85.0
        assert best_b.overall == 90.0


class TestProgress:
    """Tests for progress data retrieval."""

    def test_returns_progress_data(self, temp_history_file):
        manager = HistoryManager(str(temp_history_file))

        for i in range(3):
            record = SessionRecord(
                session_id=0,
                timestamp=f"2026-05-0{i+1}T10:00:00",
                text_id="test",
                text_title="Test",
                text_category="test",
                difficulty="beginner",
                reference_text="hello",
                overall=70.0 + i * 10,
            )
            manager.add_session(record)

        progress = manager.get_progress()
        assert len(progress["session_ids"]) == 3
        assert progress["overall"] == [70.0, 80.0, 90.0]

    def test_returns_progress_for_specific_text(self, temp_history_file):
        manager = HistoryManager(str(temp_history_file))

        for text_id in ["text_a", "text_b", "text_a", "text_b"]:
            record = SessionRecord(
                session_id=0,
                timestamp="2026-05-08T10:00:00",
                text_id=text_id,
                text_title="Test",
                text_category="test",
                difficulty="beginner",
                reference_text="hello",
                overall=80.0,
            )
            manager.add_session(record)

        progress = manager.get_progress("text_a")
        assert len(progress["session_ids"]) == 2


class TestStatistics:
    """Tests for statistics computation."""

    def test_returns_empty_stats_when_no_sessions(self, temp_history_file):
        manager = HistoryManager(str(temp_history_file))
        stats = manager.get_statistics()
        assert stats["total_sessions"] == 0

    def test_computes_correct_statistics(self, temp_history_file):
        manager = HistoryManager(str(temp_history_file))

        scores = [70.0, 80.0, 90.0]
        for i, score in enumerate(scores):
            record = SessionRecord(
                session_id=0,
                timestamp=f"2026-05-0{i+1}T10:00:00",
                text_id=f"text_{i}",
                text_title="Test",
                text_category="test",
                difficulty="beginner",
                reference_text="hello",
                overall=score,
                duration_seconds=30.0,
            )
            manager.add_session(record)

        stats = manager.get_statistics()
        assert stats["total_sessions"] == 3
        assert stats["average_score"] == 80.0
        assert stats["best_score"] == 90.0
        assert stats["worst_score"] == 70.0
        assert stats["improvement"] == 20.0  # 90 - 70
        assert stats["unique_texts"] == 3
        assert stats["total_practice_minutes"] == 1.5  # 90 seconds / 60


class TestWeakWords:
    """Tests for weak word identification."""

    def test_returns_empty_when_no_sessions(self, temp_history_file):
        manager = HistoryManager(str(temp_history_file))
        weak = manager.get_weak_words()
        assert weak == []

    def test_identifies_frequently_wrong_words(self, temp_history_file):
        manager = HistoryManager(str(temp_history_file))

        # Session 1: "hello" wrong
        record1 = SessionRecord(
            session_id=1,
            timestamp="2026-05-08T10:00:00",
            text_id="test",
            text_title="Test",
            text_category="test",
            difficulty="beginner",
            reference_text="hello world",
            overall=80.0,
            word_details=[
                {"word": "hello", "status": "wrong"},
                {"word": "world", "status": "ok"},
            ],
        )
        manager.add_session(record1)

        # Session 2: "hello" wrong again
        record2 = SessionRecord(
            session_id=2,
            timestamp="2026-05-08T10:01:00",
            text_id="test",
            text_title="Test",
            text_category="test",
            difficulty="beginner",
            reference_text="hello world",
            overall=85.0,
            word_details=[
                {"word": "hello", "status": "wrong"},
                {"word": "world", "status": "ok"},
            ],
        )
        manager.add_session(record2)

        weak = manager.get_weak_words()
        assert len(weak) >= 1
        assert weak[0][0] == "hello"  # Most problematic word
        assert weak[0][1] == 2  # 2 errors
        assert weak[0][3] == 1.0  # 100% error rate
