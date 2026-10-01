"""Controlled DERIVED_PDF generation from verified local SEC source text.

The renderer consumes only the admitted, revision-bound normalized source text
resolved through the existing original-viewer pipeline. No URL, filesystem
path, or HTML body is accepted from the browser, and no active content from the
source is ever executed: the render template emits escaped plain text into a
fixed, font-pinned ReportLab document, so output is deterministic.

Mapping is captured by construction: every rendered text block records its own
PDF rectangles while drawing, and the sidecar binds those coordinates to the
resulting artifact hash. A paragraph split across lines or pages therefore
yields multiple exact rectangles.
"""
from __future__ import annotations

import hashlib
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from configs.settings import settings
from src.api.original_viewer import ViewerSourceSnapshot
from src.api.pdf_representation import (
    RENDERER_TEMPLATE_VERSION,
    PdfArtifactIdentity,
    PdfMappingEntry,
    PdfMappingManifest,
    PdfMappingRect,
    PdfRepresentationManifest,
    PdfRendererProfile,
    source_content_hash,
)

_MAX_BLOCKS = 20_000
_HEADING_PREFIXES = ("part ", "item ", "itemª", "signature", "exhibit ", "table of contents")
_SINGLE_FLIGHT_GUARD = threading.Lock()
_SINGLE_FLIGHT: dict[str, threading.Lock] = {}
_GENERATION_SLOTS = threading.BoundedSemaphore(max(1, min(settings.pdf_generation_concurrency, 4)))


class PdfGenerationError(RuntimeError):
    """A generation failure with a machine-readable code and HTTP status."""

    def __init__(self, code: str, message: str, http_status: int = 500) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


class PdfGenerationBusy(PdfGenerationError):
    def __init__(self, key: str) -> None:
        super().__init__(
            "pdf_generation_busy",
            "Another request is generating this PDF artifact; retry shortly.",
            http_status=409,
        )
        self.key = key


def _single_flight(key: str) -> threading.Lock:
    with _SINGLE_FLIGHT_GUARD:
        lock = _SINGLE_FLIGHT.get(key)
        if lock is None:
            lock = threading.Lock()
            _SINGLE_FLIGHT[key] = lock
        return lock


def split_blocks(full_text: str) -> list[dict[str, Any]]:
    """Split normalized text into stable source-line blocks with char ranges.

    The normalized SEC viewer intentionally preserves element/line boundaries
    as single newlines rather than requiring blank-line paragraphs. Splitting on
    every non-empty line keeps mapping ranges useful for real filings while
    remaining deterministic for synthetic prose and table fixtures.
    """
    blocks: list[dict[str, Any]] = []
    index = 0
    for match in __import__("re").finditer(r"[^\n]+", full_text):
        raw = match.group(0)
        text = raw.strip()
        if not text:
            continue
        char_start = match.start() + (len(raw) - len(raw.lstrip()))
        char_end = char_start + len(text)
        compact = text[:120]
        letters = [ch for ch in compact if ch.isalpha()]
        upper_ratio = (sum(1 for ch in letters if ch.isupper()) / len(letters)) if letters else 0.0
        is_heading = (
            len(text) <= 120
            and not text.rstrip().endswith((".", ";", ","))
            and (upper_ratio >= 0.8 or text.lower().startswith(_HEADING_PREFIXES))
        )
        is_table = "|" in text and text.count("|") >= 2
        blocks.append(
            {
                "block_id": f"normalized:{index}",
                "block_index": index,
                "block_kind": "table" if is_table else "heading" if is_heading else "paragraph",
                "char_start": char_start,
                "char_end": char_end,
                "text": text,
            }
        )
        index += 1
        if index >= _MAX_BLOCKS:
            break
    return blocks


def _escape(text: str) -> str:
    escaped = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return escaped.replace("\n", "<br/>")


def _validate_pdf_bytes(pdf_bytes: bytes, page_count: int) -> None:
    """Perform a dependency-free structural sanity check before promotion."""
    if not pdf_bytes.startswith(b"%PDF-") or b"%%EOF" not in pdf_bytes[-2048:]:
        raise PdfGenerationError("artifact_invalid", "The renderer produced bytes that are not a usable PDF.", 500)
    if page_count <= 0:
        raise PdfGenerationError("artifact_invalid", "The rendered PDF has no pages.", 500)
    page_objects = len(re.findall(rb"/Type\s*/Page(?!s)", pdf_bytes))
    if page_objects < page_count:
        raise PdfGenerationError("artifact_invalid", "The rendered PDF page tree could not be validated.", 500)
    if len(pdf_bytes) > settings.pdf_max_artifact_bytes:
        raise PdfGenerationError("artifact_too_large", "The rendered PDF exceeds the configured artifact limit.", 413)


