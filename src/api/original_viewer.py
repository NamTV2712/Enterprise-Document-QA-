"""Bounded, local-only original-source inventory and normalized text windows."""
from __future__ import annotations

import hashlib
import json
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from configs.settings import settings
from src.api.content_presentation import build_chunk_presentation
from src.api.original_normalizer import NORMALIZER_VERSION, NormalizedTextLimitError, normalize_html
from src.api.original_location import bounded_preview, locate_chunk, whitespace_literal_matches
from src.ingestion.table_extractor import extract_table_rows, extract_table_unit, get_table_caption, rows_to_markdown


class OriginalViewerError(Exception):
    """A safe, user-displayable viewer failure with a stable machine code."""

    def __init__(self, code: str, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class OriginalViewerBusy(OriginalViewerError):
    def __init__(self) -> None:
        super().__init__("viewer_busy", "The original viewer is busy. Please retry shortly.", 503)


@dataclass(frozen=True)
class ViewerSourceSnapshot:
    source_document_id: str
    role: str
    label: str
    status: str
    reason: str | None
    document_revision: str | None
    text_length: int | None
    relative_filename: str
    normalized_text: str | None = None
    raw_sha256: str | None = None


@dataclass(frozen=True)
class ViewerDocumentSnapshot:
    document_id: str
    status: str
    reason: str | None
    source_set_revision: str
    sources: tuple[ViewerSourceSnapshot, ...]


def _positive_int(name: str, value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise OriginalViewerError("viewer_configuration_invalid", f"Viewer setting {name} must be a positive integer.", 500)
    return value


def _validate_settings() -> None:
    checks = (
        ("viewer_raw_file_max_bytes", settings.viewer_raw_file_max_bytes, "viewer_raw_file_hard_max_bytes", settings.viewer_raw_file_hard_max_bytes),
        ("viewer_processed_file_max_bytes", settings.viewer_processed_file_max_bytes, "viewer_processed_file_hard_max_bytes", settings.viewer_processed_file_hard_max_bytes),
        ("viewer_source_set_max_bytes", settings.viewer_source_set_max_bytes, "viewer_source_set_hard_max_bytes", settings.viewer_source_set_hard_max_bytes),
        ("viewer_normalized_source_max_codepoints", settings.viewer_normalized_source_max_codepoints, "viewer_normalized_source_hard_max_codepoints", settings.viewer_normalized_source_hard_max_codepoints),
        ("viewer_normalized_set_max_codepoints", settings.viewer_normalized_set_max_codepoints, "viewer_normalized_set_hard_max_codepoints", settings.viewer_normalized_set_hard_max_codepoints),
        ("viewer_companion_max", settings.viewer_companion_max, "viewer_companion_hard_max", settings.viewer_companion_hard_max),
    )
    for name, value, hard_name, hard_value in checks:
        _positive_int(name, value)
        _positive_int(hard_name, hard_value)
        if value > hard_value:
            raise OriginalViewerError("viewer_configuration_invalid", f"Viewer setting {name} exceeds {hard_name}.", 500)
    for name in (
        "viewer_window_default", "viewer_window_max", "viewer_find_default_limit",
        "viewer_find_max_limit", "viewer_max_pending_jobs", "viewer_cache_entries",
        "viewer_cache_max_bytes",
    ):
        _positive_int(name, getattr(settings, name))
    if settings.viewer_window_default > settings.viewer_window_max or settings.viewer_window_max > 32_000:
        raise OriginalViewerError("viewer_configuration_invalid", "Viewer window limits are invalid.", 500)
    if settings.viewer_find_default_limit > settings.viewer_find_max_limit or settings.viewer_find_max_limit > 100:
        raise OriginalViewerError("viewer_configuration_invalid", "Viewer search limits are invalid.", 500)
    if settings.viewer_max_pending_jobs > 8 or settings.viewer_cache_entries > 8 or settings.viewer_cache_max_bytes > 64 * 1024 * 1024:
        raise OriginalViewerError("viewer_configuration_invalid", "Viewer safety ceilings were raised beyond the supported maximum.", 500)


def _contained_path(root: Path, *parts: str) -> Path | None:
    """Resolve a validated candidate and prove it remains under the operator root."""
    if any(not isinstance(part, str) or not part or part in {".", ".."} or "/" in part or "\\" in part or ":" in part for part in parts):
        return None
    root_resolved = root.resolve()
    candidate = (root_resolved.joinpath(*parts)).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return None
    return candidate


_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,180}\.(?:html?|HTML?)$")
_ACCESSION_RE = re.compile(r"^\d{10}-\d{2}-\d{6}$")
_TICKER_RE = re.compile(r"^[A-Z]{1,5}(?:-[A-Z])?$")
_COMPANION_LABEL_RE = re.compile(r"annual report to (?:stockholders|security holders)", re.I)


def _safe_filename(value: str) -> bool:
    return bool(_FILENAME_RE.fullmatch(value)) and "%" not in value


def _source_id(document_id: str, role: str, relative_filename: str) -> str:
    payload = f"{document_id}\0{role}\0{relative_filename}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _document_revision(raw: bytes) -> str:
    return hashlib.sha256(NORMALIZER_VERSION.encode("utf-8") + b"\0" + raw).hexdigest()


def _read_bounded(path: Path, max_bytes: int) -> bytes:
    """Read a contained file and reject in-progress changes without path leaks."""
    for _attempt in range(2):
        try:
            before = path.stat()
            if not path.is_file():
                raise OriginalViewerError("source_unavailable", "The original source is unavailable.", 200)
            if before.st_size > max_bytes:
                raise OriginalViewerError("source_too_large", "The original source exceeds the configured size limit.", 200)
            with path.open("rb") as handle:
                raw = handle.read(max_bytes + 1)
            after = path.stat()
        except FileNotFoundError:
            raise OriginalViewerError("source_unavailable", "The original source is unavailable.", 200) from None
        if len(raw) > max_bytes:
            raise OriginalViewerError("source_too_large", "The original source exceeds the configured size limit.", 200)
        if before.st_size == after.st_size and before.st_mtime_ns == after.st_mtime_ns:
            return raw
    raise OriginalViewerError("source_changed", "The original source changed while it was being read.", 409)


def _safe_companion_filename(href: str) -> str | None:
    if not isinstance(href, str) or not href or "%" in href:
        return None
    parsed = urlparse(href)
    if parsed.scheme or parsed.netloc or parsed.params or parsed.query or not parsed.path:
        return None
    filename = parsed.path
    if "/" in filename or "\\" in filename or filename in {".", ".."}:
        return None
    return filename if _safe_filename(filename) else None


def _discover_companions(raw: bytes) -> list[tuple[str, str]]:
    soup = BeautifulSoup(raw, "lxml")
    discovered: dict[str, str] = {}
    for link in soup.find_all("a", href=True):
        label = " ".join(link.get_text(" ", strip=True).split())
        if not _COMPANION_LABEL_RE.search(label):
            continue
        filename = _safe_companion_filename(str(link["href"]).strip())
        if filename:
            discovered.setdefault(filename, label[:240])
    return sorted(discovered.items(), key=lambda item: (item[0], item[1]))


def _processed_metadata(ticker: str, accession: str) -> dict[str, Any]:
    accession_nodash = accession.replace("-", "")
    path = _contained_path(settings.data_processed_dir, ticker, f"{accession_nodash}_sections.json")
    if path is None:
        return {}
    try:
        raw = _read_bounded(path, settings.viewer_processed_file_max_bytes)
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, OriginalViewerError):
        return {}
    if not isinstance(parsed, dict) or parsed.get("ticker") != ticker or parsed.get("accession_number") != accession:
        return {}
    return parsed


