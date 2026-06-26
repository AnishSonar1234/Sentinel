"""
tests/conftest.py
──────────────────
Shared pytest fixtures for all tests.

Uses an in-memory SQLite DB for test isolation — no writes to sentinel.db.
Uses a mock FraudPredictor that always returns 0.3 to isolate API tests
from ML model availability.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from ml_pipeline.predictor import FraudPredictor

from sqlalchemy.pool import StaticPool

# ── In-memory test database ────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Mock predictor ─────────────────────────────────────────────────────────────
class MockPredictor:
    """Always returns 0.3 — neutral score that won't trigger BLOCK on its own."""
    is_loaded = True

    def score(self, feature_vector):
        return 0.3


# ── Fixtures ───────────────────────────────────────────────────────────────────
@pytest.fixture(scope="function")
def client():
    """
    Per-test FastAPI TestClient with:
    - Fresh in-memory SQLite DB (tables created, demo_user seeded)
    - Mock ML predictor (no model file needed)
    """
    # Create all tables in test DB
    from app.models import user, transaction, behavior_profile  # noqa: F401
    Base.metadata.create_all(bind=test_engine)

    # Seed demo user
    from app.db.init_db import seed_demo_user
    db = TestSessionLocal()
    try:
        seed_demo_user(db)
    finally:
        db.close()

    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.state.predictor = MockPredictor()

    with TestClient(app) as c:
        yield c

    # Teardown: drop all tables after each test
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


@pytest.fixture
def demo_transaction():
    """A valid normal transaction payload for demo_user."""
    return {
        "user_id": "demo_user",
        "amount": 250.0,
        "location": "Mumbai",
        "merchant_type": "retail",
    }


@pytest.fixture
def fraud_transaction():
    """A full-fraud transaction payload — should always BLOCK."""
    return {
        "user_id": "demo_user",
        "amount": 9999.0,
        "location": "Accra",
        "merchant_type": "wire_transfer",
        "timestamp": "2026-04-17T02:30:00",
    }
