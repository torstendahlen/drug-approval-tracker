"""Fetch drug reimbursement decisions from TLV (Tandvårds- och läkemedelsförmånsverket)."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

TLV_RSS_URLS = [
    "https://www.tlv.se/4.1d85645215ec7de889a2b3/12.1d85645215ec7de889a2c4.portlet?state=rss",
    "https://www.tlv.se/beslut/beslut-lakemedel.rss",
]
TLV_DECISIONS_URL = "https://www.tlv.se/beslut/beslut-lakemedel.html"
USER_AGENT = "DrugApprovalTracker/1.0 (https://github.com/drug-approval-tracker)"


def _parse_date(raw: str | None) -> str:
    if not raw:
        return ""
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z", "%d %B %Y"):
        try:
            return datetime.strptime(raw[:31], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    m = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
    return m.group(1) if m else ""


def _classify_tlv(text: str) -> tuple[str, str]:
    """Return (update_type, status) from Swedish TLV decision text."""
    lower = text.lower()

    if any(k in lower for k in ("ny indikation", "utvidgad subvention", "utökad subvention", "ytterligare indikation")):
        update_type = "new_indication"
    elif any(k in lower for k in ("nytt läkemedel", "ingår i läkemedelsförmånerna", "subventioneras", "beslut")):
        update_type = "new_drug"
    else:
        update_type = "other"

    if "begränsad subvention" in lower or "med begränsning" in lower:
        status = "Begränsad subvention"
    elif "avslag" in lower or "ingår inte" in lower or "subventioneras inte" in lower:
        status = "Avslag / Ej subvention"
    elif "ingår i läkemedelsförmånerna" in lower or "subventioneras" in lower:
        status = "Ingår i förmånen"
    else:
        status = "TLV Beslut"

    return update_type, status


def _extract_drug_and_substance(title: str) -> tuple[str, str]:
    """Extract drug name and optional active substance from a TLV title."""
    # Common pattern: "Tecvayli (teclistamab) ingår i läkemedelsförmånerna..."
    m = re.match(r"^([A-ZÅÄÖ][\w\-]+)\s*\(([^)]+)\)", title.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    first_word = title.strip().split(" ")[0].rstrip(",:;")
    return first_word[:60], ""


def fetch_tlv_rss(limit: int = 100) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    seen: set[str] = set()

    for url in TLV_RSS_URLS:
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
            if resp.status_code != 200:
                continue
            parsed = feedparser.parse(resp.content)
            for entry in parsed.entries[:limit]:
                link = getattr(entry, "link", "")
                if not link or link in seen:
                    continue
                seen.add(link)

                title = getattr(entry, "title", "").strip()
                summary = re.sub(r"<[^>]+>", " ", getattr(entry, "summary", "")).strip()
                summary = re.sub(r"\s+", " ", summary)
                combined = f"{title} {summary}"
                update_type, status = _classify_tlv(combined)
                drug_name, substance = _extract_drug_and_substance(title)
                date_str = _parse_date(getattr(entry, "published", "") or getattr(entry, "updated", ""))
                if not date_str:
                    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

                events.append(
                    {
                        "source": "TLV",
                        "drug_name": drug_name,
                        "active_substance": substance,
                        "atc_code": "",
                        "therapeutic_area": "",
                        "date": date_str,
                        "update_type": update_type,
                        "status": status,
                        "title": title,
                        "indication": summary[:450],
                        "summary": summary[:450],
                        "url": link,
                    }
                )
        except Exception as exc:
            logger.warning("Failed TLV RSS %s: %s", url, exc)

    return events


def fetch_tlv_html(limit: int = 80) -> list[dict[str, Any]]:
    """Fallback HTML scrape of TLV's recent drug decisions page."""
    events: list[dict[str, Any]] = []
    try:
        resp = requests.get(TLV_DECISIONS_URL, headers={"User-Agent": USER_AGENT}, timeout=30)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        for item in soup.select("article, .sv-channel-item, li.decision-item, tr")[:limit]:
            link_el = item.select_one("a[href]")
            if not link_el:
                continue
            title = link_el.get_text(" ", strip=True)
            if len(title) < 4:
                continue
            href = link_el["href"]
            if not href.startswith("http"):
                href = f"https://www.tlv.se{href}"
            text = item.get_text(" ", strip=True)
            date_str = _parse_date(text)
            if not date_str:
                continue
            update_type, status = _classify_tlv(text)
            drug_name, substance = _extract_drug_and_substance(title)
            events.append(
                {
                    "source": "TLV",
                    "drug_name": drug_name,
                    "active_substance": substance,
                    "atc_code": "",
                    "therapeutic_area": "",
                    "date": date_str,
                    "update_type": update_type,
                    "status": status,
                    "title": title,
                    "indication": text[:400],
                    "summary": text[:400],
                    "url": href,
                }
            )
    except Exception as exc:
        logger.warning("Failed TLV HTML scrape: %s", exc)
    return events


def fetch_tlv() -> list[dict[str, Any]]:
    events = fetch_tlv_rss()
    if not events:
        events = fetch_tlv_html()
    events.sort(key=lambda e: e["date"], reverse=True)
    return events
