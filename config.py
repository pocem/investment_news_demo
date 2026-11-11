"""What to track. Edit freely: every list here feeds a newsletter section."""

# --- Market indices (yfinance symbols), grouped like the newsletter ---------
INDICES = {
    "us": {
        "S&P 500": "^GSPC",
        "Nasdaq Composite": "^IXIC",
        "Dow Jones": "^DJI",
        "Russell 2000": "^RUT",
        "PHLX Semiconductor (chip index)": "^SOX",
        "VIX (volatility)": "^VIX",
    },
    "europe": {
        "STOXX 600": "^STOXX",
        "DAX (Germany)": "^GDAXI",
        "FTSE 100 (UK)": "^FTSE",
        "CAC 40 (France)": "^FCHI",
    },
    "asia_em": {
        "Nikkei 225 (Japan)": "^N225",
        "Kospi (South Korea)": "^KS11",
        "Hang Seng (Hong Kong)": "^HSI",
        "Shanghai Composite": "000001.SS",
        "Taiwan Weighted": "^TWII",
        "Nifty 50 (India)": "^NSEI",
        "MSCI Emerging Markets (EEM)": "EEM",
    },
}

COMMODITIES_FX_RATES = {
    "WTI crude oil": "CL=F",
    "Brent crude oil": "BZ=F",
    "Gold": "GC=F",
    "Bitcoin": "BTC-USD",
    "US 10Y Treasury yield": "^TNX",
    "US dollar index": "DX-Y.NYB",
    "EUR/USD": "EURUSD=X",
    "USD/JPY": "JPY=X",
}

# --- Individual stocks to rank as weekly movers (yfinance symbols) ----------
WATCHLIST = {
    # US mega caps / AI
    "NVDA": "Nvidia",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet",
    "AMZN": "Amazon",
    "META": "Meta",
    "TSLA": "Tesla",
    "AVGO": "Broadcom",
    "AMD": "AMD",
    "PLTR": "Palantir",
    "ORCL": "Oracle",
    "MU": "Micron",
    "CRWV": "CoreWeave",
    # Europe
    "ASML.AS": "ASML",
    "SAP.DE": "SAP",
    "NOVO-B.CO": "Novo Nordisk",
    "TEP.PA": "Teleperformance",
    # Asia
    "000660.KS": "SK hynix",
    "005930.KS": "Samsung Electronics",
    "2330.TW": "TSMC",
    "9984.T": "SoftBank Group",
}

# Company news from Finnhub (US symbols only on the free tier).
# Headlines are kept only if they mention one of the keywords.
NEWS_WATCHLIST = {
    "NVDA": ["Nvidia", "NVDA", "Jensen Huang"],
    "AAPL": ["Apple", "AAPL"],
    "MSFT": ["Microsoft", "MSFT"],
    "GOOGL": ["Alphabet", "Google", "GOOGL"],
    "AMZN": ["Amazon", "AMZN"],
    "META": ["Meta", "META"],
    "TSLA": ["Tesla", "TSLA"],
    "AMD": ["AMD", "Advanced Micro"],
    "PLTR": ["Palantir", "PLTR"],
}
COMPANY_NEWS_PER_SYMBOL = 5
GENERAL_NEWS_LIMIT = 40

# --- Earnings ---------------------------------------------------------------
# Finnhub's calendar lists ~1,300 companies a week; keep only big ones.
EARNINGS_MIN_MARKET_CAP_USD_BN = 20
# Always included regardless of size (US symbols in Finnhub's calendar).
EARNINGS_ALWAYS_INCLUDE = {"CRWV", "NVDA", "AMD", "PLTR", "CSCO", "AMAT", "TTWO"}
# Non-US names are not in Finnhub's free calendar; checked via yfinance instead.
EARNINGS_INTERNATIONAL = {
    "9984.T": "SoftBank Group",
    "ASML.AS": "ASML",
    "SAP.DE": "SAP",
    "NOVO-B.CO": "Novo Nordisk",
    "005930.KS": "Samsung Electronics",
    "000660.KS": "SK hynix",
    "2330.TW": "TSMC",
}

