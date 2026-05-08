"""
Progress visualization - generate evolution charts like Karpathy's autoresearch.
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class ProgressPlotter:
    """Generate progress visualization charts."""

    COLORS = {
        "kept": "#2ecc71",       # Green for personal bests
        "discarded": "#bdc3c7",  # Gray for other sessions
        "line": "#27ae60",       # Green line
        "accuracy": "#3498db",   # Blue
        "fluency": "#e74c3c",    # Red
        "rhythm": "#9b59b6",     # Purple
        "clarity": "#f39c12",    # Orange
        "completeness": "#1abc9c", # Teal
    }

    @staticmethod
    def plot_main_evolution(
        session_ids: List[int],
        timestamps: List[str],
        overall_scores: List[float],
        output_path: str = "./reports/progress_evolution.png",
        title: str = "Speaking Practice Progress",
        figsize: Tuple[int, int] = (14, 7),
    ) -> str:
        """Generate main evolution chart (autoresearch style).

        Shows all sessions as gray dots, personal bests as green dots
        connected by a step line.
        """
        fig, ax = plt.subplots(figsize=figsize)

        # Parse timestamps
        dates = [datetime.fromisoformat(ts) for ts in timestamps]

        # All sessions as light gray dots
        ax.scatter(
            session_ids, overall_scores,
            c=ProgressPlotter.COLORS["discarded"],
            s=25, alpha=0.5, zorder=2,
            label="All sessions",
        )

        # Compute running best (personal records)
        best_scores = []
        best_ids = []
        best_dates = []
        running_best = -1

        for sid, score, date in zip(session_ids, overall_scores, dates):
            if score > running_best:
                running_best = score
                best_scores.append(score)
                best_ids.append(sid)
                best_dates.append(date)

        # Green dots for personal bests
        ax.scatter(
            best_ids, best_scores,
            c=ProgressPlotter.COLORS["kept"],
            s=80, edgecolors="black", linewidths=0.8,
            zorder=5, label="Personal best",
        )

        # Step line connecting personal bests
        ax.step(
            best_ids, best_scores,
            where="post",
            c=ProgressPlotter.COLORS["line"],
            linewidth=2, alpha=0.8, zorder=4,
        )

        # Annotate key milestones (first 80+, 90+)
        milestone_scores = {80: "80+", 90: "90+"}
        for milestone, label in milestone_scores.items():
            for sid, score in zip(best_ids, best_scores):
                if score >= milestone:
                    ax.annotate(
                        label,
                        (sid, score),
                        textcoords="offset points",
                        xytext=(0, 18),
                        ha="center",
                        fontsize=9,
                        color=ProgressPlotter.COLORS["line"],
                        fontweight="bold",
                    )
                    break  # Only annotate first occurrence

        # Styling
        ax.set_xlabel("Practice Session #", fontsize=12)
        ax.set_ylabel("Overall Score", fontsize=12)
        ax.set_title(
            f"{title}: {len(session_ids)} Sessions, {len(best_ids)} Personal Records",
            fontsize=14,
        )
        ax.set_ylim(0, 105)
        ax.grid(True, alpha=0.3, linestyle="-")
        ax.legend(loc="lower right", fontsize=10)

        # Add subtle background zones
        ax.axhspan(90, 100, alpha=0.05, color="green", label="Excellent zone")
        ax.axhspan(70, 90, alpha=0.03, color="yellow")
        ax.axhspan(0, 70, alpha=0.03, color="red")

        plt.tight_layout()

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()

        return output_path

    @staticmethod
    def plot_multi_dimension_trends(
        session_ids: List[int],
        timestamps: List[str],
        accuracy: List[float],
        fluency: List[float],
        rhythm: List[float],
        clarity: List[float],
        completeness: List[float],
        output_path: str = "./reports/dimension_trends.png",
        figsize: Tuple[int, int] = (14, 10),
    ) -> str:
        """Generate multi-subplot trend chart for each dimension."""
        fig, axes = plt.subplots(5, 1, figsize=figsize, sharex=True)
        fig.suptitle("Dimension Score Trends Over Time", fontsize=14, y=0.995)

        dimensions = [
            ("Accuracy", accuracy, ProgressPlotter.COLORS["accuracy"]),
            ("Fluency", fluency, ProgressPlotter.COLORS["fluency"]),
            ("Rhythm", rhythm, ProgressPlotter.COLORS["rhythm"]),
            ("Clarity", clarity, ProgressPlotter.COLORS["clarity"]),
            ("Completeness", completeness, ProgressPlotter.COLORS["completeness"]),
        ]

        for ax, (name, scores, color) in zip(axes, dimensions):
            ax.plot(session_ids, scores, color=color, linewidth=1.5, alpha=0.8)
            ax.scatter(session_ids, scores, c=color, s=20, alpha=0.6, zorder=3)

            # Running average (moving window)
            if len(scores) >= 3:
                window = min(5, len(scores) // 2 + 1)
                smoothed = ProgressPlotter._moving_average(scores, window)
                ax.plot(
                    session_ids[window-1:], smoothed,
                    color="black", linewidth=1, alpha=0.3, linestyle="--",
                    label=f"{window}-session avg",
                )

            ax.set_ylabel(name, fontsize=10, color=color, fontweight="bold")
            ax.set_ylim(0, 105)
            ax.grid(True, alpha=0.2)
            ax.tick_params(axis="y", labelcolor=color)

        axes[-1].set_xlabel("Practice Session #", fontsize=12)
        plt.tight_layout()

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()

        return output_path

    @staticmethod
    def plot_radar_chart(
        scores: Dict[str, float],
        output_path: str = "./reports/radar_chart.png",
        figsize: Tuple[int, int] = (8, 8),
        previous_scores: Optional[Dict[str, float]] = None,
    ) -> str:
        """Generate radar chart for a single session's dimension scores."""
        import numpy as np

        categories = ["Accuracy", "Fluency", "Rhythm", "Clarity", "Completeness"]
        values = [
            scores.get("accuracy", 0),
            scores.get("fluency", 0),
            scores.get("rhythm", 0),
            scores.get("clarity", 0),
            scores.get("completeness", 0),
        ]

        # Close the polygon
        N = len(categories)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        values += values[:1]
        angles += angles[:1]

        fig, ax = plt.subplots(figsize=figsize, subplot_kw=dict(polar=True))

        # Current session
        ax.plot(angles, values, "o-", linewidth=2, color=ProgressPlotter.COLORS["line"])
        ax.fill(angles, values, alpha=0.25, color=ProgressPlotter.COLORS["line"])

        # Previous session (if provided)
        if previous_scores:
            prev_values = [
                previous_scores.get("accuracy", 0),
                previous_scores.get("fluency", 0),
                previous_scores.get("rhythm", 0),
                previous_scores.get("clarity", 0),
                previous_scores.get("completeness", 0),
            ]
            prev_values += prev_values[:1]
            ax.plot(angles, prev_values, "o-", linewidth=1.5, color="gray", alpha=0.5)
            ax.fill(angles, prev_values, alpha=0.1, color="gray")
            ax.legend(["Current", "Previous"], loc="upper right", bbox_to_anchor=(1.3, 1.1))

        # Labels
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=11)
        ax.set_ylim(0, 100)
        ax.set_title("Session Score Profile", fontsize=14, pad=20)

        plt.tight_layout()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()

        return output_path

    @staticmethod
    def plot_text_comparison(
        session_ids: List[int],
        scores: List[float],
        text_title: str,
        output_path: str = "./reports/text_comparison.png",
        figsize: Tuple[int, int] = (10, 5),
    ) -> str:
        """Plot progress on a specific text over multiple attempts."""
        fig, ax = plt.subplots(figsize=figsize)

        ax.plot(session_ids, scores, "o-", linewidth=2, markersize=8,
                color=ProgressPlotter.COLORS["accuracy"])

        # Highlight personal best
        best_idx = scores.index(max(scores))
        ax.scatter(
            session_ids[best_idx], scores[best_idx],
            s=200, c=ProgressPlotter.COLORS["kept"],
            edgecolors="black", linewidths=1.5, zorder=5,
            marker="*",
        )
        ax.annotate(
            f"Best: {scores[best_idx]:.1f}",
            (session_ids[best_idx], scores[best_idx]),
            textcoords="offset points",
            xytext=(0, 15),
            ha="center",
            fontsize=10,
            fontweight="bold",
        )

        ax.set_xlabel("Attempt #", fontsize=11)
        ax.set_ylabel("Score", fontsize=11)
        ax.set_title(f'Progress on "{text_title}"', fontsize=13)
        ax.set_ylim(0, 105)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()

        return output_path

    @staticmethod
    def _moving_average(data: List[float], window: int) -> List[float]:
        """Compute simple moving average."""
        result = []
        for i in range(len(data) - window + 1):
            result.append(sum(data[i:i+window]) / window)
        return result
