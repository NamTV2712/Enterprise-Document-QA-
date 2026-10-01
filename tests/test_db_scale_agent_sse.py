"""Real Agent HTTP/SSE reads overlap a paused uncommitted worker event append."""
import asyncio
import sqlite3
import threading

import httpx

from src.agent.durable_models import AgentRunCreateRequest
from src.workspace.database import WorkspaceDatabase
from tests.test_agent_api import _headers
from tests.test_agent_orchestration import CHUNK, DOC
from tests.test_agent_provider import BEARER, final, tool, wire
from tests.test_agent_provider_api import configured
from tests.test_agent_worker import application, worker, finish
from tests.test_workspace_worker import asynchronous


@asynchronous
async def test_sse_readers_and_worker_progress_while_event_transaction_is_held(configured, monkeypatch):
    sdk, calls = configured
    sdk.outputs = [wire(tool(document_id=DOC)), wire(final(refs=(("chunk_id", CHUNK),)))]
    service = application._agent_durable_service()
    created = service.create(AgentRunCreateRequest(goal="Find bounded evidence.",
        allow_decision_provider_execution=True), idempotency_key="db-scale-sse")
    queued = service.create(AgentRunCreateRequest(goal="Cancel queued evidence.",
        allow_decision_provider_execution=True), idempotency_key="db-scale-cancel")
    inserted, release = threading.Event(), threading.Event()
    original_connect = WorkspaceDatabase._open_connection
    class PausedConnection(sqlite3.Connection):
        def execute(self, sql, *args):
            cursor = super().execute(sql, *args)
            if sql.startswith("INSERT INTO job_events(") and "'agent_decision'" in sql and not inserted.is_set():
                inserted.set()
                assert release.wait(10)
            return cursor
    def connect(*args, **kwargs):
        return original_connect(*args, **kwargs, factory=PausedConnection)
    monkeypatch.setattr(WorkspaceDatabase, "_open_connection", staticmethod(connect))
    pool, executor = worker(service, concurrency=1)
    await pool.start()
    headers = _headers(token=BEARER)
    try:
        assert await asyncio.to_thread(inserted.wait, 5)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application.app),
                                    base_url="http://localhost:8000") as client:
            async def read(_):
                for endpoint in ["/agent/runs", f"/agent/runs/{created.run_id}",
                    f"/agent/runs/{created.run_id}/results", f"/agent/runs/{created.run_id}/events"]:
                    response = await client.get(endpoint, headers=headers)
                    assert response.status_code == 200
                    if endpoint.endswith("/events"):
                        assert "event: agent_decision" not in response.text
                return True
            assert all(await asyncio.wait_for(asyncio.gather(*(read(i) for i in range(8))), 5))
            assert not release.is_set() and not executor.finished.is_set()
            release.set()
            # The second queued run is cancelled while the first owner is still
            # executing. Its cancellation is independent of read connections.
            cancelled = service.cancel(queued.run_id, expected_revision=queued.revision)
            assert cancelled.state == "cancelled"
            await finish(pool, executor)
            terminal = service.get(created.run_id)
            assert terminal.state == "succeeded" and len(sdk.requests) == 2
            assert executor.invocations == ["job_" + created.run_id[6:]]
            events = await client.get(f"/agent/runs/{created.run_id}/events", headers=headers)
            ids = [int(line[4:]) for line in events.text.splitlines() if line.startswith("id: ")]
            assert ids == list(range(1, len(ids) + 1))
            resumed = await client.get(f"/agent/runs/{created.run_id}/events",
                headers={**headers, "Last-Event-ID": "3"})
            assert [int(line[4:]) for line in resumed.text.splitlines() if line.startswith("id: ")] == ids[3:]
            report = await client.get(f"/agent/runs/{created.run_id}/evaluation", headers=headers)
            assert report.status_code == 200 and len(report.json()["metrics"]) == 21
            assert len(sdk.requests) == 2 and calls == ["read_document"]
    finally:
        release.set()
        await pool.stop()
