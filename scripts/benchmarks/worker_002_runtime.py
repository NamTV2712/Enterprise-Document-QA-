"""Bounded benchmark-only scheduler facts; durable commits remain authoritative."""
from __future__ import annotations

import asyncio
import time
from collections import Counter
from contextlib import ExitStack, asynccontextmanager
from unittest.mock import patch

import httpx

from scripts.benchmarks import scale_002 as scale, scale_002_runtime as runtime
from scripts.benchmarks.scale_002_stats import lifecycle_durations, percentiles, throughput
from src.workspace.worker import WorkerSupervisor

MAX_RECORDS = 65536
WAKE_REASONS = frozenset({'startup', 'poll_timeout', 'durable_admission_signal', 'shutdown'})
COUNTERS = ('startup','poll_timeout','durable_admission_signal','shutdown','successful_claims',
            'empty_claims','signal_attempts','signals_accepted','signals_ignored','coalesced_signals')


def overlap_ms(windows, intervals):
    """Intersect disjoint state intervals with each queue window; job-time weighted."""
    return sum(max(0.0, min(b, d)-max(a, c))*1000 for a,b in windows for c,d in intervals)


class SchedulerProbe:
    def __init__(self):
        self.active = self.idle = self.claiming = self.providers = 0
        self.changed = asyncio.Event()
        self.bench = None
        self.measuring = False
        self.records = []
        self.claims = []
        self.idles = []
        self.counts = Counter()
        self.whole_counts = Counter()
        self.jobs = []
        self.peak_provider = 0
        self.started = self.ended = None

    def state(self):
        if min(self.active,self.idle,self.claiming,self.providers)<0:
            raise runtime.BenchmarkFailure('negative_scheduler_state')
        self.changed.set()
        if self.measuring:
            if len(self.records)>=MAX_RECORDS:
                raise runtime.BenchmarkFailure('scheduler_record_budget')
            self.records.append((time.perf_counter(),self.active,self.idle,self.claiming,self.providers))
            self.peak_provider=max(self.peak_provider,self.providers)

    def begin(self):
        self.records=[]; self.claims=[]; self.idles=[]; self.counts=Counter()
        self.peak_provider=self.providers
        self.started=time.perf_counter(); self.ended=None
        self.measuring=True
        self.state()

    def finish(self):
        self.ended=time.perf_counter()
        self.state()
        self.measuring=False

    async def all_idle(self,capacity):
        async def wait():
            while self.idle<capacity:
                self.changed.clear()
                await self.changed.wait()
        await asyncio.wait_for(wait(),10)

    def result(self, jobs, observer, capacity):
        if self.ended is None:
            raise runtime.BenchmarkFailure('scheduler_window_missing')
        intervals=list(zip(self.records,self.records[1:]))
        select=lambda predicate:[(a[0],b[0]) for a,b in intervals if predicate(a)]
        full=select(lambda a:a[1]>=capacity)
        any_idle=select(lambda a:a[2]>0)
        any_claim=select(lambda a:a[3]>0)
        provider=select(lambda a:a[4]>0)
        rows=[observer.jobs[job.job_id] for job in jobs]
        windows=[(r['created'],r['claimed']) for r in rows if 'claimed' in r]
        total=sum((b-a)*1000 for a,b in windows)
        span=self.ended-self.started
        busy_worker_seconds=sum((b[0]-a[0])*a[1] for a,b in intervals)
        provider_call_seconds=sum((b[0]-a[0])*a[4] for a,b in intervals)
        ordered=sorted(r['claimed'] for r in rows if 'claimed' in r)
        first_created=min((r['created'] for r in rows),default=None)
        successful=[r for r in self.claims if r[2]]
        later=sorted(successful,key=lambda r:r[0])[2:]
        attempts=sorted(r[0] for r in self.claims)
        opportunity=[]
        for row in rows:
            next_start=next((s for s in attempts if s>=row['created']),None)
            if next_start is not None: opportunity.append((next_start-row['created'])*1000)
        facts={'version':'worker-002-scheduler-facts-v1','window_seconds':span,
            'records':len(self.records),'counts':{k:self.counts[k] for k in COUNTERS},
            'whole_trial_counts':{k:self.whole_counts[k] for k in COUNTERS},
            'empty_claims_per_second':self.counts['empty_claims']/span if span else None,
            'active_worker_utilization':busy_worker_seconds/(span*capacity) if span else None,
            'provider_call_seconds':provider_call_seconds,'peak_provider_calls':self.peak_provider,
            'peak_active_owners':max((r[1] for r in self.records),default=0),
            'queue_job_ms':total,'queue_overlaps_ms':{
                'full_service_capacity':overlap_ms(windows,full),
                'any_idle_consumer':overlap_ms(windows,any_idle),
                'any_claim_attempt':overlap_ms(windows,any_claim),
                'any_provider_call':overlap_ms(windows,provider)},
            'first_claim_from_first_commit_ms':(ordered[0]-first_created)*1000 if ordered else None,
            'second_claim_from_first_commit_ms':(ordered[1]-first_created)*1000 if len(ordered)>1 else None,
            'global_commit_to_next_attempt_ms':percentiles(opportunity),
            'successful_claim_ms':percentiles([(b-a)*1000 for a,b,_ in successful]),
            'later_successful_claim_ms':percentiles([(b-a)*1000 for a,b,_ in later]),
            'idle_wait_ms':percentiles([(b-a)*1000 for a,b,_ in self.idles])}
        if facts['peak_active_owners']>capacity or facts['peak_provider_calls']>capacity:
            raise runtime.BenchmarkFailure('scheduler_capacity_gate')
        return facts


