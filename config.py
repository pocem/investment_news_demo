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
