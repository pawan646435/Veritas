MOCK_STOCKS: dict[str, dict] = {
    "INFY": {
        "name": "Infosys Ltd",
        "price": 1850.50,
        "pe_ratio": 27.3,
        "market_cap_cr": 780000,
        "sector": "IT Services",
        "52w_high": 2010.0,
        "52w_low": 1560.0,
    },
    "TCS": {
        "name": "Tata Consultancy Services",
        "price": 4120.75,
        "pe_ratio": 29.8,
        "market_cap_cr": 1490000,
        "sector": "IT Services",
        "52w_high": 4450.0,
        "52w_low": 3600.0,
    },
    "RELIANCE": {
        "name": "Reliance Industries",
        "price": 2980.20,
        "pe_ratio": 24.1,
        "market_cap_cr": 2015000,
        "sector": "Conglomerate",
        "52w_high": 3150.0,
        "52w_low": 2450.0,
    },
    "HDFCBANK": {
        "name": "HDFC Bank",
        "price": 1720.90,
        "pe_ratio": 19.5,
        "market_cap_cr": 1310000,
        "sector": "Banking",
        "52w_high": 1810.0,
        "52w_low": 1420.0,
    },
    "TATAMOTORS": {
        "name": "Tata Motors",
        "price": 985.40,
        "pe_ratio": 14.2,
        "market_cap_cr": 327000,
        "sector": "Automobile",
        "52w_high": 1120.0,
        "52w_low": 780.0,
    },
}


def get_stock_data(ticker: str) -> dict | None:
    """The 'tool' the agent can call.

    Deliberately covers only 5 tickers. Asking about a 6th (e.g. WIPRO) is
    exactly the kind of test case that later exposes whether the agent
    correctly admits "I don't have that data" or fabricates a plausible-
    sounding number instead — which is precisely what the groundedness
    judge (Phase 4) will be checking for.
    """
    return MOCK_STOCKS.get(ticker.upper())
