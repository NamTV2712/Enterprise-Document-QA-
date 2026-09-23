"""Public metric definitions are a read-only view of the native registry."""

from dataclasses import asdict

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.evaluations import create_evaluation_router
from src.evaluation.native_protocol import METRIC_DEFINITIONS


def test_public_metric_definitions_are_exact_and_provider_free() -> None:
    app = FastAPI()
    app.include_router(create_evaluation_router())
    response = TestClient(app).get("/evaluation/metrics")

    assert response.status_code == 200
    assert response.json() == {
        "protocol": "native-evaluation",
        "protocol_version": 1,
        "capabilities": {
            "provider_free": True,
            "computes_judge_scores": False,
            "requires_bound_judge_scores": True,
        },
        "items": [asdict(item) | {"required_inputs": list(item.required_inputs)} for item in METRIC_DEFINITIONS],
        "total": 6,
    }
    assert "Authorization" not in response.request.headers
