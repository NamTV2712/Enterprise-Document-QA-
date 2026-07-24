import asyncio
import threading
import time
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from configs.settings import Settings
from src.api import app as app_module
from src.generation.generator import RAGResponse
from src.retrieval.retriever import RetrievedChunk


@pytest.fixture
def mock_pipeline():
    """Create a fake RAGPipeline without loading models or calling LLM APIs."""
    pipeline = MagicMock()
    fake_chunk = RetrievedChunk(
        chunk_id="AAPL_test_risk_factors_0",
        ticker="AAPL",
        section="risk_factors",
        filing_date="2025-10-31",
        score=0.75,
        text="Apple faces competition risks in all its markets.",
        citation="AAPL 10-K (filed 2025-10-31), Section: Risk Factors",
    )
    pipeline.query.return_value = RAGResponse(
        answer="Apple faces competition risks [Source 1].",
        retrieved_chunks=[fake_chunk],
        model_used="mock-model",
    )
    pipeline.cache.get_stats.return_value = {
        "total_requests": 0,
        "cache_hits": 0,
        "hit_rate": 0.0,
        "entries": 0,
        "max_entries": 500,
    }
    pipeline.memory.get_stats.return_value = {"active_sessions": 0, "total_turns": 0}
    return pipeline


@pytest.fixture
def mock_decomposer():
    decomposer = MagicMock()
    decomposer.run.return_value = MagicMock(
        answer="Comparison complete.",
        model_used="mock-model",
        was_decomposed=True,
        sub_queries=[],
        all_chunks=[],
    )
    return decomposer


@pytest.fixture
def client(mock_pipeline, mock_decomposer):
    """Inject the mock pipeline and avoid FastAPI lifespan model loading."""
    app_module._state.clear()
    app_module._state["pipeline"] = mock_pipeline
    app_module._state["decomposer"] = mock_decomposer
    app_module._state["store"] = MagicMock()
    test_client = TestClient(app_module.app)
    yield test_client
    app_module._state.clear()


def test_health_returns_ok_when_pipeline_ready(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["pipeline_ready"] is True
    assert data["memory"] == {"active_sessions": 0, "total_turns": 0}


def test_allowed_origins_parses_comma_separated_env_value() -> None:
    configured = Settings(
        allowed_origins=" http://localhost:3000, https://example.vercel.app, "
    )

    assert configured.allowed_origins_list == [
        "http://localhost:3000",
        "https://example.vercel.app",
    ]


def test_cors_preflight_allows_configured_frontend(client) -> None:
    response = client.options(
        "/query",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": (
                "content-type,ngrok-skip-browser-warning"
            ),
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "ngrok-skip-browser-warning" in response.headers[
        "access-control-allow-headers"
    ].lower()


@pytest.mark.parametrize(
    ("origin", "method", "headers"),
    [
        ("https://untrusted.example", "POST", "content-type"),
        ("http://localhost:3000", "PUT", "content-type"),
        ("http://localhost:3000", "POST", "authorization"),
    ],
)
def test_cors_preflight_rejects_unapproved_access(
    client, origin: str, method: str, headers: str
) -> None:
    response = client.options(
        "/query",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": headers,
        },
    )

    assert response.status_code == 400
    if origin != "http://localhost:3000":
        assert "access-control-allow-origin" not in response.headers


def test_supported_tickers_returns_expected_structure(client) -> None:
    response = client.get("/supported-tickers")

    assert response.status_code == 200
    data = response.json()
    assert "tickers" in data
    assert "sections" in data
    assert isinstance(data["tickers"], list)
    assert "AAPL" in data["tickers"]
    assert "GOOGL" in data["tickers"]
    assert "BRK-B" in data["tickers"]
    assert "financial_table" in data["sections"]