def validated_filing_identity(row: dict[str, Any]) -> dict[str, Any] | None:
    """Return filing identity only when catalog and processed metadata agree."""
    ticker = row.get("ticker")
    accession = row.get("accession_number")
    if not isinstance(ticker, str) or not _TICKER_RE.fullmatch(ticker):
        return None
    if not isinstance(accession, str) or not _ACCESSION_RE.fullmatch(accession):
        return None
    document_id = row.get("document_id")
    if document_id != f"{ticker}:{accession}":
        return None
    metadata = _processed_metadata(ticker, accession)
    if metadata.get("document_id") not in {None, document_id}:
        return None
    cik = metadata.get("cik")
    if not isinstance(cik, int) or isinstance(cik, bool) or cik <= 0:
        return None
    return {
        "ticker": ticker,
        "cik": cik,
        "accession_number": accession,
        "filing_date": row.get("filing_date") if isinstance(row.get("filing_date"), str) else None,
        "report_date": row.get("report_date") if isinstance(row.get("report_date"), str) else None,
    }


def sec_index_url_for_document(row: dict[str, Any]) -> str | None:
    """Build a SEC index URL only from validated processed identity metadata."""
    identity = validated_filing_identity(row)
    if identity is None:
        return None
    accession = identity["accession_number"]
    cik = identity["cik"]
    accession_nodash = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/{accession}-index.html"


