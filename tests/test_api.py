import asyncio
import inspect
import threading
import time
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from configs.settings import Settings
from src.api import app as app_module
from src.generation.generator import RAGResponse
from src.memory.conversation_memory import Turn
from src.retrieval.retriever import RetrievedChunk


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Keep in-memory rate-limit counters isolated between tests."""
    app_module.limiter.reset()
    yield
    app_module.limiter.reset()


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


def test_health_live_and_ready_have_distinct_semantics() -> None:
    app_module._state.clear()
    test_client = TestClient(app_module.app)

    live_response = test_client.get("/health/live")
    ready_response = test_client.get("/health/ready")
    legacy_response = test_client.get("/health")

    assert live_response.status_code == 200
    assert live_response.json() == {"status": "ok"}
    assert ready_response.status_code == 503
    assert ready_response.json()["detail"] == "The pipeline is not ready yet"
    assert legacy_response.status_code == 200
    assert legacy_response.json()["pipeline_ready"] is False


def test_health_ready_returns_pipeline_stats(client) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["pipeline_ready"] is True
    assert response.json()["memory"] == {"active_sessions": 0, "total_turns": 0}


def test_allowed_origins_parses_comma_separated_env_value() -> None:
    configured = Settings(
        allowed_origins=" http://localhost:3000, https://example.vercel.app, "
    )

    assert configured.allowed_origins_list == [
        "http://localhost:3000",
        "https://example.vercel.app",
    ]


def test_cloud_retrieval_chunks_load_from_qdrant_payloads() -> None:
    store = MagicMock(mode="cloud")
    store.load_all_chunks.return_value = [{"chunk_id": "cloud-chunk"}]

    assert app_module._load_retrieval_chunks(store) == [
        {"chunk_id": "cloud-chunk"}
    ]
    store.load_all_chunks.assert_called_once_with()


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


def test_health_responds_while_supported_tickers_loads(
    mock_pipeline, monkeypatch
) -> None:
    main_thread_id = threading.get_ident()
    loader_thread_ids = []
    loader_started = threading.Event()
    release_loader = threading.Event()

    def blocking_loader() -> list[str]:
        loader_thread_ids.append(threading.get_ident())
        loader_started.set()
        release_loader.wait(timeout=2.0)
        return ["AAPL", "MSFT"]

    monkeypatch.setattr(app_module, "_load_supported_tickers", blocking_loader)
    app_module._state.clear()
    app_module._state["pipeline"] = mock_pipeline

    async def run_concurrent_requests() -> tuple[httpx.Response, httpx.Response, float]:
        transport = httpx.ASGITransport(app=app_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
            started_at = time.perf_counter()
            tickers_task = asyncio.create_task(async_client.get("/supported-tickers"))
            while not loader_started.is_set():
                if time.perf_counter() - started_at > 1.0:
                    raise AssertionError("Supported ticker loader did not start")
                await asyncio.sleep(0.005)
            health_response = await async_client.get("/health")
            health_elapsed = time.perf_counter() - started_at
            release_loader.set()
            tickers_response = await tickers_task
            return tickers_response, health_response, health_elapsed

    safety_release = threading.Timer(1.5, release_loader.set)
    safety_release.start()
    try:
        tickers_response, health_response, health_elapsed = asyncio.run(
            run_concurrent_requests()
        )
    finally:
        release_loader.set()
        safety_release.cancel()
        app_module._state.clear()

    assert health_response.status_code == 200
    assert health_elapsed < 0.75
    assert tickers_response.status_code == 200
    assert tickers_response.json()["tickers"] == ["AAPL", "MSFT"]
    assert loader_thread_ids[0] != main_thread_id


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


def test_session_history_returns_full_assistant_message(client, mock_pipeline) -> None:
    """Historical answers must not be truncated when the UI reloads a session."""
    long_answer = "A" * 500
    mock_pipeline.memory.get_history.return_value = [
        Turn(
            user_message="What are the main risks?",
            assistant_message=long_answer,
            rewritten_query="What are Apple's main risk factors?",
        )
    ]

    response = client.get("/session/history-regression/history")

    assert response.status_code == 200
    assert response.json()["turns"][0]["assistant"] == long_answer
    assert len(response.json()["turns"][0]["assistant"]) == 500


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


@pytest.mark.parametrize(
    ("path", "worker_name", "question"),
    [
        ("/query", "pipeline", "What are Apple's main risk factors?"),
        (
            "/query/decomposed",
            "decomposer",
            "Compare Apple and Microsoft revenue",
        ),
    ],
)
def test_non_streaming_query_timeout_returns_504(
    client,
    mock_pipeline,
    mock_decomposer,
    monkeypatch,
    path: str,
    worker_name: str,
    question: str,
) -> None:
    worker_started = threading.Event()
    release_worker = threading.Event()

    def blocking_worker(**kwargs):
        worker_started.set()
        release_worker.wait(timeout=2.0)

    worker = mock_pipeline.query if worker_name == "pipeline" else mock_decomposer.run
    worker.side_effect = blocking_worker
    monkeypatch.setattr(app_module, "QUERY_TIMEOUT_SECONDS", 0.05)

    started_at = time.perf_counter()
    try:
        response = client.post(path, json={"question": question})
        elapsed = time.perf_counter() - started_at
    finally:
        release_worker.set()

    assert worker_started.is_set()
    assert response.status_code == 504
    assert response.json()["detail"] == app_module.QUERY_TIMEOUT_DETAIL
    assert elapsed < 0.75


def test_llm_routes_share_one_burst_limit(client) -> None:
    payload = {"question": "What are Apple's main risk factors?"}
    for _ in range(9):
        assert client.post("/query", json=payload).status_code == 200

    assert client.post("/query/stream", json=payload).status_code == 200
    blocked = client.post(
        "/query/decomposed",
        json={"question": "Compare Apple and Microsoft revenue"},
    )

    assert blocked.status_code == 429
    assert "Rate limit exceeded" in blocked.json()["error"]


def test_decomposed_query_has_lower_endpoint_limit(client) -> None:
    payload = {"question": "Compare Apple and Microsoft revenue"}
    for _ in range(5):
        assert client.post("/query/decomposed", json=payload).status_code == 200

    blocked = client.post("/query/decomposed", json=payload)

    assert blocked.status_code == 429


def test_rate_limits_are_isolated_by_client_ip(mock_pipeline, mock_decomposer) -> None:
    app_module._state.clear()
    app_module._state["pipeline"] = mock_pipeline
    app_module._state["decomposer"] = mock_decomposer
    payload = {"question": "What are Apple's main risk factors?"}

    async def run_requests() -> tuple[httpx.Response, httpx.Response]:
        first_transport = httpx.ASGITransport(
            app=app_module.app,
            client=("198.51.100.10", 50000),
        )
        second_transport = httpx.ASGITransport(
            app=app_module.app,
            client=("198.51.100.20", 50000),
        )
        async with (
            httpx.AsyncClient(
                transport=first_transport,
                base_url="http://test",
            ) as first_client,
            httpx.AsyncClient(
                transport=second_transport,
                base_url="http://test",
            ) as second_client,
        ):
            for _ in range(10):
                response = await first_client.post("/query", json=payload)
                assert response.status_code == 200
            blocked = await first_client.post("/query", json=payload)
            allowed = await second_client.post("/query", json=payload)
            return blocked, allowed

    try:
        blocked, allowed = asyncio.run(run_requests())
    finally:
        app_module._state.clear()

    assert blocked.status_code == 429
    assert allowed.status_code == 200


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


def test_pipeline_stream_error_event_is_sanitized(client, mock_pipeline) -> None:
    mock_pipeline.query_stream.return_value = iter(
        [("error", "Database password: leaked-secret")]
    )

    response = client.post(
        "/query/stream",
        json={"question": "What are Apple's main risk factors?"},
    )

    assert response.status_code == 200
    assert app_module.INTERNAL_ERROR_DETAIL in response.text
    assert "leaked-secret" not in response.text


def test_stream_disconnect_sets_cancellation_event(mock_pipeline) -> None:
    captured_cancel_event = {}
    producer_stopped = threading.Event()

    def cancellable_stream(**kwargs):
        cancel_event = kwargs["cancel_event"]
        captured_cancel_event["event"] = cancel_event
        try:
            yield ("sources", [])
            while not cancel_event.is_set():
                time.sleep(0.005)
                yield ("token", "unused")
        finally:
            producer_stopped.set()

    mock_pipeline.query_stream.side_effect = cancellable_stream
    app_module._state.clear()
    app_module._state["pipeline"] = mock_pipeline
    http_request = MagicMock()
    http_request.is_disconnected = AsyncMock(side_effect=[False, True])

    async def consume_stream() -> list[str]:
        endpoint = inspect.unwrap(app_module.query_stream)
        response = await endpoint(
            request=http_request,
            request_body=app_module.QueryRequest(
                question="What are Apple's main risk factors?"
            ),
        )
        return [chunk async for chunk in response.body_iterator]

    try:
        chunks = asyncio.run(consume_stream())
    finally:
        app_module._state.clear()

    assert len(chunks) == 1
    assert captured_cancel_event["event"].is_set()
    assert producer_stopped.wait(timeout=0.5)


def test_stream_timeout_sets_cancellation_event(mock_pipeline, monkeypatch) -> None:
    captured_cancel_event = {}
    producer_stopped = threading.Event()

    def stalled_stream(**kwargs):
        cancel_event = kwargs["cancel_event"]
        captured_cancel_event["event"] = cancel_event
        while not cancel_event.is_set():
            time.sleep(0.005)
        producer_stopped.set()
        if False:
            yield ("token", "unused")

    mock_pipeline.query_stream.side_effect = stalled_stream
    app_module._state.clear()
    app_module._state["pipeline"] = mock_pipeline
    monkeypatch.setattr(app_module, "STREAM_QUERY_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(app_module, "STREAM_QUEUE_POLL_SECONDS", 0.01)
    http_request = MagicMock()
    http_request.is_disconnected = AsyncMock(return_value=False)

    async def consume_stream() -> list[str]:
        endpoint = inspect.unwrap(app_module.query_stream)
        response = await endpoint(
            request=http_request,
            request_body=app_module.QueryRequest(
                question="What are Apple's main risk factors?"
            ),
        )
        return [chunk async for chunk in response.body_iterator]

    try:
        chunks = asyncio.run(consume_stream())
    finally:
        app_module._state.clear()

    body = "".join(chunks)
    assert app_module.STREAM_TIMEOUT_DETAIL in body
    assert captured_cancel_event["event"].is_set()
    assert producer_stopped.wait(timeout=0.5)


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


def test_cache_clear_is_disabled_by_default(client, mock_pipeline) -> None:
    response = client.post("/cache/clear")

    assert response.status_code == 403
    assert response.json()["detail"] == "Cache clearing is disabled on this deployment"
    mock_pipeline.cache.clear.assert_not_called()


def test_cache_clear_can_be_enabled_explicitly(
    client,
    mock_pipeline,
    monkeypatch,
) -> None:
    monkeypatch.setattr(app_module.settings, "enable_cache_clear", True)
    mock_pipeline.cache.clear.return_value = 3

    response = client.post("/cache/clear")

    assert response.status_code == 200
    assert response.json() == {"cleared_entries": 3}


def test_cache_test_is_rate_limited(client, mock_pipeline) -> None:
    mock_pipeline.retriever.embed_query.return_value = [1.0, 0.0]
    mock_pipeline.cache.test_similarity.return_value = 1.0
    mock_pipeline.cache.threshold = 0.9
    payload = {"query_a": "First query", "query_b": "Second query"}

    for _ in range(10):
        assert client.post("/cache/test", json=payload).status_code == 200

    blocked = client.post("/cache/test", json=payload)

    assert blocked.status_code == 429


def test_health_responds_while_cache_test_embeds(mock_pipeline) -> None:
    main_thread_id = threading.get_ident()
    embedding_thread_ids = []
    embedding_started = threading.Event()
    release_embedding = threading.Event()

    def blocking_embed(query: str) -> list[float]:
        embedding_thread_ids.append(threading.get_ident())
        embedding_started.set()
        release_embedding.wait(timeout=2.0)
        return [1.0, 0.0] if query.endswith("A") else [0.9, 0.1]

    mock_pipeline.retriever.embed_query.side_effect = blocking_embed
    mock_pipeline.cache.test_similarity.return_value = 0.95
    mock_pipeline.cache.threshold = 0.9
    app_module._state.clear()
    app_module._state["pipeline"] = mock_pipeline

    async def run_concurrent_requests() -> tuple[httpx.Response, httpx.Response, float]:
        transport = httpx.ASGITransport(app=app_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
            started_at = time.perf_counter()
            cache_test_task = asyncio.create_task(
                async_client.post(
                    "/cache/test",
                    json={"query_a": "Query A", "query_b": "Query B"},
                )
            )
            while not embedding_started.is_set():
                if time.perf_counter() - started_at > 1.0:
                    raise AssertionError("Cache test embedding did not start")
                await asyncio.sleep(0.005)
            health_response = await async_client.get("/health")
            health_elapsed = time.perf_counter() - started_at
            release_embedding.set()
            cache_test_response = await cache_test_task
            return cache_test_response, health_response, health_elapsed

    safety_release = threading.Timer(1.5, release_embedding.set)
    safety_release.start()
    try:
        cache_test_response, health_response, health_elapsed = asyncio.run(
            run_concurrent_requests()
        )
    finally:
        release_embedding.set()
        safety_release.cancel()
        app_module._state.clear()

    assert health_response.status_code == 200
    assert health_elapsed < 0.75
    assert cache_test_response.status_code == 200
    assert cache_test_response.json()["similarity"] == 0.95
    embedded_queries = [
        call.args[0] for call in mock_pipeline.retriever.embed_query.call_args_list
    ]
    assert embedded_queries == ["Query A", "Query B"]
    assert len(set(embedding_thread_ids)) == 1
    assert embedding_thread_ids[0] != main_thread_id
