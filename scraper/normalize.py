"""Normalize and link drug events across EMA, TLV, and NT-rådet."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

ATC_GROUP_NAMES = {
    "A": "Alimentary tract & metabolism",
    "B": "Blood & blood forming organs",
    "C": "Cardiovascular system",
    "D": "Dermatologicals",
    "G": "Genito-urinary & sex hormones",
    "H": "Systemic hormonal preparations",
    "J": "Antiinfectives for systemic use",
    "L": "Antineoplastic & immunomodulating",
    "M": "Musculo-skeletal system",
    "N": "Nervous system",
    "P": "Antiparasitic products",
    "R": "Respiratory system",
    "S": "Sensory organs",
    "V": "Various",
}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _canonical_key(event: dict[str, Any]) -> str:
    substance = (event.get("active_substance") or "").strip().lower()
    # Strip common salt suffixes or extra parentheticals
    substance = re.sub(r"\(.*?\)", "", substance).strip()
    if substance and len(substance) >= 3:
        return f"sub:{_slug(substance)}"
    name = (event.get("drug_name") or "").strip().lower()
    name = re.sub(r"\(.*?\)", "", name).strip()
    return f"name:{_slug(name)}" if name else "unknown"


def _infer_therapeutic_area(atc_code: str, existing: str) -> str:
    if existing and existing.strip():
        return existing.strip()
    if atc_code and len(atc_code.strip()) >= 1:
        letter = atc_code.strip()[0].upper()
        if letter in ATC_GROUP_NAMES:
            return ATC_GROUP_NAMES[letter]
    return "Other / Unclassified"


def build_unified_feed(events: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}

    for ev in events:
        key = _canonical_key(ev)
        if key == "unknown":
            continue

        entry = grouped.get(key)
        if entry is None:
            entry = {
                "id": key.replace(":", "-"),
                "drug_name": ev.get("drug_name") or ev.get("active_substance") or "Unknown",
                "active_substance": ev.get("active_substance") or "",
                "atc_code": ev.get("atc_code") or "",
                "therapeutic_area": ev.get("therapeutic_area") or "",
                "latest_date": ev.get("date") or "",
                "latest_update_type": ev.get("update_type") or "new_drug",
                "sources_present": [],
                "events": [],
                "_seen_events": set(),
            }
            grouped[key] = entry

        # Enrich top-level metadata from whichever source has it
        if not entry["active_substance"] and ev.get("active_substance"):
            entry["active_substance"] = ev["active_substance"]
        if not entry["atc_code"] and ev.get("atc_code"):
            entry["atc_code"] = ev["atc_code"]
        if not entry["therapeutic_area"] and ev.get("therapeutic_area"):
            entry["therapeutic_area"] = ev["therapeutic_area"]
        if len(entry["drug_name"]) < 2 and ev.get("drug_name"):
            entry["drug_name"] = ev["drug_name"]

        dedup_key = (ev.get("source", ""), ev.get("date", ""), ev.get("title", ""))
        if dedup_key in entry["_seen_events"]:
            continue
        entry["_seen_events"].add(dedup_key)

        entry["events"].append(
            {
                "source": ev["source"],
                "date": ev.get("date", ""),
                "update_type": ev.get("update_type", "new_drug"),
                "status": ev.get("status", ""),
                "title": ev.get("title", ""),
                "indication": ev.get("indication", ""),
                "summary": ev.get("summary", ""),
                "url": ev.get("url", ""),
            }
        )

    drugs: list[dict[str, Any]] = []
    counts = {"total": 0, "ema": 0, "tlv": 0, "nt_radet": 0}

    for entry in grouped.values():
        entry.pop("_seen_events", None)
        entry["events"].sort(key=lambda e: e["date"], reverse=True)
        if not entry["events"]:
            continue

        latest = entry["events"][0]
        entry["latest_date"] = latest["date"]
        entry["latest_update_type"] = latest["update_type"]
        entry["therapeutic_area"] = _infer_therapeutic_area(entry["atc_code"], entry["therapeutic_area"])

        sources = sorted({e["source"] for e in entry["events"]})
        entry["sources_present"] = sources
        if "EMA" in sources:
            counts["ema"] += 1
        if "TLV" in sources:
            counts["tlv"] += 1
        if "NT_RADET" in sources:
            counts["nt_radet"] += 1

        drugs.append(entry)

    drugs.sort(key=lambda d: d["latest_date"], reverse=True)
    counts["total"] = len(drugs)

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts": counts,
        "drugs": drugs,
    }
