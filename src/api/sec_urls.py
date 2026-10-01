"""Allowlist SEC URLs that may be exposed as browser-facing source links."""

from __future__ import annotations

from urllib.parse import urlsplit


SEC_BROWSER_HOST = "www.sec.gov"
SEC_ARCHIVE_PREFIX = "/Archives/edgar/data/"


def sanitize_sec_browser_url(value: object) -> str | None:
    """Return a canonical SEC archive URL, or ``None`` when it is unsafe.

    ``data.sec.gov`` is an ingestion host and ``www.sec.gov/files`` is an
    ingestion-metadata path. Neither is a browser source for indexed filing
    evidence. Host matching is exact: subdomains and suffixes are rejected.
    """
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or parsed.hostname != SEC_BROWSER_HOST
        or port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or not parsed.path.startswith(SEC_ARCHIVE_PREFIX)
        or len(parsed.path) <= len(SEC_ARCHIVE_PREFIX)
    ):
        return None
    return candidate
