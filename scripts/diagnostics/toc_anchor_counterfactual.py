"""Read-only, deterministic TOC-anchor financial-table counterfactual."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag

from configs.settings import settings
from src.ingestion.chunker import build_table_chunks
from src.ingestion.table_extractor import extract_table_rows, get_table_caption

DEFAULT_OUTPUT = Path("data/diagnostics/toc_anchor_counterfactual.json")
SCHEMA_VERSION = 2
_ROOT_EXACT = re.compile(r"^item\s+8\.?\s+financial\s+statements?\s+and\s+supplementary\s+data$", re.I)
_ROOT_FINANCIAL = re.compile(r"^financial\s+statements?(?:\s+and\s+supplementary\s+data)?$", re.I)
_EXCLUDED = re.compile(r"\b(exhibit|note|balance\s+sheets?|income|operations|cash\s+flows?|stockholders?|shareholders?)\b", re.I)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def _audit_digest(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(set(paths), key=lambda item: str(item)):
        if path.is_file():
            digest.update(str(path).encode())
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return f"sha256:{digest.hexdigest()}"


def _resolve_anchor_target(soup: BeautifulSoup, anchor: Tag) -> tuple[Tag | None, str]:
    href = str(anchor.get("href", ""))
    if not href.startswith("#") or len(href) == 1:
        return None, "not_internal_anchor"
    key = href[1:]
    target = soup.find(id=key) or soup.find(attrs={"name": key})
    return (target, "resolved") if isinstance(target, Tag) else (None, f"target_not_found:{key}")


def _is_root_financial_anchor(link: Tag, label: str) -> bool:
    if not (_ROOT_EXACT.fullmatch(label) or _ROOT_FINANCIAL.fullmatch(label)):
        return False
    for parent in link.find_parents(["a", "h1", "h2", "h3", "h4", "p", "div"]):
        text = " ".join(parent.get_text(" ", strip=True).split())
        if len(text) <= 200 and _EXCLUDED.search(text):
            return False
    return True


def _find_toc_anchors_for_financial_statements(soup: BeautifulSoup) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for order, link in enumerate(soup.find_all("a", href=True)):
        label = " ".join(link.get_text(" ", strip=True).split())
        if _ROOT_EXACT.fullmatch(label) and _is_root_financial_anchor(link, label):
            rank, reason = 0, "exact_item8_root"
        elif _is_root_financial_anchor(link, label):
            rank, reason = 1, "exact_root_financial_statements"
        else:
            continue
        target, resolution = _resolve_anchor_target(soup, link)
        found.append({"label": label, "href": str(link["href"]), "toc_order": order, "rank": rank,
                      "ranking_reason": reason, "target_id": str(link["href"])[1:],
                      "target_tag": target.name if target else None,
                      "target_preview": " ".join(target.get_text(" ", strip=True).split())[:200] if target else "",
                      "resolution": resolution, "target": target})
    return sorted(found, key=lambda item: (item["rank"], item["toc_order"]))


def _get_table_fingerprint(table: Tag) -> str:
    return hashlib.sha256(" ".join(table.get_text(" ", strip=True).split()).encode()).hexdigest()


def _dom_positions(soup: BeautifulSoup) -> dict[int, int]:
    return {id(node): position for position, node in enumerate(soup.descendants)}


def _resolve_body_target(target: Tag) -> Tag:
    if " ".join(target.get_text(" ", strip=True).split()):
        return target
    for node in target.next_elements:
        if isinstance(node, Tag) and re.match(r"^item\s+8\b", " ".join(node.get_text(" ", strip=True).split()), re.I):
            return node
    return target


def _resolve_interval(soup: BeautifulSoup, start: Tag, positions: dict[int, int]) -> tuple[Tag, Tag | None, bool]:
    start_pos = positions[id(start)]
    stop: Tag | None = None
    stop_pos = len(positions) + 1
    for node in soup.find_all(["h1", "h2", "h3", "h4", "p", "div", "span"]):
        position = positions.get(id(node), -1)
        if position <= start_pos or position >= stop_pos:
            continue
        text = " ".join(node.get_text(" ", strip=True).split())
        if len(text) <= 240 and re.match(r"^item\s+(?:9|10)\b", text, re.I):
            stop, stop_pos = node, position
    return start, stop, stop is not None


def _collect_unique_tables(soup: BeautifulSoup, start: Tag, stop: Tag | None, positions: dict[int, int]) -> tuple[list[Tag], int, list[Tag], list[Tag]]:
    low = positions[id(start)]
    high = positions.get(id(stop), len(positions) + 1) if stop else len(positions) + 1
    all_tables = list(soup.find_all("table"))
    before = [table for table in all_tables if positions.get(id(table), -1) <= low]
    inside = [table for table in all_tables if low < positions.get(id(table), -1) < high]
    after = [table for table in all_tables if stop and positions.get(id(table), -1) >= high]
    unique: list[Tag] = []
    seen: set[str] = set()
    for table in inside:
        fingerprint = _get_table_fingerprint(table)
        if fingerprint not in seen:
            seen.add(fingerprint)
            unique.append(table)
    return unique, len(inside) - len(unique), before, after


def _collect_linked_statement_tables_with_evidence(
    soup: BeautifulSoup,
    positions: dict[int, int],
    section_stop: Tag | None,
) -> tuple[list[Tag], int, list[dict[str, Any]]]:
    """Collect one parseable table per non-overlapping statement-link interval."""
    section_stop_pos = positions.get(id(section_stop), len(positions) + 1) if section_stop else len(positions) + 1
    starts: list[tuple[int, str, Tag]] = []
    for link in soup.find_all("a", href=True):
        label = " ".join(link.get_text(" ", strip=True).split())
        if not re.search(r"consolidated|balance sheets?|statements? of|cash flows?", label, re.I):
            continue
        target, _ = _resolve_anchor_target(soup, link)
        if target is None:
            continue
        start = _resolve_body_target(target)
        start_pos = positions.get(id(start), -1)
        if 0 <= start_pos < section_stop_pos:
            starts.append((start_pos, label, start))

    starts.sort(key=lambda item: (item[0], item[1]))
    linked: list[Tag] = []
    intervals: list[dict[str, Any]] = []
    all_tables = list(soup.find_all("table"))
    for index, (start_pos, label, start) in enumerate(starts):
        next_start = starts[index + 1][0] if index + 1 < len(starts) else section_stop_pos
        stop_pos = min(next_start, section_stop_pos)
        candidate = next(
            (table for table in all_tables if start_pos < positions.get(id(table), -1) < stop_pos and extract_table_rows(table)),
            None,
        )
        intervals.append({
            "label": label,
            "start_position": start_pos,
            "stop_position": stop_pos if stop_pos <= len(positions) else None,
            "table_found": candidate is not None,
            "table_position": positions.get(id(candidate)) if candidate else None,
            "table_fingerprint": _get_table_fingerprint(candidate) if candidate else None,
        })
        if candidate is not None:
            linked.append(candidate)
    unique: list[Tag] = []
    seen: set[str] = set()
    for table in linked:
        fingerprint = _get_table_fingerprint(table)
        if fingerprint not in seen:
            seen.add(fingerprint)
            unique.append(table)
    return unique, len(linked) - len(unique), intervals


def _collect_linked_statement_tables(soup: BeautifulSoup, positions: dict[int, int]) -> list[Tag]:
    """Compatibility wrapper for tests and read-only diagnostics."""
    tables, _, _ = _collect_linked_statement_tables_with_evidence(soup, positions, None)
    return tables


def _build_unique_candidate_chunks(html_path: Path, tables: list[Tag], filing_data: dict[str, Any]) -> tuple[list[Any], list[str], list[str], list[str], list[str]]:
    chunks = build_table_chunks(html_path, tables, filing_data)
    chunk_ids = [chunk.chunk_id for chunk in chunks]
    duplicate_ids = [chunk_id for index, chunk_id in enumerate(chunk_ids) if chunk_id in chunk_ids[:index]]
    labels: list[str] = []
    years: set[str] = set()
    captions: list[str] = []
    for table in tables:
        caption = get_table_caption(table)
        if caption:
            captions.append(" ".join(caption.split())[:80])
        for row in extract_table_rows(table):
            if row.label and row.label not in labels:
                labels.append(row.label[:120])
            years.update(row.values_by_year)
    return chunks, duplicate_ids, labels, sorted(years), captions


def _evaluate_gates(clear_stop_boundary: bool, fiscal_years_present: bool, statement_level_rows: bool, buildable_chunks: bool, no_post_boundary_tables: bool, no_duplicate_chunks: bool, valid_body_target: bool) -> dict[str, bool]:
    gates = {"valid_body_target": valid_body_target, "clear_stop_boundary": clear_stop_boundary, "fiscal_years_present": fiscal_years_present, "statement_level_rows": statement_level_rows, "buildable_chunks": buildable_chunks, "no_post_boundary_tables": no_post_boundary_tables, "no_duplicate_chunks": no_duplicate_chunks}
    gates["overall_pass"] = all(gates.values())
    return gates


def _get_counterfactual_result(ticker: str, html_path: Path, sections_path: Path, processed_dir: Path) -> dict[str, Any]:
    del processed_dir
    filing_data = json.loads(sections_path.read_text(encoding="utf-8"))
    soup = BeautifulSoup(html_path.read_bytes(), "lxml")
    positions = _dom_positions(soup)
    candidates = _find_toc_anchors_for_financial_statements(soup)
    selected = next((candidate for candidate in candidates if candidate["target"] is not None), None)
    rejected = [{key: value for key, value in candidate.items() if key != "target"} for candidate in candidates if candidate is not selected]
    if selected is None:
        gates = _evaluate_gates(False, False, False, False, False, False, False)
        return {"schema_version": SCHEMA_VERSION, "ticker": ticker, "selected_root_anchor": None, "rejected_anchor_candidates": rejected, "gates": gates, "overall_pass": False}
    start, stop, clear = _resolve_interval(soup, _resolve_body_target(selected["target"]), positions)
    tables, duplicate_table_count, before, after = _collect_unique_tables(soup, start, stop, positions)
    discovery_mode = "item8_interval"
    statement_intervals: list[dict[str, Any]] = []
    linked_duplicate_table_count = 0
    if not tables:
        # The root Item-8/Item-9 pair can itself be a table-of-contents pair.
        # Statement anchors are then later in the document, so their own
        # non-overlapping intervals must not inherit the TOC stop boundary.
        linked, linked_duplicate_table_count, statement_intervals = _collect_linked_statement_tables_with_evidence(soup, positions, None)
        if linked:
            tables, discovery_mode = linked, "statement_toc_links"
    chunks, duplicate_ids, labels, years, captions = _build_unique_candidate_chunks(html_path, tables, filing_data)
    stop_position = positions.get(id(stop)) if stop else None
    if discovery_mode == "statement_toc_links":
        no_post_boundary_tables = all(
            interval["table_position"] is None
            or interval["stop_position"] is None
            or interval["table_position"] < interval["stop_position"]
            for interval in statement_intervals
        )
    else:
        no_post_boundary_tables = bool(stop_position is not None and all(positions.get(id(table), stop_position + 1) < stop_position for table in tables))
    gates = _evaluate_gates(clear, len(years) >= 2, bool(labels), bool(chunks), no_post_boundary_tables, not duplicate_ids, True)
    payload = {"schema_version": SCHEMA_VERSION, "ticker": ticker, "discovery_mode": discovery_mode,
               "selected_root_anchor": {key: value for key, value in selected.items() if key != "target"}, "rejected_anchor_candidates": rejected,
               "start_target": {"tag": start.name, "id": start.get("id"), "position": positions[id(start)]},
               "stop_target": {"tag": stop.name, "text": " ".join(stop.get_text(" ", strip=True).split())[:160], "position": positions[id(stop)]} if stop else None,
               "clear_stop_boundary": clear, "tables_before_boundary": len(before), "tables_inside_boundary": len(tables) + duplicate_table_count, "tables_after_boundary": len(after),
               "candidate_table_count_before_dedup": len(tables) + duplicate_table_count, "candidate_table_count_after_dedup": len(tables),
               "table_fingerprints": [_get_table_fingerprint(table) for table in tables], "parsed_table_count": sum(bool(extract_table_rows(table)) for table in tables),
               "buildable_chunk_count": len(chunks), "chunk_ids": [chunk.chunk_id for chunk in chunks], "sample_captions": captions[:5], "sample_row_labels": labels[:20],
               "fiscal_years": years, "post_boundary_table_count": len(after), "duplicate_table_count": duplicate_table_count + linked_duplicate_table_count,
               "duplicate_chunk_ids": duplicate_ids, "statement_link_intervals": statement_intervals, "gates": gates, "overall_pass": gates["overall_pass"]}
    payload["result_fingerprint"] = "sha256:" + hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return payload


def _run_counterfactual(ticker: str, processed_dir: Path, raw_dir: Path) -> dict[str, Any]:
    paths = sorted(processed_dir.glob(f"{ticker}/*_sections.json"))
    if not paths:
        return {"schema_version": SCHEMA_VERSION, "ticker": ticker, "error": "no_sections_json"}
    section = paths[0]
    html = raw_dir / ticker / (section.stem.removesuffix("_sections") + ".html")
    if not html.exists():
        return {"schema_version": SCHEMA_VERSION, "ticker": ticker, "error": "raw_html_missing"}
    return _get_counterfactual_result(ticker, html, section, processed_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--tickers", nargs="*", default=["NVDA", "ORCL", "PEP", "AAPL", "MSFT", "AMZN"])
    args = parser.parse_args(argv)
    inputs = [path for ticker in args.tickers for path in [*settings.data_processed_dir.glob(f"{ticker}/*_sections.json"), *settings.data_raw_dir.glob(f"{ticker}/*.html")]]
    before = _audit_digest(inputs)
    results = [_run_counterfactual(ticker, settings.data_processed_dir, settings.data_raw_dir) for ticker in args.tickers]
    after = _audit_digest(inputs)
    output = {"schema_version": SCHEMA_VERSION, "read_only": True, "read_inputs_immutable": before == after, "read_inputs_sha256": after, "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    for result in results:
        print(f"{result.get('ticker', '?')}: overall_pass={result.get('overall_pass', False)} tables={result.get('candidate_table_count_after_dedup', 0)} chunks={result.get('buildable_chunk_count', 0)}")
    return 0 if output["read_inputs_immutable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
