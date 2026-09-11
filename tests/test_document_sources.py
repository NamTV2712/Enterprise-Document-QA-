from __future__ import annotations

import json
from pathlib import Path

from configs.settings import settings
from src.api.document_sources import build_reader_manifest
from src.api.original_viewer import OriginalViewer


DOCUMENT_ID = "IBM:0000051143-26-000010"
ACCESSION = "0000051143-26-000010"


def _row() -> dict[str, object]:
    return {
        "document_id": DOCUMENT_ID,
        "ticker": "IBM",
        "filing_date": "2026-02-04",
        "report_date": "2025-12-31",
        "accession_number": ACCESSION,
    }


def _viewer_tree(tmp_path: Path, monkeypatch):
    raw_root = tmp_path / "raw"
    processed_root = tmp_path / "processed"
    raw_dir = raw_root / "IBM"
    processed_dir = processed_root / "IBM"
    raw_dir.mkdir(parents=True)
    processed_dir.mkdir(parents=True)
    (raw_dir / "000005114326000010.html").write_text(
        "<html><body><h1>IBM filing</h1><a href='ibm-20251231_d2.htm'>Annual Report to Stockholders</a></body></html>",
        encoding="utf-8",
    )
    (raw_dir / "ibm-20251231_d2.htm").write_text("<html><body>Companion</body></html>", encoding="utf-8")
    (processed_dir / "000005114326000010_sections.json").write_text(
        json.dumps({"ticker": "IBM", "cik": 51143, "accession_number": ACCESSION, "sections": {}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "data_raw_dir", raw_root)
    monkeypatch.setattr(settings, "data_processed_dir", processed_root)
    return OriginalViewer()


def test_reader_manifest_has_verified_identity_and_stable_sources(tmp_path: Path, monkeypatch):
    viewer = _viewer_tree(tmp_path, monkeypatch)
    first = build_reader_manifest(_row(), viewer=viewer)
    second = build_reader_manifest(_row(), viewer=viewer)

    assert first["schema_version"] == "sec-reader-v4"
    assert first["identity"]["status"] == "verified"
    assert first["identity"]["cik"] == 51143
    assert first["source_set_revision"] == second["source_set_revision"]
    assert [item["source_document_id"] for item in first["sources"]] == [item["source_document_id"] for item in second["sources"]]
    assert first["sources"][0]["canonical_url"].endswith("0000051143-26-000010-index.html")
    assert {item["kind"] for item in first["representations"]} == {"normalized_text", "structured", "pdf"}


def test_reader_manifest_does_not_guess_unverified_identity(tmp_path: Path, monkeypatch):
    viewer = _viewer_tree(tmp_path, monkeypatch)
    row = {**_row(), "document_id": "IBM:0000051143-26-000011", "accession_number": "0000051143-26-000011"}
    manifest = build_reader_manifest(row, viewer=viewer)

    assert manifest["identity"]["status"] == "unverified"
    assert manifest["identity"]["cik"] is None
    assert all(item["canonical_url"] is None for item in manifest["sources"])
    assert manifest["reason_code"] == "identity_unverified"


def test_reader_cache_eviction_counts_utf8_bytes(tmp_path: Path, monkeypatch):
    viewer = _viewer_tree(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "viewer_cache_entries", 2)
    monkeypatch.setattr(settings, "viewer_cache_max_bytes", len("é".encode("utf-8")))

    viewer._cache_text("one", "rev", "é")
    viewer._cache_text("two", "rev", "é")

    assert viewer._cache_bytes == len("é".encode("utf-8"))
    assert len(viewer._text_cache) == 1
