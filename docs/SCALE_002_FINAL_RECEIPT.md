# SCALE-002 final receipt

**SCALE-002 COMPLETE.** Source validation complete; exact final-HEAD release verification follows this documentation commit. Measured 2026-09-30 / 2026-10-01.
This characterizes the development environment, with no production SLA or maximum-user claim.

## Identity and scope

Starting HEAD: `009b04e699bc9e61b4dd37722076e1ad6237c567`.
Branch: `codex/bilingual-research-workspace`.
**Benchmarked runtime: `23702743ee6e3e807dad4004c68ff77cb6006bef`**
(`test(scale): add reproducible load benchmark harness`).
Harness bytes SHA256: `bf27f4274f3ffecc1d69d7192d9f2feb376c326c6e95a38b623ea38efd91556c`.
The final chat release receipt records the final documentation SHA, its clean gate
and exact normal push verification, avoiding a self-referential commit hash.
Final closure changes only documentation. Later reports truthfully bind
tracked_clean=false: only the protocol's telemetry/stage clarification was dirty
during those runs; committed harness/tests and production source were unchanged.

Completed product roadmap, Agent extension, PROVIDER-001 and SCALE-001 remain
complete; SCALE-003 is not started. No production source/frontend/config/default,
dependency/lockfile, route, migration, cache or architecture change. No live/paid
provider call, prior live-smoke retry, broker, distributed worker, new Agent tool
or Ragas work. Temporary databases never enter canonical workspace history.

## Protocol and environment

[scale-002-benchmark-v1](SCALE_002_BENCHMARK_PROTOCOL.md) is the reproduction authority.
Real TCP loopback Uvicorn/httpx, FastAPI/access controls, DATA-004, lifespan-owned
WorkerSupervisor, Agent coordinator/orchestrator, actual Groq SDK mocked HTTP,
tool registry, persisted events and native evaluation remain in the path.
Client/server share one process/event loop: CPU/RSS/lag include both. Existing
telemetry stays enabled; DATA-005 excludes Agent routes, so no persisted Agent
request telemetry writes are claimed. Benchmark logging is suppressed; production
log-volume cost and small instrumentation overhead are not isolated/subtracted.

| Fact | Value |
| --- | --- |
| OS | Windows 10.0.26300 |
| Python / SQLite runtime | 3.12.7 / 3.45.3 |
| Logical CPUs / total RAM | 24 / 16,890,322,944 bytes (15.73 GiB) |
| FastAPI / Starlette | 0.115.0 / 0.38.6 |
| httpx / Uvicorn | 0.28.1 / 0.32.0 |
| Groq SDK / Pydantic | 1.5.0 / 2.13.4 |
| API processes / schema | One / v7 |
| SQLite | WAL/NORMAL, serialized RLock, BEGIN IMMEDIATE claim, busy timeout 5000ms |
| Workers / poll / shutdown grace | Default 2 / 500ms / 5000ms; comparative 1/2/4/8 |
| Resources | stdlib process_time CPU; Windows sampled working set; 20ms loop-lag probe |

Three measured trials per point, each fresh DB/lifespan. Warmup four jobs plus
four read paths; read uses 20 terminal warmup rows, artifact one job; SSE/mixed
also warm a subscription. Warmup, cold imports/startup, audit and DB reopen are
excluded. All elapsed durations use time.perf_counter. Created-event commit to
running-claim commit is queue wait; claim to terminal commit is service; creation
to terminal is end-to-end. The identity holds per run; do not add component
percentiles as if they belonged to the same run.

Summaries are **medians of per-trial statistics**, preserving boundaries, never
pooled heterogeneous samples. Nearest rank: sorted sample at ceil(p*n), one-based.
Minimum samples p50=2, p95=20, p99=100. **NA is insufficient samples, not zero**.
Run p99 is NA across 20/25/50-job series. Peak active/queue below is maximum
across trials; other values, including RSS/lag maxima, are medians of trial values
unless explicitly labeled absolute range/max. Durations below are milliseconds.
Run throughput is succeeded jobs / first creation to last terminal commit;
HTTP throughput is successful requests / measured client interval.

