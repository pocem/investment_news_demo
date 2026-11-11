"""Prices from Yahoo Finance via yfinance: indices, commodities, sectors, stocks.

All weekly numbers are "last week": the close on the last trading day of
last week vs the close on the last trading day of the week before.
"latest" is the most recent close available at run time (on a Monday run
that is Monday's move, which is the snapshot the newsletter uses for its
sector heatmap).
"""

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

from .util import pct, rnd

# yfinance keeps a SQLite timezone cache that can fail with "database is
# locked" on Windows; keep it inside the project instead.
_CACHE = Path(__file__).resolve().parent.parent / ".cache" / "yfinance"
_CACHE.mkdir(parents=True, exist_ok=True)
yf.set_tz_cache_location(str(_CACHE))

DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday"]


def download_closes(symbols, start: date) -> pd.DataFrame:
    symbols = list(dict.fromkeys(symbols))
    df = yf.download(
        symbols, start=start.isoformat(), progress=False, threads=False, auto_adjust=True
    )["Close"]
    if isinstance(df, pd.Series):
        df = df.to_frame(symbols[0])
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df


def _close_on_or_before(s: pd.Series, d: date):
    s = s[s.index <= pd.Timestamp(d)]
    return (s.index[-1].date(), float(s.iloc[-1])) if len(s) else (None, None)


def series_stats(s: pd.Series, weeks) -> dict:
    s = s.dropna()
    if s.empty:
        return {"error": "no data"}
    lw = weeks.last_week

    end_day, end_close = _close_on_or_before(s, lw.end)
    _, prev_close = _close_on_or_before(s, lw.start - timedelta(days=1))
    _, ytd_base = _close_on_or_before(s, date(lw.end.year - 1, 12, 31))

    # Daily moves during last week
    daily = {}
    for i, name in enumerate(DAY_NAMES):
        d = lw.start + timedelta(days=i)
        if pd.Timestamp(d) in s.index:
            pos = s.index.get_loc(pd.Timestamp(d))
            prev = float(s.iloc[pos - 1]) if pos > 0 else None
            daily[name] = {"close": rnd(s.iloc[pos]), "change_pct": pct(float(s.iloc[pos]), prev)}
        else:
            daily[name] = None  # market closed

    # Distance from the 52-week high, as of last week's close
    year = s[(s.index > pd.Timestamp(lw.end - timedelta(days=365))) & (s.index <= pd.Timestamp(lw.end))]
    high_day = year.idxmax().date() if len(year) else None
    high = float(year.max()) if len(year) else None

    latest_day = s.index[-1].date()
    latest = float(s.iloc[-1])
    latest_prev = float(s.iloc[-2]) if len(s) > 1 else None

    return {
        "last_week": {
            "close": rnd(end_close),
            "close_date": end_day.isoformat() if end_day else None,
            "change_pct": pct(end_close, prev_close),
            "change_abs": rnd(end_close - prev_close) if end_close and prev_close else None,
            "daily": daily,
        },
        "ytd_pct": pct(end_close, ytd_base),
        "high_52w": rnd(high),
        "high_52w_date": high_day.isoformat() if high_day else None,
        "below_52w_high_pct": pct(end_close, high),
        "latest": {
            "date": latest_day.isoformat(),
            "close": rnd(latest),
            "day_change_pct": pct(latest, latest_prev),
            "since_last_week_close_pct": pct(latest, end_close) if latest_day > lw.end else None,
            "ytd_pct": pct(latest, _close_on_or_before(s, date(latest_day.year - 1, 12, 31))[1]),
        },
    }


def _start(weeks) -> date:
    return weeks.last_week.end - timedelta(days=400)


def fetch_prices(groups: dict, weeks) -> dict:
    """groups: {"us": {"S&P 500": "^GSPC", ...}, ...} -> same shape with stats."""
    symbols = [sym for g in groups.values() for sym in g.values()]
    df = download_closes(symbols, _start(weeks))
    out = {}
    for group, items in groups.items():
        out[group] = {}
        for name, sym in items.items():
            stats = series_stats(df[sym], weeks) if sym in df else {"error": "no data"}
            out[group][name] = {"symbol": sym, **stats}
    return out


def fetch_movers(watchlist: dict, weeks) -> dict:
    df = download_closes(list(watchlist), _start(weeks))
    rows = []
    for sym, name in watchlist.items():
        if sym not in df:
            continue
        st = series_stats(df[sym], weeks)
        if "error" in st:
            continue
        rows.append(
            {
                "symbol": sym,
                "name": name,
                "week_change_pct": st["last_week"]["change_pct"],
                "ytd_pct": st["ytd_pct"],
                "below_52w_high_pct": st["below_52w_high_pct"],
                "biggest_day": min(
                    (
                        (d, v["change_pct"])
                        for d, v in st["last_week"]["daily"].items()
                        if v and v["change_pct"] is not None
                    ),
                    key=lambda x: -abs(x[1]),
                    default=(None, None),
                ),
                "latest_day_change_pct": st["latest"]["day_change_pct"],
                "latest_date": st["latest"]["date"],
            }
        )
    rows = [r for r in rows if r["week_change_pct"] is not None]
    rows.sort(key=lambda r: r["week_change_pct"], reverse=True)
    for r in rows:
        day, move = r.pop("biggest_day")
        r["biggest_day_move"] = {"day": day, "change_pct": move}
    return {"ranked_by_week_change": rows}


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
    df = download_closes(syms, _start(weeks))
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
