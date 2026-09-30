"""Explicit worker execution for API tests that intentionally omit lifespan."""

import asyncio

from src.workspace.executors import AgentJobExecutor, ExecutorRegistry
from src.workspace.worker import WorkerConfig, WorkerSupervisor


def finish_agent_with_worker(service, run_id):
    async def exercise():
        done = asyncio.Event()

        class Executor(AgentJobExecutor):
            async def execute(self, job):
                try:
                    await super().execute(job)
                finally:
                    done.set()

        worker = WorkerSupervisor(service.repository, ExecutorRegistry((Executor(lambda: service),)),
                                  WorkerConfig(concurrency=1))
        await worker.start()
        try:
            await asyncio.wait_for(done.wait(), 10)
        finally:
            await worker.stop()
        return service.get(run_id)

    return asyncio.run(exercise())