@asynccontextmanager
async def observe_scheduler(probe):
    original_runtime=scale.runtime
    original_reset=runtime.Observer.reset
    original_verify=scale.verify_jobs
    original_idle=WorkerSupervisor._idle
    original_claim=WorkerSupervisor._claim
    original_execute=WorkerSupervisor._execute
    original_worker=WorkerSupervisor._worker
    original_transport=httpx.MockTransport.handle_async_request

    def reset(observer):
        original_reset(observer)
        if probe.bench is not None and probe.bench.observer is observer: probe.begin()

    @asynccontextmanager
    async def observed_runtime(scenario,directory):
        async with original_runtime(scenario,directory) as bench:
            probe.bench=bench
            yield bench

    async def verify(*args,**kwargs):
        probe.finish()
        result=await original_verify(*args,**kwargs)
        probe.jobs=result[0]
        return result

    async def worker(supervisor):
        probe.whole_counts['startup']+=1
        if probe.measuring: probe.counts['startup']+=1
        return await original_worker(supervisor)

    async def idle(supervisor):
        began=time.perf_counter()
        probe.idle+=1; probe.state()
        try:
            reason=await original_idle(supervisor)
            if reason is None: reason='shutdown' if supervisor._stop.is_set() else 'poll_timeout'
            if reason not in WAKE_REASONS: raise runtime.BenchmarkFailure('unknown_wake_reason')
            probe.whole_counts[reason]+=1
            if probe.measuring:
                if len(probe.idles)>=MAX_RECORDS: raise runtime.BenchmarkFailure('idle_record_budget')
                probe.idles.append((max(began,probe.started),time.perf_counter(),reason)); probe.counts[reason]+=1
        finally:
            probe.idle-=1; probe.state()

    async def claim(supervisor):
        began=time.perf_counter()
        probe.claiming+=1; probe.state()
        job=None
        try:
            job=await original_claim(supervisor)
            probe.whole_counts['successful_claims' if job is not None else 'empty_claims']+=1
            if probe.measuring:
                if len(probe.claims)>=MAX_RECORDS: raise runtime.BenchmarkFailure('claim_record_budget')
                probe.claims.append((max(began,probe.started),time.perf_counter(),job is not None))
                probe.counts['successful_claims' if job is not None else 'empty_claims']+=1
            return job
        finally:
            probe.claiming-=1; probe.state()

    async def execute(supervisor,job):
        probe.active+=1; probe.state()
        try: return await original_execute(supervisor,job)
        finally: probe.active-=1; probe.state()

    async def transport(mock,request):
        if runtime.CURRENT_JOB.get() is None:
            return await original_transport(mock,request)
        probe.providers+=1; probe.state()
        try: return await original_transport(mock,request)
        finally: probe.providers-=1; probe.state()

    with ExitStack() as stack:
        for owner,name,value in [(runtime.Observer,'reset',reset),(scale,'runtime',observed_runtime),
            (scale,'verify_jobs',verify),(WorkerSupervisor,'_idle',idle),
            (WorkerSupervisor,'_claim',claim),(WorkerSupervisor,'_execute',execute),
            (WorkerSupervisor,'_worker',worker),
            (httpx.MockTransport,'handle_async_request',transport)]:
            stack.enter_context(patch.object(owner,name,value))
        if hasattr(WorkerSupervisor,'notify_work'):
            original_notify=WorkerSupervisor.notify_work
            def notify(supervisor):
                already_set=supervisor._wake.is_set()
                result=original_notify(supervisor)
                probe.whole_counts['signal_attempts']+=1
                probe.whole_counts['signals_accepted' if result else 'signals_ignored']+=1
                if result and already_set: probe.whole_counts['coalesced_signals']+=1
                if probe.measuring:
                    probe.counts['signal_attempts']+=1
                    probe.counts['signals_accepted' if result else 'signals_ignored']+=1
                    if result and already_set: probe.counts['coalesced_signals']+=1
                return result
            stack.enter_context(patch.object(WorkerSupervisor,'notify_work',notify))
        yield


