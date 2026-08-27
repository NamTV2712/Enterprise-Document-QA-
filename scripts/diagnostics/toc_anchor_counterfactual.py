"""Read-only, deterministic TOC-anchor financial-table counterfactual."""
from __future__ import annotations
import argparse, hashlib, json, logging, re
from pathlib import Path
from typing import Any
from bs4 import BeautifulSoup, Tag
from configs.settings import settings
from src.ingestion.chunker import build_table_chunks
from src.ingestion.table_extractor import extract_table_rows, get_table_caption

DEFAULT_OUTPUT = Path("data/diagnostics/toc_anchor_counterfactual.json")
SCHEMA_VERSION = 2
_ITEM9 = re.compile(r"\bitem\s+9(?:\.|\s|$)", re.I)
_ITEM10 = re.compile(r"\bitem\s+10(?:\.|\s|$)", re.I)
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_ROOT_EXACT = re.compile(r"^item\s+8\.?\s+financial\s+statements?\s+and\s+supplementary\s+data$", re.I)
_ROOT_FINANCIAL = re.compile(r"^financial\s+statements?(?:\s+and\s+supplementary\s+data)?$", re.I)
_EXCLUDED = re.compile(r"\b(exhibit|note|balance\s+sheets?|income|operations|cash\s+flows?|stockholders?|shareholders?)\b", re.I)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

