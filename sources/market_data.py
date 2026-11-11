"""Prices from Yahoo Finance via yfinance: indices, commodities, sectors, stocks.

All weekly numbers are "last week": the close on the last trading day of
last week vs the close on the last trading day of the week before.
"latest" is the most recent close available at run time (on a Monday run
that is Monday's move, which is the snapshot the newsletter uses for its
sector heatmap).
"""

import io
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

from .util import BROWSER_HEADERS, pct, rnd

# yfinance keeps a SQLite timezone cache that can fail with "database is
# locked" on Windows; keep it inside the project instead.
_CACHE = Path(__file__).resolve().parent.parent / ".cache"
(_CACHE / "yfinance").mkdir(parents=True, exist_ok=True)
yf.set_tz_cache_location(str(_CACHE / "yfinance"))

DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday"]


def download(symbols, start: date, fields=("Close",)) -> dict:
    """{field: DataFrame (dates x symbols)}"""
    symbols = list(dict.fromkeys(symbols))
    raw = yf.download(symbols, start=start.isoformat(), progress=False, threads=True, auto_adjust=True)
    out = {}
    for f in fields:
        df = raw[f]
        if isinstance(df, pd.Series):
            df = df.to_frame(symbols[0])
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        out[f] = df
    return out


def _close_on_or_before(s: pd.Series, d: date):
    s = s[s.index <= pd.Timestamp(d)]
    return (s.index[-1].date(), float(s.iloc[-1])) if len(s) else (None, None)


def series_stats(s: pd.Series, weeks, low: pd.Series = None, high: pd.Series = None) -> dict:
    s = s.dropna()
    if s.empty:
        return {"error": "no data"}
    lw = weeks.last_week

    end_day, end_close = _close_on_or_before(s, lw.end)
    _, prev_close = _close_on_or_before(s, lw.start - timedelta(days=1))
    _, ytd_base = _close_on_or_before(s, date(lw.end.year - 1, 12, 31))

    # Daily moves during last week, with intraday extremes when available
    daily = {}
    worst_intraday = None
    for i, name in enumerate(DAY_NAMES):
        ts = pd.Timestamp(lw.start + timedelta(days=i))
        if ts not in s.index:
            daily[name] = None  # market closed (or not traded yet)
            continue
        pos = s.index.get_loc(ts)
        prev = float(s.iloc[pos - 1]) if pos > 0 else None
        day = {"close": rnd(s.iloc[pos]), "change_pct": pct(float(s.iloc[pos]), prev)}
        if low is not None and high is not None and ts in low.index and prev:
            lo, hi = low.get(ts), high.get(ts)
            day["intraday_low_pct"] = pct(lo, prev)
            day["intraday_high_pct"] = pct(hi, prev)
            if day["intraday_low_pct"] is not None and (
                worst_intraday is None or day["intraday_low_pct"] < worst_intraday["pct"]
            ):
                worst_intraday = {"day": name, "pct": day["intraday_low_pct"]}
        daily[name] = day

    # Distance from the 52-week high, as of last week's close
    year = s[(s.index > pd.Timestamp(lw.end - timedelta(days=365))) & (s.index <= pd.Timestamp(lw.end))]
    high_day = year.idxmax().date() if len(year) else None
    high52 = float(year.max()) if len(year) else None

    latest_day = s.index[-1].date()
    latest = float(s.iloc[-1])
    latest_prev = float(s.iloc[-2]) if len(s) > 1 else None

    out = {
        "last_week": {
            "close": rnd(end_close),
            "close_date": end_day.isoformat() if end_day else None,
            "change_pct": pct(end_close, prev_close),
            "change_abs": rnd(end_close - prev_close) if end_close and prev_close else None,
            "daily": daily,
        },
        "ytd_pct": pct(end_close, ytd_base),
        "high_52w": rnd(high52),
        "high_52w_date": high_day.isoformat() if high_day else None,
        "below_52w_high_pct": pct(end_close, high52),
        "latest": {
            "date": latest_day.isoformat(),
            "close": rnd(latest),
            "day_change_pct": pct(latest, latest_prev),
            "since_last_week_close_pct": pct(latest, end_close) if latest_day > lw.end else None,
            "ytd_pct": pct(latest, _close_on_or_before(s, date(latest_day.year - 1, 12, 31))[1]),
        },
    }
    if worst_intraday:
        out["last_week"]["worst_intraday_drop"] = worst_intraday
    if end_day and end_day < lw.end:
        out["last_week"]["note"] = f"last close available is {end_day} (holiday or week not finished)"
    return out


