"""Read-only audit for IBM's incorporated Annual Report to Stockholders."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from configs.settings import settings
from src.ingestion.chunker import build_table_chunks
from src.ingestion.table_extractor import extract_table_rows

DEFAULT_OUTPUT = Path("data/diagnostics/ibm_companion_document_audit.json")
SCHEMA_VERSION = 2
_INCORPORATION = re.compile(
    r"item\s+8\b.{0,700}?pages?\s+(\d+)\s+(?:through|to|-)\s+(\d+)"
    r".{0,240}?annual report to (?:stockholders|security holders)", re.I | re.S
)
_COMPANION_LABEL = re.compile(r"annual report to (?:stockholders|security holders)", re.I)
_CONTAMINATION = re.compile(r"\b(?:item\s+9|part\s+(?:iii|iv)|signatures?)\b", re.I)
_STATEMENT_LABELS = {
    "income": re.compile(r"statements? of (?:income|operations|earnings)|net income|net revenue", re.I),
    "balance_sheet": re.compile(r"balance sheets?|total assets|total liabilities", re.I),
    "cash_flow": re.compile(r"cash flows?|net cash (?:provided|used)", re.I),
}


def _sha256(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _input_digest(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(set(paths), key=lambda item: str(item)):
        digest.update(str(path).encode("utf-8"))
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return f"sha256:{digest.hexdigest()}"


def _normalize(value: str) -> str:
    return " ".join(value.split())


def _find_paths(processed_dir: Path, raw_dir: Path) -> tuple[Path, Path, Path]:
    sections = sorted(processed_dir.glob("IBM/*_sections.json"))
    if len(sections) != 1:
        raise FileNotFoundError(f"expected one IBM sections file, found {len(sections)}")
    sections_path = sections[0]
    accession = sections_path.stem.removesuffix("_sections")
    html_path = raw_dir / "IBM" / f"{accession}.html"
    chunks_path = sections_path.with_name(f"{accession}_chunks.jsonl")
    if not all(path.is_file() for path in (html_path, chunks_path)):
        raise FileNotFoundError("IBM raw HTML, sections, or chunks file is missing")
    return html_path, sections_path, chunks_path


def _incorporation_evidence(soup: BeautifulSoup) -> dict[str, Any]:
    text = _normalize(soup.get_text(" ", strip=True))
    matches = list(_INCORPORATION.finditer(text))
    return {
        "matches": len(matches),
        "item8_matches": len(matches),
        "page_range": ({"start": int(matches[0].group(1)), "end": int(matches[0].group(2))} if matches else None),
        "excerpts": [text[max(0, match.start() - 120):match.end() + 120] for match in matches[:4]],
    }


def _candidates(soup: BeautifulSoup, filing_dir: Path) -> list[dict[str, Any]]:
    found: dict[tuple[str, str], dict[str, Any]] = {}
    for link in soup.find_all("a", href=True):
        label = _normalize(link.get_text(" ", strip=True))
        href = str(link["href"]).strip()
        if not _COMPANION_LABEL.search(label):
            continue
        parsed = urlparse(href)
        local = None if parsed.scheme or parsed.netloc else (filing_dir / parsed.path).resolve()
        key = (href, str(local) if local else "")
        exists = bool(local and local.is_file())
        found[key] = {
            "label": label[:240], "href": href[:400],
            "provenance": "relative_filing_link" if local else "external_link",
            "local_path": str(local) if local else None, "exists": exists,
            "sha256": _sha256(local.read_bytes()) if exists and local else None,
            "decision": "eligible_candidate" if exists else "missing_local_document",
        }
    return sorted(found.values(), key=lambda item: (item["href"], item["label"]))


def _page_markers(soup: BeautifulSoup) -> list[tuple[int, int]]:
    """Find explicit page markers without treating arbitrary visible numbers as pages."""
    positions = {id(node): index for index, node in enumerate(soup.descendants)}
    markers: list[tuple[int, int]] = []
    for node in soup.find_all(True):
        for raw in (node.get("data-page"), node.get("data-page-number"), node.get("id"), node.get("name")):
            match = re.fullmatch(r"(?:page[_-]?)?(\d+)", str(raw or ""), re.I)
            if match:
                markers.append((int(match.group(1)), positions.get(id(node), -1)))
                break
    for link in soup.find_all("a", href=True):
        label = _normalize(link.get_text(" ", strip=True))
        match = re.fullmatch(r"(\d{1,3})", label)
        href = str(link["href"])
        if not match or not href.startswith("#") or len(href) == 1:
            continue
        target = soup.find(id=href[1:]) or soup.find(attrs={"name": href[1:]})
        if isinstance(target, Tag):
            markers.append((int(match.group(1)), positions.get(id(target), -1)))
    return sorted(set(markers), key=lambda item: (item[1], item[0]))


def _resolve_page_interval(soup: BeautifulSoup, page_range: dict[str, int] | None) -> tuple[int, int] | None:
    if not page_range:
        return None
    markers = _page_markers(soup)
    starts = [position for page, position in markers if page == page_range["start"]]
    start = starts[0] if starts else -1
    ends = [position for page, position in markers if page == page_range["end"] and position > start]
    return (start, ends[0]) if start >= 0 and ends else None


def _statement_evidence(path: Path, page_range: dict[str, int] | None, filing_data: dict[str, Any] | None = None) -> dict[str, Any]:
    soup = BeautifulSoup(path.read_bytes(), "lxml")
    positions = {id(node): index for index, node in enumerate(soup.descendants)}
    interval = _resolve_page_interval(soup, page_range)
    tables: list[dict[str, Any]] = []
    fingerprints: set[str] = set()
    categories: set[str] = set()
    years: set[str] = set()
    contamination: set[str] = set()
    selected_tags: list[Tag] = []
    for index, table in enumerate(soup.find_all("table")):
        position = positions.get(id(table), -1)
        if interval is None or not interval[0] < position < interval[1]:
            continue
        rows = extract_table_rows(table)
        labels = [row.label for row in rows]
        matched = [name for name, pattern in _STATEMENT_LABELS.items() if pattern.search(" | ".join(labels))]
        if not labels or not matched:
            continue
        fingerprint = _sha256(_normalize(table.get_text(" ", strip=True)).encode("utf-8"))
        fingerprints.add(fingerprint); categories.update(matched)
        years.update(year for row in rows for year in row.values_by_year)
        selected_tags.append(table)
        tables.append({"table_index": index, "fingerprint": fingerprint, "row_labels": labels[:20], "categories": matched})
    if interval is not None:
        nodes = list(soup.descendants)
        interval_text = _normalize(" ".join(node.get_text(" ", strip=True) if isinstance(node, Tag) else str(node) for node in nodes[interval[0]:interval[1] + 1]))
        contamination.update(match.group(0).lower() for match in _CONTAMINATION.finditer(interval_text))
    trial_chunks = build_table_chunks(path, selected_tags, filing_data) if selected_tags and filing_data else []
    chunk_ids = [chunk.chunk_id for chunk in trial_chunks]
    return {
        "table_count": len(tables), "unique_fingerprints": len(fingerprints), "tables": tables,
        "trial_chunk_ids": chunk_ids, "unique_chunk_ids": len(set(chunk_ids)),
        "statement_categories": sorted(categories), "fiscal_years": sorted(years),
        "contamination_markers": sorted(contamination), "page_range_requested": page_range,
        "page_interval_positions": {"start": interval[0], "end": interval[1]} if interval else None,
        "page_range_resolved": interval is not None,
    }


def _gate_state(value: bool | None) -> str:
    return "pass" if value is True else "fail" if value is False else "not_evaluated"


def audit_companion(html_path: Path, sections_path: Path, chunks_path: Path) -> dict[str, Any]:
    filing = json.loads(sections_path.read_text(encoding="utf-8"))
    soup = BeautifulSoup(html_path.read_bytes(), "lxml")
    incorporation = _incorporation_evidence(soup)
    candidates = _candidates(soup, html_path.parent)
    selected = [candidate for candidate in candidates if candidate["exists"]]
    companion = selected[0] if len(selected) == 1 else None
    evidence = _statement_evidence(Path(companion["local_path"]), incorporation["page_range"], filing) if companion else None
    content = {
        "unique_companion": len(selected) == 1,
        "provenance_linked": len(selected) == 1 and selected[0]["provenance"] == "relative_filing_link",
        "statement_range_resolved": evidence["page_range_resolved"] if evidence else None,
        "required_statements": all(name in evidence["statement_categories"] for name in _STATEMENT_LABELS) if evidence else None,
        "fiscal_years_complete": all(year in evidence["fiscal_years"] for year in ("2023", "2024", "2025")) if evidence else None,
        "no_duplicate_tables": evidence["table_count"] == evidence["unique_fingerprints"] if evidence else None,
        "no_duplicate_chunks": evidence["unique_chunk_ids"] == len(evidence["trial_chunk_ids"]) if evidence else None,
        "no_contamination": not evidence["contamination_markers"] if evidence else None,
        "input_hashes_unchanged": None,
        "reports_byte_identical": None,
    }
    gates = {name: _gate_state(value) for name, value in content.items()}
    status = "companion_missing" if not selected else "ambiguous_companion" if len(selected) > 1 else "candidate_requires_validation"
    return {"schema_version": SCHEMA_VERSION, "read_only": True, "ticker": filing.get("ticker"), "accession": filing.get("accession_number"), "filing_document": html_path.name, "incorporation_evidence": incorporation, "companion_candidates": candidates, "selected_companion": companion, "statement_evidence": evidence, "gates": gates, "overall_pass": all(value == "pass" for value in gates.values()), "status": status, "production_ready": False, "next_action": "obtain the uniquely linked companion document and rerun this read-only audit" if status == "companion_missing" else "resolve candidate ambiguity before extraction"}


def _input_paths(html_path: Path, sections_path: Path, chunks_path: Path, candidates: list[dict[str, Any]]) -> list[Path]:
    paths = [html_path, sections_path, chunks_path]
    paths.extend(Path(candidate["local_path"]) for candidate in candidates if candidate["exists"] and candidate["local_path"])
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    html_path, sections_path, chunks_path = _find_paths(settings.data_processed_dir, settings.data_raw_dir)
    preview = audit_companion(html_path, sections_path, chunks_path)
    inputs = _input_paths(html_path, sections_path, chunks_path, preview["companion_candidates"])
    before = _input_digest(inputs)
    first = audit_companion(html_path, sections_path, chunks_path)
    second = audit_companion(html_path, sections_path, chunks_path)
    after = _input_digest(inputs)
    reports_identical = json.dumps(first, sort_keys=True, ensure_ascii=False) == json.dumps(second, sort_keys=True, ensure_ascii=False)
    first["read_inputs_sha256"] = after
    first["read_inputs_immutable"] = before == after
    first["gates"]["input_hashes_unchanged"] = _gate_state(before == after)
    first["gates"]["reports_byte_identical"] = _gate_state(reports_identical)
    first["overall_pass"] = all(value == "pass" for value in first["gates"].values())
    report = {"schema_version": SCHEMA_VERSION, "read_only": True, "result": first}
    report["report_fingerprint"] = _sha256(json.dumps(report, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"IBM: {first['status']} candidates={len(first['companion_candidates'])} overall_pass={first['overall_pass']}")
    return 0 if first["read_inputs_immutable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
