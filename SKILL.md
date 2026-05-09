---
name: vocalis-oral-practice
description: Multi-dimensional oral English scoring skill for AI agents. Transcribes user speech, scores across 5 dimensions (accuracy, fluency, rhythm, clarity, completeness), generates reports, and tracks progress over time.
triggers:
  - "练习口语"
  - "oral practice"
  - "口语评分"
  - "speaking practice"
  - "朗读评分"
  - "pronunciation"
  - "英语口语"
  - "跟读练习"
---

# Vocalis Oral Practice Skill

## Purpose

Enable AI agents to guide users through structured oral English practice sessions with quantitative feedback and progress tracking.

## Capabilities

### 1. Practice Session (`run_session`)

Orchestrate a complete practice workflow:

```
Input:  reference_text + user_audio_file
Output: scoring_result + markdown_report + progress_charts
```

Steps:
1. Generate reference TTS audio (if configured)
2. Transcribe user audio via Whisper (word-level timestamps)
3. Score across 5 dimensions
4. Save to history
5. Generate report + charts

### 2. Scoring Engine (`ScoringEngine.score`)

| Dimension | Weight | Metric |
|-----------|--------|--------|
| Accuracy | 30% | WER (Word Error Rate) |
| Fluency | 25% | WPM + pause patterns |
| Rhythm | 25% | Word duration vs reference |
| Clarity | 15% | Whisper confidence (avg_logprob) |
| Completeness | 5% | Missing word ratio |

### 3. Progress Tracking (`HistoryManager`)

- Persist session records to JSON
- Personal bests per text
- Weak word detection (words with highest error rates)
- Statistics: total sessions, average score, improvement trend

### 4. Visualization (`ProgressPlotter`)

- **Evolution chart**: All sessions as dots, personal bests connected by step line
- **Dimension trends**: 5-subplot time series with moving average
- **Radar chart**: Single session 5-dimension profile
- **Text comparison**: Progress on a specific text across attempts

## Agent Integration Interface

### Python API

```python
from main import OralPracticeSession

session = OralPracticeSession(config_path="./config.yaml")
result = await session.run_session(
    text="The quick brown fox jumps over the lazy dog.",
    user_audio_path="./recordings/user.wav",
    text_id="pangram_001",
    text_title="Pangram Practice",
    difficulty="intermediate",
)
# result["result"].overall -> 93.2
# result["report"] -> markdown report text
# result["report_path"] -> path to saved report
```

### CLI

```bash
# Full session
uv run python scripts/main.py --text "..." --audio path/to/audio.wav

# Demo mode (no API calls)
uv run python scripts/main.py --demo

# View summary
uv run python scripts/main.py --summary
```

## Configuration (`config.yaml`)

Key sections:
- `scoring.weights` — Dimension weights (must sum to 1.0)
- `scoring.thresholds` — WER/WPM/pause/clarity thresholds
- `tts` — TTS provider config (edge_tts / openai / system)
- `whisper` — Whisper model and language settings
- `paths` — Data/reports/assets directories

## Requirements

- Python 3.10+
- OpenAI API key (for Whisper transcription)
- uv for environment management

## Dependencies

See `pyproject.toml`. Key packages:
- `openai` — Whisper API
- `edge-tts` — Free reference audio generation
- `matplotlib` + `numpy` — Visualization
- `pyyaml` — Config loading

## Output Artifacts

| Artifact | Location | Description |
|----------|----------|-------------|
| Report | `./reports/report_{NNN}.md` | Markdown practice report |
| Evolution chart | `./reports/progress_evolution.png` | Overall progress over time |
| Dimension trends | `./reports/dimension_trends.png` | Per-dimension time series |
| Radar chart | `./reports/radar_{NNN}.png` | Session score profile |
| History | `./data/history.json` | All session records |

## Agent Usage Patterns

### Pattern A: Guided Practice Loop

1. Agent presents practice text to user
2. User records audio → agent saves to file
3. Agent calls `run_session(text, audio_path)`
4. Agent reads back scores and recommendations to user
5. Agent offers to repeat or try new text

### Pattern B: Progress Check-in

1. Agent calls `show_summary()`
2. Agent reports: total sessions, average score, weak words
3. Agent suggests practice text targeting weak areas

### Pattern C: Comparison Mode

1. Agent runs session with reference audio generation enabled
2. Agent plays reference TTS for user to hear standard pronunciation
3. User records their version
4. Agent scores and highlights rhythm differences vs reference
