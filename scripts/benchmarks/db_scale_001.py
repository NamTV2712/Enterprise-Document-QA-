"""DB-SCALE-001 comparable enabled anchors through the committed OBS harness."""
import argparse
import asyncio
import hashlib
import json
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

from scripts.benchmarks import obs_001 as obs
from scripts.benchmarks.scale_002_stats import environment, validate_report
from src.workspace.database import WorkspaceDatabase

CAMPAIGN = 'db-scale-001-v1'

async def measured_trial(scenario, directory, index):
    counters = {'initialize_calls': 0, 'ensure_calls': 0, 'expensive_initializations': 0}
    lock = threading.Lock()
    def counted(name, operation):
        def run(database, *args, **kwargs):
            with lock:
                counters[name] += 1
            return operation(database, *args, **kwargs)
        return run
    with patch.object(WorkspaceDatabase, 'initialize', counted('initialize_calls', WorkspaceDatabase.initialize)), \
         patch.object(WorkspaceDatabase, '_initialize_locked', counted('expensive_initializations', WorkspaceDatabase._initialize_locked)):
        if hasattr(WorkspaceDatabase, 'ensure_initialized'):
            with patch.object(WorkspaceDatabase, 'ensure_initialized', counted('ensure_calls', WorkspaceDatabase.ensure_initialized)):
                result = await obs.trial(scenario, directory, index, enabled=True)
        else:
            result = await obs.trial(scenario, directory, index, enabled=True)
    result['initialization'] = {'scope': 'whole_trial_including_startup_warmup_reopen', **counters}
    return result

async def campaign(output, *, smoke=False, stage, max_seconds=1200):
    report = {'campaign': CAMPAIGN, 'protocol': obs.PROTOCOL, 'scale_protocol': 'scale-002-benchmark-v1',
              'stage': stage, **obs.binding(), 'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'environment': environment(), 'status': 'incomplete', 'scenarios': []}
    if not smoke and not report['tracked_clean']:
        raise ValueError('canonical campaign requires clean committed runtime')
    output.parent.mkdir(parents=True, exist_ok=True)
    started=time.perf_counter()
    def save():
        validate_report(report)
        output.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    save()
    scenarios=[obs.anchors()[i] for i in (1,4,5,3,0)]
    if smoke:
        scenarios=[obs.ObservedScenario(x.profile,concurrency=2,operations=2,trials=1,warmup=1,latency_ms=5 if x.latency_ms else 0) for x in scenarios]
    for scenario in scenarios:
        row={'binding':scenario.binding(),'enabled':True,'trials':[]}
        report['scenarios'].append(row)
        for index in range(1,scenario.trials+1):
            remaining=max_seconds-(time.perf_counter()-started)
            if remaining<=0: raise TimeoutError('campaign deadline')
            with tempfile.TemporaryDirectory(prefix='dbscale001-') as temp:
                try:
                    result=await asyncio.wait_for(measured_trial(scenario,Path(temp),index),min(remaining,scenario.timeout_seconds+90))
                except Exception as error:
                    row['failure_category']='timeout' if isinstance(error,TimeoutError) else 'correctness_or_runtime'
                    save()
                    raise
            row['trials'].append(result)
            save()
            print(f'{stage} {scenario.profile} clients={scenario.concurrency} trial={index} PASS',flush=True)
        row['summary']=obs.summarize(row['trials'])
        row['initialization_per_trial']=[t['initialization'] for t in row['trials']]
        save()
    report['status']='complete'
    save()
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--stage',required=True,choices=['before','after','diagnostic'])
    parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    try:
        asyncio.run(campaign(args.output,smoke=args.smoke,stage=args.stage))
    except Exception:
        print('DB-SCALE-001 campaign incomplete; inspect the bounded checkpoint.',flush=True)
        raise SystemExit(1) from None

if __name__=='__main__': main()
