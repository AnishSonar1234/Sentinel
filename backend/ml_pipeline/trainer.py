"""
ml_pipeline/trainer.py
──────────────────────
Standalone Isolation Forest trainer.

Usage:
    python -m ml_pipeline.trainer          # run directly
    from ml_pipeline.trainer import train  # called inline at cold-start

Generates synthetic data (normal + fraud patterns) and saves:
    ml_pipeline/artifacts/isolation_forest.pkl
    ml_pipeline/artifacts/scaler.pkl
"""
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "isolation_forest.pkl"
SCALER_PATH = ARTIFACTS_DIR / "scaler.pkl"

# Feature columns — must match TransactionFeatures.to_ml_vector() order
FEATURE_COLS = [
    "amount",
    "hour_of_day",
    "location_hash",
    "txn_count_1h",
    "amount_to_avg_ratio",
]


def generate_synthetic_data(n_samples: int = 3000) -> pd.DataFrame:
    """
    Generate a realistic mix of normal and fraudulent transactions.
    90% normal / 10% fraud — matches contamination parameter.
    """
    rng = np.random.default_rng(42)

    # Normal transactions (90%)
    n_normal = int(n_samples * 0.90)
    normal = pd.DataFrame({
        "amount": rng.lognormal(mean=5.5, sigma=1.0, size=n_normal),  # ~$245 avg
        "hour_of_day": rng.integers(7, 23, size=n_normal),            # normal daytime/evening
        "location_hash": rng.integers(0, 1000, size=n_normal),        # uniform across [0, 999]
        "txn_count_1h": rng.integers(0, 4, size=n_normal),            # normal 0-3 txns/hr
        "amount_to_avg_ratio": rng.uniform(0.3, 2.2, size=n_normal),  # normal ratio
    })

    # Fraudulent transactions (10%) — injected anomaly patterns
    n_fraud = n_samples - n_normal
    fraud = pd.DataFrame({
        "amount": rng.uniform(3000, 20000, size=n_fraud),             # high amount
        "hour_of_day": rng.integers(0, 6, size=n_fraud),              # 00:00–05:00 night-time
        "location_hash": rng.integers(0, 1000, size=n_fraud),         # distributed hashes
        "txn_count_1h": rng.integers(6, 18, size=n_fraud),            # velocity burst
        "amount_to_avg_ratio": rng.uniform(6.0, 40.0, size=n_fraud),  # high multiple
    })

    df = pd.concat([normal, fraud], ignore_index=True)
    return df.sample(frac=1, random_state=42).reset_index(drop=True)


def train(data: pd.DataFrame | None = None) -> None:
    """
    Train Isolation Forest on provided data or synthetic data.
    Saves model + scaler to artifacts/.
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    if data is None:
        logger.info("No data provided — generating synthetic training data (n=2000)")
        data = generate_synthetic_data(n_samples=2000)

    X = data[FEATURE_COLS].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=150,
        contamination=0.10,   # 10% expected fraud rate
        max_samples="auto",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_scaled)

    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

    logger.info(f"Model saved -> {MODEL_PATH}")
    logger.info(f"Scaler saved -> {SCALER_PATH}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print("Training Isolation Forest on synthetic data...")
    train()
    print("Training complete. Artifacts saved to ml_pipeline/artifacts/")
