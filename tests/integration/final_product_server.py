"""TEST-004 real application bootstrap/HTTP/SQLite with offline RAG dependencies.

No route, access dependency, database, migration, job coordinator or telemetry
handler is replaced. The production lifespan runs. Only model/corpus/provider
dependencies use declared synthetic data, never developer artifacts or secrets.
"""

from __future__ import annotations

import os
import sys
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
TOKEN = "test004-synthetic-local-token-0123456789abcdef"


def install_runtime_dependencies(stack: ExitStack, directory: Path):
    # The legacy fixture module initializes subprocess defaults at import.
    # Reusing its dependencies must not leak those defaults into pytest peers.
    with patch.dict(os.environ):
        from tests.integration import harness_server as fixtures
    from src.api import app as application
    from src.evaluation.frozen_job_plan import registered_artifact_bytes
    from src.evaluation.job_service import EvaluationJobService
    from tests.test_evaluation_jobs import _artifact
    from tests.test_native_evaluation_analytics_api import _case, _publish

    directory.mkdir(parents=True, exist_ok=True)
    stack.enter_context(patch.dict(application._state, {}, clear=True))
    artifacts = directory / "artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / "test004-phase1.json").write_bytes(_artifact())
    publications = directory / "publications"
    publications.mkdir(exist_ok=True)
    _publish(publications, "test004-baseline", faith=0.0,
             cases=[_case(faith=0.0, answer="Revenue was 10 [Source 1].")])
    _publish(publications, "test004-candidate", faith=0.5,
             cases=[_case(faith=0.5, answer="Insufficient context.")])
    stack.enter_context(patch.object(application.settings, "data_public_evaluations_dir", publications))
    closed = []
    store = SimpleNamespace(close=lambda: closed.append(True))
    from rank_bm25 import BM25Okapi
    from src.retrieval.hybrid_retriever import HybridRetriever, _tokenize

    class OfflineRetriever(fixtures.FakeRetriever):
        tokenize_query = HybridRetriever.tokenize_query
        bm25_scores = HybridRetriever.bm25_scores
        bm25_terms_present = HybridRetriever.bm25_terms_present

        def __init__(self):
            super().__init__()
            self.bm25 = BM25Okapi([_tokenize(chunk["text"]) for chunk in self._all_chunks])

    def pipeline(**_kwargs):
        result = fixtures.FakePipeline()
        result.retriever = OfflineRetriever()
        return result

    for name, replacement in {
        "VectorStore": lambda **_kwargs: store,
        "load_retrieval_chunks": lambda *_args: list(fixtures.HARNESS_DOCUMENT_CHUNKS),
        "Embedder": lambda **_kwargs: SimpleNamespace(),
        "HybridRetriever": lambda **_kwargs: OfflineRetriever(),
        "Generator": fixtures.FakeGenerator,
        "RAGPipeline": pipeline,
    }.items():
        stack.enter_context(patch.object(application, name, replacement))

    def evaluation_service(repository):
        return EvaluationJobService(
            repository,
            artifact_loader=lambda identity: registered_artifact_bytes(identity, directory=artifacts),
            provider_factory=lambda _model: (
                lambda _prompt: "Apple's total net sales in fiscal 2024 were 391,035 million [Source 1].",
                lambda _prompt: {"faithfulness": 0.0, "answer_relevancy": 1.0, "context_precision": 0.5},
            ),
        )

    stack.enter_context(patch.object(application, "EvaluationJobService", evaluation_service))
    return application, closed


def main() -> None:
    import tempfile

    directory = Path(os.environ.get("TEST004_RUNTIME_DIR") or tempfile.mkdtemp(prefix="edqa-test004-")).resolve()
    port = int(os.environ.get("TEST004_API_PORT", "8778"))
    # Pin every credential input before Settings imports, including inherited
    # environment variables. These are intentionally synthetic test sentinels.
    for key in ("GROQ_API_KEY", "GROQ_API_KEY_FALL_BACK"):
        os.environ[key] = "test004-offline-synthetic-provider-key"
    os.environ.update({
        "GROQ_KEY_POLICY": "key5_only", "QDRANT_MODE": "local",
        "QDRANT_CLOUD_URL": "", "QDRANT_CLOUD_API_KEY": "",
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "WORKSPACE_MODE": os.environ.get("TEST004_WORKSPACE_MODE", "local"),
        "LOCAL_WORKSPACE_TOKEN": TOKEN, "ENABLE_WORKSPACE_EXECUTION": "true",
        "WORKSPACE_DB_PATH": str(directory / "workspace.sqlite3"),
        "WORKSPACE_RUNS_DIR": str(directory / "runs"),
        "LOCAL_WORKSPACE_ALLOWED_HOSTS": f"127.0.0.1:{port}",
        "LOCAL_WORKSPACE_ALLOWED_ORIGINS": "http://localhost:4177",
        "ALLOWED_ORIGINS": "http://localhost:4177",
        "HARNESS_TEMP_DIR": str(directory / "dependencies"),
        "LLM_RATE_LIMIT_BURST": "1000/minute", "LLM_RATE_LIMIT_DAILY": "10000/day",
    })
    from configs.offline_guard import offline_socket_guard
    import uvicorn

    with offline_socket_guard(), ExitStack() as stack:
        application, _closed = install_runtime_dependencies(stack, directory)
        uvicorn.run(application.app, host="127.0.0.1", port=port,
                    proxy_headers=False, access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
