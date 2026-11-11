"""Economic calendar (CPI, PPI, jobs, GDP, central banks...) with forecasts.

Finnhub's economic calendar is premium-only, so this uses the free Forex
Factory weekly feed. It only covers the *current* Sun-Sat week, so it lines
up with "this week" when the script runs on Sunday or Monday. A Saturday run
still sees the week that just ended. The feed is also rate-limited, so avoid
running it more than a couple of times in five minutes.
"""

from collections import Counter

import requests

from .util import BROWSER_HEADERS

URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


def fetch(window, countries, impacts) -> dict:
    r = requests.get(URL, headers=BROWSER_HEADERS, timeout=20)
    r.raise_for_status()
    events = r.json()

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