# --- Economic calendar (Forex Factory feed) ----------------------------------
ECON_COUNTRIES = {"USD", "EUR", "GBP", "JPY", "CNY"}
ECON_IMPACT = {"High", "Medium"}

# --- Economic results (FRED) --------------------------------------------------
# Forex Factory event title -> (FRED series, how to turn it into the headline
# number). "mom" = % change vs prior month, "diff_k" = change in thousands,
# "level" = the value itself, "level_k" = value in thousands.
# Last week's forecasts come from the calendar snapshot saved when the script
# ran during (or just before) that week.
FRED_EVENT_MAP = {
    "CPI m/m": ("CPIAUCSL", "mom"),
    "Core CPI m/m": ("CPILFESL", "mom"),
    "PPI m/m": ("PPIFIS", "mom"),
    "Core PPI m/m": ("PPIFES", "mom"),
    "Non-Farm Employment Change": ("PAYEMS", "diff_k"),
    "Unemployment Rate": ("UNRATE", "level"),
    "Retail Sales m/m": ("RSAFS", "mom"),
    "Unemployment Claims": ("ICSA", "level_k"),
    "Advance GDP q/q": ("A191RL1Q225SBEA", "level"),
    "Prelim GDP q/q": ("A191RL1Q225SBEA", "level"),
    "Final GDP q/q": ("A191RL1Q225SBEA", "level"),
    "Core PCE Price Index m/m": ("PCEPILFE", "mom"),
    "PCE Price Index m/m": ("PCEPI", "mom"),
    "Industrial Production m/m": ("INDPRO", "mom"),
}
# Headline US indicators always reported with their latest value.
FRED_HEADLINE = {
    "Payrolls change (k)": ("PAYEMS", "diff_k"),
    "Unemployment rate (%)": ("UNRATE", "level"),
    "CPI m/m (%)": ("CPIAUCSL", "mom"),
    "Core CPI m/m (%)": ("CPILFESL", "mom"),
    "CPI y/y (%)": ("CPIAUCSL", "yoy"),
    "PPI final demand m/m (%)": ("PPIFIS", "mom"),
    "Retail sales m/m (%)": ("RSAFS", "mom"),
    "Core PCE m/m (%)": ("PCEPILFE", "mom"),
    "Real GDP q/q annualized (%)": ("A191RL1Q225SBEA", "level"),
    "Initial jobless claims (k)": ("ICSA", "level_k"),
    "Consumer sentiment (UMich)": ("UMCSENT", "level"),
}
CENTRAL_BANK_RATES = {
    "Fed funds target (upper)": "DFEDTARU",
    "ECB deposit rate": "ECBDFR",
    "UK SONIA (tracks BoE Bank Rate)": "IUDSOIA",
}

# --- Rate-hike odds (Kalshi prediction market, no key) ----------------------
KALSHI_FED_SERIES = "KXFEDDECISION"
KALSHI_MEETINGS = 2  # next N FOMC meetings

# --- Google News search (no key) ---------------------------------------------
# Each query is searched for last week's dates; up to NEWS_PER_QUERY kept.
NEWS_QUERIES_LAST_WEEK = {
    "us_markets": '"stock market" OR "Wall Street" OR "S&P 500" OR Nasdaq',
    "fed_economy": '"Federal Reserve" OR inflation OR "jobs report" OR "rate hike" OR "rate cut"',
    "europe": '"European stocks" OR "STOXX 600" OR ECB OR "Bank of England"',
    "asia_em": 'Nikkei OR Kospi OR "Hang Seng" OR "emerging markets" stocks',
    "ai_tech": '"AI stocks" OR "chip stocks" OR Nvidia OR semiconductors',
    "commodities": '"oil prices" OR "gold prices" OR OPEC',
    "politics_policy": '(Congress OR tariffs OR regulation OR election OR "White House") stocks',
    "strategist_calls": '(Citi OR Goldman OR "Morgan Stanley" OR JPMorgan OR UBS) strategists stocks',
}
# Searched from last Friday onward: previews of the coming week.
NEWS_QUERIES_WEEK_AHEAD = {
    "week_ahead": '"week ahead" stocks OR "what to watch" stocks OR "week ahead" markets',
}
NEWS_PER_QUERY = 15

