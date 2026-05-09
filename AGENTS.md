# Agent Integration Protocol — Vocalis

## Role

Vocalis is a **speech scoring skill** for AI agents. It does not replace the agent's conversational role — it provides structured scoring capabilities that the agent invokes on behalf of the user.

## Responsibilities

### Agent (Caller)

- Manage conversation flow with the user
- Present practice texts, collect audio recordings
- Invoke Vocalis via Python API or CLI
- Interpret and present results in natural language
- Encourage and guide based on scores

### Vocalis (Skill)

- Transcribe audio accurately
- Compute fair, consistent scores
- Generate human-readable reports
- Track history persistently
- Never interact directly with the user

## Invocation Rules

1. **Always use `uv run`** — Never call `python` directly. Environment is managed by uv.
2. **Check for `OPENAI_API_KEY`** before invoking — Whisper requires it. If missing, warn user.
3. **Save audio files** to `./data/` before passing paths to Vocalis.
4. **Use meaningful `text_id`** — Enables per-text progress tracking. Format: `{category}_{NNN}`.
5. **Handle demo mode gracefully** — If API unavailable, fall back to `--demo` for testing.

## Score Interpretation Guide

When presenting scores to users:

| Score | Emoji | Description |
|-------|-------|-------------|
| 90-100 | 🏆 | Excellent — near-native delivery |
| 80-89 | 🌟 | Good — minor issues |
| 70-79 | 👍 | Fair — noticeable room for improvement |
| 60-69 | 💪 | Developing — needs focused practice |
| <60 | 📚 | Needs Work — fundamentals to work on |

Always report the **overall score** first, then highlight the **weakest dimension** with specific advice.

## Conversation Patterns

### Starting a Session

```
Agent: "Ready to practice? I'll read a sentence, then you repeat it."
[Agent generates reference audio via Vocalis TTS]
Agent: [plays audio] "Now your turn — record yourself saying that."
[user records]
[Agent calls Vocalis.run_session()]
Agent: "Great effort! You scored 82/100. Your accuracy was strong, but rhythm
        was a bit off — you held 'jumps' too long. Want to try again?"
```

### Reviewing Progress

```
Agent: "You've practiced 12 times this week. Your average is up 5 points!
        Your weakest words are: 'thorough', 'rhythm', 'specifically'.
        Want to drill those?"
```

## Error Handling

| Error | Agent Response |
|-------|---------------|
| OpenAI API key missing | "I need an OpenAI API key to score your speech. Please set OPENAI_API_KEY." |
| Audio file not found | "I couldn't find your recording. Please record again." |
| Whisper transcription failed | "I had trouble understanding the audio. Try speaking closer to the mic." |
| TTS generation failed | "Reference audio unavailable, but I can still score your recording." |

## File Layout Convention

```
./data/
  history.json          # Auto-managed by Vocalis
  ref_{text_id}.mp3     # Reference audio (auto-generated)
  user_{timestamp}.wav  # User recordings (agent-managed)

./reports/
  report_{NNN}.md       # Per-session reports
  progress_evolution.png
  dimension_trends.png
  radar_{NNN}.png
  summary.md            # Overall summary
```

## Extending Vocalis

If the agent needs new capabilities:

1. Add scoring dimensions in `config.yaml`
2. Extend `ScoringEngine` in `scripts/scorer.py`
3. Update `ReportGenerator` in `scripts/reporter.py`
4. Update this file to document new agent patterns
