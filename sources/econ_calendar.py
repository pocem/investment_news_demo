"""Economic calendar (CPI, PPI, jobs, GDP, central banks...) with forecasts.

Finnhub's economic calendar is premium-only, so this uses the free Forex
Factory weekly feed. It only covers the *current* Sun-Sat week, so it lines
up with "this week" when the script runs on Sunday or Monday. A Saturday run
still sees the week that just ended. The feed is also rate-limited, so avoid
running it more than a couple of times in five minutes.
"""

import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import requests

from .util import BROWSER_HEADERS

URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

# Every fetch is saved here, keyed by the Monday of the week it covers, so the
# following week's run can compare actual results against these forecasts.
SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "data" / "econ_calendar"


def _save_snapshot(events: list) -> Path | None:
    days = sorted(e["date"][:10] for e in events)
    if not days:
        return None
    first = date.fromisoformat(days[0])  # feed weeks start on Sunday
    monday = first + timedelta(days=(7 - first.weekday()) % 7)
    path = SNAPSHOT_DIR / f"{monday.isoformat()}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(events, indent=1, ensure_ascii=False), encoding="utf-8")
    return path


def load_snapshot(monday: date) -> list:
    path = SNAPSHOT_DIR / f"{monday.isoformat()}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def fetch(window, countries, impacts) -> dict:
    r = requests.get(URL, headers=BROWSER_HEADERS, timeout=20)
    r.raise_for_status()
    events = r.json()
    _save_snapshot(events)

    start, end = window.start.isoformat(), window.end.isoformat()
    in_window = [e for e in events if start <= e["date"][:10] <= end]

    note = None
    if not in_window and events:
        covered = f"{min(e['date'][:10] for e in events)} to {max(e['date'][:10] for e in events)}"
        note = (
            f"The feed currently covers {covered}, not {start} to {end}. "
            "Run on Sunday or Monday to get this week's calendar."
        )

    kept = [
        {
            "date": e["date"][:10],
            "time_et": e["date"][11:16],
            "country": e["country"],
            "event": e["title"],
            "impact": e["impact"],
            "forecast": e.get("forecast") or None,
            "previous": e.get("previous") or None,
        }
        for e in in_window
        if e["country"] in countries and e["impact"] in impacts
    ]
    kept.sort(key=lambda e: (e["date"], e["time_et"]))

    return {
        "source": "Forex Factory weekly calendar (times are US Eastern)",
        "note": note,
        "events": kept,
        "counts_by_country": dict(Counter(e["country"] for e in kept)),
    }
