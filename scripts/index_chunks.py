"""
Script: index_chunks.py
Read all of *_chunks_embedded.jsonl and upload it to Qdrant.
"""

import json
import logging
from pathlib import Path

from configs.settings import settings
from src.retrieval.vector_store import COLLECTION_NAME, VectorStore

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    with VectorStore(path=settings.qdrant_local_path) as store:
        existing = [c.name for c in store.client.get_collections().collections]
        if COLLECTION_NAME in existing:
            store.client.delete_collection(collection_name=COLLECTION_NAME)
            logger.info("Deleted existing collection '%s' before reindexing", COLLECTION_NAME)

        store.create_collection(embedding_dim=768)

        embedded_files = sorted(
            settings.data_processed_dir.glob("*/*_chunks_embedded.jsonl")
        )
        total = 0
        for path in embedded_files:
            chunks = [json.loads(line) for line in path.open(encoding="utf-8")]
            store.upsert_chunks(chunks)
            total += len(chunks)
            logger.info("%s: %d chunks indexed", path.name, len(chunks))

        info = store.get_collection_info()
        logger.info("Completed. Collection info: %s", info)
        logger.info("Total: %d chunks indexed", total)


if __name__ == "__main__":
    main()
