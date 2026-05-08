"""Tests for configuration loading."""

import pytest
from config_loader import load_config, deep_merge, DEFAULT_CONFIG


class TestLoadConfig:
    """Tests for load_config function."""

    def test_default_config_has_required_sections(self):
        """Default config must contain all required top-level keys."""
        config = DEFAULT_CONFIG
        assert "scoring" in config
        assert "tts" in config
        assert "whisper" in config
        assert "paths" in config

    def test_default_weights_sum_to_one(self):
        """Default scoring weights must sum to 1.0."""
        weights = DEFAULT_CONFIG["scoring"]["weights"]
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01

    def test_deep_merge_overrides_top_level(self):
        """deep_merge should override top-level values."""
        base = {"a": 1, "b": 2}
        override = {"b": 99}
        result = deep_merge(base, override)
        assert result["a"] == 1
        assert result["b"] == 99

    def test_deep_merge_merges_nested_dicts(self):
        """deep_merge should recursively merge nested dicts."""
        base = {"scoring": {"weights": {"accuracy": 0.3, "fluency": 0.25}}}
        override = {"scoring": {"weights": {"accuracy": 0.5}}}
        result = deep_merge(base, override)
        assert result["scoring"]["weights"]["accuracy"] == 0.5
        assert result["scoring"]["weights"]["fluency"] == 0.25

    def test_deep_merge_preserves_untouched_branches(self):
        """deep_merge should not modify branches not in override."""
        base = {"a": {"x": 1}, "b": {"y": 2}}
        override = {"a": {"x": 99}}
        result = deep_merge(base, override)
        assert result["b"]["y"] == 2


class TestWeightNormalization:
    """Tests for weight normalization in load_config."""

    def test_weights_are_normalized_if_not_summing_to_one(self, monkeypatch, tmp_path):
        """If weights don't sum to 1.0, they should be normalized."""
        # Create a temp config with weights summing to 2.0
        config_content = """
scoring:
  weights:
    accuracy: 0.60
    fluency: 0.50
    rhythm: 0.50
    clarity: 0.30
    completeness: 0.10
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)

        config = load_config(str(config_file))
        weights = config["scoring"]["weights"]
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01
        assert abs(weights["accuracy"] - 0.30) < 0.01


class TestThresholds:
    """Tests for scoring thresholds."""

    def test_wer_thresholds_are_ordered(self):
        """WER thresholds must be in ascending order."""
        t = DEFAULT_CONFIG["scoring"]["thresholds"]
        assert t["wer_excellent"] < t["wer_good"]
        assert t["wer_good"] < t["wer_fair"]
        assert t["wer_fair"] < t["wer_poor"]

    def test_wpm_tolerance_is_positive(self):
        """WPM tolerance must be positive."""
        t = DEFAULT_CONFIG["scoring"]["thresholds"]
        assert t["wpm_tolerance"] > 0

    def test_duration_diff_thresholds_are_ordered(self):
        """Duration diff thresholds must be in ascending order."""
        t = DEFAULT_CONFIG["scoring"]["thresholds"]
        assert t["duration_diff_excellent"] < t["duration_diff_good"]
        assert t["duration_diff_good"] < t["duration_diff_fair"]
