"""
ml_pipeline/predictor.py
────────────────────────
Singleton fraud predictor — loaded ONCE at app startup into app.state.

Pattern: Chandra-Prashant — model deserialized once, not per-request.
This keeps latency low (no disk I/O per request).
"""
import logging
from pathlib import Path

import joblib
import numpy as np

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "isolation_forest.pkl"
SCALER_PATH = ARTIFACTS_DIR / "scaler.pkl"

# Cold-start score: returned when model hasn't been trained yet
# 0.3 = slightly suspicious but won't trigger BLOCK on its own
COLD_START_SCORE = 0.3


class FraudPredictor:
    """
    Wraps the trained Isolation Forest.

    Usage:
        predictor = FraudPredictor.load()   # at startup
        app.state.predictor = predictor

        score = predictor.score(features.to_ml_vector())  # per request
    """

    def __init__(self) -> None:
        self.model = None
        self.scaler = None
        self._loaded = False

    @classmethod
    def load(cls) -> "FraudPredictor":
        """
        Load model artifacts from disk.
        Raises FileNotFoundError if artifacts don't exist.
        Call ml_pipeline.trainer.train() first.
        """
        instance = cls()

        if not MODEL_PATH.exists() or not SCALER_PATH.exists():
            raise FileNotFoundError(
                f"Model artifacts not found at {ARTIFACTS_DIR}. "
                "Run: python -m ml_pipeline.trainer"
            )

        instance.model = joblib.load(MODEL_PATH)
        instance.scaler = joblib.load(SCALER_PATH)
        instance._loaded = True
        logger.info(f"✅ FraudPredictor loaded from {ARTIFACTS_DIR}")
        return instance

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def score(self, feature_vector: list) -> float:
        """
        Score a transaction's anomaly level.

        Returns:
            float in [0.0, 1.0]
            0.0 = perfectly normal
            1.0 = highly anomalous (likely fraud)

        Isolation Forest score_samples() returns values in roughly [-0.5, 0.5].
        More negative = more anomalous. We normalize to [0, 1]:
            anomaly_score = clip(1.0 - (raw + 0.5), 0, 1)
        """
        if not self._loaded:
            logger.warning("Predictor not loaded — using cold-start score")
            return COLD_START_SCORE

        try:
            X = np.array(feature_vector, dtype=float).reshape(1, -1)
            X_scaled = self.scaler.transform(X)
            raw_score = float(self.model.score_samples(X_scaled)[0])

            # Normalize: more negative raw = higher anomaly score
            anomaly = float(np.clip(1.0 - (raw_score + 0.5), 0.0, 1.0))
            return round(anomaly, 4)

        except Exception as e:
            logger.error(f"Prediction error: {e} — returning cold-start score")
            return COLD_START_SCORE
