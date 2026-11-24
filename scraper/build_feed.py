"""Orchestrate fetching EMA, TLV, and NT-rådet, merge with archive, and write docs/data/drugs.json."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fetch_ema import fetch_ema
from fetch_nt_radet import fetch_nt_radet
from fetch_tlv import fetch_tlv
from normalize import build_unified_feed

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("build_feed")

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "docs" / "data" / "drugs.json"


def _load_existing_events() -> list[dict[str, Any]]:
    if not OUTPUT_PATH.exists():
        return []
    try:
        data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        events: list[dict[str, Any]] = []
        for drug in data.get("drugs", []):
            for ev in drug.get("events", []):
                events.append(
                    {
                        "source": ev.get("source", ""),
                        "drug_name": drug.get("drug_name", ""),
                        "active_substance": drug.get("active_substance", ""),
                        "atc_code": drug.get("atc_code", ""),
                        "therapeutic_area": drug.get("therapeutic_area", ""),
                        "date": ev.get("date", ""),
                        "update_type": ev.get("update_type", "new_drug"),
                        "status": ev.get("status", ""),
                        "title": ev.get("title", ""),
                        "indication": ev.get("indication", ""),
                        "summary": ev.get("summary", ""),
                        "url": ev.get("url", ""),
                    }
                )
        logger.info("Loaded %d archived events from %s", len(events), OUTPUT_PATH)
        return events
    except Exception as exc:
        logger.warning("Could not load existing archive: %s", exc)
        return []


def main() -> None:
    events = _load_existing_events()
    fetched_any = False

    for name, fn in (("EMA", fetch_ema), ("TLV", fetch_tlv), ("NT-rådet", fetch_nt_radet)):
        try:
            fetched = fn()
            logger.info("Fetched %d events from %s", len(fetched), name)
            if fetched:
                fetched_any = True
                events.extend(fetched)
        except Exception as exc:
            logger.exception("Error fetching %s: %s", name, exc)

    if not fetched_any and not events:
        logger.warning("No events fetched from any source; keeping existing %s if present.", OUTPUT_PATH)
        return

    feed = build_unified_feed(events)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(feed, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(
        "Wrote %d unified drugs (EMA=%d, TLV=%d, NT-rådet=%d) to %s",
        feed["counts"]["total"],
        feed["counts"]["ema"],
        feed["counts"]["tlv"],
        feed["counts"]["nt_radet"],
        OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()
