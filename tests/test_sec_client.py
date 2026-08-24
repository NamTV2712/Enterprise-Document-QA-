"""Hermetic tests for the SEC EDGAR client.

Every HTTP interaction is faked at the ``requests.Session.get`` boundary,
so these tests verify URL construction, the mandatory User-Agent header,
response parsing, caching, and error mapping without touching the
network. A separate opt-in live smoke lives in
``scripts/diagnostics/sec_live_smoke.py``.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from src.ingestion import sec_client as sec_client_module
from src.ingestion.sec_client import (
    EdgarNotFoundError,
    EdgarRateLimitError,
    FilingMetadata,
    SECEdgarClient,
)

USER_AGENT = "Test Agent test@example.com"

# Shape mirrors https://www.sec.gov/files/company_tickers.json (dict of str -> entry).
TICKER_MAP_PAYLOAD = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
}


@pytest.fixture(autouse=True)
def _no_throttle_sleep(monkeypatch):
    """Skip the 0.5s inter-request sleep inside unit tests."""
    monkeypatch.setattr(sec_client_module.time, "sleep", lambda seconds: None)


def _fake_response(json_data=None, status_code: int = 200) -> MagicMock:
    response = MagicMock(spec=requests.Response)
    response.status_code = status_code
    if json_data is not None:
        response.json.return_value = json_data
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(
            f"{status_code} error"
        )
    else:
        response.raise_for_status.return_value = None
    return response


def _client_spying_on_get(response: MagicMock, monkeypatch):
    """Build a real client whose outbound GET is replaced by a spy."""
    client = SECEdgarClient(user_agent=USER_AGENT)
    get_mock = MagicMock(return_value=response)
    monkeypatch.setattr(client.session, "get", get_mock)
    return client, get_mock


def test_user_agent_without_email_is_rejected() -> None:
    with pytest.raises(ValueError, match="user_agent"):
        SECEdgarClient(user_agent="anonymous-agent")


def test_user_agent_header_is_registered_for_all_requests() -> None:
    client = SECEdgarClient(user_agent=USER_AGENT)

    assert client.session.headers["User-Agent"] == USER_AGENT


def test_get_cik_parses_apple_cik_and_requests_map_url(monkeypatch) -> None:
    client, get_mock = _client_spying_on_get(
        _fake_response(TICKER_MAP_PAYLOAD), monkeypatch
    )

    assert client.get_cik("AAPL") == 320193

    get_mock.assert_called_once()
    requested_url = get_mock.call_args.args[0]
    assert requested_url == SECEdgarClient.TICKER_MAP_URL
    assert "timeout" in get_mock.call_args.kwargs


def test_ticker_map_is_cached_after_first_download(monkeypatch) -> None:
    client, get_mock = _client_spying_on_get(
        _fake_response(TICKER_MAP_PAYLOAD), monkeypatch
    )

    assert client.get_cik("AAPL") == 320193
    assert client.get_cik("MSFT") == 789019
    assert client.get_cik("aapl") == 320193

    get_mock.assert_called_once()


def test_overrides_short_circuit_http_entirely(monkeypatch) -> None:
    client = SECEdgarClient(user_agent=USER_AGENT, ticker_cik_overrides={"AAPL": 999999})
    get_mock = MagicMock()
    monkeypatch.setattr(client.session, "get", get_mock)

    assert client.get_cik("AAPL") == 999999

    get_mock.assert_not_called()


def test_unknown_ticker_raises_not_found(monkeypatch) -> None:
    client, _ = _client_spying_on_get(
        _fake_response(TICKER_MAP_PAYLOAD), monkeypatch
    )

    with pytest.raises(EdgarNotFoundError, match="NOPE"):
        client.get_cik("NOPE")


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (404, EdgarNotFoundError),
        (429, EdgarRateLimitError),
    ],
)
def test_sec_error_statuses_map_to_domain_exceptions(
    monkeypatch, status_code: int, expected_error: type[Exception]
) -> None:
    client, _ = _client_spying_on_get(
        _fake_response(status_code=status_code), monkeypatch
    )

    with pytest.raises(expected_error):
        client.get_cik("AAPL")


def test_unexpected_http_errors_propagate_unchanged(monkeypatch) -> None:
    """Only 404/429 map to domain errors; other failures stay requests errors."""
    client, _ = _client_spying_on_get(
        _fake_response(status_code=503), monkeypatch
    )

    with pytest.raises(requests.HTTPError):
        client.get_cik("AAPL")


def test_get_filings_returns_metadata_for_latest_form(monkeypatch) -> None:
    submissions_payload = {
        "filings": {
            "recent": {
                "form": ["8-K", "10-K", "10-Q"],
                "accessionNumber": ["0000-8k", "0000320193-25-000079", "0000-10q"],
                "filingDate": ["2025-11-01", "2025-10-31", "2025-08-01"],
                "reportDate": ["2025-10-30", "2025-09-27", "2025-06-28"],
                "primaryDocument": ["a.htm", "aapl-20250927.htm", "b.htm"],
            }
        }
    }
    client = SECEdgarClient(user_agent=USER_AGENT)
    responses = iter([
        _fake_response(TICKER_MAP_PAYLOAD),
        _fake_response(submissions_payload),
    ])
    requested_urls: list[str] = []

    def fake_get(url, **kwargs):
        requested_urls.append(url)
        return next(responses)

    monkeypatch.setattr(client.session, "get", fake_get)

    filings = client.get_filings("AAPL", form_type="10-K", limit=1)

    assert filings == [
        FilingMetadata(
            ticker="AAPL",
            cik=320193,
            form_type="10-K",
            accession_number="0000320193-25-000079",
            filing_date="2025-10-31",
            report_date="2025-09-27",
            primary_document="aapl-20250927.htm",
        )
    ]
    assert requested_urls[1] == (
        SECEdgarClient.SUBMISSIONS_URL_TEMPLATE.format(cik="0000320193")
    )


def test_filing_url_strips_accession_dashes() -> None:
    filing = FilingMetadata(
        ticker="AAPL",
        cik=320193,
        form_type="10-K",
        accession_number="0000320193-25-000079",
        filing_date="2025-10-31",
        report_date="2025-09-27",
        primary_document="aapl-20250927.htm",
    )

    assert filing.accession_nodash == "000032019325000079"
    assert filing.filing_url == (
        "https://www.sec.gov/Archives/edgar/data/"
        "320193/000032019325000079/aapl-20250927.htm"
    )


def test_get_filings_without_matching_form_raises_not_found(monkeypatch) -> None:
    empty_payload = {
        "filings": {"recent": {
            "form": ["8-K"],
            "accessionNumber": ["x"],
            "filingDate": ["y"],
            "reportDate": ["z"],
            "primaryDocument": ["w"],
        }}
    }
    client = SECEdgarClient(user_agent=USER_AGENT)
    responses = iter([
        _fake_response(TICKER_MAP_PAYLOAD),
        _fake_response(empty_payload),
    ])
    monkeypatch.setattr(
        client.session, "get", lambda url, **kwargs: next(responses)
    )

    with pytest.raises(EdgarNotFoundError, match="20-F"):
        client.get_filings("AAPL", form_type="20-F")
