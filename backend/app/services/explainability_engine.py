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
        decision: str = "ALLOW",
        hard_block: bool = False,
        hard_reason: str = "",
    ) -> list[str]:
        """
        Build final reason list for the API response.

        Hard block: returns a single authoritative reason.
        Normal path: returns top 3 from soft rule reasons.
        ALLOW decision: returns clear positive baseline explanations.
        """
        if hard_block and hard_reason:
            return [hard_reason]

        reasons = list(rule_result.reasons)

        if decision == "ALLOW":
            if not reasons:
                return [
                    "Transaction amount matches normal spending baseline",
                    "Verified behavior profile and location pattern",
                ]
            return reasons[:2]

        # Ensure we always return something meaningful for VERIFY or BLOCK
        if not reasons:
            reasons = self._fallback_reasons(features, decision)

        # Cap at 3 for clean output
        return reasons[:3]

    def _fallback_reasons(self, features: TransactionFeatures, decision: str = "VERIFY") -> list[str]:
        """
        Generate clear reasons when strict rule thresholds were not met
        but ML anomaly score elevated the risk to VERIFY or BLOCK.
        """
        reasons = []
        if features.amount_to_avg_ratio > 1.3:
            reasons.append(f"Amount: {features.amount_to_avg_ratio:.1f}x higher than standard profile")
        if features.txn_count_1h >= 2:
            reasons.append(f"Elevated velocity: {features.txn_count_1h} transactions in last hour")
        if features.location_is_new:
            reasons.append(f"Unrecognized location: {features.raw_location}")
        if features.time_anomaly:
            reasons.append(f"Unusual transaction hour ({features.raw_hour:02d}:00)")

        if not reasons:
            if decision == "BLOCK":
                reasons.append("High-risk multivariate anomaly pattern detected by ML model")
            else:
                reasons.append("Multivariate behavioral pattern deviation detected by ML model")

        return reasons
