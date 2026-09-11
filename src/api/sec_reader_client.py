"""Bounded, pinned SEC acquisition for the document reader.

The ingestion downloader intentionally has a different trust contract and is
not reused here. This client accepts a trusted document identity only and
returns bytes to its caller; it never writes the RAG corpus or user storage.
"""
from __future__ import annotations

import hashlib
import http.client
import ipaddress
import re
import socket
import ssl
import threading
import time
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Callable
from urllib.parse import urlsplit

from src.api.original_viewer import validated_filing_identity


SEC_HOST = "www.sec.gov"
SEC_PORT = 443
INDEX_MAX_BYTES = 2 * 1024 * 1024
SOURCE_MAX_BYTES = 20 * 1024 * 1024
SOURCE_SET_MAX_BYTES = 40 * 1024 * 1024
CONNECT_TIMEOUT_SECONDS = 5.0
READ_INACTIVITY_SECONDS = 10.0
TOTAL_TIMEOUT_SECONDS = 30.0
MAX_TRANSIENT_RETRIES = 1
MAX_PENDING_ACQUISITIONS = 4
MIN_REQUEST_INTERVAL_SECONDS = 0.5
_ARCHIVE_PATH_RE = re.compile(r"^/Archives/edgar/data/(\d{1,10})/(\d{18})/([^/?#]+)$", re.I)
_HTML_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,180}\.(?:html?|xhtml?)$", re.I)
_FORM_RE = re.compile(r"\b10-k(?:/a)?\b", re.I)


