from __future__ import annotations

import hashlib
import json
from pathlib import Path

from configs.settings import settings
from src.api.original_viewer import OriginalViewer
from src.api.structured_document import StructuredDocumentService
from src.api.structured_location import StructuredLocationService


ACCESSION = "0000051143-26-000010"
ROW = {"document_id": f"IBM:{ACCESSION}", "ticker": "IBM", "filing_date": "2026-02-04", "accession_number": ACCESSION}


def _fixture(tmp_path: Path, monkeypatch, body: str) -> tuple[OriginalViewer, StructuredLocationService]:
    raw_root = tmp_path / "raw" / "IBM"
    processed_root = tmp_path / "processed" / "IBM"
    raw_root.mkdir(parents=True)
    processed_root.mkdir(parents=True)
    (raw_root / f"{ACCESSION.replace('-', '')}.html").write_text(body, encoding="utf-8")
    (processed_root / f"{ACCESSION.replace('-', '')}_sections.json").write_text(json.dumps({"ticker": "IBM", "cik": 51143, "accession_number": ACCESSION, "sections": {}}), encoding="utf-8")
    monkeypatch.setattr(settings, "data_raw_dir", tmp_path / "raw")
    monkeypatch.setattr(settings, "data_processed_dir", tmp_path / "processed")
    viewer = OriginalViewer()
    return viewer, StructuredLocationService(viewer, StructuredDocumentService(viewer))


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_unique_paragraph_returns_revision_bound_structured_range(tmp_path: Path, monkeypatch) -> None:
    viewer, service = _fixture(tmp_path, monkeypatch, "<html><body><h1>Risk factors</h1><p>Revenue grew in the latest period.</p></body></html>")
    manifest = viewer.manifest(ROW)
    text = "Revenue grew in the latest period."
    result = service.locate(ROW, "chunk-1", text, _hash(text), manifest["source_set_revision"], "risk_factors")

    assert result.status == "exact"
    assert result.source_document_id
    assert result.document_revision
    assert result.representation_revision
    assert len(result.ranges) == 1
    assert result.ranges[0].method == "text_whitespace"


def test_duplicate_paragraph_is_ambiguous_and_has_no_ranges(tmp_path: Path, monkeypatch) -> None:
    viewer, service = _fixture(tmp_path, monkeypatch, "<html><body><p>Repeated disclosure.</p><p>Repeated disclosure.</p></body></html>")
    manifest = viewer.manifest(ROW)
    text = "Repeated disclosure."
    result = service.locate(ROW, "chunk-1", text, _hash(text), manifest["source_set_revision"], "risk_factors")

    assert result.status == "ambiguous"
    assert result.match_count == 2
    assert result.match_count_capped is True
    assert result.ranges == []


def test_wrong_hash_is_stale_and_incomplete_source_set_is_unavailable(tmp_path: Path, monkeypatch) -> None:
    viewer, service = _fixture(tmp_path, monkeypatch, "<html><body><p>Primary disclosure.</p><a href='annual.htm'>Annual Report to Stockholders</a></body></html>")
    manifest = viewer.manifest(ROW)
    text = "Primary disclosure."
    stale = service.locate(ROW, "chunk-1", text, _hash("changed"), manifest["source_set_revision"], "risk_factors")
    unavailable = service.locate(ROW, "chunk-1", text, _hash(text), manifest["source_set_revision"], "risk_factors")

    assert stale.status == "stale"
    assert stale.ranges == []
    assert unavailable.status == "unavailable"
    assert unavailable.ranges == []


def test_table_correspondence_is_semantic_and_numeric_only_is_not_proof(tmp_path: Path, monkeypatch) -> None:
    viewer, service = _fixture(tmp_path, monkeypatch, "<html><body><table><caption>Revenue</caption><tr><th>Metric</th><th>2024</th><th>2025</th></tr><tr><td>Total sales</td><td>90</td><td>100</td></tr></table></body></html>")
    manifest = viewer.manifest(ROW)
    table = "### Revenue\n| Metric | 2024 | 2025 |\n| --- | --- | --- |\n| Total sales | 90 | 100 |"
    exact = service.locate(ROW, "chunk-table", table, _hash(table), manifest["source_set_revision"], "financial_table")
    numeric = "100"
    not_proven = service.locate(ROW, "chunk-number", numeric, _hash(numeric), manifest["source_set_revision"], "financial_table")

    assert exact.status == "exact"
    assert exact.ranges[0].method == "table_semantic"
    assert not_proven.status == "not_found"
