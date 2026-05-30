from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from app.db.repositories.developers import upsert_developer_ledger
from app.db.repositories.planting_records import list_planting_records


def _now_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def build_ledger_from_records(records: list[dict]) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        grouped[record.get("developer_id", "unknown")].append(record)

    ledgers: dict[str, dict] = {}
    for developer_id, dev_records in grouped.items():
        promised = sum(int(r.get("promised_count", 0) or 0) for r in dev_records)
        planted = sum(int(r.get("planted_count", 0) or 0) for r in dev_records)
        surviving = sum(int(r.get("surviving_3yr_count", 0) or 0) for r in dev_records)
        compliance_rate = round(surviving / promised, 4) if promised else 0.0

        violations = []
        for record in dev_records:
            promised_count = int(record.get("promised_count", 0) or 0)
            planted_count = int(record.get("planted_count", 0) or 0)
            surviving_count = int(record.get("surviving_3yr_count", 0) or 0)
            missing = max(promised_count - planted_count, 0)
            mortality = max(planted_count - surviving_count, 0)
            status = record.get("status", "unknown")

            if missing:
                violations.append({
                    "permit_id": record.get("permit_id", ""),
                    "type": "missing_replacement",
                    "count": missing,
                    "year": int(record.get("inspection_year", 0) or 0),
                })
            if mortality and status != "verified":
                violations.append({
                    "permit_id": record.get("permit_id", ""),
                    "type": "replacement_mortality",
                    "count": mortality,
                    "year": int(record.get("inspection_year", 0) or 0),
                })
            if status in {"late_planting", "species_substitution_unapproved"}:
                violations.append({
                    "permit_id": record.get("permit_id", ""),
                    "type": status,
                    "count": max(missing or mortality, 1),
                    "year": int(record.get("inspection_year", 0) or 0),
                })

        ledgers[developer_id] = {
            "permits_filed": len({r.get("permit_id") for r in dev_records if r.get("permit_id")}),
            "promised_replacements": promised,
            "verified_planted": planted,
            "verified_surviving": surviving,
            "compliance_rate": compliance_rate,
            "violations": violations,
            "last_audit": _now_date(),
            "reconciliation_source": "planting_records",
        }

    return ledgers


async def reconcile_developer_ledgers(developer_id: str | None = None) -> dict:
    records = await list_planting_records(developer_id)
    ledgers = build_ledger_from_records(records)

    for dev_id, ledger in ledgers.items():
        await upsert_developer_ledger(dev_id, ledger)

    return {
        "developers_reconciled": len(ledgers),
        "records_processed": len(records),
        "developer_ids": sorted(ledgers.keys()),
    }
