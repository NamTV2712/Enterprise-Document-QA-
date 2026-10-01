"""API-006 model and dataset registry contracts.

All checks are hermetic. Registry reads inspect only injected configuration,
already-loaded runtime objects, catalog metadata, and local manifest bytes.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api import access
from src.api import app as app_module
from src.api.access import AccessCapability, AccessGrant, require_execution_access
from src.api.catalog import build_stats
from src.api.registry import RegistryService
from src.evaluation.test_set import TestCase as EvaluationCase
from src.retrieval.index_manifest import compute_corpus_fingerprint


SECRET = "secret-provider-key-that-must-not-appear"
PRIVATE_PATH = "C:/Users/example/private/model-cache"


def _settings(tmp_path, *, manifest: dict | str | None = None):
    manifest_path = tmp_path / "index-manifest.json"
    if isinstance(manifest, dict):
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    elif isinstance(manifest, str):
        manifest_path.write_text(manifest, encoding="utf-8")
    return SimpleNamespace(
        embedding_model_id="fixture/embedding",
        embedding_model_revision="embedding-revision",
        reranker_model_id="fixture/reranker",
        reranker_model_revision="reranker-revision",
        qdrant_index_manifest_path=manifest_path,
        groq_key_policy="pool",
        groq_api_key=SECRET,
        groq_api_key_fall_back="",
        model_cache_path=PRIVATE_PATH,
    )


def _chunks() -> list[dict]:
    return [
        {
            "chunk_id": f"chunk-{index}",
            "text": f"Fixture text {index}",
            "ticker": "AAPL" if index < 4 else "MSFT",
            "section": "business",
            "accession_number": "1" if index < 4 else "2",
            "chunk_index": index,
        }
        for index in range(7)
    ]


def _manifest(*, point_count: int = 7, corpus_fingerprint: str | None = None) -> dict:
    return {
        "schema_version": 2,
        "collection_name": "sec_filings",
        "corpus_fingerprint": corpus_fingerprint or compute_corpus_fingerprint(_chunks()),
        "point_count": point_count,
        "embedding_model_id": "fixture/embedding",
        "embedding_model_revision": "embedding-revision",
        "vector_dimension": 768,
        "distance_metric": "cosine",
        "build_version": "index-builder-v2-manifest",
        "snapshot_id": "sha256:" + "b" * 64,
        "embedding_generation_id": "generation-001",
        "embedding_generation_fingerprint": "sha256:" + "c" * 64,
    }


def _catalog() -> list[dict]:
    return [
        {
            "document_id": "AAPL:1",
            "ticker": "AAPL",
            "filing_date": "2025-10-31",
            "report_date": "2025-09-27",
            "sections": ["business", "risk_factors"],
            "chunk_count": 4,
        },
        {
            "document_id": "MSFT:2",
            "ticker": "MSFT",
            "filing_date": "2024-07-30",
            "report_date": "2024-06-30",
            "sections": ["business", "mdna"],
            "chunk_count": 3,
        },
    ]


def _pipeline() -> SimpleNamespace:
    embedder = SimpleNamespace(
        model_name="fixture/embedding",
        model_revision="embedding-revision",
        model=MagicMock(),
        device="cpu",
    )
    cross_encoder = MagicMock()
    retriever = SimpleNamespace(
        embedder=embedder,
        cross_encoder_model="fixture/reranker",
        cross_encoder_revision="reranker-revision",
        cross_encoder=cross_encoder,
        _all_chunks=_chunks(),
    )
    generator = SimpleNamespace(
        model="openai/gpt-oss-120b",
        clients=[MagicMock()],
    )
    return SimpleNamespace(retriever=retriever, generator=generator)


def _evaluation_cases() -> list[EvaluationCase]:
    return [
        EvaluationCase(
            question="Question A",
            category="fact_lookup",
            ticker="AAPL",
            section=None,
            ground_truth="Answer A",
            priority=1,
        ),
        EvaluationCase(
            question="Question B",
            category="comparative",
            ticker=None,
            section="business",
            ground_truth="Answer B",
            priority=2,
        ),
    ]


def _service(tmp_path, *, manifest: dict | str | None = None, state=None, rows=None):
    runtime_state = {"pipeline": _pipeline()} if state is None else state
    catalog_rows = _catalog() if rows is None else rows
    return RegistryService(
        settings=_settings(tmp_path, manifest=manifest),
        get_state=lambda: runtime_state,
        get_catalog_rows=lambda: catalog_rows,
        get_chunks=_chunks,
        evaluation_cases=_evaluation_cases(),
    )


def test_model_registry_has_stable_roles_order_and_truthful_states(tmp_path) -> None:
    service = _service(tmp_path, manifest=_manifest())

    items = service.list_models()

    assert [item.id for item in items] == ["generator", "embedding", "reranker"]
    assert [item.role for item in items] == ["generator", "embedding", "reranker"]
    assert all(item.configuration_status == "configured" for item in items)
    assert all(item.load_status == "loaded" for item in items)
    assert items[0].availability_status == "unknown"
    assert "not probed" in (items[0].availability_reason or "").lower()
    assert [item.availability_status for item in items[1:]] == [
        "available",
        "available",
    ]
    assert service.list_models(role="embedding") == [items[1]]


def test_model_registry_distinguishes_missing_config_from_not_loaded(tmp_path) -> None:
    settings = _settings(tmp_path)
    settings.embedding_model_id = ""
    settings.embedding_model_revision = ""
    service = RegistryService(
        settings=settings,
        get_state=lambda: {},
        get_catalog_rows=lambda: [],
        get_chunks=lambda: [],
        evaluation_cases=[],
    )

    entries = {entry.id: entry for entry in service.list_models()}

    assert entries["embedding"].configuration_status == "not_configured"
    assert entries["embedding"].load_status == "not_loaded"
    assert entries["embedding"].availability_status == "unavailable"
    assert entries["embedding"].configured_revision is None
    assert entries["reranker"].configuration_status == "configured"
    assert entries["reranker"].load_status == "not_loaded"
    assert entries["reranker"].availability_status == "unknown"


def test_registry_reads_never_execute_models_or_expose_secrets_or_paths(tmp_path) -> None:
    pipeline = _pipeline()
    pipeline.retriever.embedder.model.encode.side_effect = AssertionError("embedding ran")
    pipeline.retriever.cross_encoder.predict.side_effect = AssertionError("reranker ran")
    pipeline.generator.clients[0].chat.completions.create.side_effect = AssertionError(
        "provider ran"
    )
    service = _service(
        tmp_path,
        manifest=_manifest(),
        state={"pipeline": pipeline},
    )

    payload = json.dumps(
        {
            "models": [item.model_dump(mode="json") for item in service.list_models()],
            "datasets": [item.model_dump(mode="json") for item in service.list_datasets()],
        }
    )

    assert SECRET not in payload
    assert PRIVATE_PATH not in payload
    assert "authorization" not in payload.casefold()
    pipeline.retriever.embedder.model.encode.assert_not_called()
    pipeline.retriever.cross_encoder.predict.assert_not_called()
    pipeline.generator.clients[0].chat.completions.create.assert_not_called()


def test_secret_looking_identity_and_manifest_fields_are_redacted(tmp_path) -> None:
    manifest_secret = "gsk_secret-looking-manifest-value"
    unsafe_manifest = _manifest()
    unsafe_manifest["collection_name"] = manifest_secret
    settings = _settings(tmp_path, manifest=unsafe_manifest)
    settings.embedding_model_id = PRIVATE_PATH
    pipeline = _pipeline()
    pipeline.retriever.embedder.model_name = PRIVATE_PATH
    service = RegistryService(
        settings=settings,
        get_state=lambda: {"pipeline": pipeline},
        get_catalog_rows=_catalog,
        get_chunks=_chunks,
        evaluation_cases=_evaluation_cases(),
    )

    embedding = service.get_model("embedding")
    corpus = service.get_dataset("serving-corpus")
    payload = json.dumps(
        {
            "model": embedding.model_dump(mode="json"),
            "dataset": corpus.model_dump(mode="json"),
        }
    )

    assert embedding.configuration_status == "configured"
    assert embedding.configured_model_id is None
    assert embedding.runtime_model_id is None
    assert embedding.availability_status == "unavailable"
    assert corpus.provenance.status == "invalid"
    assert SECRET not in payload
    assert manifest_secret not in payload
    assert PRIVATE_PATH not in payload


def test_runtime_identity_test_is_deterministic_and_provider_free(tmp_path) -> None:
    pipeline = _pipeline()
    service = _service(
        tmp_path,
        manifest=_manifest(),
        state={"pipeline": pipeline},
    )

    result = service.run_model_test("generator", "runtime_identity")

    assert result.result == "passed"
    assert result.provider_executed is False
    assert [check.id for check in result.checks] == [
        "configured_identity",
        "runtime_loaded",
        "runtime_identity",
        "runtime_revision",
    ]
    assert result.checks[-1].status == "unavailable"
    pipeline.generator.clients[0].chat.completions.create.assert_not_called()


def test_dataset_registry_reuses_catalog_counts_and_manifest_binding(tmp_path) -> None:
    rows = _catalog()
    service = _service(tmp_path, manifest=_manifest(), rows=rows)

    summaries = service.list_datasets()
    corpus = service.get_dataset("serving-corpus")
    evaluation = service.get_dataset("evaluation-test-set")

    assert [item.id for item in summaries] == [
        "serving-corpus",
        "evaluation-test-set",
    ]
    assert service.list_datasets(kind="evaluation") == [summaries[1]]
    expected = build_stats(rows)
    assert corpus.coverage.documents == expected["documents"]
    assert corpus.coverage.companies == expected["companies"]
    assert corpus.coverage.chunks == expected["chunks"]
    assert corpus.coverage.filing_years.earliest == expected["filing_dates"]["earliest"]
    assert corpus.coverage.filing_years.latest == expected["filing_dates"]["latest"]
    assert corpus.provenance.status == "consistent"
    assert corpus.provenance.point_count == expected["chunks"]
    assert corpus.availability == "available"
    assert evaluation.coverage.cases == 2
    assert [(entry.key, entry.count) for entry in evaluation.coverage.categories] == [
        ("comparative", 1),
        ("fact_lookup", 1),
    ]
    assert evaluation.revision.startswith("sha256:")


@pytest.mark.parametrize(
    ("manifest", "status", "reason_code"),
    [
        (None, "missing", "index_manifest_missing"),
        ("not-json", "invalid", "index_manifest_invalid"),
        (_manifest(point_count=99), "mismatch", "index_manifest_mismatch"),
        (
            _manifest(corpus_fingerprint="sha256:" + "d" * 64),
            "mismatch",
            "index_manifest_mismatch",
        ),
    ],
)
def test_dataset_registry_reports_missing_invalid_and_mismatched_manifests(
    tmp_path,
    manifest,
    status: str,
    reason_code: str,
) -> None:
    service = _service(tmp_path, manifest=manifest)

    corpus = service.get_dataset("serving-corpus")

    assert corpus.availability == "degraded"
    assert corpus.provenance.status == status
    assert corpus.provenance.reason_code == reason_code
    assert corpus.coverage.documents == 2


def test_unavailable_catalog_is_not_reported_as_an_empty_dataset(tmp_path) -> None:
    service = RegistryService(
        settings=_settings(tmp_path, manifest=_manifest()),
        get_state=lambda: {},
        get_catalog_rows=lambda: None,
        get_chunks=lambda: None,
        evaluation_cases=_evaluation_cases(),
    )

    corpus = service.get_dataset("serving-corpus")

    assert corpus.availability == "unavailable"
    assert corpus.record_count is None
    assert corpus.coverage is None
    assert corpus.reason_code == "catalog_unavailable"


def test_genuinely_empty_sources_remain_explicit_registry_entries(tmp_path) -> None:
    service = RegistryService(
        settings=_settings(tmp_path),
        get_state=lambda: {},
        get_catalog_rows=lambda: [],
        get_chunks=lambda: [],
        evaluation_cases=[],
    )

    corpus = service.get_dataset("serving-corpus")
    evaluation = service.get_dataset("evaluation-test-set")

    assert corpus.availability == "degraded"
    assert corpus.reason_code == "empty_catalog"
    assert corpus.record_count == 0
    assert corpus.coverage.documents == 0
    assert evaluation.availability == "available"
    assert evaluation.record_count == 0
    assert evaluation.coverage.cases == 0


def test_registry_http_contract_and_access_classification(tmp_path, monkeypatch) -> None:
    manifest_path = tmp_path / "index-manifest.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
    pipeline = _pipeline()
    app_module._state.clear()
    app_module._state.update(
        {"pipeline": pipeline, "document_rows": _catalog()}
    )
    monkeypatch.setattr(app_module.settings, "qdrant_index_manifest_path", manifest_path)
    monkeypatch.setattr(app_module.settings, "embedding_model_id", "fixture/embedding")
    monkeypatch.setattr(
        app_module.settings, "embedding_model_revision", "embedding-revision"
    )
    monkeypatch.setattr(app_module.settings, "reranker_model_id", "fixture/reranker")
    monkeypatch.setattr(
        app_module.settings, "reranker_model_revision", "reranker-revision"
    )
    app_module.app.dependency_overrides[require_execution_access] = lambda: AccessGrant(
        frozenset(
            {
                AccessCapability.PUBLIC_PROVIDER_FREE,
                AccessCapability.LOCAL_WORKSPACE,
                AccessCapability.EXECUTION_JOBS,
            }
        )
    )
    try:
        client = TestClient(app_module.app)
        models = client.get("/models")
        datasets = client.get("/datasets")
        detail = client.get("/datasets/serving-corpus")
        tested = client.post(
            "/models/embedding/tests",
            json={"test_type": "runtime_identity"},
        )
        unknown = client.get("/datasets/not-a-dataset")
    finally:
        app_module.app.dependency_overrides.clear()
        app_module._state.clear()

    assert models.status_code == 200
    assert list(models.json()) == ["items", "total"]
    assert [item["id"] for item in models.json()["items"]] == [
        "generator",
        "embedding",
        "reranker",
    ]
    assert datasets.status_code == 200
    assert detail.status_code == 200
    assert tested.status_code == 200
    assert tested.json()["provider_executed"] is False
    assert unknown.status_code == 404
    assert unknown.json() == {"detail": "Dataset registry entry not found"}


def test_model_test_endpoint_remains_execution_gated_in_public_mode(
    monkeypatch,
) -> None:
    monkeypatch.setattr(access.settings, "workspace_mode", "public")
    monkeypatch.setattr(access.settings, "enable_workspace_execution", False)

    response = TestClient(app_module.app).post(
        "/models/embedding/tests",
        json={"test_type": "runtime_identity"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Local workspace capability is unavailable"
    }
