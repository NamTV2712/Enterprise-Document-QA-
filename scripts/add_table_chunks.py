"""
Append supplemental financial_table chunks to existing *_chunks.jsonl files.

Run from the project root:
    python -m scripts.add_table_chunks

This script is idempotent: it skips table chunks whose chunk_id already exists
in the target chunks file.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from configs.settings import settings
from src.ingestion.chunker import build_table_chunks
from scripts.diagnostics.diagnose_all_financial_tables import find_tables_in_financial_section

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

def _load_existing_chunk_ids(chunks_path: Path) -> set[str]:
    if not chunks_path.exists():
        return set()

    chunk_ids = set()
    for line in chunks_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        chunk_ids.add(json.loads(line)["chunk_id"])
    return chunk_ids


def _discover_filings() -> list[tuple[str, Path, Path, Path]]:
    filings = []
    for sections_path in sorted(settings.data_processed_dir.glob("*/*_sections.json")):
        ticker = sections_path.parent.name
        accession_nodash = sections_path.name.removesuffix("_sections.json")
        html_path = settings.data_raw_dir / ticker / f"{accession_nodash}.html"
        chunks_path = sections_path.with_name(f"{accession_nodash}_chunks.jsonl")
        filings.append((ticker, html_path, sections_path, chunks_path))
    return filings


def main() -> None:
    total_new = 0
    for ticker, html_path, sections_path, chunks_path in _discover_filings():
        if not html_path.exists() or not sections_path.exists() or not chunks_path.exists():
            logger.warning("Skipping %s because one or more local artifacts are missing", ticker)
            continue

        filing_data = json.loads(sections_path.read_text(encoding="utf-8"))
        if "financial_statements" not in filing_data.get("sections", {}):
            logger.warning("Skipping %s table chunks because financial_statements is missing", ticker)
            continue

        tables = find_tables_in_financial_section(html_path, sections_path)
        table_chunks = build_table_chunks(html_path, tables, filing_data)

        existing_ids = _load_existing_chunk_ids(chunks_path)
        new_chunks = [chunk for chunk in table_chunks if chunk.chunk_id not in existing_ids]
        total_new += len(new_chunks)

        with chunks_path.open("a", encoding="utf-8") as file:
            for chunk in new_chunks:
                file.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")

        logger.info(
            "%s: %d table chunks generated, %d appended, %d already existed",
            ticker,
            len(table_chunks),
            len(new_chunks),
            len(table_chunks) - len(new_chunks),
        )

    logger.info("Total new financial_table chunks appended: %d", total_new)


if __name__ == "__main__":
    main()
