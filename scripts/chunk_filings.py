"""
Script: chunk_filings.py
Run: python -m scripts.chunk_filings  (from the project's root directory)
"""

import json
import logging
from collections import Counter
from pathlib import Path

from configs.settings import settings
from src.ingestion.chunker import build_chunks_for_filing, save_chunks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _output_path(input_path: Path, ticker: str, accession_number: str) -> Path:
    accession_nodash = accession_number.replace("-", "")
    return input_path.parent / f"{accession_nodash}_chunks.jsonl"


def process_file(input_path: Path) -> list[dict]:
    filing_data = json.loads(input_path.read_text(encoding="utf-8"))
    chunks = build_chunks_for_filing(filing_data)
    output_path = _output_path(input_path, filing_data["ticker"], filing_data["accession_number"])
    save_chunks(chunks, output_path)
    logger.info("Saved %d chunks -> %s", len(chunks), output_path)
    return [chunk.__dict__ for chunk in chunks]


def print_summary(chunks: list[dict]) -> None:
    counts = Counter((chunk["ticker"], chunk["section"]) for chunk in chunks)
    print("ticker,section,chunks")
    for ticker, section in sorted(counts):
        print(f"{ticker},{section},{counts[(ticker, section)]}")


def main() -> None:
    section_files = sorted(settings.data_processed_dir.glob("*/*_sections.json"))
    all_chunks: list[dict] = []

    for section_file in section_files:
        all_chunks.extend(process_file(section_file))

    print_summary(all_chunks)


if __name__ == "__main__":
    main()
