"""
app/db/init_db.py
─────────────────
Database initialization:
  1. create_all()     — create all ORM tables if they don't exist
  2. seed_demo_user() — seed 'demo_user' with a stable warm profile

Called once at application startup (app/main.py lifespan).
"""
import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine, SessionLocal

logger = logging.getLogger(__name__)


def create_tables() -> None:
    """
    Create all SQLAlchemy ORM tables (no Alembic needed — demo-friendly).
    Import all models here so Base.metadata knows about them.
    """
    from app.models import user, transaction, behavior_profile  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables ready")


def seed_demo_user(db: Session) -> None:
    """
    Create 'demo_user' with a stable, pre-warmed behavior profile.

    Why avg_amount=250?
      → full_fraud scenario sends $9999 → ratio = ~40x → guaranteed BLOCK
      → reason code: "Amount: 40.0x above user average" (impressive for demo)

    The frequent_locations list ensures Lagos / Accra are flagged as new.
    The active_hours list ensures 03:00 AM is flagged as unusual.
    """
    from app.models.user import User
    from app.models.behavior_profile import UserBehaviorProfile

    if db.query(User).filter_by(user_id="demo_user").first():
        logger.info("demo_user already seeded — skipping")
        return

    db.add(User(user_id="demo_user"))
    db.add(UserBehaviorProfile(
        user_id="demo_user",
        avg_amount=250.0,
        std_amount=80.0,
        transaction_count=50,
        frequent_locations=json.dumps(["Mumbai", "Pune"]),
        active_hours=json.dumps(list(range(9, 19))),   # 09:00–18:00
        baseline_hourly_rate=1.2,
        last_updated=datetime.utcnow(),
    ))
    db.commit()
    logger.info("✅ demo_user seeded (avg_amount=250, locations=[Mumbai, Pune])")


def init_db() -> None:
    """Full initialization — called at startup."""
    create_tables()
    db = SessionLocal()
    try:
        seed_demo_user(db)
    finally:
        db.close()
