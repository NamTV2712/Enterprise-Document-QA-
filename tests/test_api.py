from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

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
def client(mock_pipeline):
    """Inject the mock pipeline and avoid FastAPI lifespan model loading."""
    app_module._state.clear()
    app_module._state["pipeline"] = mock_pipeline
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


def test_query_handles_pipeline_exception_gracefully(client, mock_pipeline) -> None:
    mock_pipeline.query.side_effect = RuntimeError("Unexpected retrieval error")

    response = client.post(
        "/query",
        json={"question": "What are Apple's risks?"},
    )

    assert response.status_code == 500
    assert "Unexpected retrieval error" in response.json()["detail"]


def test_cache_stats_endpoint(client) -> None:
    response = client.get("/cache/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["hit_rate"] == 0.0
    assert data["max_entries"] == 500