async def custom_trial(scenario,directory,index,*,kind,probe,arrival_ms=0,idle_seconds=4):
    """Same real runtime/commits/gates/statistics as SCALE; controlled arrivals."""
    async with scale.runtime(scenario,directory) as bench:
        warm=await runtime.bounded_map(scenario.warmup,min(scenario.workers,scenario.concurrency),
            lambda i:bench.create(f'warmup-{i}'))
        await bench.wait_terminal(warm,idle=True)
        for i in range(4): await bench.read(warm[0],i)
        await probe.all_idle(scenario.workers)
        bench.observer.reset()
        bench.request_ms.clear(); bench.statuses.clear(); bench.endpoint_ms.clear()
        bench.sse.clear(); bench.delivery_ms.clear(); bench.entered.clear(); bench.loop_lag_ms.clear()
        bench.measuring=True; bench.observer.measuring=True
        started,cpu_started=time.perf_counter(),time.process_time()
        ids=[]
        if kind=='single':
            for i in range(scenario.operations):
                await probe.all_idle(scenario.workers)
                identifier=await bench.create(f'measured-{i}')
                ids.append(identifier)
                await bench.wait_terminal([identifier],idle=True)
        elif kind=='staggered':
            for i in range(scenario.operations):
                target=started+i*arrival_ms/1000
                await asyncio.sleep(max(0,target-time.perf_counter()))
                ids.append(await bench.create(f'measured-{i}'))
            await bench.wait_terminal(ids,idle=True)
        elif kind in ('burst','restart'):
            if kind=='restart':
                previous=bench.pool
                bench.application._state.pop('worker_supervisor',None)
                await previous.stop()
            ids=await runtime.bounded_map(scenario.operations,scenario.concurrency,
                lambda i:bench.create(f'measured-{i}'))
            if kind=='restart':
                from src.workspace.executors import AgentJobExecutor,ExecutorRegistry
                from src.workspace.jobs import SQLiteJobRepository
                from src.workspace.worker import WorkerConfig
                repository=SQLiteJobRepository.from_settings(bench.application.settings)
                fresh=WorkerSupervisor(repository,ExecutorRegistry((AgentJobExecutor(
                    lambda:bench.application._agent_service_for_repository(repository)),)),
                    WorkerConfig(scenario.workers,scenario.poll_ms,5000),attribution_enabled=True,
                    attribution_sink=bench.application._publish_performance)
                bench.application._state['worker_supervisor']=fresh
                await fresh.start()
            await bench.wait_terminal(ids,idle=True)
        elif kind=='idle': await asyncio.sleep(idle_seconds)
        else: raise ValueError('unsupported controlled workload')
        elapsed,cpu=time.perf_counter()-started,time.process_time()-cpu_started
        bench.measuring=False; bench.observer.measuring=False
        expected={'succeeded':len(ids)} if ids else {}
        jobs,correctness=await scale.verify_jobs(bench,ids,expected,len(warm))
        queue=[]; service=[]; e2e=[]
        for job in jobs:
            row=bench.observer.jobs[job.job_id]
            q,s,e=lifecycle_durations(row['created'],row['claimed'],row['terminal'])
            queue.append(q); service.append(s); e2e.append(e)
        rows=[bench.observer.jobs[j.job_id] for j in jobs]
        drain=max(r['terminal'] for r in rows)-min(r['created'] for r in rows) if rows else None
        successes=sum(bench.statuses.values())
        result={'status':'complete','trial':index,'operations':scenario.operations,
            'warmup_operations':len(warm),'request_count':successes,'successes':successes,
            'failures':0,'expected_rejections':0,'unexpected_5xx':0,
            'status_distribution':dict(bench.statuses),'elapsed_seconds':elapsed,
            'requests_per_second':throughput(successes,elapsed),'jobs_per_second':throughput(len(ids),drain) if drain else None,
            'drain_ms':drain*1000 if drain is not None else None,
            'peak_active_workers':bench.observer.peak_active,'peak_queue_depth':bench.observer.peak_queue,
            'peak_worker_tasks_sampled':bench.peak_worker_tasks,'cpu_seconds':cpu,'cpu_core_equivalents':cpu/elapsed,
            'peak_rss_bytes':bench.peak_rss_bytes,'resource_scope':'combined_server_client_same_process',
            'sse':dict(bench.sse),'decision_calls':sum(bench.observer.calls.values()),'failure_injections':0,
            'correctness':correctness,'endpoint_ms':{n:percentiles(v) for n,v in bench.endpoint_ms.items()},
            'scheduler':probe.result(jobs,bench.observer,scenario.workers)}
        for name,values in {'request_ms':bench.request_ms,'queue_wait_ms':queue,'service_ms':service,
            'end_to_end_ms':e2e,'claim_ms':bench.observer.claim_ms,'write_transaction_ms':bench.observer.transaction_ms,
            'write_lock_wait_ms':bench.observer.lock_wait_ms,'provider_ms':bench.observer.provider_ms,
            'tool_ms':bench.observer.tool_ms,'event_delivery_ms':bench.delivery_ms,'loop_lag_ms':bench.loop_lag_ms}.items():
            result[name]=percentiles(values)
        return result
