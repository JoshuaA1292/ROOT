from __future__ import annotations

from typing import Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings


def bson_clean(obj: Any) -> Any:
    """
    Recursively convert any BSON ObjectId (and other non-JSON-serializable BSON
    types) to their string equivalents so FastAPI can serialize them cleanly.
    Call this on every raw MongoDB document before returning it from an endpoint.
    """
    try:
        from bson import ObjectId, Decimal128
    except ImportError:
        return obj

    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, Decimal128):
        return float(str(obj))
    if isinstance(obj, dict):
        return {k: bson_clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [bson_clean(item) for item in obj]
    return obj

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            settings.mongodb_uri,
            # Fail fast instead of hanging for 30 s — gives a clear error immediately.
            serverSelectionTimeoutMS=8_000,
            connectTimeoutMS=8_000,
            socketTimeoutMS=20_000,
        )
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[settings.mongodb_db]


async def ping() -> bool:
    """Return True if Atlas is reachable; False otherwise. Never raises."""
    try:
        await get_client().admin.command("ping")
        return True
    except Exception:
        return False


async def close_client() -> None:
    global _client
    if _client:
        _client.close()
        _client = None
