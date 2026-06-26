"""
app/services/rules_engine.py
─────────────────────────────
Dedicated rules module (AnomalyShield pattern).

Two tiers of rules:

1. HARD RULES (Fix 4 — short-circuit):
   Checked BEFORE ML scoring. If triggered, decision is immediately BLOCK
   with risk_score=100. ML model is NOT called.

2. SOFT RULES (weighted scoring):
   Only executed if no hard rule triggered.
   Produces a rule_score in [0, 1] plus structured reason codes.
"""
import logging
from dataclasses import dataclass, field

from config.settings import settings
from ml_pipeline.features import TransactionFeatures

logger = logging.getLogger(__name__)

# ── Weights for soft rule scoring ──────────────────────────────────────────────
WEIGHTS: dict[str, float] = {
    "amount_deviation": 0.35,
    "location_change":  0.25,
    "time_anomaly":     0.20,
    "frequency_spike":  0.20,
}

# Normalisation ceilings — values at or above these map to score=1.0
CEILINGS: dict[str, float] = {
    "amount_deviation": 5.0,   # z-score of 5+ → fully suspicious
    "location_change":  1.0,   # binary 0/1
    "time_anomaly":     1.0,   # binary 0/1
    "frequency_spike":  3.0,   # 3x baseline rate → fully suspicious
}


@dataclass
class RuleResult:
    score: float                        # [0, 1] weighted rule score
    reasons: list[str] = field(default_factory=list)
    hard_block: bool = False
    hard_reason: str = ""


class RulesEngine:

    # ── Hard rules ─────────────────────────────────────────────────────────────

    def is_hard_block(self, f: TransactionFeatures) -> tuple[bool, str]:
        """
        Fix 4: Check hard-block conditions BEFORE calling ML.
        Returns (is_blocked, reason_string).

        Hard block conditions (any one triggers):
          1. Trifecta signal: high amount + new location + unusual hour
          2. Extreme velocity: > 10 txns in the last hour
        """
        # Condition 1: Trifecta fraud pattern
        if (
            f.amount_to_avg_ratio >= settings.high_amount_multiplier
            and f.location_is_new
            and f.time_anomaly
        ):
            reason = (
                f"Hard block: {f.amount_to_avg_ratio:.1f}x amount + "
                f"new location ({f.raw_location}) + "
                f"unusual hour ({f.raw_hour:02d}:00)"
            )
            return True, reason

        # Condition 2: Extreme velocity
        if f.txn_count_1h > 10:
            reason = (
                f"Hard block: extreme velocity — "
                f"{f.txn_count_1h} transactions in last hour"
            )
            return True, reason

        return False, ""

    # ── Soft rules ─────────────────────────────────────────────────────────────

    def evaluate(self, f: TransactionFeatures) -> RuleResult:
        """
        Evaluate weighted soft rules and return score + triggered reasons.
        Only called when no hard rule was triggered.
        """
        raw_values = {
            "amount_deviation": f.amount_deviation,
            "location_change":  float(f.location_is_new),
            "time_anomaly":     float(f.time_anomaly),
            "frequency_spike":  f.frequency_spike,
        }

        # Normalise each signal to [0, 1] using ceiling clipping
        normalised = {
            k: min(raw_values[k] / CEILINGS[k], 1.0)
            for k in WEIGHTS
        }

        # Weighted sum → rule_score in [0, 1]
        rule_score = sum(WEIGHTS[k] * normalised[k] for k in WEIGHTS)
        rule_score = round(min(rule_score, 1.0), 4)

        reasons = self._build_reasons(f)
        return RuleResult(score=rule_score, reasons=reasons)

    # ── Reason code generation ─────────────────────────────────────────────────

    def _build_reasons(self, f: TransactionFeatures) -> list[str]:
        """
        Build sorted list of triggered soft-rule reason strings.
        Sorted by severity (highest contribution first).
        """
        triggered: list[tuple[float, str]] = []

        if f.amount_to_avg_ratio >= 2.0:
            triggered.append((
                f.amount_to_avg_ratio,
                f"Amount: {f.amount_to_avg_ratio:.1f}x above user average",
            ))

        if f.txn_count_1h >= settings.velocity_spike_threshold:
            triggered.append((
                float(f.txn_count_1h),
                f"Velocity: {f.txn_count_1h} transactions in last hour",
            ))

        if f.location_is_new:
            triggered.append((
                3.0,  # fixed high weight for new location
                f"Unrecognized location: {f.raw_location}",
            ))

        if f.time_anomaly:
            triggered.append((
                2.0,
                f"Unusual hour: transaction at {f.raw_hour:02d}:00",
            ))

        if f.amount_deviation >= 3.0:
            triggered.append((
                f.amount_deviation,
                f"Statistical outlier: {f.amount_deviation:.1f} std deviations from mean",
            ))

        if f.frequency_spike >= 2.0:
            triggered.append((
                f.frequency_spike,
                f"Frequency spike: {f.frequency_spike:.1f}x above normal rate",
            ))

        # Sort by severity descending, return reason strings only
        triggered.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in triggered]
