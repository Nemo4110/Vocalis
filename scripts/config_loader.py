"""
Configuration loader - reads YAML config with defaults.
"""

import os
from pathlib import Path
from typing import Dict, Any


DEFAULT_CONFIG = {
    "scoring": {
        "weights": {
            "accuracy": 0.30,
            "fluency": 0.25,
            "rhythm": 0.25,
            "clarity": 0.15,
            "completeness": 0.05,
        },
        "thresholds": {
            "wer_excellent": 0.05,
            "wer_good": 0.15,
            "wer_fair": 0.30,
            "wer_poor": 0.50,
            "wpm_ideal": 150,
            "wpm_tolerance": 30,
            "duration_diff_excellent": 0.10,
            "duration_diff_good": 0.25,
            "duration_diff_fair": 0.50,
            "pause_expected_between_sentences": 0.8,
            "pause_expected_between_clauses": 0.4,
            "pause_max_acceptable_in_sentence": 1.5,
            "clarity_excellent": -0.3,
            "clarity_good": -0.5,
            "clarity_fair": -0.8,
        },
    },
    "tts": {
        "provider": "edge_tts",
        "edge_tts": {
            "voice": "en-US-AvaNeural",
            "rate": "-10%",
            "volume": "+0%",
            "pitch": "+0Hz",
        },
        "openai": {
            "model": "tts-1",
            "voice": "alloy",
            "speed": 1.0,
        },
        "system": {
            "engine": "sapi5",
            "rate": 150,
        },
    },
    "whisper": {
        "model": "whisper-1",
        "language": "en",
        "response_format": "verbose_json",
        "timestamp_granularities": ["word", "segment"],
    },
    "paths": {
        "data_dir": "./data",
        "reports_dir": "./reports",
        "assets_dir": "./assets",
        "history_file": "./data/history.json",
    },
}


def load_config(config_path: str = "./config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file with fallback to defaults.

    Args:
        config_path: Path to YAML config file.

    Returns:
        Merged configuration dict (file overrides defaults).
    """
    config = deep_copy(DEFAULT_CONFIG)

    path = Path(config_path)
    if path.exists():
        try:
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f)
            if user_config:
                config = deep_merge(config, user_config)
        except ImportError:
            print("Warning: PyYAML not installed. Using default config.")
            print("Install with: pip install pyyaml")
        except Exception as e:
            print(f"Warning: Could not load config file: {e}. Using defaults.")

    # Validate weights sum to 1.0
    weights = config.get("scoring", {}).get("weights", {})
    total = sum(weights.values())
    if abs(total - 1.0) > 0.01:
        print(f"Warning: Scoring weights sum to {total:.2f}, normalizing to 1.0")
        for key in weights:
            weights[key] = weights[key] / total

    return config


def deep_copy(obj: Any) -> Any:
    """Deep copy a nested dict/list structure."""
    import copy
    return copy.deepcopy(obj)


def deep_merge(base: Dict, override: Dict) -> Dict:
    """Recursively merge override into base.

    Values in override take precedence. Nested dicts are merged
    rather than replaced.
    """
    result = deep_copy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deep_copy(value)
    return result
