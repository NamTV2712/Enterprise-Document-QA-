"""
Compare local and cloud Qdrant retrieval for a fixed smoke query.

Run after migration:
    python -m scripts.verify_qdrant_cloud
"""

from configs.settings import settings
from src.retrieval.embedder import Embedder
from src.retrieval.vector_store import VectorStore


def main() -> None:
    if not settings.qdrant_cloud_url or not settings.qdrant_cloud_api_key:
        raise ValueError(
            "QDRANT_CLOUD_URL and QDRANT_CLOUD_API_KEY must be configured in .env"
        )

    embedder = Embedder()
    query_vector = embedder.embed_query("What was Apple's total net sales in 2024?")

    with VectorStore(path=settings.qdrant_local_path) as local_store:
        local_results = local_store.search(query_vector=query_vector, top_k=5, ticker="AAPL")

    with VectorStore(
        mode="cloud",
        url=settings.qdrant_cloud_url,
        api_key=settings.qdrant_cloud_api_key,
    ) as cloud_store:
        cloud_results = cloud_store.search(query_vector=query_vector, top_k=5, ticker="AAPL")

    local_ids = [result["chunk_id"] for result in local_results]
    cloud_ids = [result["chunk_id"] for result in cloud_results]

    print("Local top-5 chunk_ids:", local_ids)
    print("Cloud top-5 chunk_ids:", cloud_ids)
    print("Exact match:", local_ids == cloud_ids)


if __name__ == "__main__":
    main()
