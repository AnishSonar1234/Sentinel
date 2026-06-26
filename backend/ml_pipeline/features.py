"""
ml_pipeline/features.py
────────────────────────
TransactionFeatures dataclass — the unified feature vector
used by both the RulesEngine and the ML model.
"""
from dataclasses import dataclass


@dataclass
class TransactionFeatures:
    # ── ML features (numeric vector for Isolation Forest) ─────────────
    amount: float
    hour_of_day: int            # 0–23
    location_hash: int          # hash(location) % 1000
    txn_count_1h: int           # velocity: transactions in last 60 min
    amount_to_avg_ratio: float  # amount / effective_avg  (key signal)

    # ── Behavioral (for rules engine weighted scoring) ─────────────────
    amount_deviation: float     # |amount - avg| / std  (z-score)
    location_is_new: int        # 0 or 1
    time_anomaly: int           # 0 or 1 (outside active hours)
    frequency_spike: float      # txn_count_1h / baseline_hourly_rate

    # ── Raw values (for explainability reason codes) ───────────────────
    raw_location: str
    raw_amount: float
    raw_hour: int
    raw_txn_count: int

    def to_ml_vector(self) -> list:
        """5-feature vector consumed by the Isolation Forest predictor."""
        return [
            self.amount,
            self.hour_of_day,
            self.location_hash,
            self.txn_count_1h,
            self.amount_to_avg_ratio,
        ]
