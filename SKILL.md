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

### 4. Built-in Text Library (`TextLibrary`)

Curated practice texts organized by category and difficulty:

| Category | Description | Difficulty Levels |
|----------|-------------|-------------------|
| speeches | Classic speeches (Gettysburg Address, I Have a Dream, etc.) | beginner - advanced |
| prose | Literary prose (Thoreau, Fitzgerald, Melville, Austen) | beginner - advanced |
| poetry | Classic poems (Frost, Shakespeare, Shelley, Henley) | beginner - intermediate |
| excerpts | Book excerpts (Mockingbird, 1984, Alice in Wonderland, etc.) | beginner - intermediate |

### 5. Caching (`CacheManager`)

Transparent disk caching to avoid repeated API calls:
- **TTS cache**: Reference audio cached by `(text + voice_config)` hash
- **Transcription cache**: Whisper results cached by audio file content hash
- Cache auto-managed; clear with `--clear-cache`

### 6. Visualization (`ProgressPlotter`)

- **Evolution chart**: All sessions as dots, personal bests connected by step line
- **Dimension trends**: 5-subplot time series with moving average
- **Radar chart**: Single session 5-dimension profile
- **Text comparison**: Progress on a specific text across attempts

## Agent Integration Interface

### Python API

```python
from main import OralPracticeSession
from text_library import TextLibrary

session = OralPracticeSession(config_path="./config.yaml")

# Practice with built-in text
library = TextLibrary()
entry = library.get_by_id("gettysburg_address")
result = await session.run_session(
    text=entry.content_clean,
    user_audio_path="./recordings/user.wav",
    text_id=entry.text_id,
    text_title=entry.title,
    text_category=entry.category,
    difficulty=entry.difficulty,
)
# result["result"].overall -> 93.2
# result["report"] -> markdown report text (machine-parseable)
# result["report_path"] -> path to saved report

# Or practice with custom text
result = await session.run_session(
    text="Your custom text here",
    user_audio_path="./recordings/user.wav",
    text_id="custom_001",
    text_title="Custom Practice",
)
```

### CLI

```bash
# --- Practice with custom text ---
uv run python scripts/main.py --text "Your text" --audio path/to/audio.wav

# --- Practice with built-in library text ---
uv run python scripts/main.py --text-id gettysburg_address --audio path/to/audio.wav

# --- Library management ---
uv run python scripts/main.py --list-texts                    # Show all texts
uv run python scripts/main.py --list-texts --difficulty beginner  # Filter by difficulty
uv run python scripts/main.py --show-text sonnet_18           # Preview a text

# --- Cache management ---
uv run python scripts/main.py --cache-stats                   # Show cache usage
uv run python scripts/main.py --clear-cache                   # Clear all cached data

# --- Other commands ---
uv run python scripts/main.py --demo                          # Demo mode (no API)
uv run python scripts/main.py --summary                       # View practice summary
```

## Configuration (`config.yaml`)

Key sections:
- `scoring.weights` — Dimension weights (must sum to 1.0)
- `scoring.thresholds` — WER/WPM/pause/clarity thresholds
- `tts` — TTS provider config (edge_tts / openai / system)
- `whisper` — Whisper model and language settings
- `paths` — Data/reports/assets directories

## Project Structure

```
.
├── scripts/
│   ├── main.py              # Entry point & session orchestration
│   ├── transcriber.py       # Whisper API transcription
│   ├── tts_provider.py      # TTS abstraction (edge-tts / OpenAI / system)
│   ├── scorer.py            # Multi-dimensional scoring engine
│   ├── reporter.py          # Machine-parseable Markdown report generation
│   ├── history.py           # Session history persistence
│   ├── plot_progress.py     # Progress visualization (matplotlib)
│   ├── text_library.py      # Built-in practice text library loader
│   └── cache_manager.py     # TTS & transcription disk cache
├── assets/
│   └── texts/
│       └── library.yaml     # Curated practice texts
├── tests/                   # pytest test suite
├── config.yaml              # Scoring weights & thresholds
├── pyproject.toml           # uv dependency management
└── data/history.json        # Practice history (auto-created)
```

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

## Output Format: Machine-Parseable Markdown

Vocalis reports are pure Markdown with **HTML comment anchors** for machine parsing. No JSON output — the same file is readable by both humans and agents.

