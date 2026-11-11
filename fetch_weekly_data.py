"""Collect the data for one Snowball News issue.

Usage:
    python fetch_weekly_data.py                 # run date = today
    python fetch_weekly_data.py --date 2026-11-09

Meant to run on Saturday, Sunday or Monday. Covers:
  - last week:  markets recap, movers, sectors, earnings results, news
  - this week:  earnings, economic calendar (with forecasts), market holidays
plus the current CNN Fear & Greed reading.

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
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

import config
from sources import econ_calendar, fear_greed, market_data
from sources.finnhub_client import Finnhub
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
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        sys.exit("FINNHUB_API_KEY is missing; put it in .env")

    weeks = issue_weeks(args.date)
    lw, tw = weeks.last_week, weeks.this_week
    log(f"Issue {weeks.label}: last week {lw.start}..{lw.end}, this week {tw.start}..{tw.end}")
    if args.date.weekday() in (1, 2, 3, 4):
        log("  note: mid-week run; 'this week' is the current week and its data is partly in the past")

    fh = Finnhub(api_key)
    data, errors = {}, {}

    run_section("fear_greed", lambda: fear_greed.fetch(lw.start), data, errors)
    run_section("markets", lambda: market_data.fetch_prices(
        {**config.INDICES, "commodities_fx_rates": config.COMMODITIES_FX_RATES}, weeks), data, errors)
    run_section("sectors", lambda: market_data.fetch_sectors(weeks), data, errors)
    run_section("movers", lambda: market_data.fetch_movers(config.WATCHLIST, weeks), data, errors)
    run_section("earnings", lambda: fh.earnings(
        lw, tw, config.EARNINGS_MIN_MARKET_CAP_USD_BN, config.EARNINGS_ALWAYS_INCLUDE), data, errors)
    run_section("earnings_international", lambda: {
        "last_week": market_data.fetch_international_earnings(config.EARNINGS_INTERNATIONAL, lw),
        "this_week": market_data.fetch_international_earnings(config.EARNINGS_INTERNATIONAL, tw),
    }, data, errors)
    run_section("economic_calendar_this_week", lambda: econ_calendar.fetch(
        tw, config.ECON_COUNTRIES, config.ECON_IMPACT), data, errors)
    run_section("market_holidays_this_week", lambda: fh.market_holidays(tw), data, errors)
    run_section("news_general", lambda: fh.general_news(lw.start, config.GENERAL_NEWS_LIMIT), data, errors)
    run_section("news_companies", lambda: fh.company_news(
        config.NEWS_WATCHLIST, lw.start, args.date, config.COMPANY_NEWS_PER_SYMBOL), data, errors)

    out = {
        "meta": {
            "issue": weeks.label,
            "run_date": args.date.isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "last_week": lw.as_dict(),
            "this_week": tw.as_dict(),
            "not_covered": [
                "Rate-hike odds (CME FedWatch has no free API)",
                "Last week's macro actuals (e.g. jobs report): the free calendar only covers this week",
                "Policy/political events (elections, regulation): use the news sections",
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