### Executed workloads

| Profile | Definition | Clients | Operations/trial | Workers | Artificial delay/call | Trials |
| --- | --- | --- | --- | --- | --- | --- |
| Admission | POST Agent run, workers disabled | 1,5,10,25,50,100 | 200 | 0 executing | 0ms, no calls | 18 |
| Read | list/detail/result/evaluation evenly | 1,5,10,25,50,100 | 200, 50/endpoint | 2 idle | 0ms, no measured calls | 18 |
| Worker baseline | create, read, final, terminal | 1,2,5,10,25,50 | 20; 25/50 at last levels | 2 | 0 and 250ms | 36 |
| Worker comparison | Same 25-client workload | 25 | 25 | 1,4,8; reuse worker=2 | 0 and 250ms | 18 extra |
| Research | search, read, final, result/evaluation | 1,2,5,10,25,50 | 20; 25/50 at last levels | 2 | 0 and 250ms | 36 |
| SSE | One live research job, finite batches + suffix resume | 1,10,25,50 | One subscriber/client | 2 | 250ms | 12 |
| Mixed | create, list/detail, subscribe, result/evaluation per lane | 5,25,50 | 5/25/50 jobs | 2 | 250ms | 9 |
| Cancel | Six jobs, two queued/one held in-flight cancellations, stale revision | 6 | 6 | 2 | 250ms + barrier | 3 |
| Degraded | First goal selects one mocked 503, no retry | 10 | 20 | 2 | 250ms | 3 |
| Optional artifact | Local discovery/BM25/reader, mocked decisions | 1 | 2 | 2 | 0ms | 3 separate |

**51 hermetic scenarios / 153 complete trials**, plus one artifact scenario /
three trials. Worker=2 comparison reuses the identical baseline point. Lanes
are closed-loop: next request after response, next run after terminal (and research
reads). These are bounded burst/drain tests, not an external arrival-rate/soak test.
Mixed ratio per job: one create, two initial reads, two terminal reads and one
subscriber, with variable batch/resume requests. SSE reconnects every 100ms and
checks a true terminal frame, then resume after event ID 3. No production-traffic
ratio claim. Full-run/SSE 100, workers 16, slow 1000ms and cold-start were not run;
plateaus through 50/8 already give the requested bounded characterization.

Per-trial bound: min(240s, max(30s, 30s + 3*jobs*decisions*synthetic_seconds/workers)).
HTTP 30s, startup 60s, shutdown wait 15s; artifact also has external process deadline.
User interruption stopped the extra sweep at worker=8/250ms with two of three
trials: both old trials remain incomplete and excluded. That entire point was
rerun with three fresh trials. Five earlier points already had complete individual
three-trial boundaries and were retained. No partial result was relabeled complete.
All accepted series share runtime SHA/harness digest; development smokes are excluded.

## Results

## Admission

| Clients | Requests/sec | p50 ms | p95 ms | p99 ms | Failures (3 trials) |
| --- | --- | --- | --- | --- | --- |
| 1 | 62.04 | 14.00 | 21.92 | 26.86 | 0 |
| 5 | 59.14 | 73.74 | 133.90 | 272.02 | 0 |
| 10 | 57.03 | 161.27 | 314.05 | 338.85 | 0 |
| 25 | 65.56 | 309.41 | 745.49 | 1036.03 | 0 |
| 50 | 53.91 | 500.37 | 2759.33 | 3512.53 | 0 |
| 100 | 57.57 | 1024.00 | 3216.14 | 3459.35 | 0 |

## Read

