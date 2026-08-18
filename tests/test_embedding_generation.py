import json
import shutil
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest

import src.retrieval.embedding_generation as generation_module
from src.retrieval.embedding_generation import (
    EMBEDDING_GENERATION_MANIFEST_NAME,
    build_embedding_generation,
    compute_embedding_generation_fingerprint,
    load_validated_embedding_generation,
    validate_generation_id,
)


@contextmanager
def _workspace():
    root = Path("tests") / f".embedding_generation_{uuid4().hex}"
    root.mkdir()
    try:
        yield root
    finally:
        shutil.rmtree(root)


class _FakeEmbedder:
    def __init__(self, *, fail_on_call: int | None = None):
        self.calls = []
        self.fail_on_call = fail_on_call

    def embed_documents(self, texts):
        self.calls.append(texts)
        if self.fail_on_call == len(self.calls):
            raise RuntimeError("embedding failed")
        base = float(len(self.calls))
        return [[base, base + 0.1] for _ in texts]


def _record(chunk_id: str, ticker: str, chunk_index: int = 0) -> dict:
    return {
        "chunk_id": chunk_id,
        "text": f"Evidence {chunk_id}",
        "ticker": ticker,
        "section": "risk_factors",
        "accession_number": f"filing-{ticker}",
        "filing_date": "2025-01-01",
        "report_date": "2024-12-31",
        "chunk_index": chunk_index,
        "token_count": 2,
    }


def _write_source(root: Path, ticker: str, records: list[dict]) -> Path:
    ticker_dir = root / ticker
    ticker_dir.mkdir(parents=True, exist_ok=True)
    path = ticker_dir / f"{ticker}_chunks.jsonl"
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    if records:
        embedded_path = ticker_dir / f"{ticker}_chunks_embedded.jsonl"
        embedded_path.write_text(
            "".join(
                json.dumps({**record, "embedding": [0.0, 0.0]}) + "\n"
                for record in records
            ),
            encoding="utf-8",
        )
    return path


def _metadata() -> dict:
    return {
        "embedding_model_id": "nomic-ai/nomic-embed-text-v1.5",
        "embedding_model_revision": "model-commit",
        "vector_dimension": 2,
        "document_prefix": "search_document: ",
        "sentence_transformers_version": "5.6.0",
        "torch_version": "2.11.0+cu128",
        "compute_device": "cuda",
        "torch_cuda_version": "12.8",
        "embedding_dtype": "float32",
        "normalize_embeddings": False,
        "builder_version": "embedding-builder-v1-generation",
    }


@pytest.mark.parametrize(
    "generation_id",
    ["../escape", "..", ".", "nested/path", r"nested\path", " space"],
)
def test_generation_id_rejects_traversal_and_separators(generation_id) -> None:
    with pytest.raises(ValueError, match="generation_id"):
        validate_generation_id(generation_id)


def test_existing_generation_directory_fails_before_embedding() -> None:
    with _workspace() as root:
        source = root / "source"
        generations = root / "generations"
        _write_source(source, "AAPL", [_record("A", "AAPL")])
        (generations / "generation-001").mkdir(parents=True)
        embedder = _FakeEmbedder()

        with pytest.raises(FileExistsError):
            build_embedding_generation(
                source_dir=source,
                generations_root=generations,
                generation_id="generation-001",
                embedder=embedder,
                metadata=_metadata(),
            )

        assert embedder.calls == []


