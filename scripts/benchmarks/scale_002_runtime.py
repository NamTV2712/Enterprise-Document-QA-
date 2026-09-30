"""Real loopback FastAPI/SQLite/Agent runtime with benchmark-only observation."""

from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import os
import socket
import sqlite3
import threading
import time
from collections import Counter, defaultdict
from contextlib import ExitStack, asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from scripts.benchmarks.scale_002_stats import Scenario, working_set_bytes


TOKEN = "SCALE002_SYNTHETIC_LOCAL_SESSION_719C"
KEY = "SCALE002_SYNTHETIC_PROVIDER_CREDENTIAL_72CD"
ORIGIN = "http://localhost:4173"
CURRENT_JOB = contextvars.ContextVar("scale002_job", default=None)
TERMINAL = {"succeeded", "failed", "cancelled", "interrupted"}


class BenchmarkFailure(RuntimeError):
    """Fixed safe failure category; never contains request/exception bodies."""


class Observer:
    def __init__(self):
        self.lock = threading.RLock()
        self.reset()

    def reset(self):
        with self.lock:
            self.jobs = {}
            self.events = defaultdict(dict)
            self.owners = Counter()
            self.calls = Counter()
            self.provider_ms = []
            self.tool_ms = []
            self.claim_ms = []
            self.transaction_ms = []
            self.lock_wait_ms = []
            self.errors = Counter()
            self.active = 0
            self.peak_active = 0
            self.peak_queue = 0
            self.queued = set()
            self.measuring = False

    def committed(self, events, stamp):
        with self.lock:
            for job_id, sequence, kind, state in events:
                row = self.jobs.setdefault(job_id, {})
                self.events[job_id][sequence] = stamp
                if kind == "created":
                    row["created"] = stamp
                    self.queued.add(job_id)
                    self.peak_queue = max(self.peak_queue, len(self.queued))
                if kind == "state_changed" and state == "running":
                    if "claimed" in row:
                        self.errors["duplicate_claim"] += 1
                    row["claimed"] = stamp
                    self.queued.discard(job_id)
                if state in TERMINAL:
                    if "terminal" in row:
                        self.errors["duplicate_terminal"] += 1
                    row["terminal"] = stamp
                    self.queued.discard(job_id)


def observe_database(stack: ExitStack, database_path: Path, observer: Observer):
    """Observe successful commits; preserve production connection/lock code."""
    from src.workspace import database as database_module
    from src.workspace.jobs import SQLiteJobRepository
    original_connect = sqlite3.connect
    original_lock = database_module._write_lock_for
    original_claim = SQLiteJobRepository.claim_next_job

    class ObservedConnection(sqlite3.Connection):
        pending = None
        began = None

        def execute(self, sql, parameters=()):
            try:
                result = super().execute(sql, parameters)
            except sqlite3.Error as error:
                with observer.lock:
                    observer.errors["sqlite_busy" if "locked" in str(error).lower()
                                    or "busy" in str(error).lower() else "sqlite_error"] += 1
                raise
            if sql == "BEGIN IMMEDIATE":
                self.began = time.perf_counter()
            if sql.startswith("INSERT INTO job_events("):
                if self.pending is None:
                    self.pending = []
                # Both existing insertion forms share job/sequence; decision
                # insertion has literal type and therefore one fewer parameter.
                decision = "'agent_decision'" in sql
                kind, state = ("agent_decision", parameters[3]) if decision else parameters[3:5]
                self.pending.append((parameters[1], parameters[2], kind, state))
            if sql.startswith("UPDATE jobs ") and result.rowcount:
                with observer.lock:
                    for value in parameters:
                        if isinstance(value, str) and value.startswith("job_") and "terminal" in observer.jobs.get(value, {}):
                            observer.errors["mutation_after_terminal"] += 1
            return result

        def commit(self):
            super().commit()
            stamp = time.perf_counter()  # The durable boundary, not wall time or UI paint.
            if self.began is not None and observer.measuring:
                with observer.lock:
                    observer.transaction_ms.append((stamp - self.began) * 1000)
            self.began = None
            observer.committed(self.pending or (), stamp)
            self.pending = None

        def rollback(self):
            super().rollback()
            self.pending = None
            self.began = None

    def connect(*args, **kwargs):
        if args and Path(args[0]).resolve() == database_path:
            kwargs["factory"] = ObservedConnection
        return original_connect(*args, **kwargs)

    class TimedLock:
        def __init__(self, original):
            self.original = original

        def __enter__(self):
            started = time.perf_counter()
            self.original.acquire()
            if observer.measuring:
                with observer.lock:
                    observer.lock_wait_ms.append((time.perf_counter() - started) * 1000)
            return self

        def __exit__(self, *_args):
            self.original.release()

    def lock_for(path):
        lock = original_lock(path)
        return TimedLock(lock) if path == database_path else lock

    def claim(repository, eligible):
        started = time.perf_counter()
        try:
            job = original_claim(repository, eligible)
        except Exception:
            with observer.lock: observer.errors["claim_failure"] += 1
            raise
        if job is not None:
            with observer.lock: observer.claim_ms.append((time.perf_counter() - started) * 1000)
        return job

    stack.enter_context(patch.object(sqlite3, "connect", connect))
    stack.enter_context(patch.object(database_module, "_write_lock_for", lock_for))
    stack.enter_context(patch.object(SQLiteJobRepository, "claim_next_job", claim))


