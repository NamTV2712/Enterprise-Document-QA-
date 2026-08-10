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
