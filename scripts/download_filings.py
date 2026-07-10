"""
Script: download_filings.py
Run: python -m scripts.download_filings  (from the project's root directory)

Batch SEC 10-K ingestion for the configured corpus. The script is idempotent:
tickers with an existing *_sections.json file are skipped so failed batch runs
can be resumed safely.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from configs.settings import settings
from configs.tickers import TICKERS, TICKER_CIK_OVERRIDES
from src.ingestion.sec_client import SECEdgarClient, EdgarClientError
from src.ingestion.section_extractor import extract_sections, html_to_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

USER_AGENT = "Li Back cauvang2172@gmail.com"
INGESTION_REPORT_PATH = Path("data/ingestion_report.json")
EXPECTED_SECTIONS = ["business", "risk_factors", "mdna", "financial_statements"]


@dataclass
class TickerResult:
    ticker: str
    status: str
    error: str | None = None
    sections_found: list[str] | None = None
    warnings: list[str] | None = None
    skipped_existing: bool = False


def _missing_section_warnings(sections_found: list[str]) -> list[str]:
    return [
        f"Section '{section}' NOT found in this filing"
        for section in EXPECTED_SECTIONS
        if section not in sections_found
    ]


def _result_for_sections(
    ticker: str,
    sections_found: list[str],
    warnings: list[str] | None = None,
    skipped_existing: bool = False,
) -> TickerResult:
    warnings = warnings or _missing_section_warnings(sections_found)
    if not sections_found:
        return TickerResult(
            ticker=ticker,
            status="failed",
            error="No sections extracted from filing",
            sections_found=sections_found,
            warnings=warnings,
            skipped_existing=skipped_existing,
        )
    if len(sections_found) < len(EXPECTED_SECTIONS):
        return TickerResult(
            ticker=ticker,
            status="degraded",
            sections_found=sections_found,
            warnings=warnings,
            skipped_existing=skipped_existing,
        )
    return TickerResult(
        ticker=ticker,
        status="success",
        sections_found=sections_found,
        warnings=warnings or None,
        skipped_existing=skipped_existing,
    )


def _existing_sections(ticker: str) -> list[str] | None:
    """Return extracted section names for an existing processed filing."""
    processed_dir = settings.data_processed_dir / ticker
    if not processed_dir.exists():
        return None

    section_files = sorted(processed_dir.glob("*_sections.json"))
    if not section_files:
        return None

    data = json.loads(section_files[0].read_text(encoding="utf-8"))
    return list(data.get("sections", {}).keys())


def process_ticker(client: SECEdgarClient, ticker: str) -> TickerResult:
    existing_sections = _existing_sections(ticker)
    if existing_sections is not None:
        logger.info("SKIP %s: sections JSON already exists", ticker)
        return _result_for_sections(
            ticker=ticker,
            sections_found=existing_sections,
            skipped_existing=True,
        )

    try:
        filing = client.get_filings(ticker, form_type="10-K", limit=1)[0]
    except EdgarClientError as e:
        logger.error("FAILED %s during filing lookup: %s", ticker, e)
        return TickerResult(ticker=ticker, status="failed", error=str(e))

    raw_path = settings.data_raw_dir / ticker / f"{filing.accession_nodash}.html"
    try:
        client.download_filing(filing, raw_path)
    except EdgarClientError as e:
        logger.error("FAILED %s during filing download: %s", ticker, e)
        return TickerResult(ticker=ticker, status="failed", error=str(e))

    try:
        text = html_to_text(raw_path.read_bytes())
        result = extract_sections(text)
    except Exception as e:
        logger.exception("FAILED %s during section extraction", ticker)
        return TickerResult(ticker=ticker, status="failed", error=str(e))

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
    logger.info("Processed %s -> %s", ticker, processed_path)

    return _result_for_sections(
        ticker=ticker,
        sections_found=list(result.sections.keys()),
        warnings=result.warnings or None,
    )


def _write_report(results: list[TickerResult]) -> None:
    success = [result for result in results if result.status == "success"]
    degraded = [result for result in results if result.status == "degraded"]
    failed = [result for result in results if result.status == "failed"]
    skipped = [result for result in results if result.skipped_existing]

    logger.info(
        "COMPLETED: %d success, %d degraded, %d failed, %d skipped_existing / %d total",
        len(success),
        len(degraded),
        len(failed),
        len(skipped),
        len(results),
    )

    if failed:
        logger.error("Failed tickers requiring follow-up:")
        for result in failed:
            logger.error("  - %s: %s", result.ticker, result.error)

    if degraded:
        logger.warning("Tickers with degraded section extraction:")
        for result in degraded:
            logger.warning("  - %s: %s", result.ticker, result.sections_found)

    report = {
        "timestamp": datetime.now().isoformat(),
        "total": len(results),
        "success": len(success),
        "degraded": len(degraded),
        "skipped": len(skipped),
        "failed": len(failed),
        "details": [asdict(result) for result in results],
    }
    INGESTION_REPORT_PATH.parent.mkdir(exist_ok=True)
    INGESTION_REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("Full ingestion report saved to: %s", INGESTION_REPORT_PATH)


def main() -> None:
    client = SECEdgarClient(
        user_agent=USER_AGENT,
        ticker_cik_overrides=TICKER_CIK_OVERRIDES,
    )
    results = []

    for ticker in TICKERS:
        logger.info("=== Processing %s ===", ticker)
        results.append(process_ticker(client, ticker))

    _write_report(results)


if __name__ == "__main__":
    main()
