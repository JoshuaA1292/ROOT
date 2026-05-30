"""
09_wipe_and_reseed.py

1. Wipes all filed cases: briefings, notifications, outcomes, briefing_jobs
2. Seeds 30 new permits spread across all 5 NYC boroughs
3. Seeds 150 trees clustered near the new permits so coalition analysis finds them

Usage:
  cd /path/to/ROOT
  python data/scripts/09_wipe_and_reseed.py
"""
import json
import math
import os
import random
import sys
from datetime import datetime, timezone

try:
    from pymongo import MongoClient, GEOSPHERE
    from pymongo.errors import DuplicateKeyError
    from dotenv import load_dotenv
except ImportError:
    print("Install: pip install pymongo python-dotenv")
    sys.exit(1)

load_dotenv(os.path.join(os.path.dirname(__file__), "../../backend/.env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB  = os.getenv("MONGODB_DB",  "root_trees")

random.seed(42)

# ── Developer IDs (must match what's in the DB) ───────────────────────────────
DEV_IDS = [
    "dev_atlas_holdings",
    "dev_prospect_realty",
    "dev_brooklyn_build",
    "dev_sunset_park",
    "dev_crown_heights",
    "dev_flatbush_props",
    "dev_bk_urban",
    "dev_williamsburg_heights",
    "dev_park_slope",
    "dev_greenpoint_grp",
    "dev_ridgewood_realty",
]

SPECIES = [
    ("Honeylocust",        "Gleditsia triacanthos"),
    ("London Planetree",   "Platanus × acerifolia"),
    ("Norway Maple",       "Acer platanoides"),
    ("Callery Pear",       "Pyrus calleryana"),
    ("Pin Oak",            "Quercus palustris"),
    ("Ginkgo",             "Ginkgo biloba"),
    ("Littleleaf Linden",  "Tilia cordata"),
    ("Red Maple",          "Acer rubrum"),
    ("Japanese Zelkova",   "Zelkova serrata"),
    ("Sweetgum",           "Liquidambar styraciflua"),
    ("American Elm",       "Ulmus americana"),
    ("Green Ash",          "Fraxinus pennsylvanica"),
    ("Tulip Tree",         "Liriodendron tulipifera"),
    ("Silver Maple",       "Acer saccharinum"),
    ("Eastern Redbud",     "Cercis canadensis"),
]

PROJECT_TYPES = [
    "mixed_use_tower",
    "residential_tower",
    "commercial_renovation",
    "industrial_conversion",
    "hotel_development",
    "office_tower",
    "parking_structure",
]

REMOVAL_REASONS = [
    "Foundation excavation requires clearing street trees along property boundary.",
    "Root systems conflict with planned below-grade parking structure.",
    "Utility trench for new infrastructure conflicts with mature tree root zones.",
    "Building footprint expansion requires removal of trees obstructing facade alignment.",
    "Loading dock widening — mature trees block required truck clearance.",
    "Sidewalk vault construction incompatible with existing root ball depth.",
    "Street-level retail expansion conflicts with existing canopy overhang.",
    "Trees within crane swing radius for planned high-rise construction.",
    "Underground stormwater management system conflicts with root systems.",
    "Fire egress lane widening requires removal of mature street trees.",
    "HVAC unit placement conflicts with tree canopy above mechanical level.",
    "Hotel valet drop-off lane conflicts with two mature Oaks on block face.",
    "Solar installation on roof requires removal of shading trees below.",
    "Subsurface piping replacement conflicts with deep root network of old-growth trees.",
    "ADA-compliant ramp construction requires removal of trees blocking grade transition.",
]

# ── 30 new permits across all 5 boroughs ──────────────────────────────────────
NEW_PERMITS = [
    # Manhattan
    {
        "_id": "permit_2026_1001",
        "developer_id": "dev_atlas_holdings",
        "filed_date": "2026-05-28",
        "address": "432 W 42nd St, Manhattan, NY 10036",
        "project_type": "mixed_use_tower",
        "removal_radius_m": 90,
        "center": {"type": "Point", "coordinates": [-73.9944, 40.7587]},
        "stated_reason": "Foundation excavation for 22-story mixed-use tower. 7 mature trees within building footprint.",
        "promised_replacements": 14,
        "comment_deadline": "2026-07-10",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1002",
        "developer_id": "dev_brooklyn_build",
        "filed_date": "2026-05-20",
        "address": "560 W 125th St, Manhattan, NY 10027",
        "project_type": "residential_tower",
        "removal_radius_m": 70,
        "center": {"type": "Point", "coordinates": [-73.9558, 40.8134]},
        "stated_reason": "Affordable housing tower. Root systems of 5 mature London Planetrees conflict with utility trench.",
        "promised_replacements": 10,
        "comment_deadline": "2026-07-15",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1003",
        "developer_id": "dev_prospect_realty",
        "filed_date": "2026-05-22",
        "address": "285 Madison Ave, Manhattan, NY 10017",
        "project_type": "office_tower",
        "removal_radius_m": 60,
        "center": {"type": "Point", "coordinates": [-73.9818, 40.7515]},
        "stated_reason": "Office tower lobby expansion. Sidewalk vault construction incompatible with root ball depth.",
        "promised_replacements": 6,
        "comment_deadline": "2026-07-20",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1004",
        "developer_id": "dev_atlas_holdings",
        "filed_date": "2026-05-25",
        "address": "170 Amsterdam Ave, Manhattan, NY 10023",
        "project_type": "hotel_development",
        "removal_radius_m": 80,
        "center": {"type": "Point", "coordinates": [-73.9845, 40.7740]},
        "stated_reason": "Boutique hotel valet lane conflicts with 4 mature Ginkgos on block face.",
        "promised_replacements": 8,
        "comment_deadline": "2026-07-25",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1005",
        "developer_id": "dev_crown_heights",
        "filed_date": "2026-05-27",
        "address": "88 Fulton St, Manhattan, NY 10038",
        "project_type": "commercial_renovation",
        "removal_radius_m": 50,
        "center": {"type": "Point", "coordinates": [-74.0086, 40.7079]},
        "stated_reason": "Ground-floor retail buildout. ADA ramp conflicts with two Norway Maples.",
        "promised_replacements": 4,
        "comment_deadline": "2026-07-30",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1006",
        "developer_id": "dev_flatbush_props",
        "filed_date": "2026-05-29",
        "address": "344 W 72nd St, Manhattan, NY 10023",
        "project_type": "residential_tower",
        "removal_radius_m": 75,
        "center": {"type": "Point", "coordinates": [-73.9814, 40.7785]},
        "stated_reason": "16-story residential conversion. Crane swing radius requires removal of 3 mature elms.",
        "promised_replacements": 9,
        "comment_deadline": "2026-08-05",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    # Bronx
    {
        "_id": "permit_2026_1007",
        "developer_id": "dev_bk_urban",
        "filed_date": "2026-05-15",
        "address": "2199 Grand Concourse, Bronx, NY 10453",
        "project_type": "mixed_use_tower",
        "removal_radius_m": 85,
        "center": {"type": "Point", "coordinates": [-73.9217, 40.8567]},
        "stated_reason": "Grand Concourse mixed-use development. 6 mature London Planetrees within 85ft of building.",
        "promised_replacements": 12,
        "comment_deadline": "2026-07-12",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1008",
        "developer_id": "dev_sunset_park",
        "filed_date": "2026-05-18",
        "address": "891 Westchester Ave, Bronx, NY 10459",
        "project_type": "commercial_renovation",
        "removal_radius_m": 55,
        "center": {"type": "Point", "coordinates": [-73.8936, 40.8233]},
        "stated_reason": "Retail plaza renovation. Loading bay expansion conflicts with 3 mature Red Maples.",
        "promised_replacements": 6,
        "comment_deadline": "2026-07-18",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1009",
        "developer_id": "dev_prospect_realty",
        "filed_date": "2026-05-21",
        "address": "3440 Jerome Ave, Bronx, NY 10467",
        "project_type": "residential_tower",
        "removal_radius_m": 70,
        "center": {"type": "Point", "coordinates": [-73.8922, 40.8786]},
        "stated_reason": "10-story residential tower. Subsurface utility work conflicts with 4 old-growth Pin Oaks.",
        "promised_replacements": 8,
        "comment_deadline": "2026-07-22",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1010",
        "developer_id": "dev_atlas_holdings",
        "filed_date": "2026-05-24",
        "address": "558 E 187th St, Bronx, NY 10458",
        "project_type": "parking_structure",
        "removal_radius_m": 60,
        "center": {"type": "Point", "coordinates": [-73.8919, 40.8583]},
        "stated_reason": "5-level parking structure. Root systems of existing Norway Maples conflict with pile foundations.",
        "promised_replacements": 7,
        "comment_deadline": "2026-07-28",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    # Queens
    {
        "_id": "permit_2026_1011",
        "developer_id": "dev_williamsburg_heights",
        "filed_date": "2026-05-10",
        "address": "37-10 Junction Blvd, Queens, NY 11372",
        "project_type": "mixed_use_tower",
        "removal_radius_m": 80,
        "center": {"type": "Point", "coordinates": [-73.8898, 40.7454]},
        "stated_reason": "14-story transit-oriented development. Block face has 8 mature Callery Pears within building footprint.",
        "promised_replacements": 16,
        "comment_deadline": "2026-07-08",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1012",
        "developer_id": "dev_park_slope",
        "filed_date": "2026-05-14",
        "address": "144-20 Jamaica Ave, Queens, NY 11435",
        "project_type": "commercial_renovation",
        "removal_radius_m": 50,
        "center": {"type": "Point", "coordinates": [-73.8050, 40.7023]},
        "stated_reason": "Strip mall expansion. Three mature Zelkovas conflict with new stormwater system.",
        "promised_replacements": 5,
        "comment_deadline": "2026-07-14",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1013",
        "developer_id": "dev_greenpoint_grp",
        "filed_date": "2026-05-17",
        "address": "82-11 Lefferts Blvd, Queens, NY 11418",
        "project_type": "residential_tower",
        "removal_radius_m": 65,
        "center": {"type": "Point", "coordinates": [-73.8360, 40.6953]},
        "stated_reason": "12-story residential development. Sidewalk vault below 4 mature Honey Locusts.",
        "promised_replacements": 8,
        "comment_deadline": "2026-07-20",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1014",
        "developer_id": "dev_ridgewood_realty",
        "filed_date": "2026-05-19",
        "address": "61-15 Woodhaven Blvd, Queens, NY 11374",
        "project_type": "hotel_development",
        "removal_radius_m": 75,
        "center": {"type": "Point", "coordinates": [-73.8636, 40.7191]},
        "stated_reason": "Airport hotel development. HVAC placement conflicts with mature canopy on south face.",
        "promised_replacements": 10,
        "comment_deadline": "2026-07-25",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1015",
        "developer_id": "dev_bk_urban",
        "filed_date": "2026-05-23",
        "address": "34-02 Steinway St, Queens, NY 11101",
        "project_type": "office_tower",
        "removal_radius_m": 70,
        "center": {"type": "Point", "coordinates": [-73.9204, 40.7560]},
        "stated_reason": "18-story office tower. Foundation depth conflicts with root systems of 5 mature Ginkgos.",
        "promised_replacements": 10,
        "comment_deadline": "2026-07-30",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1016",
        "developer_id": "dev_atlas_holdings",
        "filed_date": "2026-05-26",
        "address": "108-22 Queens Blvd, Queens, NY 11375",
        "project_type": "mixed_use_tower",
        "removal_radius_m": 90,
        "center": {"type": "Point", "coordinates": [-73.8456, 40.7219]},
        "stated_reason": "25-story mixed-use tower on Queens Blvd corridor. 9 mature Red Maples within building envelope.",
        "promised_replacements": 18,
        "comment_deadline": "2026-08-05",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    # Staten Island
    {
        "_id": "permit_2026_1017",
        "developer_id": "dev_sunset_park",
        "filed_date": "2026-05-12",
        "address": "2655 Richmond Ave, Staten Island, NY 10314",
        "project_type": "commercial_renovation",
        "removal_radius_m": 60,
        "center": {"type": "Point", "coordinates": [-74.1496, 40.5879]},
        "stated_reason": "Big-box retail parking expansion. 4 mature Pin Oaks within expansion zone.",
        "promised_replacements": 6,
        "comment_deadline": "2026-07-10",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1018",
        "developer_id": "dev_brooklyn_build",
        "filed_date": "2026-05-16",
        "address": "4040 Hylan Blvd, Staten Island, NY 10308",
        "project_type": "residential_tower",
        "removal_radius_m": 70,
        "center": {"type": "Point", "coordinates": [-74.1524, 40.5430]},
        "stated_reason": "Suburban residential development. Utility corridor conflicts with 6 mature trees.",
        "promised_replacements": 9,
        "comment_deadline": "2026-07-16",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1019",
        "developer_id": "dev_prospect_realty",
        "filed_date": "2026-05-20",
        "address": "1150 Forest Ave, Staten Island, NY 10310",
        "project_type": "parking_structure",
        "removal_radius_m": 55,
        "center": {"type": "Point", "coordinates": [-74.1305, 40.6254]},
        "stated_reason": "3-story parking garage. Pile foundations conflict with root network of 3 mature Sweetgums.",
        "promised_replacements": 5,
        "comment_deadline": "2026-07-22",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1020",
        "developer_id": "dev_crown_heights",
        "filed_date": "2026-05-24",
        "address": "880 Richmond Terrace, Staten Island, NY 10301",
        "project_type": "mixed_use_tower",
        "removal_radius_m": 80,
        "center": {"type": "Point", "coordinates": [-74.0969, 40.6449]},
        "stated_reason": "Waterfront mixed-use development. 5 mature American Elms within 80ft of building footprint.",
        "promised_replacements": 12,
        "comment_deadline": "2026-07-28",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    # Brooklyn (additional)
    {
        "_id": "permit_2026_1021",
        "developer_id": "dev_greenpoint_grp",
        "filed_date": "2026-05-11",
        "address": "168 Nassau Ave, Brooklyn, NY 11222",
        "project_type": "residential_tower",
        "removal_radius_m": 65,
        "center": {"type": "Point", "coordinates": [-73.9510, 40.7234]},
        "stated_reason": "10-story residential building. Root systems of 4 mature trees conflict with underground parking.",
        "promised_replacements": 8,
        "comment_deadline": "2026-07-10",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1022",
        "developer_id": "dev_ridgewood_realty",
        "filed_date": "2026-05-13",
        "address": "940 Myrtle Ave, Brooklyn, NY 11206",
        "project_type": "commercial_renovation",
        "removal_radius_m": 45,
        "center": {"type": "Point", "coordinates": [-73.9427, 40.6992]},
        "stated_reason": "Retail expansion with outdoor seating area. Existing London Planetrees block proposed canopy structure.",
        "promised_replacements": 5,
        "comment_deadline": "2026-07-14",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1023",
        "developer_id": "dev_park_slope",
        "filed_date": "2026-05-16",
        "address": "455 4th Ave, Brooklyn, NY 11215",
        "project_type": "mixed_use_tower",
        "removal_radius_m": 80,
        "center": {"type": "Point", "coordinates": [-73.9862, 40.6712]},
        "stated_reason": "20-story mixed-use development at 4th Ave transit node. 7 mature trees along block face.",
        "promised_replacements": 14,
        "comment_deadline": "2026-07-18",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1024",
        "developer_id": "dev_williamsburg_heights",
        "filed_date": "2026-05-19",
        "address": "115 N 7th St, Brooklyn, NY 11249",
        "project_type": "hotel_development",
        "removal_radius_m": 55,
        "center": {"type": "Point", "coordinates": [-73.9578, 40.7194]},
        "stated_reason": "12-story boutique hotel. Rooftop crane conflicts with mature Ginkgo overhang on north face.",
        "promised_replacements": 6,
        "comment_deadline": "2026-07-22",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1025",
        "developer_id": "dev_atlas_holdings",
        "filed_date": "2026-05-22",
        "address": "310 Wythe Ave, Brooklyn, NY 11249",
        "project_type": "office_tower",
        "removal_radius_m": 70,
        "center": {"type": "Point", "coordinates": [-73.9634, 40.7189]},
        "stated_reason": "14-story creative office building. Subsurface stormwater cistern conflicts with 3 mature oaks.",
        "promised_replacements": 9,
        "comment_deadline": "2026-07-28",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1026",
        "developer_id": "dev_flatbush_props",
        "filed_date": "2026-05-24",
        "address": "688 Atlantic Ave, Brooklyn, NY 11238",
        "project_type": "industrial_conversion",
        "removal_radius_m": 75,
        "center": {"type": "Point", "coordinates": [-73.9762, 40.6842]},
        "stated_reason": "Warehouse-to-residential conversion. ADA-compliant street access requires removal of 5 trees.",
        "promised_replacements": 10,
        "comment_deadline": "2026-08-01",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1027",
        "developer_id": "dev_bk_urban",
        "filed_date": "2026-05-26",
        "address": "220 Knickerbocker Ave, Brooklyn, NY 11237",
        "project_type": "residential_tower",
        "removal_radius_m": 60,
        "center": {"type": "Point", "coordinates": [-73.9213, 40.7007]},
        "stated_reason": "8-story residential building. HVAC equipment placement requires removal of 2 mature Sweetgums.",
        "promised_replacements": 4,
        "comment_deadline": "2026-08-05",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1028",
        "developer_id": "dev_crown_heights",
        "filed_date": "2026-05-28",
        "address": "1450 Nostrand Ave, Brooklyn, NY 11226",
        "project_type": "commercial_renovation",
        "removal_radius_m": 50,
        "center": {"type": "Point", "coordinates": [-73.9498, 40.6487]},
        "stated_reason": "Medical office expansion. Utility trench conflicts with mature Red Maple root zone.",
        "promised_replacements": 3,
        "comment_deadline": "2026-08-10",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1029",
        "developer_id": "dev_prospect_realty",
        "filed_date": "2026-05-29",
        "address": "512 Church Ave, Brooklyn, NY 11218",
        "project_type": "mixed_use_tower",
        "removal_radius_m": 85,
        "center": {"type": "Point", "coordinates": [-73.9658, 40.6433]},
        "stated_reason": "16-story mixed-use tower on Church Ave corridor. 6 mature London Planetrees within building envelope.",
        "promised_replacements": 12,
        "comment_deadline": "2026-08-15",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
    {
        "_id": "permit_2026_1030",
        "developer_id": "dev_brooklyn_build",
        "filed_date": "2026-05-29",
        "address": "750 Coney Island Ave, Brooklyn, NY 11218",
        "project_type": "hotel_development",
        "removal_radius_m": 90,
        "center": {"type": "Point", "coordinates": [-73.9636, 40.6380]},
        "stated_reason": "Boutique hotel with rooftop bar. Solar panels require canopy removal on south-facing block face.",
        "promised_replacements": 15,
        "comment_deadline": "2026-08-20",
        "status": "open_for_comment",
        "threatened_tree_ids": [],
    },
]

HEALTH_CHOICES = ["Good", "Fair", "Poor", "Good", "Good", "Fair"]


def meters_to_deg(meters: float) -> float:
    """Rough approximation: 1 degree ≈ 111,320 m at NYC latitude."""
    return meters / 111_320


def make_tree(tree_num: int, lng: float, lat: float, borough: str, address_prefix: str) -> dict:
    sp_common, sp_latin = random.choice(SPECIES)
    diam = round(random.uniform(5.0, 28.0), 1)
    base_stormwater = diam * random.uniform(80, 130)
    base_co2        = diam * random.uniform(12, 20)
    base_cooling    = diam * random.uniform(5, 9)
    base_aq         = diam * random.uniform(0.3, 0.7)
    total = round(base_stormwater * 0.0088 + base_co2 * 0.021 + base_cooling * 0.14 + base_aq, 2)

    heat_pct = round(random.uniform(40.0, 99.0), 1)

    # Jitter within ~80m of center
    jitter = meters_to_deg(random.uniform(10, 75))
    angle  = random.uniform(0, 2 * math.pi)
    tlng = round(lng + jitter * math.cos(angle), 6)
    tlat = round(lat + jitter * math.sin(angle) * 0.7, 6)

    return {
        "_id": f"tree_{200000 + tree_num}",
        "nyc_tree_id": 200000 + tree_num,
        "species": {"common": sp_common, "latin": sp_latin},
        "diameter_in": diam,
        "health": random.choice(HEALTH_CHOICES),
        "status": "Alive",
        "location": {"type": "Point", "coordinates": [tlng, tlat]},
        "address": f"{random.randint(10, 999)} {address_prefix}",
        "borough": borough,
        "census_tract": str(random.randint(100, 999)),
        "ecosystem_value_usd_yr": {
            "stormwater_gal": round(base_stormwater, 1),
            "stormwater_usd": round(base_stormwater * 0.0088, 2),
            "co2_lbs": round(base_co2, 1),
            "co2_usd": round(base_co2 * 0.021, 2),
            "cooling_kwh": round(base_cooling, 1),
            "cooling_usd": round(base_cooling * 0.14, 2),
            "air_quality_usd": round(base_aq, 2),
            "total_usd": total,
        },
        "ej_score": {
            "heat_vuln_pct": heat_pct,
            "tract_score": round(heat_pct / 100, 3),
        },
        "planted_year": random.randint(1975, 2020),
        "last_inspection": f"202{random.randint(2,4)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
    }


# Map permit centers to borough + street name for address generation
PERMIT_CONTEXT = {
    # (borough, street_name)
    "permit_2026_1001": ("Manhattan", "W 42nd St"),
    "permit_2026_1002": ("Manhattan", "W 125th St"),
    "permit_2026_1003": ("Manhattan", "Madison Ave"),
    "permit_2026_1004": ("Manhattan", "Amsterdam Ave"),
    "permit_2026_1005": ("Manhattan", "Fulton St"),
    "permit_2026_1006": ("Manhattan", "W 72nd St"),
    "permit_2026_1007": ("Bronx", "Grand Concourse"),
    "permit_2026_1008": ("Bronx", "Westchester Ave"),
    "permit_2026_1009": ("Bronx", "Jerome Ave"),
    "permit_2026_1010": ("Bronx", "E 187th St"),
    "permit_2026_1011": ("Queens", "Junction Blvd"),
    "permit_2026_1012": ("Queens", "Jamaica Ave"),
    "permit_2026_1013": ("Queens", "Lefferts Blvd"),
    "permit_2026_1014": ("Queens", "Woodhaven Blvd"),
    "permit_2026_1015": ("Queens", "Steinway St"),
    "permit_2026_1016": ("Queens", "Queens Blvd"),
    "permit_2026_1017": ("Staten Island", "Richmond Ave"),
    "permit_2026_1018": ("Staten Island", "Hylan Blvd"),
    "permit_2026_1019": ("Staten Island", "Forest Ave"),
    "permit_2026_1020": ("Staten Island", "Richmond Terrace"),
    "permit_2026_1021": ("Brooklyn", "Nassau Ave"),
    "permit_2026_1022": ("Brooklyn", "Myrtle Ave"),
    "permit_2026_1023": ("Brooklyn", "4th Ave"),
    "permit_2026_1024": ("Brooklyn", "N 7th St"),
    "permit_2026_1025": ("Brooklyn", "Wythe Ave"),
    "permit_2026_1026": ("Brooklyn", "Atlantic Ave"),
    "permit_2026_1027": ("Brooklyn", "Knickerbocker Ave"),
    "permit_2026_1028": ("Brooklyn", "Nostrand Ave"),
    "permit_2026_1029": ("Brooklyn", "Church Ave"),
    "permit_2026_1030": ("Brooklyn", "Coney Island Ave"),
}

TREES_PER_PERMIT = 5  # 30 permits × 5 = 150 new trees


def main():
    print(f"Connecting to MongoDB at {MONGODB_URI[:40]}...")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB]
    print(f"Database: {MONGODB_DB}\n")

    # ── 1. Wipe all case data ──────────────────────────────────────────────────
    print("── Step 1: Clearing case data ──────────────────────────")
    b = db.briefings.delete_many({})
    n = db.notifications.delete_many({})
    o = db.outcomes.delete_many({})
    j = db.briefing_jobs.delete_many({})
    print(f"  briefings deleted:     {b.deleted_count}")
    print(f"  notifications deleted: {n.deleted_count}")
    print(f"  outcomes deleted:      {o.deleted_count}")
    print(f"  briefing_jobs deleted: {j.deleted_count}")

    # ── 2. Seed new permits ────────────────────────────────────────────────────
    print("\n── Step 2: Seeding 30 new permits ──────────────────────")
    ins, upd = 0, 0
    for permit in NEW_PERMITS:
        try:
            db.permits.insert_one(permit)
            ins += 1
        except DuplicateKeyError:
            db.permits.replace_one({"_id": permit["_id"]}, permit)
            upd += 1
    print(f"  {ins} inserted, {upd} updated")

    # Ensure geospatial index
    db.permits.create_index([("center", GEOSPHERE)], background=True)
    print("  Geospatial index on permits.center: ensured")

    # ── 3. Seed trees near each new permit ────────────────────────────────────
    print(f"\n── Step 3: Seeding {len(NEW_PERMITS) * TREES_PER_PERMIT} trees near new permits ──")
    tree_num = 0
    tree_ins, tree_upd = 0, 0

    for permit in NEW_PERMITS:
        pid = permit["_id"]
        lng, lat = permit["center"]["coordinates"]
        borough, street = PERMIT_CONTEXT.get(pid, ("Brooklyn", "Main St"))

        for _ in range(TREES_PER_PERMIT):
            tree = make_tree(tree_num, lng, lat, borough, street)
            tree_num += 1
            try:
                db.trees.insert_one(tree)
                tree_ins += 1
            except DuplicateKeyError:
                db.trees.replace_one({"_id": tree["_id"]}, tree)
                tree_upd += 1

    print(f"  {tree_ins} inserted, {tree_upd} updated")

    # Ensure geospatial index on trees
    db.trees.create_index([("location", GEOSPHERE)], background=True)
    print("  Geospatial index on trees.location: ensured")

    # ── 4. Summary ────────────────────────────────────────────────────────────
    print("\n── Final collection counts ──────────────────────────────")
    for col_name in ["trees", "permits", "developers", "briefings", "notifications", "outcomes", "briefing_jobs"]:
        count = db[col_name].count_documents({})
        print(f"  {col_name:<22} {count:>6} documents")

    client.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
