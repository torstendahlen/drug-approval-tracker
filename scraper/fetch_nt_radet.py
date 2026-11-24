"""Fetch recommendations & full archive from NT-rådet (samverkanlakemedel.se)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

NT_BASE = "https://samverkanlakemedel.se"
NT_RADET_URLS = [
    "https://samverkanlakemedel.se/lakemedel---ordnat-inforande/nt-radets-rekommendationer",
    "https://samverkanlakemedel.se/lakemedel---ordnat-inforande/arkiverade-rekommendationer",
]
USER_AGENT = "DrugApprovalTracker/1.2 (https://github.com/torstendahlen/drug-approval-tracker)"


def _parse_date(raw: str) -> str:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", raw or "")
    return m.group(1) if m else ""


def _abs_nt_url(href: str | None, fallback: str) -> str:
    u = (href or "").strip()
    if not u or u.startswith("#") or u.lower().startswith("javascript:"):
        return fallback
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return urljoin(NT_BASE, u)


def _classify_nt_update(indication: str, comment: str, seen_products: set[str], product_key: str) -> str:
    combined = f"{indication} {comment}".lower()
    if any(k in combined for k in ("ny indikation", "utökad indikation", "tilläggsindikation", "uppdaterad")):
        return "new_indication"
    if product_key in seen_products:
        return "new_indication"
    return "new_drug"


def _extract_embedded_products(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    for script in soup.select("script"):
        txt = script.string or ""
        if '"products"' not in txt:
            continue
        m = re.search(r'(\{"products"\s*:\s*\[.*?\]\s*(?:,\s*"[^"]+"\s*:[^}]*)?\})', txt, re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                products = data.get("products", [])
                if isinstance(products, list) and products:
                    return products
            except json.JSONDecodeError:
                pass
        # Fallback: extract just the products array
        m2 = re.search(r'"products"\s*:\s*(\[.*?\])\s*[,}]', txt, re.S)
        if m2:
            try:
                products = json.loads(m2.group(1))
                if isinstance(products, list) and products:
                    return products
            except json.JSONDecodeError:
                pass
    return []


def fetch_nt_radet(limit: int = 2000) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    seen_products: set[str] = set()

    for page_url in NT_RADET_URLS:
        try:
            resp = requests.get(page_url, headers={"User-Agent": USER_AGENT}, timeout=40)
            if resp.status_code != 200:
                logger.warning("NT-rådet %s returned HTTP %s", page_url, resp.status_code)
                continue

            products = _extract_embedded_products(resp.text)
            logger.info("Extracted %d NT-rådet products from %s", len(products), page_url)

            for item in products:
                if not isinstance(item, dict):
                    continue
                drug_name = str(item.get("productName") or "").strip()
                substance = str(item.get("substances") or "").strip()
                indication = str(item.get("indication") or "").strip()
                atc_code = str(item.get("atc") or "").strip()
                status = str(item.get("recommendation") or "Rekommendation").strip().capitalize()
                comment = str(item.get("comment") or "").strip()
                date_str = _parse_date(str(item.get("publishDate") or ""))
                row_url = _abs_nt_url(item.get("url"), page_url)

                if not drug_name and not substance:
                    continue

                pkey = (substance or drug_name).lower()
                update_type = _classify_nt_update(indication, comment, seen_products, pkey)
                seen_products.add(pkey)

                summary_parts = [f"NT-rådet: {status}."]
                if indication:
                    summary_parts.append(indication)
                if comment:
                    summary_parts.append(comment)

                events.append(
                    {
                        "source": "NT_RADET",
                        "drug_name": drug_name or substance,
                        "active_substance": substance,
                        "atc_code": atc_code,
                        "therapeutic_area": "",
                        "date": date_str or "2026-01-01",
                        "update_type": update_type,
                        "status": status,
                        "title": f"{drug_name or substance} – {status}",
                        "indication": indication[:500],
                        "summary": " ".join(summary_parts)[:500],
                        "url": row_url,
                    }
                )
        except Exception as exc:
            logger.warning("Failed NT-rådet %s: %s", page_url, exc)

    events.sort(key=lambda e: e["date"], reverse=True)
    return events[:limit]
