"""Finnhub (free tier): news, earnings calendar, company profiles, holidays.

Free tier limit is 60 calls/minute; the client spaces calls out and retries
once on HTTP 429. Indices, price candles and the economic calendar are
premium-only, which is why those come from other sources.
"""

import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from .util import rnd

BASE = "https://finnhub.io/api/v1"
_CAP_CACHE = Path(__file__).resolve().parent.parent / ".cache" / "market_caps.json"
_CAP_CACHE_DAYS = 14


class Finnhub:
    def __init__(self, api_key: str, min_interval: float = 1.05):
        self.key = api_key
        self.min_interval = min_interval
        self._last = 0.0
        self.session = requests.Session()

    def get(self, path: str, **params):
        params["token"] = self.key
        for attempt in range(3):
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            r = self.session.get(BASE + path, params=params, timeout=20)
            if r.status_code == 429:
                time.sleep(10 * (attempt + 1))
                continue
            if r.status_code == 403:
                raise PermissionError(f"Finnhub {path}: not available on this plan")
            r.raise_for_status()
            return r.json()
        raise RuntimeError(f"Finnhub {path}: rate limited")

    # --- news --------------------------------------------------------------
    @staticmethod
    def _article(a: dict) -> dict:
        return {
            "datetime": datetime.fromtimestamp(a["datetime"], tz=timezone.utc).isoformat(),
            "headline": a.get("headline"),
            "source": a.get("source"),
            "summary": (a.get("summary") or "")[:400],
            "url": a.get("url"),
        }

    def general_news(self, since: date, limit: int) -> list:
        """Finnhub only returns the latest ~100 general headlines, so on a
        Monday run this reaches back a few days, not the whole of last week."""
        cutoff = datetime.combine(since, datetime.min.time(), tzinfo=timezone.utc).timestamp()
        items = [a for a in self.get("/news", category="general") if a["datetime"] >= cutoff]
        items.sort(key=lambda a: a["datetime"], reverse=True)
        return [self._article(a) for a in items[:limit]]

    def company_news(self, watchlist: dict, start: date, end: date, per_symbol: int) -> dict:
        out = {}
        for sym, keywords in watchlist.items():
            items = self.get("/company-news", symbol=sym, **{"from": start.isoformat(), "to": end.isoformat()})
            kw = [k.lower() for k in keywords]
            relevant = [a for a in items if any(k in (a.get("headline") or "").lower() for k in kw)]
            seen, picked = set(), []
            for a in sorted(relevant, key=lambda a: a["datetime"], reverse=True):
                h = a.get("headline")
                if h in seen:
                    continue
                seen.add(h)
                picked.append(self._article(a))
                if len(picked) >= per_symbol:
                    break
            out[sym] = picked
        return out

    # --- earnings ----------------------------------------------------------
    def _market_caps(self, symbols) -> dict:
        """Market cap in USD bn, cached on disk for a couple of weeks."""
        cache = {}
        if _CAP_CACHE.exists():
            cache = json.loads(_CAP_CACHE.read_text())
        fresh_after = (date.today() - timedelta(days=_CAP_CACHE_DAYS)).isoformat()
        caps = {}
        for sym in symbols:
            hit = cache.get(sym)
            if hit and hit["fetched"] >= fresh_after:
                caps[sym] = hit
                continue
            p = self.get("/stock/profile2", symbol=sym) or {}
            hit = {
                "cap_bn": rnd((p.get("marketCapitalization") or 0) / 1000),
                "name": p.get("name"),
                "industry": p.get("finnhubIndustry"),
                "currency": p.get("currency"),
                "fetched": date.today().isoformat(),
            }
            cache[sym] = caps[sym] = hit
        _CAP_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _CAP_CACHE.write_text(json.dumps(cache, indent=1))
        return caps

    def earnings(self, last_week, this_week, min_cap_bn: float, always: set) -> dict:
        # One call per day: a multi-day range gets silently truncated
        # (the earliest days go missing).
        cal = []
        for w in (last_week, this_week):
            for i in range(5):
                d = (w.start + timedelta(days=i)).isoformat()
                cal += self.get("/calendar/earnings", **{"from": d, "to": d}).get("earningsCalendar", [])

        # Pre-filter before looking up market caps (one API call each).
        # Revenue estimates are in local currency, so this is generous.
        candidates = {
            e["symbol"] for e in cal if (e.get("revenueEstimate") or 0) > 1e9 or e["symbol"] in always
        }
        caps = self._market_caps(sorted(candidates))

        def keep(e):
            c = caps.get(e["symbol"])
            return c and (e["symbol"] in always or (c["cap_bn"] or 0) >= min_cap_bn)

        def row(e):
            c = caps[e["symbol"]]
            eps_a, eps_e = e.get("epsActual"), e.get("epsEstimate")
            rev_a, rev_e = e.get("revenueActual"), e.get("revenueEstimate")
            r = {
                "symbol": e["symbol"],
                "name": c["name"],
                "industry": c["industry"],
                "market_cap_usd_bn": c["cap_bn"],
                "date": e["date"],
                "timing": {"bmo": "before open", "amc": "after close", "dmh": "during market"}.get(
                    e.get("hour"), e.get("hour") or None
                ),
                "eps_estimate": rnd(eps_e, 4),
                "revenue_estimate": rev_e,
            }
            if eps_a is not None or rev_a is not None:
                r.update(
                    {
                        "eps_actual": rnd(eps_a, 4),
                        "revenue_actual": rev_a,
                        "eps_beat": eps_a > eps_e if eps_a is not None and eps_e is not None else None,
                        "revenue_beat": rev_a > rev_e if rev_a and rev_e else None,
                        "revenue_surprise_pct": rnd((rev_a / rev_e - 1) * 100) if rev_a and rev_e else None,
                    }
                )
            return r

        def in_window(e, w):
            return w.start.isoformat() <= e["date"] <= w.end.isoformat()

        def section(w):
            rows = [row(e) for e in cal if in_window(e, w) and keep(e)]
            rows.sort(key=lambda r: (r["date"], -(r["market_cap_usd_bn"] or 0)))
            return rows

        return {
            "source": f"Finnhub earnings calendar, US-listed, market cap >= ${min_cap_bn}bn or watchlist",
            "last_week": section(last_week),
            "this_week": section(this_week),
        }

    # --- holidays ----------------------------------------------------------
    def market_holidays(self, window, bond_holidays: dict) -> dict:
        start, end = window.start.isoformat(), window.end.isoformat()
        data = self.get("/stock/market-holiday", exchange="US").get("data", [])
        return {
            "us_stocks": [
                {"date": h["atDate"], "event": h["eventName"], "trading_hours": h.get("tradingHour") or "closed"}
                for h in data
                if start <= h["atDate"] <= end
            ],
            "us_bonds": [
                {"date": d, "event": name} for d, name in sorted(bond_holidays.items()) if start <= d <= end
            ],
        }