class _RectRecorder:
    """Collects per-block rectangles while the document is drawn."""

    def __init__(self) -> None:
        self.rects: dict[str, list[PdfMappingRect]] = {}
        self.dropped: set[str] = set()


class _MappedParagraph(Paragraph):
    """Paragraph that records its own PDF rectangles while drawing.

    ReportLab's split() rebuilds fragments through ``self.__class__`` with
    framework kwargs, so the mapping identity is re-injected after every split.
    A block wrapped across lines or pages therefore yields one rect per
    fragment, each with its own page number.
    """

    def __init__(self, text: str, style: ParagraphStyle, block_id: str | None = None, recorder: "_RectRecorder | None" = None, **kwargs: Any) -> None:
        super().__init__(text, style, **kwargs)
        self._block_id = block_id
        self._recorder = recorder

    def draw(self) -> None:
        if self._block_id and self._recorder is not None:
            try:
                x, y = self.canv.absolutePosition(0, 0)
                rect = PdfMappingRect(page=self.canv.getPageNumber(), x=round(x, 2), y=round(y, 2), w=round(self.width, 2), h=round(self.height, 2))
                self._recorder.rects.setdefault(self._block_id, []).append(rect)
            except Exception:  # pragma: no cover - defensive; never break rendering
                self._recorder.dropped.add(self._block_id)
        super().draw()

    def split(self, availWidth: int, availHeight: int) -> list[Any]:
        fragments = super().split(availWidth, availHeight)
        for fragment in fragments:
            fragment._block_id = self._block_id
            fragment._recorder = self._recorder
        return fragments


def render_pdf(
    blocks: list[dict[str, Any]],
    *,
    header_lines: list[str],
) -> tuple[bytes, int, _RectRecorder]:
    """Render the controlled print document and return (bytes, page_count, recorder)."""
    recorder = _RectRecorder()
    body_style = ParagraphStyle(
        "filing-body",
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#111111"),
        spaceAfter=6,
    )
    heading_style = ParagraphStyle(
        "filing-heading",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        spaceBefore=8,
        spaceAfter=5,
    )
    meta_style = ParagraphStyle(
        "filing-meta",
        parent=body_style,
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#444444"),
        spaceAfter=10,
    )

    story: list[Any] = []
    for line in header_lines:
        story.append(Paragraph(_escape(line), meta_style))
    for block in blocks:
        style = heading_style if block["block_kind"] == "heading" else body_style
        story.append(_MappedParagraph(_escape(str(block["text"])), style, str(block["block_id"]), recorder))
        story.append(Spacer(1, 1))

    import io

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=56,
        leftMargin=56,
        topMargin=56,
        bottomMargin=56,
        title="Derived PDF from official SEC filing",
        author="Enterprise Document QA derived-PDF renderer",
        subject="Generated PDF derived from the verified local SEC filing source",
        creator=f"edqa-derived-pdf ({RENDERER_TEMPLATE_VERSION})",
    )
    document.build(story)
    page_count = document.page
    return buffer.getvalue(), page_count, recorder