### Metadata Block (top of every report)

```markdown
<!-- vocalis:meta:start -->
<!-- vocalis:overall_score=82.3 -->
<!-- vocalis:accuracy=91.0 -->
<!-- vocalis:fluency=78.5 -->
<!-- vocalis:rhythm=74.2 -->
<!-- vocalis:clarity=88.0 -->
<!-- vocalis:completeness=95.0 -->
<!-- vocalis:wer=0.045 -->
<!-- vocalis:wpm=135.0 -->
<!-- vocalis:word_count=42 -->
<!-- vocalis:missing_words=2 -->
<!-- vocalis:extra_words=0 -->
<!-- vocalis:pause_count=3 -->
<!-- vocalis:meta:end -->
```

### Section Anchors

| Anchor | Section |
|--------|---------|
| `<!-- vocalis:section=overall -->` | Overall score + improvement delta |
| `<!-- vocalis:section=dimensions -->` | 5-dimension breakdown table |
| `<!-- vocalis:section=metrics -->` | Key metrics (WER, WPM, pauses) |
| `<!-- vocalis:section=words -->` | Word-level alignment table |
| `<!-- vocalis:section=pauses -->` | Pause analysis table |
| `<!-- vocalis:section=recommendations -->` | Personalized recommendations |

### Parsing Strategy for Agents

```python
import re

def parse_vocalis_report(report_text: str) -> dict:
    """Extract structured data from a Vocalis markdown report."""
    result = {}

    # Parse metadata
    meta_pattern = r'<!-- vocalis:(\w+)=(.+?) -->'
    for match in re.finditer(meta_pattern, report_text):
        key, value = match.groups()
        if key != 'meta':
            try:
                result[key] = float(value)
            except ValueError:
                result[key] = value

    # Extract sections by anchor
    sections = {}
    section_pattern = r'<!-- vocalis:section=(\w+) -->\n(.*?)(?=\n<!--|\Z)'
    for match in re.finditer(section_pattern, report_text, re.DOTALL):
        sections[match.group(1)] = match.group(2).strip()

    return {"scores": result, "sections": sections}
```

## Output Artifacts

| Artifact | Location | Description |
|----------|----------|-------------|
| Report | `./reports/report_{NNN}.md` | Markdown practice report (machine-parseable) |
| Evolution chart | `./reports/progress_evolution.png` | Overall progress over time |
| Dimension trends | `./reports/dimension_trends.png` | Per-dimension time series |
| Radar chart | `./reports/radar_{NNN}.png` | Session score profile |
| History | `./data/history.json` | All session records |
| TTS cache | `./data/cache/tts/` | Cached reference audio files |
| Transcription cache | `./data/cache/transcription/` | Cached Whisper results |

## Agent Usage Patterns

### Pattern A: Guided Practice with Built-in Library

```
Agent: "Want to practice a classic speech? Here are some options:"
[Agent calls --list-texts --difficulty intermediate]
Agent: "How about the Gettysburg Address? It's 272 words, intermediate difficulty."
User: "Sure!"
[Agent calls --show-text gettysburg_address to display the text]
Agent: "Read this aloud, then send me your recording."
[User sends audio]
[Agent calls --text-id gettysburg_address --audio user.wav]
[Agent parses report via HTML comment anchors]
Agent: "You scored 85.3! Your accuracy was excellent, but rhythm needs work --
        you held 'consecrated' too long. Want to try again?"
```

### Pattern B: Progress Check-in

```
Agent: "Let's check your progress."
[Agent calls --summary]
Agent: "You've practiced 12 times this week. Average score: 78.5.
        Your weakest words: 'thorough', 'rhythm', 'specifically'.
        Want to drill those?"
```

### Pattern C: Comparison Mode (with Reference Audio)

1. Agent runs session with reference audio generation enabled
2. Agent plays reference TTS for user to hear standard pronunciation
3. User records their version
4. Agent scores and highlights rhythm differences vs reference
5. Agent uses word-level duration diff data to pinpoint specific words

### Pattern D: Targeted Difficulty Progression

```
Agent: "You scored 92 on beginner texts. Ready for intermediate?"
[Agent calls --list-texts --difficulty intermediate]
Agent: "Try Ozymandias by Shelley. It's a poem with challenging vocabulary."
```
