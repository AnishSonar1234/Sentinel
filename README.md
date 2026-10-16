# 🛡️ Sentinel — Real-Time Fraud Decision Engine & Intelligence Dashboard

> **Live Deployment:** [https://sentinel-46uf.onrender.com](https://sentinel-46uf.onrender.com)  
> **API Docs (Swagger UI):** [https://sentinel-46uf.onrender.com/docs](https://sentinel-46uf.onrender.com/docs)

**Sentinel** is a production-grade, modular real-time fraud decision engine and interactive intelligence dashboard. It combines multi-tier deterministic rules, calibrated machine learning anomaly detection (Isolation Forest), adaptive online user behavioral profiling (Welford's algorithm), and step-up OTP verification to classify and explain transaction risk in milliseconds.

The project is structured as a unified application: a high-performance **FastAPI** backend that runs the scoring pipeline and serves the compiled **React + Vite** frontend SPA with runtime environment configuration.

---

## 🏛️ System Architecture

```
                  ┌──────────────────────────────────────────────┐
                  │             Incoming Transaction             │
                  └──────────────────────┬───────────────────────┘
                                         │
                         ┌───────────────┴───────────────┐
                         ▼                               ▼
               ┌───────────────────┐           ┌───────────────────┐
               │  Idempotency Check │           │  Velocity Monitor │
               │   (Cached Result) │           │    (Live DB 1h)   │
               └─────────┬─────────┘           └─────────┬─────────┘
                         │                               │
                         └───────────────┬───────────────┘
                                         ▼
                         ┌───────────────────────────────┐
                         │   Adaptive Behavior Engine    │
                         │    (Welford's Mean & Std)     │
                         └───────────────┬───────────────┘
                                         ▼
                         ┌───────────────────────────────┐
                         │    Hard-Rule Short Circuit    ├─────► [ BLOCK (100) ]
                         │ (Trifecta / Velocity Spike >10)│       (ML Skipped)
                         └───────────────┬───────────────┘
                                         │ (No hard block)
                         ┌───────────────┴───────────────┐
                         ▼                               ▼
               ┌───────────────────┐           ┌───────────────────┐
               │ Rules Engine (60%)│           │  ML Predictor(40%)│
               │ • Amount Z-score  │           │ • Isolation Forest│
               │ • Unrecognized Loc│           │ • Sigmoid Calib   │
               │ • Time Anomaly    │           │ • Inlier/Outlier  │
               │ • Frequency Burst │           │   Decision Map    │
               └─────────┬─────────┘           └─────────┬─────────┘
                         │                               │
                         └───────────────┬───────────────┘
                                         ▼
                         ┌───────────────────────────────┐
                         │      Score Fusion Engine      │
                         │   Risk = (0.60*R + 0.40*M)*100│
                         └───────────────┬───────────────┘
                                         ▼
                         ┌───────────────────────────────┐
                         │    Tiered Decision Engine     │
                         ├───────────────────────────────┤
                         │ < 40   →  ALLOW   (Proceed)   │
                         │ 40–74  →  VERIFY  (OTP StepUp)│
                         │ ≥ 75   →  BLOCK   (Rejected)  │
                         └───────────────┬───────────────┘
                                         ▼
                         ┌───────────────────────────────┐
                         │     Explainability Engine     │
                         │  (Clear, Actionable Reasons)  │
                         └───────────────┬───────────────┘
                                         ▼
                         ┌───────────────────────────────┐
                         │  Welford Profile Update & DB  │
                         └───────────────────────────────┘
```

---

## ✨ Key Features

- **⚡ Sub-Millisecond Score Fusion:** Fuses interpretable business rules (60%) with unsupervised machine learning (40%) into a normalized [0–100] risk score.
- **🌲 Calibrated Isolation Forest:** Uses Scikit-Learn `decision_function` mapped through a calibrated sigmoid curve to accurately assign low anomaly scores (5–12%) to normal spending while detecting genuine fraud anomalies (75–85%).
- **🔄 Dynamic Model Reset (`POST /api/v1/reset-model`):** Retrains the Isolation Forest model on fresh data distributions and hot-reloads it in-memory without server downtime.
- **👤 Adaptive Behavior Profiling:** Implements Welford's online algorithm to maintain running means and standard deviations in $O(1)$ time with zero historical table scans.
- **🛡️ Trifecta Hard-Block Guardrail:** Extreme fraud (high amount multiplier + foreign location + off-hours 00:00–05:00) triggers instant rejection and short-circuits ML processing.
- **📱 Step-Up OTP Verification:** Transactions in the `VERIFY` band generate a 6-digit cryptographic OTP expiring in 2 minutes. Successful OTP validation transitions the transaction to `ALLOW`.
- **🕵️ Analyst Investigation Modal:** The web console allows analysts to review transaction reasons, trigger Step-up MFA, Allow, or Block transactions directly.
- **🧪 Built-In Live Fraud Simulator:** Interactive preset scenarios (`normal`, `high_amount`, `new_location`, `night_time`, `rapid_fire`, `full_fraud`) test the pipeline end-to-end.
- **🌐 Unified Deployment:** Built for containerized or zero-configuration cloud deployment (Render, Docker, Railway, Fly.io).

---

## 📂 Project Structure

```
Sentinel/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── feedback.py          # POST /api/v1/feedback
│   │   │   │   ├── health.py            # GET /health, POST /reset-model
│   │   │   │   ├── simulate.py          # POST /api/v1/simulate
│   │   │   │   ├── transactions.py      # POST /analyze, POST /verify, GET /transactions
│   │   │   │   └── users.py             # GET /api/v1/user-profile
│   │   │   └── router.py                # Aggregated API routes
│   │   ├── db/
│   │   │   ├── base.py                  # Declarative base
│   │   │   ├── init_db.py               # Table creation & seed demo user
│   │   │   └── session.py               # Engine & session management
│   │   ├── models/                      # SQLAlchemy ORM models
│   │   ├── schemas/                     # Pydantic v2 schemas
│   │   ├── services/
│   │   │   ├── agent_investigator.py   # AI Copilot SAR report generator
│   │   │   ├── behavior_engine.py      # Welford online profiling & velocity
│   │   │   ├── decision_engine.py      # Score fusion & threshold tiers
│   │   │   ├── explainability_engine.py# Plain-English reason code generator
│   │   │   ├── ml_engine_service.py    # Service wrapper for ML predictor
│   │   │   ├── rules_engine.py         # Hard & soft deterministic rules
│   │   │   └── verification_service.py # OTP generation and verification
│   │   └── main.py                      # FastAPI app & static SPA server
│   ├── config/
│   │   └── settings.py                  # Pydantic BaseSettings (.env)
│   ├── ml_pipeline/
│   │   ├── artifacts/                   # Saved model & scaler .pkl files
│   │   ├── features.py                  # TransactionFeatures dataclass
│   │   ├── predictor.py                 # In-memory FraudPredictor singleton
│   │   └── trainer.py                   # Isolation Forest training script
│   ├── static/                          # Production frontend build assets
│   ├── tests/                           # Pytest unit & integration suite
│   ├── requirements.txt                 # Backend Python dependencies
│   └── .env                             # Environment configuration
├── frontend/
│   └── dist/                            # Pre-built Vite SPA distribution
│       ├── env.js                       # Runtime environment configuration
│       ├── index.html                   # Entry HTML
│       └── assets/                      # Bundled JS and CSS
└── README.md                            # Main project documentation
```

---

## 🚀 Quick Start (Local Setup)

### Prerequisites
- Python 3.10+
- pip

### 1. Clone and Enter Directory
```bash
git clone https://github.com/AnishSonar1234/Sentinel.git
cd Sentinel
```

### 2. Set Up Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 4. Run Sentinel
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

On startup, Sentinel automatically:
- Creates SQLite tables in `sentinel.db`.
- Seeds a pre-warmed `demo_user` behavior profile.
- Trains or loads the Isolation Forest model artifacts from `backend/ml_pipeline/artifacts/`.
- Mounts and serves the React dashboard at `http://localhost:8000/`.
- Mounts the interactive Swagger documentation at `http://localhost:8000/docs`.

---

## ⚙️ Environment Configuration

### Backend (`backend/.env`)

```ini
DATABASE_URL=sqlite:///./sentinel.db
DEBUG=False
APP_NAME=Sentinel
ALLOW_THRESHOLD=40.0
BLOCK_THRESHOLD=75.0
VELOCITY_WINDOW_MINUTES=60
VELOCITY_SPIKE_THRESHOLD=5
HIGH_AMOUNT_MULTIPLIER=3.0
```

> **Using Supabase / PostgreSQL in Production:**  
> Simply change `DATABASE_URL` in `.env` to:  
> `DATABASE_URL=postgresql+psycopg2://postgres:<PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres`  
> and install `psycopg2-binary`. No schema changes required.

### Frontend Runtime Configuration (`frontend/dist/env.js` and `backend/static/env.js`)

Sentinel uses a zero-rebuild runtime configuration pattern. You can change the backend URL in `env.js` without recompiling:

```javascript
window.ENV = {
  API_URL: "https://sentinel-46uf.onrender.com" // or "http://localhost:8000"
};
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/analyze-transaction` | Core fraud analysis pipeline returning risk score, decision, reasons, and OTP (if VERIFY) |
| `POST` | `/api/v1/verify-transaction` | Submit 6-digit OTP to verify and approve a flagged transaction |
| `POST` | `/api/v1/feedback` | Label transaction as legitimate or fraudulent for audit and retraining |
| `POST` | `/api/v1/simulate` | Execute preset fraud scenarios against the scoring pipeline |
| `POST` | `/api/v1/reset-model` | Retrain Isolation Forest model and hot-reload in memory |
| `GET` | `/api/v1/transactions` | Query transaction history (filterable by user, decision, limit) |
| `GET` | `/api/v1/user-profile` | Inspect a user's learned baseline stats, frequent locations, and active hours |
| `GET` | `/api/v1/health` | System health check and model status |

### Example Request (`POST /api/v1/analyze-transaction`)

```json
{
  "user_id": "demo_user",
  "amount": 250.00,
  "location": "Mumbai",
  "merchant_type": "retail",
  "timestamp": "2026-10-16T14:30:00Z"
}
```

### Example Response (`ALLOW`)

```json
{
  "transaction_id": "txn_637d662e",
  "user_id": "demo_user",
  "amount": 250.0,
  "decision": "ALLOW",
  "risk_score": 8.56,
  "rule_score": 0.0437,
  "anomaly_score": 0.1485,
  "reasons": [
    "Transaction amount matches normal spending baseline",
    "Verified behavior profile and location pattern"
  ],
  "otp": null
}
```

---

## 🧪 Simulation Scenarios

The `/api/v1/simulate` endpoint provides rapid end-to-end testing:

| Scenario | Expected Decision | Signals Tested |
|---|---|---|
| `normal` | **ALLOW** | Standard spending amount, home location, standard operating hours |
| `high_amount` | **VERIFY** / **BLOCK** | 4–10x above user's moving average amount |
| `new_location` | **VERIFY** | Location absent from user's frequent locations profile |
| `night_time` | **VERIFY** | Off-hours payment (03:00 AM) outside active hour profile |
| `rapid_fire` | **BLOCK** | Velocity burst (>5 transactions within 60 minutes) |
| `full_fraud` | **BLOCK** | Trifecta: 40x amount + foreign location + 02:00 AM (Hard Rule) |

---

## 🔬 Testing

Run the full automated test suite covering rules, score fusion, model loading, and API endpoints:

```bash
cd backend
python -m pytest tests/ -v
```

Expected result:
```text
tests/test_api.py ...........................                            [ 54%]
tests/test_decision_engine.py .............                              [ 80%]
tests/test_rules_engine.py ..........                                    [100%]
====================== 50 passed in 1.20s =======================
```

---

## ☁️ Deployment

### Render Configuration
- **Build Command:** `pip install -r backend/requirements.txt`
- **Start Command:** `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir backend`
- **Environment Variables:**
  - `PYTHON_VERSION`: `3.11.9` or `3.13.0`
  - `DATABASE_URL`: `sqlite:///./sentinel.db`

---

## 📄 License

This project is licensed under the MIT License.