def generate_derived_pdf(
    row: dict[str, Any],
    *,
    document_id: str,
    source: ViewerSourceSnapshot,
    source_set_revision: str,
    timeout_seconds: float,
    store: Any = None,
) -> tuple[PdfRepresentationManifest, PdfMappingManifest, bytes]:
    """Render, validate, and describe one derived-PDF artifact for one identity."""
    source_document_id = source.source_document_id
    document_revision = source.document_revision or ""
    # Single-flight is keyed on the stable identity fields excluding the content
    # hash: concurrent requests for the same document revision must not spawn
    # duplicate render jobs.
    stable_key = hashlib.sha256(
        "|".join([
            document_id,
            source_document_id,
            source_set_revision,
            document_revision,
            PdfRendererProfile().renderer_version,
            PdfRendererProfile().template_version,
        ]).encode("utf-8")
    ).hexdigest()[:32]
    if not _GENERATION_SLOTS.acquire(timeout=timeout_seconds):
        raise PdfGenerationBusy(stable_key)
    lock = _single_flight(stable_key)
    if not lock.acquire(timeout=timeout_seconds):
        _GENERATION_SLOTS.release()
        raise PdfGenerationBusy(stable_key)
    try:
        started = time.monotonic()
        full_text = str(source.normalized_text or "")
        if not full_text.strip():
            raise PdfGenerationError("source_unavailable", "The verified source text is empty; nothing to render.", 409)
        if len(full_text) > min(settings.pdf_source_max_codepoints, 8_000_000):
            raise PdfGenerationError("source_too_large", "The verified source exceeds the PDF generation limit.", 413)
        blocks = split_blocks(full_text)
        if not blocks:
            raise PdfGenerationError("source_unavailable", "No renderable blocks were found in the verified source text.", 409)
        if len(blocks) > min(settings.pdf_max_blocks, _MAX_BLOCKS):
            raise PdfGenerationError("source_too_large", "The verified source has too many renderable blocks.", 413)
        raw_hash = source_content_hash(full_text)
        identity = PdfArtifactIdentity(
            representation_type="DERIVED_PDF",
            document_id=document_id,
            source_document_id=source_document_id,
            source_set_revision=source_set_revision,
            document_revision=document_revision,
            source_content_hash=raw_hash,
        )
        label = str(row.get("ticker") or "SEC filing")
        header_lines = [
            f"Generated PDF - Derived from official SEC filing - {label}",
            f"Source document {source_document_id} - source set revision {source_set_revision[:24]} - document revision {document_revision[:24]}",
            "This artifact was generated by the local system from the admitted filing text; page numbers refer to the generated representation.",
        ]
        try:
            pdf_bytes, page_count, recorder = render_pdf(blocks, header_lines=header_lines)
        except Exception as error:  # pragma: no cover - renderer crash path
            raise PdfGenerationError("renderer_failed", f"The PDF renderer failed: {error}", 500) from error
        if time.monotonic() - started > timeout_seconds:
            raise PdfGenerationError("render_timeout", "PDF generation exceeded the configured time limit.", 504)
        _validate_pdf_bytes(pdf_bytes, page_count)
        if page_count <= 0 or len(recorder.rects) == 0:
            raise PdfGenerationError("artifact_invalid", "The rendered artifact has no pages or no mapped blocks.", 500)

        artifact_hash = hashlib.sha256(pdf_bytes).hexdigest()
        entries: list[PdfMappingEntry] = []
        for block in blocks:
            block_id = str(block["block_id"])
            rects = recorder.rects.get(block_id, [])
            entries.append(
                PdfMappingEntry(
                    block_id=block_id,
                    block_index=int(block["block_index"]),
                    block_kind=str(block["block_kind"]),  # type: ignore[arg-type]
                    char_start=int(block["char_start"]),
                    char_end=int(block["char_end"]),
                    text_preview=str(block["text"])[:240],
                    status="exact" if rects else "unavailable",
                    reason=None if rects else "The block was not placed in the rendered artifact.",
                    rects=rects,
                )
            )
        mapping_status = "exact" if all(entry.rects for entry in entries) else "unavailable"
        mapping = PdfMappingManifest(
            mapping_manifest_id=f"mapping:{identity.artifact_key()}",
            representation_id=identity.representation_id(),
            document_id=document_id,
            source_document_id=source_document_id,
            source_content_hash=identity.source_content_hash,
            artifact_key=identity.artifact_key(),
            artifact_hash=artifact_hash,
            source_set_revision=source_set_revision,
            document_revision=document_revision,
            entries=entries,
        )
        elapsed = time.monotonic() - started
        manifest = PdfRepresentationManifest(
            representation_id=identity.representation_id(),
            representation_type="DERIVED_PDF",
            page_semantics="generated_representation_pages",
            artifact_status="available",
            document_id=document_id,
            source_document_id=source_document_id,
            source_set_revision=source_set_revision,
            document_revision=document_revision,
            source_content_hash=identity.source_content_hash,
            artifact_key=identity.artifact_key(),
            artifact_hash=artifact_hash,
            artifact_size_bytes=len(pdf_bytes),
            page_count=page_count,
            renderer=PdfRendererProfile(),
            generated_at=datetime.now(timezone.utc).isoformat(),
            mapping_manifest_id=mapping.mapping_manifest_id,
            mapping_status=mapping_status,  # type: ignore[arg-type]
            mapping_entry_count=len(entries),
            reason=f"Rendered {page_count} generated pages from {len(entries)} source blocks in {elapsed:.2f}s.",
        )
        return manifest, mapping, pdf_bytes
    finally:
        lock.release()
        _GENERATION_SLOTS.release()
