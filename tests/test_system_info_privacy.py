"""Public system metadata must not disclose runtime paths or unsafe values."""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.system import create_system_router


def _client(embedding: object, reranker: object) -> TestClient:
    pipeline = SimpleNamespace(retriever=SimpleNamespace(
        embedder=SimpleNamespace(model_name=embedding), cross_encoder_model=reranker,
    ))
    app = FastAPI()
    app.include_router(create_system_router(lambda: pipeline, lambda: {}, lambda: "0.1.0"))
    return TestClient(app)


@pytest.mark.parametrize("unsafe", [
    "C:/Users/SyntheticOperator/model-cache",
    r"C:\Users\SyntheticOperator\model-cache",
    "/private/runtime/model-cache",
    r"\\synthetic-server\private\model-cache",
    "~/private/model-cache",
    "../private/model-cache",
    "file:///private/model-cache",
    "https://synthetic.invalid/private-model",
    "gsk_synthetic_credential_only",
    "sk-synthetic-credential-only",
    "ghp_synthetic_credential_only",
    "Bearer synthetic-credential-only",
    "model\nprivate-runtime-detail",
    "x" * 257,
])
def test_public_system_info_projects_unsafe_model_and_build_values(
    unsafe: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_REVISION", unsafe)
    monkeypatch.setenv("BUILD_VERSION", unsafe)
    with _client(unsafe, unsafe) as client:
        response = client.get("/system/info")
    assert response.status_code == 200
    payload = response.json()
    assert payload["retrieval"]["embedding_model"] is None
    assert payload["retrieval"]["reranker_model"] is None
    assert payload["build"] == {}
    assert unsafe not in response.text


def test_public_system_info_preserves_safe_existing_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_REVISION", "abcdef0123456789")
    monkeypatch.setenv("BUILD_VERSION", "release-2026.09")
    with _client("nomic-ai/nomic-embed-text-v1.5", "cross-encoder/ms-marco-MiniLM-L-6-v2") as client:
        response = client.get("/system/info")
    assert response.status_code == 200
    payload = response.json()
    assert payload["retrieval"]["embedding_model"] == "nomic-ai/nomic-embed-text-v1.5"
    assert payload["retrieval"]["reranker_model"] == "cross-encoder/ms-marco-MiniLM-L-6-v2"
    assert payload["build"] == {"GIT_REVISION": "abcdef0123456789", "BUILD_VERSION": "release-2026.09"}
    assert payload["retrieval"]["default"] == "hybrid_rerank"
    assert payload["api_version"] == "0.1.0"
