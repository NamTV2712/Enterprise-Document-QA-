"""
Script: download_filings.py
Run: python -m scripts.download_filings  (from the project's root directory)
"""

import json
import logging

from configs.settings import settings
from src.ingestion.sec_client import SECEdgarClient, EdgarClientError
from src.ingestion.section_extractor import html_to_text, extract_sections

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TICKERS = ["AAPL", "MSFT", "AMZN"]   
USER_AGENT = "TenBan email@cuaban.com"  


def process_ticker(client: SECEdgarClient, ticker: str) -> None:
    logger.info("=== Processing %s ===", ticker)
    try:
        filing = client.get_filings(ticker, form_type="10-K", limit=1)[0]
    except EdgarClientError as e:
        # Only catch domain-specific errors (API/data issues), not general exceptions —
        # if there's a real bug in the code (e.g., TypeError), we WANT it to crash so we know immediately.
        logger.error("Skipping %s due to error: %s", ticker, e)
        return

    raw_path = settings.data_raw_dir / ticker / f"{filing.accession_nodash}.html"
    client.download_filing(filing, raw_path)

    text = html_to_text(raw_path.read_bytes())
    result = extract_sections(text)
    for warning in result.warnings:
        logger.warning("[%s] %s", ticker, warning)

    output = {
        "ticker": filing.ticker,
        "cik": filing.cik,
        "accession_number": filing.accession_number,
        "filing_date": filing.filing_date,
        "report_date": filing.report_date,
        "sections": result.sections,
    }
    processed_path = (
        settings.data_processed_dir / ticker / f"{filing.accession_nodash}_sections.json"
    )
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    processed_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("Hoàn thành %s -> %s", ticker, processed_path)


def main() -> None:
    client = SECEdgarClient(user_agent=USER_AGENT)
    for ticker in TICKERS:
        process_ticker(client, ticker)


if __name__ == "__main__":
    main()