class Runtime:
    def __init__(self, application, observer, scenario, client):
        self.application, self.observer, self.scenario, self.client = application, observer, scenario, client
        self.request_ms = []
        self.statuses = Counter()
        self.endpoint_ms = defaultdict(list)
        self.sse = Counter()
        self.delivery_ms = []
        self.loop_lag_ms = []
        self.measuring = False
        self.release = asyncio.Event()
        self.entered = set()
        self.fail_job = None
        self.fixture_document = "AAPL:HARNESS"
        self.fixture_chunk = "AAPL_harness_0000"
        self.fixture_ticker = "AAPL"
        self.monitor_stop = asyncio.Event()
        self.peak_worker_tasks = 0
        self.peak_rss_bytes = None

    @property
    def pool(self):
        return self.application._state.get("worker_supervisor")

    async def request(self, method, endpoint, *, expected=200, **kwargs):
        started = time.perf_counter()
        response = await self.client.request(method, endpoint, **kwargs)
        if self.measuring:
            duration = (time.perf_counter() - started) * 1000
            self.request_ms.append(duration)
            category = ("create" if method == "POST" and endpoint == "/agent/runs" else
                        "evaluation" if endpoint.endswith("/evaluation") else
                        "result" if endpoint.endswith("/results") else
                        "sse_resume" if endpoint.endswith("/events") else
                        "cancel" if endpoint.endswith("/cancel") else
                        "list" if endpoint == "/agent/runs" else "detail")
            self.endpoint_ms[category].append(duration)
            self.statuses[str(response.status_code)] += 1
        if response.status_code != expected:
            raise BenchmarkFailure("unexpected_http_status")
        return response

    async def create(self, ordinal, research=False):
        body = {"goal": "Research benchmark filing evidence.", "allow_decision_provider_execution": True}
        if self.scenario.profile == "degraded" and ordinal == "measured-0":
            body["goal"] += " Selected synthetic failure."
        if research:
            body["research"] = {"objectives": [{"objective_id": "filing_evidence",
                "question": "Find filing evidence", "ticker_scope": self.fixture_ticker}]}
        response = await self.request("POST", "/agent/runs", expected=201, json=body,
                                      headers={"Idempotency-Key": f"bench-{ordinal}"})
        data = response.json()
        if data["state"] != "queued":
            raise BenchmarkFailure("creation_not_queued")
        return data["run_id"]

    async def monitor(self):
        period = .02
        while not self.monitor_stop.is_set():
            scheduled = time.perf_counter() + period
            try:
                await asyncio.wait_for(self.monitor_stop.wait(), period)
            except asyncio.TimeoutError:
                if self.measuring:
                    self.loop_lag_ms.append(max(0, time.perf_counter() - scheduled) * 1000)
                    rss = working_set_bytes()
                    if rss is not None: self.peak_rss_bytes = max(self.peak_rss_bytes or 0, rss)
                    if self.pool:
                        self.peak_worker_tasks = max(self.peak_worker_tasks, self.pool.task_count)
                        if not self.pool.healthy:
                            self.observer.errors["unhealthy_pool"] += 1

    async def wait_terminal(self, ids, *, idle=False):
        while not all("terminal" in self.observer.jobs.get("job_" + identifier[6:], {}) for identifier in ids):
            if self.pool and not self.pool.healthy:
                raise BenchmarkFailure("unhealthy_pool")
            await asyncio.sleep(.02)
        while idle and self.pool and self.pool.active_count:
            await asyncio.sleep(.01)

    async def read(self, identifier, operation):
        endpoint = ("/agent/runs", f"/agent/runs/{identifier}",
                    f"/agent/runs/{identifier}/results", f"/agent/runs/{identifier}/evaluation")[operation % 4]
        response = await self.request("GET", endpoint)
        if endpoint.endswith("/evaluation") and len(response.json()["metrics"]) != 21:
            raise BenchmarkFailure("evaluation_contract")

    async def subscribe(self, identifier):
        cursor = 0
        observed = []
        job_id = "job_" + identifier[6:]
        self.sse["subscribers"] += 1
        terminal = False
        while not terminal:
            started = time.perf_counter()
            async with self.client.stream("GET", f"/agent/runs/{identifier}/events",
                    headers={"Last-Event-ID": str(cursor)}) as response:
                self.sse["connections"] += 1
                if response.status_code != 200:
                    self.sse["connection_failures"] += 1
                    raise BenchmarkFailure("sse_connection_failure")
                frame = {}
                async for line in response.aiter_lines():
                    if line.startswith("id: "): frame["sequence"] = int(line[4:])
                    elif line.startswith("data: "): frame["data"] = json.loads(line[6:])
                    elif line == "" and frame:
                        sequence = frame["sequence"]
                        self.sse["duplicate_events"] += int(sequence in observed)
                        self.sse["ordering_violations"] += int(sequence <= cursor)
                        observed.append(sequence)
                        cursor = sequence
                        stamp = self.observer.events[job_id].get(sequence)
                        if stamp is not None:
                            self.delivery_ms.append((time.perf_counter() - stamp) * 1000)
                        terminal = terminal or frame["data"]["state"] in TERMINAL
                        frame = {}
            if self.measuring:
                duration = (time.perf_counter() - started) * 1000
                self.request_ms.append(duration)
                self.endpoint_ms["sse_batch"].append(duration)
                self.statuses["200"] += 1
            self.sse["finite_closures"] += 1
            if not terminal: await asyncio.sleep(.1)
        expected = sorted(self.observer.events[job_id])
        self.sse["missing_events"] += len(set(expected) - set(observed))
        resume_cursor = min(3, cursor)
        resumed = await self.request("GET", f"/agent/runs/{identifier}/events",
                                     headers={"Last-Event-ID": str(resume_cursor)})
        resumed_ids = [int(line[4:]) for line in resumed.text.splitlines() if line.startswith("id: ")]
        self.sse["resume_failures"] += int(resumed.status_code != 200
            or resumed_ids != [sequence for sequence in expected if sequence > resume_cursor])
        self.sse["successful_streams"] += 1


