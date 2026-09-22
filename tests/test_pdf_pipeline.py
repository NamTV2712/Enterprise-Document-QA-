"""PDF-01/PDF-02 contract, generator, storage, and route tests.

These tests prove that a derived PDF is bound to one verified source revision,
that identity changes invalidate artifacts, and that the generation surface
accepts only a project-owned document id (never a URL, path, or HTML body).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

import pytest
from fastapi.testclient import TestClient

from configs.settings import settings
from src.api import app as app_module
from src.api import original_viewer
from src.api import pdf_generator as pdf_generator_module
from src.api.pdf_generator import PdfGenerationBusy, generate_derived_pdf, split_blocks
from src.api.pdf_representation import (
    PdfArtifactIdentity,
    PdfMappingManifest,
    PdfRendererProfile,
    PdfRepresentationManifest,
    PdfStore,
    official_pdf_manifest,
)


@dataclass
class FakeSource:
    source_document_id: str = "AAPL:primary"
    role: str = "primary_filing"
    label: str = "Primary filing"
    status: str = "available"
    reason: str | None = None
    document_revision: str | None = "rev-1"
    text_length: int | None = None
    relative_filename: str = "aapl.htm"
    normalized_text: str | None = None
    raw_sha256: str | None = "a" * 64


@dataclass
class FakeSnapshot:
    document_id: str = "AAPL:0001"
    status: str = "available"
    reason: str | None = None
    source_set_revision: str = "ssr-1"
    sources: tuple[Any, ...] = field(default_factory=tuple)


SAMPLE_TEXT = (
    "PART I\n\n"
    "Item 1. Business\n\n"
    "The Company designs and markets smartphones and personal computers. "
    "Its fiscal year is the 52- or 53-week period that ends on the last Saturday of September.\n\n"
    "Risk Factors. Global economic conditions could adversely affect demand for the "
    "Company's products and services, including inflation, interest rates, and trade tensions.\n\n"
)

LONG_PARAGRAPH = (
    "Global economic conditions remain uncertain and adverse developments in the U.S. "
    "or international markets could reduce consumer spending. " * 220
)

SOURCE_LAYOUT_TABLE = (
    "CONSOLIDATED STATEMENTS OF OPERATIONS\n\n"
    "| Fiscal year | Revenue | Net income |\n"
    "| 2025 | 100 | 20 |\n"
    "| 2024 | 90 | 18 |\n"
)

IDENTITY = PdfArtifactIdentity(
    document_id="AAPL:0001",
    source_document_id="AAPL:primary",
    source_set_revision="ssr-1",
    document_revision="rev-1",
    source_content_hash="b" * 64,
)
TEST_ARTIFACT = b"%PDF-1.4 ... %%EOF"
TEST_ARTIFACT_HASH = hashlib.sha256(TEST_ARTIFACT).hexdigest()


def _identity_changed(**overrides: str) -> PdfArtifactIdentity:
    values = {
        "document_id": IDENTITY.document_id,
        "source_document_id": IDENTITY.source_document_id,
        "source_set_revision": IDENTITY.source_set_revision,
        "document_revision": IDENTITY.document_revision,
        "source_content_hash": IDENTITY.source_content_hash,
    }
    values.update(overrides)
    return PdfArtifactIdentity(**values)


def _make_source(text: str = SAMPLE_TEXT + LONG_PARAGRAPH, revision: str = "rev-1", sha: str = "a" * 64) -> FakeSource:
    return FakeSource(document_revision=revision, normalized_text=text, raw_sha256=sha, text_length=len(text))


# --- PDF-01: identity and store contracts -------------------------------------


def test_identity_key_is_deterministic_and_binding_sensitive(tmp_path) -> None:
    assert IDENTITY.artifact_key() == IDENTITY.artifact_key()
    assert IDENTITY.artifact_key() != _identity_changed(source_content_hash="c" * 64).artifact_key()
    assert IDENTITY.artifact_key() != _identity_changed(document_revision="rev-2").artifact_key()
    assert IDENTITY.artifact_key() != _identity_changed(source_set_revision="ssr-2").artifact_key()
    profile = IDENTITY.renderer.model_copy(update={"template_version": "restrained-filing-v2"})
    assert IDENTITY.artifact_key() != IDENTITY.model_copy(update={"renderer": profile}).artifact_key()
    assert IDENTITY.representation_id().startswith("derived_pdf:")


def test_official_and_derived_page_semantics_are_distinct() -> None:
    official = official_pdf_manifest(
        document_id="AAPL:0001",
        source_document_id="AAPL:official-pdf",
        source_set_revision="ssr-1",
        document_revision="rev-1",
        source_content_hash="a" * 64,
        artifact_key="official-key",
        artifact_hash="b" * 64,
        artifact_size_bytes=123,
        page_count=4,
    )
    assert official.representation_type == "OFFICIAL_PDF"
    assert official.page_semantics == "official_pdf_pages"
    assert official.generated_at is None


def test_store_rejects_unbound_artifact_and_path_keys(tmp_path) -> None:
    store = PdfStore(tmp_path)
    with pytest.raises(ValueError):
        store.artifact_dir("../outside")
    manifest = PdfRepresentationManifest(
        representation_id=IDENTITY.representation_id(),
        artifact_status="available", document_id="AAPL:0001", source_document_id="AAPL:primary",
        source_set_revision="ssr-1", document_revision="rev-1", source_content_hash="b" * 64,
        artifact_key=IDENTITY.artifact_key(), artifact_hash="0" * 64,
    )
    mapping = PdfMappingManifest(
        representation_id=IDENTITY.representation_id(), document_id="AAPL:0001", source_document_id="AAPL:primary",
        source_content_hash="b" * 64, artifact_key=IDENTITY.artifact_key(), artifact_hash="0" * 64,
        source_set_revision="ssr-1", document_revision="rev-1",
    )
    with pytest.raises(ValueError):
        store.promote(IDENTITY.artifact_key(), TEST_ARTIFACT, manifest, mapping)


def test_store_promote_roundtrip_is_atomic(tmp_path) -> None:
    store = PdfStore(tmp_path)
    manifest = PdfRepresentationManifest(
        representation_id=IDENTITY.representation_id(),
        artifact_status="available", document_id="AAPL:0001", source_document_id="AAPL:primary",
        source_set_revision="ssr-1", document_revision="rev-1", source_content_hash="b" * 64,
        artifact_key=IDENTITY.artifact_key(), artifact_hash=TEST_ARTIFACT_HASH, page_count=2,
    )
    mapping = PdfMappingManifest(
        representation_id=IDENTITY.representation_id(), document_id="AAPL:0001", source_document_id="AAPL:primary",
        source_content_hash="b" * 64,
        artifact_key=IDENTITY.artifact_key(), artifact_hash=TEST_ARTIFACT_HASH,
        source_set_revision="ssr-1", document_revision="rev-1", entries=[],
    )
    store.promote(IDENTITY.artifact_key(), TEST_ARTIFACT, manifest, mapping)
    loaded = store.load_manifest(IDENTITY.artifact_key())
    assert loaded is not None and loaded.page_count == 2
    loaded_mapping = store.load_mapping(IDENTITY.artifact_key())
    assert loaded_mapping is not None and loaded_mapping.artifact_hash == TEST_ARTIFACT_HASH
    assert store.artifact_path(IDENTITY.artifact_key()).read_bytes().startswith(b"%PDF-")


def test_status_lifecycle_supported_available_stale_failed(tmp_path) -> None:
    store = PdfStore(tmp_path)
    status, manifest, _ = store.status_for(IDENTITY, pdf_supported=True)
    assert status == "supported" and manifest is None

    manifest = PdfRepresentationManifest(
        representation_id=IDENTITY.representation_id(),
        artifact_status="available", document_id="AAPL:0001", source_document_id="AAPL:primary",
        source_set_revision="ssr-1", document_revision="rev-1", source_content_hash="b" * 64,
        artifact_key=IDENTITY.artifact_key(), artifact_hash=TEST_ARTIFACT_HASH,
    )
    mapping = PdfMappingManifest(
        representation_id=IDENTITY.representation_id(), document_id="AAPL:0001", source_document_id="AAPL:primary",
        source_content_hash="b" * 64, artifact_key=IDENTITY.artifact_key(), artifact_hash=TEST_ARTIFACT_HASH,
        source_set_revision="ssr-1", document_revision="rev-1",
    )
    store.promote(IDENTITY.artifact_key(), TEST_ARTIFACT, manifest, mapping)
    status, manifest, _ = store.status_for(IDENTITY, pdf_supported=True)
    assert status == "available" and manifest is not None

    stale_identity = _identity_changed(document_revision="rev-2")
    status, _, reason = store.status_for(stale_identity, pdf_supported=True)
    assert status == "supported"

    # A stored manifest for the NEW identity is stale when its bindings differ.
    stale_manifest = manifest.model_copy(update={"document_revision": "rev-1"})
    stale_bytes = b"%PDF-1.4 stale"
    stale_manifest = stale_manifest.model_copy(update={"representation_id": stale_identity.representation_id(), "artifact_key": stale_identity.artifact_key(), "artifact_hash": hashlib.sha256(stale_bytes).hexdigest()})
    stale_mapping = mapping.model_copy(update={"representation_id": stale_identity.representation_id(), "artifact_key": stale_identity.artifact_key(), "artifact_hash": hashlib.sha256(stale_bytes).hexdigest()})
    store.promote(stale_identity.artifact_key(), stale_bytes, stale_manifest, stale_mapping)
    status, _, reason = store.status_for(stale_identity, pdf_supported=True)
    assert status == "stale" and "different source revision" in (reason or "")

    assert store.status_for(IDENTITY, pdf_supported=False)[0] == "unsupported"

    store.record_failure("stable-1", "renderer crashed")
    assert (store.load_failure("stable-1") or {}).get("artifact_status") == "failed"
    store.clear_failure("stable-1")
    assert store.load_failure("stable-1") is None


# --- PDF-02: generator ---------------------------------------------------------


def test_split_blocks_is_deterministic_with_headings() -> None:
    first = split_blocks(SAMPLE_TEXT)
    second = split_blocks(SAMPLE_TEXT)
    assert [b["block_id"] for b in first] == [b["block_id"] for b in second]
    assert first[0]["block_kind"] == "heading"
    assert first[2]["block_kind"] == "paragraph"
    assert first[-1]["char_end"] <= len(SAMPLE_TEXT)


def test_generate_produces_valid_pdf_with_exact_mapping(tmp_path) -> None:
    store = PdfStore(tmp_path)
    source = _make_source()
    manifest, mapping, pdf_bytes = generate_derived_pdf(
        {"ticker": "AAPL"},
        document_id="AAPL:0001",
        source=source,
        source_set_revision="ssr-1",
        timeout_seconds=30,
        store=store,
    )
    assert pdf_bytes.startswith(b"%PDF-") and b"%%EOF" in pdf_bytes[-1024:]
    assert manifest.representation_type == "DERIVED_PDF"
    assert manifest.artifact_status == "available"
    assert manifest.page_count >= 1
    assert manifest.artifact_hash and len(manifest.artifact_hash) == 64
    assert manifest.source_content_hash == hashlib.sha256(source.normalized_text.encode("utf-8")).hexdigest()
    assert manifest.mapping_status == "exact"
    assert all(entry.rects for entry in mapping.entries)
    assert mapping.artifact_hash == manifest.artifact_hash
    # The mapping is bound to the same artifact identity.
    assert mapping.artifact_key == manifest.artifact_key


def test_generate_multi_page_document_yields_multi_page_rects(tmp_path) -> None:
    source = _make_source(text=(SAMPLE_TEXT + LONG_PARAGRAPH) * 2)
    _, mapping, pdf_bytes = generate_derived_pdf(
        {"ticker": "AAPL"},
        document_id="AAPL:0001",
        source=source,
        source_set_revision="ssr-1",
        timeout_seconds=60,
    )
    assert pdf_bytes.startswith(b"%PDF-")
    pages = {rect.page for entry in mapping.entries for rect in entry.rects}
    assert max(pages) >= 2, "a long document must span multiple generated pages"


def test_generate_preserves_source_layout_table_text_and_mapping(tmp_path) -> None:
    source = _make_source(text=SOURCE_LAYOUT_TABLE)
    manifest, mapping, pdf_bytes = generate_derived_pdf(
        {"ticker": "AAPL"},
        document_id="AAPL:0001",
        source=source,
        source_set_revision="ssr-1",
        timeout_seconds=30,
        store=PdfStore(tmp_path),
    )
    assert manifest.mapping_status == "exact"
    table_entries = [entry for entry in mapping.entries if entry.block_kind == "table"]
    table_text = " ".join(entry.text_preview for entry in table_entries)
    assert table_entries and "Revenue" in table_text and "2025" in table_text
    assert pdf_bytes.startswith(b"%PDF-")


def test_generation_rejects_render_timeout_before_publish(monkeypatch, tmp_path) -> None:
    original_render = pdf_generator_module.render_pdf

    def slow_render(*args: Any, **kwargs: Any):
        import time
        time.sleep(0.03)
        return original_render(*args, **kwargs)

    monkeypatch.setattr(pdf_generator_module, "render_pdf", slow_render)
    with pytest.raises(Exception) as caught:
        generate_derived_pdf(
            {"ticker": "AAPL"},
            document_id="AAPL:0001",
            source=_make_source(text=SAMPLE_TEXT),
            source_set_revision="ssr-1",
            timeout_seconds=0.001,
            store=PdfStore(tmp_path),
        )
    assert getattr(caught.value, "code", None) == "render_timeout"
    assert not list(tmp_path.glob("**/artifact.pdf"))


def test_invalid_renderer_output_is_not_publishable(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(pdf_generator_module, "render_pdf", lambda *args, **kwargs: (b"not-a-pdf", 1, object()))
    with pytest.raises(Exception) as caught:
        generate_derived_pdf(
            {"ticker": "AAPL"},
            document_id="AAPL:0001",
            source=_make_source(text=SAMPLE_TEXT),
            source_set_revision="ssr-1",
            timeout_seconds=30,
            store=PdfStore(tmp_path),
        )
    assert getattr(caught.value, "code", None) == "artifact_invalid"
    assert not list(tmp_path.glob("**/artifact.pdf"))


def test_generation_single_flight_blocks_duplicate_jobs(tmp_path) -> None:
    from src.api.pdf_generator import _single_flight

    lock = _single_flight("k-1")
    assert lock is _single_flight("k-1")
    with lock:
        acquired = lock.acquire(timeout=0.05)
        assert acquired is False


# --- Route contracts -----------------------------------------------------------


@pytest.fixture()
def pdf_client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "pdf_artifacts_dir", tmp_path)
    monkeypatch.setattr(settings, "pdf_generation_enabled", True)
    monkeypatch.setattr(app_module, "_find_document_row", lambda document_id: {"document_id": "AAPL:0001", "ticker": "AAPL"} if document_id == "AAPL:0001" else None)
    monkeypatch.setattr(app_module.original_viewer, "snapshot", lambda row: FakeSnapshot(sources=(_make_source(),)))
    previous_pipeline = app_module._state.get("pipeline")
    app_module._state["pipeline"] = object()
    client = TestClient(app_module.app)
    try:
        yield client, tmp_path
    finally:
        if previous_pipeline is None:
            app_module._state.pop("pipeline", None)
        else:
            app_module._state["pipeline"] = previous_pipeline


def test_pdf_route_lifecycle_supported_generate_content_stale(pdf_client, monkeypatch) -> None:
    client, tmp_path = pdf_client

    supported = client.get("/documents/AAPL:0001/pdf")
    assert supported.status_code == 200
    assert supported.json()["artifact_status"] == "supported"

    unknown = client.get("/documents/AAPL:MISSING/pdf")
    assert unknown.status_code == 404

    generated = client.post("/documents/AAPL:0001/pdf")
    assert generated.status_code == 200, generated.text
    body = generated.json()
    assert body["artifact_status"] == "available"
    assert body["representation_type"] == "DERIVED_PDF"
    assert body["page_count"] >= 1

    status = client.get("/documents/AAPL:0001/pdf").json()
    assert status["artifact_status"] == "available"
    assert status["artifact_hash"] == body["artifact_hash"]
    assert status["page_count"] == body["page_count"]

    content = client.get("/documents/AAPL:0001/pdf/content")
    assert content.status_code == 200
    assert content.headers["content-type"].startswith("application/pdf")
    assert content.content.startswith(b"%PDF-")
    assert content.headers["X-Artifact-Key"] == body["artifact_key"]
    assert "generated.pdf" in content.headers["content-disposition"]

    # A different source revision must never be served the old bytes.
    monkeypatch.setattr(app_module.original_viewer, "snapshot", lambda row: FakeSnapshot(sources=(_make_source(revision="rev-2", sha="e" * 64),)))
    stale = client.get("/documents/AAPL:0001/pdf").json()
    assert stale["artifact_status"] == "stale"
    stale_content = client.get("/documents/AAPL:0001/pdf/content")
    assert stale_content.status_code == 409
    assert stale_content.json()["detail"]["code"] == "pdf_stale"


def test_pdf_generation_accepts_only_document_identity(pdf_client) -> None:
    """A URL/path/HTML body is ignored: generation resolves the source internally."""
    client, _ = pdf_client
    response = client.post(
        "/documents/AAPL:0001/pdf",
        json={"url": "https://evil.example/filing.html", "path": "C:/Windows/system32", "html": "<script>1</script>"},
    )
    assert response.status_code == 200
    assert response.json()["source_document_id"] == "AAPL:primary"
    assert response.json()["representation_type"] == "DERIVED_PDF"


def test_pdf_mapping_and_exact_location_are_bound_to_the_current_artifact(pdf_client, monkeypatch) -> None:
    client, tmp_path = pdf_client
    generated = client.post("/documents/AAPL:0001/pdf").json()
    mapping = client.get("/documents/AAPL:0001/pdf/mapping")
    assert mapping.status_code == 200
    assert mapping.json()["artifact_hash"] == generated["artifact_hash"]
    assert mapping.json()["document_id"] == "AAPL:0001"

    exact_text = "Item 1. Business"
    long_text = LONG_PARAGRAPH
    records = {
        "chunk-exact": [("AAPL:0001", {"text": exact_text, "section": "business"})],
        "chunk-long": [("AAPL:0001", {"text": long_text, "section": "business"})],
        "chunk-partial": [("AAPL:0001", {"text": "Business", "section": "business"})],
    }
    monkeypatch.setattr(app_module, "_chunk_records_index", lambda: records)
    common = {
        "source_document_id": "AAPL:primary",
        "source_set_revision": "ssr-1",
        "document_revision": "rev-1",
    }
    exact = client.get(
        "/documents/AAPL:0001/pdf/mapping/location",
        params={"chunk_id": "chunk-exact", "chunk_text_hash": hashlib.sha256(exact_text.encode()).hexdigest(), **common},
    )
    assert exact.status_code == 200
    assert exact.json()["status"] == "exact"
    assert exact.json()["rects"]

    wrapped = client.get(
        "/documents/AAPL:0001/pdf/mapping/location",
        params={"chunk_id": "chunk-long", "chunk_text_hash": hashlib.sha256(long_text.encode()).hexdigest(), **common},
    )
    assert wrapped.status_code == 200
    assert wrapped.json()["status"] == "exact"
    assert len(wrapped.json()["rects"]) > 1

    partial = client.get(
        "/documents/AAPL:0001/pdf/mapping/location",
        params={"chunk_id": "chunk-partial", "chunk_text_hash": hashlib.sha256(b"Business").hexdigest(), **common},
    )
    assert partial.status_code == 200
    assert partial.json()["status"] == "unavailable"
    assert not partial.json()["rects"]


def test_pdf_mapping_rejects_corrupt_artifact(pdf_client) -> None:
    client, tmp_path = pdf_client
    generated = client.post("/documents/AAPL:0001/pdf").json()
    artifact_dir = tmp_path / generated["artifact_key"]
    (artifact_dir / "artifact.pdf").write_bytes(b"%PDF-1.4 corrupt")
    status = client.get("/documents/AAPL:0001/pdf")
    assert status.status_code == 200
    assert status.json()["artifact_status"] == "failed"
    content = client.get("/documents/AAPL:0001/pdf/content")
    assert content.status_code == 409
    assert content.json()["detail"]["code"] == "pdf_stale"
    corrupt = client.get("/documents/AAPL:0001/pdf/mapping")
    assert corrupt.status_code == 409
    assert corrupt.json()["detail"]["code"] == "pdf_mapping_stale"

def test_pdf_mapping_rejects_missing_sidecar(pdf_client) -> None:
    client, tmp_path = pdf_client
    generated = client.post("/documents/AAPL:0001/pdf").json()
    artifact_dir = tmp_path / generated["artifact_key"]
    (artifact_dir / "mapping.json").unlink()
    missing = client.get("/documents/AAPL:0001/pdf/mapping")
    assert missing.status_code == 409
    assert missing.json()["detail"]["code"] == "pdf_mapping_missing"


def test_pdf_generation_disabled_reports_unsupported(pdf_client, monkeypatch) -> None:
    client, _ = pdf_client
    monkeypatch.setattr(settings, "pdf_generation_enabled", False)
    status = client.get("/documents/AAPL:0001/pdf")
    assert status.json()["artifact_status"] == "unsupported"
    blocked = client.post("/documents/AAPL:0001/pdf")
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "pdf_unsupported"


def test_route_revalidates_source_before_promotion(pdf_client, monkeypatch) -> None:
    client, tmp_path = pdf_client
    snapshots = iter(
        [
            FakeSnapshot(sources=(_make_source(revision="rev-1", sha="a" * 64),)),
            FakeSnapshot(sources=(_make_source(revision="rev-1", sha="a" * 64),)),
            FakeSnapshot(sources=(_make_source(revision="rev-2", sha="e" * 64),)),
        ]
    )
    monkeypatch.setattr(app_module.original_viewer, "snapshot", lambda row: next(snapshots))
    response = client.post("/documents/AAPL:0001/pdf")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "source_changed"
    assert not list(tmp_path.glob("**/artifact.pdf"))


def test_route_failure_publishes_no_pdf_and_exposes_failed_state(pdf_client, monkeypatch) -> None:
    client, tmp_path = pdf_client
    monkeypatch.setattr(pdf_generator_module, "render_pdf", lambda *args, **kwargs: (b"not-a-pdf", 1, object()))
    response = client.post("/documents/AAPL:0001/pdf")
    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "artifact_invalid"
    assert not list(tmp_path.glob("**/artifact.pdf"))
    status = client.get("/documents/AAPL:0001/pdf")
    assert status.status_code == 200
    assert status.json()["artifact_status"] == "failed"


def test_reader_manifest_pdf_entry_follows_supplied_availability() -> None:
    from src.api.document_sources import build_reader_manifest

    class StubSnapshot:
        document_id = "AAPL:0001"
        status = "available"
        reason = None
        source_set_revision = "ssr-1"
        sources: tuple[Any, ...] = ()

    class StubViewer:
        def snapshot(self, row: dict[str, Any]) -> StubSnapshot:
            return StubSnapshot()

    manifest = build_reader_manifest({"document_id": "AAPL:0001", "ticker": "AAPL"}, viewer=StubViewer())
    pdf_entry = next(item for item in manifest["representations"] if item["kind"] == "pdf")
    assert pdf_entry["status"] == "unavailable"

    provided = build_reader_manifest(
        {"document_id": "AAPL:0001", "ticker": "AAPL"},
        viewer=StubViewer(),
        pdf_availability={"status": "available", "reason_code": "available", "reason": "A derived PDF artifact is available."},
    )
    pdf_entry = next(item for item in provided["representations"] if item["kind"] == "pdf")
    assert pdf_entry["status"] == "available"