| Clients | Requests/sec | p50 ms | p95 ms | p99 ms | Failures (3 trials) |
| --- | --- | --- | --- | --- | --- |
| 1 | 57.68 | 16.74 | 29.66 | 37.16 | 0 |
| 5 | 61.52 | 77.30 | 134.42 | 151.38 | 0 |
| 10 | 62.07 | 148.73 | 250.64 | 279.93 | 0 |
| 25 | 61.01 | 380.68 | 663.86 | 891.59 | 0 |
| 50 | 57.76 | 665.45 | 1987.34 | 2788.12 | 0 |
| 100 | 56.95 | 1146.44 | 3346.40 | 3470.85 | 0 |

## Worker

| Clients | Workers | Delay/call ms | Jobs/trial | Jobs/sec | Queue p95 ms | Service p95 ms | E2E p95 ms | Peak active | Peak queue | Drain ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2 | 0 | 20 | 4.26 | 421.89 | 43.04 | 463.11 | 1 | 1 | 4689.46 |
| 2 | 2 | 0 | 20 | 9.70 | 412.20 | 100.74 | 535.52 | 2 | 2 | 2062.66 |
| 5 | 2 | 0 | 20 | 11.15 | 535.72 | 134.81 | 640.85 | 2 | 5 | 1793.56 |
| 10 | 2 | 0 | 20 | 11.28 | 853.14 | 192.76 | 1057.73 | 2 | 10 | 1773.76 |
| 1 | 2 | 250 | 20 | 1.46 | 472.29 | 579.31 | 1048.03 | 1 | 1 | 13732.85 |
| 2 | 2 | 250 | 20 | 2.31 | 521.11 | 610.82 | 1093.69 | 2 | 2 | 8672.47 |
| 5 | 2 | 250 | 20 | 3.11 | 1281.74 | 646.89 | 1889.35 | 2 | 5 | 6425.65 |
| 10 | 2 | 250 | 20 | 3.07 | 2790.28 | 645.82 | 3414.62 | 2 | 10 | 6507.47 |
| 25 | 2 | 0 | 25 | 13.13 | 1336.42 | 224.71 | 1421.42 | 2 | 25 | 1903.75 |
| 25 | 2 | 250 | 25 | 3.06 | 6760.21 | 624.32 | 7309.02 | 2 | 25 | 8171.90 |
| 50 | 2 | 0 | 50 | 12.14 | 2814.48 | 268.05 | 3082.53 | 2 | 47 | 4119.85 |
| 50 | 2 | 250 | 50 | 3.25 | 13287.94 | 648.52 | 13889.64 | 2 | 48 | 15379.03 |
| 25 | 1 | 0 | 25 | 16.98 | 1068.98 | 36.52 | 1103.21 | 1 | 25 | 1472.74 |
| 25 | 4 | 0 | 25 | 14.10 | 1189.35 | 217.54 | 1353.52 | 4 | 25 | 1773.21 |
| 25 | 8 | 0 | 25 | 13.34 | 1048.17 | 598.94 | 1394.16 | 8 | 21 | 1874.10 |
| 25 | 1 | 250 | 25 | 1.74 | 12934.17 | 571.62 | 13501.59 | 1 | 25 | 14396.73 |
| 25 | 4 | 250 | 25 | 5.21 | 3392.75 | 697.10 | 4181.40 | 4 | 25 | 4802.23 |
| 25 | 8 | 250 | 25 | 8.52 | 1535.08 | 724.14 | 2255.08 | 8 | 25 | 2932.94 |

## Research

