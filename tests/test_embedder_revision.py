from types import SimpleNamespace

import src.retrieval.embedder as embedder_module


def test_embedder_passes_pinned_revision_to_sentence_transformer(monkeypatch) -> None:
    calls = []

    class FakeSentenceTransformer:
        def __init__(self, model_name, **kwargs):
            calls.append((model_name, kwargs))

        def get_embedding_dimension(self):
            return 768

    monkeypatch.setattr(embedder_module, "SentenceTransformer", FakeSentenceTransformer)
    monkeypatch.setattr(embedder_module, "resolve_torch_device", lambda device: "cpu")

    embedder = embedder_module.Embedder(
        model_name="embedding-model",
        revision="model-commit",
    )

    assert embedder.model_name == "embedding-model"
    assert embedder.model_revision == "model-commit"
    assert calls == [
        (
            "embedding-model",
            {
                "revision": "model-commit",
                "trust_remote_code": True,
                "device": "cpu",
            },
        )
    ]
    assert embedder.normalize_embeddings is False
    assert embedder.embedding_dtype == "float32"


def test_embedder_passes_declared_normalization_policy_to_encode(monkeypatch) -> None:
    encode_calls = []

    class FakeArray:
        def __init__(self, value):
            self.value = value

        def tolist(self):
            return self.value

    class FakeSentenceTransformer:
        def __init__(self, model_name, **kwargs):
            pass

        def get_embedding_dimension(self):
            return 2

        def encode(self, value, **kwargs):
            encode_calls.append((value, kwargs))
            if isinstance(value, list):
                return FakeArray([[0.1, 0.2] for _ in value])
            return FakeArray([0.1, 0.2])

    monkeypatch.setattr(embedder_module, "SentenceTransformer", FakeSentenceTransformer)
    monkeypatch.setattr(embedder_module, "resolve_torch_device", lambda device: "cpu")
    embedder = embedder_module.Embedder(
        model_name="embedding-model",
        revision="model-commit",
    )

    embedder.embed_documents(["document"])
    embedder.embed_query("question")

    assert encode_calls[0][1]["normalize_embeddings"] is False
    assert encode_calls[1][1]["normalize_embeddings"] is False
