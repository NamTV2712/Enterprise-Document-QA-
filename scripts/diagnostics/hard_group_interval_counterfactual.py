"""Read-only candidate-interval counterfactual for CVX, XOM, and JPM."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag

from configs.settings import settings
from src.ingestion.table_extractor import extract_table_rows, get_table_caption

DEFAULT_OUTPUT = Path("data/diagnostics/hard_group_interval_counterfactual.json")
DEFAULT_TICKERS = ("CVX", "XOM", "JPM")
SCHEMA_VERSION = 1
_START_LABELS = (
    (0, re.compile(r"^consolidated statements? of (income|operations|earnings)", re.I)),
    (1, re.compile(r"^consolidated financial statements$", re.I)),
    (2, re.compile(r"^(consolidated )?(balance sheet|statement of cash flows?)$", re.I)),
)
_STOP = re.compile(r"^(?:notes to (?:the )?consolidated financial statements|item\s+9\b|part\s+(?:iii|iv)\b|signatures?\b)", re.I)
_CONTAMINATION = re.compile(r"\b(?:item\s+9|part\s+iv|signatures?)\b", re.I)
_CATEGORY_PATTERNS = {
    "income": re.compile(r"net (?:income|earnings|revenue)|total revenues?|cost of sales", re.I),
    "balance_sheet": re.compile(r"total assets|total liabilities|cash and cash equivalents", re.I),
    "cash_flow": re.compile(r"net cash (?:provided|used)|cash flows?", re.I),
    "equity": re.compile(r"stockholders?.{0,4}equity|shareholders?.{0,4}equity|common stock", re.I),
}


def _sha256(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _digest_inputs(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(set(paths), key=lambda item: str(item)):
        if path.is_file():
            digest.update(str(path).encode())
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return f"sha256:{digest.hexdigest()}"


def _find_paths(ticker: str, processed_dir: Path, raw_dir: Path) -> tuple[Path, Path]:
    matches = sorted(processed_dir.glob(f"{ticker}/*_sections.json"))
    if len(matches) != 1:
        raise FileNotFoundError(f"expected one sections file for {ticker}, found {len(matches)}")
    sections_path = matches[0]
    accession = sections_path.stem.removesuffix("_sections")
    html_path = raw_dir / ticker / f"{accession}.html"
    if not html_path.is_file():
        raise FileNotFoundError(f"missing raw HTML for {ticker}")
    return html_path, sections_path


def _positions(soup: BeautifulSoup) -> dict[int, int]:
    return {id(node): index for index, node in enumerate(soup.descendants)}


def _link_starts(soup: BeautifulSoup, positions: dict[int, int]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[int] = set()
    for link in soup.find_all("a", href=True):
        label = " ".join(link.get_text(" ", strip=True).split())
        rank = next((rank for rank, pattern in _START_LABELS if pattern.fullmatch(label)), None)
        if rank is None:
            continue
        href = str(link["href"])
        if not href.startswith("#") or len(href) == 1:
            continue
        target = soup.find(id=href[1:]) or soup.find(attrs={"name": href[1:]})
        if not isinstance(target, Tag):
            continue
        position = positions.get(id(target))
        if position is None or position in seen:
            continue
        seen.add(position)
        candidates.append({"rank": rank, "label": label, "href": href, "position": position, "target": target})
    return sorted(candidates, key=lambda item: (item["rank"], item["position"], item["label"]))


def _find_stop(soup: BeautifulSoup, start: Tag, positions: dict[int, int]) -> Tag | None:
    start_position = positions[id(start)]
    candidates: list[tuple[int, Tag]] = []
    for node in soup.find_all(["h1", "h2", "h3", "h4", "p", "div", "span"]):
        position = positions.get(id(node), -1)
        if position <= start_position:
            continue
        text = " ".join(node.get_text(" ", strip=True).split())
        if len(text) <= 240 and _STOP.match(text):
            candidates.append((position, node))
    return min(candidates, key=lambda item: item[0])[1] if candidates else None


def _interval_text(start: Tag, stop: Tag | None) -> str:
    fragments: list[str] = []
    for node in start.next_elements:
        if node is stop:
            break
        if isinstance(node, NavigableString):
            fragments.append(str(node))
    return "\n".join(fragments)


def _table_fingerprint(table: Tag) -> str:
    return _sha256(" ".join(table.get_text(" ", strip=True).split()).encode())


def _interval_tables(soup: BeautifulSoup, start: Tag, stop: Tag | None, positions: dict[int, int]) -> list[dict[str, Any]]:
    low = positions[id(start)]
    high = positions.get(id(stop), len(positions) + 1) if stop else len(positions) + 1
    rows: list[dict[str, Any]] = []
    for table_index, table in enumerate(soup.find_all("table")):
        position = positions.get(id(table), -1)
        if not low < position < high:
            continue
        parsed = extract_table_rows(table)
        if not parsed:
            continue
        labels = [row.label for row in parsed]
        joined = " | ".join(labels)
        categories = sorted(category for category, pattern in _CATEGORY_PATTERNS.items() if pattern.search(joined))
        rows.append({
            "table_index": table_index,
            "position": position,
            "fingerprint": _table_fingerprint(table),
            "caption": " ".join(get_table_caption(table).split())[:180],
            "row_labels": labels[:16],
            "fiscal_years": sorted({year for row in parsed for year in row.values_by_year}),
            "statement_categories": categories,
        })
    return rows


def audit_interval(html_path: Path, sections_path: Path) -> dict[str, Any]:
    filing = json.loads(sections_path.read_text(encoding="utf-8"))
    html = html_path.read_bytes()
    soup = BeautifulSoup(html, "lxml")
    positions = _positions(soup)
    starts = _link_starts(soup, positions)
    selected = starts[0] if starts else None
    if selected is None:
        return {
            "schema_version": SCHEMA_VERSION,
            "ticker": filing["ticker"],
            "selected_start": None,
            "gates": {"start_resolved": False, "overall_pass": False},
            "overall_pass": False,
        }
    stop = _find_stop(soup, selected["target"], positions)
    text = _interval_text(selected["target"], stop)
    tables = _interval_tables(soup, selected["target"], stop, positions)
    fiscal_years = sorted({year for table in tables for year in table["fiscal_years"]})
    categories = sorted({category for table in tables for category in table["statement_categories"]})
    fingerprints = [table["fingerprint"] for table in tables]
    gates = {
        "start_resolved": True,
        "stop_resolved": stop is not None,
        "nonempty_parseable_tables": bool(tables),
        "fiscal_years_present": len(fiscal_years) >= 2,
        "primary_statement_coverage": len(categories) >= 3,
        "no_duplicate_tables": len(fingerprints) == len(set(fingerprints)),
        "no_contamination": not bool(_CONTAMINATION.search(text)),
    }
    gates["overall_pass"] = all(gates.values())
    result = {
        "schema_version": SCHEMA_VERSION,
        "ticker": filing["ticker"],
        "candidate_starts": [{key: value for key, value in item.items() if key != "target"} for item in starts],
        "selected_start": {key: value for key, value in selected.items() if key != "target"},
        "stop": {"position": positions[id(stop)], "text": " ".join(stop.get_text(" ", strip=True).split())[:240]} if stop else None,
        "interval_text_chars": len(text),
        "tables": tables,
        "fiscal_years": fiscal_years,
        "statement_categories": categories,
        "gates": gates,
        "overall_pass": gates["overall_pass"],
    }
    result["result_fingerprint"] = _sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode())
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tickers", nargs="*", default=list(DEFAULT_TICKERS))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    paths = [_find_paths(ticker, settings.data_processed_dir, settings.data_raw_dir) for ticker in args.tickers]
    inputs = [path for pair in paths for path in pair]
    before = _digest_inputs(inputs)
    results = [audit_interval(*pair) for pair in paths]
    after = _digest_inputs(inputs)
    report = {"schema_version": SCHEMA_VERSION, "read_only": True, "read_inputs_immutable": before == after, "read_inputs_sha256": after, "results": results}
    report["report_fingerprint"] = _sha256(json.dumps(report, sort_keys=True, ensure_ascii=False).encode())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    for result in results:
        print(f"{result['ticker']}: overall_pass={result['overall_pass']} tables={len(result.get('tables', []))}")
    return 0 if report["read_inputs_immutable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