@asynccontextmanager
async def runtime(scenario: Scenario, directory: Path):
    """No routes or production timing are replaced; mocks only external boundaries."""
    import uvicorn
    from groq import AsyncGroq
    from pydantic import SecretStr
    from configs.offline_guard import offline_socket_guard

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(2048)
    port = sock.getsockname()[1]
    observer = Observer()
    old_disabled = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    with offline_socket_guard(), ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
            "HARNESS_TEMP_DIR": str(directory / "dependencies")}))
        from src.api import app as application
        from src.agent import provider
        from src.agent.durable import AgentDurableService
        from src.agent.registry import AgentToolRegistry
        from tests.integration.final_product_server import install_runtime_dependencies
        from tests.integration.harness_server import FakeGenerator
        if scenario.mode == "hermetic":
            install_runtime_dependencies(stack, directory)
        else:
            stack.enter_context(patch.dict(application._state, {}, clear=True))
            stack.enter_context(patch.object(application, "Generator", FakeGenerator))
        stack.enter_context(patch.object(FakeGenerator, "model", "openai/gpt-oss-120b"))
        values = {"workspace_mode": "local", "enable_workspace_execution": True,
            "workspace_worker_enabled": scenario.profile not in ("admission", "cancel"),
            "workspace_worker_concurrency": scenario.workers, "workspace_worker_poll_interval_ms": scenario.poll_ms,
            "workspace_worker_shutdown_grace_ms": 5000, "workspace_sqlite_busy_timeout_ms": 5000,
            "workspace_db_path": directory / "workspace.sqlite3", "workspace_runs_dir": directory / "runs",
            "local_workspace_token": SecretStr(TOKEN), "local_workspace_allowed_hosts": f"127.0.0.1:{port}",
            "local_workspace_allowed_origins": ORIGIN, "allowed_origins": ORIGIN,
            "groq_key_policy": "key5_only", "qdrant_mode": "local",
            "qdrant_cloud_url": "", "qdrant_cloud_api_key": ""}
        values.update({name: KEY if name == "groq_api_key5" else ""
            for name in type(application.settings).model_fields if name.startswith("groq_api_key")})
        if scenario.mode == "artifact":
            values.update(qdrant_local_path=Path("data/processed/qdrant"),
                          qdrant_index_manifest_path=Path("data/processed/qdrant_index_manifest.json"),
                          data_raw_dir=Path("data/raw"), data_processed_dir=Path("data/processed"))
        for name, value in values.items(): stack.enter_context(patch.object(application.settings, name, value))
        observe_database(stack, (directory / "workspace.sqlite3").resolve(), observer)
        original_execute = AgentDurableService.execute_claimed
        original_tool = AgentToolRegistry.invoke
        client = httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", trust_env=False,
            headers={"Authorization": f"Bearer {TOKEN}", "Origin": ORIGIN}, timeout=30,
            limits=httpx.Limits(max_connections=300, max_keepalive_connections=100))
        bench = Runtime(application, observer, scenario, client)

        async def execute(service, job):
            token = CURRENT_JOB.set(job.job_id)
            with observer.lock:
                observer.owners[job.job_id] += 1
                observer.active += 1
                observer.peak_active = max(observer.peak_active, observer.active)
            try: return await original_execute(service, job)
            finally:
                with observer.lock: observer.active -= 1
                CURRENT_JOB.reset(token)

        async def tool(registry, *args, **kwargs):
            started = time.perf_counter()
            try: return await original_tool(registry, *args, **kwargs)
            finally:
                with observer.lock: observer.tool_ms.append((time.perf_counter() - started) * 1000)

        async def transport(request):
            payload = json.loads(request.content)
            text = json.dumps(payload["messages"])
            if KEY in text or TOKEN in text or "tools" in payload:
                raise BenchmarkFailure("unsafe_model_context")
            job_id = CURRENT_JOB.get()
            if job_id is None: raise BenchmarkFailure("provider_without_owner")
            data = json.loads(payload["messages"][1]["content"])
            if data["goal"].endswith("Selected synthetic failure."):
                bench.fail_job = job_id
            observer.calls[job_id] += 1
            bench.entered.add(job_id)
            started = time.perf_counter()
            if scenario.profile == "cancel" and bench.measuring: await bench.release.wait()
            await asyncio.sleep(scenario.latency_ms / 1000)
            observer.provider_ms.append((time.perf_counter() - started) * 1000)
            if job_id == bench.fail_job:
                return httpx.Response(503, json={"error": {"message": "Synthetic deterministic failure"}})
            observations = data["observations"]
            objective = data["research"]["config"]["objectives"][0]["objective_id"] if data["research"] else None
            if not observations and objective:
                decision = {"kind": "tool", "tool_name": "search_documents", "objective_id": objective,
                    "arguments": [{"name": "query", "value": f"{bench.fixture_ticker} filing evidence"},
                                  {"name": "ticker", "value": bench.fixture_ticker}]}
            elif len(observations) < (2 if objective else 1):
                decision = {"kind": "tool", "tool_name": "read_document", "objective_id": objective,
                    "arguments": [{"name": "document_id", "value": bench.fixture_document}]}
            else:
                decision = {"kind": "final", "answer": "Benchmark filing evidence summary.",
                    "evidence_refs": [{"kind": "document_id", "value": bench.fixture_document},
                                      {"kind": "chunk_id", "value": bench.fixture_chunk}],
                    "unresolved_objective_ids": []}
            return httpx.Response(200, json={"id": "scale002-mocked", "object": "chat.completion", "created": 1,
                "model": payload["model"], "choices": [{"index": 0, "finish_reason": "stop", "message": {
                    "role": "assistant", "content": json.dumps({"decision": decision})}}]})

        def sdk(**options):
            if options["max_retries"] != 0: raise BenchmarkFailure("provider_retry_enabled")
            return AsyncGroq(**options, http_client=httpx.AsyncClient(transport=httpx.MockTransport(transport)))
        stack.enter_context(patch.object(AgentDurableService, "execute_claimed", execute))
        stack.enter_context(patch.object(AgentToolRegistry, "invoke", tool))
        stack.enter_context(patch.object(provider, "AsyncGroq", sdk))
        server = uvicorn.Server(uvicorn.Config(application.app, log_level="critical", access_log=False,
            lifespan="on", proxy_headers=False, loop="asyncio", ws="none"))
        async def serve():
            try: await server.serve(sockets=[sock])
            except SystemExit: raise BenchmarkFailure("runtime_startup_failed") from None
        task = asyncio.create_task(serve(), name="scale002-http-server")
        monitor = None
        try:
            async def ready():
                while not server.started:
                    if task.done(): raise BenchmarkFailure("runtime_startup_failed")
                    await asyncio.sleep(.01)
            await asyncio.wait_for(ready(), 60)
            if scenario.mode == "artifact":
                chunks = application._state["document_chunks_by_id"]
                bench.fixture_document = next(iter(chunks))
                chunk = chunks[bench.fixture_document][0]
                bench.fixture_chunk, bench.fixture_ticker = chunk["chunk_id"], chunk["ticker"]
            monitor = asyncio.create_task(bench.monitor(), name="scale002-loop-probe")
            yield bench
        finally:
            bench.release.set()
            bench.monitor_stop.set()
            if monitor: await monitor
            if scenario.profile == "cancel" and bench.pool:
                await bench.pool.stop()
                application._state.pop("worker_supervisor", None)
            await client.aclose()
            server.should_exit = True
            try: await asyncio.wait_for(task, 15)
            finally:
                if not task.done(): task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                sock.close()
                logging.disable(old_disabled)


async def bounded_map(count, concurrency, operation):
    next_index = 0
    results = [None] * count
    async def lane():
        nonlocal next_index
        while next_index < count:
            index = next_index
            next_index += 1
            results[index] = await operation(index)
    tasks = [asyncio.create_task(lane()) for _ in range(min(count, concurrency))]
    try: await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            if not task.done(): task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    return results
