"""Canonical source resolution for the V4 document reader.

This module is intentionally local-only. It derives a browser-safe manifest from
the startup document catalog and the bounded original viewer; it never guesses a
CIK, fetches SEC content, or exposes a filesystem path.
"""
from __future__ import annotations

from typing import Any

from src.api.document_reader_models import (
    CanonicalSource,
    CoverageStatus,
    ReaderAvailability,
    ReaderFilingIdentity,
    ReaderManifest,
)
from src.api.original_viewer import OriginalViewer, OriginalViewerError, sec_index_url_for_document, validated_filing_identity
from src.api.structured_document import StructuredDocumentService


def _source_reason_code(status: str) -> str:
    return "available" if status == "available" else "source_unavailable"


def _structured_details(
    row: dict[str, Any],
    snapshot: Any,
    *,
    viewer: OriginalViewer,
    reader: StructuredDocumentService | None,
) -> tuple[str, CoverageStatus, str | None, str | None, str | None]:
    """Assess structured coverage per admitted source without changing storage."""
    available_sources = [source for source in snapshot.sources if source.status == "available" and source.document_revision]
    if not available_sources:
        return (
            "unavailable",
            "unknown",
            "A structured document representation is not available in the local corpus.",
            "source_unavailable",
            "structured_representation_unavailable",
        )
    service = reader or StructuredDocumentService(viewer)
    documents = []
    failures: list[str] = []
    for source in available_sources:
        try:
            documents.append(service.document(row, source.source_document_id, snapshot.source_set_revision, source.document_revision or ""))
        except OriginalViewerError as error:
            failures.append(error.message)
    if not documents:
        return (
            "unavailable",
            "unknown",
            "The structured document representation could not be loaded from the local source.",
            "coverage_not_assessed",
            "structured_representation_unavailable",
        )
    if failures:
        return (
            "partial" if snapshot.status != "unavailable" else "unavailable",
            "unknown",
            "Coverage could not be assessed for every admitted structured source.",
            "coverage_not_assessed",
            None,
        )
    if snapshot.status == "partial":
        return (
            "partial",
            "partial",
            snapshot.reason or "The structured view covers only the available portion of the declared source set.",
            "source_set_incomplete",
            None,
        )
    partial = next((document for document in documents if document.coverage_status == "partial"), None)
    if partial is not None:
        return "available", "partial", partial.coverage_reason, partial.coverage_reason_code, None
    unknown = next((document for document in documents if document.coverage_status == "unknown"), None)
    if unknown is not None:
        return "available", "unknown", unknown.coverage_reason, unknown.coverage_reason_code, None
    return "available", "complete", "All visible source text is represented in this structured view.", "verified_complete", None


def build_reader_manifest(
    row: dict[str, Any],
    *,
    viewer: OriginalViewer,
    structured_reader: StructuredDocumentService | None = None,
) -> dict[str, Any]:
    """Resolve one catalog row to a stable, revision-bound reader manifest."""
    snapshot = viewer.snapshot(row)
    verified = validated_filing_identity(row)
    identity = ReaderFilingIdentity(
        ticker=verified.get("ticker") if verified else row.get("ticker"),
        cik=verified.get("cik") if verified else None,
        accession_number=verified.get("accession_number") if verified else row.get("accession_number"),
        filing_date=verified.get("filing_date") if verified else row.get("filing_date"),
        report_date=verified.get("report_date") if verified else row.get("report_date"),
        status="verified" if verified else "unverified",
        reason_code="verified" if verified else "identity_unverified",
    )
    canonical_index_url = sec_index_url_for_document(row) if verified else None
    sources = [
        CanonicalSource(
            source_document_id=source.source_document_id,
            role=source.role,
            label=source.label,
            status=source.status,
            reason_code=_source_reason_code(source.status),
            reason=source.reason,
            canonical_url=canonical_index_url if source.role == "primary_filing" else None,
            document_revision=source.document_revision,
            text_length=source.text_length,
        )
        for source in snapshot.sources
    ]
    reader_reason_code = "available" if snapshot.status != "unavailable" else (
        "identity_unverified" if not verified else "source_unavailable"
    )
    structured_status, structured_coverage, structured_coverage_reason, structured_coverage_code, structured_unavailable_code = _structured_details(
        row,
        snapshot,
        viewer=viewer,
        reader=structured_reader,
    )
    normalized_coverage: CoverageStatus = "complete" if snapshot.status == "available" else "partial" if snapshot.status == "partial" else "unknown"
    normalized_coverage_reason = (
        "All admitted normalized local text is available."
        if normalized_coverage == "complete"
        else snapshot.reason or "The normalized local source set is incomplete."
        if normalized_coverage == "partial"
        else "Normalized local text is unavailable."
    )
    normalized_coverage_code = "verified_complete" if normalized_coverage == "complete" else "source_set_incomplete" if normalized_coverage == "partial" else "source_unavailable"
    structured_reason_code = structured_unavailable_code or ("available" if structured_status != "unavailable" else "structured_representation_unavailable")
    return ReaderManifest(
        document_id=snapshot.document_id,
        status=snapshot.status,
        reason_code=reader_reason_code,
        reason=snapshot.reason or (None if verified else "The filing identity is not fully verified from local metadata."),
        identity=identity,
        source_set_revision=snapshot.source_set_revision,
        sources=sources,
        representations=[
            ReaderAvailability(
                kind="normalized_text",
                status=snapshot.status,
                reason_code="available" if snapshot.status != "unavailable" else reader_reason_code,
                reason=snapshot.reason,
                coverage_status=normalized_coverage,
                coverage_reason=normalized_coverage_reason,
                coverage_reason_code=normalized_coverage_code,
            ),
            ReaderAvailability(
                kind="structured",
                status=structured_status,
                reason_code=structured_reason_code,
                reason=structured_coverage_reason if structured_status != "available" else None,
                coverage_status=structured_coverage,
                coverage_reason=structured_coverage_reason,
                coverage_reason_code=structured_coverage_code,
            ),
            ReaderAvailability(
                kind="pdf",
                status="unavailable",
                reason_code="pdf_representation_unavailable",
                reason="An official or derived PDF is not available in the local corpus.",
                coverage_status="unknown",
                coverage_reason="An official or derived PDF is not available in the local corpus.",
                coverage_reason_code="pdf_representation_unavailable",
            ),
        ],
    ).model_dump(mode="json")
