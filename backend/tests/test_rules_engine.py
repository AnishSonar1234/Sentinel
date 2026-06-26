"""
tests/test_rules_engine.py
───────────────────────────
Unit tests for hard-rule short-circuit and soft-rule scoring.
"""
import pytest
from ml_pipeline.features import TransactionFeatures
from app.services.rules_engine import RulesEngine


def make_features(**overrides) -> TransactionFeatures:
    """
    Build a baseline 'normal' feature set, then apply overrides.
    Baseline represents a perfectly typical transaction.
    """
    defaults = dict(
        amount=250.0,
        hour_of_day=14,
        location_hash=123,
        txn_count_1h=1,
        amount_to_avg_ratio=1.0,
        amount_deviation=0.5,
        location_is_new=0,
        time_anomaly=0,
        frequency_spike=0.8,
        raw_location="Mumbai",
        raw_amount=250.0,
        raw_hour=14,
        raw_txn_count=1,
    )
    defaults.update(overrides)
    return TransactionFeatures(**defaults)


engine = RulesEngine()


class TestHardRules:
    """Fix 4: hard block should short-circuit before ML."""

    def test_no_hard_block_for_normal(self):
        f = make_features()
        is_blocked, reason = engine.is_hard_block(f)
        assert not is_blocked
        assert reason == ""

    def test_hard_block_trifecta(self):
        """High amount + new location + unusual hour → instant BLOCK."""
        f = make_features(
            amount_to_avg_ratio=5.0,   # > 3x threshold
            location_is_new=1,
            time_anomaly=1,
        )
        is_blocked, reason = engine.is_hard_block(f)
        assert is_blocked
        assert "Hard block" in reason

    def test_hard_block_extreme_velocity(self):
        """More than 10 txns in 1 hour → instant BLOCK."""
        f = make_features(txn_count_1h=11)
        is_blocked, reason = engine.is_hard_block(f)
        assert is_blocked
        assert "velocity" in reason.lower()

    def test_no_hard_block_partial_trifecta(self):
        """Only 2/3 trifecta conditions → not a hard block."""
        f = make_features(amount_to_avg_ratio=5.0, location_is_new=1, time_anomaly=0)
        is_blocked, _ = engine.is_hard_block(f)
        assert not is_blocked


class TestSoftRules:

    def test_normal_transaction_low_score(self):
        f = make_features()
        result = engine.evaluate(f)
        assert result.score < 0.3
        assert not result.hard_block

    def test_high_amount_raises_score(self):
        f = make_features(amount_to_avg_ratio=6.0, amount_deviation=5.0)
        result = engine.evaluate(f)
        assert result.score > 0.3
        assert any("Amount" in r for r in result.reasons)

    def test_new_location_raises_score(self):
        f = make_features(location_is_new=1)
        result = engine.evaluate(f)
        assert result.score > 0.2
        assert any("location" in r.lower() for r in result.reasons)

    def test_unusual_hour_raises_score(self):
        f = make_features(time_anomaly=1, raw_hour=3)
        result = engine.evaluate(f)
        assert any("hour" in r.lower() or "Unusual" in r for r in result.reasons)

    def test_velocity_spike_reason(self):
        f = make_features(txn_count_1h=6, raw_txn_count=6)
        result = engine.evaluate(f)
        # Score should increase and velocity reason should appear
        assert any("Velocity" in r or "transactions" in r for r in result.reasons)

    def test_score_bounded_to_one(self):
        """Even with all signals maxed, score should not exceed 1.0."""
        f = make_features(
            amount_to_avg_ratio=50.0,
            amount_deviation=10.0,
            location_is_new=1,
            time_anomaly=1,
            frequency_spike=5.0,
            txn_count_1h=8,
        )
        result = engine.evaluate(f)
        assert result.score <= 1.0
