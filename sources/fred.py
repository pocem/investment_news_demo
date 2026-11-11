"""FRED (St. Louis Fed): actual economic numbers and central bank rates.

FRED has the actual results but not economists' forecasts. Forecasts come
from the Forex Factory calendar snapshot saved during the week in question
(see econ_calendar.load_snapshot), so "actual vs forecast" for last week only
works if the script ran at some point during or just before last week.
"""

from datetime import date, datetime, timedelta

import requests

from .util import rnd

BASE = "https://api.stlouisfed.org/fred"


class Fred:
    def __init__(self, api_key: str):
        self.key = api_key
        self.session = requests.Session()
        self._cache = {}

    def _get(self, path, **params):
        params.update(api_key=self.key, file_type="json")
        r = self.session.get(f"{BASE}/{path}", params=params, timeout=20)
        r.raise_for_status()
        return r.json()

    def series(self, sid: str) -> dict:
        """Series info plus the last ~26 observations (oldest first)."""
        if sid not in self._cache:
            info = self._get("series", series_id=sid)["seriess"][0]
            obs = self._get("series/observations", series_id=sid, sort_order="desc", limit=26)["observations"]
            obs = [(o["date"], float(o["value"])) for o in reversed(obs) if o["value"] not in (".", "")]
            self._cache[sid] = {
                "title": info["title"],
                "units": info.get("units_short"),
                "frequency": info.get("frequency_short"),
                "last_updated": info["last_updated"][:10],
                "obs": obs,
            }
        return self._cache[sid]

    def headline_value(self, sid: str, transform: str, offset: int = 0):
        """(period, value, previous value) for the latest observation."""
        obs = self.series(sid)["obs"]

        def val(i):  # i = position from the end (0 = latest)
            j = len(obs) - 1 - i
            if j < 0:
                return None
            if transform == "level":
                return obs[j][1]
            if transform == "level_k":
                return obs[j][1] / 1000
            if j < 1:
                return None
            if transform == "mom":
                return (obs[j][1] / obs[j - 1][1] - 1) * 100
            if transform == "diff_k":
                return obs[j][1] - obs[j - 1][1]
            if transform == "yoy":
                return (obs[j][1] / obs[j - 12][1] - 1) * 100 if j >= 12 else None
            raise ValueError(transform)

        period = obs[-1 - offset][0] if len(obs) > offset else None
        return period, val(offset), val(offset + 1)


def _num(s):
    """'0.3%' / '165K' / '-1.2M' -> float in the same units FRED gives."""
    if not s:
        return None
    s = s.strip().replace(",", "")
    mult = 1.0
    if s.endswith("%"):
        s = s[:-1]
    elif s[-1:] in "KMB":
        mult = {"K": 1, "M": 1000, "B": 1_000_000}[s[-1]]
        s = s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return None


def last_week_results(fred: Fred, snapshot: list, window, event_map: dict) -> dict:
    """Join last week's calendar (with forecasts) to FRED actuals."""
    if not snapshot:
        return {
            "note": "No calendar snapshot saved for last week, so forecasts are unknown. "
            "Running the script during each week (Sunday/Monday is enough) fixes this going forward.",
            "results": [],
        }
    start, end = window.start.isoformat(), window.end.isoformat()
    rows = []
    for e in snapshot:
        d = e["date"][:10]
        if not (start <= d <= end) or e["country"] != "USD" or e["impact"] not in ("High", "Medium"):
            continue
        row = {
            "date": d,
            "event": e["title"],
            "impact": e["impact"],
            "forecast": e.get("forecast") or None,
            "previous": e.get("previous") or None,
            "actual": None,
            "vs_forecast": None,
        }
        m = event_map.get(e["title"])
        if m:
            sid, transform = m
            s = fred.series(sid)
            if s["last_updated"] >= d:
                period, actual, _ = fred.headline_value(sid, transform)
                row.update(actual=rnd(actual, 1), period=period, fred_series=sid)
                f = _num(row["forecast"])
                if actual is not None and f is not None:
                    diff = round(actual, 1) - f
                    row["vs_forecast"] = "above" if diff > 0.05 else "below" if diff < -0.05 else "in line"
            else:
                row["actual_note"] = f"FRED not yet updated (last update {s['last_updated']})"
        elif e.get("forecast"):
            row["actual_note"] = "no FRED mapping; check the release"
        rows.append(row)
    rows.sort(key=lambda r: r["date"])
    return {
        "source": "Forecasts: Forex Factory snapshot. Actuals: FRED.",
        "note": "m/m actuals are computed from FRED's index levels and can differ by 0.1 from the "
        "official headline; double-check close calls against the release.",
        "results": rows,
    }


def headline_indicators(fred: Fred, indicators: dict, window) -> list:
    out = []
    released_from = window.start.isoformat()
    released_to = (window.end + timedelta(days=2)).isoformat()
    for label, (sid, transform) in indicators.items():
        s = fred.series(sid)
        period, value, prev = fred.headline_value(sid, transform)
        out.append(
            {
                "indicator": label,
                "period": period,
                "value": rnd(value, 2),
                "previous": rnd(prev, 2),
                "fred_series": sid,
                "last_updated": s["last_updated"],
                "updated_last_week": released_from <= s["last_updated"] <= released_to,
            }
        )
    return out


def central_bank_rates(fred: Fred, rates: dict, window) -> list:
    out = []
    for label, sid in rates.items():
        obs = fred.series(sid)["obs"]
        latest_date, latest = obs[-1]
        before = [v for d, v in obs if d < window.start.isoformat()]
        prior = before[-1] if before else None
        out.append(
            {
                "rate": label,
                "latest": rnd(latest, 3),
                "as_of": latest_date,
                "before_last_week": rnd(prior, 3),
                "changed": prior is not None and abs(latest - prior) >= 0.1,
                "fred_series": sid,
            }
        )
    return out