# --- Options-implied earnings moves (yfinance) ------------------------------
IMPLIED_MOVE_MAX_COMPANIES = 15  # biggest this-week reporters, plus watchlist

# --- Broader movers -----------------------------------------------------------
# US universe = S&P 500 (downloaded from Wikipedia, cached 30 days).
MOVERS_TOP_N = 10
MOVERS_EUROPE = {
    # Euro area
    "ADS.DE": "Adidas", "ADYEN.AS": "Adyen", "AD.AS": "Ahold Delhaize", "AI.PA": "Air Liquide",
    "AIR.PA": "Airbus", "ALV.DE": "Allianz", "ABI.BR": "AB InBev", "ARGX.BR": "argenx",
    "ASML.AS": "ASML", "CS.PA": "AXA", "BAS.DE": "BASF", "BAYN.DE": "Bayer", "BBVA.MC": "BBVA",
    "SAN.MC": "Banco Santander", "BMW.DE": "BMW", "BNP.PA": "BNP Paribas", "BN.PA": "Danone",
    "DB1.DE": "Deutsche Boerse", "DBK.DE": "Deutsche Bank", "DHL.DE": "DHL", "DTE.DE": "Deutsche Telekom",
    "ENEL.MI": "Enel", "ENI.MI": "Eni", "EL.PA": "EssilorLuxottica", "RACE.MI": "Ferrari",
    "IBE.MC": "Iberdrola", "ITX.MC": "Inditex", "IFX.DE": "Infineon", "INGA.AS": "ING",
    "ISP.MI": "Intesa Sanpaolo", "KER.PA": "Kering", "OR.PA": "L'Oreal", "MC.PA": "LVMH",
    "MBG.DE": "Mercedes-Benz", "MUV2.DE": "Munich Re", "NOKIA.HE": "Nokia", "RI.PA": "Pernod Ricard",
    "PRX.AS": "Prosus", "RHM.DE": "Rheinmetall", "SAF.PA": "Safran", "SAN.PA": "Sanofi", "SAP.DE": "SAP",
    "SU.PA": "Schneider Electric", "SIE.DE": "Siemens", "ENR.DE": "Siemens Energy", "STLAM.MI": "Stellantis",
    "TTE.PA": "TotalEnergies", "UCG.MI": "UniCredit", "DG.PA": "Vinci", "VOW3.DE": "Volkswagen",
    "WKL.AS": "Wolters Kluwer", "RMS.PA": "Hermes", "TEP.PA": "Teleperformance", "CAP.PA": "Capgemini",
    # UK
    "AZN.L": "AstraZeneca", "SHEL.L": "Shell", "HSBA.L": "HSBC", "ULVR.L": "Unilever", "BP.L": "BP",
    "RIO.L": "Rio Tinto", "GSK.L": "GSK", "REL.L": "RELX", "BARC.L": "Barclays", "LSEG.L": "LSEG",
    "RR.L": "Rolls-Royce", "BA.L": "BAE Systems",
    # Switzerland / Nordics
    "NESN.SW": "Nestle", "RO.SW": "Roche", "NOVN.SW": "Novartis", "UBSG.SW": "UBS", "ABBN.SW": "ABB",
    "NOVO-B.CO": "Novo Nordisk", "ATCO-A.ST": "Atlas Copco", "VOLV-B.ST": "Volvo",
    "ERIC-B.ST": "Ericsson", "INVE-B.ST": "Investor AB",
}
MOVERS_ASIA = {
    "7203.T": "Toyota", "6758.T": "Sony", "8306.T": "MUFG", "6861.T": "Keyence", "9984.T": "SoftBank Group",
    "8035.T": "Tokyo Electron", "6857.T": "Advantest", "9983.T": "Fast Retailing", "7974.T": "Nintendo",
    "6501.T": "Hitachi", "4063.T": "Shin-Etsu", "005930.KS": "Samsung Electronics", "000660.KS": "SK hynix",
    "373220.KS": "LG Energy Solution", "005380.KS": "Hyundai Motor", "035420.KS": "Naver",
    "2330.TW": "TSMC", "2317.TW": "Hon Hai (Foxconn)", "2454.TW": "MediaTek", "0700.HK": "Tencent",
    "9988.HK": "Alibaba", "3690.HK": "Meituan", "1810.HK": "Xiaomi", "0939.HK": "China Construction Bank",
    "1299.HK": "AIA", "600519.SS": "Kweichow Moutai", "300750.SZ": "CATL", "601318.SS": "Ping An",
    "RELIANCE.NS": "Reliance Industries", "TCS.NS": "TCS", "HDFCBANK.NS": "HDFC Bank", "INFY.NS": "Infosys",
    "ICICIBANK.NS": "ICICI Bank", "BHP.AX": "BHP", "CBA.AX": "Commonwealth Bank",
}

