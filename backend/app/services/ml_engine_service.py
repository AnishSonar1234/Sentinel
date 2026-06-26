"""
app/services/ml_engine_service.py
───────────────────────────────────
Thin wrapper around FraudPredictor.

The predictor is loaded ONCE at startup and injected via app.state.
This service is a convenience layer — it adds logging and a fallback.
"""
import logging

from ml_pipeline.features import TransactionFeatures
from ml_pipeline.predictor import FraudPredictor

logger = logging.getLogger(__name__)


class MLEngineService:
    """
    Wraps the FraudPredictor singleton stored in app.state.predictor.

    Usage:
        ml_service = MLEngineService(request.app.state.predictor)
        score = ml_service.score(features)
    """

    def __init__(self, predictor: FraudPredictor) -> None:
        self.predictor = predictor

    def score(self, features: TransactionFeatures) -> float:
        """
        Returns anomaly score in [0, 1].
        Delegates to FraudPredictor which handles cold-start fallback internally.
        """
        vector = features.to_ml_vector()
        anomaly_score = self.predictor.score(vector)
        logger.debug(f"ML anomaly score: {anomaly_score}")
        return anomaly_score
