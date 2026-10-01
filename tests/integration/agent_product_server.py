"""TEST-005 real FastAPI/SQLite server with offline, injectable Agent decisions.

Only corpus/model dependencies and the abstract Agent decision-model factory
are substituted. Agent routes, access, jobs, tools, events and evaluation are
the production implementations. Test controls exist only in this loopback
harness, never in the application router.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import threading
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
from tests.integration.final_product_server import install_runtime_dependencies  # noqa: E402


TOKEN = "test005-synthetic-local-token-0123456789abcdef"
DOCUMENT_ID = "AAPL:HARNESS"
CHUNK_ID = "AAPL_harness_0000"


class AgentHarnessState:
    def __init__(self) -> None:
        self.mode = "unconfigured"
        self.entered = threading.Event()
        self.release = threading.Event()
        self.model_requests = 0

    def select(self, mode: str) -> None:
        if mode not in {"unconfigured", "research", "waiting"}:
            raise ValueError("unknown deterministic Agent mode")
        self.mode = mode
        self.entered.clear()
        self.release.clear()
        self.model_requests = 0

    def model(self, _identity: str):
        if self.mode == "research":
            from tests.test_agent_research import _final, _tool

            state = self

            class ResearchModel:
                requires_provider = False

                def __init__(self) -> None:
                    self.decisions = [
                        _tool("apple_risk", "search_documents", query="Apple risk", ticker="AAPL", group_by="chunk"),
                        _tool("apple_risk", "read_document", document_id=DOCUMENT_ID),
                        _final("The recorded Apple filing contains risk evidence.",
                               ("document_id", DOCUMENT_ID), ("chunk_id", CHUNK_ID)),
                    ]

                async def decide(self, _request):
                    state.model_requests += 1
                    return self.decisions.pop(0)

            return ResearchModel()
        if self.mode == "waiting":
            state = self

            class WaitingModel:
                requires_provider = False

                async def decide(self, _request):
                    state.model_requests += 1
                    state.entered.set()
                    await asyncio.to_thread(state.release.wait)
                    from tests.test_agent_orchestration import _tool
                    return _tool("read_document", document_id=DOCUMENT_ID)

            return WaitingModel()
        return None


def main() -> None:
    port = int(os.environ.get("TEST005_API_PORT", "8788"))
    directory = Path(os.environ.get("TEST005_RUNTIME_DIR") or tempfile.mkdtemp(prefix="edqa-test005-")).resolve()
    mode = os.environ.get("TEST005_WORKSPACE_MODE", "local")
    for key in ("GROQ_API_KEY", "GROQ_API_KEY_FALL_BACK"):
        os.environ[key] = "test005-offline-synthetic-provider-key"
    os.environ.update({
        "GROQ_KEY_POLICY": "key5_only", "QDRANT_MODE": "local",
        "QDRANT_CLOUD_URL": "", "QDRANT_CLOUD_API_KEY": "",
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "WORKSPACE_MODE": mode, "LOCAL_WORKSPACE_TOKEN": TOKEN,
        "ENABLE_WORKSPACE_EXECUTION": "true",
        "WORKSPACE_DB_PATH": str(directory / "workspace.sqlite3"),
        "WORKSPACE_RUNS_DIR": str(directory / "runs"),
        "LOCAL_WORKSPACE_ALLOWED_HOSTS": f"127.0.0.1:{port}",
        "LOCAL_WORKSPACE_ALLOWED_ORIGINS": "http://localhost:4187",
        "ALLOWED_ORIGINS": "http://localhost:4187",
        "HARNESS_TEMP_DIR": str(directory / "dependencies"),
        "LLM_RATE_LIMIT_BURST": "1000/minute", "LLM_RATE_LIMIT_DAILY": "10000/day",
    })

    from configs.offline_guard import offline_socket_guard
    from fastapi import HTTPException
    from src.agent.durable import AgentDurableService
    from src.agent.durable_models import AgentRunCreateRequest
    from src.workspace.jobs import SQLiteJobRepository
    import uvicorn

    state = AgentHarnessState()
    with offline_socket_guard(), ExitStack() as stack:
        application, _closed = install_runtime_dependencies(stack, directory)

        def agent_service(repository, registry_factory, **_provider_options):
            if state.mode == "unconfigured":
                return AgentDurableService(repository, registry_factory)
            return AgentDurableService(
                repository, registry_factory, decision_model_factory=state.model,
                decision_model_id="test005_scripted",
            )

        stack.enter_context(patch.object(application, "AgentDurableService", agent_service))

        @application.app.post("/__test005__/agent/mode")
        async def set_agent_mode(body: dict[str, str]):
            try:
                state.select(body["mode"])
            except (KeyError, ValueError) as error:
                raise HTTPException(422, "unknown deterministic Agent mode") from error
            return {"mode": state.mode}

        @application.app.get("/__test005__/agent/state")
        async def agent_harness_state():
            return {"mode": state.mode, "entered": state.entered.is_set(),
                    "model_requests": state.model_requests}

        @application.app.post("/__test005__/agent/release")
        async def release_agent():
            state.release.set()
            return {"released": True}

        @application.app.post("/__test005__/agent/interrupted")
        async def interrupted_fixture():
            repository = SQLiteJobRepository.from_settings(application.settings)
            service = AgentDurableService(repository, application.create_agent_tool_registry)
            run = service.create(
                AgentRunCreateRequest(goal="Inspect interrupted Agent research."),
                idempotency_key=f"test005-interrupted-{os.urandom(8).hex()}",
            )
            job = repository.get_job("job_" + run.run_id[6:])
            running = repository.transition_job(job.job_id, expected_revision=job.revision, target_state="running")
            repository.transition_step(
                job.job_id, running.steps[0].step_id,
                expected_job_revision=running.revision,
                expected_step_revision=running.steps[0].revision,
                target_state="running",
            )
            repository.recover_interrupted_jobs()
            current = service.get(run.run_id)
            return {"run_id": current.run_id, "state": current.state, "revision": current.revision}

        uvicorn.run(application.app, host="127.0.0.1", port=port,
                    proxy_headers=False, access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
