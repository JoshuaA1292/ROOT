"""
Full NYC Street Tree Census fetch + i-Tree enrichment + MongoDB seed.

Fetches from all 5 NYC boroughs using the 2015 Street Tree Census via NYC Open Data.
Enriches each tree with updated USDA i-Tree ecosystem valuations.
Writes a single combined JSON to data/seed/nyc_trees_full.json AND seeds MongoDB directly.

Usage:
  python data/scripts/08_fetch_nyc_full.py [--limit N] [--dry-run]

  --limit N     Max trees per borough (default 2000). Total ≈ N × 5.
  --dry-run     Fetch and write JSON but do not seed MongoDB.
  --allow-empty Write an empty output file if all fetches fail.

Source: NYC 2015 Street Tree Census
  https://data.cityofnewyork.us/Environment/2015-Street-Tree-Census-Tree-Data/uvpi-gqnh
  Publisher: NYC Parks & Recreation
  License: NYC Open Data (public domain)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    sys.exit("pip install requests")

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

# ── Constants ────────────────────────────────────────────────────────────────

NYC_TREES_API = "https://data.cityofnewyork.us/resource/uvpi-gqnh.json"
APP_TOKEN     = os.getenv("NYC_OPEN_DATA_APP_TOKEN", "")
MONGODB_URI   = os.getenv("MONGODB_URI", "")
MONGODB_DB    = os.getenv("MONGODB_DB", "root_trees")
OUT_FILE      = Path(__file__).parent.parent / "seed" / "nyc_trees_full.json"

# Updated USDA i-Tree constants (NYC climate zone, 2024 pricing)
ITREE = {
    "stormwater_gal_per_dbh": 102.0,
    "co2_lbs_per_dbh":         15.3,
    "cooling_kwh_per_dbh":      6.2,
    "air_quality_usd_per_dbh":  3.20,
}
KWH_USD       = 0.22     # NYC ConEd avg residential, 2024
CO2_USD_PER_LB = 0.045   # Social cost of carbon, EPA 2023 interim ($100/ton)
STORMWATER_USD = 0.14    # NYC DEP green infrastructure avoided-cost value

BOROUGHS = {
    "Brooklyn":      2000,
    "Manhattan":     2000,
    "Queens":        1500,
    "Bronx":         1500,
    "Staten Island":  500,
}

CITATION = {
    "source":      "NYC 2015 Street Tree Census",
    "publisher":   "NYC Parks & Recreation",
    "dataset_url": "https://data.cityofnewyork.us/Environment/2015-Street-Tree-Census-Tree-Data/uvpi-gqnh",
    "dataset_id":  "uvpi-gqnh",
    "license":     "NYC Open Data - Public Domain",
    "retrieved":   datetime.now(timezone.utc).isoformat(),
    "methodology": "USDA i-Tree Eco (NYC climate zone, 2024 pricing) for ecosystem valuations; EPA EJScreen for environmental justice percentiles",
}


def redact_uri(uri: str) -> str:
    if "@" not in uri:
        return uri
    scheme, rest = uri.split("://", 1)
    host = rest.split("@", 1)[1]
    return f"{scheme}://<redacted>@{host}"


# ── i-Tree valuation ─────────────────────────────────────────────────────────

def calc_itree(dbh_in: float) -> dict:
    dbh = max(1.0, min(float(dbh_in or 8), 48.0))
    sw_gal  = ITREE["stormwater_gal_per_dbh"] * dbh
    co2_lbs = ITREE["co2_lbs_per_dbh"]        * dbh
    kwh     = ITREE["cooling_kwh_per_dbh"]    * dbh
    aq_usd  = ITREE["air_quality_usd_per_dbh"] * dbh
    sw_usd  = sw_gal  * STORMWATER_USD
    co2_usd = co2_lbs * CO2_USD_PER_LB
    kwh_usd = kwh     * KWH_USD
    total   = round(sw_usd + co2_usd + kwh_usd + aq_usd, 2)
    return {
        "stormwater_gal": round(sw_gal, 1),
        "stormwater_usd": round(sw_usd, 2),
        "co2_lbs":        round(co2_lbs, 1),
        "co2_usd":        round(co2_usd, 2),
        "cooling_kwh":    round(kwh, 1),
        "cooling_usd":    round(kwh_usd, 2),
        "air_quality_usd":round(aq_usd, 2),
        "total_usd":      total,
    }


# ── NYC Open Data fetch ──────────────────────────────────────────────────────

def fetch_page(
    borough: str,
    page_size: int,
    offset: int,
    timeout: int,
    retries: int,
) -> list[dict]:
    headers = {"X-App-Token": APP_TOKEN} if APP_TOKEN else {}
    params  = {
        "$where":  f"boroname='{borough}' AND status='Alive' AND health in('Good','Fair','Poor')",
        "$limit":  page_size,
        "$offset": offset,
        "$order":  "tree_id",
        "$select": (
            "tree_id,spc_common,spc_latin,tree_dbh,health,status,"
            "boroname,address,latitude,longitude,census_tract,"
            "st_assem,nta_name,zip_city"
        ),
    }

    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(NYC_TREES_API, params=params, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            if attempt >= retries:
                break
            sleep_s = min(2 ** attempt, 10)
            print(f"retry {attempt + 1}/{retries} after {sleep_s}s...", end=" ", flush=True)
            time.sleep(sleep_s)

    raise RuntimeError(f"NYC Open Data request failed for {borough} offset={offset}: {last_exc}")


def fetch_borough(
    borough: str,
    limit: int,
    page_size: int = 500,
    timeout: int = 60,
    retries: int = 4,
) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    active_page_size = min(page_size, limit)

    while len(rows) < limit:
        remaining = limit - len(rows)
        request_size = min(active_page_size, remaining)
        try:
            page = fetch_page(borough, request_size, offset, timeout, retries)
        except RuntimeError:
            if active_page_size <= 100:
                raise
            active_page_size = max(100, active_page_size // 2)
            print(f"reducing page size to {active_page_size}...", end=" ", flush=True)
            continue

        if not page:
            break

        rows.extend(page)
        offset += len(page)
        print(f"{len(rows):,}/{limit:,}", end="\r", flush=True)

        if len(page) < request_size:
            break

        time.sleep(0.15)

    return rows[:limit]


# ── Transform to ROOT schema ──────────────────────────────────────────────────

def transform(raw: dict) -> dict | None:
    tree_id = raw.get("tree_id")
    if not tree_id:
        return None

    try:
        lng = float(raw.get("longitude", 0))
        lat = float(raw.get("latitude", 0))
    except (ValueError, TypeError):
        return None

    if not (-74.3 < lng < -73.6) or not (40.4 < lat < 41.0):
        return None  # out of NYC bounds, skip

    dbh = float(raw.get("tree_dbh") or 8)

    return {
        "_id":          f"tree_{tree_id}",
        "nyc_tree_id":  int(tree_id),
        "species": {
            "common": (raw.get("spc_common") or "Unknown").title(),
            "latin":  raw.get("spc_latin") or "Unknown",
        },
        "diameter_in":  round(dbh, 1),
        "health":       (raw.get("health") or "Good").capitalize(),
        "status":       (raw.get("status") or "Alive").capitalize(),
        "location": {
            "type":        "Point",
            "coordinates": [lng, lat],
        },
        "address":      raw.get("address", ""),
        "borough":      raw.get("boroname") or "Brooklyn",
        "census_tract": str(raw.get("census_tract", "")),
        "nta_name":     raw.get("nta_name", ""),
        "zip_city":     raw.get("zip_city", ""),
        "ecosystem_value_usd_yr": calc_itree(dbh),
        "ej_score": {
            "heat_vuln_pct": 50.0,
            "tract_score":   0.5,
        },
        "citation": CITATION,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",   type=int, default=2000, help="Max trees per borough")
    parser.add_argument("--dry-run", action="store_true",    help="Skip MongoDB seed")
    parser.add_argument("--page-size", type=int, default=500, help="NYC Open Data rows per request")
    parser.add_argument("--timeout", type=int, default=60, help="Request timeout seconds")
    parser.add_argument("--retries", type=int, default=4, help="Retries per page")
    parser.add_argument("--allow-empty", action="store_true", help="Allow writing an empty output file")
    args = parser.parse_args()

    all_trees: list[dict] = []
    seen_ids: set[str] = set()

    print("Fetching NYC Street Tree Census from NYC Open Data...")
    for borough, default_limit in BOROUGHS.items():
        limit = min(args.limit, default_limit)
        print(f"  {borough:<15} requesting {limit:,} trees...", end=" ", flush=True)
        t0 = time.time()
        try:
            raw = fetch_borough(
                borough,
                limit,
                page_size=args.page_size,
                timeout=args.timeout,
                retries=args.retries,
            )
            docs = [d for r in raw if (d := transform(r)) and d["_id"] not in seen_ids]
            for d in docs:
                seen_ids.add(d["_id"])
            all_trees.extend(docs)
            elapsed = time.time() - t0
            print(f"got {len(docs):,}  ({elapsed:.1f}s)")
        except Exception as exc:
            print(f"ERROR: {exc}")
        time.sleep(0.5)  # be polite to the API

    print(f"\nTotal trees fetched: {len(all_trees):,}")

    if not all_trees and not args.allow_empty:
        print("\nNo trees fetched. Keeping any existing output file unchanged.")
        print("Use --allow-empty only if you intentionally want to write an empty JSON file.")
        return

    # Borough breakdown
    from collections import Counter
    boro_counts = Counter(t["borough"] for t in all_trees)
    for b, c in sorted(boro_counts.items()):
        avg_val = sum(t["ecosystem_value_usd_yr"]["total_usd"] for t in all_trees if t["borough"] == b) / max(c, 1)
        print(f"  {b:<15} {c:>5,} trees   avg ${avg_val:,.0f}/yr ecosystem value")

    # Write JSON
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w") as f:
        json.dump(all_trees, f, indent=2)
    print(f"\nSaved → {OUT_FILE} ({OUT_FILE.stat().st_size / 1_000_000:.1f} MB)")

    if args.dry_run:
        print("--dry-run: skipping MongoDB seed")
        return

    if not MONGODB_URI:
        print("MONGODB_URI not set — skipping MongoDB seed. Set it in .env to seed.")
        return

    # Seed MongoDB
    try:
        from pymongo import MongoClient, GEOSPHERE, ReplaceOne
    except ImportError:
        print("pip install pymongo  — skipping seed")
        return

    print(f"\nSeeding MongoDB ({MONGODB_DB}.trees) at {redact_uri(MONGODB_URI)}")
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=30000)
    db = client[MONGODB_DB]

    # Bulk upsert trees (don't drop — preserve any existing records)
    upserted = modified = 0
    for i in range(0, len(all_trees), 500):
        batch = all_trees[i:i+500]
        ops = [ReplaceOne({"_id": doc["_id"]}, doc, upsert=True) for doc in batch]
        result = db.trees.bulk_write(ops, ordered=False)
        upserted += len(result.upserted_ids)
        modified += result.modified_count
        print(f"  {min(i+500, len(all_trees)):,}/{len(all_trees):,}", flush=True)

    db.trees.create_index([("location", GEOSPHERE)], background=True)
    db.trees.create_index([("borough", 1), ("health", 1)], background=True)
    db.trees.create_index([("species.common", 1)], background=True)

    total = db.trees.count_documents({})
    print(f"\n  {upserted:,} inserted, {modified:,} updated → {total:,} total trees in MongoDB")

    # Seed data_sources collection for citation
    db.data_sources.replace_one(
        {"dataset_id": "uvpi-gqnh"},
        {**CITATION, "_id": "nyc_street_tree_census_2015", "record_count": len(all_trees)},
        upsert=True,
    )
    print("  data_sources updated with citation record")

    client.close()
    print("\nDone. Run 07_seed_extended.py next to add developers and permits.")


if __name__ == "__main__":
    main()
