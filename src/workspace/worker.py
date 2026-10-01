"""Lifespan-owned bounded asyncio consumers of the existing DATA-004 queue."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import nullcontext
from src.workspace.attribution import capture, record_interval, span, timed
from dataclasses import dataclass

from configs.settings import Settings
from src.workspace.executors import ExecutorRegistry
from src.workspace.jobs import DurableJob, JobConflictError, JobTransitionError, SQLiteJobRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkerConfig:
    concurrency: int = 2
    poll_interval_ms: int = 500
    shutdown_grace_ms: int = 5000

    def __post_init__(self) -> None:
        for value, lower, upper in ((self.concurrency, 1, 16),
                                    (self.poll_interval_ms, 100, 5000),
                                    (self.shutdown_grace_ms, 100, 60_000)):
            if type(value) is not int or not lower <= value <= upper:
                raise ValueError("worker configuration is out of bounds")

    @classmethod
    def from_settings(cls, configured: Settings) -> WorkerConfig:
        return cls(configured.workspace_worker_concurrency,
                   configured.workspace_worker_poll_interval_ms,
                   configured.workspace_worker_shutdown_grace_ms)


class WorkerSupervisor:
    """N fixed consumers, no per-queued-job task and no namespace business loop."""

    def __init__(self, repository: SQLiteJobRepository, registry: ExecutorRegistry,
                 config: WorkerConfig = WorkerConfig(), *, attribution_enabled: bool = False,
                 attribution_sink=None) -> None:
        self.repository = repository
        self.registry = registry
        self.config = config
        self._stop = asyncio.Event()
        self._tasks: tuple[asyncio.Task[None], ...] = ()
        self._active: set[str] = set()
        self._stopping = False
        self.attribution_enabled = attribution_enabled
        self.attribution_sink = attribution_sink

    @property
    def task_count(self) -> int:
        return sum(not task.done() for task in self._tasks)

    @property
    def active_count(self) -> int:
        return len(self._active)

    @property
    def healthy(self) -> bool:
        return not self._stop.is_set() and self.task_count == self.config.concurrency

    async def start(self) -> None:
        if self._tasks:
            raise RuntimeError("worker supervisor has already started")
        self._stop.clear()
        self._stopping = False
        self._tasks = tuple(asyncio.create_task(self._worker(), name=f"durable-worker-{index}")
                            for index in range(self.config.concurrency))
        for task in self._tasks:
            task.add_done_callback(self._worker_done)
        logger.info("durable_workers_started capacity=%d", self.config.concurrency)

    def _worker_done(self, task: asyncio.Task[None]) -> None:
        if not self._stopping:
            self._stop.set()
            logger.error("durable_worker_stopped_unexpectedly")
        if not task.cancelled():
            task.exception()  # Retrieve without exposing exception content.

    async def _idle(self) -> None:
        try:
            await asyncio.wait_for(self._stop.wait(), self.config.poll_interval_ms / 1000)
        except asyncio.TimeoutError:
            pass

    def _interrupt(self, job_id: str) -> None:
        # Bounded CAS retries reconcile cancellation/terminal commits; no work retry.
        for _ in range(3):
            job = self.repository.get_job(job_id)
            if job.state not in ("running", "cancelling"):
                return
            try:
                self.repository.transition_job(
                    job_id, expected_revision=job.revision, target_state="interrupted",
                    failure_code="worker_interrupted",
                    failure_message="Worker stopped before terminal execution was committed.",
                )
                return
            except (JobConflictError, JobTransitionError):
                continue
        raise JobConflictError("worker interruption revision conflict")

    async def _reconcile(self, job: DurableJob) -> None:
        try:
            await asyncio.to_thread(self._interrupt, job.job_id)
        except Exception:
            # DB failure leaves active authority for startup recovery; never replay.
            logger.error("durable_worker_reconciliation_failed")

    @timed("worker.claim")
    async def _claim(self) -> DurableJob | None:
        # Cancellation cannot abandon a thread that may commit ownership later.
        # Finish the bounded SQLite operation, then reconcile any claimed row.
        task = asyncio.create_task(asyncio.to_thread(self.repository.claim_next_job, self.registry.eligible))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            job = await task
            if job is not None:
                await self._reconcile(job)
            raise

    async def _worker(self) -> None:
        previous_idle = None
        while not self._stop.is_set():
            job = None
            with capture("worker") if self.attribution_enabled else nullcontext() as trace:
                if previous_idle is not None:
                    record_interval("worker.poll_wait", *previous_idle)
                with span("worker.cycle"):
                    job = await self._iteration()
            if job is not None and job.namespace == "agent" and self.attribution_sink is not None and trace is not None:
                try:
                    await self.attribution_sink(trace, correlation_id=job.job_id, route_template="worker.agent")
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.warning("performance_telemetry_write_failed")
            if job is None:
                began = time.perf_counter_ns()
                await self._idle()
                previous_idle = (began, time.perf_counter_ns())
            else:
                previous_idle = None

    async def _iteration(self):
        try:
            job = await self._claim()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error("durable_worker_claim_failed")
            return None
        if job is None:
            return None
        if self._stop.is_set():
            await self._reconcile(job)
            return job
        await self._execute(job)
        return job

    @timed("worker.service")
    async def _execute(self, job):
        self._active.add(job.job_id)
        try:
            await self.registry.resolve(job).execute(job)
            # A returned executor must have persisted its namespace outcome.
            # If it did not, the external boundary is uncertain, never retry.
            await self._reconcile(job)
        except asyncio.CancelledError:
            await self._reconcile(job)
            raise
        except Exception:
            logger.error("durable_worker_executor_failed namespace=%s", job.namespace)
            await self._reconcile(job)
        finally:
            self._active.discard(job.job_id)

    async def stop(self) -> None:
        self._stopping = True
        self._stop.set()
        if not self._tasks:
            return
        _, pending = await asyncio.wait(self._tasks, timeout=self.config.shutdown_grace_ms / 1000)
        for task in pending:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = ()
        logger.info("durable_workers_stopped")