| Clients | Workers | Delay/call ms | Jobs/trial | Jobs/sec | Queue p95 ms | Service p95 ms | E2E p95 ms | Peak active | Peak queue | Drain ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2 | 0 | 20 | 1.87 | 477.06 | 52.77 | 523.87 | 1 | 1 | 10684.29 |
| 2 | 2 | 0 | 20 | 3.72 | 491.14 | 134.83 | 604.51 | 2 | 2 | 5370.55 |
| 5 | 2 | 0 | 20 | 7.71 | 575.47 | 209.60 | 733.29 | 2 | 5 | 2594.51 |
| 10 | 2 | 0 | 20 | 7.98 | 1082.80 | 228.39 | 1297.28 | 2 | 10 | 2504.94 |
| 1 | 2 | 250 | 20 | 0.85 | 479.04 | 838.43 | 1286.21 | 1 | 1 | 23554.13 |
| 2 | 2 | 250 | 20 | 1.62 | 463.90 | 877.22 | 1293.34 | 2 | 2 | 12368.86 |
| 5 | 2 | 250 | 20 | 2.19 | 1747.27 | 909.94 | 2578.61 | 2 | 5 | 9123.37 |
| 10 | 2 | 250 | 20 | 2.20 | 3559.31 | 897.66 | 4516.85 | 2 | 10 | 9108.25 |
| 25 | 2 | 0 | 25 | 7.86 | 2433.64 | 337.89 | 2773.94 | 2 | 25 | 3180.07 |
| 25 | 2 | 250 | 25 | 2.19 | 9802.50 | 898.46 | 10632.56 | 2 | 25 | 11439.21 |
| 50 | 2 | 0 | 50 | 8.29 | 4904.88 | 317.37 | 5054.78 | 2 | 48 | 6028.44 |
| 50 | 2 | 250 | 50 | 2.26 | 19721.69 | 907.66 | 20521.86 | 2 | 48 | 22147.54 |

## SSE

| Subscribers/trial | Successful (3 trials) | Delivery p50 ms | p95 ms | p99 ms | Loop p95 ms |
| --- | --- | --- | --- | --- | --- |
| 1 | 3 | 29.73 | NA | NA | 26.89 |
| 10 | 30 | 88.14 | 195.63 | NA | 13.26 |
| 25 | 75 | 236.88 | 422.79 | 473.38 | 12.26 |
| 50 | 150 | 492.80 | 809.92 | 943.59 | 12.00 |

## Mixed

| Clients | Jobs/trial | Succeeded jobs/sec | Queue p95 ms | Service p95 ms | E2E p95 ms | Drain ms | Terminals (3 trials) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 5 | 1.63 | NA | NA | NA | 3075.96 | {'succeeded': 15, 'cancelled': 0, 'failed': 0} |
| 25 | 25 | 1.45 | 15235.15 | 1884.51 | 16229.85 | 17246.98 | {'succeeded': 75, 'cancelled': 0, 'failed': 0} |
| 50 | 50 | 1.06 | 43635.37 | 2842.57 | 44428.16 | 47003.39 | {'succeeded': 150, 'cancelled': 0, 'failed': 0} |

## Cancel

| Clients | Jobs/trial | Succeeded jobs/sec | Queue p95 ms | Service p95 ms | E2E p95 ms | Drain ms | Terminals (3 trials) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | 6 | 2.28 | NA | NA | NA | 1314.70 | {'succeeded': 9, 'cancelled': 9, 'failed': 0} |

## Degraded

| Clients | Jobs/trial | Succeeded jobs/sec | Queue p95 ms | Service p95 ms | E2E p95 ms | Drain ms | Terminals (3 trials) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 20 | 2.93 | 2491.00 | 614.10 | 3090.50 | 6473.61 | {'succeeded': 57, 'cancelled': 0, 'failed': 3} |

## SQLite and resources

