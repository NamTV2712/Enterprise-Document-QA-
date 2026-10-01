"""Explicit DATA-004 consumers; persisted strings never resolve Python code."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable, Sequence
from typing import Protocol

from src.agent.durable import AGENT_JOB_TYPE, AgentDurableService
from src.workspace.jobs import DurableJob, JOB_NAMESPACES, JobNamespace


class DurableJobExecutor(Protocol):
    namespace: JobNamespace
    job_type: str

    async def execute(self, job: DurableJob) -> None: ...


class ExecutorRegistry:
    """Immutable exact namespace/type registration from application callables."""

    def __init__(self, executors: Sequence[DurableJobExecutor]) -> None:
        if not 1 <= len(executors) <= len(JOB_NAMESPACES):
            raise ValueError("executor registry size is out of bounds")
        self._executors: dict[tuple[JobNamespace, str], DurableJobExecutor] = {}
        for executor in executors:
            key = (executor.namespace, executor.job_type)
            if (executor.namespace not in JOB_NAMESPACES or key in self._executors
                    or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", executor.job_type)):
                raise ValueError("unknown or duplicate executor registration")
            self._executors[key] = executor

    @property
    def eligible(self) -> tuple[tuple[JobNamespace, str], ...]:
        return tuple(self._executors)

    def resolve(self, job: DurableJob) -> DurableJobExecutor:
        try:
            return self._executors[(job.namespace, job.job_type)]
        except KeyError:
            raise ValueError("job has no registered executor") from None


class AgentJobExecutor:
    namespace: JobNamespace = "agent"
    job_type = AGENT_JOB_TYPE

    def __init__(self, service_factory: Callable[[], AgentDurableService]) -> None:
        self._service_factory = service_factory

    async def execute(self, job: DurableJob) -> None:
        # Runtime credentials/provider binding are resolved after claim, never
        # serialized in the queue. Service owns Agent semantics and cancellation.
        service = await asyncio.to_thread(self._service_factory)
        await service.execute_claimed(job)
