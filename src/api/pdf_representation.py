"""Derived-PDF representation contracts, identity, and artifact storage.

A generated PDF is a DOCUMENT REPRESENTATION, never an evidence identity. Every
artifact is bound to the verified source revision it was rendered from:
document_id + source_document_id + source_set_revision + document_revision +
source_content_hash + renderer profile. When any binding field changes, the
previous artifact is reported ``stale`` and is never silently reused.

The generation surface accepts only a project-owned ``document_id``; no URL,
filesystem path, or HTML body is ever accepted from the browser.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

PDF_MANIFEST_SCHEMA_VERSION = "sec-pdf-manifest-v2"
PDF_MAPPING_SCHEMA_VERSION = "sec-pdf-mapping-v2"

PdfRepresentationType = Literal["OFFICIAL_PDF", "DERIVED_PDF"]
PdfArtifactStatus = Literal[
    "unavailable", "supported", "generating", "available", "failed", "stale", "unsupported"
]
PdfMappingStatus = Literal["exact", "ambiguous", "unavailable", "stale"]
PdfPageSemantics = Literal["official_pdf_pages", "generated_representation_pages"]

RENDERER_NAME = "reportlab-platypus"
RENDERER_VERSION = "reportlab-4.2.5"
RENDERER_TEMPLATE_VERSION = "restrained-filing-v1"
RENDERER_PAGE_SIZE = "A4"
RENDERER_ORIENTATION = "portrait"
RENDERER_MARGINS_PT = {"top": 56, "bottom": 56, "left": 56, "right": 56}


class PdfRendererProfile(BaseModel):
    """Frozen render environment; part of the artifact identity."""

    renderer: str = RENDERER_NAME
    renderer_version: str = RENDERER_VERSION
    template_version: str = RENDERER_TEMPLATE_VERSION
    page_size: str = RENDERER_PAGE_SIZE
    orientation: str = RENDERER_ORIENTATION
    margins_pt: dict[str, int] = Field(default_factory=lambda: dict(RENDERER_MARGINS_PT))
    print_background: bool = True
    locale: str = "en-US"
    font_family: str = "Helvetica"


class PdfArtifactIdentity(BaseModel):
    """Identity binding; the artifact key is derived, never supplied."""

    representation_type: PdfRepresentationType = "DERIVED_PDF"
    document_id: str = Field(min_length=1, max_length=256)
    source_document_id: str = Field(min_length=1, max_length=128)
    source_set_revision: str = Field(min_length=1, max_length=128)
    document_revision: str = Field(min_length=1, max_length=128)
    source_content_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    renderer: PdfRendererProfile = Field(default_factory=PdfRendererProfile)
    artifact_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    def artifact_key(self) -> str:
        """Deterministic storage key derived from the full identity binding."""
        payload = json.dumps(self.model_dump(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]

    def representation_id(self) -> str:
        """Stable browser-facing identity for this representation artifact."""
        return f"{self.representation_type.lower()}:{self.artifact_key()}"


class PdfMappingRect(BaseModel):
    """One rectangle in PDF points, origin bottom-left of the generated page."""

    page: int = Field(ge=1)
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    w: float = Field(gt=0)
    h: float = Field(gt=0)


class PdfMappingEntry(BaseModel):
    """Correspondence for one render block of the verified source text."""

    block_id: str = Field(min_length=1, max_length=256)
    block_index: int = Field(ge=0)
    block_kind: Literal["heading", "paragraph", "table"]
    char_start: int = Field(ge=0)
    char_end: int = Field(gt=0)
    text_preview: str = Field(max_length=240)
    status: PdfMappingStatus = "exact"
    reason: str | None = None
    rects: list[PdfMappingRect] = Field(default_factory=list)


class PdfMappingManifest(BaseModel):
    """Mapping sidecar bound to one exact PDF artifact hash."""

    schema_version: str = PDF_MAPPING_SCHEMA_VERSION
    mapping_manifest_id: str | None = None
    representation_id: str
    document_id: str
    source_document_id: str
    source_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_key: str
    artifact_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_set_revision: str
    document_revision: str
    entries: list[PdfMappingEntry] = Field(default_factory=list)


class PdfEvidenceLocation(BaseModel):
    """A source-bound PDF location safe for citation highlighting."""

    schema_version: str = "sec-pdf-evidence-location-v1"
    document_id: str
    source_document_id: str
    source_set_revision: str
    document_revision: str
    source_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    representation_id: str
    artifact_key: str
    artifact_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    mapping_manifest_id: str | None = None
    chunk_id: str
    chunk_text_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: PdfMappingStatus
    reason: str | None = None
    match_count: int = Field(default=0, ge=0, le=2)
    match_count_capped: bool = False
    entry_ids: list[str] = Field(default_factory=list)
    rects: list[PdfMappingRect] = Field(default_factory=list)


class PdfRepresentationManifest(BaseModel):
    """Browser-safe PDF representation manifest; no paths or acquisition data."""

    schema_version: str = PDF_MANIFEST_SCHEMA_VERSION
    representation_id: str
    representation_type: PdfRepresentationType = "DERIVED_PDF"
    page_semantics: PdfPageSemantics = "generated_representation_pages"
    artifact_status: PdfArtifactStatus
    document_id: str = Field(min_length=1, max_length=256)
    source_document_id: str | None = Field(default=None, max_length=128)
    source_set_revision: str | None = Field(default=None, max_length=128)
    document_revision: str | None = Field(default=None, max_length=128)
    source_content_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    artifact_key: str | None = None
    artifact_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    artifact_size_bytes: int | None = Field(default=None, ge=0)
    page_count: int | None = Field(default=None, ge=0)
    renderer: PdfRendererProfile = Field(default_factory=PdfRendererProfile)
    generated_at: str | None = None
    mapping_manifest_id: str | None = None
    mapping_status: PdfMappingStatus = "unavailable"
    mapping_entry_count: int = Field(default=0, ge=0)
    reason: str | None = None


class PdfStore:
    """Backend-managed artifact storage with atomic promotion semantics."""

    def __init__(self, root: Path) -> None:
        self.root = root

    @staticmethod
    def _validate_key(key: str) -> str:
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", key):
            raise ValueError("Invalid PDF artifact key")
        return key

    def artifact_dir(self, key: str) -> Path:
        return self.root / self._validate_key(key)

    def load_manifest(self, key: str) -> PdfRepresentationManifest | None:
        path = self.artifact_dir(key) / "manifest.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return PdfRepresentationManifest.model_validate(raw)
        except (OSError, ValueError):
            return None

    def load_mapping(self, key: str) -> PdfMappingManifest | None:
        path = self.artifact_dir(key) / "mapping.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return PdfMappingManifest.model_validate(raw)
        except (OSError, ValueError):
            return None

    def artifact_path(self, key: str) -> Path:
        return self.artifact_dir(key) / "artifact.pdf"

    def promote(
        self,
        key: str,
        pdf_bytes: bytes,
        manifest: PdfRepresentationManifest,
        mapping: PdfMappingManifest,
    ) -> None:
        """Publish validated artifact bytes and manifests atomically.

        Everything is written into a temporary sibling directory first; the
        directory rename is the atomic publication point, so a crash can never
        leave a half-written current artifact behind.
        """
        self._validate_key(key)
        actual_hash = hashlib.sha256(pdf_bytes).hexdigest()
        if manifest.artifact_key != key or manifest.artifact_hash != actual_hash:
            raise ValueError("PDF manifest is not bound to the artifact bytes")
        if mapping.artifact_key != key or mapping.artifact_hash != actual_hash:
            raise ValueError("PDF mapping is not bound to the artifact bytes")
        if (
            mapping.representation_id != manifest.representation_id
            or mapping.document_id != manifest.document_id
            or mapping.source_document_id != manifest.source_document_id
            or mapping.source_content_hash != manifest.source_content_hash
            or mapping.source_set_revision != (manifest.source_set_revision or "")
            or mapping.document_revision != (manifest.document_revision or "")
        ):
            raise ValueError("PDF mapping is not bound to the manifest source identity")
        if manifest.mapping_manifest_id and mapping.mapping_manifest_id not in {None, manifest.mapping_manifest_id}:
            raise ValueError("PDF manifest and mapping manifest identities differ")
        final_dir = self.artifact_dir(key)
        self.root.mkdir(parents=True, exist_ok=True)
        temp_dir = self.root / f".tmp-{key}-{uuid.uuid4().hex}"
        quarantine_dir: Path | None = None
        temp_dir.mkdir(parents=True)
        try:
            artifact_temp = temp_dir / "artifact.pdf"
            artifact_temp.write_bytes(pdf_bytes)
            (temp_dir / "manifest.json").write_text(manifest.model_dump_json(indent=1), encoding="utf-8")
            (temp_dir / "mapping.json").write_text(mapping.model_dump_json(indent=1), encoding="utf-8")
            for path in (artifact_temp, temp_dir / "manifest.json", temp_dir / "mapping.json"):
                with path.open("r+b") as handle:
                    os.fsync(handle.fileno())
            if final_dir.exists():
                existing = self.load_manifest(key)
                if existing is not None and existing.artifact_hash == actual_hash and self.artifact_path(key).is_file():
                    return
                quarantine_dir = self.root / f".stale-{key}-{uuid.uuid4().hex}"
                os.replace(final_dir, quarantine_dir)
            os.replace(temp_dir, final_dir)
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            if quarantine_dir is not None and quarantine_dir.exists():
                shutil.rmtree(quarantine_dir, ignore_errors=True)

    def record_failure(self, key: str, reason: str) -> None:
        """Persist a failure receipt so the UI can report a retryable state."""
        final_dir = self.artifact_dir(key)
        final_dir.mkdir(parents=True, exist_ok=True)
        receipt = {
            "artifact_status": "failed",
            "reason": reason[:500],
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        (final_dir / "failure.json").write_text(json.dumps(receipt, indent=1), encoding="utf-8")

    def load_failure(self, key: str) -> dict[str, Any] | None:
        path = self.artifact_dir(key) / "failure.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def write_latest(self, stable_key: str, payload: dict[str, Any]) -> None:
        """Record the newest artifact binding for one stable identity family.

        The reader manifest uses this small marker to report available/stale
        without re-reading the full source text; the strict hash check still
        happens whenever artifact bytes are actually served.
        """
        self._validate_key(stable_key)
        latest_dir = self.root / "latest"
        latest_dir.mkdir(parents=True, exist_ok=True)
        temp = latest_dir / f".tmp-{stable_key}-{uuid.uuid4().hex}"
        temp.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        with temp.open("r+b") as handle:
            os.fsync(handle.fileno())
        os.replace(temp, latest_dir / f"{stable_key}.json")

    def read_latest(self, stable_key: str) -> dict[str, Any] | None:
        self._validate_key(stable_key)
        path = self.root / "latest" / f"{stable_key}.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def write_generation_state(
        self,
        stable_key: str,
        status: Literal["generating", "failed", "stale"],
        *,
        reason: str | None = None,
    ) -> None:
        """Publish a truthful lifecycle marker separate from artifact identity."""
        self._validate_key(stable_key)
        state_dir = self.root / "generation-state"
        state_dir.mkdir(parents=True, exist_ok=True)
        temp = state_dir / f".tmp-{stable_key}-{uuid.uuid4().hex}"
        temp.write_text(
            json.dumps(
                {
                    "status": status,
                    "reason": reason[:500] if reason else None,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=1,
            ),
            encoding="utf-8",
        )
        with temp.open("r+b") as handle:
            os.fsync(handle.fileno())
        os.replace(temp, state_dir / f"{stable_key}.json")

    def read_generation_state(self, stable_key: str) -> dict[str, Any] | None:
        self._validate_key(stable_key)
        path = self.root / "generation-state" / f"{stable_key}.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def clear_generation_state(self, stable_key: str) -> None:
        self._validate_key(stable_key)
        path = self.root / "generation-state" / f"{stable_key}.json"
        try:
            path.unlink()
        except OSError:
            return


    def clear_failure(self, key: str) -> None:
        path = self.artifact_dir(key) / "failure.json"
        try:
            path.unlink()
        except OSError:
            return

    def status_for(
        self,
        identity: PdfArtifactIdentity,
        *,
        pdf_supported: bool,
    ) -> tuple[PdfArtifactStatus, PdfRepresentationManifest | None, str | None]:
        """Derive the truthful current status for one identity binding."""
        if not pdf_supported:
            return "unsupported", None, "PDF generation is disabled in this deployment."
        key = identity.artifact_key()
        manifest = self.load_manifest(key)
        if manifest is None:
            failure = self.load_failure(key)
            if failure:
                return "failed", None, str(failure.get("reason") or "The previous generation attempt failed.")
            return "supported", None, "A derived PDF can be generated from the verified local source."
        stored_identity_ok = (
            manifest.source_set_revision == identity.source_set_revision
            and manifest.document_revision == identity.document_revision
            and manifest.source_content_hash == identity.source_content_hash
            and manifest.renderer.renderer_version == identity.renderer.renderer_version
            and manifest.renderer.template_version == identity.renderer.template_version
        )
        if not stored_identity_ok:
            return "stale", manifest, "The stored PDF was generated from a different source revision."
        return "available", manifest, None


def official_pdf_manifest(
    *,
    document_id: str,
    source_document_id: str,
    source_set_revision: str,
    document_revision: str,
    source_content_hash: str,
    artifact_key: str,
    artifact_hash: str,
    artifact_size_bytes: int,
    page_count: int,
) -> PdfRepresentationManifest:
    """Describe a verified official artifact without relabelling a derived PDF.

    The current corpus does not admit an official PDF, but the shared manifest
    contract keeps this path explicit for a future trusted source inventory.
    The caller is an internal admission path; browser requests cannot supply
    the artifact or its filesystem location.
    """
    return PdfRepresentationManifest(
        representation_id=f"official_pdf:{artifact_key}",
        representation_type="OFFICIAL_PDF",
        page_semantics="official_pdf_pages",
        artifact_status="available",
        document_id=document_id,
        source_document_id=source_document_id,
        source_set_revision=source_set_revision,
        document_revision=document_revision,
        source_content_hash=source_content_hash,
        artifact_key=artifact_key,
        artifact_hash=artifact_hash,
        artifact_size_bytes=artifact_size_bytes,
        page_count=page_count,
        renderer=PdfRendererProfile(
            renderer="verified-official-source",
            renderer_version="source-artifact",
            template_version="not_applicable",
        ),
        generated_at=None,
        reason="Verified official PDF source artifact; page numbers refer to the official PDF.",
    )


def source_content_hash(text: str) -> str:
    """Content hash over the exact admitted source text used for rendering."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