| Profile | Clients | Workers | Delay ms | Claim p95 ms | Txn p95 ms | Lock p95 ms | Loop p50 ms | Loop p95 ms | Loop max ms | CPU cores | Peak RSS MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| admission | 1 | 2 | 0 | NA | 2.18 | 0.00 | 0.00 | 3.34 | 18.33 | 0.85 | 749.33 |
| admission | 100 | 2 | 0 | NA | 3.53 | 7.83 | 11.21 | 43.80 | 206.27 | 0.94 | 778.83 |
| read | 1 | 2 | 0 | NA | NA | 1.06 | 0.00 | 7.71 | 21.35 | 0.96 | 758.17 |
| read | 100 | 2 | 0 | NA | NA | 92.47 | 9.14 | 92.34 | 200.89 | 0.98 | 798.21 |
| worker | 25 | 2 | 0 | 17.38 | 2.79 | 9.92 | 1.53 | 27.76 | 67.40 | 0.75 | 762.62 |
| worker | 25 | 2 | 250 | 19.56 | 3.47 | 7.31 | 10.92 | 22.80 | 50.96 | 0.19 | 777.62 |
| worker | 25 | 1 | 0 | 4.24 | 1.70 | 2.96 | 0.00 | 20.20 | 33.15 | 0.84 | 760.89 |
| worker | 25 | 4 | 0 | 34.03 | 2.49 | 15.73 | 8.91 | 42.96 | 59.31 | 0.66 | 778.04 |
| worker | 25 | 8 | 0 | 38.82 | 2.67 | 30.19 | 26.91 | 103.21 | 128.09 | 0.71 | 787.68 |
| worker | 25 | 1 | 250 | 5.92 | 3.40 | 2.91 | 10.94 | 17.35 | 35.10 | 0.11 | 794.29 |
| worker | 25 | 4 | 250 | 37.92 | 3.31 | 13.76 | 10.76 | 25.73 | 105.11 | 0.34 | 803.43 |
| worker | 25 | 8 | 250 | 27.80 | 2.73 | 16.13 | 11.00 | 36.80 | 101.12 | 0.44 | 770.11 |
| mixed | 5 | 2 | 250 | NA | 3.95 | 45.94 | 1.71 | 18.39 | 66.50 | 0.47 | 758.76 |
| mixed | 25 | 2 | 250 | 350.20 | 5.93 | 261.17 | 0.00 | 27.61 | 312.44 | 0.81 | 781.25 |
| mixed | 50 | 2 | 250 | 42.59 | 6.63 | 540.39 | 0.00 | 31.18 | 736.83 | 0.84 | 796.59 |


### Endpoint and worker comparisons

Read endpoint p95 list/detail/result/evaluation: at one client,
31.25/20.49/20.52/35.73ms; at 100, 3202.93/3427.88/3427.35/3315.06ms.
Per-endpoint sample size is 50/trial (p99 NA); aggregate read is 200/trial.

At 25 clients, throughput relative to worker=2 for workers 1/2/4/8:
instant **1.29/1.00/1.07/1.02**; moderate **0.57/1.00/1.70/2.79**.
Moderate queue p95: one worker adds 91.3% wait, four reduces it 49.8%, eight 77.3%.
More workers help artificial waiting; they do not consistently improve the instant
local ceiling. Sequential commands/timing variability limit a causal CPU explanation.

### SSE, mixed and failure checks

Dedicated SSE: 258/258 subscribers succeeded; mixed another 240/240. All
**498/498** passed terminal/missing/duplicate/order/resume checks. **12,249**
connections closed as finite batches; closure alone never meant job completion.
At 1/10/25/50 subscribers, delivery samples are 8/80/200/400 per trial: eight
correlated events from one job. Thus SSE p95 NA at one; p99 NA at one/ten.
Commit-to-frame timing includes TCP, client and reconnect scheduling and is not
an independent-user latency distribution.

Mixed requests/trial: 102-104 / 990-1046 / 2714-2876 at 5/25/50 clients.
At 50, transport-await p95 489.08ms exceeds injected 250ms, tool p95 7.78ms,
service p95 2842.57ms: additional scheduling/request/serialization overhead is
present. This is not Groq performance. Native evaluation remained available;
evaluation reads caused no terminal mutation.

Cancellation per trial: three succeeded, two queued cancelled with zero execution,
one held in-flight cancelled after its single call with zero tools. Seven exact
measured calls. One stale revision produced expected 409, then current-revision
cancellation succeeded. Queue/service/end-to-end p50 medians:
69.23/552.63/723.74ms; p95/p99 NA. This is correctness under load, not a latency SLA.
Degraded per trial: one selected failed job, 19 succeeded, one injected SDK HTTP
503, one attempt for failed job; following work drained and pool stayed healthy.
Three terminal failures are expected; no API HTTP 5xx or retry storm.

