"""
app/models/behavior_profile.py
───────────────────────────────
Per-user behavioral profile maintained by the BehaviorEngine.

frequent_locations and active_hours are stored as JSON strings
(SQLite doesn't have native JSON array support).
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.db.base import Base


class UserBehaviorProfile(Base):
    __tablename__ = "user_behavior_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, unique=True, nullable=False, index=True)

    # Welford running statistics
    avg_amount = Column(Float, default=0.0)
    std_amount = Column(Float, default=0.0)
    transaction_count = Column(Integer, default=0)

    # Behavioral patterns (JSON-encoded)
    frequent_locations = Column(Text, default="[]")   # list[str]
    active_hours = Column(Text, default="[]")          # list[int]

    # For velocity spike ratio computation
    baseline_hourly_rate = Column(Float, default=0.0)

    last_updated = Column(DateTime, default=datetime.utcnow)
