"""
Test progress chart generation with mock history data.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from history import HistoryManager
from plot_progress import ProgressPlotter


def test_charts():
    history = HistoryManager("./data/history.json")
    progress = history.get_progress()

    print(f"Loaded {len(progress['session_ids'])} sessions")

    # Main evolution chart
    print("\nGenerating evolution chart...")
    path = ProgressPlotter.plot_main_evolution(
        progress["session_ids"],
        progress["timestamps"],
        progress["overall"],
        output_path="./reports/progress_evolution.png",
    )
    print(f"  Saved: {path}")

    # Dimension trends
    print("\nGenerating dimension trends...")
    path = ProgressPlotter.plot_multi_dimension_trends(
        progress["session_ids"],
        progress["timestamps"],
        progress["accuracy"],
        progress["fluency"],
        progress["rhythm"],
        progress["clarity"],
        progress["completeness"],
        output_path="./reports/dimension_trends.png",
    )
    print(f"  Saved: {path}")

    # Radar chart for latest session
    print("\nGenerating radar chart...")
    latest = history.get_all_sessions()[-1]
    path = ProgressPlotter.plot_radar_chart(
        {
            "accuracy": latest.accuracy,
            "fluency": latest.fluency,
            "rhythm": latest.rhythm,
            "clarity": latest.clarity,
            "completeness": latest.completeness,
        },
        output_path="./reports/radar_latest.png",
    )
    print(f"  Saved: {path}")

    # Text-specific progress
    print("\nGenerating text-specific progress charts...")
    for text_id in set(s.text_id for s in history.get_all_sessions()):
        text_progress = history.get_progress(text_id)
        if len(text_progress["session_ids"]) >= 2:
            session = history.get_sessions_for_text(text_id)[0]
            path = ProgressPlotter.plot_text_comparison(
                list(range(1, len(text_progress["session_ids"]) + 1)),
                text_progress["overall"],
                session.text_title,
                output_path=f"./reports/text_progress_{text_id}.png",
            )
            print(f"  {session.text_title}: {path}")

    print("\n✅ All charts generated successfully!")


if __name__ == "__main__":
    test_charts()