### Optional artifact series

Three offline trials, one client, two jobs/trial, one warmup, worker=2, 0ms delay.
Six succeeded, 18 exact decisions, sufficient canonical evidence/native evaluation.
Manifest SHA256: `05ac6608f3114476341f58ddd35faab5fe7312c8bfdea87e1c07d144185d7e4b`.
Median **1.97 jobs/sec**, queue/service/E2E p50 **383.95/64.91/453.95ms**,
drain **1014.99ms**; run p95/p99 NA (two samples/trial).
Tool p50 0.22ms, median trial tool max 15.44ms; four samples/trial, p95/p99 NA.
CPU median 0.203125 process seconds, sampled peak RSS median 1872.32MiB,
loop p95 12.06ms. Cached model initialization/index hydration are excluded startup.
The actual chosen path exercises discovery/BM25 and chunk reading. Initialized
dense/reranker components do not establish their measured performance. This tiny
private-artifact series is separate from the different hermetic fixture and is
not a capacity sweep. No corpus/index regeneration, movement or deletion.

## Correctness, SQLite and resources

Accepted trials: **25,452 successful HTTP responses** (6246 create, 19,206 other),
**three expected stale-revision 409s**, zero unexpected HTTP failures/5xx.
Measured durable states: 3600 intentionally queued admission rows, 2634 succeeded,
nine cancelled, three selected failed. Warmup rows/timings are additional/excluded.
Exactly **6462** measured mocked decision calls; no external/paid call or retry.

Every recorded correctness counter is zero: lost jobs/IDs, duplicate execution /
provider / claim / terminal, capacity, illegal lifecycle, research coverage,
cancellation bounds, terminal mutation, event/SSE order/missing/duplicate/resume,
unhealthy pool, SQLite busy/locked/error/claim failure and DB issues. Every trial
stopped/gathered workers, reopened the **same** DB, schema v7, integrity_check=ok,
exact warmup+measured rows and no running/cancelling rows. Admission deliberately
stays queued. Reopen/audit is excluded from timing. Functional checks are separate
from capacity metrics. No product benchmark route exists.

Claim duration includes lock/DB work; empty polls are excluded. Transaction spans
successful BEGIN IMMEDIATE return to commit, excluding prior Python lock wait.
Lock observation covers existing initialization/write acquisitions, not one SQL
operation or exclusively claims. Mixed50 transaction p95 **6.63ms**, lock wait
p95 **540.39ms**; read100 lock p95 **92.47ms**. Mixed claim p95 is non-monotonic
(350.20ms at 25, 42.59ms at 50), so no simple monotonic claim-cost claim follows.
Zero busy errors does not mean zero contention. Serialized Python-side access
contributes to latency; SQLite engine write throughput is not established as the
sole ceiling and these data do not justify migration.

Resource metrics include client/server and imports, not an isolated production
worker. Hermetic trial RSS peaks ranged **748.38-805.66MiB**; absolute maximum
observed loop lag **760.12ms** (table gives median trial maxima). CPU is average
core equivalents, not whole-machine utilization. The 20ms probe can miss stalls.
Worker tasks stayed fixed/bounded; no deadline/drain/pool/resource instability
was observed. Three short trials do not establish long-soak memory behavior or
cross-process contention.

## Saturation and ranked bottleneck evidence

1. **Synthetic waiting/default worker capacity: strong evidence.** At worker=2,
   moderate worker throughput plateaus 3.06-3.25 jobs/sec from 5-50 clients,
   queue p95 1.28 to 13.29s. Research plateaus 2.19-2.26 jobs/sec, queue p95
   1.75 to 19.72s, service p95 about 0.90s, peak active 2. Extra workers reduce
   waiting. Counter-evidence: instant scaling differs; no real-provider latency
   or production eight-worker suitability is established.
