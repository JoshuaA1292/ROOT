"""Run once after seeding to create all required MongoDB indexes."""
import asyncio
from pymongo import ASCENDING, GEOSPHERE
from app.db.client import get_db


async def create_indexes() -> None:
    db = get_db()

    # trees: 2dsphere for geospatial queries + compound filter index
    await db.trees.create_index([("location", GEOSPHERE)])
    await db.trees.create_index([("borough", ASCENDING), ("status", ASCENDING)])

    # permits: 2dsphere on center + status/deadline compound
    await db.permits.create_index([("center", GEOSPHERE)])
    await db.permits.create_index([("status", ASCENDING), ("comment_deadline", ASCENDING)])

    # developers: lookup by name / linked entities
    await db.developers.create_index([("name", ASCENDING)])

    # briefings: lookup by permit
    await db.briefings.create_index([("permit_id", ASCENDING)])
    await db.briefings.create_index([("status", ASCENDING)])

    # NOTE: Atlas Vector Search index on precedents.embedding must be created
    # via the Atlas UI or Atlas CLI — the MongoDB driver cannot create vector indexes.
    # Index name: "precedents_vector_index"
    # Type: vectorSearch, dimensions: 768, similarity: cosine
    # Field: "embedding"
    print("All programmatic indexes created.")
    print(
        "ACTION REQUIRED: Create Atlas Vector Search index on precedents.embedding via Atlas UI.\n"
        "  Name: precedents_vector_index\n"
        "  Field: embedding\n"
        "  Dimensions: 768\n"
        "  Similarity: cosine"
    )


if __name__ == "__main__":
    asyncio.run(create_indexes())
