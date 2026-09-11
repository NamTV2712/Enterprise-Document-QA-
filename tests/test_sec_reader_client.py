from __future__ import annotations

import json
from pathlib import Path

import pytest

from configs.settings import settings
from src.api.sec_reader_client import (
    INDEX_MAX_BYTES,
    SOURCE_MAX_BYTES,
    HttpResponse,
    SecReaderClient,
    SecReaderError,
    _public_addresses,
    _validated_archive_url,
)


ACCESSION = "0000051143-26-000010"
ROW = {
    "document_id": f"IBM:{ACCESSION}",
    "ticker": "IBM",
    "filing_date": "2026-02-04",
    "accession_number": ACCESSION,
}


@pytest.fixture
def trusted_identity_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    processed = tmp_path / "processed" / "IBM"
    processed.mkdir(parents=True)
    (processed / f"{ACCESSION.replace('-', '')}_sections.json").write_text(
        json.dumps({"ticker": "IBM", "cik": 51143, "accession_number": ACCESSION, "sections": {}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "data_processed_dir", tmp_path / "processed")
    return ROW


def test_acquisition_requires_real_contact_user_agent() -> None:
    with pytest.raises(SecReaderError, match="contact User-Agent"):
        SecReaderClient("")


def test_archive_url_is_pinned_to_expected_identity() -> None:
    valid = "https://www.sec.gov/Archives/edgar/data/51143/000005114326000010/ibm-10k.htm"
    assert _validated_archive_url(valid, expected_cik=51143, expected_accession=ACCESSION).endswith("ibm-10k.htm")
    for invalid in (
        valid.replace("www.sec.gov", "example.test"),
        valid.replace("https://", "http://"),
        valid + "?download=1",
        valid.replace("51143", "10.0.0.1"),
        valid.replace("000005114326000010", "000005114326000011"),
    ):
        with pytest.raises(SecReaderError):
            _validated_archive_url(invalid, expected_cik=51143, expected_accession=ACCESSION)


def test_missing_local_source_resolves_one_html_primary_and_hashes_it(trusted_identity_tree) -> None:
    index = b"""
    <html><body><table><tr><th>Description</th><th>Document</th><th>Type</th></tr>
    <tr><td>Annual report</td><td><a href='ibm-10k.htm'>primary</a></td><td>10-K</td></tr>
    </table></body></html>
    """
    source = b"<html><body><h1>IBM filing</h1><p>Revenue $100</p></body></html>"
    responses = [
        HttpResponse(200, {"content-type": "text/html"}, index),
        HttpResponse(200, {"content-type": "text/html"}, source),
    ]

    def request(_url: str, _maximum: int, _user_agent: str) -> HttpResponse:
        return responses.pop(0)

    result = SecReaderClient("Researcher researcher@example.com", request=request).acquire(trusted_identity_tree)

    assert result.primary_document == "ibm-10k.htm"
    assert result.bytes_received == len(source)
    assert result.raw_sha256
    assert result.request_count == 2
    assert not responses


def test_index_requires_unique_filing_type_and_bounds_responses(trusted_identity_tree) -> None:
    ambiguous = b"<html><body><table><tr><td>10-K</td><td><a href='one.htm'>one</a><a href='two.htm'>two</a></td></tr></table></body></html>"
    with pytest.raises(SecReaderError, match="unique"):
        SecReaderClient("Researcher researcher@example.com", request=lambda *_: HttpResponse(200, {"content-type": "text/html"}, ambiguous)).acquire(trusted_identity_tree)

    oversized = HttpResponse(200, {"content-type": "text/html"}, b"<html>" + b"x" * (INDEX_MAX_BYTES + 1))
    with pytest.raises(SecReaderError, match="size limit"):
        SecReaderClient("Researcher researcher@example.com", request=lambda *_: oversized).acquire(trusted_identity_tree)

    redirect = HttpResponse(302, {"location": "https://example.test"}, b"<html></html>")
    with pytest.raises(SecReaderError, match="redirect"):
        SecReaderClient("Researcher researcher@example.com", request=lambda *_: redirect).acquire(trusted_identity_tree)


def test_source_rejects_non_html_and_oversized_primary(trusted_identity_tree) -> None:
    index = b"<html><body><table><tr><td>10-K</td><td><a href='ibm-10k.htm'>one</a></td></tr></table></body></html>"
    responses = iter((HttpResponse(200, {"content-type": "text/html"}, index), HttpResponse(200, {"content-type": "application/pdf"}, b"%PDF")))
    with pytest.raises(SecReaderError, match="non-HTML"):
        SecReaderClient("Researcher researcher@example.com", request=lambda *_: next(responses)).acquire(trusted_identity_tree)

    assert SOURCE_MAX_BYTES == 20 * 1024 * 1024


def test_transient_failure_retries_once(trusted_identity_tree) -> None:
    index = b"<html><body><table><tr><td>10-K</td><td><a href='ibm-10k.htm'>one</a></td></tr></table></body></html>"
    source = b"<html><body>ok</body></html>"
    responses = iter((HttpResponse(500, {"content-type": "text/html"}, b"<html>retry</html>"), HttpResponse(200, {"content-type": "text/html"}, index), HttpResponse(200, {"content-type": "text/html"}, source)))
    result = SecReaderClient("Researcher researcher@example.com", request=lambda *_: next(responses)).acquire(trusted_identity_tree)
    assert result.request_count == 3


def test_private_address_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.api.sec_reader_client.socket.getaddrinfo", lambda *_args, **_kwargs: [(2, 1, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(SecReaderError, match="non-public"):
        _public_addresses("www.sec.gov")
