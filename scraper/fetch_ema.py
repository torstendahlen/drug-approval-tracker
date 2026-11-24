"""Fetch recent drug approvals and indication extensions from EMA."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests

logger = logging.getLogger(__name__)

EMA_MEDICINES_JSON_URLS = [
    "https://www.ema.europa.eu/en/documents/report/medicines-output-medicines_json-report_en.json",
    "https://www.ema.europa.eu/en/documents/report/medicines-output-medicines-report_en.json",
]

EMA_RSS_URLS = [
    "https://www.ema.europa.eu/en/news/rss.xml",
    "https://www.ema.europa.eu/en/medicines/rss.xml",
]

USER_AGENT = "DrugApprovalTracker/1.0 (https://github.com/drug-approval-tracker)"


def _parse_date(raw: str | None) -> str:
    if not raw:
        return ""
    raw = raw.strip()
    for fmt in (
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d %B %Y",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
    ):
        try:
            dt = datetime.strptime(raw[:31], fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    m = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        return m.group(1)
    return ""


def _classify_ema_update(text: str, is_initial_ma: bool = False) -> str:
    lower = text.lower()
    if any(
        kw in lower
        for kw in (
            "extension of indication",
            "new indication",
            "therapeutic indication",
            "indication extension",
            "type ii variation",
        )
    ):
        return "new_indication"
    if is_initial_ma or any(
        kw in lower
        for kw in (
            "new medicine",
            "initial marketing authorisation",
            "marketing authorisation",
            "positive opinion",
            "authorised",
            "recommended for approval",
        )
    ):
        return "new_drug"
    return "other"


def fetch_ema_json(limit: int = 250) -> list[dict[str, Any]]:
    """Fetch EMA's structured human medicines JSON report."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    data = None
    for url in EMA_MEDICINES_JSON_URLS:
        try:
            resp = requests.get(url, headers=headers, timeout=45)
            if resp.status_code == 200:
                data = resp.json()
                logger.info("Fetched EMA JSON from %s", url)
                break
        except Exception as exc:
            logger.warning("Failed EMA JSON %s: %s", url, exc)

    if not data:
        return []

    records = data if isinstance(data, list) else data.get("data", [])
    events: list[dict[str, Any]] = []

    for item in records:
        if not isinstance(item, dict):
            continue
        category = str(item.get("Category") or item.get("category") or "").lower()
        if category and "human" not in category:
            continue

        status = str(
            item.get("Authorisation status")
            or item.get("authorisation_status")
            or item.get("Medicine status")
            or ""
        ).strip()
        if status.lower() not in ("authorised", "authorized", "positive opinion", ""):
            continue

        name = str(item.get("Medicine name") or item.get("Name of medicine") or item.get("name") or "").strip()
        substance = str(
            item.get("Active substance")
            or item.get("International non-proprietary name (INN) / common name")
            or item.get("active_substance")
            or ""
        ).strip()
        atc = str(item.get("ATC code") or item.get("atc_code") or "").strip()
        indication = str(item.get("Therapeutic indication") or item.get("therapeutic_indication") or "").strip()
        area = str(item.get("Therapeutic area") or item.get("therapeutic_area") or "").strip()

        rev_date = _parse_date(
            str(
                item.get("Revision date")
                or item.get("Date of opinion")
                or item.get("Marketing authorisation date")
                or item.get("First published")
                or ""
            )
        )
        ma_date = _parse_date(str(item.get("Marketing authorisation date") or ""))
        date_str = rev_date or ma_date
        if not name or not date_str:
            continue

        url = str(item.get("URL") or item.get("url") or "").strip()
        if url and not url.startswith("http"):
            url = f"https://www.ema.europa.eu{url}"

        update_type = "new_drug"
        if ma_date and rev_date and rev_date > ma_date:
            update_type = "new_indication"

        events.append(
            {
                "source": "EMA",
                "drug_name": name,
                "active_substance": substance,
                "atc_code": atc,
                "therapeutic_area": area,
                "date": date_str,
                "update_type": update_type,
                "status": status or "Authorised",
                "title": f"{name} ({substance}) – {status or 'Authorised'}",
                "indication": indication[:600],
                "summary": f"EMA status: {status or 'Authorised'}. MA date: {ma_date or date_str}.",
                "url": url or "https://www.ema.europa.eu/en/medicines",
            }
        )

    events.sort(key=lambda e: e["date"], reverse=True)
    return events[:limit]


def fetch_ema_rss(limit: int = 80) -> list[dict[str, Any]]:
    """Fetch EMA RSS feeds for CHMP highlights, new approvals, and indication extensions."""
    events: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for rss_url in EMA_RSS_URLS:
        try:
            resp = requests.get(rss_url, headers={"User-Agent": USER_AGENT}, timeout=30)
            if resp.status_code != 200:
                continue
            parsed = feedparser.parse(resp.content)
            for entry in parsed.entries[:limit]:
                link = getattr(entry, "link", "")
                if not link or link in seen_urls:
                    continue
                seen_urls.add(link)

                title = getattr(entry, "title", "").strip()
                summary = re.sub(r"<[^>]+>", " ", getattr(entry, "summary", "")).strip()
                summary = re.sub(r"\s+", " ", summary)
                combined = f"{title} {summary}"
                update_type = _classify_ema_update(combined)

                if update_type == "other" and not any(
                    k in combined.lower() for k in ("chmp", "medicine", "epar", "approval", "indication")
                ):
                    continue

                date_str = _parse_date(getattr(entry, "published", "") or getattr(entry, "updated", ""))
                if not date_str:
                    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

                drug_name = title.split(":")[0].split("(")[0].strip()[:60]
                events.append(
                    {
                        "source": "EMA",
                        "drug_name": drug_name,
                        "active_substance": "",
                        "atc_code": "",
                        "therapeutic_area": "",
                        "date": date_str,
                        "update_type": update_type,
                        "status": "CHMP / EMA Update",
                        "title": title,
                        "indication": summary[:400],
                        "summary": summary[:400],
                        "url": link,
                    }
                )
        except Exception as exc:
            logger.warning("Failed EMA RSS %s: %s", rss_url, exc)

    return events


def fetch_ema() -> list[dict[str, Any]]:
    """Combine EMA JSON report and RSS highlights."""
    json_events = fetch_ema_json()
    rss_events = fetch_ema_rss()
    combined = json_events + rss_events
    combined.sort(key=lambda e: e["date"], reverse=True)
    return combined
