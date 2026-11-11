"""Google News search via its public RSS feed (no key).

Supports date ranges through the after:/before: search operators, so it can
cover all of last week (unlike Finnhub's latest-headlines feed). Links point
to Google News redirect URLs. Keep usage light: a handful of searches per run.
"""

import re
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

from .util import BROWSER_HEADERS

URL = "https://news.google.com/rss/search"


def _norm(title: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", title.lower())[:80]


def search(query: str, start: date, end: date, limit: int) -> list:
    """Articles published from `start` up to and including `end`."""
    q = f"{query} after:{start.isoformat()} before:{(end + timedelta(days=1)).isoformat()}"
    r = requests.get(
        URL, params={"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"}, headers=BROWSER_HEADERS, timeout=30
    )
    r.raise_for_status()
    items = []
    for it in ET.fromstring(r.content).findall(".//item"):
        source = it.findtext("source") or ""
        title = it.findtext("title") or ""
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3]
        try:
            published = parsedate_to_datetime(it.findtext("pubDate")).astimezone(timezone.utc)
        except (TypeError, ValueError):
            published = None
        if published and not (start <= published.date() <= end):
            continue
        items.append(
            {
                "published": published.isoformat() if published else None,
                "title": title,
                "source": source,
                "url": it.findtext("link"),
            }
        )
        if len(items) >= limit:
            break
    return items


def fetch(queries: dict, start: date, end: date, limit: int, pause: float = 1.5) -> dict:
    """Run several searches; drop headlines already seen under an earlier topic."""
    seen, out = set(), {}
    for i, (topic, q) in enumerate(queries.items()):
        if i:
            time.sleep(pause)
        rows = []
        for a in search(q, start, end, limit * 2):
            key = _norm(a["title"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(a)
            if len(rows) >= limit:
                break
        out[topic] = rows
    return {"source": "Google News search", "from": start.isoformat(), "to": end.isoformat(), "topics": out}
