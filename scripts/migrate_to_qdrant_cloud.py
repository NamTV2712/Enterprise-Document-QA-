"""
Migrate the active local Qdrant collection to Qdrant Cloud.

Run from the project root after setting QDRANT_CLOUD_URL and
QDRANT_CLOUD_API_KEY in .env:
    python -m scripts.migrate_to_qdrant_cloud

The script reads points from the local Qdrant collection instead of rebuilding
from JSONL, so it migrates exactly what the current local app is serving.
"""

import argparse
import logging

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, PointStruct, VectorParams

from configs.settings import settings
from src.retrieval.vector_store import COLLECTION_NAME, PAYLOAD_INDEX_FIELDS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

BATCH_SIZE = 100
EMBEDDING_DIMENSION = 768


def _require_cloud_settings() -> None:
    if not settings.qdrant_cloud_url or not settings.qdrant_cloud_api_key:
        raise ValueError(
            "QDRANT_CLOUD_URL and QDRANT_CLOUD_API_KEY must be configured in .env"
        )


def _ensure_payload_indexes(client: QdrantClient) -> None:
    info = client.get_collection(COLLECTION_NAME)
    existing_schema = getattr(info, "payload_schema", None) or {}
    for field_name in PAYLOAD_INDEX_FIELDS:
        if field_name in existing_schema:
            continue
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field_name,
            field_schema=PayloadSchemaType.KEYWORD,
        )
        logger.info("Created cloud payload index for '%s'", field_name)


def migrate(recreate: bool = False) -> None:
    _require_cloud_settings()
    local_client = QdrantClient(path=str(settings.qdrant_local_path))
    cloud_client = QdrantClient(
        url=settings.qdrant_cloud_url,
        api_key=settings.qdrant_cloud_api_key,
    )

    local_collections = [collection.name for collection in local_client.get_collections().collections]
    if COLLECTION_NAME not in local_collections:
        raise ValueError(
            f"Local collection '{COLLECTION_NAME}' does not exist at {settings.qdrant_local_path}"
        )

    local_info = local_client.get_collection(COLLECTION_NAME)
    total_points = local_info.points_count
    logger.info("Local collection '%s' has %d points", COLLECTION_NAME, total_points)

    existing = [collection.name for collection in cloud_client.get_collections().collections]
    if recreate and COLLECTION_NAME in existing:
        cloud_client.delete_collection(collection_name=COLLECTION_NAME)
        existing.remove(COLLECTION_NAME)
        logger.info("Deleted existing cloud collection '%s'", COLLECTION_NAME)

    if COLLECTION_NAME not in existing:
        cloud_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=Distance.COSINE),
        )
        logger.info("Created cloud collection '%s'", COLLECTION_NAME)
    else:
        logger.warning(
            "Cloud collection '%s' already exists; points will be upserted without deleting it",
            COLLECTION_NAME,
        )

    _ensure_payload_indexes(cloud_client)

    migrated = 0
    offset = None
    while True:
        records, next_offset = local_client.scroll(
            collection_name=COLLECTION_NAME,
            limit=BATCH_SIZE,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        if not records:
            break

        cloud_client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(id=record.id, vector=record.vector, payload=record.payload)
                for record in records
            ],
        )
        migrated += len(records)
        logger.info("Migrated %d/%d points", migrated, total_points)

        if next_offset is None:
            break
        offset = next_offset

    cloud_info = cloud_client.get_collection(COLLECTION_NAME)
    logger.info(
        "Completed migration. Local points: %d, cloud points: %d",
        total_points,
        cloud_info.points_count,
    )
    if cloud_info.points_count != total_points:
        raise RuntimeError(
            f"Point count mismatch after migration: local={total_points}, cloud={cloud_info.points_count}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate local Qdrant points to Qdrant Cloud.")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete and recreate the cloud collection before uploading points.",
    )
    args = parser.parse_args()
    migrate(recreate=args.recreate)
