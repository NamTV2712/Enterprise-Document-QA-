"""Opt-in live smoke against SEC EDGAR.

This script is NOT part of the pytest suite. The default suite is
hermetic (see tests/conftest.py); run this only when you explicitly
want to verify real SEC connectivity, for example after a provider
layout change:

    python -m scripts.diagnostics.sec_live_smoke

Exit code is nonzero when any check fails.
"""

from __future__ import annotations

import sys

from src.ingestion.sec_client import SECEdgarClient

EXPECTED_AAPL_CIK = 320193
SMOKE_USER_AGENT = "EnterpriseDocumentQA-Smoke ops@example.com"


def main() -> int:
    client = SECEdgarClient(user_agent=SMOKE_USER_AGENT)

    cik = client.get_cik("AAPL")
    print(f"AAPL CIK: {cik}")
    if cik != EXPECTED_AAPL_CIK:
        print(f"FAIL: expected CIK {EXPECTED_AAPL_CIK}, got {cik}")
        return 1

    filings = client.get_filings("AAPL", form_type="10-K", limit=1)
    filing = filings[0]
    print(f"Latest 10-K: {filing.accession_number} filed {filing.filing_date}")
    print(f"Primary document URL: {filing.filing_url}")

    print("Live SEC smoke passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
