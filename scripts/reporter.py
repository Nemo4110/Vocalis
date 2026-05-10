"""
Practice report generator - creates human-readable text reports.
"""

from typing import List, Optional
from scorer import ScoringResult, WordAlignment


class ReportGenerator:
    """Generate formatted practice reports."""

    @staticmethod
    def generate(
        result: ScoringResult,
        reference_text: str,
        text_title: str = "Practice Text",
        previous_best: Optional[float] = None,
    ) -> str:
        """Generate a full practice report as markdown text.

        The report uses HTML comment anchors to enable machine parsing
        while remaining fully human-readable.
        """
        lines = []

        # Machine-parseable metadata header
        lines.append("<!-- vocalis:meta:start -->")
        lines.append(f"<!-- vocalis:overall_score={result.overall:.1f} -->")
        lines.append(f"<!-- vocalis:accuracy={result.accuracy:.1f} -->")
        lines.append(f"<!-- vocalis:fluency={result.fluency:.1f} -->")
        lines.append(f"<!-- vocalis:rhythm={result.rhythm:.1f} -->")
        lines.append(f"<!-- vocalis:clarity={result.clarity:.1f} -->")
        lines.append(f"<!-- vocalis:completeness={result.completeness:.1f} -->")
        lines.append(f"<!-- vocalis:wer={result.wer:.3f} -->")
        lines.append(f"<!-- vocalis:wpm={result.wpm:.1f} -->")
        lines.append(f"<!-- vocalis:word_count={result.word_count} -->")
        lines.append(f"<!-- vocalis:missing_words={result.missing_words} -->")
        lines.append(f"<!-- vocalis:extra_words={result.extra_words} -->")
        lines.append(f"<!-- vocalis:pause_count={result.pause_count} -->")
        lines.append("<!-- vocalis:meta:end -->")
        lines.append("")

        # Header
        lines.append(f"#  Speaking Practice Report: {text_title}")
        lines.append("")

        # Overall score
        lines.append("<!-- vocalis:section=overall -->")
        score_emoji = ReportGenerator._score_emoji(result.overall)
        lines.append(f"## Overall Score: {result.overall:.1f}/100 {score_emoji}")
        if previous_best is not None:
            delta = result.overall - previous_best
            if delta > 0:
                lines.append(f"**↑ Improvement: +{delta:.1f} points** (previous best: {previous_best:.1f})")
            elif delta < 0:
                lines.append(f"**↓ {abs(delta):.1f} points below your best** ({previous_best:.1f})")
            else:
                lines.append(f"**→ Tied with your personal best!**")
        lines.append("")

        # Dimension scores
        lines.append("<!-- vocalis:section=dimensions -->")
        lines.append("## Dimension Breakdown")
        lines.append("")
        lines.append("| Dimension | Score | Rating |")
        lines.append("|-----------|-------|--------|")
        dims = [
            ("Accuracy", result.accuracy),
            ("Fluency", result.fluency),
            ("Rhythm", result.rhythm),
            ("Clarity", result.clarity),
            ("Completeness", result.completeness),
        ]
        for name, score in dims:
            rating = ReportGenerator._rating_text(score)
            bar = ReportGenerator._score_bar(score)
            lines.append(f"| {name:<12} | {score:5.1f} | {rating} {bar} |")
        lines.append("")

        # Key metrics
        lines.append("<!-- vocalis:section=metrics -->")
        lines.append("## Key Metrics")
        lines.append("")
        lines.append(f"- **Word Error Rate (WER):** {result.wer*100:.1f}% ({result.missing_words} missing, {result.extra_words} extra)")
        lines.append(f"- **Speaking Speed:** {result.wpm:.0f} WPM (words per minute)")
        lines.append(f"- **Pauses Detected:** {result.pause_count} (avg duration: {result.avg_pause_duration:.1f}s)")
        lines.append(f"- **Words:** {result.word_count}")
        lines.append(f"- **Whisper Confidence:** {result.avg_logprob:.2f}")
        lines.append("")

        # Word-level analysis
        lines.append("<!-- vocalis:section=words -->")
        lines.append("## Word-Level Analysis")
        lines.append("")
        lines.append(ReportGenerator._word_table(result.word_alignments))
        lines.append("")

        # Pause analysis
        if result.pauses:
            lines.append("<!-- vocalis:section=pauses -->")
            lines.append("## Pause Analysis")
            lines.append("")
            lines.append("| # | After Word | Duration | Assessment |")
            lines.append("|---|-----------|----------|------------|")

            # Map pauses to words
            word_list = [a for a in result.word_alignments if a.user_end is not None]
            for i, (start, end, duration) in enumerate(result.pauses[:10], 1):
                # Find which word precedes this pause
                preceding = "(unknown)"
                for j, w in enumerate(word_list):
                    if abs(w.user_end - start) < 0.2:
                        preceding = w.user_word or w.ref_word
                        break

                assessment = "Normal" if duration < 0.8 else "Long" if duration < 1.5 else "Very long"
                lines.append(f"| {i} | {preceding} | {duration:.1f}s | {assessment} |")
            lines.append("")

        # Recommendations
        lines.append("<!-- vocalis:section=recommendations -->")
        lines.append("## Recommendations")
        lines.append("")
        lines.extend(ReportGenerator._recommendations(result))
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _score_emoji(score: float) -> str:
        if score >= 90:
            return "[A+]"
        elif score >= 80:
            return "[A]"
        elif score >= 70:
            return "[B]"
        elif score >= 60:
            return "[C]"
        else:
            return "[D]"

    @staticmethod
    def _rating_text(score: float) -> str:
        if score >= 90:
            return "Excellent"
        elif score >= 80:
            return "Good"
        elif score >= 70:
            return "Fair"
        elif score >= 60:
            return "Developing"
        else:
            return "Needs Work"

    @staticmethod
    def _score_bar(score: float, width: int = 15) -> str:
        filled = int(score / 100 * width)
        return "#" * filled + "-" * (width - filled)

    @staticmethod
    def _word_table(alignments: List[WordAlignment], max_rows: int = 50) -> str:
        """Generate a markdown table of word-level results."""
        lines = []
        lines.append("| # | Reference | You Said | Status | Duration Diff |")
        lines.append("|---|-----------|----------|--------|---------------|")

        for i, a in enumerate(alignments[:max_rows], 1):
            ref = a.ref_word or "(extra)"
            user = a.user_word or "-"

            if a.status == "ok":
                status = "OK"
                diff = f"{a.duration_diff_pct*100:+.0f}%" if a.duration_diff_pct is not None else "-"
            elif a.status == "missing":
                status = "MISS"
                diff = "-"
            elif a.status == "extra":
                status = "EXTRA"
                diff = "-"
            elif a.status == "wrong":
                status = "WRONG"
                diff = f"{a.duration_diff_pct*100:+.0f}%" if a.duration_diff_pct is not None else "-"
            else:
                status = "?"
                diff = "-"

            # Truncate long words
            ref = ref[:20]
            user = user[:20]

            lines.append(f"| {i} | {ref} | {user} | {status} | {diff} |")

        if len(alignments) > max_rows:
            lines.append(f"| ... | ({len(alignments) - max_rows} more words) | | | |")

        return "\n".join(lines)

    @staticmethod
    def _recommendations(result: ScoringResult) -> List[str]:
        """Generate personalized recommendations."""
        recs = []

        # Accuracy recommendations
        if result.accuracy < 70:
            if result.wer > 0.3:
                recs.append("[Accuracy] Many words were missed or misread. Try reading more slowly and focus on each word.")
            else:
                recs.append("[Accuracy] Some words were incorrect. Review the word-level table above to identify trouble spots.")
        elif result.accuracy < 85:
            recs.append("[Accuracy] Good! A few errors remain. Check the marked words above and practice those specifically.")

        # Fluency recommendations
        if result.fluency < 70:
            if result.wpm < 100:
                recs.append("[Fluency] Your pace is quite slow. Try to read more continuously without long hesitations.")
            elif result.wpm > 200:
                recs.append("[Fluency] You're speaking very fast! Slow down a bit for better clarity and rhythm.")
            elif result.pause_count > 5:
                recs.append(f"[Fluency] You had {result.pause_count} pauses. Try to read more smoothly with fewer mid-sentence breaks.")
        elif result.fluency < 85:
            recs.append("[Fluency] Decent pace. Work on reducing unnecessary pauses within sentences.")

        # Rhythm recommendations
        if result.rhythm < 70:
            recs.append("[Rhythm] Your word timing differs significantly from the reference. Listen to the standard audio and try to match its rhythm more closely.")
        elif result.rhythm < 85:
            recs.append("[Rhythm] Getting there! Some words were held too long or too short. Focus on the words marked with large duration differences.")

        # Clarity recommendations
        if result.clarity < 70:
            recs.append("[Clarity] Pronunciation was unclear in places. Speak closer to the microphone and enunciate each word clearly.")
        elif result.clarity < 85:
            recs.append("[Clarity] Generally clear. Pay attention to words with low confidence scores in the table above.")

        # Completeness
        if result.completeness < 90:
            recs.append(f"[Completeness] You skipped {result.missing_words} word(s). Try to read the entire text without skipping.")

        if not recs:
            recs.append("[Great work!] All dimensions scored well. Keep practicing to maintain this level!")

        return [f"{i+1}. {r}" for i, r in enumerate(recs)]

    @staticmethod
    def generate_summary(
        history_stats: dict,
        weak_words: List[tuple],
    ) -> str:
        """Generate a summary report of all practice history."""
        lines = []
        lines.append("#  Practice Summary")
        lines.append("")
        lines.append(f"**Total Sessions:** {history_stats.get('total_sessions', 0)}")
        lines.append(f"**Average Score:** {history_stats.get('average_score', 0):.1f}")
        lines.append(f"**Best Score:** {history_stats.get('best_score', 0):.1f}")
        lines.append(f"**Unique Texts Practiced:** {history_stats.get('unique_texts', 0)}")
        lines.append(f"**Total Practice Time:** {history_stats.get('total_practice_minutes', 0):.0f} minutes")
        lines.append("")

        if weak_words:
            lines.append("## Words to Practice More")
            lines.append("")
            lines.append("| Word | Errors | Total | Error Rate |")
            lines.append("|------|--------|-------|------------|")
            for word, errors, total, rate in weak_words[:15]:
                lines.append(f"| {word} | {errors} | {total} | {rate*100:.0f}% |")
            lines.append("")

        return "\n".join(lines)
