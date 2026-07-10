"""Corpus ticker configuration."""

TICKERS: list[str] = [
    # Big Tech
    "AAPL",
    "MSFT",
    "AMZN",
    "GOOGL",
    "META",
    "NVDA",
    "TSLA",
    # Finance
    "JPM",
    "BAC",
    "GS",
    "MS",
    "BRK-B",
    # Healthcare
    "JNJ",
    "UNH",
    "PFE",
    # Consumer/Retail
    "WMT",
    "HD",
    "MCD",
    # Energy
    "XOM",
    "CVX",
    # Semiconductor
    "AMD",
    "INTC",
    "QCOM",
    # Cloud/SaaS
    "CRM",
    "ORCL",
]

TICKER_CIK_OVERRIDES: dict[str, int] = {
    # SEC's ticker map currently points XOM to a new entity without 10-K history.
    "XOM": 34088,
}
