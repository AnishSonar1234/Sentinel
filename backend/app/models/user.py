"""
app/models/user.py
──────────────────
User ORM model.
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