def test_query_returns_answer_and_sources(client, mock_pipeline) -> None:
    response = client.post(
        "/query",
        json={
            "question": "What are Apple's main risk factors?",
            "ticker": "AAPL",
            "section": "risk_factors",
            "top_k": 5,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "Apple faces competition risks" in data["answer"]
    assert data["model_used"] == "mock-model"
    assert data["num_chunks_retrieved"] == 1
    assert len(data["sources"]) == 1
    assert data["sources"][0]["citation"] == (
        "AAPL 10-K (filed 2025-10-31), Section: Risk Factors"
    )

    mock_pipeline.query.assert_called_once()
    call_kwargs = mock_pipeline.query.call_args.kwargs
    assert call_kwargs["question"] == "What are Apple's main risk factors?"
    assert call_kwargs["ticker"] == "AAPL"
    assert call_kwargs["section"] == "risk_factors"
    assert call_kwargs["top_k"] == 5


def test_query_rejects_too_short_question(client) -> None:
    response = client.post("/query", json={"question": "Hi"})

    assert response.status_code == 422


def test_query_rejects_invalid_ticker_format(client) -> None:
    response = client.post(
        "/query",
        json={
            "question": "What are the risks for this company?",
            "ticker": "invalid-ticker-123",
        },
    )

    assert response.status_code == 422


def test_query_accepts_dash_ticker(client, mock_pipeline) -> None:
    response = client.post(
        "/query",
        json={
            "question": "What are Berkshire Hathaway's risks?",
            "ticker": "BRK-B",
        },
    )

    assert response.status_code == 200
    assert mock_pipeline.query.call_args.kwargs["ticker"] == "BRK-B"


def test_query_returns_503_when_pipeline_not_ready() -> None:
    app_module._state.clear()
    test_client = TestClient(app_module.app)

    response = test_client.post(
        "/query",
        json={"question": "What are Apple's risks?"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "The pipeline is not ready yet"


def test_query_error_does_not_leak_exception_details(client, mock_pipeline) -> None:
    secret = "Database connection: postgres://user:secret@internal-host/db"
    mock_pipeline.query.side_effect = RuntimeError(secret)

    response = client.post(
        "/query",
        json={"question": "Test question for secure error handling"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == app_module.INTERNAL_ERROR_DETAIL
    assert "secret" not in response.text
    assert "postgres://" not in response.text


def test_decomposed_error_does_not_leak_exception_details(
    client, mock_decomposer
) -> None:
    mock_decomposer.run.side_effect = RuntimeError(
        "Private model path: /srv/models/internal-secret"
    )

    response = client.post(
        "/query/decomposed",
        json={"question": "Compare Apple and Microsoft revenue"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == app_module.INTERNAL_ERROR_DETAIL
    assert "internal-secret" not in response.text
    assert "/srv/models" not in response.text


def test_stream_error_does_not_leak_exception_details(client, mock_pipeline) -> None:
    mock_pipeline.query_stream.side_effect = RuntimeError(
        "Provider token: super-secret-provider-token"
    )

    response = client.post(
        "/query/stream",
        json={"question": "What are Apple's main risk factors?"},
    )

    assert response.status_code == 200
    assert app_module.INTERNAL_ERROR_DETAIL in response.text
    assert "super-secret-provider-token" not in response.text


def test_health_responds_while_decomposed_query_runs(mock_pipeline) -> None:
    decomposer_started = threading.Event()
    release_decomposer = threading.Event()
    decomposer = MagicMock()
    result = MagicMock(
        answer="Comparison complete.",
        model_used="mock-model",
        was_decomposed=True,
        sub_queries=[],
        all_chunks=[],
    )

    def blocking_run(**kwargs):
        decomposer_started.set()
        release_decomposer.wait(timeout=2.0)
        return result

    decomposer.run.side_effect = blocking_run
    app_module._state.clear()
    app_module._state["pipeline"] = mock_pipeline
    app_module._state["decomposer"] = decomposer

    async def run_concurrent_requests() -> tuple[httpx.Response, httpx.Response, float]:
        transport = httpx.ASGITransport(app=app_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
            started_at = time.perf_counter()
            decomposed_task = asyncio.create_task(
                async_client.post(
                    "/query/decomposed",
                    json={
                        "question": "Compare Apple and Microsoft revenue",
                        "ticker": "AAPL",
                        "section": "financial_table",
                        "top_k": 3,
                        "session_id": "concurrency-test",
                    },
                )
            )
            while not decomposer_started.is_set():
                if time.perf_counter() - started_at > 1.0:
                    raise AssertionError("Decomposed query did not start")
                await asyncio.sleep(0.005)
            health_response = await async_client.get("/health")
            health_elapsed = time.perf_counter() - started_at
            release_decomposer.set()
            decomposed_response = await decomposed_task
            return decomposed_response, health_response, health_elapsed

    safety_release = threading.Timer(1.5, release_decomposer.set)
    safety_release.start()
    try:
        decomposed_response, health_response, health_elapsed = asyncio.run(
            run_concurrent_requests()
        )
    finally:
        release_decomposer.set()
        safety_release.cancel()
        app_module._state.clear()

    assert health_response.status_code == 200
    assert health_response.json()["pipeline_ready"] is True
    assert health_elapsed < 0.75
    assert decomposed_response.status_code == 200
    decomposer.run.assert_called_once_with(
        question="Compare Apple and Microsoft revenue",
        top_k=3,
        ticker="AAPL",
        section="financial_table",
        session_id="concurrency-test",
    )


def test_cache_stats_endpoint(client) -> None:
    response = client.get("/cache/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["hit_rate"] == 0.0
    assert data["max_entries"] == 500
