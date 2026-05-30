"""
Developer Accountability Intelligence — MongoDB Aggregation Pipeline.

Replaces Python-side reconciliation with a single MongoDB $lookup + $facet
aggregation that computes compliance trend, violation breakdown, active permit
exposure, and risk classification in one round-trip.

MongoDB features used:
  $lookup   — join planting_records and permits to the developer document
  $facet    — run 4 parallel sub-pipelines on the same input simultaneously
  $unwind   — flatten planting_records and violations arrays for grouping
  $group    — aggregate promised/planted/surviving by inspection year
  $addFields + $cond — compute derived survival_rate without application code
  $switch   — classify developer into risk tier (critical/high/elevated/compliant)
  $elemMatch — match linked entity names across the developer collection
"""
from __future__ import annotations

from app.db.client import get_db, bson_clean


async def get_developer_risk_intelligence(developer_id: str) -> dict:
    """
    Single aggregation call that returns a complete accountability picture:
      - compliance_by_year:  survival rate per inspection cohort
      - active_exposure:     open permits and trees currently at risk
      - violation_breakdown: which violation types caused the most canopy loss
      - risk_profile:        MongoDB-computed risk tier + network metadata
    """
    db = get_db()
    pipeline = [
        {"$match": {"_id": developer_id}},

        # ── Stage 1: JOIN historical planting outcomes ─────────────────────────
        {
            "$lookup": {
                "from": "planting_records",
                "localField": "_id",
                "foreignField": "developer_id",
                "as": "planting_records",
            }
        },

        # ── Stage 2: JOIN all permits (open and historical) ────────────────────
        {
            "$lookup": {
                "from": "permits",
                "localField": "_id",
                "foreignField": "developer_id",
                "as": "all_permits",
            }
        },

        # ── Stage 3: PARALLEL ANALYTICS ($facet = one round-trip, N results) ──
        {
            "$facet": {

                # How has this developer's replacement survival changed over time?
                "compliance_by_year": [
                    {
                        "$unwind": {
                            "path": "$planting_records",
                            "preserveNullAndEmpty": False,
                        }
                    },
                    {
                        "$group": {
                            "_id": "$planting_records.inspection_year",
                            "promised": {"$sum": "$planting_records.promised_count"},
                            "planted": {"$sum": "$planting_records.planted_count"},
                            "surviving": {"$sum": "$planting_records.surviving_3yr_count"},
                        }
                    },
                    {
                        "$addFields": {
                            "survival_rate": {
                                "$cond": [
                                    {"$gt": ["$promised", 0]},
                                    {
                                        "$round": [
                                            {"$divide": ["$surviving", "$promised"]},
                                            2,
                                        ]
                                    },
                                    0,
                                ]
                            }
                        }
                    },
                    {"$sort": {"_id": 1}},
                ],

                # Which open permits represent outstanding accountability risk?
                "active_exposure": [
                    {
                        "$unwind": {
                            "path": "$all_permits",
                            "preserveNullAndEmpty": False,
                        }
                    },
                    {"$match": {"all_permits.status": "open_for_comment"}},
                    {
                        "$group": {
                            "_id": None,
                            "open_permit_count": {"$sum": 1},
                            "trees_at_risk": {
                                "$sum": "$all_permits.promised_replacements"
                            },
                            "earliest_deadline": {
                                "$min": "$all_permits.comment_deadline"
                            },
                        }
                    },
                    {"$project": {"_id": 0}},
                ],

                # What types of violations caused the most canopy loss?
                "violation_breakdown": [
                    {
                        "$unwind": {
                            "path": "$violations",
                            "preserveNullAndEmpty": False,
                        }
                    },
                    {
                        "$group": {
                            "_id": "$violations.type",
                            "trees_affected": {"$sum": "$violations.count"},
                            "permit_count": {"$sum": 1},
                        }
                    },
                    {"$sort": {"trees_affected": -1}},
                ],

                # MongoDB-computed risk tier — no application-side logic needed
                "risk_profile": [
                    {
                        "$project": {
                            "_id": 0,
                            "developer_id": "$_id",
                            "name": 1,
                            "compliance_rate": 1,
                            "linked_entities": 1,
                            "network_entity_count": {"$size": "$linked_entities"},
                            "risk_tier": {
                                "$switch": {
                                    "branches": [
                                        {
                                            "case": {
                                                "$lt": ["$compliance_rate", 0.40]
                                            },
                                            "then": "critical",
                                        },
                                        {
                                            "case": {
                                                "$lt": ["$compliance_rate", 0.60]
                                            },
                                            "then": "high",
                                        },
                                        {
                                            "case": {
                                                "$lt": ["$compliance_rate", 0.85]
                                            },
                                            "then": "elevated",
                                        },
                                    ],
                                    "default": "compliant",
                                }
                            },
                            # How far below (or above) the 85% city target?
                            "accountability_gap_pct": {
                                "$round": [
                                    {
                                        "$multiply": [
                                            {"$subtract": [0.85, "$compliance_rate"]},
                                            100,
                                        ]
                                    },
                                    1,
                                ]
                            },
                        }
                    }
                ],
            }
        },
    ]

    cursor = db.developers.aggregate(pipeline)
    results = await cursor.to_list(length=1)
    if not results:
        return {}

    doc = bson_clean(results[0])
    # Unwrap single-element $facet branches for cleaner API response
    doc["risk_profile"] = doc["risk_profile"][0] if doc["risk_profile"] else {}
    exposure = doc.get("active_exposure", [])
    doc["active_exposure"] = (
        exposure[0]
        if exposure
        else {"open_permit_count": 0, "trees_at_risk": 0, "earliest_deadline": None}
    )
    return doc


