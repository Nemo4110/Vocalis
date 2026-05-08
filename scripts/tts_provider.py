"""
TTS Provider Abstraction Layer
Supports: edge-tts (default), OpenAI TTS, system TTS
"""

import os
import abc
import asyncio
import tempfile
from pathlib import Path
from typing import Optional


class TTSProvider(abc.ABC):
    """Abstract base class for TTS providers."""

    @abc.abstractmethod
    async def synthesize(self, text: str, output_path: str) -> str:
        """Synthesize text to speech and save to output_path.

        Returns:
            Path to the generated audio file.
        """
        pass

    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass


class EdgeTTSProvider(TTSProvider):
    """Microsoft Edge TTS - free, no API key needed."""

    def __init__(
        self,
        voice: str = "en-US-AvaNeural",
        rate: str = "-10%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
    ):
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.pitch = pitch

    @property
    def name(self) -> str:
        return "edge_tts"

    async def synthesize(self, text: str, output_path: str) -> str:
        try:
            import edge_tts
        except ImportError:
            raise ImportError("edge-tts not installed. Run: pip install edge-tts")

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            volume=self.volume,
            pitch=self.pitch,
        )
        await communicate.save(output_path)
        return output_path

    def list_voices(self) -> list[dict]:
        """List available voices. Requires async."""
        try:
            import edge_tts
        except ImportError:
            raise ImportError("edge-tts not installed.")

        # edge-tts voices can be listed via CLI: edge-tts --list-voices
        # In code, we can use the VoicesManager
        # This is a sync wrapper for demo purposes
        import subprocess
        result = subprocess.run(
            ["edge-tts", "--list-voices"],
            capture_output=True,
            text=True,
        )
        voices = []
        for line in result.stdout.strip().split("\n")[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 4:
                voices.append({
                    "name": parts[0],
                    "locale": parts[1],
                    "gender": parts[2],
                    "content_categories": parts[3] if len(parts) > 3 else "",
                })
        return voices


class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS API - requires API key."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "tts-1",
        voice: str = "alloy",
        speed: float = 1.0,
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var.")
        self.model = model
        self.voice = voice
        self.speed = speed

    @property
    def name(self) -> str:
        return "openai"

    async def synthesize(self, text: str, output_path: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)

        response = client.audio.speech.create(
            model=self.model,
            voice=self.voice,
            input=text,
            speed=self.speed,
        )

        response.stream_to_file(output_path)
        return output_path


class SystemTTSProvider(TTSProvider):
    """System TTS using pyttsx3 - offline, no network needed."""

    def __init__(self, engine: str = "sapi5", rate: int = 150):
        self.engine_name = engine
        self.rate = rate

    @property
    def name(self) -> str:
        return "system"

    async def synthesize(self, text: str, output_path: str) -> str:
        try:
            import pyttsx3
        except ImportError:
            raise ImportError("pyttsx3 not installed. Run: pip install pyttsx3")

        # pyttsx3 is synchronous, run in a way that doesn't block async
        import threading

        def _synthesize():
            engine = pyttsx3.init(self.engine_name)
            engine.setProperty("rate", self.rate)
            engine.save_to_file(text, output_path)
            engine.runAndWait()

        # Run in thread pool
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _synthesize)
        return output_path


class TTSProviderFactory:
    """Factory for creating TTS providers from config."""

    @staticmethod
    def create(config: dict) -> TTSProvider:
        provider_name = config.get("provider", "edge_tts")

        if provider_name == "edge_tts":
            cfg = config.get("edge_tts", {})
            return EdgeTTSProvider(
                voice=cfg.get("voice", "en-US-AvaNeural"),
                rate=cfg.get("rate", "-10%"),
                volume=cfg.get("volume", "+0%"),
                pitch=cfg.get("pitch", "+0Hz"),
            )
        elif provider_name == "openai":
            cfg = config.get("openai", {})
            return OpenAITTSProvider(
                model=cfg.get("model", "tts-1"),
                voice=cfg.get("voice", "alloy"),
                speed=cfg.get("speed", 1.0),
            )
        elif provider_name == "system":
            cfg = config.get("system", {})
            return SystemTTSProvider(
                engine=cfg.get("engine", "sapi5"),
                rate=cfg.get("rate", 150),
            )
        else:
            raise ValueError(f"Unknown TTS provider: {provider_name}")