class OriginalViewer:
    def __init__(self) -> None:
        self._active = threading.Lock()
        self._pending_lock = threading.Lock()
        self._pending = 0
        self._text_cache: OrderedDict[tuple[str, str], str] = OrderedDict()
        self._cache_bytes = 0

    def run(self, _key: str, operation: Callable[[], Any]) -> Any:
        _validate_settings()
        with self._pending_lock:
            if self._pending >= settings.viewer_max_pending_jobs:
                raise OriginalViewerBusy()
            self._pending += 1
        try:
            with self._active:
                return operation()
        finally:
            with self._pending_lock:
                self._pending -= 1

    def _cached_text(self, source_id: str, revision: str) -> str | None:
        key = (source_id, revision)
        text = self._text_cache.get(key)
        if text is not None:
            self._text_cache.move_to_end(key)
        return text

    def _cache_text(self, source_id: str, revision: str, text: str) -> None:
        key = (source_id, revision)
        previous = self._text_cache.pop(key, None)
        if previous is not None:
            self._cache_bytes -= len(previous.encode("utf-8"))
        encoded_size = len(text.encode("utf-8"))
        if encoded_size > settings.viewer_cache_max_bytes:
            return
        self._text_cache[key] = text
        self._cache_bytes += encoded_size
        while len(self._text_cache) > settings.viewer_cache_entries or self._cache_bytes > settings.viewer_cache_max_bytes:
            _, evicted = self._text_cache.popitem(last=False)
            self._cache_bytes -= len(evicted.encode("utf-8"))

    def _make_source(
        self,
        document_id: str,
        role: str,
        label: str,
        relative_filename: str,
        path: Path | None,
        source_set_bytes: int,
    ) -> tuple[ViewerSourceSnapshot, bytes | None, int]:
        source_id = _source_id(document_id, role, relative_filename)
        if path is None:
            return ViewerSourceSnapshot(source_id, role, label, "unavailable", "The original source path is not allowed.", None, None, relative_filename), None, source_set_bytes
        try:
            raw = _read_bounded(path, settings.viewer_raw_file_max_bytes)
        except OriginalViewerError as error:
            return ViewerSourceSnapshot(source_id, role, label, "unavailable", error.message, None, None, relative_filename), None, source_set_bytes
        next_bytes = source_set_bytes + len(raw)
        if next_bytes > settings.viewer_source_set_hard_max_bytes:
            return ViewerSourceSnapshot(source_id, role, label, "unavailable", "The source set exceeds the hard size limit.", None, None, relative_filename), None, source_set_bytes
        revision = _document_revision(raw)
        text = self._cached_text(source_id, revision)
        try:
            if text is None:
                text = normalize_html(raw, max_codepoints=settings.viewer_normalized_source_max_codepoints)
                self._cache_text(source_id, revision, text)
        except NormalizedTextLimitError as error:
            return ViewerSourceSnapshot(source_id, role, label, "unavailable", str(error), revision, None, relative_filename, raw_sha256=hashlib.sha256(raw).hexdigest()), raw, next_bytes
        return ViewerSourceSnapshot(source_id, role, label, "available", None, revision, len(text), relative_filename, text, hashlib.sha256(raw).hexdigest()), raw, next_bytes

    def snapshot(self, row: dict[str, Any]) -> ViewerDocumentSnapshot:
        document_id = row.get("document_id")
        if not isinstance(document_id, str) or not document_id:
            raise OriginalViewerError("document_not_found", "Document not found.", 404)
        ticker = row.get("ticker")
        accession = row.get("accession_number")
        if not isinstance(ticker, str) or not _TICKER_RE.fullmatch(ticker) or not isinstance(accession, str) or not _ACCESSION_RE.fullmatch(accession):
            return ViewerDocumentSnapshot(document_id, "unavailable", "This document has no validated original identity.", "", ())
        accession_nodash = accession.replace("-", "")
        root = settings.data_raw_dir
        primary_path = _contained_path(root, ticker, f"{accession_nodash}.html")
        primary_relative = f"{ticker}/{accession_nodash}.html"
        primary, primary_raw, source_bytes = self._make_source(document_id, "primary_filing", "Primary filing", primary_relative, primary_path, 0)
        sources: list[ViewerSourceSnapshot] = [primary]
        incomplete_reason: str | None = None
        if primary_raw is not None:
            discovered = _discover_companions(primary_raw)
            if len(discovered) > settings.viewer_companion_max:
                incomplete_reason = "The companion inventory is bounded; some eligible links were not admitted."
            for filename, label in discovered[: settings.viewer_companion_max]:
                companion_path = _contained_path(root, ticker, filename)
                companion_relative = f"{ticker}/{filename}"
                companion, _, source_bytes = self._make_source(document_id, "annual_report_companion", f"Annual report companion · {label}", companion_relative, companion_path, source_bytes)
                sources.append(companion)
            if len(discovered) > settings.viewer_companion_hard_max:
                incomplete_reason = "The companion inventory exceeds the hard safety ceiling."
        total_codepoints = sum(source.text_length or 0 for source in sources if source.status == "available")
        if source_bytes > settings.viewer_source_set_max_bytes:
            incomplete_reason = incomplete_reason or "The source set exceeds the configured inventory budget."
        if total_codepoints > settings.viewer_normalized_set_hard_max_codepoints:
            incomplete_reason = "The normalized source set exceeds the hard code-point limit."
        elif total_codepoints > settings.viewer_normalized_set_max_codepoints:
            incomplete_reason = incomplete_reason or "The normalized source set exceeds the configured matching budget."
        available = [source for source in sources if source.status == "available"]
        status = "available" if available and len(available) == len(sources) and incomplete_reason is None else "partial" if available else "unavailable"
        reason = incomplete_reason
        if reason is None and status == "unavailable": reason = "No usable local original source is available."
        revision_payload = {
            "document_id": document_id,
            "normalizer_version": NORMALIZER_VERSION,
            "sources": [
                {
                    "source_document_id": source.source_document_id,
                    "status": source.status,
                    "document_revision": source.document_revision,
                }
                for source in sorted(sources, key=lambda item: item.source_document_id)
            ],
        }
        source_set_revision = hashlib.sha256(json.dumps(revision_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        return ViewerDocumentSnapshot(document_id, status, reason, source_set_revision, tuple(sources))

    def manifest(self, row: dict[str, Any]) -> dict[str, Any]:
        snapshot = self.snapshot(row)
        return {
            "document_id": snapshot.document_id,
            "status": snapshot.status,
            "reason": snapshot.reason,
            "normalizer_version": NORMALIZER_VERSION,
            "source_set_revision": snapshot.source_set_revision,
            "sources": [
                {
                    "source_document_id": source.source_document_id,
                    "role": source.role,
                    "label": source.label,
                    "status": source.status,
                    "reason": source.reason,
                    "document_revision": source.document_revision,
                    "text_length": source.text_length,
                }
                for source in snapshot.sources
            ],
        }

    def source_bytes(
        self,
        row: dict[str, Any],
        source_document_id: str,
        source_set_revision: str,
        document_revision: str,
    ) -> bytes:
        """Return validated local bytes to an application-owned parser only."""
        snapshot = self.snapshot(row)
        if snapshot.source_set_revision != source_set_revision:
            raise OriginalViewerError("source_changed", "The original source set changed. Reload the viewer.")
        source = next((item for item in snapshot.sources if item.source_document_id == source_document_id), None)
        if source is None or source.status != "available":
            raise OriginalViewerError("source_unavailable", "The selected original source is unavailable.", 404)
        if source.document_revision != document_revision:
            raise OriginalViewerError("source_changed", "The selected original source changed. Reload the viewer.")
        parts = source.relative_filename.split("/")
        path = _contained_path(settings.data_raw_dir, *parts)
        if path is None:
            raise OriginalViewerError("source_unavailable", "The selected original source is unavailable.", 404)
        raw = _read_bounded(path, settings.viewer_raw_file_max_bytes)
        if _document_revision(raw) != document_revision:
            raise OriginalViewerError("source_changed", "The selected original source changed. Reload the viewer.")
        return raw

    def content(
        self,
        row: dict[str, Any],
        source_document_id: str,
        source_set_revision: str,
        document_revision: str,
        start: int,
        limit: int,
        find: str | None = None,
        chunk_text: str | None = None,
        chunk_text_hash: str | None = None,
    ) -> dict[str, Any]:
        snapshot = self.snapshot(row)
        if snapshot.source_set_revision != source_set_revision:
            raise OriginalViewerError("source_changed", "The original source set changed. Reload the viewer.")
        source = next((item for item in snapshot.sources if item.source_document_id == source_document_id), None)
        if source is None or source.status != "available" or source.normalized_text is None:
            raise OriginalViewerError("source_unavailable", "The selected original source is unavailable.", 404)
        if source.document_revision != document_revision:
            raise OriginalViewerError("source_changed", "The selected original source changed. Reload the viewer.")
        if not 0 <= start <= len(source.normalized_text):
            raise OriginalViewerError("invalid_window", "The original text window is outside the available source.", 422)
        if not 1 <= limit <= settings.viewer_window_max:
            raise OriginalViewerError("invalid_window", "The original text window limit is invalid.", 422)
        end = min(len(source.normalized_text), start + limit)
        text = source.normalized_text
        query = find.strip() if isinstance(find, str) else ""
        if query and len(query) > 200:
            raise OriginalViewerError("invalid_search", "The inline search query is too long.", 422)
        spans: list[tuple[int, int]] = []
        if query:
            spans = whitespace_literal_matches(text, query)
        evidence_span: tuple[int, int] | None = None
        if (chunk_text is None) != (chunk_text_hash is None):
            raise OriginalViewerError("invalid_request", "chunk_id and chunk_text_hash must be supplied together.", 422)
        if chunk_text is not None and chunk_text_hash is not None:
            if hashlib.sha256(chunk_text.encode("utf-8")).hexdigest() != chunk_text_hash:
                raise OriginalViewerError("chunk_changed", "The indexed chunk changed. Reload the evidence.")
            presentation = build_chunk_presentation(chunk_text, "financial_table")
            location = self.table_location(row, chunk_text, chunk_text_hash, source_set_revision) if presentation["kind"] == "markdown_table" else locate_chunk(snapshot, chunk_text, chunk_text_hash, source_set_revision)
            if location["status"] == "exact" and location["location"]["source_document_id"] == source.source_document_id:
                evidence_span = (location["location"]["start"], location["location"]["end"])
        boundaries = {start, end}
        all_spans = spans + ([evidence_span] if evidence_span else [])
        for span_start, span_end in all_spans:
            if start < span_start < end: boundaries.add(span_start)
            if start < span_end < end: boundaries.add(span_end)
        ordered = sorted(boundaries)
        segments = [
            {
                "text": text[left:right],
                "evidence": bool(evidence_span and evidence_span[0] < right and evidence_span[1] > left),
                "search": any(span_start < right and span_end > left for span_start, span_end in spans),
            }
            for left, right in zip(ordered, ordered[1:]) if left < right
        ]
        return {
            "document_id": snapshot.document_id,
            "source_document_id": source.source_document_id,
            "source_set_revision": source_set_revision,
            "document_revision": document_revision,
            "start": start,
            "end": end,
            "total_length": len(text),
            "previous_start": max(0, start - limit) if start > 0 else None,
            "next_start": end if end < len(text) else None,
            "segments": segments,
        }

    def table_location(
        self,
        row: dict[str, Any],
        chunk_text: str,
        chunk_text_hash: str,
        source_set_revision: str,
    ) -> dict[str, Any]:
        snapshot = self.snapshot(row)
        if snapshot.source_set_revision != source_set_revision:
            raise OriginalViewerError("source_changed", "The original source set changed. Reload the evidence.")
        if hashlib.sha256(chunk_text.encode("utf-8")).hexdigest() != chunk_text_hash:
            raise OriginalViewerError("chunk_changed", "The indexed chunk changed. Reload the evidence.")
        if snapshot.status != "available" or any(source.status != "available" for source in snapshot.sources):
            return {"status": "unavailable", "reason": snapshot.reason or "The complete local source set is not available.", "match_count": 0, "match_count_capped": False, "location": None}
        presentation = build_chunk_presentation(chunk_text, "financial_table")
        if presentation["kind"] != "markdown_table":
            return {"status": "not_found", "reason": "The indexed chunk has no supported table presentation.", "match_count": 0, "match_count_capped": False, "location": None}
        matches: list[tuple[ViewerSourceSnapshot, int, int]] = []
        for source in snapshot.sources:
            filename = source.relative_filename.split("/", 1)[-1]
            path = _contained_path(settings.data_raw_dir, str(row["ticker"]), filename)
            if path is None:
                continue
            raw = _read_bounded(path, settings.viewer_raw_file_max_bytes)
            soup = BeautifulSoup(raw, "lxml")
            for table in soup.find_all("table"):
                rows = extract_table_rows(table)
                if not rows:
                    continue
                serialized = rows_to_markdown(rows, table_name=get_table_caption(table), table_unit=extract_table_unit(table))
                if serialized != chunk_text:
                    continue
                table_text = " ".join(table.get_text(" ", strip=True).split())
                spans = whitespace_literal_matches(source.normalized_text or "", table_text)
                if len(spans) != 1:
                    if len(spans) > 1:
                        return {"status": "ambiguous", "reason": "The matched source table text occurs more than once.", "match_count": 2, "match_count_capped": True, "location": None}
                    continue
                matches.append((source, spans[0][0], spans[0][1]))
                if len(matches) >= 2:
                    return {"status": "ambiguous", "reason": "The indexed table matches more than one eligible source table.", "match_count": 2, "match_count_capped": True, "location": None}
        if not matches:
            return {"status": "not_found", "reason": "The indexed table was not found as one unique source table.", "match_count": 0, "match_count_capped": False, "location": None}
        source, start, end = matches[0]
        return {
            "status": "exact",
            "reason": None,
            "match_count": 1,
            "match_count_capped": False,
            "location": {
                "source_document_id": source.source_document_id,
                "document_revision": source.document_revision,
                "method": "table_serialization",
                "start": start,
                "end": end,
            },
        }

    def search(
        self,
        row: dict[str, Any],
        source_document_id: str,
        source_set_revision: str,
        document_revision: str,
        query: str,
        cursor: int,
        limit: int,
    ) -> dict[str, Any]:
        snapshot = self.snapshot(row)
        if snapshot.source_set_revision != source_set_revision:
            raise OriginalViewerError("source_changed", "The original source set changed. Reload the viewer.")
        source = next((item for item in snapshot.sources if item.source_document_id == source_document_id), None)
        if source is None or source.status != "available" or source.normalized_text is None:
            raise OriginalViewerError("source_unavailable", "The selected original source is unavailable.", 404)
        if source.document_revision != document_revision:
            raise OriginalViewerError("source_changed", "The selected original source changed. Reload the viewer.")
        trimmed = query.strip()
        if not 2 <= len(trimmed) <= 200:
            raise OriginalViewerError("invalid_search", "Find queries must contain 2 to 200 characters.", 422)
        if not 0 <= cursor <= len(source.normalized_text):
            raise OriginalViewerError("invalid_search", "The search cursor is invalid.", 422)
        if not 1 <= limit <= settings.viewer_find_max_limit:
            raise OriginalViewerError("invalid_search", "The search result limit is invalid.", 422)
        text = source.normalized_text
        all_matches = whitespace_literal_matches(text, trimmed)
        page_matches = [match for match in all_matches if match[0] >= cursor][:limit]
        matches = [{"start": found, "end": end, "preview": bounded_preview(text, found, end)} for found, end in page_matches]
        next_cursor = page_matches[-1][0] + 1 if len(page_matches) == limit and any(match[0] > page_matches[-1][0] for match in all_matches) else None
        return {
            "document_id": snapshot.document_id,
            "source_document_id": source.source_document_id,
            "source_set_revision": source_set_revision,
            "document_revision": document_revision,
            "query": trimmed,
            "matches": matches,
            "next_cursor": next_cursor,
        }


original_viewer = OriginalViewer()
