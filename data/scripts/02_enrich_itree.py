"""
Enriches raw NYC tree data with i-Tree ecosystem valuations.
Uses a lookup table derived from i-Tree Benefits data for NYC's climate zone.
No API key needed — these are published reference values from the USDA Forest Service.

Inputs:  data/raw/nyc_tree_sample.json
Outputs: data/raw/nyc_tree_enriched.json

Run: python data/scripts/02_enrich_itree.py
"""
import json
import os

INPUT = os.path.join(os.path.dirname(__file__), "../raw/nyc_tree_sample.json")
OUTPUT = os.path.join(os.path.dirname(__file__), "../raw/nyc_tree_enriched.json")

# i-Tree reference values per diameter class for NYC (Humid Subtropical climate zone)
# Source: USDA Forest Service i-Tree Streets methodology
# Values are annual unless noted. Scaled linearly by DBH for simplicity.
ITREE_PER_DBH_INCH = {
    "stormwater_gal": 102,    # gallons per inch DBH per year (USDA i-Tree Streets)
    "co2_lbs": 15.3,          # lbs CO2 per inch DBH per year
    "cooling_kwh": 6.2,       # kWh cooling energy saved per inch DBH per year
    "air_quality_usd": 3.20,  # USD per inch DBH per year (PM2.5 + O3 + NO2, NYC 2023)
}

KWH_TO_USD = 0.22           # NYC ConEd avg residential rate (2024)
CO2_STORMWATER_RATIO = 0.14  # $/gallon — NYC green infra avoided-cost value (NYC DEP 2023)
CO2_USD_PER_LB = 0.045       # social cost of carbon at $100/ton (EPA 2023 interim)


def enrich(tree: dict) -> dict:
    dbh = float(tree.get("tree_dbh", 8) or 8)
    dbh = max(1.0, min(dbh, 40.0))  # clamp

    stormwater_gal = ITREE_PER_DBH_INCH["stormwater_gal"] * dbh
    co2_lbs = ITREE_PER_DBH_INCH["co2_lbs"] * dbh
    cooling_kwh = ITREE_PER_DBH_INCH["cooling_kwh"] * dbh
    air_quality_usd = ITREE_PER_DBH_INCH["air_quality_usd"] * dbh

    stormwater_usd = stormwater_gal * CO2_STORMWATER_RATIO
    co2_usd = co2_lbs * CO2_USD_PER_LB
    cooling_usd = cooling_kwh * KWH_TO_USD
    total_usd = stormwater_usd + co2_usd + cooling_usd + air_quality_usd

    tree["ecosystem_value_usd_yr"] = {
        "stormwater_gal": round(stormwater_gal, 1),
        "stormwater_usd": round(stormwater_usd, 2),
        "co2_lbs": round(co2_lbs, 1),
        "co2_usd": round(co2_usd, 2),
        "cooling_kwh": round(cooling_kwh, 1),
        "cooling_usd": round(cooling_usd, 2),
        "air_quality_usd": round(air_quality_usd, 2),
        "total_usd": round(total_usd, 2),
    }
    return tree


def main():
    with open(INPUT) as f:
        trees = json.load(f)

    enriched = [enrich(t) for t in trees]

    with open(OUTPUT, "w") as f:
        json.dump(enriched, f, indent=2)
    print(f"Enriched {len(enriched)} trees → {OUTPUT}")


if __name__ == "__main__":
    main()
