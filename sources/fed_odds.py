"""Fed rate-decision odds from Kalshi's prediction market (public API, no key).

These are traded probabilities, similar in spirit to CME FedWatch (which has
no free API) but not identical. Each outcome's price in dollars (0-1) is read
as its probability; they are renormalised to add up to 100%.
"""

import time
from datetime import datetime, timezone

import requests

from .util import BROWSER_HEADERS, rnd

BASE = "https://api.elections.kalshi.com/trade-api/v2"


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _now_price(m):
    last = _f(m.get("last_price_dollars"))
    bid, ask = _f(m.get("yes_bid_dollars")), _f(m.get("yes_ask_dollars"))
    if bid is not None and ask is not None and ask > 0:
        return (bid + ask) / 2
    return last


def _price_days_ago(series, ticker, days):
    now = int(time.time())
    r = requests.get(
        f"{BASE}/series/{series}/markets/{ticker}/candlesticks",
        params={"start_ts": now - (days + 3) * 86400, "end_ts": now - days * 86400, "period_interval": 1440},
        headers=BROWSER_HEADERS,
        timeout=20,
    )
    if not r.ok:
        return None
    candles = r.json().get("candlesticks") or []
    for c in reversed(candles):
        p = _f((c.get("price") or {}).get("close_dollars"))
        if p is None:
            bid = _f((c.get("yes_bid") or {}).get("close_dollars"))
            ask = _f((c.get("yes_ask") or {}).get("close_dollars"))
            p = (bid + ask) / 2 if bid is not None and ask is not None else None
        if p is not None:
            return p
    return None


def _normalise(d):
    total = sum(v for v in d.values() if v is not None)
    if not total:
        return {k: None for k in d}
    return {k: rnd(v / total * 100, 1) if v is not None else None for k, v in d.items()}


def fetch(series: str, meetings: int) -> dict:
    r = requests.get(
        f"{BASE}/events", params={"series_ticker": series, "status": "open", "limit": 100},
        headers=BROWSER_HEADERS, timeout=20,
    )
    r.raise_for_status()
    events = sorted(r.json().get("events", []), key=lambda e: e.get("strike_date") or "9999")
    out = []
    for ev in events[:meetings]:
        mr = requests.get(
            f"{BASE}/markets", params={"event_ticker": ev["event_ticker"], "limit": 50},
            headers=BROWSER_HEADERS, timeout=20,
        )
        mr.raise_for_status()
        markets = mr.json().get("markets", [])
        now, prev_day, week_ago = {}, {}, {}
        for m in markets:
            label = m.get("yes_sub_title") or m["ticker"]
            now[label] = _now_price(m)
            prev_day[label] = _f(m.get("previous_price_dollars"))
            week_ago[label] = _price_days_ago(series, m["ticker"], 7)
        now_n = _normalise(now)
        out.append(
            {
                "meeting_date": (ev.get("strike_date") or "")[:10],
                "event": ev["event_ticker"],
                "probabilities_pct": dict(sorted(now_n.items(), key=lambda kv: -(kv[1] or 0))),
                "previous_day_pct": _normalise(prev_day),
                "one_week_ago_pct": _normalise(week_ago),
                "any_hike_pct": rnd(sum(v or 0 for k, v in now_n.items() if k.lower().startswith("hike")), 1),
                "any_cut_pct": rnd(sum(v or 0 for k, v in now_n.items() if k.lower().startswith("cut")), 1),
            }
        )
    return {
        "source": "Kalshi prediction market (traded odds, not CME FedWatch)",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "meetings": out,
    }
