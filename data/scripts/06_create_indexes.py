"""
Creates all MongoDB indexes (programmatic + prints instructions for Vector Search).
Run after 04_seed_mongo.py.

Run: python data/scripts/06_create_indexes.py
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.db.indexes import create_indexes

if __name__ == "__main__":
    asyncio.run(create_indexes())
