from __future__ import annotations

import json
from pathlib import Path

import pytest

from configs.settings import settings
from src.api.original_viewer import OriginalViewer, OriginalViewerError
from src.api.structured_document import StructuredDocumentError, StructuredDocumentService, parse_structured_document


ACCESSION = "0000051143-26-000010"
ROW = {"document_id": f"IBM:{ACCESSION}", "ticker": "IBM", "filing_date": "2026-02-04", "accession_number": ACCESSION}


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
    assert content["blocks"][0]["kind"] == "heading"
    assert b"<script" not in payload
    assert b"&lt;b&gt;safe&lt;/b&gt;" in payload
    assert media_type.startswith("text/html")
    with pytest.raises(OriginalViewerError, match="source set changed"):
        service.content(ROW, source["source_document_id"], "stale", source["document_revision"], 0, 64)


def test_parser_rejects_depth_over_limit() -> None:
    raw = ("<html><body>" + ("<div>" * 130) + "text" + ("</div>" * 130) + "</body></html>").encode()
    with pytest.raises(StructuredDocumentError, match="nesting"):
        parse_structured_document(raw, "doc", "source", "set", "revision")
