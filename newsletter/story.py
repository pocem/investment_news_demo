"""Turn the weekly JSON into plain-English newsletter content.

Rules of thumb for the wording:
  - say what an index is the first time it appears
  - "rose/fell X%" instead of jargon; "hotter than expected" instead of "beat consensus"
  - one idea per sentence, and say why it matters for an ordinary investor
"""

import re
from datetime import date, timedelta

from .visuals import gauge_svg, heat

MINUS = "−"

INDEX_PLAIN = {
    "S&P 500": "the S&P 500 (the 500 biggest US companies)",
    "Nasdaq Composite": "the tech-heavy Nasdaq",
    "Dow Jones": "the Dow (30 large US companies)",
    "Russell 2000": "the Russell 2000 (smaller US companies)",
    "STOXX 600": "the STOXX 600 (600 big European companies)",
    "DAX (Germany)": "Germany's DAX",
    "FTSE 100 (UK)": "the UK's FTSE 100",
    "CAC 40 (France)": "France's CAC 40",
    "Nikkei 225 (Japan)": "Japan's Nikkei",
    "Kospi (South Korea)": "South Korea's Kospi",
    "Hang Seng (Hong Kong)": "Hong Kong's Hang Seng",
    "Shanghai Composite": "mainland China's Shanghai Composite",
    "Taiwan Weighted": "Taiwan's main index",
    "Nifty 50 (India)": "India's Nifty 50",
}

FED_OUTCOME_PLAIN = {
    "Hike 25bps": "Small hike (+0.25 points)",
    "Hike >25bps": "Bigger hike",
    "Fed maintains rate": "No change",
    "Cut 25bps": "Small cut (−0.25 points)",
    "Cut >25bps": "Bigger cut",
}

EVENT_PLAIN = {
    "CPI m/m": "Monthly rise in consumer prices (CPI)",
    "Core CPI m/m": "Consumer prices without food & energy (core CPI)",
    "CPI y/y": "Consumer prices over the past 12 months",
    "PPI m/m": "Monthly rise in prices businesses pay (PPI)",
    "Core PPI m/m": "Business prices without food & energy (core PPI)",
    "Non-Farm Employment Change": "New jobs added",
    "Unemployment Rate": "Unemployment rate",
    "Unemployment Claims": "New jobless claims",
    "Retail Sales m/m": "Shop sales (retail sales)",
    "Core Retail Sales m/m": "Shop sales without cars",
    "Advance GDP q/q": "Economic growth (GDP), first estimate",
    "Prelim GDP q/q": "Economic growth (GDP)",
    "Flash GDP q/q": "Economic growth (GDP), first estimate",
    "GDP m/m": "Economic growth (GDP), monthly",
    "Core PCE Price Index m/m": "The Fed's favourite inflation gauge (core PCE)",
    "FOMC Meeting Minutes": "Notes from the Fed's last meeting",
    "Federal Funds Rate": "Fed interest-rate decision",
    "Main Refinancing Rate": "ECB interest-rate decision",
    "Official Bank Rate": "Bank of England rate decision",
    "Prelim UoM Consumer Sentiment": "Consumer mood survey",
    "Empire State Manufacturing Index": "New York factory survey",
    "Philly Fed Manufacturing Index": "Philadelphia factory survey",
    "Flash Manufacturing PMI": "Factory activity survey (PMI)",
    "Flash Services PMI": "Services activity survey (PMI)",
    "ISM Manufacturing PMI": "Factory activity survey (ISM)",
    "ISM Services PMI": "Services activity survey (ISM)",
    "Building Permits": "New building permits",
    "Housing Starts": "New homes being built",
    "Existing Home Sales": "Home sales",
    "New Home Sales": "New home sales",
    "JOLTS Job Openings": "Job openings",
    "ADP Non-Farm Employment Change": "Private-sector jobs (ADP survey)",
}
SPEAKER_PATTERNS = [
    (r"^FOMC Member (\w+) Speaks$", r"Fed official \1 speaks"),
    (r"^Fed Chair (\w+) Speaks$", r"Fed Chair \1 speaks"),
    (r"^ECB President (\w+) Speaks$", r"ECB head \1 speaks"),
    (r"^BOE Gov (\w+) Speaks$", r"Bank of England head \1 speaks"),
    (r"^BOJ Gov (\w+) Speaks$", r"Bank of Japan head \1 speaks"),
]
COUNTRY = {"USD": "US", "EUR": "Euro area", "GBP": "UK", "JPY": "Japan", "CNY": "China"}
INFLATION_WORDS = ("CPI", "PPI", "PCE")