def test_complete_generation_is_reloaded_and_validated_from_disk() -> None:
    with _workspace() as root:
        source = root / "source"
        generations = root / "generations"
        _write_source(source, "AAPL", [_record("A", "AAPL")])
        _write_source(source, "MSFT", [_record("B", "MSFT")])
        _write_source(source, "EMPTY", [])

        generation_dir, manifest = build_embedding_generation(
            source_dir=source,
            generations_root=generations,
            generation_id="generation-001",
            embedder=_FakeEmbedder(),
            metadata=_metadata(),
        )
        chunks, loaded = load_validated_embedding_generation(
            generation_dir,
            active_corpus_dir=source,
        )

        assert loaded == manifest
        assert {chunk["chunk_id"] for chunk in chunks} == {"A", "B"}
        assert manifest["source_file_count"] == 3
        assert manifest["embedded_file_count"] == 2
        assert manifest["empty_source_files"] == ["EMPTY/EMPTY_chunks.jsonl"]
        assert [entry["relative_path"] for entry in manifest["files"]] == [
            "AAPL/AAPL_chunks_embedded.jsonl",
            "MSFT/MSFT_chunks_embedded.jsonl",
        ]
        assert all(entry["record_count"] == 1 for entry in manifest["files"])
        assert all(entry["file_sha256"].startswith("sha256:") for entry in manifest["files"])
        assert manifest["compute_device"] == "cuda"
        assert manifest["embedding_dtype"] == "float32"
        assert manifest["normalize_embeddings"] is False


def test_embedding_failure_leaves_generation_without_completion_manifest() -> None:
    with _workspace() as root:
        source = root / "source"
        generations = root / "generations"
        _write_source(source, "AAPL", [_record("A", "AAPL")])
        _write_source(source, "MSFT", [_record("B", "MSFT")])

        with pytest.raises(RuntimeError, match="embedding failed"):
            build_embedding_generation(
                source_dir=source,
                generations_root=generations,
                generation_id="generation-failed",
                embedder=_FakeEmbedder(fail_on_call=2),
                metadata=_metadata(),
            )

        generation_dir = generations / "generation-failed"
        assert generation_dir.is_dir()
        assert not (generation_dir / EMBEDDING_GENERATION_MANIFEST_NAME).exists()
        with pytest.raises(ValueError, match="completion manifest is absent"):
            load_validated_embedding_generation(
                generation_dir,
                active_corpus_dir=source,
            )


def test_generation_reuses_only_exact_matching_payloads() -> None:
    with _workspace() as root:
        source = root / "source"
        generations = root / "generations"
        _write_source(source, "AAPL", [_record("A", "AAPL")])
        _write_source(source, "MSFT", [_record("B", "MSFT")])
        original_embedder = _FakeEmbedder()
        original_dir, _ = build_embedding_generation(
            source_dir=source,
            generations_root=generations,
            generation_id="generation-original",
            embedder=original_embedder,
            metadata=_metadata(),
        )

        changed = _record("B", "MSFT")
        changed["text"] = "Changed evidence"
        _write_source(source, "MSFT", [changed])
        incremental_embedder = _FakeEmbedder()
        generation_dir, _ = build_embedding_generation(
            source_dir=source,
            generations_root=generations,
            generation_id="generation-incremental",
            embedder=incremental_embedder,
            metadata=_metadata(),
            reuse_generation_dir=original_dir,
        )

        assert incremental_embedder.calls == [["Changed evidence"]]
        aapl = json.loads(
            (generation_dir / "AAPL" / "AAPL_chunks_embedded.jsonl").read_text(
                encoding="utf-8"
            )
        )
        assert aapl["embedding"] == [1.0, 1.1]

def test_completion_manifest_is_not_published_when_disk_reload_fails(
    monkeypatch,
) -> None:
    with _workspace() as root:
        source = root / "source"
        generations = root / "generations"
        _write_source(source, "AAPL", [_record("A", "AAPL")])

        def fail_reload(**kwargs):
            raise ValueError("disk validation failed")

        monkeypatch.setattr(generation_module, "_manifest_from_disk", fail_reload)
        with pytest.raises(ValueError, match="disk validation failed"):
            build_embedding_generation(
                source_dir=source,
                generations_root=generations,
                generation_id="generation-failed",
                embedder=_FakeEmbedder(),
                metadata=_metadata(),
            )

        generation_dir = generations / "generation-failed"
        assert (generation_dir / "AAPL" / "AAPL_chunks_embedded.jsonl").exists()
        assert not (generation_dir / EMBEDDING_GENERATION_MANIFEST_NAME).exists()


