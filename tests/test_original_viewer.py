from __future__ import annotations

import json
from pathlib import Path

import pytest

from configs.settings import settings
from src.api.original_normalizer import normalize_html
from src.api.original_viewer import OriginalViewer, OriginalViewerError, sec_index_url_for_document
from src.ingestion.table_extractor import extract_table_rows, extract_table_unit, get_table_caption, rows_to_markdown
from bs4 import BeautifulSoup


DOCUMENT_ID = "IBM:0000051143-26-000010"
TICKER = "IBM"
ACCESSION = "0000051143-26-000010"


def _row() -> dict[str, object]:
    return {
        "document_id": DOCUMENT_ID,
        "ticker": TICKER,
        "filing_date": "2026-02-04",
        "accession_number": ACCESSION,
    }


@pytest.fixture
def viewer_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> OriginalViewer:
    raw_root = tmp_path / "raw"
    processed_root = tmp_path / "processed"
    raw_dir = raw_root / TICKER
    processed_dir = processed_root / TICKER
    raw_dir.mkdir(parents=True)
    processed_dir.mkdir(parents=True)
    (raw_dir / "000005114326000010.html").write_text(
        """
        <html><head><style>ignore style</style><script>ignore script</script></head>
        <body><h1>IBM Annual filing</h1><p>Revenue <strong>$100</strong> million.</p>
        <div aria-hidden=\"true\">Assistive content stays in source text.</div>
        <div style=\"display:none\">Hidden content must not appear.</div>
        <a href=\"ibm-20251231_d2.htm#page-1\">Annual Report to Stockholders</a>
        <a href=\"../escape.html\">Annual Report to Stockholders</a>
        <a href=\"https://example.test/report.html\">Annual Report to Stockholders</a>
        </body></html>
        """,
        encoding="utf-8",
    )
    (raw_dir / "ibm-20251231_d2.htm").write_text(
        "<html><body><p>Companion financial statements. Revenue $100 million.</p></body></html>",
        encoding="utf-8",
    )
    (processed_dir / "000005114326000010_sections.json").write_text(
        json.dumps({"ticker": TICKER, "cik": 51143, "accession_number": ACCESSION, "sections": {}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "data_raw_dir", raw_root)
    monkeypatch.setattr(settings, "data_processed_dir", processed_root)
    return OriginalViewer()


def test_normalizer_removes_executable_and_hidden_content_without_aria_guessing() -> None:
    value = normalize_html(
        b"<html><head><script>bad()</script></head><body><p>A<strong>1</strong></p><div aria-hidden='true'>kept</div><div style='visibility:hidden'>gone</div></body></html>"
    )
    assert "bad" not in value
    assert "gone" not in value
    assert "A1" in value
    assert "kept" in value


def test_manifest_is_bounded_and_admits_only_safe_companion_links(viewer_tree: OriginalViewer) -> None:
    manifest = viewer_tree.manifest(_row())

    assert manifest["status"] == "available"
    assert len(manifest["sources"]) == 2
    assert {source["role"] for source in manifest["sources"]} == {"primary_filing", "annual_report_companion"}
    assert all("path" not in json.dumps(source).lower() for source in manifest["sources"])
    assert manifest["source_set_revision"]


def test_content_and_search_are_revision_bound(viewer_tree: OriginalViewer) -> None:
    manifest = viewer_tree.manifest(_row())
    primary = next(source for source in manifest["sources"] if source["role"] == "primary_filing")
    content = viewer_tree.content(
        _row(), primary["source_document_id"], manifest["source_set_revision"], primary["document_revision"], 0, 16_000, "Revenue"
    )
    assert content["total_length"] > 0
    assert any(segment["search"] for segment in content["segments"])
    assert all("script" not in segment["text"] for segment in content["segments"])

    search = viewer_tree.search(
        _row(), primary["source_document_id"], manifest["source_set_revision"], primary["document_revision"], "Revenue", 0, 20
    )
    assert search["matches"]
    assert search["matches"][0]["start"] < search["matches"][0]["end"]
    with pytest.raises(OriginalViewerError, match="changed"):
        viewer_tree.content(_row(), primary["source_document_id"], "stale", primary["document_revision"], 0, 100)


def test_known_document_without_original_is_explicitly_unavailable(viewer_tree: OriginalViewer) -> None:
    row = {**_row(), "document_id": "IBM:0000051143-26-000011", "accession_number": "0000051143-26-000011"}
    manifest = viewer_tree.manifest(row)
    assert manifest["status"] == "unavailable"
    assert manifest["reason"]


def test_sec_index_url_requires_validated_processed_identity(viewer_tree: OriginalViewer) -> None:
    assert sec_index_url_for_document(_row()) == "https://www.sec.gov/Archives/edgar/data/51143/000005114326000010/0000051143-26-000010-index.html"
    assert sec_index_url_for_document({**_row(), "accession_number": "not-an-accession"}) is None


def test_table_location_requires_a_unique_serializer_match(viewer_tree: OriginalViewer) -> None:
    primary_path = settings.data_raw_dir / TICKER / "000005114326000010.html"
    primary_path.write_text(
        "<html><body><p>Financial statement context</p><p>Revenue table with values</p>"
        "<table><tr><th>Metric</th><th>2025</th><th>2024</th></tr>"
        "<tr><td>Revenue</td><td>100</td><td>90</td></tr></table></body></html>",
        encoding="utf-8",
    )
    soup = BeautifulSoup(primary_path.read_bytes(), "lxml")
    table = soup.find("table")
    assert table is not None
    chunk_text = rows_to_markdown(extract_table_rows(table), get_table_caption(table), extract_table_unit(table))
    import hashlib
    manifest = viewer_tree.manifest(_row())
    result = viewer_tree.table_location(_row(), chunk_text, hashlib.sha256(chunk_text.encode()).hexdigest(), manifest["source_set_revision"])
    assert result["status"] == "exact"
    assert result["location"]["method"] == "table_serialization"
