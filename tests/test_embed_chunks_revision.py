import json
from pathlib import Path
from uuid import uuid4

from scripts.embed_chunks import process_chunks_file


class _FakeEmbedder:
    def __init__(self):
        self.calls = []

    def embed_documents(self, texts):
        self.calls.append(texts)
        return [[0.9, 1.0] for _ in texts]


def test_forced_revision_build_replaces_fresh_but_untrusted_vectors() -> None:
    stem = f".revision_{uuid4().hex}_chunks"
    chunks_path = Path("tests") / f"{stem}.jsonl"
    output_path = Path("tests") / f"{stem}_embedded.jsonl"
    chunks_path.write_text(
        json.dumps({"chunk_id": "A", "text": "Evidence"}) + "\n",
        encoding="utf-8",
    )
    output_path.write_text(
        json.dumps(
            {"chunk_id": "A", "text": "Evidence", "embedding": [0.1, 0.2]}
        )
        + "\n",
        encoding="utf-8",
    )
    embedder = _FakeEmbedder()
    try:
        result = process_chunks_file(embedder, chunks_path, force=True)
        record = json.loads(result.read_text(encoding="utf-8"))

        assert embedder.calls == [["Evidence"]]
        assert record["embedding"] == [0.9, 1.0]
    finally:
        chunks_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
