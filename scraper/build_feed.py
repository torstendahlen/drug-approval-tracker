"""Orchestrate fetching EMA, TLV, and NT-rådet and write docs/data/drugs.json."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fetch_ema import fetch_ema
from fetch_nt_radet import fetch_nt_radet
from fetch_tlv import fetch_tlv
from normalize import build_unified_feed

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("build_feed")

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "docs" / "data" / "drugs.json"


def main() -> None:
    events = []

    for name, fn in (("EMA", fetch_ema), ("TLV", fetch_tlv), ("NT-rådet", fetch_nt_radet)):
        try:
            fetched = fn()
            logger.info("Fetched %d events from %s", len(fetched), name)
            events.extend(fetched)
        except Exception as exc:
            logger.exception("Error fetching %s: %s", name, exc)

    if not events:
        logger.warning("No events fetched from any source; keeping existing %s if present.", OUTPUT_PATH)
        return

    feed = build_unified_feed(events)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(feed, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Wrote %d unified drug records to %s", feed["counts"]["total"], OUTPUT_PATH)


if __name__ == "__main__":
    main()
