"""
Oral Practice Prototype - Main workflow

Usage:
    python main.py --text "Your practice text here" --audio path/to/user_audio.wav
    python main.py --text "Your practice text here" --demo  (uses mock data)
"""

import os
import sys
import argparse
import asyncio
from pathlib import Path
from datetime import datetime

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config_loader import load_config
from tts_provider import TTSProviderFactory
from transcriber import WhisperTranscriber
from scorer import ScoringEngine
from reporter import ReportGenerator
from history import HistoryManager, SessionRecord
from plot_progress import ProgressPlotter
from text_library import TextLibrary
from cache_manager import CacheManager


class OralPracticeSession:
    """Manages a complete practice session workflow."""

    def __init__(self, config_path: str = "./config.yaml"):
        self.config = load_config(config_path)
        self.scorer = ScoringEngine(self.config)
        self.history = HistoryManager(
            self.config.get("paths", {}).get("history_file", "./data/history.json")
        )
        self.library = TextLibrary()
        self.cache = CacheManager(
            str(self.data_dir / "cache")
        )

        # Initialize Whisper transcriber
        whisper_cfg = self.config.get("whisper", {})
        self.transcriber = WhisperTranscriber(
            model=whisper_cfg.get("model", "whisper-1"),
            language=whisper_cfg.get("language", "en"),
        )

        # Data directories
        self.data_dir = Path(self.config.get("paths", {}).get("data_dir", "./data"))
        self.reports_dir = Path(self.config.get("paths", {}).get("reports_dir", "./reports"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    async def run_session(
        self,
        text: str,
        user_audio_path: str,
        text_id: str = "custom",
        text_title: str = "Practice Text",
        text_category: str = "custom",
        difficulty: str = "intermediate",
        generate_reference: bool = True,
    ) -> dict:
        """Run a complete practice session.

        Args:
            text: Reference text to practice.
            user_audio_path: Path to user's recorded audio.
            text_id: Unique identifier for this text.
            text_title: Human-readable title.
            text_category: Category (e.g., "classic_speeches").
            difficulty: Difficulty level.
            generate_reference: Whether to generate reference TTS audio.

        Returns:
            Dict with scoring result, report text, and output paths.
        """
        print(f"\n{'='*60}")
        print(f"🎤 Starting Practice Session")
        print(f"{'='*60}")
        print(f"Text: {text[:80]}{'...' if len(text) > 80 else ''}")
        print(f"Audio: {user_audio_path}")
        print()

        # Step 1: Generate reference audio (optional)
        reference_transcription = None
        if generate_reference:
            print("Step 1/5: Generating reference audio...")
            ref_audio_path = await self._generate_reference_audio(text, text_id)
            if ref_audio_path:
                print(f"  Reference audio: {ref_audio_path}")
                # Transcribe reference to get word timestamps (with caching)
                try:
                    cached_ref = self.cache.get_transcription(str(ref_audio_path))
                    if cached_ref:
                        reference_transcription = cached_ref
                        print(f"  Reference words: {reference_transcription.word_count} (cached)")
                    else:
                        reference_transcription = self.transcriber.transcribe(str(ref_audio_path))
                        self.cache.save_transcription(str(ref_audio_path), reference_transcription)
                        print(f"  Reference words: {reference_transcription.word_count}")
                except Exception as e:
                    print(f"  Warning: Could not transcribe reference: {e}")
            else:
                print("  Skipped (TTS not available)")
        else:
            print("Step 1/5: Reference audio generation skipped")

        # Step 2: Transcribe user audio (with caching)
        print("\nStep 2/5: Transcribing your audio...")
        cached_transcription = self.cache.get_transcription(user_audio_path)
        if cached_transcription:
            user_transcription = cached_transcription
            print(f"  (cached)")
        else:
            user_transcription = self.transcriber.transcribe(user_audio_path)
            self.cache.save_transcription(user_audio_path, user_transcription)
        print(f"  Detected words: {user_transcription.word_count}")
        print(f"  Duration: {user_transcription.duration:.1f}s")
        print(f"  Speed: {user_transcription.wpm:.0f} WPM")

        # Step 3: Score
        print("\nStep 3/5: Scoring...")
        result = self.scorer.score(text, user_transcription, reference_transcription)
        print(f"  Overall: {result.overall:.1f}/100")
        print(f"  Accuracy: {result.accuracy:.1f} | Fluency: {result.fluency:.1f}")
        print(f"  Rhythm: {result.rhythm:.1f} | Clarity: {result.clarity:.1f}")

        # Step 4: Save to history
        print("\nStep 4/5: Saving to history...")
        record = SessionRecord(
            session_id=0,  # Will be auto-assigned
            timestamp=datetime.now().isoformat(),
            text_id=text_id,
            text_title=text_title,
            text_category=text_category,
            difficulty=difficulty,
            reference_text=text,
            overall=result.overall,
            accuracy=result.accuracy,
            fluency=result.fluency,
            rhythm=result.rhythm,
            clarity=result.clarity,
            completeness=result.completeness,
            wer=result.wer,
            wpm=result.wpm,
            pause_count=result.pause_count,
            avg_pause_duration=result.avg_pause_duration,
            rhythm_similarity=result.rhythm_similarity,
            word_count=result.word_count,
            duration_seconds=user_transcription.duration,
            avg_logprob=result.avg_logprob,
            word_details=[
                {
                    "word": a.ref_word or a.user_word,
                    "user_word": a.user_word,
                    "status": a.status,
                    "duration_diff_pct": a.duration_diff_pct,
                }
                for a in result.word_alignments
            ],
        )
        self.history.add_session(record)

        # Step 5: Generate report and charts
        print("\nStep 5/5: Generating reports...")

        # Get previous best for comparison
        prev_best = self.history.get_personal_best(text_id)
        prev_best_score = prev_best.overall if prev_best else None

        # Text report
        report = ReportGenerator.generate(
            result, text, text_title, previous_best=prev_best_score
        )
        report_path = self.reports_dir / f"report_{record.session_id:03d}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"  Report: {report_path}")

        # Evolution chart
        progress = self.history.get_progress()
        if len(progress["session_ids"]) >= 1:
            chart_path = self.reports_dir / "progress_evolution.png"
            ProgressPlotter.plot_main_evolution(
                progress["session_ids"],
                progress["timestamps"],
                progress["overall"],
                output_path=str(chart_path),
            )
            print(f"  Evolution chart: {chart_path}")

            # Dimension trends
            trend_path = self.reports_dir / "dimension_trends.png"
            ProgressPlotter.plot_multi_dimension_trends(
                progress["session_ids"],
                progress["timestamps"],
                progress["accuracy"],
                progress["fluency"],
                progress["rhythm"],
                progress["clarity"],
                progress["completeness"],
                output_path=str(trend_path),
            )
            print(f"  Trend chart: {trend_path}")

            # Radar chart for this session
            radar_path = self.reports_dir / f"radar_{record.session_id:03d}.png"
            prev_scores = None
            if prev_best and prev_best.session_id != record.session_id:
                prev_scores = {
                    "accuracy": prev_best.accuracy,
                    "fluency": prev_best.fluency,
                    "rhythm": prev_best.rhythm,
                    "clarity": prev_best.clarity,
                    "completeness": prev_best.completeness,
                }
            ProgressPlotter.plot_radar_chart(
                {
                    "accuracy": result.accuracy,
                    "fluency": result.fluency,
                    "rhythm": result.rhythm,
                    "clarity": result.clarity,
                    "completeness": result.completeness,
                },
                output_path=str(radar_path),
                previous_scores=prev_scores,
            )
            print(f"  Radar chart: {radar_path}")

        # Text-specific progress
        text_progress = self.history.get_progress(text_id)
        if len(text_progress["session_ids"]) >= 2:
            text_chart_path = self.reports_dir / f"text_progress_{text_id}.png"
            ProgressPlotter.plot_text_comparison(
                list(range(1, len(text_progress["session_ids"]) + 1)),
                text_progress["overall"],
                text_title,
                output_path=str(text_chart_path),
            )
            print(f"  Text progress: {text_chart_path}")

        print(f"\n{'='*60}")
        print(f"✅ Session complete! Score: {result.overall:.1f}/100")
        print(f"{'='*60}\n")

        return {
            "result": result,
            "report": report,
            "report_path": str(report_path),
            "session_id": record.session_id,
        }

    async def _generate_reference_audio(self, text: str, text_id: str) -> Path:
        """Generate reference TTS audio for the text (with caching)."""
        tts_config = self.config.get("tts", {})
        voice_cfg = tts_config.get(tts_config.get("provider", "edge_tts"), {})

        # Check cache first
        cached = self.cache.get_tts_path(text, voice_cfg)
        if cached:
            print(f"  Reference audio (cached): {cached}")
            return cached

        try:
            provider = TTSProviderFactory.create(tts_config)
            output_path = self.data_dir / f"ref_{text_id}.mp3"
            await provider.synthesize(text, str(output_path))

            # Save to cache
            self.cache.save_tts_path(text, voice_cfg, str(output_path))
            return output_path
        except Exception as e:
            print(f"  Warning: TTS generation failed: {e}")
            return None

    def show_summary(self) -> str:
        """Generate and return a summary of all practice history."""
        stats = self.history.get_statistics()
        weak_words = self.history.get_weak_words(top_n=15)
        summary = ReportGenerator.generate_summary(stats, weak_words)

        summary_path = self.reports_dir / "summary.md"
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary)

        print(summary)
        print(f"\nSummary saved to: {summary_path}")
        return summary


def run_demo():
    """Run a demo session with mock data (no API calls)."""
    print("\n[DEMO MODE] Using mock data (no API calls)\n")

    from transcriber import TranscriptionResult, SegmentInfo, WordTimestamp
    from scorer import ScoringResult

    # Mock reference text
    text = "The quick brown fox jumps over the lazy dog."

    # Mock user transcription (user reads it correctly but slightly slower)
    user_words = [
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

    user_transcription = TranscriptionResult(
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
                words=user_words,
            )
        ],
        words=user_words,
    )

    # Mock reference transcription (faster, ideal pace)
    ref_words = [
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

    ref_transcription = TranscriptionResult(
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
                words=ref_words,
            )
        ],
        words=ref_words,
    )

    # Score
    config = load_config()
    engine = ScoringEngine(config)
    result = engine.score(text, user_transcription, ref_transcription)

    # Generate report
    report = ReportGenerator.generate(result, text, "Demo: Pangram")
    print(report)

    # Save report
    Path("./reports").mkdir(parents=True, exist_ok=True)
    with open("./reports/demo_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("\n" + "="*60)
    print("Demo report saved to: ./reports/demo_report.md")
    print("="*60)

    return result


async def main():
    parser = argparse.ArgumentParser(description="Vocalis Oral Practice Skill")
    parser.add_argument("--text", type=str, help="Reference text to practice")
    parser.add_argument("--audio", type=str, help="Path to user audio file")
    parser.add_argument("--text-id", type=str, default="custom", help="Text identifier (use with --text or select from library)")
    parser.add_argument("--title", type=str, default="Practice Text", help="Text title")
    parser.add_argument("--demo", action="store_true", help="Run with mock data (no API)")
    parser.add_argument("--summary", action="store_true", help="Show practice summary")
    parser.add_argument("--config", type=str, default="./config.yaml", help="Config file path")
    parser.add_argument("--no-ref", action="store_true", help="Skip reference audio generation")

    # Text library commands
    parser.add_argument("--list-texts", action="store_true", help="List built-in practice texts")
    parser.add_argument("--show-text", type=str, help="Show a specific text by ID")
    parser.add_argument("--category", type=str, help="Filter by category (speeches, prose, poetry, excerpts)")
    parser.add_argument("--difficulty", type=str, help="Filter by difficulty (beginner, intermediate, advanced)")

    # Cache commands
    parser.add_argument("--clear-cache", action="store_true", help="Clear all cached TTS and transcription data")
    parser.add_argument("--cache-stats", action="store_true", help="Show cache statistics")

    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    # Text library commands
    library = TextLibrary()

    if args.list_texts:
        if args.category or args.difficulty:
            entries = library.filter(category=args.category, difficulty=args.difficulty)
            print(f"\n# Filtered Texts ({len(entries)} found)\n")
            print("| ID | Title | Author | Difficulty | Words |")
            print("|----|-------|--------|------------|-------|")
            for e in entries:
                diff_emoji = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}.get(e.difficulty, "⚪")
                print(f"| `{e.text_id}` | {e.title} | {e.author} | {diff_emoji} {e.difficulty} | {e.word_count} |")
            print()
        else:
            print(library.format_catalog())
        return

    if args.show_text:
        output = library.format_entry(args.show_text)
        if output:
            print(output)
        else:
            print(f"Text not found: {args.show_text}")
            print(f"Use --list-texts to see available texts.")
        return

    if args.summary:
        session = OralPracticeSession(args.config)
        session.show_summary()
        return

    # Cache commands
    if args.clear_cache:
        cache = CacheManager("./data/cache")
        stats_before = cache.stats()
        cache.clear()
        print("Cache cleared.")
        print(f"  Removed: {stats_before['tts_count']} TTS files ({stats_before['tts_size_mb']} MB)")
        print(f"  Removed: {stats_before['transcription_count']} transcriptions ({stats_before['transcription_size_mb']} MB)")
        return

    if args.cache_stats:
        cache = CacheManager("./data/cache")
        stats = cache.stats()
        print("\n# Cache Statistics\n")
        print(f"TTS audio files: {stats['tts_count']} ({stats['tts_size_mb']} MB)")
        print(f"Transcriptions:  {stats['transcription_count']} ({stats['transcription_size_mb']} MB)")
        print(f"Total:           {stats['total_size_mb']} MB")
        print()
        return

    # Resolve text: either from --text, or from --text-id in library
    text = args.text
    text_title = args.title
    text_category = "custom"
    difficulty = "intermediate"

    if not text and args.text_id != "custom":
        entry = library.get_by_id(args.text_id)
        if entry:
            text = entry.content_clean
            text_title = entry.title
            text_category = entry.category
            difficulty = entry.difficulty
            print(f"Loaded text from library: {entry.display_name}")
            print(f"Difficulty: {entry.difficulty} | Words: {entry.word_count}")
            print()
        else:
            print(f"Error: Text ID '{args.text_id}' not found in library.")
            print("Use --list-texts to see available texts.")
            return

    if not text or not args.audio:
        print("Error: --text and --audio are required (or use --text-id, --demo, --list-texts)")
        parser.print_help()
        return

    if not os.path.exists(args.audio):
        print(f"Error: Audio file not found: {args.audio}")
        return

    # Run session
    session = OralPracticeSession(args.config)
    await session.run_session(
        text=text,
        user_audio_path=args.audio,
        text_id=args.text_id,
        text_title=text_title,
        text_category=text_category,
        difficulty=difficulty,
        generate_reference=not args.no_ref,
    )


if __name__ == "__main__":
    asyncio.run(main())