class SecReaderError(Exception):
    """Typed safe failure returned by the reader acquisition boundary."""

    def __init__(self, code: str, message: str, status_code: int = 200, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retry_after = retry_after


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes


@dataclass(frozen=True)
class AcquiredSource:
    canonical_url: str
    primary_document: str
    raw_sha256: str
    bytes_received: int
    request_count: int
    body: bytes


@dataclass
class _Flight:
    event: threading.Event
    result: AcquiredSource | None = None
    error: SecReaderError | None = None


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to a prevalidated address while retaining SEC hostname/SNI."""

    def __init__(self, hostname: str, address: str, context: ssl.SSLContext, timeout: float) -> None:
        super().__init__(hostname, port=SEC_PORT, timeout=timeout, context=context)
        self._pinned_address = address

    def connect(self) -> None:  # pragma: no cover - socket/TLS exercised by bounded live gate
        self.sock = socket.create_connection((self._pinned_address, SEC_PORT), self.timeout)
        self.sock = self._context.wrap_socket(self.sock, server_hostname=SEC_HOST)


def _validate_user_agent(user_agent: str) -> str:
    if not isinstance(user_agent, str) or "@" not in user_agent or len(user_agent.strip()) < 5:
        raise SecReaderError(
            "acquisition_unconfigured",
            "On-demand SEC reader acquisition requires a configured contact User-Agent.",
            503,
        )
    return " ".join(user_agent.split())[:240]


def _validated_archive_url(url: str, *, expected_cik: int, expected_accession: str, allow_index: bool = False) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != SEC_HOST or parsed.port not in (None, SEC_PORT):
        raise SecReaderError("invalid_source_url", "The SEC source URL is outside the permitted host and port.", 200)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise SecReaderError("invalid_source_url", "The SEC source URL contains unsupported URL components.", 200)
    match = _ARCHIVE_PATH_RE.fullmatch(parsed.path)
    if match is None:
        raise SecReaderError("invalid_source_url", "The SEC source URL is outside the permitted archive path.", 200)
    cik, accession_nodash, filename = match.groups()
    if int(cik) != expected_cik or accession_nodash != expected_accession.replace("-", ""):
        raise SecReaderError("identity_mismatch", "The SEC source URL does not match the trusted filing identity.", 200)
    if not _HTML_FILENAME_RE.fullmatch(filename):
        raise SecReaderError("unsupported_content", "The SEC source is not an HTML document.", 200)
    if not allow_index and filename.casefold().endswith("-index.html"):
        raise SecReaderError("invalid_primary", "The filing index is not the primary filing document.", 200)
    return f"https://{SEC_HOST}{parsed.path}"


def _index_url(identity: dict[str, Any]) -> str:
    accession = str(identity["accession_number"])
    nodash = accession.replace("-", "")
    return f"https://{SEC_HOST}/Archives/edgar/data/{int(identity['cik'])}/{nodash}/{accession}-index.html"


def _public_addresses(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, SEC_PORT, type=socket.SOCK_STREAM)
    except OSError as error:
        raise SecReaderError("network_unavailable", "SEC hostname resolution failed.", 200) from error
    addresses: list[str] = []
    for info in infos:
        address = info[4][0]
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError:
            continue
        if parsed.is_global and address not in addresses:
            addresses.append(address)
    if not addresses:
        raise SecReaderError("private_address_rejected", "SEC resolved only to non-public addresses.", 200)
    return addresses


def _safe_html_body(response: HttpResponse, maximum: int) -> bytes:
    if len(response.body) > maximum:
        raise SecReaderError("source_too_large", "The SEC response exceeds the reader size limit.", 200)
    content_type = response.headers.get("content-type", "").casefold()
    if content_type and "text/html" not in content_type and "application/xhtml+xml" not in content_type:
        raise SecReaderError("unexpected_content", "SEC returned a non-HTML representation.", 200)
    stripped = response.body.lstrip()
    if stripped.startswith((b"%PDF", b"PK\x03\x04", b"{")) or b"<html" not in stripped[:8192].lower():
        raise SecReaderError("unexpected_content", "SEC returned an unexpected or non-HTML document.", 200)
    return response.body


def _select_primary_document(index_html: bytes, identity: dict[str, Any]) -> str:
    """Select exactly one filing-type HTML document from the SEC index."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(index_html, "lxml")
    expected_nodash = str(identity["accession_number"]).replace("-", "")
    candidates: set[str] = set()
    for row in soup.find_all("tr"):
        text = " ".join(row.get_text(" ", strip=True).split())
        if not _FORM_RE.search(text):
            continue
        for anchor in row.find_all("a", href=True):
            href = str(anchor["href"]).strip()
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or not parsed.path:
                continue
            filename = PurePosixPath(parsed.path).name
            if _HTML_FILENAME_RE.fullmatch(filename) and filename.casefold() != f"{expected_nodash}-index.html":
                candidates.add(filename)
    if len(candidates) != 1:
        raise SecReaderError(
            "primary_ambiguous" if candidates else "primary_not_found",
            "The SEC index did not identify one unique filing-type primary HTML document.",
            200,
        )
    return next(iter(candidates))


class SecReaderClient:
    """SEC reader acquisition with bounded transport and single-flight control."""

    def __init__(self, user_agent: str, *, request: Callable[[str, int, str], HttpResponse] | None = None) -> None:
        self.user_agent = _validate_user_agent(user_agent)
        self._request_override = request
        self._active = threading.Lock()
        self._pending_lock = threading.Lock()
        self._pending = 0
        self._request_lock = threading.Lock()
        self._last_request_at = 0.0
        self._inflight_lock = threading.Lock()
        self._inflight: dict[str, _Flight] = {}

    def _bounded_get(self, url: str, maximum: int, *, conditional: dict[str, str] | None = None) -> HttpResponse:
        if self._request_override is not None:
            return self._request_override(url, maximum, self.user_agent)
        parsed = urlsplit(url)
        if parsed.hostname != SEC_HOST or parsed.scheme != "https" or parsed.port not in (None, SEC_PORT):
            raise SecReaderError("invalid_source_url", "The SEC request target is not permitted.", 200)
        address = _public_addresses(SEC_HOST)[0]
        context = ssl.create_default_context()
        connection = _PinnedHTTPSConnection(SEC_HOST, address, context, CONNECT_TIMEOUT_SECONDS)
        headers = {
            "Host": SEC_HOST,
            "User-Agent": self.user_agent,
            "Accept": "text/html, application/xhtml+xml",
            "Accept-Encoding": "identity",
            "Connection": "close",
        }
        headers.update(conditional or {})
        try:  # pragma: no cover - exercised by bounded live gate
            connection.request("GET", parsed.path, headers=headers)
            response = connection.getresponse()
            length = response.getheader("Content-Length")
            if length and int(length) > maximum:
                raise SecReaderError("source_too_large", "The SEC response exceeds the reader size limit.", 200)
            body = response.read(maximum + 1)
            return HttpResponse(response.status, {key.casefold(): value for key, value in response.getheaders()}, body)
        except SecReaderError:
            raise
        except (OSError, http.client.HTTPException) as error:
            raise SecReaderError("network_unavailable", "SEC reader transport failed.", 200) from error
        finally:
            connection.close()

    def _request_with_retry(self, url: str, maximum: int, *, conditional: dict[str, str] | None = None) -> tuple[HttpResponse, int]:
        attempts = 0
        while True:
            with self._request_lock:
                delay = MIN_REQUEST_INTERVAL_SECONDS - (time.monotonic() - self._last_request_at)
                if delay > 0:
                    time.sleep(delay)
                self._last_request_at = time.monotonic()
            response = self._bounded_get(url, maximum, conditional=conditional)
            attempts += 1
            if response.status_code in (301, 302, 303, 307, 308):
                raise SecReaderError("redirect_rejected", "SEC redirects are not followed by the reader.", 200)
            if response.status_code in (403, 404):
                raise SecReaderError("sec_not_available", "The SEC source is not available for this filing.", 200)
            if response.status_code == 429:
                raise SecReaderError("sec_rate_limited", "SEC rate-limited the reader request.", 200, retry_after=1)
            if response.status_code >= 500 and attempts <= MAX_TRANSIENT_RETRIES:
                continue
            if response.status_code >= 400:
                raise SecReaderError("sec_unavailable", "SEC could not serve the requested source.", 200)
            return response, attempts

    def _acquire_uncached(self, row: dict[str, Any]) -> AcquiredSource:
        identity = validated_filing_identity(row)
        if identity is None:
            raise SecReaderError("identity_unverified", "The filing identity is not verified from local metadata.", 200)
        index_response, index_requests = self._request_with_retry(_index_url(identity), INDEX_MAX_BYTES)
        index_html = _safe_html_body(index_response, INDEX_MAX_BYTES)
        filename = _select_primary_document(index_html, identity)
        target = _validated_archive_url(
            f"https://{SEC_HOST}/Archives/edgar/data/{identity['cik']}/{identity['accession_number'].replace('-', '')}/{filename}",
            expected_cik=int(identity["cik"]),
            expected_accession=str(identity["accession_number"]),
        )
        source_response, source_requests = self._request_with_retry(target, SOURCE_MAX_BYTES)
        body = _safe_html_body(source_response, SOURCE_MAX_BYTES)
        if len(body) > SOURCE_SET_MAX_BYTES:
            raise SecReaderError("source_set_too_large", "The SEC source set exceeds the reader budget.", 200)
        return AcquiredSource(target, filename, hashlib.sha256(body).hexdigest(), len(body), index_requests + source_requests, body)

    def acquire(self, row: dict[str, Any], *, refresh: bool = False) -> AcquiredSource:
        """Acquire one exact filing source and always release in-flight state."""
        identity = validated_filing_identity(row)
        if identity is None:
            raise SecReaderError("identity_unverified", "The filing identity is not verified from local metadata.", 200)
        key = f"{identity['ticker']}:{identity['accession_number']}"
        with self._inflight_lock:
            existing = self._inflight.get(key)
            if existing is not None:
                flight = existing
                leader = False
            else:
                with self._pending_lock:
                    if self._pending >= MAX_PENDING_ACQUISITIONS:
                        raise SecReaderError("reader_busy", "The SEC reader is busy. Please retry shortly.", 503, retry_after=1)
                    self._pending += 1
                flight = _Flight(threading.Event())
                self._inflight[key] = flight
                leader = True
        if not leader:
            if not flight.event.wait(TOTAL_TIMEOUT_SECONDS):
                raise SecReaderError("acquisition_timeout", "SEC reader acquisition timed out.", 200)
            if flight.result is not None:
                return flight.result
            if flight.error is not None:
                raise flight.error
            raise SecReaderError("acquisition_failed", "SEC reader acquisition failed.", 200)
        try:
            with self._active:
                result = self._acquire_uncached(row)
            with self._inflight_lock:
                flight.result = result
            return result
        except SecReaderError as error:
            with self._inflight_lock:
                flight.error = error
            raise
        finally:
            flight.event.set()
            with self._pending_lock:
                self._pending -= 1
            with self._inflight_lock:
                if self._inflight.get(key) is flight:
                    self._inflight.pop(key, None)
