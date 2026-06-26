"""
app/main.py
────────────
FastAPI application entry point.

Startup sequence (lifespan):
  1. create_all()      → SQLite tables created if not exist
  2. seed_demo_user()  → stable demo user seeded (Fix 5)
  3. Auto-train ML     → if artifacts missing, train on synthetic data
  4. Load predictor    → FraudPredictor loaded once into app.state (Fix 4)

After startup: uvicorn is ready, Swagger at /docs
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.db.init_db import init_db
from ml_pipeline.predictor import FraudPredictor
from ml_pipeline.trainer import train

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("sentinel")


# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup / shutdown lifecycle.
    Everything here runs BEFORE the server accepts requests.
    """
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("  🛡️  Sentinel — Fraud Decision Engine")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Step 1 + 2: DB tables + demo user seed
    logger.info("▶ Initializing database...")
    init_db()

    # Step 3: Auto-train if model artifacts are missing (cold start)
    from ml_pipeline.predictor import MODEL_PATH, SCALER_PATH
    if not MODEL_PATH.exists() or not SCALER_PATH.exists():
        logger.info("▶ Model artifacts not found — training on synthetic data...")
        train()
        logger.info("▶ Training complete.")

    # Step 4: Load model into memory (loaded ONCE — Chandra-Prashant pattern)
    logger.info("▶ Loading ML model into memory...")
    try:
        app.state.predictor = FraudPredictor.load()
        logger.info("▶ Model loaded successfully ✅")
    except Exception as e:
        logger.error(f"▶ Failed to load model: {e}")
        app.state.predictor = None

    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("  ✅ Sentinel ready — http://localhost:8000/docs")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    yield  # Server runs here

    # Shutdown
    logger.info("▶ Sentinel shutting down.")


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Sentinel — Real-Time Fraud Decision Engine",
    description="""
## 🛡️ Sentinel Fraud Engine

A production-grade, explainable fraud decision API.

### How it works
1. Submit a transaction → receives **ALLOW / VERIFY / BLOCK**
2. Every decision comes with **structured reason codes**
3. Behavioral profiling learns each user's patterns over time
4. ML anomaly detection (Isolation Forest) acts as a second opinion

### Quick Demo
Use `POST /api/v1/simulate` with scenario `full_fraud` to see an instant BLOCK
with reasons like *"Amount: 40x above user average"*.

### Architecture
- **Rules Engine**: weighted scoring (60%) — interpretable, auditable
- **ML Engine**: Isolation Forest anomaly detection (40%)
- **Decision thresholds**: < 40 → ALLOW | 40–74 → VERIFY | ≥ 75 → BLOCK
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ─────────────────────────────────────────────────────────────────────
app.include_router(api_router)


# ── Root redirect ──────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root():
    return {
        "message": "🛡️ Sentinel Fraud Engine is running",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
