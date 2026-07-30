from types import SimpleNamespace
from unittest.mock import MagicMock, call

from src.retrieval.vector_store import COLLECTION_NAME, VectorStore


def test_load_all_chunks_scrolls_payloads_without_vectors() -> None:
    store = VectorStore.__new__(VectorStore)
    store.client = MagicMock()
    store.client.scroll.side_effect = [
        ([SimpleNamespace(payload={"chunk_id": "first"})], "next-page"),
        ([SimpleNamespace(payload={"chunk_id": "second"})], None),
    ]

    chunks = store.load_all_chunks(page_size=10)

    assert chunks == [{"chunk_id": "first"}, {"chunk_id": "second"}]
    assert store.client.scroll.call_args_list == [
        call(
            collection_name=COLLECTION_NAME,
            limit=10,
            offset=None,
            with_payload=True,
            with_vectors=False,
        ),
        call(
            collection_name=COLLECTION_NAME,
            limit=10,
            offset="next-page",
            with_payload=True,
            with_vectors=False,
        ),
    ]
