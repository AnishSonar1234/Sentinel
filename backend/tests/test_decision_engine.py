"""
tests/test_decision_engine.py
──────────────────────────────
Unit tests for score fusion and decision thresholds.
No DB or HTTP needed — pure function tests.
"""
import pytest
from app.services.decision_engine import fuse_scores, make_decision


class TestFuseScores:
    def test_mid_values(self):
        score = fuse_scores(rule_score=0.5, anomaly_score=0.5)
        assert score == 50.0

    def test_zero_scores(self):
        assert fuse_scores(0.0, 0.0) == 0.0

    def test_max_scores(self):
        assert fuse_scores(1.0, 1.0) == 100.0

    def test_weighting_rule_heavy(self):
        # 60% rule + 40% anomaly
        score = fuse_scores(rule_score=1.0, anomaly_score=0.0)
        assert score == 60.0

    def test_weighting_ml_heavy(self):
        score = fuse_scores(rule_score=0.0, anomaly_score=1.0)
        assert score == 40.0

    def test_output_clamped_to_100(self):
        # Shouldn't go above 100 in practice
        score = fuse_scores(1.0, 1.0)
        assert score <= 100.0

    def test_output_clamped_to_zero(self):
        score = fuse_scores(0.0, 0.0)
        assert score >= 0.0


class TestMakeDecision:
    """Boundary value tests for the three decision tiers."""

    def test_below_allow_threshold(self):
        assert make_decision(0.0) == "ALLOW"
        assert make_decision(39.9) == "ALLOW"

    def test_at_allow_threshold(self):
        assert make_decision(40.0) == "VERIFY"

    def test_mid_verify_range(self):
        assert make_decision(57.0) == "VERIFY"

    def test_just_below_block_threshold(self):
        assert make_decision(74.9) == "VERIFY"

    def test_at_block_threshold(self):
        assert make_decision(75.0) == "BLOCK"

    def test_above_block_threshold(self):
        assert make_decision(100.0) == "BLOCK"
        assert make_decision(99.9) == "BLOCK"
