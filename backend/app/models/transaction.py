"""
app/models/transaction.py
─────────────────────────
Transaction ORM model.

anomaly_score is nullable — it will be NULL when a hard rule
short-circuits the decision before ML scoring (Fix 4).

otp_generated_at tracks when OTP was issued for 2-minute expiry (Fix 2).
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from app.db.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)

    # Input fields
    amount = Column(Float, nullable=False)
    location = Column(String, nullable=False)
    merchant_type = Column(String)
    timestamp = Column(DateTime, nullable=False)

    # Scoring
    risk_score = Column(Float, nullable=False)
    rule_score = Column(Float, nullable=False)
    anomaly_score = Column(Float)           # NULL if hard rule blocked (Fix 4)

    # Decision
    decision = Column(String, nullable=False)   # ALLOW | VERIFY | BLOCK
    reasons = Column(Text, nullable=False)       # JSON-encoded list[str]

    # OTP verification (only set when decision=VERIFY)
    otp = Column(String)
    otp_generated_at = Column(DateTime)          # Fix 2: OTP expiry tracking
    otp_verified = Column(Boolean, default=False)

    # Feedback (set later via /feedback endpoint)
    feedback_is_fraud = Column(Boolean)

    created_at = Column(DateTime, default=datetime.utcnow)
