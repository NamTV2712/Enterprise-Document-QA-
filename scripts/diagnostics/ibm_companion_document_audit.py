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
from src.ingestion.table_extractor import extract_table_rows

DEFAULT_OUTPUT = Path("data/diagnostics/ibm_companion_document_audit.json")
SCHEMA_VERSION = 1
_INCORPORATION = re.compile(
    r"item\s+8\b.{0,700}?pages?\s+(\d+)\s+(?:through|to|-)\s+(\d+)"
    r".{0,240}?annual report to (?:stockholders|security holders)",
    re.IGNORECASE | re.DOTALL,
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
    selected = matches
    excerpts = [text[max(0, match.start() - 120):match.end() + 120] for match in selected]
    return {
        "matches": len(matches),
        "item8_matches": len(matches),
        "page_range": {"start": int(selected[0].group(1)), "end": int(selected[0].group(2))} if selected else None,
        "excerpts": excerpts[:4],
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
        found[key] = {
            "label": label[:240],
            "href": href[:400],
            "provenance": "relative_filing_link" if local else "external_link",
            "local_path": str(local) if local else None,
            "exists": bool(local and local.is_file()),
            "decision": "eligible_candidate" if local and local.is_file() else "missing_local_document",
        }
    return sorted(found.values(), key=lambda item: (item["href"], item["label"]))


def _statement_evidence(path: Path, page_range: dict[str, int] | None) -> dict[str, Any]:
    soup = BeautifulSoup(path.read_bytes(), "lxml")
    tables = []
    fingerprints: set[str] = set()
    categories: set[str] = set()
    years: set[str] = set()
    contamination: set[str] = set()
    for index, table in enumerate(soup.find_all("table")):
        rows = extract_table_rows(table)
        labels = [row.label for row in rows]
        if not labels:
            continue
        text = _normalize(table.get_text(" ", strip=True))
        matched = [name for name, pattern in _STATEMENT_LABELS.items() if pattern.search(" | ".join(labels))]
        if not matched:
            continue
        fingerprint = _sha256(text.encode("utf-8"))
        fingerprints.add(fingerprint)
        categories.update(matched)
        years.update(year for row in rows for year in row.values_by_year)
        tables.append({"table_index": index, "fingerprint": fingerprint, "row_labels": labels[:20], "categories": matched})
    text = _normalize(soup.get_text(" ", strip=True))
    contamination.update(match.group(0).lower() for match in _CONTAMINATION.finditer(text))
    return {
        "table_count": len(tables),
        "unique_fingerprints": len(fingerprints),
        "tables": tables,
        "statement_categories": sorted(categories),
        "fiscal_years": sorted(years),
        "contamination_markers": sorted(contamination),
        "page_range_requested": page_range,
        "page_range_resolved": False,
    }


def audit_companion(html_path: Path, sections_path: Path, chunks_path: Path) -> dict[str, Any]:
    filing = json.loads(sections_path.read_text(encoding="utf-8"))
    soup = BeautifulSoup(html_path.read_bytes(), "lxml")
    incorporation = _incorporation_evidence(soup)
    candidates = _candidates(soup, html_path.parent)
    selected = [candidate for candidate in candidates if candidate["exists"]]
    gates = {
        "unique_companion": len(selected) == 1,
        "provenance_linked": len(selected) == 1 and selected[0]["provenance"] == "relative_filing_link",
        "statement_range_resolved": False,
        "required_statements": False,
        "fiscal_years_complete": False,
        "no_duplicate_tables": False,
        "no_contamination": False,
    }
    companion = None
    evidence = None
    if len(selected) == 1 and incorporation["page_range"]:
        companion = selected[0]
        evidence = _statement_evidence(Path(companion["local_path"]), incorporation["page_range"])
        gates["statement_range_resolved"] = evidence["page_range_resolved"]
        gates["required_statements"] = all(name in evidence["statement_categories"] for name in _STATEMENT_LABELS)
        gates["fiscal_years_complete"] = all(year in evidence["fiscal_years"] for year in ("2023", "2024", "2025"))
        gates["no_duplicate_tables"] = evidence["table_count"] == evidence["unique_fingerprints"]
        gates["no_contamination"] = not evidence["contamination_markers"]
    gates["input_hashes_unchanged"] = True
    gates["reports_byte_identical"] = None
    status = "companion_missing" if not selected else "ambiguous_companion" if len(selected) > 1 else "candidate_requires_validation"
    return {
        "schema_version": SCHEMA_VERSION,
        "read_only": True,
        "ticker": filing.get("ticker"),
        "accession": filing.get("accession_number"),
        "filing_document": html_path.name,
        "incorporation_evidence": incorporation,
        "companion_candidates": candidates,
        "selected_companion": companion,
        "statement_evidence": evidence,
        "gates": gates,
        "overall_pass": all(value is True for value in gates.values() if value is not None),
        "status": status,
        "production_ready": False,
        "next_action": "obtain the uniquely linked companion document and rerun this read-only audit" if status == "companion_missing" else "resolve candidate ambiguity before extraction",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    html_path, sections_path, chunks_path = _find_paths(settings.data_processed_dir, settings.data_raw_dir)
    inputs = [html_path, sections_path, chunks_path]
    before = _input_digest(inputs)
    result = audit_companion(html_path, sections_path, chunks_path)
    after = _input_digest(inputs)
    result["read_inputs_sha256"] = after
    result["read_inputs_immutable"] = before == after
    result["gates"]["input_hashes_unchanged"] = before == after
    result["gates"]["reports_byte_identical"] = None
    result["overall_pass"] = all(value is True for value in result["gates"].values() if value is not None)
    report = {"schema_version": SCHEMA_VERSION, "read_only": True, "result": result}
    report["report_fingerprint"] = _sha256(json.dumps(report, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"IBM: {result['status']} candidates={len(result['companion_candidates'])} overall_pass={result['overall_pass']}")
    return 0 if result["read_inputs_immutable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