NEWS_TOPICS = {
    "us_markets": "US markets",
    "fed_economy": "The Fed & the economy",
    "ai_tech": "AI & tech",
    "europe": "Europe",
    "asia_em": "Asia & emerging markets",
    "commodities": "Oil & gold",
    "politics_policy": "Politics & policy",
    "strategist_calls": "What the big banks are saying",
}
NEWS_JUNK = re.compile(r"charts, data and news|price today|stock price|per ounce|live updates|quote", re.I)

GLOSSARY = {
    "correction": (
        "Correction",
        "A correction is when a market falls 10% or more from a recent high. A fall of 20% or more is "
        "called a bear market. Corrections feel scary, but they are a normal part of investing: the S&P 500 "
        "has had several in recent years and has recovered from each of them so far. What matters most is "
        "staying calm and not selling in a panic.",
    ),
    "rate_hike": (
        "Rate hike",
        "When the Federal Reserve (the US central bank) raises its interest rate, borrowing becomes more "
        "expensive for everyone, from home buyers to companies. The Fed does this to cool down inflation. "
        "Higher rates tend to weigh on stocks, especially fast-growing tech companies whose biggest profits "
        "are expected far in the future.",
    ),
    "implied_move": (
        "Implied move",
        "Options are contracts that let investors bet on how much a stock will move. From their prices you "
        "can work out how big a jump traders expect, in either direction. If a company's implied move is "
        "±10%, traders expect its share price to swing by roughly that much after its results, but "
        "they don't know which way.",
    ),
    "fear_greed": (
        "Fear & Greed Index",
        "CNN's Fear & Greed Index combines seven market signals into one number from 0 (extreme fear) to "
        "100 (extreme greed). It is a mirror of investors' emotions, not a buy or sell signal. Extreme fear "
        "has often shown up near market lows, but not always.",
    ),
}


# --- formatting --------------------------------------------------------------------

def pct(x, signed=True, nd=1):
    if x is None:
        return "n/a"
    s = f"{abs(x):.{nd}f}%"
    if not signed:
        return s
    return ("+" if x > 0 else MINUS if x < 0 else "") + s


def verb(x, big=3.0):
    if x is None:
        return "had no data"
    if abs(x) < 0.15:
        return "was flat"
    if x > 0:
        return ("jumped " if x >= big else "rose ") + pct(x, False)
    return ("dropped " if x <= -big else "fell ") + pct(x, False)


def nice_date(iso, weekday=False):
    if not iso:
        return ""
    d = date.fromisoformat(iso[:10])
    return (f"{d:%A} " if weekday else "") + f"{d.day} {d:%B}"


def money(x, unit=""):
    if x is None:
        return "n/a"
    return f"${x:,.0f}{unit}" if x >= 100 else f"${x:,.2f}{unit}"


_SUFFIX = re.compile(
    r"[,.]?\s+(Inc|Incorporated|Corp|Corporation|Co|Company|Companies|Ltd|Limited|PLC|plc|Holding|Holdings|"
    r"Group|SA|NV|N\.V|AG|LP|L\.P|SE|ADR|&|Class [A-C])\.?$"
)
_NAME_FIX = {"NVIDIA": "Nvidia", "Alphabet": "Alphabet (Google)", "Meta Platforms": "Meta"}


