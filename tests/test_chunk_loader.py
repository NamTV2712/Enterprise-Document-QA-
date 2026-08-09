import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.retrieval.chunk_loader import load_embedded_chunks, load_retrieval_chunks


def test_cloud_mode_loads_qdrant_payloads_without_reading_local_files() -> None:
    store = MagicMock(mode="cloud")
    store.load_all_chunks.return_value = [{"chunk_id": "cloud-chunk"}]

    with patch(
        "src.retrieval.chunk_loader.load_embedded_chunks"
    ) as load_local_chunks:
        chunks = load_retrieval_chunks(store, Path("unused-local-corpus"))

    assert chunks == [{"chunk_id": "cloud-chunk"}]
    store.load_all_chunks.assert_called_once_with()
    load_local_chunks.assert_not_called()


def test_local_mode_loads_jsonl_without_scrolling_qdrant_payloads() -> None:
    store = MagicMock(mode="local")
    data_processed_dir = Path("custom-local-corpus")

    with patch(
        "src.retrieval.chunk_loader.load_embedded_chunks",
        return_value=[{"chunk_id": "local-chunk"}],
    ) as load_local_chunks:
        chunks = load_retrieval_chunks(store, data_processed_dir)

    assert chunks == [{"chunk_id": "local-chunk"}]
    load_local_chunks.assert_called_once_with(data_processed_dir)
    store.load_all_chunks.assert_not_called()


def test_local_loader_reads_nested_ticker_files_and_removes_embeddings(
    tmp_path: Path,
) -> None:
    ticker_dir = tmp_path / "AAPL"
    ticker_dir.mkdir()
    embedded_path = ticker_dir / "AAPL_chunks_embedded.jsonl"
    embedded_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "chunk_id": "AAPL_0",
                        "ticker": "AAPL",
                        "text": "first",
                        "embedding": [0.1, 0.2],
                    }
                ),
                "",
                json.dumps(
                    {
                        "chunk_id": "AAPL_1",
                        "ticker": "AAPL",
                        "text": "second",
                        "embedding": [0.3, 0.4],
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    (ticker_dir / "AAPL_chunks.jsonl").write_text(
        json.dumps(
            {
                "chunk_id": "IGNORED",
                "ticker": "AAPL",
                "text": "not embedded",
            }
        ),
        encoding="utf-8",
    )

    chunks = load_embedded_chunks(tmp_path)

    assert {chunk["chunk_id"] for chunk in chunks} == {"AAPL_0", "AAPL_1"}
    assert all("embedding" not in chunk for chunk in chunks)
    assert all(chunk["ticker"] == "AAPL" for chunk in chunks)
