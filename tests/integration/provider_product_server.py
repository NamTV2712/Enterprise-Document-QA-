"""Real PROVIDER-001 resolver/SDK/API/SQLite with an offline HTTP transport."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
TOKEN = "AGENT_PROVIDER_TEST_BEARER_7D2A_browser_synthetic"
KEY = "AGENT_PROVIDER_TEST_KEY_91C4_browser_synthetic"


def main() -> None:
    directory = Path(os.environ.get("PROVIDER001_RUNTIME_DIR") or tempfile.mkdtemp(prefix="edqa-provider001-")).resolve()
    for name in ("GROQ_API_KEY", "GROQ_API_KEY2", "GROQ_API_KEY3", "GROQ_API_KEY4",
                 "GROQ_API_KEY5", "GROQ_API_KEY_FALL_BACK", "GROQ_API_KEY_FALL_BACK2"):
        os.environ[name] = KEY if name == "GROQ_API_KEY5" else ""
    os.environ.update({
        "GROQ_KEY_POLICY": "key5_only", "QDRANT_MODE": "local",
        "QDRANT_CLOUD_URL": "", "QDRANT_CLOUD_API_KEY": "",
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "WORKSPACE_MODE": "local", "LOCAL_WORKSPACE_TOKEN": TOKEN,
        "ENABLE_WORKSPACE_EXECUTION": "true",
        "WORKSPACE_DB_PATH": str(directory / "workspace.sqlite3"),
        "WORKSPACE_RUNS_DIR": str(directory / "runs"),
        "LOCAL_WORKSPACE_ALLOWED_HOSTS": "127.0.0.1:8789",
        "LOCAL_WORKSPACE_ALLOWED_ORIGINS": "http://localhost:4189",
        "ALLOWED_ORIGINS": "http://localhost:4189",
        "HARNESS_TEMP_DIR": str(directory / "dependencies"),
    })
    import httpx
    import uvicorn
    from groq import AsyncGroq
    from configs.offline_guard import offline_socket_guard
    from src.agent import provider
    from tests.integration.final_product_server import install_runtime_dependencies

    with offline_socket_guard(), ExitStack() as stack:
        application, _closed = install_runtime_dependencies(stack, directory)
        from tests.integration.harness_server import FakeGenerator
        stack.enter_context(patch.object(FakeGenerator, "model", "openai/gpt-oss-120b"))
        attempts = []

        def http_response(request):
            payload = json.loads(request.content)
            assert payload["response_format"]["json_schema"]["strict"] is True
            assert payload["include_reasoning"] is False and "tools" not in payload
            assert KEY not in json.dumps(payload["messages"]) and TOKEN not in json.dumps(payload["messages"])
            data = json.loads(payload["messages"][1]["content"])
            observations = data["observations"]
            objective = data["research"]["config"]["objectives"][0]["objective_id"]
            if not observations:
                decision = {"kind": "tool", "tool_name": "search_documents", "objective_id": objective,
                    "arguments": [{"name": "query", "value": "Apple risk"}, {"name": "ticker", "value": "AAPL"}]}
            elif len(observations) == 1:
                decision = {"kind": "tool", "tool_name": "read_document", "objective_id": objective,
                    "arguments": [{"name": "document_id", "value": "AAPL:HARNESS"}]}
            else:
                decision = {"kind": "final", "answer": "Recorded Apple filing evidence supports this bounded summary.",
                    "evidence_refs": [{"kind": "document_id", "value": "AAPL:HARNESS"},
                                      {"kind": "chunk_id", "value": "AAPL_harness_0000"}],
                    "unresolved_objective_ids": []}
            attempts.append(1)
            return httpx.Response(200, json={"id": "provider001-mock", "object": "chat.completion",
                "created": 1, "model": payload["model"], "choices": [{"index": 0, "finish_reason": "stop",
                    "message": {"role": "assistant", "content": json.dumps({"decision": decision})}}]})

        def client(**options):
            return AsyncGroq(**options, http_client=httpx.AsyncClient(transport=httpx.MockTransport(http_response)))

        stack.enter_context(patch.object(provider, "AsyncGroq", client))

        @application.app.post("/__provider001__/mode")
        async def select_mode(body: dict[str, str]):
            application.settings.groq_api_key5 = "" if body["mode"] == "missing" else KEY
            application._state["pipeline"].generator.model = (
                "ordinary-chat-only" if body["mode"] == "unsupported" else "openai/gpt-oss-120b")
            return {"attempts": len(attempts)}

        @application.app.get("/__provider001__/attempts")
        async def transport_attempts():
            return {"attempts": len(attempts)}

        uvicorn.run(application.app, host="127.0.0.1", port=8789,
                    proxy_headers=False, access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
