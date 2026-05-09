# Vocalis

An AI-powered oral English practice tool that scores your spoken delivery across multiple dimensions and tracks progress over time.

## What It Does

Vocalis takes a reference text and your recorded audio, then:

1. **Transcribes** your speech using OpenAI Whisper (with word-level timestamps)
2. **Generates** a reference TTS audio for comparison (via edge-tts, OpenAI, or system TTS)
3. **Scores** your performance on 5 dimensions: accuracy, fluency, rhythm, clarity, completeness
4. **Reports** results as a detailed Markdown report with word-level analysis
5. **Tracks** your practice history and visualizes progress with charts

## Quick Start

This project uses [uv](https://docs.astral.sh/uv/) for environment management.

```bash
# Create virtual environment and install dependencies
uv venv
uv pip install -r requirements.txt

# Or use pyproject.toml (recommended)
uv sync

# Set your OpenAI API key
set OPENAI_API_KEY=your_key_here

# Run a demo (no API calls, uses mock data)
uv run python scripts/main.py --demo

# Practice with your own audio
uv run python scripts/main.py --text "The quick brown fox jumps over the lazy dog." --audio path/to/your_recording.wav

# View practice summary
uv run python scripts/main.py --summary
```

## Scoring Dimensions

| Dimension | Weight | Based On |
|-----------|--------|----------|
| Accuracy | 30% | Word Error Rate (WER) |
| Fluency | 25% | Speaking speed (WPM) and pause patterns |
| Rhythm | 25% | Word duration consistency vs reference audio |
| Clarity | 15% | Whisper confidence scores |
| Completeness | 5% | Missing words from reference text |

All thresholds and weights are configurable in `config.yaml`.

## Project Structure

```
.
├── scripts/
│   ├── main.py              # Entry point & session orchestration
│   ├── transcriber.py       # Whisper API transcription
│   ├── tts_provider.py      # TTS abstraction (edge-tts / OpenAI / system)
│   ├── scorer.py            # Multi-dimensional scoring engine
│   ├── reporter.py          # Markdown report generation
│   ├── history.py           # Session history persistence
│   └── plot_progress.py     # Progress visualization (matplotlib)
├── tests/                   # pytest test suite
├── config.yaml              # Scoring weights & thresholds
├── requirements.txt
└── data/history.json        # Practice history (auto-created)
```

## Requirements

- Python 3.10+
- OpenAI API key (for Whisper transcription; optional for TTS if using edge-tts)

## License

MIT
