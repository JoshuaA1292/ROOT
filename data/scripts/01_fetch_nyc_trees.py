"""
Fetches a curated sample of ~1000 NYC street trees from the NYC Open Data API
(2015 Street Tree Census). Filters for healthy/alive trees in Brooklyn and Manhattan
to maximize demo impact. Saves to data/raw/nyc_tree_sample.json.

Run: python data/scripts/01_fetch_nyc_trees.py
"""
import json
import os
import sys
import requests

OUTPUT = os.path.join(os.path.dirname(__file__), "../raw/nyc_tree_sample.json")
LIMIT = 1000
# NYC Open Data: 2015 Street Tree Census
API_URL = "https://data.cityofnewyork.us/resource/uvpi-gqnh.json"

PARAMS = {
    "$limit": LIMIT,
    "$where": "status='Alive' AND health IN('Good','Fair') AND boroname IN('Brooklyn','Manhattan')",
    "$select": "tree_id,spc_common,spc_latin,tree_dbh,health,status,boroname,nta,census_tract,latitude,longitude,address",
    "$order": "tree_dbh DESC",  # largest trees first = most ecosystem value
}

# Use app token if set (higher rate limits)
app_token = os.environ.get("NYC_OPEN_DATA_APP_TOKEN")
if app_token:
    PARAMS["$$app_token"] = app_token


def fetch():
    print(f"Fetching {LIMIT} trees from NYC Open Data...")
    resp = requests.get(API_URL, params=PARAMS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    print(f"Got {len(data)} records.")

    # Filter rows missing coordinates
    valid = [r for r in data if r.get("latitude") and r.get("longitude")]
    print(f"{len(valid)} records with valid coordinates.")

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(valid, f, indent=2)
    print(f"Saved to {OUTPUT}")


if __name__ == "__main__":
    fetch()
