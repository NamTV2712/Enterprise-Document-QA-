"""WORKER-002 controlled arrivals and occupancy, using unchanged SCALE/OBS gates."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import tempfile
import time
from dataclasses import asdict,dataclass
from pathlib import Path
from statistics import median
from unittest.mock import patch

from scripts.benchmarks import obs_001 as obs,scale_002 as scale
from scripts.benchmarks.scale_002_stats import environment,validate_report
if __package__:
    from .worker_002_runtime import SchedulerProbe,observe_scheduler,custom_trial
else:
    from worker_002_runtime import SchedulerProbe,observe_scheduler,custom_trial

CAMPAIGN='worker-002-v1'

@dataclass(frozen=True)
class Point:
    name:str
    kind:str
    workers:int=2
    clients:int=1
    operations:int=20
    delay_ms:int=0
    poll_ms:int=500
    arrival_ms:int=0
    trials:int=3

    def scenario(self):
        profile=self.kind if self.kind in ('research','mixed') else 'worker'
        return obs.ObservedScenario(profile,concurrency=self.clients,workers=self.workers,
            operations=self.operations,latency_ms=self.delay_ms,poll_ms=self.poll_ms,trials=self.trials)

def points():
    return [Point(f'single-poll-{p}','single',poll_ms=p) for p in (100,250,500,1000)] + [
        Point(f'stagger-{a}','staggered',arrival_ms=a) for a in (50,100,250,750)] + [
        Point(f'burst-{n}','burst',workers=1,clients=n,operations=n) for n in (1,2,5,10,25,50)] + [
        Point('research-10-250','research',clients=10,delay_ms=250),
        Point('mixed-25-250','mixed',clients=25,operations=25,delay_ms=250)] + [
        Point(f'workers-{n}-delay-{delay}','worker',workers=n,clients=25,operations=25,delay_ms=delay)
        for delay in (250,0) for n in (1,2,4,8)] + [Point('idle','idle'),Point('restart','restart',clients=20)]

def scheduler_summary(trials):
    values=[t['scheduler'] for t in trials]
    result={'aggregation':'median_of_trial_statistics','counts_per_trial':[v['counts'] for v in values],
            'whole_trial_counts':[v['whole_trial_counts'] for v in values]}
    for name in ('window_seconds','empty_claims_per_second','active_worker_utilization','provider_call_seconds',
        'peak_provider_calls','peak_active_owners','queue_job_ms','first_claim_from_first_commit_ms',
        'second_claim_from_first_commit_ms'):
        result[name]=median(v[name] for v in values) if all(v[name] is not None for v in values) else None
    result['queue_overlaps_ms']={k:median(v['queue_overlaps_ms'][k] for v in values) for k in values[0]['queue_overlaps_ms']}
    for name in ('global_commit_to_next_attempt_ms','successful_claim_ms','later_successful_claim_ms','idle_wait_ms'):
        result[name]={k:median(v[name][k] for v in values) if all(v[name][k] is not None for v in values) else None
                      for k in ('p50','p95','p99','max')}
        result[name]['samples_per_trial']=[v[name]['samples'] for v in values]
    return result

async def measured_trial(point,directory,index):
    probe=SchedulerProbe()
    async with observe_scheduler(probe):
        if point.kind in ('worker','research','mixed'):
            result=await obs.trial(point.scenario(),directory,index,enabled=True)
            result['scheduler']=probe.result(probe.jobs,probe.bench.observer,point.workers)
        else:
            async def controlled(scenario,destination,trial_index):
                return await custom_trial(scenario,destination,trial_index,kind=point.kind,
                    probe=probe,arrival_ms=point.arrival_ms,idle_seconds=.3 if point.operations==2 else 4)
            with patch.object(scale,'trial',controlled):
                result=await obs.trial(point.scenario(),directory,index,enabled=True)
    validate_report(result)
    return result

async def campaign(output,*,stage,smoke=False,selected=None,max_seconds=3600):
    source=Path(__file__).parent
    digest=hashlib.sha256(b''.join((source/n).read_bytes() for n in ('worker_002.py','worker_002_runtime.py'))).hexdigest()
    report={'campaign':CAMPAIGN,'stage':stage,**obs.binding(),'driver_sha256':digest,
        'protocol':obs.PROTOCOL,'scale_protocol':'scale-002-benchmark-v1','db_protocol':'db-scale-001-v1',
        'environment':environment(),'status':'incomplete','scenarios':[]}
    if not smoke and not report['tracked_clean']: raise ValueError('canonical runtime must be tracked clean')
    output.parent.mkdir(parents=True,exist_ok=True)
    def save():
        validate_report(report)
        output.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    started=time.perf_counter(); save()
    matrix=points()
    if selected: matrix=[p for p in matrix if p.name in selected]
    if not matrix: raise ValueError('empty campaign')
    if smoke: matrix=[Point(p.name,p.kind,workers=1,clients=2,operations=2,delay_ms=5,
        arrival_ms=5,trials=1) for p in matrix]
    for point in matrix:
        row={'binding':asdict(point),'scale_binding':point.scenario().binding(),'enabled':True,'trials':[]}
        report['scenarios'].append(row)
        for index in range(1,point.trials+1):
            remaining=max_seconds-(time.perf_counter()-started)
            if remaining<=0: raise TimeoutError('campaign deadline')
            with tempfile.TemporaryDirectory(prefix='worker002-') as directory:
                try: result=await asyncio.wait_for(measured_trial(point,Path(directory),index),min(remaining,330))
                except Exception as error:
                    row['failure_category']='timeout' if isinstance(error,TimeoutError) else 'correctness_or_runtime'
                    save(); raise
            row['trials'].append(result); save()
            print(f'{stage} {point.name} trial={index} PASS',flush=True)
        row['summary']=obs.summarize(row['trials'])
        row['scheduler_summary']=scheduler_summary(row['trials'])
        save()
    report['status']='complete'; save()
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',required=True,choices=('before','after','diagnostic'))
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--points',nargs='+')
    args=parser.parse_args()
    try: asyncio.run(campaign(args.output,stage=args.stage,smoke=args.smoke,selected=args.points))
    except Exception:
        print('WORKER-002 campaign incomplete; inspect bounded checkpoint.',flush=True)
        raise SystemExit(1) from None

if __name__=='__main__': main()
