"""Real SCALE-001 lifespan/pool/API/SDK/SQLite with offline transport barriers."""

import asyncio
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
TOKEN = "SCALE001_SYNTHETIC_BEARER_BROWSER_719C"
KEY = "SCALE001_SYNTHETIC_PROVIDER_KEY_72CD"


def main():
    directory = Path(os.environ.get("SCALE001_RUNTIME_DIR") or tempfile.mkdtemp(prefix="edqa-scale001-")).resolve()
    for name in ("GROQ_API_KEY", "GROQ_API_KEY2", "GROQ_API_KEY3", "GROQ_API_KEY4", "GROQ_API_KEY5",
                 "GROQ_API_KEY_FALL_BACK", "GROQ_API_KEY_FALL_BACK2"):
        os.environ[name] = KEY if name == "GROQ_API_KEY5" else ""
    os.environ.update({
        "GROQ_KEY_POLICY":"key5_only", "QDRANT_MODE":"local", "QDRANT_CLOUD_URL":"",
        "QDRANT_CLOUD_API_KEY":"", "HF_HUB_OFFLINE":"1", "TRANSFORMERS_OFFLINE":"1",
        "WORKSPACE_MODE":"local", "LOCAL_WORKSPACE_TOKEN":TOKEN, "ENABLE_WORKSPACE_EXECUTION":"true",
        "WORKSPACE_WORKER_ENABLED":"true", "WORKSPACE_WORKER_CONCURRENCY":"2",
        "WORKSPACE_DB_PATH":str(directory / "workspace.sqlite3"), "WORKSPACE_RUNS_DIR":str(directory / "runs"),
        "LOCAL_WORKSPACE_ALLOWED_HOSTS":"127.0.0.1:8790", "LOCAL_WORKSPACE_ALLOWED_ORIGINS":"http://localhost:4191",
        "ALLOWED_ORIGINS":"http://localhost:4191", "HARNESS_TEMP_DIR":str(directory / "dependencies"),
    })
    import httpx
    import uvicorn
    from groq import AsyncGroq
    from configs.offline_guard import offline_socket_guard
    from src.agent import provider
    from tests.integration.final_product_server import install_runtime_dependencies
    from tests.integration.harness_server import FakeGenerator

    with offline_socket_guard(), ExitStack() as stack:
        application, _closed = install_runtime_dependencies(stack, directory)
        stack.enter_context(patch.object(FakeGenerator, "model", "openai/gpt-oss-120b"))
        entered, release = asyncio.Event(), asyncio.Event()
        attempts = []

        async def transport(request):
            payload = json.loads(request.content)
            assert payload["response_format"]["json_schema"]["strict"] is True
            assert payload["include_reasoning"] is False and "tools" not in payload
            assert KEY not in json.dumps(payload["messages"]) and TOKEN not in json.dumps(payload["messages"])
            attempts.append(1)
            entered.set()
            await release.wait()
            data = json.loads(payload["messages"][1]["content"])
            observations = data["observations"]
            objective = data["research"]["config"]["objectives"][0]["objective_id"] if data["research"] else None
            if not observations:
                decision = {"kind":"tool", "tool_name":"search_documents", "objective_id":objective,
                    "arguments":[{"name":"query","value":"Apple risk"},{"name":"ticker","value":"AAPL"}]}
            elif len(observations) == 1:
                decision = {"kind":"tool", "tool_name":"read_document", "objective_id":objective,
                    "arguments":[{"name":"document_id","value":"AAPL:HARNESS"}]}
            else:
                decision = {"kind":"final", "answer":"Worker-owned Apple evidence summary.",
                    "evidence_refs":[{"kind":"document_id","value":"AAPL:HARNESS"},
                                     {"kind":"chunk_id","value":"AAPL_harness_0000"}],
                    "unresolved_objective_ids":[]}
            return httpx.Response(200, json={"id":"scale001-mock", "object":"chat.completion", "created":1,
                "model":payload["model"], "choices":[{"index":0,"finish_reason":"stop", "message":{
                    "role":"assistant", "content":json.dumps({"decision":decision})}}]})

        def client(**options):
            return AsyncGroq(**options, http_client=httpx.AsyncClient(transport=httpx.MockTransport(transport)))
        stack.enter_context(patch.object(provider, "AsyncGroq", client))

        @application.app.post("/__scale001__/control")
        async def control(body: dict[str, str]):
            pool = application._state["worker_supervisor"]
            if body["action"] in {"reset", "missing"}:
                await pool.stop()
                entered.clear()
                release.clear()
                attempts.clear()
                application.settings.groq_api_key5 = "" if body["action"] == "missing" else KEY
            elif body["action"] == "start":
                await pool.start()
            elif body["action"] == "release":
                release.set()
            return {"entered":entered.is_set(), "attempts":len(attempts),
                    "workers":pool.task_count, "active":pool.active_count}

        @application.app.get("/__scale001__/state")
        async def state():
            pool = application._state["worker_supervisor"]
            return {"entered":entered.is_set(), "attempts":len(attempts),
                    "workers":pool.task_count, "active":pool.active_count,
                    "eligible":pool.registry.eligible}

        uvicorn.run(application.app, host="127.0.0.1", port=8790, proxy_headers=False,
                    access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