def company(name):
    """'TransDigm Group Incorporated' -> 'TransDigm', 'The Walt Disney Co' -> 'Walt Disney'."""
    if not name:
        return ""
    name = name.strip()
    prev = None
    while prev != name:
        prev = name
        name = _SUFFIX.sub("", name).strip()
    name = re.sub(r"^The\s+", "", name)
    return _NAME_FIX.get(name, name)


def event_plain(title):
    if title in EVENT_PLAIN:
        return EVENT_PLAIN[title]
    for pat, rep in SPEAKER_PATTERNS:
        if re.match(pat, title):
            return re.sub(pat, rep, title)
    return title


def cap(s):
    return s[:1].upper() + s[1:] if s else s


# --- the story ----------------------------------------------------------------------

class Story:
    def __init__(self, d: dict):
        self.d = d
        self.meta = d["meta"]
        self.m = d.get("markets", {})

    # helpers
    def idx(self, group, name):
        return (self.m.get(group) or {}).get(name) or {}

    def wk(self, group, name):
        return (self.idx(group, name).get("last_week") or {}).get("change_pct")

    def describe(self, group, names):
        parts = []
        for n in names:
            v = self.wk(group, n)
            if v is not None:
                parts.append(f"{INDEX_PLAIN.get(n, n)} {verb(v)}")
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0]
        return ", ".join(parts[:-1]) + " and " + parts[-1]

    def biggest_day(self, group, name):
        daily = (self.idx(group, name).get("last_week") or {}).get("daily") or {}
        days = [(k, v["change_pct"]) for k, v in daily.items() if v and v.get("change_pct") is not None]
        return max(days, key=lambda kv: abs(kv[1]), default=(None, None))

    def high_sentence(self, group, name, short):
        st = self.idx(group, name)
        b, hd = st.get("below_52w_high_pct"), st.get("high_52w_date")
        if b is None:
            return ""
        if b > -1:
            return f"The {short} ended the week at or near its highest level of the past year."
        where = f"{pct(b, False)} below its peak from {nice_date(hd)}"
        if b > -10:
            return f"The {short} is now {where}: a dip, but not a correction (a fall of 10% or more)."
        if b > -20:
            return f"The {short} is now {where}, which counts as a correction (a fall of 10% or more)."
        return f"The {short} is now {where}, which is bear-market territory (a fall of 20% or more)."

    def intraday_sentence(self, group, name, short, threshold=-3.0):
        w = (self.idx(group, name).get("last_week") or {}).get("worst_intraday_drop")
        close = None
        if w:
            day = ((self.idx(group, name).get("last_week") or {}).get("daily") or {}).get(w["day"]) or {}
            close = day.get("change_pct")
        if not w or w["pct"] > threshold or close is None or w["pct"] - close > -1:
            return ""
        ended = "flat" if abs(close) < 0.15 else f"{'up' if close > 0 else 'down'} {pct(close, False)}"
        return (
            f"On {w['day'].capitalize()}, {short} was down as much as {pct(w['pct'], False)} at one point, "
            f"before ending the day {ended}."
        )

    # sections
    def status(self):
        lw_end = self.meta["last_week"]["end"]
        sp = self.idx("us", "S&P 500").get("last_week") or {}
        if sp.get("close_date") and sp["close_date"] < lw_end:
            return f"Preview: last week isn't over yet. Market data runs to {nice_date(sp['close_date'], True)}."
        return None

    def mood(self):
        fg = self.d.get("fear_greed")
        if not fg:
            return None
        cur = fg["current"]["score"]
        rating = fg["current"]["rating"]
        bits = []
        if fg.get("one_week_ago") is not None:
            bits.append(f"{round(fg['one_week_ago'])} a week ago")
        if fg.get("one_month_ago") is not None:
            bits.append(f"{round(fg['one_month_ago'])} a month ago")
        if fg.get("one_year_ago") is not None:
            bits.append(f"{round(fg['one_year_ago'])} a year ago")
        compare = f" For context, it was {', '.join(bits[:-1])} and {bits[-1]}." if len(bits) > 1 else ""
        return {
            "score": round(cur),
            "rating": rating,
            "gauge": gauge_svg(cur),
            "text": (
                f"CNN's Fear & Greed Index, a 0-to-100 mood meter for US stocks, reads {round(cur)} "
                f"(“{rating}”).{compare} Think of it as a mirror for investors' emotions, "
                "not a buy or sell signal."
            ),
        }

    def fed(self):
        meetings = (self.d.get("fed_rate_odds") or {}).get("meetings") or []
        if not meetings:
            return None
        m = meetings[0]
        probs = m["probabilities_pct"]
        prev = m.get("one_week_ago_pct") or {}
        hike_now = m.get("any_hike_pct") or 0
        cut_now = m.get("any_cut_pct") or 0
        hike_prev = sum(v or 0 for k, v in prev.items() if k.lower().startswith("hike")) if prev else None
        cut_prev = sum(v or 0 for k, v in prev.items() if k.lower().startswith("cut")) if prev else None
        when = nice_date(m["meeting_date"])
        if hike_now >= cut_now:
            main, before, word = hike_now, hike_prev, "raises"
            why = "Higher rates make loans more expensive and tend to weigh on stocks, especially tech."
        else:
            main, before, word = cut_now, cut_prev, "cuts"
            why = "Lower rates make borrowing cheaper, which usually supports stocks."
        change = ""
        if before is not None and any(v is not None for v in prev.values()):
            diff = main - before
            if abs(diff) >= 2:
                change = f", {'up' if diff > 0 else 'down'} from {round(before)}% a week ago"
            else:
                change = ", about the same as a week ago"
        text = (
            f"Traders now see a {round(main)}% chance that the Fed {word} interest rates at its next "
            f"meeting on {when}{change}. {why}"
        )
        bars = [
            {"label": FED_OUTCOME_PLAIN.get(k, k), "pct": v or 0, "prev": prev.get(k)}
            for k, v in probs.items()
            if (v or 0) >= 1
        ]
        nxt = None
        if len(meetings) > 1:
            n = meetings[1]
            nxt = (
                f"For the meeting after that ({nice_date(n['meeting_date'])}), the odds of a hike are "
                f"{round(n.get('any_hike_pct') or 0)}% and of a cut {round(n.get('any_cut_pct') or 0)}%."
            )
        if hike_now >= cut_now:
            title = "Rate-hike odds are rising." if (hike_prev is not None and hike_now - hike_prev >= 5) else (
                "Rate-hike odds are falling." if (hike_prev is not None and hike_prev - hike_now >= 5) else "Rate expectations held steady.")
        else:
            title = "Rate-cut hopes are growing." if (cut_prev is not None and cut_now - cut_prev >= 5) else "Rate expectations shifted."
        return {"text": text, "next": nxt, "bars": bars, "title": title, "short": text.split(". ")[0] + "."}

    def econ_results(self):
        res = (self.d.get("economic_results_last_week") or {}).get("results") or []
        rows = []
        for r in res:
            if not r.get("forecast"):
                continue
            plain = event_plain(r["event"])
            vs = r.get("vs_forecast")
            inflation = any(w in r["event"] for w in INFLATION_WORDS)
            jobs_bad = r["event"] in ("Unemployment Rate", "Unemployment Claims")
            if vs == "above":
                verdict = "hotter than expected" if inflation else ("worse than expected" if jobs_bad else "stronger than expected")
            elif vs == "below":
                verdict = "cooler than expected" if inflation else ("better than expected" if jobs_bad else "weaker than expected")
            elif vs == "in line":
                verdict = "as expected"
            else:
                verdict = "not out yet" if r.get("actual") is None else ""
            unit = "%" if "%" in (r.get("forecast") or "") else ("K" if "K" in (r.get("forecast") or "") else "")
            actual = None if r.get("actual") is None else f"{r['actual']:g}{unit}"
            rows.append(
                {
                    "day": nice_date(r["date"], True),
                    "raw": r["event"],
                    "event": plain,
                    "expected": r["forecast"],
                    "actual": actual,
                    "verdict": verdict,
                    "tone": "up" if vs == "above" else "down" if vs == "below" else "",
                    "inflation": inflation,
                    "impact": r.get("impact"),
                }
            )
        return rows

    def insights(self, fed, econ):
        out = []
        sp, nq = self.wk("us", "S&P 500"), self.wk("us", "Nasdaq Composite")
        if sp is not None:
            if sp >= 2:
                title = "Stocks rallied."
            elif sp >= 0.5:
                title = "Stocks edged higher."
            elif sp > -0.5:
                title = "A choppy, mostly flat week."
            elif sp > -2:
                title = "Stocks slipped."
            else:
                title = "A rough week for stocks."
            day, move = self.biggest_day("us", "S&P 500")
            extra = f" The biggest swing came on {day.capitalize()} ({pct(move)})." if day and abs(move) >= 1 else ""
            out.append({"title": title, "text": f"The S&P 500 {verb(sp)} and the Nasdaq {verb(nq)} last week.{extra}"})
        if fed:
            out.append({"title": fed["title"], "text": fed["short"]})
        priority = ["Non-Farm Employment Change", "CPI m/m", "Core PCE Price Index m/m", "Advance GDP q/q",
                    "Retail Sales m/m", "PPI m/m"]
        hot = [r for r in econ if r["verdict"] and r["verdict"] not in ("not out yet", "") and r["impact"] == "High"]
        hot.sort(key=lambda r: priority.index(r["raw"]) if r["raw"] in priority else 99)
        if hot:
            r = hot[0]
            why = ""
            if r["inflation"] and r["tone"] == "up":
                why = " Hotter inflation makes a Fed rate hike more likely."
            elif r["inflation"] and r["tone"] == "down":
                why = " Cooler inflation takes some pressure off the Fed."
            short_title = re.sub(r"^Monthly rise in ", "", r["event"].split(" (")[0])
            out.append(
                {
                    "title": f"{cap(short_title)}: {r['verdict']}.",
                    "text": f"{r['event']} came in at {r['actual']} vs {r['expected']} expected.{why}",
                }
            )
        wl = (self.d.get("movers") or {}).get("watchlist") or []
        if len(wl) >= 2:
            top, bot = wl[0], wl[-1]
            out.append(
                {
                    "title": "Winners and losers.",
                    "text": f"Among the big names we follow, {top['name']} {verb(top['week_change_pct'])} while "
                    f"{bot['name']} {verb(bot['week_change_pct'])}.",
                }
            )
        eu_ytd = self.idx("europe", "STOXX 600").get("ytd_pct")
        us_ytd = self.idx("us", "S&P 500").get("ytd_pct")
        if eu_ytd is not None and us_ytd is not None:
            lead = "Europe is ahead this year." if eu_ytd > us_ytd else "The US is ahead this year."
            out.append(
                {
                    "title": lead,
                    "text": f"So far in {self.meta['last_week']['end'][:4]}, Europe's STOXX 600 is {pct(eu_ytd)} "
                    f"and the S&P 500 {pct(us_ytd)}. Owning both is a simple way to spread your risk.",
                }
            )
        return out

    def us(self):
        sp = self.wk("us", "S&P 500")
        if sp is None:
            return None
        lead = "US stocks rose last week." if sp > 0.15 else "US stocks fell last week." if sp < -0.15 else "US stocks ended the week about flat."
        s = [lead, cap(self.describe("us", ["S&P 500", "Nasdaq Composite", "Dow Jones"])) + "."]
        day, move = self.biggest_day("us", "S&P 500")
        if day and abs(move) >= 1:
            s.append(f"The biggest day was {day.capitalize()}, when the S&P 500 {verb(move)}.")
        chips = self.wk("us", "PHLX Semiconductor (chip index)")
        if chips is not None and abs(chips) >= 3:
            s.append(f"Chip stocks had a big week: the chip index {verb(chips)}.")
        s.append(self.high_sentence("us", "S&P 500", "S&P 500"))
        nq_b = self.idx("us", "Nasdaq Composite").get("below_52w_high_pct")
        if nq_b is not None and nq_b <= -10:
            s.append(self.high_sentence("us", "Nasdaq Composite", "Nasdaq"))
        sec = [x for x in (self.d.get("sectors") or {}).get("sectors", []) if x.get("last_week_change_pct") is not None]
        if len(sec) >= 4:
            sec = sorted(sec, key=lambda x: x["last_week_change_pct"], reverse=True)
            best = " and ".join(f"{x['sector'].lower()} ({pct(x['last_week_change_pct'])})" for x in sec[:2])
            worst = " and ".join(f"{x['sector'].lower()} ({pct(x['last_week_change_pct'])})" for x in sec[-2:][::-1])
            s.append(f"The best-performing sectors were {best}; the weakest were {worst}.")
        c = self.m.get("commodities_fx_rates") or {}
        oil, gold = c.get("WTI crude oil") or {}, c.get("Gold") or {}
        if oil.get("last_week") and gold.get("last_week"):
            s.append(
                f"US oil {verb(oil['last_week']['change_pct'])} to about {money(oil['last_week']['close'])} a barrel, "
                f"and gold {verb(gold['last_week']['change_pct'])} to about {money(gold['last_week']['close'])} an ounce."
            )
        ty = c.get("US 10Y Treasury yield") or {}
        if ty.get("last_week") and ty["last_week"].get("close") is not None and ty["last_week"].get("change_abs") is not None:
            ch = ty["last_week"]["change_abs"]
            dirn = "rose" if ch > 0.02 else "fell" if ch < -0.02 else "held"
            s.append(
                f"The interest rate on 10-year US government bonds {dirn} {'at' if dirn == 'held' else 'to'} "
                f"{ty['last_week']['close']:.2f}%. When it rises, loans and mortgages tend to get pricier."
            )
        return " ".join(x for x in s if x)

    def _region_movers(self, key, n=3):
        reg = (self.d.get("movers") or {}).get(key) or {}
        up = reg.get("top_gainers") or []
        down = reg.get("top_losers") or []
        if not up or not down:
            return ""
        ups = ", ".join(f"{x['name']} ({pct(x['week_change_pct'])})" for x in up[:n])
        downs = ", ".join(f"{x['name']} ({pct(x['week_change_pct'])})" for x in down[:n])
        return f"Biggest risers: {ups}. Biggest fallers: {downs}."

    def europe(self):
        v = self.wk("europe", "STOXX 600")
        if v is None:
            return None
        lead = "European stocks rose." if v > 0.15 else "European stocks fell." if v < -0.15 else "European stocks ended about flat."
        s = [lead, cap(self.describe("europe", ["STOXX 600", "DAX (Germany)", "FTSE 100 (UK)", "CAC 40 (France)"])) + "."]
        s.append(self.high_sentence("europe", "STOXX 600", "STOXX 600"))
        for r in self.d.get("central_bank_rates") or []:
            if r.get("changed") and "Fed" not in r["rate"]:
                s.append(f"{r['rate']} moved from {r['before_last_week']}% to {r['latest']}%.")
        s.append(self._region_movers("europe"))
        return " ".join(x for x in s if x)

    def asia(self):
        names = ["Nikkei 225 (Japan)", "Kospi (South Korea)", "Hang Seng (Hong Kong)", "Shanghai Composite",
                 "Taiwan Weighted", "Nifty 50 (India)"]
        if all(self.wk("asia_em", n) is None for n in names):
            return None
        s = [cap(self.describe("asia_em", names)) + "."]
        for n in names:
            short = INDEX_PLAIN.get(n, n)
            sent = self.intraday_sentence("asia_em", n, short)
            if sent:
                s.append(sent)
        s.append(self._region_movers("asia"))
        return " ".join(x for x in s if x)

    def earnings_recap(self, n=8):
        rows = [r for r in (self.d.get("earnings") or {}).get("last_week", []) if r.get("eps_actual") is not None]
        if not rows:
            return None
        beats = sum(1 for r in rows if r.get("eps_beat"))
        top = sorted(rows, key=lambda r: -(r.get("market_cap_usd_bn") or 0))[:n]
        return {
            "summary": f"{len(rows)} large companies reported results last week, and {beats} of them earned more "
            f"than analysts expected. Here are the biggest:",
            "rows": [
                {
                    "name": company(r["name"]) or r["symbol"],
                    "symbol": r["symbol"],
                    "profit": "beat" if r.get("eps_beat") else "missed" if r.get("eps_beat") is False else "n/a",
                    "sales": "beat" if r.get("revenue_beat") else "missed" if r.get("revenue_beat") is False else "n/a",
                }
                for r in top
            ],
        }

    def sectors(self):
        sec = (self.d.get("sectors") or {}).get("sectors") or []
        out = []
        for x in sec:
            ch = x.get("last_week_change_pct")
            bg, fg = heat(ch)
            out.append(
                {
                    "name": x["sector"],
                    "weight": x.get("market_weight_pct") or 0,
                    "week": pct(ch),
                    "ytd": pct(x.get("ytd_pct_as_of_last_week")),
                    "ytd_raw": x.get("ytd_pct_as_of_last_week"),
                    "week_raw": ch,
                    "bg": bg,
                    "fg": fg,
                }
            )
        return out

    def movers_table(self, key, n=5):
        reg = (self.d.get("movers") or {}).get(key) or {}
        return {
            "up": [{"name": x["name"], "chg": pct(x["week_change_pct"])} for x in (reg.get("top_gainers") or [])[:n]],
            "down": [{"name": x["name"], "chg": pct(x["week_change_pct"])} for x in (reg.get("top_losers") or [])[:n]],
        }

    def week_ahead(self, earnings_per_day=5):
        tw = self.meta["this_week"]
        start = date.fromisoformat(tw["start"])
        cal = self.d.get("economic_calendar_this_week") or {}
        events = cal.get("events") or []
        earn = (self.d.get("earnings") or {}).get("this_week") or []
        intl = (self.d.get("earnings_international") or {}).get("this_week") or []
        moves = {m["symbol"]: m["implied_move_pct"] for m in (self.d.get("earnings_implied_moves_this_week") or {}).get("moves", [])}
        hol = self.d.get("market_holidays_this_week") or {}
        fed_meetings = {m["meeting_date"] for m in (self.d.get("fed_rate_odds") or {}).get("meetings", [])}

        days = []
        for i in range(5):
            d = (start + timedelta(days=i)).isoformat()
            items = []
            for h in hol.get("us_stocks", []):
                if h["date"] == d:
                    items.append({"kind": "holiday", "text": f"US stock market: {h['event']} ({h['trading_hours']})"})
            for h in hol.get("us_bonds", []):
                if h["date"] == d:
                    items.append({"kind": "holiday", "text": f"US bond market: {h['event']}"})
            if d in fed_meetings:
                items.append({"kind": "econ", "text": "US: Fed interest-rate decision (see the odds above)"})
            for e in events:
                if e["date"] != d:
                    continue
                if e["impact"] != "High" and e["country"] not in ("USD", "EUR"):
                    continue
                txt = f"{COUNTRY.get(e['country'], e['country'])}: {event_plain(e['event'])}"
                if e.get("forecast"):
                    txt += f", expected {e['forecast']}"
                    if e.get("previous"):
                        txt += f" (last time {e['previous']})"
                items.append({"kind": "econ", "text": txt, "high": e["impact"] == "High"})
            todays = sorted([r for r in earn if r["date"] == d], key=lambda r: -(r.get("market_cap_usd_bn") or 0))
            for r in todays[:earnings_per_day]:
                when = {"before open": "before the market opens", "after close": "after the market closes"}.get(r.get("timing"), "")
                txt = f"{company(r['name']) or r['symbol']} reports results" + (f" {when}" if when else "")
                if r["symbol"] in moves:
                    txt += f". Options traders expect a move of about ±{moves[r['symbol']]:g}%"
                items.append({"kind": "earnings", "text": txt})
            if len(todays) > earnings_per_day:
                more = ", ".join(company(r["name"]) or r["symbol"] for r in todays[earnings_per_day:earnings_per_day + 4])
                items.append({"kind": "earnings-more", "text": f"Also reporting: {more}" + (" and others" if len(todays) > earnings_per_day + 4 else "")})
            for r in intl:
                if r["date"] == d:
                    items.append({"kind": "earnings", "text": f"{r['name']} reports results"})
            days.append({"label": nice_date(d, True), "items": items})

        note = None
        if not events:
            note = (
                "The economic calendar for this week (inflation, jobs and similar reports) isn't published yet. "
                "It appears when the data is pulled on Sunday or Monday."
            )
        return {"days": days, "note": note}

    def news(self, per_topic=4):
        topics = (self.d.get("news_last_week") or {}).get("topics") or {}
        out = []
        for key, label in NEWS_TOPICS.items():
            items = [a for a in topics.get(key, []) if not NEWS_JUNK.search(a["title"])][:per_topic]
            if items:
                out.append({"label": label, "items": items})
        ahead = [a for a in ((self.d.get("news_week_ahead") or {}).get("topics") or {}).get("week_ahead", [])
                 if not NEWS_JUNK.search(a["title"])][:5]
        return out, ahead

    def term(self):
        for g, n in (("us", "S&P 500"), ("us", "Nasdaq Composite"), ("europe", "STOXX 600")):
            b = self.idx(g, n).get("below_52w_high_pct")
            if b is not None and b <= -10:
                return GLOSSARY["correction"]
        meetings = (self.d.get("fed_rate_odds") or {}).get("meetings") or []
        if meetings and (meetings[0].get("any_hike_pct") or 0) >= 50:
            return GLOSSARY["rate_hike"]
        if (self.d.get("earnings_implied_moves_this_week") or {}).get("moves"):
            return GLOSSARY["implied_move"]
        return GLOSSARY["fear_greed"]

    def build(self) -> dict:
        fed = self.fed()
        econ = self.econ_results()
        news, ahead = self.news()
        lw, tw = self.meta["last_week"], self.meta["this_week"]
        return {
            "issue": self.meta["issue"],
            "week_no": tw["iso_week"],
            "last_week_no": lw["iso_week"],
            "last_week_range": f"{nice_date(lw['start'])} – {nice_date(lw['end'])}",
            "this_week_range": f"{nice_date(tw['start'])} – {nice_date(tw['end'])}",
            "status": self.status(),
            "mood": self.mood(),
            "insights": self.insights(fed, econ),
            "us": self.us(),
            "europe": self.europe(),
            "asia": self.asia(),
            "fed": fed,
            "econ": econ,
            "earnings": self.earnings_recap(),
            "sectors": self.sectors(),
            "movers": {
                "watch": (self.d.get("movers") or {}).get("watchlist") or [],
                "us": self.movers_table("us_sp500"),
            },
            "ahead": self.week_ahead(),
            "news": news,
            "news_ahead": ahead,
            "term": self.term(),
            "generated_at": self.meta.get("generated_at"),
            "errors": self.d.get("errors") or {},
            "pct": pct,
        }