2. **Local API/serialized access overhead: substantial evidence, attribution
   incomplete.** Admission/read plateau about 54-66 / 57-62 requests/sec from
   the lowest level; at 100, p95 3.22/3.35s. Mixed falls 1.63 to 1.06 jobs/sec,
   queue p95 reaches 43.64s, lock waits/stalls rise. Instant worker service p95
   rises 36.52 to 598.94ms at workers 1 to 8 without throughput gain. Read cost
   exists without measured provider calls. Counter-evidence: short transactions,
   zero DB errors, non-monotonic claims and shared client/server prevent naming
   one function/SQLite as sole cause. Access, settings/service/repository
   initialization, validation/serialization, read/evaluation and client CPU
   stages are not separately instrumented.
3. **Low-load poll scheduling: consistent evidence, not isolated causality.**
   One-client instant research queue p50/p95 444.56/477.06ms versus service
   p50 45.77ms is consistent with 500ms idle polling. One-client worker has a
   different submission phase/lower queue median. No poll-interval comparison
   was run; no default change follows.
4. **Retrieval/reranking dominance: not established.** Synthetic hermetic tools
   and tiny discovery/BM25/reader artifact series cannot establish it.

Saturation means throughput stops increasing while waiting rises: worker/research
near 5-10 outstanding runs at worker=2; admission/read already near ceiling at the
lowest measured point (knee below one client unresolved); mixed contention
pronounced at 25-50. Highest successful tested: admission/read 100, full/mixed/SSE 50,
workers 8. These are benchmark regions, **not production maximum users**.

### Recommended next task (proposal only)

**OBS-001 - Attribute Agent API, stream and serialized-access overhead under
fixed hermetic load.** Separate client/server CPU and profile access,
configuration/service/repository initialization, validation/serialization,
evaluation reads, lock acquisition/hold and SQL boundaries. Retain exact instant,
worker=2 and mixed 25/50 fixtures/correctness gates. Identify repeated work and lock
wait causes before choosing optimization. The plateau/mixed degradation support
this task; current data do not select a cache policy, database migration or worker
default change. Recommendation only; SCALE-003 remains not started.

## Defects and corrections

No new reproducible **P0-P2 product correctness defect** was found in this bounded
campaign. Slow numbers/lawful queue waiting are not correctness defects.

| Severity | Reproduction | Fix | Rerun |
| --- | --- | --- | --- |
| P3 harness | Initial rollback test used wrong failure hook | Existing after_create instead of after_job_insert | Empty rolled-back observations; final suite |
| P3 harness | Intentionally stopped warm pool falsely counted unhealthy in cancel | Remove stopped warm pool from app state | Smoke + three primary cancel trials |
| P3 harness | Sync artifact startup could outlive async deadline | External child deadline, incomplete timeout report | Deterministic test + three artifact trials |
| P3 docs | Telemetry/artifact wording implied unmeasured stages | Explicit route catalog and exercised stage coverage | Source audit, docs-only change |

Benchmark HTTP-only Uvicorn ws=none avoids irrelevant WebSocket warnings; product
config unchanged. Selected degraded identity is fixed by goal before admission,
so scheduling cannot change failed job. User interruption is incomplete evidence.

## Validation and release

| Gate actually run | Result |
| --- | --- |
| Final new statistic/protocol/harness tests | 49 passed / one inherited warning; eight offline HTTP profile smokes |
| Final harness + SCALE-001 + provider regressions | 196 passed / one inherited warning (49 + 51 + 96) |
| Development CLI smokes | Admission and worker small runs; optional artifact research; excluded from primary timing tables |
| Primary admission/read | 18 trials / 3600 requests each, every level complete |
| Primary worker/research | 54 / 36 hermetic trials, exact ladders/sweep above |
| Primary SSE/mixed | 12 / 9 trials, 498 total subscriber checks including mixed |
| Cancellation/degraded | Three trials each; controlled expected cancellations/failures only |
| Optional artifact | Three separate research trials |
| Integrity/reopen | All 156 accepted trials, same DB/schema 7/integrity/no active rows |
| Full primary backend | 1779 passed / zero failed / 188 warnings |
| Committed source-clean full backend | 1745 passed / 34 expected artifact skips / 148 warnings |
| Own-source import, primary/source-clean | PASS; no import-time pool |
| Product route inventory, primary/source-clean | 90 unique method/path pairs |
| Fresh/reopened schema, primary/source-clean | v7/v7, integrity ok |
| Finite/sanitized report and binding audit | 52 distinct scenarios, 156 complete trials, common runtime/digest, no partial mixing |
| git diff --check | PASS |
| Frontend | Production source unchanged; inherited 94 files / 818 tests, TS/build PASS, not rerun in SCALE-002 |

