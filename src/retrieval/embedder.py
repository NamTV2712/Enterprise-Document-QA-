"""
Module: embedder.py
Purpose: Create document and query embeddings with Nomic's required prefixes.
"""

import logging

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"
DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "


class Embedder:
    def __init__(self, model_name: str = MODEL_NAME):
        logger.info("Loading embedding model: %s", model_name)
        self.model = SentenceTransformer(model_name, trust_remote_code=True)
        self.dimension = self.model.get_embedding_dimension()

    def embed_documents(self, texts: list[str], batch_size: int = 16) -> list[list[float]]:
        """Embed chunks for storage in the vector index."""
        prefixed = [DOCUMENT_PREFIX + text for text in texts]
        embeddings = self.model.encode(
            prefixed,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Embed a user query for retrieval."""
        embedding = self.model.encode(QUERY_PREFIX + text, convert_to_numpy=True)
        return embedding.tolist()
