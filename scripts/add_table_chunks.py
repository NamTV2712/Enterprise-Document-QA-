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

from src.ingestion.chunker import build_table_chunks
from scripts.diagnose_all_financial_tables import find_tables_in_financial_section

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

FILINGS = [
    (
        "AAPL",
        Path("data/raw/AAPL/000032019325000079.html"),
        Path("data/processed/AAPL/000032019325000079_sections.json"),
        Path("data/processed/AAPL/000032019325000079_chunks.jsonl"),
    ),
    (
        "MSFT",
        Path("data/raw/MSFT/000095017025100235.html"),
        Path("data/processed/MSFT/000095017025100235_sections.json"),
        Path("data/processed/MSFT/000095017025100235_chunks.jsonl"),
    ),
    (
        "AMZN",
        Path("data/raw/AMZN/000101872426000004.html"),
        Path("data/processed/AMZN/000101872426000004_sections.json"),
        Path("data/processed/AMZN/000101872426000004_chunks.jsonl"),
    ),
]


def _load_existing_chunk_ids(chunks_path: Path) -> set[str]:
    if not chunks_path.exists():
        return set()

    chunk_ids = set()
    for line in chunks_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        chunk_ids.add(json.loads(line)["chunk_id"])
    return chunk_ids


def main() -> None:
    total_new = 0
    for ticker, html_path, sections_path, chunks_path in FILINGS:
        if not html_path.exists() or not sections_path.exists() or not chunks_path.exists():
            logger.warning("Skipping %s because one or more local artifacts are missing", ticker)
            continue

        filing_data = json.loads(sections_path.read_text(encoding="utf-8"))
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