Baseline primary 1730/188 warnings becomes **1779/188**; clean 1696/34 skips/148
becomes **1745/34/148**: the exact 49 added cases, zero failures and no warning
growth. Routes 90/schema 7 remain. Clean source checkout contains no .env/data,
prior benchmark output, credentials or main-tree untracked source. Existing
external Python runs that checkout's own modules; no package installation.
The final committed documentation HEAD additionally receives its own clean full
backend, new 49 tests, independent one-client admission/worker CLI smokes,
route/schema/import and DB/pool/offline gates. Exact outcomes/SHA are recorded
in final chat after this commit. Documentation-only closure does not invalidate
runtime 2370274 measurements. No expensive matrix repetition is needed.


## Files, commits and audits

Created: scripts/benchmarks/__init__.py, scale_002.py, scale_002_runtime.py,
scale_002_stats.py; tests/test_scale_002_benchmark.py;
docs/SCALE_002_BENCHMARK_PROTOCOL.md; docs/SCALE_002_FINAL_RECEIPT.md.
Modified: README.md, PROJECT_STATE.md, docs/SCALING_ROADMAP.md. Deleted: none.
No dependency/lockfile, migration, route, production config/source/frontend change.

Commits: `23702743ee6e3e807dad4004c68ff77cb6006bef` (tested harness/protocol/checkpoint),
then `docs(scale): record load and capacity characterization` (documentation-only
closure). Final chat gives full release hash, clean gate and normal push proof.
Raw JSON, interrupted evidence, test logs and scratch scripts remain ignored in
.local/benchmarks/scale-002; no DB/WAL/SHM, traces, transcripts, screenshot,
model cache, build output, dependency or private artifact is staged.
Finite JSON/sensitive-field/private-path validation and final changed-file credential
scan passed without printing values. .env is never staged. No corpus regeneration.
Same 12 unrelated untracked paths preserved: .audit-runtime/, .mimosa/,
.zcodeignore, PROJECT_CONTEXT.md, frontend/.audit-runtime/, frontend/.mimosa/,
frontend/e2e/capture-ui-round.mjs, frontend/e2e/probe-box.mjs,
frontend/e2e/probe-contrast.mjs, frontend/e2e/v5-1-visual-capture.spec.ts,
harness_stacks.txt, screenshots/. No reset/clean/stash/destructive restore/mass
staging. Managed verification worktrees archived after gates.

Known limitations: Collections/model-test browser bearer staged, native zoom
manual/unverified, inherited ~508.63kB build warning, Ragas optional, previous
live-provider timeout not retried. Benchmark limitations: shared process/event
loop, short closed-loop burst, synthetic provider latency, logging suppression,
measurement overhead, small artifact sample, excluded cold start, no multi-process
DB/Qdrant or soak characterization. Local Qdrant still requires one API process.
Uncertain in-flight effects/no replay/exactly-once guarantees remain unchanged.
New product regressions: none observed.

PROJECT_STATE/SCALING_ROADMAP record the envelope, findings and proposal.
SCALE-001/002 complete after release gates; SCALE-003 not started.
Normal push to origin/codex/bilingual-research-workspace; final chat records exact
validated HEAD, matching upstream/remote and ahead/behind 0/0.
**Exact next action: STOP.** Proposed OBS-001 requires a separate request.
