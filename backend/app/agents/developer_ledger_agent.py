"""
Developer Ledger Agent: retrieves and normalizes a developer's replacement
compliance history for a permit.
"""
from __future__ import annotations

from typing import Any

from app.db.repositories.developers import get_developer_by_id
from app.db.repositories.permits import get_permit_by_id
from app.models.briefing import DeveloperSnapshot


CITY_SURVIVAL_TARGET = 0.85


def _unknown_snapshot(developer_id: str = "unknown") -> DeveloperSnapshot:
    return DeveloperSnapshot(
        developer_id=developer_id,
        name="Unknown Developer",
        compliance_rate=0.0,
        city_target=CITY_SURVIVAL_TARGET,
        target_delta=-CITY_SURVIVAL_TARGET,
        permits_filed=0,
        promised_replacements=0,
        verified_surviving=0,
        violations_count=0,
        at_risk_replacements=0,
    )


def build_snapshot(dev_doc: dict[str, Any] | None, developer_id: str = "unknown") -> DeveloperSnapshot:
    if not dev_doc:
        return _unknown_snapshot(developer_id)

    compliance_rate = float(dev_doc.get("compliance_rate", 0.0) or 0.0)
    promised = int(dev_doc.get("promised_replacements", 0) or 0)
    verified = int(dev_doc.get("verified_surviving", 0) or 0)
    expected_survivors = round(promised * CITY_SURVIVAL_TARGET)

    return DeveloperSnapshot(
        developer_id=str(dev_doc.get("_id", developer_id)),
        name=dev_doc.get("name", "Unknown Developer"),
        compliance_rate=compliance_rate,
        city_target=CITY_SURVIVAL_TARGET,
        target_delta=round(compliance_rate - CITY_SURVIVAL_TARGET, 4),
        permits_filed=int(dev_doc.get("permits_filed", 0) or 0),
        promised_replacements=promised,
        verified_surviving=verified,
        violations_count=len(dev_doc.get("violations", [])),
        at_risk_replacements=max(expected_survivors - verified, 0),
    )


async def run_for_developer(developer_id: str) -> DeveloperSnapshot:
    dev_doc = await get_developer_by_id(developer_id)
    return build_snapshot(dev_doc, developer_id)


async def run(permit_id: str) -> DeveloperSnapshot:
    permit = await get_permit_by_id(permit_id)
    if not permit:
        return _unknown_snapshot()

    developer_id = permit.get("developer_id", "unknown")
    return await run_for_developer(developer_id)
