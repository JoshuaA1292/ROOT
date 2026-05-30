"""
Extended seeding script — seeds v2 data (11 developers, 15 permits, 14 planting records).
Run after 04_seed_mongo.py has run successfully.

Usage: python data/scripts/07_seed_extended.py
"""
import json
import os
import sys
from datetime import datetime

try:
    from pymongo import MongoClient, GEOSPHERE
    from pymongo.errors import DuplicateKeyError
    from dotenv import load_dotenv
except ImportError:
    print("Install: pip install pymongo python-dotenv")
    sys.exit(1)

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB  = os.getenv("MONGODB_DB",  "root_trees")

SEED_DIR = os.path.join(os.path.dirname(__file__), "../seed")


def redact_uri(uri: str) -> str:
    if "@" not in uri:
        return uri
    scheme, rest = uri.split("://", 1)
    host = rest.split("@", 1)[1]
    return f"{scheme}://<redacted>@{host}"


def load_json(filename: str) -> list:
    path = os.path.join(SEED_DIR, filename)
    with open(path) as f:
        return json.load(f)


def upsert_collection(db, collection_name: str, docs: list, id_field: str = "_id") -> tuple[int, int]:
    inserted, updated = 0, 0
    col = db[collection_name]
    for doc in docs:
        try:
            col.insert_one(doc)
            inserted += 1
        except DuplicateKeyError:
            col.replace_one({id_field: doc[id_field]}, doc)
            updated += 1
    return inserted, updated


def main():
    print(f"Connecting to MongoDB at {redact_uri(MONGODB_URI)}")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB]
    print(f"Using database: {MONGODB_DB}\n")

    # ── Developers v2 ──────────────────────────────────────
    developers = load_json("developers_v2.json")
    ins, upd = upsert_collection(db, "developers", developers)
    print(f"developers_v2: {ins} inserted, {upd} updated ({len(developers)} total)")

    # ── Permits v2 ─────────────────────────────────────────
    permits = load_json("permits_v2.json")
    ins, upd = upsert_collection(db, "permits", permits)
    print(f"permits_v2:    {ins} inserted, {upd} updated ({len(permits)} total)")

    # ── Planting records v2 ────────────────────────────────
    records = load_json("planting_records_v2.json")
    # planting_records don't have a top-level _id, use permit_id as key
    col = db["planting_records"]
    ins, upd = 0, 0
    for rec in records:
        result = col.replace_one({"permit_id": rec["permit_id"]}, rec, upsert=True)
        if result.upserted_id:
            ins += 1
        else:
            upd += 1
    print(f"planting_v2:   {ins} inserted, {upd} updated ({len(records)} total)")

    # ── Ensure geospatial index on permits ─────────────────
    db.permits.create_index([("center", GEOSPHERE)], background=True)
    print("\nGeospatial index on permits.center: ensured")

    # ── Summary ────────────────────────────────────────────
    print("\n── Collection counts ───────────────────────────")
    for col_name in ["trees", "developers", "permits", "planting_records", "precedents", "city_policies"]:
        count = db[col_name].count_documents({})
        print(f"  {col_name:<20} {count:>6} documents")

    # ── Enforcement flags ──────────────────────────────────
    # Flag developers below 85% compliance who have open permits
    print("\n── Enforcement flags ────────────────────────────")
    bad_devs = list(db.developers.find({"compliance_rate": {"$lt": 0.85}}))
    for dev in bad_devs:
        open_permits = db.permits.count_documents({"developer_id": dev["_id"], "status": "open_for_comment"})
        if open_permits > 0:
            pct = round(dev["compliance_rate"] * 100)
            print(f"  ⚠  {dev['name'][:35]:<35} {pct}% compliance — {open_permits} open permit(s) FLAGGED")

    client.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
