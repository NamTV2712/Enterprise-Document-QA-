"""
Module: embedder.py
Purpose: Create document and query embeddings with Nomic's required prefixes.
"""

import logging

import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"
DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "
AUTO_DEVICE = "auto"


def resolve_torch_device(device: str = AUTO_DEVICE) -> str:
    """Resolve the torch device for neural retrieval models."""
    if device != AUTO_DEVICE:
        return device
    return "cuda" if torch.cuda.is_available() else "cpu"


class Embedder:
    def __init__(self, model_name: str = MODEL_NAME, device: str = AUTO_DEVICE):
        self.device = resolve_torch_device(device)
        logger.info("Loading embedding model: %s on %s", model_name, self.device)
        self.model = SentenceTransformer(
            model_name,
            trust_remote_code=True,
            device=self.device,
        )
        self.dimension = self.model.get_embedding_dimension()
        self.default_document_batch_size = 64 if self.device == "cuda" else 16

    def embed_documents(self, texts: list[str], batch_size: int | None = None) -> list[list[float]]:
        """Embed chunks for storage in the vector index."""
        batch_size = batch_size or self.default_document_batch_size
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
