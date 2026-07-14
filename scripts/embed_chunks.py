"""
Script: embed_chunks.py
Run: python -m scripts.embed_chunks  (from the project's root directory)
"""

import json
import logging
from pathlib import Path

from configs.settings import settings
from src.retrieval.embedder import Embedder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def process_chunks_file(embedder: Embedder, chunks_path: Path) -> Path:
    output_path = chunks_path.with_name(f"{chunks_path.stem}_embedded.jsonl")
    if output_path.exists() and output_path.stat().st_mtime >= chunks_path.stat().st_mtime:
        logger.info("Skipping already embedded chunks file: %s", output_path)
        return output_path
    if output_path.exists():
        logger.info("Re-embedding stale chunks file: %s", chunks_path)

    records = [
        json.loads(line)
        for line in chunks_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not records:
        logger.warning("Skipping empty chunks file: %s", chunks_path)
        return output_path

    texts = [record["text"] for record in records]
    embeddings = embedder.embed_documents(texts)

    for record, embedding in zip(records, embeddings):
        record["embedding"] = embedding

    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info("Embedded %d chunks -> %s", len(records), output_path)
    return output_path


def main() -> None:
    embedder = Embedder()
    chunks_files = sorted(settings.data_processed_dir.glob("*/*_chunks.jsonl"))

    if not chunks_files:
        logger.warning("No *_chunks.jsonl files found in %s", settings.data_processed_dir)
        return

    for chunks_path in chunks_files:
        process_chunks_file(embedder, chunks_path)


if __name__ == "__main__":
    main()