def _start(weeks) -> date:
    return weeks.last_week.end - timedelta(days=400)


def fetch_prices(groups: dict, weeks) -> dict:
    """groups: {"us": {"S&P 500": "^GSPC", ...}, ...} -> same shape with stats."""
    symbols = [sym for g in groups.values() for sym in g.values()]
    d = download(symbols, _start(weeks), fields=("Close", "Low", "High"))
    c, lo, hi = d["Close"], d["Low"], d["High"]
    out = {}
    for group, items in groups.items():
        out[group] = {}
        for name, sym in items.items():
            if sym in c:
                stats = series_stats(c[sym], weeks, lo[sym].dropna(), hi[sym].dropna())
            else:
                stats = {"error": "no data"}
            out[group][name] = {"symbol": sym, **stats}
    return out


# --- movers ---------------------------------------------------------------------

def _mover_rows(names: dict, closes: pd.DataFrame, weeks) -> list:
    rows = []
    for sym, name in names.items():
        if sym not in closes:
            continue
        st = series_stats(closes[sym], weeks)
        if "error" in st or st["last_week"]["change_pct"] is None:
            continue
        moves = [
            (d, v["change_pct"]) for d, v in st["last_week"]["daily"].items() if v and v["change_pct"] is not None
        ]
        big_day, big_move = max(moves, key=lambda x: abs(x[1]), default=(None, None))
        rows.append(
            {
                "symbol": sym,
                "name": name,
                "week_change_pct": st["last_week"]["change_pct"],
                "ytd_pct": st["ytd_pct"],
                "below_52w_high_pct": st["below_52w_high_pct"],
                "biggest_day_move": {"day": big_day, "change_pct": big_move},
                "latest_date": st["latest"]["date"],
                "latest_day_change_pct": st["latest"]["day_change_pct"],
            }
        )
    rows.sort(key=lambda r: r["week_change_pct"], reverse=True)
    return rows


def sp500_constituents() -> dict:
    """S&P 500 {yahoo symbol: name}, scraped from Wikipedia, cached 30 days."""
    path = _CACHE / "sp500.json"
    if path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        if cached["fetched"] >= (date.today() - timedelta(days=30)).isoformat():
            return cached["symbols"]
    html = requests.get(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", headers=BROWSER_HEADERS, timeout=30
    ).text
    table = pd.read_html(io.StringIO(html), attrs={"id": "constituents"})[0]
    symbols = {str(r["Symbol"]).replace(".", "-"): r["Security"] for _, r in table.iterrows()}
    path.write_text(json.dumps({"fetched": date.today().isoformat(), "symbols": symbols}), encoding="utf-8")
    return symbols


def fetch_movers(watchlist: dict, regions: dict, weeks, top_n: int) -> dict:
    """Watchlist ranked in full; each region reduced to top/bottom N."""
    universe = dict(watchlist)
    for names in regions.values():
        universe.update(names)
    start = weeks.last_week.start - timedelta(days=400)
    closes = download(list(universe), start)["Close"]

    out = {"watchlist": _mover_rows(watchlist, closes, weeks)}
    missing = []
    for region, names in regions.items():
        rows = _mover_rows(names, closes, weeks)
        missing += [s for s in names if s not in closes or closes[s].dropna().empty]
        out[region] = {
            "universe_size": len(names),
            "with_data": len(rows),
            "top_gainers": rows[:top_n],
            "top_losers": list(reversed(rows[-top_n:])),
        }
    if missing:
        out["symbols_without_data"] = missing
    return out


# --- sectors --------------------------------------------------------------------

