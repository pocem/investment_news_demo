"""Collect the data for one Snowball News issue.

Usage:
    python fetch_weekly_data.py                 # run date = today
    python fetch_weekly_data.py --date 2026-11-09

Meant to run on Sunday or Monday. Covers:
  - last week:  markets recap (incl. intraday lows), movers (watchlist, S&P 500,
                Europe, Asia), sectors, earnings results, economic results vs
                forecasts, central bank rates, news by topic
  - this week:  earnings with options-implied moves, economic calendar with
                forecasts, stock & bond market holidays, week-ahead previews
  - now:        CNN Fear & Greed, Fed rate-decision odds (Kalshi)

Keys in .env: FINNHUB_API_KEY, FRED_API_KEY.

Writes output/<YYYY>-W<NN>.json (the week number of the week being previewed).
Each section is fetched independently; a failure is recorded under "errors"
and the rest of the run continues.
"""

import argparse
import json
import os
import sys
import time
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

import config
from sources import econ_calendar, fear_greed, fed_odds, fred, google_news, market_data
from sources.finnhub_client import Finnhub
from sources.fred import Fred
from weeks import issue_weeks

ROOT = Path(__file__).resolve().parent


def log(msg: str):
    print(msg, file=sys.stderr, flush=True)


def run_section(name, fn, result, errors):
    log(f"- {name} ...")
    t = time.monotonic()
    try:
        result[name] = fn()
        log(f"  ok ({time.monotonic() - t:.1f}s)")
    except Exception as e:  # keep going; report at the end
        errors[name] = f"{type(e).__name__}: {e}"
        log(f"  FAILED: {errors[name]}")
        if os.environ.get("DEBUG"):
            traceback.print_exc()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--date", type=date.fromisoformat, default=date.today(), help="run date (YYYY-MM-DD)")
    p.add_argument("--out", type=Path, default=None, help="output file (default: output/<week>.json)")
    args = p.parse_args()

    load_dotenv(ROOT / ".env")
    missing = [k for k in ("FINNHUB_API_KEY", "FRED_API_KEY") if not os.environ.get(k)]
    if missing:
        sys.exit(f"Missing in .env: {', '.join(missing)}")

    weeks = issue_weeks(args.date)
    lw, tw = weeks.last_week, weeks.this_week
    log(f"Issue {weeks.label}: last week {lw.start}..{lw.end}, this week {tw.start}..{tw.end}")
    if args.date.weekday() in (1, 2, 3, 4):
        log("  note: mid-week run; 'this week' is the current week and its data is partly in the past")

    fh = Finnhub(os.environ["FINNHUB_API_KEY"])
    fr = Fred(os.environ["FRED_API_KEY"])
    data, errors = {}, {}
    weekend_end = lw.end + timedelta(days=2)  # recap news runs through Sunday
    news_to = min(args.date, date.today())

    # --- mood & last week's markets ---
    run_section("fear_greed", lambda: fear_greed.fetch(lw.start), data, errors)
    run_section("fed_rate_odds", lambda: fed_odds.fetch(config.KALSHI_FED_SERIES, config.KALSHI_MEETINGS),
                data, errors)
    run_section("markets", lambda: market_data.fetch_prices(
        {**config.INDICES, "commodities_fx_rates": config.COMMODITIES_FX_RATES}, weeks), data, errors)
    run_section("sectors", lambda: market_data.fetch_sectors(weeks), data, errors)
    run_section("movers", lambda: market_data.fetch_movers(
        config.WATCHLIST,
        {"us_sp500": market_data.sp500_constituents(), "europe": config.MOVERS_EUROPE, "asia": config.MOVERS_ASIA},
        weeks, config.MOVERS_TOP_N), data, errors)

    # --- economy: last week's results, current rates ---
    # Fetch this week's calendar first: it also saves the snapshot that next
    # week's run will use for "actual vs forecast".
    run_section("economic_calendar_this_week", lambda: econ_calendar.fetch(
        tw, config.ECON_COUNTRIES, config.ECON_IMPACT), data, errors)
    run_section("economic_results_last_week", lambda: fred.last_week_results(
        fr, econ_calendar.load_snapshot(lw.start), lw, config.FRED_EVENT_MAP), data, errors)
    run_section("economic_indicators", lambda: fred.headline_indicators(fr, config.FRED_HEADLINE, lw),
                data, errors)
    run_section("central_bank_rates", lambda: fred.central_bank_rates(fr, config.CENTRAL_BANK_RATES, lw),
                data, errors)

    # --- earnings ---
    run_section("earnings", lambda: fh.earnings(
        lw, tw, config.EARNINGS_MIN_MARKET_CAP_USD_BN, config.EARNINGS_ALWAYS_INCLUDE), data, errors)
    run_section("earnings_international", lambda: {
        "last_week": market_data.fetch_international_earnings(config.EARNINGS_INTERNATIONAL, lw),
        "this_week": market_data.fetch_international_earnings(config.EARNINGS_INTERNATIONAL, tw),
    }, data, errors)
    if "earnings" in data:
        run_section("earnings_implied_moves_this_week", lambda: market_data.fetch_implied_moves(
            data["earnings"]["this_week"], config.EARNINGS_ALWAYS_INCLUDE, config.IMPLIED_MOVE_MAX_COMPANIES),
            data, errors)

    run_section("market_holidays_this_week", lambda: fh.market_holidays(tw, config.BOND_MARKET_HOLIDAYS),
                data, errors)

    # --- news ---
    run_section("news_last_week", lambda: google_news.fetch(
        config.NEWS_QUERIES_LAST_WEEK, lw.start, min(weekend_end, news_to), config.NEWS_PER_QUERY), data, errors)
    run_section("news_week_ahead", lambda: google_news.fetch(
        config.NEWS_QUERIES_WEEK_AHEAD, lw.end, news_to, config.NEWS_PER_QUERY), data, errors)
    run_section("news_latest_headlines", lambda: fh.general_news(lw.start, config.GENERAL_NEWS_LIMIT),
                data, errors)
    run_section("news_companies", lambda: fh.company_news(
        config.NEWS_WATCHLIST, lw.start, news_to, config.COMPANY_NEWS_PER_SYMBOL), data, errors)

    out = {
        "meta": {
            "issue": weeks.label,
            "run_date": args.date.isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "last_week": lw.as_dict(),
            "this_week": tw.as_dict(),
            "notes": [
                "Rate odds are Kalshi prediction-market prices, not CME FedWatch.",
                "Economic actual-vs-forecast needs the calendar snapshot from the previous week's run "
                "(data/econ_calendar/). Only US releases are matched to FRED.",
                "Euro-area flash inflation/GDP and BoE/ECB decisions: check news_last_week; FRED lags for these.",
            ],
        },
        **data,
        "errors": errors,
    }

    path = args.out or ROOT / "output" / f"{weeks.label}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    log(f"\nWrote {path}")
    if errors:
        log(f"{len(errors)} section(s) failed: {', '.join(errors)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