def test_loader_recomputes_file_and_vector_fingerprints() -> None:
    with _workspace() as root:
        source = root / "source"
        generations = root / "generations"
        _write_source(source, "AAPL", [_record("A", "AAPL")])
        generation_dir, _ = build_embedding_generation(
            source_dir=source,
            generations_root=generations,
            generation_id="generation-001",
            embedder=_FakeEmbedder(),
            metadata=_metadata(),
        )
        output = generation_dir / "AAPL" / "AAPL_chunks_embedded.jsonl"
        record = json.loads(output.read_text(encoding="utf-8"))
        record["embedding"] = [9.0, 9.1]
        output.write_text(json.dumps(record) + "\n", encoding="utf-8")

        with pytest.raises(ValueError, match="does not match disk"):
            load_validated_embedding_generation(
                generation_dir,
                active_corpus_dir=source,
            )


def test_loader_rejects_manifest_file_path_traversal() -> None:
    with _workspace() as root:
        source = root / "source"
        generations = root / "generations"
        _write_source(source, "AAPL", [_record("A", "AAPL")])
        generation_dir, _ = build_embedding_generation(
            source_dir=source,
            generations_root=generations,
            generation_id="generation-001",
            embedder=_FakeEmbedder(),
            metadata=_metadata(),
        )
        manifest_path = generation_dir / EMBEDDING_GENERATION_MANIFEST_NAME
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"][0]["relative_path"] = "../outside_chunks_embedded.jsonl"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        with pytest.raises(ValueError, match="stay within generation"):
            load_validated_embedding_generation(
                generation_dir,
                active_corpus_dir=source,
            )


def test_loader_rejects_active_corpus_drift() -> None:
    with _workspace() as root:
        source = root / "source"
        generations = root / "generations"
        source_path = _write_source(source, "AAPL", [_record("A", "AAPL")])
        generation_dir, _ = build_embedding_generation(
            source_dir=source,
            generations_root=generations,
            generation_id="generation-001",
            embedder=_FakeEmbedder(),
            metadata=_metadata(),
        )
        changed = _record("A", "AAPL")
        changed["text"] = "Changed canonical evidence"
        source_path.write_text(json.dumps(changed) + "\n", encoding="utf-8")

        with pytest.raises(ValueError, match="Active source corpus"):
            load_validated_embedding_generation(
                generation_dir,
                active_corpus_dir=source,
            )


def test_loader_rejects_canonical_bm25_payload_drift() -> None:
    with _workspace() as root:
        source = root / "source"
        generations = root / "generations"
        _write_source(source, "AAPL", [_record("A", "AAPL")])
        generation_dir, _ = build_embedding_generation(
            source_dir=source,
            generations_root=generations,
            generation_id="generation-001",
            embedder=_FakeEmbedder(),
            metadata=_metadata(),
        )
        canonical_path = source / "AAPL" / "AAPL_chunks_embedded.jsonl"
        changed = _record("A", "AAPL")
        changed["text"] = "Stale or changed BM25 payload"
        changed["embedding"] = [0.0, 0.0]
        canonical_path.write_text(json.dumps(changed) + "\n", encoding="utf-8")

        with pytest.raises(ValueError, match="canonical BM25 payload"):
            load_validated_embedding_generation(
                generation_dir,
                active_corpus_dir=source,
            )


def test_generation_fingerprint_excludes_completed_at_and_itself() -> None:
    manifest = {"generation_id": "generation-001", "completed_at": "first"}
    first = compute_embedding_generation_fingerprint(manifest)
    manifest["completed_at"] = "second"
    manifest["embedding_generation_fingerprint"] = "ignored"

    assert compute_embedding_generation_fingerprint(manifest) == first
