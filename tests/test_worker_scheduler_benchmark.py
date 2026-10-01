import asyncio
import json
from types import SimpleNamespace

import pytest

from scripts.benchmarks.worker_002_runtime import SchedulerProbe,MAX_RECORDS,overlap_ms
from scripts.benchmarks.scale_002_runtime import BenchmarkFailure
from scripts.benchmarks.scale_002_stats import validate_report

def test_job_time_overlaps_are_independent_not_additive():
    windows=[(1.,3.),(2.,4.)]
    assert overlap_ms(windows,[(1.,2.),(3.,4.)])==2000
    assert overlap_ms(windows,[(2.,3.)])==2000
    assert overlap_ms(windows,[(0.,5.)])==4000

def test_capacity_overlap_does_not_assign_a_future_worker():
    probe=SchedulerProbe()
    probe.started=0.; probe.ended=4.
    probe.records=[(0.,0,2,0,0),(1.,2,0,0,2),(3.,0,1,1,0),(4.,0,2,0,0)]
    jobs=[SimpleNamespace(job_id='job_synthetic')]
    observer=SimpleNamespace(jobs={'job_synthetic':{'created':.5,'claimed':3.5}})
    result=probe.result(jobs,observer,2)
    assert result['queue_job_ms']==3000
    assert result['queue_overlaps_ms']=={'full_service_capacity':2000,'any_idle_consumer':1000,
        'any_claim_attempt':500,'any_provider_call':2000}
    assert result['active_worker_utilization']==.5
    assert result['peak_active_owners']==2
    assert result['second_claim_from_first_commit_ms'] is None
    assert result['successful_claim_ms']['p95'] is None
    validate_report(result)
    encoded=json.dumps(result,allow_nan=False)
    assert 'job_synthetic' not in encoded

def test_record_budget_and_negative_state_fail_closed():
    probe=SchedulerProbe()
    probe.measuring=True
    probe.records=[(0.,0,0,0,0)]*MAX_RECORDS
    with pytest.raises(BenchmarkFailure,match='scheduler_record_budget'): probe.state()
    probe.records=[]; probe.idle=-1
    with pytest.raises(BenchmarkFailure,match='negative_scheduler_state'): probe.state()

def test_idle_barrier_uses_current_state():
    async def run():
        probe=SchedulerProbe(); probe.idle=2
        await probe.all_idle(2)
        probe.idle=0
        waiting=asyncio.create_task(probe.all_idle(2))
        await asyncio.sleep(0)
        assert not waiting.done()
        probe.idle=2; probe.state()
        await asyncio.wait_for(waiting,1)
    asyncio.run(run())
