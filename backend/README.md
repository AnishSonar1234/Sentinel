# Sentinel — Real-Time Fraud Decision Engine API

> 🛡️ A production-grade, modular fraud decision engine built with FastAPI + SQLite.
> Every decision is **explainable**, **fast**, and **demo-ready**.

---

## Architecture

```
Transaction → BehaviorEngine → RulesEngine ──┐
                                              ├→ fuse_scores() → ALLOW/VERIFY/BLOCK
            → VelocityCheck → MLEngine ───────┘
                                      ↓
                          ExplainabilityEngine → reason_codes[]
```

**Decision thresholds:**

| Score | Decision |
|---|---|
| < 40 | ✅ ALLOW |
| 40 – 74 | ⚠️ VERIFY (OTP required) |
| ≥ 75 | 🚫 BLOCK |

---

## Quick Start (Zero Setup)

```bash
# 1. Clone and enter the directory
cd sentinel

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment file
copy .env.example .env

# 5. Start the server
uvicorn app.main:app --reload
```

On first startup, Sentinel will automatically:
- Create `sentinel.db` (SQLite)
- Seed `demo_user` with a warm behavior profile
- Train the Isolation Forest model on synthetic data
- Load the model into memory

👉 **Open Swagger UI:** http://localhost:8000/docs

---

## Demo Script (5-Minute Demo)

```bash
BASE=http://localhost:8000/api/v1

# 1. Health check
curl $BASE/health

# 2. Normal transaction → ALLOW
curl -X POST $BASE/simulate \
  -H "Content-Type: application/json" \
  -d '{"user_id":"demo_user","scenario":"normal"}'

# 3. High amount → VERIFY or BLOCK
curl -X POST $BASE/simulate \
  -H "Content-Type: application/json" \
  -d '{"user_id":"demo_user","scenario":"high_amount"}'

# 4. Full fraud → BLOCK (40x amount + new location + 2AM)
curl -X POST $BASE/simulate \
  -H "Content-Type: application/json" \
  -d '{"user_id":"demo_user","scenario":"full_fraud"}'

# 5. Verify the OTP from a VERIFY decision
curl -X POST $BASE/verify-transaction \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"<txn_id>","otp":"<otp>"}'

# 6. Submit feedback
curl -X POST $BASE/feedback \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"<txn_id>","is_fraud":true}'

# 7. View user profile (shows learned behavior)
curl "$BASE/user-profile?user_id=demo_user"
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/analyze-transaction` | Submit transaction for fraud analysis |
| POST | `/api/v1/verify-transaction` | Submit OTP to verify a flagged transaction |
| POST | `/api/v1/feedback` | Label a transaction as fraud/legitimate |
| POST | `/api/v1/simulate` | Run a fraud scenario through the full pipeline |
| GET | `/api/v1/transactions` | List transactions (filterable) |
| GET | `/api/v1/user-profile` | Get a user's behavior profile |
| GET | `/api/v1/health` | System health + model status |

### Example request

```json
POST /api/v1/analyze-transaction
{
  "user_id": "user_001",
  "amount": 9999.00,
  "location": "Lagos",
  "merchant_type": "electronics",
  "timestamp": "2026-04-17T03:00:00Z"
}
```

### Example response

```json
{
  "transaction_id": "txn_9a8b7c",
  "decision": "BLOCK",
  "risk_score": 100.0,
  "rule_score": 1.0,
  "anomaly_score": null,
  "reasons": [
    "Hard block: 40.0x amount + new location (Lagos) + unusual hour (03:00)"
  ]
}
```

---

## Simulation Scenarios

| Scenario | Expected Decision | Why |
|---|---|---|
| `normal` | ALLOW | Typical amount, known location, business hours |
| `high_amount` | VERIFY / BLOCK | 5–10x above average |
| `new_location` | VERIFY | Location not in user's history |
| `night_time` | VERIFY | Transaction at 03:00 AM |
| `rapid_fire` | BLOCK | Call 5+ times to trigger velocity spike |
| `full_fraud` | BLOCK | 40x amount + new location + 2AM (hard rule) |

---

## Running Tests

```bash
pytest tests/ -v --tb=short
```

---

## Switching to Supabase (Production Path)

Everything is database-agnostic via SQLAlchemy. To use Supabase PostgreSQL:

1. Add to `.env`:
   ```
   DATABASE_URL=postgresql+psycopg2://postgres:<pw>@db.<ref>.supabase.co:5432/postgres
   ```
2. Install: `pip install psycopg2-binary`
3. Restart the server — all ORM queries work identically

No code changes needed.

---

## Technical Design Notes

- **Rules Engine** (60%): Weighted scoring across 4 signals (amount deviation, location change, time anomaly, velocity spike)
- **ML Engine** (40%): Isolation Forest anomaly detection, trained on synthetic data
- **Hard-rule short-circuit**: Trifecta fraud (high amount + new location + 3AM) → immediate BLOCK, ML skipped
- **OTP Expiry**: VERIFY decisions expire in 2 minutes → auto-escalate to BLOCK
- **Idempotency**: Duplicate `transaction_id` returns cached result
- **New-user fallback**: `transaction_count < 5` → global defaults to avoid division by zero
- **Welford's algorithm**: Incremental mean/std update — O(1), no historical data needed
