"""Load retrieval chunks from the corpus source used by the active store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.retrieval.vector_store import VectorStore


def load_embedded_chunks(data_processed_dir: Path) -> list[dict]:
    """Load local embedded chunk artifacts without their dense vectors."""
    chunks = []
    for path in sorted(data_processed_dir.glob("*/*_chunks_embedded.jsonl")):
        with path.open(encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                record = json.loads(line)
                record.pop("embedding", None)
                chunks.append(record)
    return chunks


def load_retrieval_chunks(
    store: VectorStore,
    data_processed_dir: Path,
) -> list[dict]:
    """Load one consistent chunk corpus for lexical and structured retrieval."""
    if store.mode == "cloud":
        return store.load_all_chunks()

    return load_embedded_chunks(data_processed_dir)