async def get_entity_network(developer_id: str) -> dict:
    """
    Aggregate accountability across a developer's entire entity network.

    Uses $lookup + $elemMatch to find every developer record whose name
    appears in this developer's linked_entities list, or vice versa.
    Groups the matched records to expose the network's combined
    compliance rate — the number that matters when a developer routes
    permits through shell companies to obscure a bad individual record.
    """
    db = get_db()

    primary = await db.developers.find_one({"_id": developer_id})
    if not primary:
        return {}

    linked = primary.get("linked_entities", [])
    primary_name = primary.get("name", "")
    all_names = [primary_name] + linked

    # Match the primary developer plus any related entities found by name
    match_clause: dict = {"_id": developer_id}
    if linked:
        match_clause = {
            "$or": [
                {"_id": developer_id},
                # Another developer whose own name is in our linked_entities
                {"name": {"$in": linked}},
                # Another developer who lists us in their linked_entities
                {"linked_entities": {"$elemMatch": {"$in": all_names}}},
            ]
        }

    pipeline = [
        {"$match": match_clause},

        # Join planting records to get raw promised/surviving counts
        {
            "$lookup": {
                "from": "planting_records",
                "localField": "_id",
                "foreignField": "developer_id",
                "as": "records",
            }
        },

        # Collapse all matched entities into one network summary
        {
            "$group": {
                "_id": None,
                "entities": {
                    "$push": {
                        "id": "$_id",
                        "name": "$name",
                        "compliance_rate": "$compliance_rate",
                    }
                },
                "total_permits_filed": {"$sum": "$permits_filed"},
                "total_promised": {"$sum": "$promised_replacements"},
                "total_surviving": {"$sum": "$verified_surviving"},
                "combined_violations": {"$sum": {"$size": "$violations"}},
            }
        },

        # Derive the true network-wide compliance rate from raw counts
        {
            "$addFields": {
                "network_compliance_rate": {
                    "$cond": [
                        {"$gt": ["$total_promised", 0]},
                        {
                            "$round": [
                                {
                                    "$divide": [
                                        "$total_surviving",
                                        "$total_promised",
                                    ]
                                },
                                2,
                            ]
                        },
                        0,
                    ]
                },
                "all_entity_names": all_names,
            }
        },

        {"$project": {"_id": 0}},
    ]

    cursor = db.developers.aggregate(pipeline)
    results = await cursor.to_list(length=1)
    return bson_clean(results[0]) if results else {}
