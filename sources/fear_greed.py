"""CNN Fear & Greed Index.

Uses the JSON endpoint behind CNN's own page. It is not an official API, so it
may change or start blocking requests without notice.
"""

from datetime import date, datetime, timedelta, timezone

import requests

from .util import BROWSER_HEADERS, rnd

URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

COMPONENTS = [
    "market_momentum_sp500",
    "stock_price_strength",
    "stock_price_breadth",
    "put_call_options",
    "market_volatility_vix",
    "junk_bond_demand",
    "safe_haven_demand",
]


def _rating(score):
    if score is None:
        return None
    if score < 25:
        return "extreme fear"
    if score < 45:
        return "fear"
    if score <= 55:
        return "neutral"
    if score <= 75:
        return "greed"
    return "extreme greed"


def fetch(last_start: date, history_days: int = 45) -> dict:
    r = requests.get(URL, headers=BROWSER_HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()

    fg = data["fear_and_greed"]
    points = data.get("fear_and_greed_historical", {}).get("data", [])

    history = {}
    for p in points:
        day = datetime.fromtimestamp(p["x"] / 1000, tz=timezone.utc).date()
        history[day] = rnd(p["y"], 1)  # last reading of each day wins
    cutoff = date.today() - timedelta(days=history_days)
    daily = [
        {"date": d.isoformat(), "score": s, "rating": _rating(s)}
        for d, s in sorted(history.items())
        if d >= cutoff
    ]

    def on_or_before(d):
        days = [k for k in history if k <= d]
        return history[max(days)] if days else None

    last_week = {}
    for i, name in enumerate(["monday", "tuesday", "wednesday", "thursday", "friday"]):
        s = on_or_before(last_start + timedelta(days=i))
        last_week[name] = {"score": s, "rating": _rating(s)}

    components = {}
    for key in COMPONENTS:
        c = data.get(key) or {}
        components[key] = {"score": rnd(c.get("score"), 1), "rating": c.get("rating")}

    return {
        "source": "CNN Fear & Greed Index (0 = extreme fear, 100 = extreme greed)",
        "current": {
            "score": rnd(fg.get("score"), 1),
            "rating": fg.get("rating"),
            "timestamp": fg.get("timestamp"),
        },
        "previous_close": rnd(fg.get("previous_close"), 1),
        "one_week_ago": rnd(fg.get("previous_1_week"), 1),
        "one_month_ago": rnd(fg.get("previous_1_month"), 1),
        "one_year_ago": rnd(fg.get("previous_1_year"), 1),
        "last_week_by_day": last_week,
        "components": components,
        "daily_history": daily,
    }
