"""
config/settings.py
──────────────────
Centralized application settings using Pydantic BaseSettings.
All values are read from environment variables / .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────
    app_name: str = "Sentinel"
    app_version: str = "1.0.0"
    secret_key: str = "secret-key-default"
    debug: bool = False
    gemini_api_key: str = ""

    # ── Supabase ──────────────────────────────────────────────────────
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""
    database_url: str = ""  # postgresql+asyncpg://...

    # ── ML Model ──────────────────────────────────────────────────────
    ml_model_path: str = "./ml_pipeline/artifacts/isolation_forest.pkl"
    ml_scaler_path: str = "./ml_pipeline/artifacts/scaler.pkl"
    ml_cold_start_score: float = 0.3  # fallback when model not trained yet

    # ── Risk Score Thresholds ─────────────────────────────────────────
    allow_threshold: float = 40.0   # score < 40  → ALLOW
    block_threshold: float = 75.0   # score >= 75 → BLOCK
                                    # else        → VERIFY

    # ── Rules Engine ──────────────────────────────────────────────────
    high_amount_multiplier: float = 3.0          # amount > avg * 3x → flag
    velocity_window_minutes: int = 60            # velocity check window
    velocity_spike_threshold: int = 5            # > 5 txns/hour → flag
    unusual_hour_start: int = 0                  # unusual hours: 00:00 to 05:00
    unusual_hour_end: int = 5
    multi_location_threshold: int = 2            # 2+ unique locs in 1h → flag

    # ── Feedback / Retraining ─────────────────────────────────────────
    retrain_feedback_threshold: int = 50         # retrain after N feedback records


# Singleton — import this everywhere
settings = Settings()
