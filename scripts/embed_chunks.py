"""
Script: embed_chunks.py
Run: python -m scripts.embed_chunks  (from the project's root directory)
"""

import argparse
import logging
from pathlib import Path

import sentence_transformers
import torch

from configs.settings import settings
from src.retrieval.embedder import DOCUMENT_PREFIX, Embedder
from src.retrieval.embedding_generation import build_embedding_generation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

EMBEDDING_BUILDER_VERSION = "embedding-builder-v1-generation"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a new immutable embedding generation"
    )
    parser.add_argument(
        "--generation-id",
        required=True,
        help="Unique generation directory name; existing directories are rejected",
    )
    parser.add_argument(
        "--reuse-from",
        type=Path,
        help=(
            "Optional completed generation whose vectors are reused only when "
            "the model metadata and canonical payload match exactly"
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Optional document embedding batch size; lower values reduce GPU memory pressure",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not settings.embedding_model_revision:
        raise ValueError(
            "EMBEDDING_MODEL_REVISION must pin the exact Hugging Face commit "
            "before rebuilding embedded artifacts"
        )
    embedder = Embedder(
        model_name=settings.embedding_model_id,
        revision=settings.embedding_model_revision,
    )
    generation_dir, manifest = build_embedding_generation(
        source_dir=settings.data_processed_dir,
        generations_root=settings.embedding_generations_dir,
        generation_id=args.generation_id,
        embedder=embedder,
        metadata={
            "embedding_model_id": settings.embedding_model_id,
            "embedding_model_revision": settings.embedding_model_revision,
            "vector_dimension": embedder.dimension,
            "document_prefix": DOCUMENT_PREFIX,
            "sentence_transformers_version": sentence_transformers.__version__,
            "torch_version": torch.__version__,
            "compute_device": embedder.device,
            "torch_cuda_version": torch.version.cuda,
            "embedding_dtype": embedder.embedding_dtype,
            "normalize_embeddings": embedder.normalize_embeddings,
            "builder_version": EMBEDDING_BUILDER_VERSION,
        },
        reuse_generation_dir=args.reuse_from,
        batch_size=args.batch_size,
    )
    logger.info(
        "Completed immutable embedding generation %s (%d points)",
        generation_dir,
        manifest["point_count"],
    )


if __name__ == "__main__":
    main()
