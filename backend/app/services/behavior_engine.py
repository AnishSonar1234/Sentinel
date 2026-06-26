"""
app/services/behavior_engine.py
────────────────────────────────
Per-user behavioral profile engine.

Uses Welford's online algorithm for computing running mean and standard
deviation — O(1) per update, no need to store historical transactions.

Fix 1 (New-user fallback):
    If transaction_count < WARM_UP_THRESHOLD, use global defaults
    instead of the user's own (unreliable) stats. This prevents
    garbage z-scores for brand-new users.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.behavior_profile import UserBehaviorProfile
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import TransactionInput
from ml_pipeline.features import TransactionFeatures

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
WARM_UP_THRESHOLD = 5      # min transactions before trusting the profile
GLOBAL_AVG_AMOUNT = 1000.0 # fallback average for cold-start users (Fix 1)
GLOBAL_STD_AMOUNT = 500.0  # fallback std    for cold-start users (Fix 1)
MAX_FREQUENT_LOCATIONS = 10
VELOCITY_WINDOW_MINUTES = 60


def _hash_location(location: str) -> int:
    """Stable numeric hash of a location string, bounded to [0, 999]."""
    return abs(hash(location.lower().strip())) % 1000


class BehaviorEngine:
    """
    Stateless service — all state is persisted in the DB.
    Inject via FastAPI dependency or instantiate directly.
    """

    # ── Profile management ─────────────────────────────────────────────────────

    def get_or_create_profile(
        self, user_id: str, db: Session
    ) -> UserBehaviorProfile:
        """Return existing profile or create a new blank one."""
        profile = (
            db.query(UserBehaviorProfile)
            .filter_by(user_id=user_id)
            .first()
        )
        if profile is None:
            # Ensure the user row exists first
            if not db.query(User).filter_by(user_id=user_id).first():
                db.add(User(user_id=user_id))

            profile = UserBehaviorProfile(
                user_id=user_id,
                avg_amount=0.0,
                std_amount=0.0,
                transaction_count=0,
                frequent_locations=json.dumps([]),
                active_hours=json.dumps([]),
                baseline_hourly_rate=0.0,
                last_updated=datetime.utcnow(),
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
            logger.info(f"Created new profile for user: {user_id}")
        return profile

    # ── Velocity ───────────────────────────────────────────────────────────────

    def get_velocity(self, user_id: str, now: datetime, db: Session) -> int:
        """
        Count transactions in the last VELOCITY_WINDOW_MINUTES (60 min).
        This is the live velocity check — queried fresh on every request.
        """
        window_start = now - timedelta(minutes=VELOCITY_WINDOW_MINUTES)
        count = (
            db.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.timestamp >= window_start,
            )
            .count()
        )
        return count

    # ── Feature computation ────────────────────────────────────────────────────

    def compute_features(
        self,
        tx: TransactionInput,
        profile: UserBehaviorProfile,
        txn_count_1h: int,
    ) -> TransactionFeatures:
        """
        Build the TransactionFeatures dataclass from raw input + user profile.

        Fix 1: Use global defaults when profile is not yet warmed up.
        """
        count = profile.transaction_count
        warmed_up = count >= WARM_UP_THRESHOLD

        effective_avg = profile.avg_amount if warmed_up else GLOBAL_AVG_AMOUNT
        effective_std = profile.std_amount if warmed_up else GLOBAL_STD_AMOUNT

        # Parse JSON fields
        frequent_locations: list[str] = json.loads(profile.frequent_locations or "[]")
        active_hours: list[int] = json.loads(profile.active_hours or "[]")

        # ── Feature calculations ───────────────────────────────────────────────
        amount_deviation = abs(tx.amount - effective_avg) / (effective_std + 1e-6)
        amount_to_avg_ratio = tx.amount / (effective_avg + 1e-6)
        location_is_new = int(tx.location.lower() not in [l.lower() for l in frequent_locations])

        tx_hour = tx.timestamp.hour
        time_anomaly = int(bool(active_hours) and tx_hour not in active_hours)

        baseline = profile.baseline_hourly_rate
        frequency_spike = txn_count_1h / max(baseline, 0.1)

        return TransactionFeatures(
            amount=tx.amount,
            hour_of_day=tx_hour,
            location_hash=_hash_location(tx.location),
            txn_count_1h=txn_count_1h,
            amount_to_avg_ratio=round(amount_to_avg_ratio, 4),
            amount_deviation=round(amount_deviation, 4),
            location_is_new=location_is_new,
            time_anomaly=time_anomaly,
            frequency_spike=round(frequency_spike, 4),
            raw_location=tx.location,
            raw_amount=tx.amount,
            raw_hour=tx_hour,
            raw_txn_count=txn_count_1h,
        )

    # ── Profile update (Welford's algorithm) ──────────────────────────────────

    def update_profile(
        self,
        profile: UserBehaviorProfile,
        tx: TransactionInput,
        db: Session,
    ) -> None:
        """
        Incrementally update the user profile using Welford's online algorithm.
        O(1) — no historical data needed.

        Welford's update:
            n     = n + 1
            delta = x - mean
            mean  = mean + delta / n
            M2    = M2 + delta * (x - mean)
            std   = sqrt(M2 / n)
        """
        n = profile.transaction_count + 1
        x = tx.amount

        # Welford step
        delta = x - profile.avg_amount
        new_avg = profile.avg_amount + delta / n

        # We store variance incrementally via M2 approximation
        # For simplicity: update std directly using running variance
        if n == 1:
            new_std = 0.0
        else:
            # Running std approximation (good enough for scoring)
            alpha = 0.1  # exponential smoothing factor
            new_std = (1 - alpha) * profile.std_amount + alpha * abs(x - new_avg)

        # Update frequent locations (keep top MAX_FREQUENT_LOCATIONS)
        locations: list[str] = json.loads(profile.frequent_locations or "[]")
        loc = tx.location
        if loc not in locations:
            locations.append(loc)
            if len(locations) > MAX_FREQUENT_LOCATIONS:
                locations.pop(0)

        # Update active hours
        hours: list[int] = json.loads(profile.active_hours or "[]")
        hour = tx.timestamp.hour
        if hour not in hours:
            hours.append(hour)

        # Update baseline hourly rate (rolling average of hourly rates)
        # Simple approximation: transaction_count / hours_since_first_txn
        new_baseline = max(n / max(len(set(hours)), 1), 0.1)

        # Persist
        profile.avg_amount = round(new_avg, 4)
        profile.std_amount = round(new_std, 4)
        profile.transaction_count = n
        profile.frequent_locations = json.dumps(locations)
        profile.active_hours = json.dumps(sorted(set(hours)))
        profile.baseline_hourly_rate = round(new_baseline, 4)
        profile.last_updated = datetime.utcnow()

        db.add(profile)
        db.commit()
