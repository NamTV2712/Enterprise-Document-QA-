"""Promote one verified immutable embedding generation into the active corpus."""
from __future__ import annotations

import argparse

from configs.settings import settings
from src.retrieval.embedding_generation import promote_embedding_generation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--generation",
        type=str,
        required=True,
        help="Completed generation directory to promote",
    )
    args = parser.parse_args(argv)
    manifest = promote_embedding_generation(
        generation_dir=settings.embedding_generations_dir / args.generation,
        active_corpus_dir=settings.data_processed_dir,
    )
    print(
        "Promoted "
        f"{manifest['generation_id']} ({manifest['point_count']} points, "
        f"{manifest['corpus_fingerprint']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
