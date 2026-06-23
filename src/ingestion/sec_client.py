"""
Module: sec_client.py

Purpose: Wrapper for SEC EDGAR's public APIs.

Why this module exists separately:
- Concentrates ALL logic regarding rate-limiting, retry, and HTTP error handling in one place.
- If SEC later changes the URL structure, or we want to add caching, we only need to modify it here —
not modify it scattered across every notebook/script that calls it.
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import requests

logger = logging.getLogger(__name__)


# --- Domain-specific exceptions, not general request exceptions ---

class EdgarClientError(Exception):
    """The original exception class for all errors related to the EDGAR client SEC.
        The calling code can catch only EdgarClientError to distinguish it from a real bug
        (e.g., TypeError, AttributeError caused by our own logic error)"""


class EdgarRateLimitError(EdgarClientError):
    """SEC returned 429 — we called too quickly"""


class EdgarNotFoundError(EdgarClientError):
    """SEC returned 404 — ticker/CIK/filing does not exist"""


@dataclass
class FilingMetadata:
    """The structured representation for a single filing

    Why use @dataclass instead of a regular dict:
    With a dict, a typo in the key (e.g., `filing["accesion_number"]` missing the 's')
    is only caught at runtime, and the error is hard to understand (KeyError).
    With a dataclass, your IDE will suggest the correct field names, and type checking
    tools (like mypy) can catch this error before running the code
    """
    ticker: str
    cik: int
    form_type: str
    accession_number: str
    filing_date: str
    report_date: str
    primary_document: str

    @property
    def accession_nodash(self) -> str:
        """SEC uses accession number with hyphens when displaying (0000320193-24-000123)
        but the file URL requires removing the hyphen. We calculate this property in advance to avoid
        repeating the .replace("-", "") logic in multiple places."""
        return self.accession_number.replace("-", "")

    @property
    def filing_url(self) -> str:
        return (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{self.cik}/{self.accession_nodash}/{self.primary_document}"
        )


class SECEdgarClient:
    """
    Client to interact with the SEC EDGAR public API.

    This object maintains 2 states throughout its lifetime: an HTTP session (to reuse
    TCP connections, making requests faster than opening a new connection each time) and the timestamp of the last request
    (for rate-limiting).
    """

    TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
    SUBMISSIONS_URL_TEMPLATE = "https://data.sec.gov/submissions/CIK{cik}.json"
    MIN_REQUEST_INTERVAL_SECONDS = 0.5

    def __init__(self, user_agent: str):
        if "@" not in user_agent:
            # Block the error early at initialization — instead of letting it cause
            # a vague 403 error on any request, which could be 10 lines of code later,
            # wasting your time debugging it back to here.
            raise ValueError(
                "user_agent must contain a real contact email, "
                "e.g., 'NguyenVanA nguyenvana@email.com'"
            )
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self._last_request_time: float = 0.0
        self._ticker_to_cik: Optional[dict[str, int]] = None  # Cache, load once

    def _throttled_get(self, url: str, timeout: int = 15) -> requests.Response:
        """All outgoing requests MUST go through this function — do not call
        self.session.get() directly in other functions. This is the ONLY place
        to handle rate-limit and map status code to a separate exception."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL_SECONDS:
            time.sleep(self.MIN_REQUEST_INTERVAL_SECONDS - elapsed)

        logger.debug("GET %s", url)
        response = self.session.get(url, timeout=timeout)
        self._last_request_time = time.monotonic()

        if response.status_code == 404:
            raise EdgarNotFoundError(f"Resource not found: {url}")
        if response.status_code == 429:
            raise EdgarRateLimitError(f"Rate-limited when calling: {url}")
        response.raise_for_status()  # raise for any other 4xx/5xx status codes
        return response

    def get_cik(self, ticker: str) -> int:
        """Get CIK from ticker. File ticker map is large (several MB) so we only load
        it once and cache it in self._ticker_to_cik (memoization technique)."""
        if self._ticker_to_cik is None:
            response = self._throttled_get(self.TICKER_MAP_URL)
            data = response.json()
            self._ticker_to_cik = {
                entry["ticker"]: entry["cik_str"] for entry in data.values()
            }
            logger.info("Ticket map has been downloaded: %d companies", len(self._ticker_to_cik))

        ticker = ticker.upper()
        if ticker not in self._ticker_to_cik:
            raise EdgarNotFoundError(f"Ticker '{ticker}' not found in SEC EDGAR")
        return self._ticker_to_cik[ticker]

    def get_filings(
        self, ticker: str, form_type: str = "10-K", limit: int = 1
    ) -> list[FilingMetadata]:
        """Get the N most recent filings for a company, filtered by form type"""
        cik = self.get_cik(ticker)
        url = self.SUBMISSIONS_URL_TEMPLATE.format(cik=str(cik).zfill(10))
        submissions = self._throttled_get(url).json()
        recent = submissions["filings"]["recent"]

        results: list[FilingMetadata] = []
        for i, form in enumerate(recent["form"]):
            if form == form_type:
                results.append(FilingMetadata(
                    ticker=ticker.upper(),
                    cik=cik,
                    form_type=form,
                    accession_number=recent["accessionNumber"][i],
                    filing_date=recent["filingDate"][i],
                    report_date=recent["reportDate"][i],
                    primary_document=recent["primaryDocument"][i],
                ))
            if len(results) >= limit:
                break

        if not results:
            raise EdgarNotFoundError(
                f"Resource not found: No filings of type '{form_type}' for {ticker}"
            )
        return results

    def download_filing(self, filing: FilingMetadata, save_path: Path) -> Path:
        response = self._throttled_get(filing.filing_url)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(response.content)
        logger.info("Resource saved: %s -> %s", filing.accession_number, save_path)
        return save_path