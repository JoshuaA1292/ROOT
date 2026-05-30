from app.config import settings


def ingestion_source_status() -> dict:
    return {
        "nyc_dob_permit_url": {
            "configured": bool(settings.nyc_dob_permit_url),
            "env": "NYC_DOB_PERMIT_URL",
        },
        "parks_tree_work_url": {
            "configured": bool(settings.parks_tree_work_url),
            "env": "PARKS_TREE_WORK_URL",
        },
        "portland_tree_inventory_url": {
            "configured": bool(settings.portland_tree_inventory_url),
            "env": "PORTLAND_TREE_INVENTORY_URL",
        },
        "seattle_tree_inventory_url": {
            "configured": bool(settings.seattle_tree_inventory_url),
            "env": "SEATTLE_TREE_INVENTORY_URL",
        },
    }


def require_ingestion_sources() -> None:
    missing = [
        item["env"]
        for item in ingestion_source_status().values()
        if not item["configured"]
    ]
    if missing:
        raise ValueError(f"Missing ingestion source env vars: {', '.join(missing)}")
