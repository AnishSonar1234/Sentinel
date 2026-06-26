"""
app/services/explainability_engine.py
──────────────────────────────────────
SHAP-inspired human-readable reasons for every fraud decision.

Format (nkhalfe56-star pattern):
    "Amount: 8.3x above user average"
    "Velocity: 6 transactions in last hour"
    "Unrecognized location: Lagos"
    "Unusual hour: transaction at 03:00"
    "Statistical outlier: 4.1 std deviations from mean"

Returns the top 3 most impactful reasons — clean output for demos.
"""
from ml_pipeline.features import TransactionFeatures
from app.services.rules_engine import RuleResult


class ExplainabilityEngine:

    def generate_reasons(
        self,
        features: TransactionFeatures,
        rule_result: RuleResult,
        hard_block: bool = False,
        hard_reason: str = "",
    ) -> list[str]:
        """
        Build final reason list for the API response.

        Hard block: returns a single authoritative reason.
        Normal path: returns top 3 from soft rule reasons.
        """
        if hard_block and hard_reason:
            return [hard_reason]

        reasons = rule_result.reasons

        # Ensure we always return something meaningful
        if not reasons:
            reasons = self._fallback_reasons(features)

        # Cap at 3 for clean output
        return reasons[:3]

    def _fallback_reasons(self, features: TransactionFeatures) -> list[str]:
        """
        Generate at least one reason when no rules were triggered.
        Used for edge cases where ML score drove a VERIFY decision.
        """
        if features.amount_to_avg_ratio > 1.5:
            return [f"Amount: {features.amount_to_avg_ratio:.1f}x above user average"]
        if features.txn_count_1h > 2:
            return [f"Elevated activity: {features.txn_count_1h} transactions in last hour"]
        return ["Anomaly detected by ML model (pattern deviation)"]
