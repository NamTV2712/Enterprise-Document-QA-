"""Canonical source resolution for the V4 document reader.

This module is intentionally local-only. It derives a browser-safe manifest from
the startup document catalog and the bounded original viewer; it never guesses a
CIK, fetches SEC content, or exposes a filesystem path.
"""
from __future__ import annotations

from typing import Any

from src.api.document_reader_models import (
    CanonicalSource,
    ReaderAvailability,
    ReaderFilingIdentity,
    ReaderManifest,
)
from src.api.original_viewer import OriginalViewer, sec_index_url_for_document, validated_filing_identity


def _source_reason_code(status: str) -> str:
    return "available" if status == "available" else "source_unavailable"


def build_reader_manifest(
    row: dict[str, Any],
    *,
    viewer: OriginalViewer,
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
            ),
            ReaderAvailability(
                kind="structured",
                status=snapshot.status,
                reason_code="available" if snapshot.status != "unavailable" else "structured_representation_unavailable",
                reason=None if snapshot.status != "unavailable" else "A structured document representation is not available in the local corpus.",
            ),
            ReaderAvailability(
                kind="pdf",
                status="unavailable",
                reason_code="pdf_representation_unavailable",
                reason="An official or derived PDF is not available in the local corpus.",
            ),
        ],
    ).model_dump(mode="json")
