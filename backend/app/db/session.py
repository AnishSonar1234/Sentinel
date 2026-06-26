"""
app/db/session.py
─────────────────
Synchronous SQLAlchemy engine + session factory.

Default: SQLite (zero setup, perfect for demo).

To switch to Supabase PostgreSQL, change DATABASE_URL in .env to:
    postgresql+psycopg2://postgres:<pw>@db.<ref>.supabase.co:5432/postgres
And install: pip install psycopg2-binary
Everything else stays the same.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config.settings import settings

# SQLite needs check_same_thread=False for FastAPI's thread handling
_connect_args = (
    {"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    FastAPI dependency — yields a DB session per request, closes on exit.

    Usage in route:
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
