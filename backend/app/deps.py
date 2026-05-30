"""FastAPI dependency injection helpers."""
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.client import get_db as _get_db


def get_db() -> AsyncIOMotorDatabase:
    return _get_db()