# --- US bond market (SIFMA recommended) holidays ------------------------------
# Finnhub only knows stock-exchange holidays. Bonds also close on Columbus Day
# and Veterans Day while stocks trade. Check sifma.org each January and update.
BOND_MARKET_HOLIDAYS = {
    "2026-01-01": "New Year's Day (closed)", "2026-01-19": "Martin Luther King Jr. Day (closed)",
    "2026-02-16": "Presidents Day (closed)", "2026-04-02": "Early close 2pm ET (before Good Friday)",
    "2026-04-03": "Good Friday (closed)", "2026-05-22": "Early close 2pm ET (before Memorial Day)",
    "2026-05-25": "Memorial Day (closed)", "2026-06-19": "Juneteenth (closed)",
    "2026-07-02": "Early close 2pm ET (before Independence Day)", "2026-07-03": "Independence Day observed (closed)",
    "2026-09-07": "Labor Day (closed)", "2026-10-12": "Columbus Day (bonds closed, stocks open)",
    "2026-11-11": "Veterans Day (bonds closed, stocks open)", "2026-11-26": "Thanksgiving (closed)",
    "2026-11-27": "Early close 2pm ET (day after Thanksgiving)", "2026-12-24": "Early close 2pm ET (Christmas Eve)",
    "2026-12-25": "Christmas (closed)", "2026-12-31": "Early close 2pm ET (New Year's Eve)",
    "2027-01-01": "New Year's Day (closed)", "2027-01-18": "Martin Luther King Jr. Day (closed)",
    "2027-02-15": "Presidents Day (closed)", "2027-03-26": "Good Friday (closed)",
    "2027-05-28": "Early close 2pm ET (before Memorial Day)", "2027-05-31": "Memorial Day (closed)",
    "2027-06-18": "Juneteenth observed (closed)", "2027-07-02": "Early close 2pm ET (before Independence Day)",
    "2027-07-05": "Independence Day observed (closed)", "2027-09-06": "Labor Day (closed)",
    "2027-10-11": "Columbus Day (bonds closed, stocks open)", "2027-11-11": "Veterans Day (bonds closed, stocks open)",
    "2027-11-25": "Thanksgiving (closed)", "2027-11-26": "Early close 2pm ET (day after Thanksgiving)",
    "2027-12-23": "Early close 2pm ET (before Christmas)", "2027-12-24": "Christmas observed (closed)",
    "2027-12-31": "Early close 2pm ET (New Year's Eve)",
}
