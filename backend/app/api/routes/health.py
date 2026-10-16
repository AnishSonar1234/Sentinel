"""
app/api/routes/health.py
─────────────────────────
GET /api/v1/health — system health + model status check.
"""
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health", summary="System health check")
def health_check(request: Request):
    """
    Returns service status including:
    - DB connectivity (implicit — if this route works, DB is up)
    - ML model load status
    - App version
    """
    predictor = getattr(request.app.state, "predictor", None)
    model_loaded = predictor is not None and predictor.is_loaded

    return {
        "status": "ok",
        "app": "Sentinel — Real-Time Fraud Decision Engine",
        "version": "1.0.0",
        "model_loaded": model_loaded,
        "model_path": "./ml_pipeline/artifacts/isolation_forest.pkl",
        "db": "sqlite (sentinel.db)",
        "endpoints": [
            "POST /api/v1/analyze-transaction",
            "POST /api/v1/verify-transaction",
            "POST /api/v1/feedback",
            "POST /api/v1/simulate",
            "GET  /api/v1/transactions",
            "GET  /api/v1/user-profile",
            "GET  /api/v1/health",
            "POST /api/v1/reset-model",
        ],
    }


@router.post("/reset-model", summary="Retrain and reset ML model")
def reset_model(request: Request):
    """
    Retrains the Isolation Forest model on fresh data distribution and
    reloads the predictor in memory.
    """
    from ml_pipeline.trainer import train
    from ml_pipeline.predictor import FraudPredictor

    train()
    request.app.state.predictor = FraudPredictor.load()

    return {
        "status": "ok",
        "message": "Model successfully retrained and reloaded into memory.",
        "model_loaded": request.app.state.predictor.is_loaded,
    }
