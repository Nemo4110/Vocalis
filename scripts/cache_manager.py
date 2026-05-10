"""
Cache manager for TTS reference audio and Whisper transcriptions.

Caches expensive operations to avoid repeated API calls:
- TTS: key = hash(text + voice_config) -> audio file path
- Transcription: key = hash(audio content) -> TranscriptionResult
"""

import hashlib
import json
import pickle
from pathlib import Path
from typing import Optional, Any

from transcriber import TranscriptionResult


class CacheManager:
    """Manages disk-based caching for TTS and transcription results."""

    def __init__(self, cache_dir: str = "./data/cache"):
        self.cache_dir = Path(cache_dir)
        self.tts_dir = self.cache_dir / "tts"
        self.transcription_dir = self.cache_dir / "transcription"

        self.tts_dir.mkdir(parents=True, exist_ok=True)
        self.transcription_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _hash_text(text: str, extra: str = "") -> str:
        """Create a hash key from text and optional extra data."""
        content = f"{text}::{extra}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _hash_file(file_path: str) -> str:
        """Create a hash key from file contents."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()[:16]

    # ── TTS Cache ──

    def get_tts_path(self, text: str, voice_config: dict) -> Optional[Path]:
        """Get cached TTS audio path if it exists."""
        key = self._hash_text(text, json.dumps(voice_config, sort_keys=True))
        cached = self.tts_dir / f"{key}.mp3"
        if cached.exists():
            return cached
        return None

    def save_tts_path(self, text: str, voice_config: dict, audio_path: str) -> Path:
        """Store TTS audio in cache and return the cached path."""
        key = self._hash_text(text, json.dumps(voice_config, sort_keys=True))
        cached = self.tts_dir / f"{key}.mp3"
        import shutil
        shutil.copy2(audio_path, cached)
        return cached

    # ── Transcription Cache ──

    def get_transcription(self, audio_path: str) -> Optional[TranscriptionResult]:
        """Get cached transcription if it exists."""
        key = self._hash_file(audio_path)
        cached = self.transcription_dir / f"{key}.pkl"
        if cached.exists():
            try:
                with open(cached, "rb") as f:
                    return pickle.load(f)
            except Exception:
                return None
        return None

    def save_transcription(self, audio_path: str, result: TranscriptionResult) -> None:
        """Store transcription result in cache."""
        key = self._hash_file(audio_path)
        cached = self.transcription_dir / f"{key}.pkl"
        with open(cached, "wb") as f:
            pickle.dump(result, f)

    # ── Cache Management ──

    def clear(self) -> None:
        """Clear all cached data."""
        import shutil
        if self.tts_dir.exists():
            shutil.rmtree(self.tts_dir)
            self.tts_dir.mkdir(parents=True, exist_ok=True)
        if self.transcription_dir.exists():
            shutil.rmtree(self.transcription_dir)
            self.transcription_dir.mkdir(parents=True, exist_ok=True)

    def stats(self) -> dict:
        """Return cache statistics."""
        tts_files = list(self.tts_dir.glob("*.mp3")) if self.tts_dir.exists() else []
        trans_files = list(self.transcription_dir.glob("*.pkl")) if self.transcription_dir.exists() else []

        tts_size = sum(f.stat().st_size for f in tts_files)
        trans_size = sum(f.stat().st_size for f in trans_files)

        return {
            "tts_count": len(tts_files),
            "tts_size_mb": round(tts_size / (1024 * 1024), 2),
            "transcription_count": len(trans_files),
            "transcription_size_mb": round(trans_size / (1024 * 1024), 2),
            "total_size_mb": round((tts_size + trans_size) / (1024 * 1024), 2),
        }
