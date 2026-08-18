"""Audit annual-report extraction boundaries without changing generated artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from configs.settings import settings
from src.ingestion.section_extractor import extract_sections_from_html


TICKERS = ("MS", "MCD", "INTC", "COST", "GE", "HON")
OUTPUT = Path("data/diagnostics/annual_report_extraction_audit.json")


def _section_audit(content: str) -> dict[str, object]:
    prefix = " ".join(content[:500].split()).lower()
    return {
        "characters": len(content),
        "prefix": " ".join(content[:180].split()),
        "starts_with_toc_marker": prefix.startswith("table of contents"),
    }


def main() -> None:
    results = {}
    for ticker in TICKERS:
        raw_files = sorted((settings.data_raw_dir / ticker).glob("*.html"))
        if len(raw_files) != 1:
            raise ValueError(f"Expected exactly one raw filing for {ticker}")
        result = extract_sections_from_html(raw_files[0].read_bytes())
        sections = {name: _section_audit(content) for name, content in result.sections.items()}
        results[ticker] = {
            "all_sections_present": len(sections) == 4,
            "sections": sections,
            "warnings": result.warnings,
        }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = [
        ticker
        for ticker, audit in results.items()
        if not audit["all_sections_present"]
        or any(section["starts_with_toc_marker"] for section in audit["sections"].values())
    ]
    print(f"Wrote {OUTPUT}")
    print("PASS" if not failures else f"REVIEW REQUIRED: {', '.join(failures)}")


if __name__ == "__main__":
    main()
