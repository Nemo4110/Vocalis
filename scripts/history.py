"""
Practice history tracking and persistence.
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class SessionRecord:
    """A single practice session record."""
    session_id: int
    timestamp: str
    text_id: str
    text_title: str
    text_category: str
    difficulty: str
    reference_text: str

    # Scores (0-100)
    overall: float = 0.0
    accuracy: float = 0.0
    fluency: float = 0.0
    rhythm: float = 0.0
    clarity: float = 0.0
    completeness: float = 0.0

    # Raw metrics
    wer: float = 0.0
    wpm: float = 0.0
    pause_count: int = 0
    avg_pause_duration: float = 0.0
    rhythm_similarity: float = 0.0
    word_count: int = 0
    duration_seconds: float = 0.0
    avg_logprob: float = 0.0

    # Word-level details
    word_details: List[Dict[str, Any]] = field(default_factory=list)

    # Notes
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionRecord":
        return cls(**data)


class HistoryManager:
    """Manages practice session history."""

    def __init__(self, history_file: str = "./data/history.json"):
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self._records: List[SessionRecord] = []
        self._load()

    def _load(self) -> None:
        """Load history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._records = [
                        SessionRecord.from_dict(r) for r in data.get("sessions", [])
                    ]
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Could not load history file: {e}")
                self._records = []
        else:
            # Create empty history file
            self._save()

    def _save(self) -> None:
        """Save history to file."""
        data = {
            "total_sessions": len(self._records),
            "last_updated": datetime.now().isoformat(),
            "sessions": [r.to_dict() for r in self._records],
            "personal_bests": self._get_personal_bests(),
        }
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _get_personal_bests(self) -> Dict[str, Any]:
        """Compute personal bests from records."""
        if not self._records:
            return {}

        overall_best = max(self._records, key=lambda r: r.overall)

        # Best per text
        text_bests = {}
        for r in self._records:
            key = r.text_id
            if key not in text_bests or r.overall > text_bests[key]["score"]:
                text_bests[key] = {
                    "score": r.overall,
                    "session_id": r.session_id,
                    "timestamp": r.timestamp,
                }

        return {
            "overall_best": {
                "score": overall_best.overall,
                "session_id": overall_best.session_id,
                "timestamp": overall_best.timestamp,
            },
            "by_text": text_bests,
        }

    def add_session(self, record: SessionRecord) -> None:
        """Add a new session record."""
        if not record.session_id:
            record.session_id = len(self._records) + 1
        self._records.append(record)
        self._save()

    def get_all_sessions(self) -> List[SessionRecord]:
        """Get all session records."""
        return self._records[:]

    def get_sessions_for_text(self, text_id: str) -> List[SessionRecord]:
        """Get all sessions for a specific text."""
        return [r for r in self._records if r.text_id == text_id]

    def get_personal_best(self, text_id: Optional[str] = None) -> Optional[SessionRecord]:
        """Get personal best record (overall or for specific text)."""
        sessions = (
            self.get_sessions_for_text(text_id) if text_id else self._records
        )
        if not sessions:
            return None
        return max(sessions, key=lambda r: r.overall)

    def get_progress(self, text_id: Optional[str] = None) -> Dict[str, List]:
        """Get progress data for plotting.

        Returns dict with lists of session_ids, timestamps, and scores.
        """
        sessions = (
            self.get_sessions_for_text(text_id) if text_id else self._records
        )

        return {
            "session_ids": [r.session_id for r in sessions],
            "timestamps": [r.timestamp for r in sessions],
            "overall": [r.overall for r in sessions],
            "accuracy": [r.accuracy for r in sessions],
            "fluency": [r.fluency for r in sessions],
            "rhythm": [r.rhythm for r in sessions],
            "clarity": [r.clarity for r in sessions],
            "completeness": [r.completeness for r in sessions],
            "wer": [r.wer for r in sessions],
            "wpm": [r.wpm for r in sessions],
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics."""
        if not self._records:
            return {"total_sessions": 0}

        scores = [r.overall for r in self._records]
        return {
            "total_sessions": len(self._records),
            "average_score": sum(scores) / len(scores),
            "best_score": max(scores),
            "worst_score": min(scores),
            "improvement": scores[-1] - scores[0] if len(scores) > 1 else 0,
            "unique_texts": len(set(r.text_id for r in self._records)),
            "total_practice_minutes": sum(r.duration_seconds for r in self._records) / 60,
        }

    def get_weak_words(self, top_n: int = 20) -> List[tuple]:
        """Get most frequently problematic words.

        Returns list of (word, error_count, total_count, error_rate).
        """
        from collections import defaultdict

        word_stats = defaultdict(lambda: {"errors": 0, "total": 0})

        for record in self._records:
            for wd in record.word_details:
                word = wd.get("word", "").lower().strip(".,!?;:")
                if not word:
                    continue
                word_stats[word]["total"] += 1
                if wd.get("status") in ("missing", "wrong"):
                    word_stats[word]["errors"] += 1

        # Sort by error rate (minimum 2 occurrences)
        results = []
        for word, stats in word_stats.items():
            if stats["total"] >= 2:
                error_rate = stats["errors"] / stats["total"]
                results.append((word, stats["errors"], stats["total"], error_rate))

        results.sort(key=lambda x: (-x[3], -x[1]))
        return results[:top_n]
