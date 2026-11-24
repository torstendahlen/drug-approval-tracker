"""Fetch recommendations from NT-rådet (samverkanlakemedel.se)."""

from __future__ import annotations

import logging
import re
from typing import Any

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

NT_RADET_URLS = [
    "https://samverkanlakemedel.se/nt-radets-rekommendationer/",
    "https://www.samverkanlakemedel.se/nt-radets-rekommendationer/",
    "https://samverkanlakemedel.se/lakemedel/nt-radets-rekommendationer/",
]
USER_AGENT = "DrugApprovalTracker/1.0 (https://github.com/drug-approval-tracker)"


def _parse_date(raw: str) -> str:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", raw or "")
    return m.group(1) if m else ""


def _classify_nt_update(indication: str, comment: str) -> str:
    combined = f"{indication} {comment}".lower()
    if any(k in combined for k in ("ny indikation", "utökad indikation", "tilläggsindikation", "uppdaterad")):
        return "new_indication"
    return "new_drug"


def fetch_nt_radet(limit: int = 200) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    for url in NT_RADET_URLS:
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=35)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            tables = soup.select("table")
            if not tables:
                continue

            for table in tables:
                headers = [th.get_text(" ", strip=True).lower() for th in table.select("thead th, tr:first-child th")]
                rows = table.select("tbody tr") or table.select("tr")[1:]
                for row in rows[:limit]:
                    cells = [td.get_text(" ", strip=True) for td in row.select("td")]
                    if len(cells) < 3:
                        continue

                    # Map columns flexibly by header name or standard order
                    col_map: dict[str, str] = {}
                    for idx, val in enumerate(cells):
                        key = headers[idx] if idx < len(headers) else f"col_{idx}"
                        col_map[key] = val

                    substance = (
                        col_map.get("substans")
                        or col_map.get("aktiv substans")
                        or cells[0]
                    ).strip()
                    drug_name = (
                        col_map.get("läkemedel")
                        or col_map.get("läkemedelsnamn")
                        or col_map.get("produktnamn")
                        or (cells[1] if len(cells) > 1 else substance)
                    ).strip()
                    indication = (
                        col_map.get("indikation")
                        or (cells[2] if len(cells) > 2 else "")
                    ).strip()
                    atc_code = (col_map.get("atc-kod") or col_map.get("atc") or "").strip()
                    status = (
                        col_map.get("rekommendation")
                        or col_map.get("beslut")
                        or (cells[3] if len(cells) > 3 else "Rekommendation")
                    ).strip()
                    date_raw = (
                        col_map.get("datum")
                        or col_map.get("publicerad")
                        or " ".join(cells)
                    )
                    date_str = _parse_date(date_raw)

                    link_el = row.select_one("a[href]")
                    row_url = url
                    if link_el:
                        href = link_el["href"]
                        row_url = href if href.startswith("http") else f"https://samverkanlakemedel.se{href}"

                    if not drug_name and not substance:
                        continue

                    events.append(
                        {
                            "source": "NT_RADET",
                            "drug_name": drug_name or substance,
                            "active_substance": substance,
                            "atc_code": atc_code,
                            "therapeutic_area": "",
                            "date": date_str or "2026-01-01",
                            "update_type": _classify_nt_update(indication, status),
                            "status": status,
                            "title": f"{drug_name or substance} – {status}",
                            "indication": indication[:500],
                            "summary": f"NT-rådet: {status}. {indication[:300]}".strip(),
                            "url": row_url,
                        }
                    )
            if events:
                break
        except Exception as exc:
            logger.warning("Failed NT-rådet %s: %s", url, exc)

    events.sort(key=lambda e: e["date"], reverse=True)
    return events[:limit]
