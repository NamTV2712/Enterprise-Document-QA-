from __future__ import annotations

import json
from pathlib import Path

import pytest

from configs.settings import settings
from src.api.original_viewer import OriginalViewer, OriginalViewerError
from src.api.structured_document import StructuredDocumentError, StructuredDocumentService, parse_structured_document


ACCESSION = "0000051143-26-000010"
ROW = {"document_id": f"IBM:{ACCESSION}", "ticker": "IBM", "filing_date": "2026-02-04", "accession_number": ACCESSION}


def test_source_layout_fixture_freezes_aapl_like_physical_grid() -> None:
    """V4-P00.1 baseline: preserve the source facts before semantic adaptation."""
    from bs4 import BeautifulSoup

    fixture = Path(__file__).parent / "fixtures" / "reader_table_source_layout.html"
    soup = BeautifulSoup(fixture.read_bytes(), "lxml")
    rows = soup.find_all("tr")
    cells = [[cell for cell in row.find_all(["th", "td"], recursive=False)] for row in rows]

    assert len(cells) == 7
    assert len(cells[0]) == 12
    assert all(cell.get_text(strip=True) == "" for cell in cells[0])
    assert [cell.get("colspan") for cell in cells[1]] == ["3", "3", "3", "3"]
    assert cells[3][1].get_text(strip=True) == "$"
    assert cells[3][2].get_text(strip=True) == "100"
    assert cells[5][0].get("rowspan") == "2"


def test_source_layout_fixture_classifies_physical_cells_without_fake_headers() -> None:
    """V4-P01.1 closes the baseline without changing source cell order."""
    fixture = Path(__file__).parent / "fixtures" / "reader_table_source_layout.html"
    document = parse_structured_document(fixture.read_bytes(), "AAPL:fixture", "source-fixture", "set-1", "revision-1")
    table = next(block for block in document.blocks if block.kind == "table")

    assert table.table_mode == "source_layout"
    assert table.header_rows == []
    assert table.table_adapter_version == "sec-table-adapter-v2"
    assert len(table.rows[0]) == 12
    assert table.rows[3][1].text == "$"
    assert table.rows[3][2].text == "100"
    assert table.rows[5][0].rowspan == 2


def test_table_adapter_marks_explicit_multilevel_headers_semantic() -> None:
    raw = b"""
    <table><caption>Revenue</caption>
      <tr><th rowspan='2'>Metric</th><th colspan='2'>Year ended</th></tr>
      <tr><th>2025</th><th>2024</th></tr>
      <tr><th scope='row'>Total revenue</th><td>416,161</td><td>391,035</td></tr>
    </table>
    """
    table = next(block for block in parse_structured_document(raw, "doc", "source", "set", "rev").blocks if block.kind == "table")

    assert table.table_mode == "semantic"
    assert table.header_row_count == 2
    assert len(table.header_rows) == 2
    assert table.header_rows[0][1].colspan == 2
    assert table.rows[2][0].header is True
    assert table.rows[2][0].cell_id


def test_table_adapter_marks_invalid_span_unsupported_without_dropping_raw_text() -> None:
    raw = b"<table><tr><td colspan='wat'>Metric</td><td>100</td></tr></table>"
    table = next(block for block in parse_structured_document(raw, "doc", "source", "set", "rev").blocks if block.kind == "table")

    assert table.table_mode == "unsupported"
    assert table.table_reason and "malformed" in table.table_reason
    assert [cell.text for cell in table.rows[0]] == ["Metric", "100"]


def test_parser_returns_application_owned_blocks_without_active_markup() -> None:
    raw = b"""
    <html><head><script>alert('x')</script><style>hide</style></head><body>
      <h1>Risk factors</h1><p>Revenue <strong>$100</strong> million.</p>
      <ul><li>Competition</li><li>Supply chain</li></ul>
      <table><caption>Revenue</caption><tr><th>Metric</th><th>2025</th></tr><tr><td>Total sales</td><td>100</td></tr></table>
      <img src="https://evil.test/tracker" /><iframe src="https://evil.test"></iframe>
    </body></html>
    """

    document = parse_structured_document(raw, "IBM:doc", "source-1", "set-1", "revision-1")

    assert [block.kind for block in document.blocks] == ["heading", "paragraph", "list", "list", "table", "unsupported", "unsupported"]
    assert document.outline[0].label == "Risk factors"
    assert document.blocks[1].runs[1].strong is True
    assert document.blocks[4].rows[1][1].text == "100"
    assert all("script" not in block.text.casefold() for block in document.blocks)


def test_service_is_revision_bound_and_exports_escaped_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw_root = tmp_path / "raw" / "IBM"
    processed_root = tmp_path / "processed" / "IBM"
    raw_root.mkdir(parents=True)
    processed_root.mkdir(parents=True)
    (raw_root / f"{ACCESSION.replace('-', '')}.html").write_text("<html><body><h1>Heading</h1><p>A &lt;b&gt;safe&lt;/b&gt; value.</p></body></html>", encoding="utf-8")
    (processed_root / f"{ACCESSION.replace('-', '')}_sections.json").write_text(json.dumps({"ticker": "IBM", "cik": 51143, "accession_number": ACCESSION, "sections": {}}), encoding="utf-8")
    monkeypatch.setattr(settings, "data_raw_dir", tmp_path / "raw")
    monkeypatch.setattr(settings, "data_processed_dir", tmp_path / "processed")
    viewer = OriginalViewer()
    service = StructuredDocumentService(viewer)
    manifest = viewer.manifest(ROW)
    source = manifest["sources"][0]

    content = service.content(ROW, source["source_document_id"], manifest["source_set_revision"], source["document_revision"], 0, 64)
    payload, media_type = service.export(ROW, source["source_document_id"], manifest["source_set_revision"], source["document_revision"], "html")

    assert content["complete"] is True
    assert content["coverage_status"] == "complete"
    assert content["coverage_reason"]
    assert content["blocks"][0]["kind"] == "heading"
    assert b"<script" not in payload
    assert b"&lt;b&gt;safe&lt;/b&gt;" in payload
    assert media_type.startswith("text/html")
    search = service.search(ROW, source["source_document_id"], manifest["source_set_revision"], source["document_revision"], "safe", 0, 50)
    assert search["coverage_status"] == "complete"
    assert search["matches"]
    with pytest.raises(OriginalViewerError, match="source set changed"):
        service.content(ROW, source["source_document_id"], "stale", source["document_revision"], 0, 64)


def test_parser_rejects_depth_over_limit() -> None:
    raw = ("<html><body>" + ("<div>" * 130) + "text" + ("</div>" * 130) + "</body></html>").encode()
    with pytest.raises(StructuredDocumentError, match="nesting"):
        parse_structured_document(raw, "doc", "source", "set", "revision")


def test_structured_representation_reports_visible_content_outside_supported_blocks() -> None:
    raw = b"<html><body><div>Company Background</div><p>Known paragraph.</p></body></html>"

    document = parse_structured_document(raw, "doc", "source", "set", "revision")

    assert document.model_dump()["coverage_status"] == "partial"
    assert document.model_dump()["coverage_reason_code"] == "unsupported_visible_content"