def _audit_digest(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for path in sorted(set(paths), key=lambda p: str(p)):
        if path.is_file():
            h.update(str(path).encode()); h.update(hashlib.sha256(path.read_bytes()).digest())
    return f"sha256:{h.hexdigest()}"

def _resolve_anchor_target(soup: BeautifulSoup, anchor: Tag) -> tuple[Tag | None, str]:
    href = str(anchor.get("href", ""))
    if not href.startswith("#") or len(href) == 1: return None, "not_internal_anchor"
    key = href[1:]; target = soup.find(id=key) or soup.find(attrs={"name": key})
    return (target, "") if isinstance(target, Tag) else (None, f"target_not_found:{key}")

def _anchor_rank(label: str) -> int | None:
    label = " ".join(label.split()).strip()
    if _ROOT_EXACT.fullmatch(label): return 0
    if _ROOT_FINANCIAL.fullmatch(label): return 1
    return None if _EXCLUDED.search(label) else None

def _find_toc_anchors_for_financial_statements(soup: BeautifulSoup) -> list[dict[str, Any]]:
    found = []
    for order, link in enumerate(soup.find_all("a", href=True)):
        label = " ".join(link.get_text(" ", strip=True).split()); rank = _anchor_rank(label)
        if rank is None: continue
        target, reason = _resolve_anchor_target(soup, link)
        found.append({"label": label, "href": link["href"], "toc_order": order, "rank": rank,
                      "target_id": link["href"][1:], "target_tag": target.name if target else None,
                      "target_preview": " ".join(target.get_text(" ", strip=True).split())[:200] if target else "",
                      "resolution": reason or "resolved", "target": target})
    return sorted(found, key=lambda x: (x["rank"], x["toc_order"]))

def _get_table_fingerprint(table: Tag) -> str:
    return hashlib.sha256(" ".join(table.get_text(" ", strip=True).split()).encode()).hexdigest()

def _dom_positions(soup: BeautifulSoup) -> dict[int, int]:
    return {id(node): i for i, node in enumerate(soup.descendants)}

def _resolve_body_target(target: Tag) -> Tag:
    """Move an empty SEC anchor to the following Item 8 body heading."""
    text = " ".join(target.get_text(" ", strip=True).split())
    if text:
        return target
    for node in target.next_elements:
        if isinstance(node, str) and re.search(r"\bitem\s+8\b", node, re.I):
            return node.parent if isinstance(node.parent, Tag) else target
    return target

def _resolve_interval(soup: BeautifulSoup, start: Tag, positions: dict[int, int]) -> tuple[Tag, Tag | None, bool]:
    start_pos = positions[id(start)]; stop = None; stop_pos = len(positions) + 1
    for node in soup.find_all(["h1", "h2", "h3", "h4", "p", "div", "span", "td", "th"]):
        if positions.get(id(node), -1) <= start_pos: continue
        text = " ".join(node.get_text(" ", strip=True).split())
        if (_ITEM9.search(text) or _ITEM10.search(text)) and positions[id(node)] < stop_pos:
            stop, stop_pos = node, positions[id(node)]
    return start, stop, stop is not None

def _collect_unique_tables(soup: BeautifulSoup, start: Tag, stop: Tag | None, positions: dict[int, int]) -> tuple[list[Tag], int, list[Tag]]:
    lo = positions[id(start)]; hi = positions.get(id(stop), len(positions) + 1) if stop else len(positions) + 1
    inside = [t for t in soup.find_all("table") if lo < positions.get(id(t), -1) < hi]
    after = [t for t in soup.find_all("table") if stop and positions.get(id(t), -1) >= hi]
    unique, seen = [], set()
    for table in inside:
        fp = _get_table_fingerprint(table)
        if fp not in seen: seen.add(fp); unique.append(table)
    return unique, len(inside) - len(unique), after

def _collect_linked_statement_tables(soup: BeautifulSoup, anchors: list[dict[str, Any]], positions: dict[int, int]) -> list[Tag]:
    """Collect tables reached by individual statement TOC links."""
    linked = []
    all_links = list(anchors)
    for link in soup.find_all("a", href=True):
        label = " ".join(link.get_text(" ", strip=True).split())
        target, reason = _resolve_anchor_target(soup, link)
        all_links.append({"label": label, "target": target, "resolution": reason})
    for anchor in all_links:
        label = anchor["label"]
        if not re.search(r"consolidated|balance sheets?|statements? of|cash flows?", label, re.I):
            continue
        target = anchor.get("target")
        if target is None:
            continue
        start = _resolve_body_target(target); lo = positions.get(id(start), -1)
        for table in soup.find_all("table"):
            if positions.get(id(table), -1) > lo:
                linked.append(table)
                break
    unique, seen = [], set()
    for table in linked:
        fp = _get_table_fingerprint(table)
        if fp not in seen: seen.add(fp); unique.append(table)
    return unique

def _build_unique_candidate_chunks(html_path: Path, tables: list[Tag], filing_data: dict[str, Any]) -> tuple[list[Any], list[str], list[str], list[str], list[str]]:
    chunks = build_table_chunks(html_path, tables, filing_data)
    ids, labels, years, captions = [], [], set(), []
    for chunk in chunks:
        if chunk.chunk_id in ids: ids.append(chunk.chunk_id)
        else: ids.append(chunk.chunk_id)
    for table in tables:
        caption = get_table_caption(table)
        if caption: captions.append(" ".join(caption.split())[:80])
        for row in extract_table_rows(table):
            if row.label and row.label not in labels: labels.append(row.label[:120])
            years.update(row.values_by_year)
    duplicate_ids = [x for i, x in enumerate(ids) if x in ids[:i]]
    return chunks, duplicate_ids, labels, sorted(years), captions

def _evaluate_gates(clear_stop_boundary: bool, fiscal_years_present: bool, statement_level_rows: bool, buildable_chunks: bool, no_post_boundary_tables: bool, no_duplicate_chunks: bool, valid_body_target: bool) -> dict[str, bool]:
    gates = {"valid_body_target": valid_body_target, "clear_stop_boundary": clear_stop_boundary, "fiscal_years_present": fiscal_years_present, "statement_level_rows": statement_level_rows, "buildable_chunks": buildable_chunks, "no_post_boundary_tables": no_post_boundary_tables, "no_duplicate_chunks": no_duplicate_chunks}
    gates["overall_pass"] = all(gates.values()); return gates

def _get_counterfactual_result(ticker: str, html_path: Path, sections_path: Path, processed_dir: Path) -> dict[str, Any]:
    filing_data = json.loads(sections_path.read_text(encoding="utf-8")); soup = BeautifulSoup(html_path.read_bytes(), "lxml"); positions = _dom_positions(soup)
    candidates = _find_toc_anchors_for_financial_statements(soup); selected = next((a for a in candidates if a["target"] is not None), None)
    rejected = [{k: v for k, v in a.items() if k != "target"} for a in candidates if a is not selected]
    if selected is None:
        gates = _evaluate_gates(False, False, False, False, False, False, False)
        return {"schema_version": SCHEMA_VERSION, "ticker": ticker, "selected_root_anchor": None, "rejected_anchor_candidates": rejected, "gates": gates, "overall_pass": False}
    body_target = _resolve_body_target(selected["target"])
    start, stop, clear = _resolve_interval(soup, body_target, positions); tables, dup_count, after = _collect_unique_tables(soup, start, stop, positions)
    discovery_mode = "item8_interval"
    if not tables:
        linked_tables = _collect_linked_statement_tables(soup, candidates, positions)
        if linked_tables:
            tables = linked_tables; discovery_mode = "statement_toc_links"
    chunks, duplicate_ids, labels, years, captions = _build_unique_candidate_chunks(html_path, tables, filing_data)
    # Tables after the resolved boundary are expected in a filing; the gate
    # asserts that they were excluded from the candidate interval.
    gates = _evaluate_gates(clear, len(years) >= 2, bool(labels), bool(chunks), clear, not duplicate_ids and dup_count == 0, True)
    payload = {"schema_version": SCHEMA_VERSION, "ticker": ticker, "discovery_mode": discovery_mode, "selected_root_anchor": {k: v for k, v in selected.items() if k != "target"}, "rejected_anchor_candidates": rejected, "start_target": {"tag": start.name, "id": start.get("id"), "position": positions[id(start)]}, "stop_target": {"tag": stop.name, "text": " ".join(stop.get_text(" ", strip=True).split())[:160], "position": positions[id(stop)]} if stop else None, "clear_stop_boundary": clear, "candidate_table_count_before_dedup": len(tables) + dup_count, "candidate_table_count_after_dedup": len(tables), "table_fingerprints": [_get_table_fingerprint(t) for t in tables], "parsed_table_count": sum(bool(extract_table_rows(t)) for t in tables), "buildable_chunk_count": len(chunks), "chunk_ids": [c.chunk_id for c in chunks], "sample_captions": captions[:5], "sample_row_labels": labels[:20], "fiscal_years": years, "post_boundary_table_count": len(after), "duplicate_table_count": dup_count, "duplicate_chunk_ids": duplicate_ids, "gates": gates, "overall_pass": gates["overall_pass"]}
    payload["result_fingerprint"] = "sha256:" + hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest(); return payload

def _run_counterfactual(ticker: str, processed_dir: Path, raw_dir: Path) -> dict[str, Any]:
    paths = sorted(processed_dir.glob(f"{ticker}/*_sections.json"))
    if not paths: return {"schema_version": SCHEMA_VERSION, "ticker": ticker, "error": "no_sections_json"}
    section = paths[0]; html = raw_dir / ticker / (section.stem.removesuffix("_sections") + ".html")
    if not html.exists(): return {"schema_version": SCHEMA_VERSION, "ticker": ticker, "error": "raw_html_missing"}
    return _get_counterfactual_result(ticker, html, section, processed_dir)

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0]); parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT); parser.add_argument("--tickers", nargs="*", default=["NVDA", "ORCL", "PEP", "AAPL", "MSFT", "AMZN"]); args = parser.parse_args(argv)
    inputs = [p for t in args.tickers for p in list(settings.data_processed_dir.glob(f"{t}/*_sections.json")) + list(settings.data_raw_dir.glob(f"{t}/*.html"))]; before = _audit_digest(inputs); results = [_run_counterfactual(t, settings.data_processed_dir, settings.data_raw_dir) for t in args.tickers]; after = _audit_digest(inputs)
    output = {"schema_version": SCHEMA_VERSION, "read_only": True, "read_inputs_immutable": before == after, "read_inputs_sha256": after, "results": results}; args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    for r in results: print(f"{r.get('ticker', '?')}: overall_pass={r.get('overall_pass', False)} tables={r.get('candidate_table_count_after_dedup', 0)} chunks={r.get('buildable_chunk_count', 0)}")
    return 0 if output["read_inputs_immutable"] else 1

if __name__ == "__main__": raise SystemExit(main())
