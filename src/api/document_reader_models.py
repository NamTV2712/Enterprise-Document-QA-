"""Typed contracts for the V4 document reader identity and availability surface."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ReaderStatus = Literal["available", "partial", "unavailable"]
SourceStatus = Literal["available", "unavailable"]
AvailabilityCode = Literal[
    "available",
    "identity_unverified",
    "source_unavailable",
    "structured_representation_unavailable",
    "pdf_representation_unavailable",
]


class ReaderFilingIdentity(BaseModel):
    """Identity is verified only when local metadata agrees with the document row."""

    ticker: str | None = None
    cik: int | None = Field(default=None, ge=1)
    accession_number: str | None = None
    filing_date: str | None = None
    report_date: str | None = None
    status: Literal["verified", "unverified"]
    reason_code: Literal["verified", "identity_unverified"]


class ReaderAvailability(BaseModel):
    """Availability of one representation without implying remote acquisition."""

    kind: Literal["normalized_text", "structured", "pdf"]
    status: ReaderStatus
    reason_code: AvailabilityCode
    reason: str | None = None


class CanonicalSource(BaseModel):
    """A stable source identity safe to send to the browser."""

    source_document_id: str = Field(min_length=1, max_length=128)
    role: Literal["primary_filing", "annual_report_companion"]
    label: str = Field(min_length=1, max_length=240)
    status: SourceStatus
    reason_code: AvailabilityCode
    reason: str | None = None
    canonical_url: str | None = None
    media_type: Literal["text/html"] = "text/html"
    document_revision: str | None = None
    text_length: int | None = Field(default=None, ge=0)


class ReaderManifest(BaseModel):
    """Revision-bound reader manifest; paths and acquisition details are excluded."""

    schema_version: Literal["sec-reader-v4"] = "sec-reader-v4"
    document_id: str = Field(min_length=1, max_length=256)
    status: ReaderStatus
    reason_code: AvailabilityCode
    reason: str | None = None
    identity: ReaderFilingIdentity
    source_set_revision: str
    sources: list[CanonicalSource]
    representations: list[ReaderAvailability]


class ReaderResolveRequest(BaseModel):
    refresh: bool = False


class ReaderAcquisition(BaseModel):
    status: Literal["not_needed", "acquired", "unavailable"]
    code: str
    message: str
    canonical_url: str | None = None
    raw_sha256: str | None = None
    bytes_received: int | None = Field(default=None, ge=0)
    request_count: int = Field(default=0, ge=0, le=4)


class ReaderResolveResponse(BaseModel):
    manifest: ReaderManifest
    acquisition: ReaderAcquisition


class EvidenceRange(BaseModel):
    """A source-backed range in one immutable structured block."""

    block_id: str = Field(min_length=1, max_length=128)
    block_index: int = Field(ge=0)
    kind: Literal["heading", "paragraph", "list", "table", "separator", "unsupported"]
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    method: Literal["text_whitespace", "table_semantic"]


class EvidenceLocation(BaseModel):
    """Exact structured correspondence or an explicit non-provable result."""

    chunk_id: str = Field(min_length=1, max_length=256)
    chunk_text_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    document_id: str = Field(min_length=1, max_length=256)
    source_set_revision: str = Field(min_length=1, max_length=128)
    status: Literal["exact", "ambiguous", "not_found", "unavailable", "stale"]
    reason_code: Literal["exact", "ambiguous", "not_found", "unavailable", "stale"]
    reason: str | None = None
    source_document_id: str | None = None
    document_revision: str | None = None
    representation_revision: str | None = None
    ranges: list[EvidenceRange] = Field(default_factory=list)
    match_count: int = Field(default=0, ge=0, le=2)
    match_count_capped: bool = False
