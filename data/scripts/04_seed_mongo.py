"""
Seeds MongoDB Atlas with all ROOT collections.
Run AFTER scripts 01-03 have been executed.

Prerequisites:
  - MONGODB_URI set in environment or .env file
  - data/raw/nyc_tree_ej.json exists (or falls back to data/seed/trees.json)
  - data/seed/permits.json, developers.json, planting_records.json, precedents.json,
    city_policies.json exist

Run: python data/scripts/04_seed_mongo.py
"""
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient, GEOSPHERE, ASCENDING

load_dotenv(Path(__file__).parent.parent.parent / ".env")

MONGODB_URI = os.environ.get("MONGODB_URI")
MONGODB_DB = os.environ.get("MONGODB_DB", "root_trees")

if not MONGODB_URI:
    sys.exit("ERROR: MONGODB_URI not set. Copy .env.example to .env and fill in your Atlas URI.")

DATA_DIR = Path(__file__).parent.parent

# Prefer pipeline-enriched data; fall back to pre-built seed JSON
TREES_FILE = DATA_DIR / "raw" / "nyc_tree_ej.json"
if not TREES_FILE.exists():
    TREES_FILE = DATA_DIR / "seed" / "trees.json"
    print(f"Using pre-built seed: {TREES_FILE}")


def load_json(path: Path) -> list:
    with open(path) as f:
        return json.load(f)


def transform_tree(raw: dict, index: int) -> dict:
    """Convert NYC Open Data format → ROOT tree document."""
    tree_id = raw.get("tree_id") or raw.get("nyc_tree_id") or f"synthetic_{index}"
    return {
        "_id": f"tree_{tree_id}",
        "nyc_tree_id": int(str(tree_id).replace("synthetic_", "0") or 0),
        "species": {
            "common": raw.get("spc_common") or raw.get("species", {}).get("common", "Unknown"),
            "latin": raw.get("spc_latin") or raw.get("species", {}).get("latin", "Unknown"),
        },
        "diameter_in": float(raw.get("tree_dbh") or raw.get("diameter_in") or 8),
        "health": raw.get("health", "Good"),
        "status": raw.get("status", "Alive"),
        "location": {
            "type": "Point",
            "coordinates": [
                float(raw.get("longitude") or raw.get("location", {}).get("coordinates", [-73.95])[0]),
                float(raw.get("latitude") or raw.get("location", {}).get("coordinates", [40.65, 40.65])[1]),
            ],
        },
        "address": raw.get("address", ""),
        "borough": raw.get("boroname") or raw.get("borough", "Brooklyn"),
        "census_tract": str(raw.get("census_tract", "")),
        "ecosystem_value_usd_yr": raw.get("ecosystem_value_usd_yr", {
            "stormwater_gal": 0, "stormwater_usd": 0,
            "co2_lbs": 0, "co2_usd": 0,
            "cooling_kwh": 0, "cooling_usd": 0,
            "air_quality_usd": 0, "total_usd": 0,
        }),
        "ej_score": raw.get("ej_score", {"heat_vuln_pct": 50.0, "tract_score": 0.5}),
        "planted_year": raw.get("planted_year"),
        "last_inspection": raw.get("last_inspection"),
    }


def seed_collection(db, name: str, docs: list, id_field: str = "_id") -> None:
    col = db[name]
    col.drop()
    if docs:
        col.insert_many(docs)
    print(f"  {name}: inserted {len(docs)} documents")


def main():
    print(f"Connecting to MongoDB: {MONGODB_URI[:40]}...")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB]

    # Trees
    print("Seeding trees...")
    raw_trees = load_json(TREES_FILE)
    trees = [transform_tree(t, i) for i, t in enumerate(raw_trees)]
    seed_collection(db, "trees", trees)

    # Permits — prefer v2 (15 permits across all boroughs) if available
    permits_file = DATA_DIR / "seed" / "permits_v2.json"
    if not permits_file.exists():
        permits_file = DATA_DIR / "seed" / "permits.json"
    if permits_file.exists():
        seed_collection(db, "permits", load_json(permits_file))

    # Developers — prefer v2 (11 developers) if available
    developers_file = DATA_DIR / "seed" / "developers_v2.json"
    if not developers_file.exists():
        developers_file = DATA_DIR / "seed" / "developers.json"
    if developers_file.exists():
        seed_collection(db, "developers", load_json(developers_file))

    # Replacement planting / inspection records — prefer v2
    planting_file = DATA_DIR / "seed" / "planting_records_v2.json"
    if not planting_file.exists():
        planting_file = DATA_DIR / "seed" / "planting_records.json"
    if planting_file.exists():
        seed_collection(db, "planting_records", load_json(planting_file))

    # Precedents (embeddings added by script 05)
    precedents_file = DATA_DIR / "seed" / "precedents.json"
    if precedents_file.exists():
        seed_collection(db, "precedents", load_json(precedents_file))

    # City policies
    policies_file = DATA_DIR / "seed" / "city_policies.json"
    if policies_file.exists():
        seed_collection(db, "city_policies", load_json(policies_file))

    # Data sources / citations
    data_sources_file = DATA_DIR / "seed" / "data_sources.json"
    if data_sources_file.exists():
        seed_collection(db, "data_sources", load_json(data_sources_file))

    # Indexes
    print("Creating indexes...")
    db.trees.create_index([("location", GEOSPHERE)])
    db.trees.create_index([("borough", ASCENDING), ("status", ASCENDING)])
    db.permits.create_index([("center", GEOSPHERE)])
    db.permits.create_index([("status", ASCENDING), ("comment_deadline", ASCENDING)])
    db.planting_records.create_index([("developer_id", ASCENDING)])
    db.planting_records.create_index([("permit_id", ASCENDING)])
    db.briefings.create_index([("permit_id", ASCENDING)])
    db.briefing_jobs.create_index([("status", ASCENDING), ("created_at", ASCENDING)])

    print(f"\nDone. Database '{MONGODB_DB}' seeded successfully.")
    print("Next: run script 05 to add vector embeddings to precedents.")
    print("Then: create Atlas Vector Search index via the Atlas UI.")


if __name__ == "__main__":
    main()