def fetch_sectors(weeks) -> dict:
    """The 11 Yahoo Finance sectors: market weight plus day / week / YTD returns."""
    from yfinance.const import SECTOR_INDUSTY_MAPPING  # sic: yfinance's spelling

    meta = {}
    for name in SECTOR_INDUSTY_MAPPING:
        key = name.lower().replace(" ", "-")
        ov = yf.Sector(key).overview or {}
        board = ov.get("message_board_id") or ""  # e.g. "INDEXYH311" -> "^YH311"
        meta[name] = {
            "symbol": "^" + board.removeprefix("INDEX") if board else None,
            "market_weight_pct": rnd((ov.get("market_weight") or 0) * 100),
        }

    syms = [m["symbol"] for m in meta.values() if m["symbol"]]
    df = download(syms, _start(weeks))["Close"]
    rows = []
    for name, m in meta.items():
        row = {"sector": name, "symbol": m["symbol"], "market_weight_pct": m["market_weight_pct"]}
        if m["symbol"] in df:
            st = series_stats(df[m["symbol"]], weeks)
            if "error" not in st:
                row.update(
                    {
                        "last_week_change_pct": st["last_week"]["change_pct"],
                        "ytd_pct_as_of_last_week": st["ytd_pct"],
                        "latest_date": st["latest"]["date"],
                        "latest_day_change_pct": st["latest"]["day_change_pct"],
                        "latest_ytd_pct": st["latest"]["ytd_pct"],
                    }
                )
        rows.append(row)
    rows.sort(key=lambda r: r["market_weight_pct"] or 0, reverse=True)
    return {"source": "Yahoo Finance sectors", "sectors": rows}


# --- earnings helpers -------------------------------------------------------------

def fetch_international_earnings(names: dict, window) -> list:
    """Earnings dates for non-US names (not in Finnhub's free calendar)."""
    out = []
    for sym, name in names.items():
        try:
            cal = yf.Ticker(sym).calendar or {}
        except Exception:
            continue
        for d in cal.get("Earnings Date") or []:
            if window.start <= d <= window.end:
                out.append(
                    {
                        "symbol": sym,
                        "name": name,
                        "date": d.isoformat(),
                        "eps_estimate": rnd(cal.get("Earnings Average"), 4),
                        "revenue_estimate": cal.get("Revenue Average"),
                        "source": "yfinance",
                    }
                )
    return out


def implied_move(symbol: str, earnings_date: str, timing: str | None) -> dict:
    """Expected +/- move priced by options: at-the-money straddle / share price,
    using the first expiry after the earnings reaction day."""
    t = yf.Ticker(symbol)
    d = date.fromisoformat(earnings_date)
    react = d + timedelta(days=1) if timing != "before open" else d
    expiries = [e for e in t.options if date.fromisoformat(e) >= react]
    if not expiries:
        return {"symbol": symbol, "error": "no option expiry after earnings"}
    expiry = expiries[0]
    spot = t.fast_info.get("lastPrice") or t.fast_info.get("previousClose")
    chain = t.option_chain(expiry)

    def mid(row):
        bid, ask, last = row.get("bid"), row.get("ask"), row.get("lastPrice")
        if bid and ask and ask > 0:
            return (bid + ask) / 2
        return last

    calls, puts = chain.calls, chain.puts
    strikes = sorted(set(calls["strike"]) & set(puts["strike"]), key=lambda k: abs(k - spot))
    if not strikes or not spot:
        return {"symbol": symbol, "error": "no usable strikes"}
    k = strikes[0]
    straddle = mid(calls[calls["strike"] == k].iloc[0]) + mid(puts[puts["strike"] == k].iloc[0])
    return {
        "symbol": symbol,
        "earnings_date": earnings_date,
        "timing": timing,
        "expiry_used": expiry,
        "price": rnd(spot),
        "atm_strike": rnd(k),
        "implied_move_pct": rnd(straddle / spot * 100, 1),
    }


def fetch_implied_moves(earnings_rows: list, always: set, max_companies: int) -> dict:
    picked = sorted(earnings_rows, key=lambda r: -(r.get("market_cap_usd_bn") or 0))[:max_companies]
    picked += [r for r in earnings_rows if r["symbol"] in always and r not in picked]
    out, errors = [], {}
    for r in picked:
        try:
            m = implied_move(r["symbol"], r["date"], r.get("timing"))
            m["name"] = r.get("name")
            (errors.__setitem__(r["symbol"], m["error"]) if "error" in m else out.append(m))
        except Exception as e:
            errors[r["symbol"]] = f"{type(e).__name__}: {e}"
    out.sort(key=lambda m: m["earnings_date"])
    return {
        "method": "ATM straddle price / share price, first expiry after the earnings reaction day. "
        "Weekly expiries include a few extra days of normal movement, so this slightly overstates the pure earnings move.",
        "moves": out,
        "errors": errors,
    }
