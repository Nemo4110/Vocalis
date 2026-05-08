"""
Generate mock history data for testing progress charts.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path


def generate_mock_history(
    num_sessions: int = 30,
    output_path: str = "./data/history.json",
    seed: int = 42,
):
    """Generate realistic mock practice history.

    Scores start low and gradually improve with some variance.
    """
    random.seed(seed)

    sample_texts = [
        ("gettysburg", "Gettysburg Address", "classic_speeches", "advanced"),
        ("fox_dog", "The Quick Brown Fox", "tongue_twisters", "beginner"),
        ("hamlet", "Hamlet Soliloquy", "classic_literature", "advanced"),
        ("daily_1", "Morning Routine", "daily_conversation", "beginner"),
        ("news_1", "Tech News Summary", "news", "intermediate"),
    ]

    sessions = []
    base_date = datetime.now() - timedelta(days=num_sessions)

    for i in range(1, num_sessions + 1):
        # Gradual improvement with noise
        progress = i / num_sessions  # 0.0 to 1.0
        base_score = 50 + progress * 35  # 50 to 85
        noise = random.gauss(0, 5)
        overall = max(0, min(100, base_score + noise))

        # Dimensions correlated with overall
        accuracy = max(0, min(100, overall + random.gauss(0, 8)))
        fluency = max(0, min(100, overall + random.gauss(-5, 10)))
        rhythm = max(0, min(100, overall * 0.9 + random.gauss(0, 12)))
        clarity = max(0, min(100, overall + random.gauss(3, 7)))
        completeness = max(0, min(100, 85 + progress * 15 + random.gauss(0, 5)))

        text_id, title, category, difficulty = random.choice(sample_texts)

        # Generate word details
        word_count = random.randint(20, 80)
        word_details = []
        for w in range(word_count):
            statuses = ["ok"] * 8 + ["missing"] * 1 + ["wrong"] * 1
            word_details.append({
                "word": f"word_{w}",
                "user_word": f"word_{w}",
                "status": random.choice(statuses),
                "duration_diff_pct": random.gauss(0, 0.3) if random.random() > 0.2 else None,
            })

        session = {
            "session_id": i,
            "timestamp": (base_date + timedelta(days=i)).isoformat(),
            "text_id": text_id,
            "text_title": title,
            "text_category": category,
            "difficulty": difficulty,
            "reference_text": f"Sample text content for {title}",
            "overall": round(overall, 1),
            "accuracy": round(accuracy, 1),
            "fluency": round(fluency, 1),
            "rhythm": round(rhythm, 1),
            "clarity": round(clarity, 1),
            "completeness": round(completeness, 1),
            "wer": round(random.uniform(0.05, 0.25), 3),
            "wpm": round(random.gauss(140, 20), 1),
            "pause_count": random.randint(0, 8),
            "avg_pause_duration": round(random.uniform(0.3, 1.2), 2),
            "rhythm_similarity": round(random.uniform(0.5, 0.9), 3),
            "word_count": word_count,
            "duration_seconds": round(random.uniform(20, 60), 1),
            "avg_logprob": round(random.uniform(-0.8, -0.2), 3),
            "word_details": word_details,
            "notes": "",
        }
        sessions.append(session)

    data = {
        "total_sessions": num_sessions,
        "last_updated": datetime.now().isoformat(),
        "sessions": sessions,
        "personal_bests": {},
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Generated {num_sessions} mock sessions in {output_path}")


if __name__ == "__main__":
    generate_mock_history(50)
