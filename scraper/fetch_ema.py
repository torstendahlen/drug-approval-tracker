"""Fetch drug approvals, full archive, and indication extensions from EMA."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import feedparser
import requests

logger = logging.getLogger(__name__)

EMA_BASE = "https://www.ema.europa.eu"

EMA_MEDICINES_JSON_URLS = [
    "https://www.ema.europa.eu/en/documents/report/medicines-output-medicines_json-report_en.json",
    "https://www.ema.europa.eu/en/documents/report/medicines-output-medicines-report_en.json",
]

EMA_POST_AUTH_JSON_URLS = [
    "https://www.ema.europa.eu/en/documents/report/medicines-output-post_authorisation_json-report_en.json",
]

EMA_RSS_URLS = [
    "https://www.ema.europa.eu/en/news/rss.xml",
    "https://www.ema.europa.eu/en/medicines/rss.xml",
]

USER_AGENT = "DrugApprovalTracker/1.2 (https://github.com/torstendahlen/drug-approval-tracker)"


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
    return m.group(1) if m else ""


def _abs_ema_url(raw_url: str | None) -> str:
    u = (raw_url or "").strip()
    if not u:
        return f"{EMA_BASE}/en/medicines"
    if u.startswith("http://") or u.startswith("https://"):
        return u
    return urljoin(EMA_BASE, u)


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


def _fetch_json_first(urls: list[str]) -> Any:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=60)
            if resp.status_code == 200:
                logger.info("Fetched EMA JSON from %s", url)
                return resp.json()
            logger.warning("EMA JSON %s returned HTTP %s", url, resp.status_code)
        except Exception as exc:
            logger.warning("Failed EMA JSON %s: %s", url, exc)
    return None


def fetch_ema_json(limit: int = 3000) -> list[dict[str, Any]]:
    """Fetch EMA's full structured human medicines JSON archive."""
    data = _fetch_json_first(EMA_MEDICINES_JSON_URLS)
    if not data:
        return []

    records = data if isinstance(data, list) else data.get("data", [])
    events: list[dict[str, Any]] = []

    for item in records:
        if not isinstance(item, dict):
            continue
        category = str(item.get("category") or item.get("Category") or "").lower()
        if category and "human" not in category:
            continue

        status = str(
            item.get("medicine_status")
            or item.get("opinion_status")
            or item.get("Authorisation status")
            or ""
        ).strip()
        if status.lower() not in ("authorised", "authorized", "positive opinion", ""):
            continue

        name = str(item.get("name_of_medicine") or item.get("Medicine name") or "").strip()
        substance = str(
            item.get("active_substance")
            or item.get("international_non_proprietary_name_common_name")
            or item.get("Active substance")
            or ""
        ).strip()
        atc = str(item.get("atc_code_human") or item.get("ATC code") or "").strip()
        indication = str(item.get("therapeutic_indication") or item.get("Therapeutic indication") or "").strip()
        area = str(
            item.get("pharmacotherapeutic_group_human")
            or item.get("therapeutic_area_mesh")
            or item.get("Therapeutic area")
            or ""
        ).strip()

        ma_date = _parse_date(str(item.get("marketing_authorisation_date") or ""))
        opinion_date = _parse_date(str(item.get("opinion_adopted_date") or ""))
        updated_date = _parse_date(str(item.get("last_updated_date") or item.get("first_published_date") or ""))
        date_str = updated_date or ma_date or opinion_date
        if not name or not date_str:
            continue

        url = _abs_ema_url(str(item.get("medicine_url") or item.get("URL") or ""))

        update_type = "new_drug"
        if ma_date and updated_date and updated_date > ma_date:
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
                "url": url,
            }
        )

    events.sort(key=lambda e: e["date"], reverse=True)
    return events[:limit]


def fetch_ema_post_authorisation(limit: int = 1000) -> list[dict[str, Any]]:
    """Fetch EMA post-authorisation procedures (e.g. extension of indications)."""
    data = _fetch_json_first(EMA_POST_AUTH_JSON_URLS)
    if not data:
        return []

    records = data if isinstance(data, list) else data.get("data", [])
    events: list[dict[str, Any]] = []

    for item in records:
        if not isinstance(item, dict):
            continue
        category = str(item.get("category") or "").lower()
        if category and "human" not in category:
            continue

        name = str(item.get("name_of_medicine") or "").strip()
        substance = str(item.get("active_substance") or item.get("international_non_proprietary_name_common_name") or "").strip()
        proc_status = str(item.get("post_authorisation_procedure_status") or "").strip()
        opinion = str(item.get("post_authorisation_opinion_status") or proc_status or "Post-authorisation").strip()
        date_str = _parse_date(
            str(
                item.get("post_authorisation_opinion_date")
                or item.get("last_updated_date")
                or item.get("first_published_date")
                or ""
            )
        )
        if not name or not date_str:
            continue

        area = str(item.get("therapeutic_area_mesh") or "").strip()
        url = _abs_ema_url(str(item.get("medicine_url") or ""))
        events.append(
            {
                "source": "EMA",
                "drug_name": name,
                "active_substance": substance,
                "atc_code": str(item.get("atc_code_human") or "").strip(),
                "therapeutic_area": area,
                "date": date_str,
                "update_type": "new_indication",
                "status": opinion,
                "title": f"{name} ({substance}) – {opinion}",
                "indication": area,
                "summary": f"EMA post-authorisation ({opinion}).",
                "url": url,
            }
        )

    events.sort(key=lambda e: e["date"], reverse=True)
    return events[:limit]


def fetch_ema_rss(limit: int = 100) -> list[dict[str, Any]]:
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
                link = _abs_ema_url(getattr(entry, "link", ""))
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
    """Combine EMA JSON archive, post-authorisation indication extensions, and RSS."""
    combined = fetch_ema_json() + fetch_ema_post_authorisation() + fetch_ema_rss()
    combined.sort(key=lambda e: e["date"], reverse=True)
    return combined
