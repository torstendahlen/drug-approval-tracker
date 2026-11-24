"""Fetch drug reimbursement decisions & archive from TLV (tlv.se)."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

TLV_BASE = "https://www.tlv.se"
TLV_RSS_DIRECTORY_URL = "https://www.tlv.se/press/prenumerationer/rss-prenumerationer.html"
TLV_DECISION_PAGES = [
    "https://www.tlv.se/beslut/",
    "https://www.tlv.se/beslut/beslut-om-lakemedel.html",
    "https://www.tlv.se/beslut/beslut-om-lakemedel/generell-subvention.html",
    "https://www.tlv.se/beslut/beslut-om-lakemedel/begransad-subvention.html",
    "https://www.tlv.se/beslut/beslut-om-lakemedel/avslag-och-uteslutningar.html",
]
USER_AGENT = "DrugApprovalTracker/1.1 (https://github.com/torstendahlen/drug-approval-tracker)"


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


def _abs_tlv_url(href: str | None) -> str:
    u = (href or "").strip()
    if not u:
        return f"{TLV_BASE}/beslut/"
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return urljoin(TLV_BASE, u)


def _classify_tlv(text: str) -> tuple[str, str]:
    lower = text.lower()
    if any(k in lower for k in ("ny indikation", "utvidgad subvention", "utökad subvention", "ytterligare indikation")):
        update_type = "new_indication"
    elif any(k in lower for k in ("nytt läkemedel", "ingår i läkemedelsförmånerna", "subventioneras", "subvention")):
        update_type = "new_drug"
    else:
        update_type = "other"

    if "begränsad subvention" in lower or "med begränsning" in lower:
        status = "Begränsad subvention"
    elif "avslag" in lower or "ingår inte" in lower or "subventioneras inte" in lower or "uteslut" in lower:
        status = "Avslag / Ej subvention"
    elif "generell subvention" in lower or "ingår i läkemedelsförmånerna" in lower or "subventioneras" in lower:
        status = "Ingår i förmånen"
    else:
        status = "TLV Beslut"

    return update_type, status


def _extract_drug_and_substance(title: str) -> tuple[str, str]:
    m = re.match(r"^([A-ZÅÄÖ][\w\-\s]{1,35}?)\s*\(([^)]+)\)", title.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    first_word = title.strip().split(" ")[0].rstrip(",:;")
    return first_word[:60], ""


def _discover_tlv_rss_urls() -> list[str]:
    """Discover the current 'Beslut läkemedel' RSS URLs from TLV's RSS page."""
    urls: list[str] = []
    try:
        resp = requests.get(TLV_RSS_DIRECTORY_URL, headers={"User-Agent": USER_AGENT}, timeout=25)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            for a in soup.select("a[href]"):
                href = a["href"]
                label = a.get_text(" ", strip=True).lower()
                if ("rss" in href.lower() or "state=rss" in href.lower()) and (
                    "läkemedel" in label or "beslut" in label
                ):
                    urls.append(_abs_tlv_url(href))
    except Exception as exc:
        logger.warning("Could not discover TLV RSS links: %s", exc)
    return urls


def fetch_tlv_rss(limit: int = 200) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    seen: set[str] = set()

    for url in _discover_tlv_rss_urls():
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
            if resp.status_code != 200:
                continue
            parsed = feedparser.parse(resp.content)
            for entry in parsed.entries[:limit]:
                link = _abs_tlv_url(getattr(entry, "link", ""))
                if link in seen:
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


def fetch_tlv_html(limit: int = 300) -> list[dict[str, Any]]:
    """Scrape TLV's decision pages and archives for direct decision links."""
    events: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for page_url in TLV_DECISION_PAGES:
        try:
            resp = requests.get(page_url, headers={"User-Agent": USER_AGENT}, timeout=30)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            for item in soup.select("article, .sv-channel-item, li, tr"):
                link_el = item.select_one("a[href]")
                if not link_el:
                    continue
                href = _abs_tlv_url(link_el.get("href"))
                if "/beslut/" not in href or href in seen_urls or href.rstrip("/") == page_url.rstrip("/"):
                    continue

                title = link_el.get_text(" ", strip=True)
                if len(title) < 4:
                    continue

                text = item.get_text(" ", strip=True)
                date_str = _parse_date(text)
                if not date_str:
                    continue

                seen_urls.add(href)
                update_type, status = _classify_tlv(f"{title} {text}")
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
                        "indication": text[:450],
                        "summary": text[:450],
                        "url": href,
                    }
                )
                if len(events) >= limit:
                    return events
        except Exception as exc:
            logger.warning("Failed TLV HTML %s: %s", page_url, exc)

    return events


def fetch_tlv() -> list[dict[str, Any]]:
    events = fetch_tlv_rss() + fetch_tlv_html()
    events.sort(key=lambda e: e["date"], reverse=True)
    return events
