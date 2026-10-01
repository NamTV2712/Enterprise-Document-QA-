# WORKER-002 final receipt

Date: 2026-10-01. Optional scheduling/admission attribution on **main**.
Starting runtime: `d7bd0d4f66a03bc00be05876059a1b1ed1f04877`.
Accepted measured runtime: **`8f5d9a819ca52e6f04ebfa1343437ef11a1c06e3`**.
Required roadmap, AGENT-001–006/UI-014/TEST-005, PROVIDER/CRED and
SCALE-001/002/OBS/DB-SCALE remain COMPLETE. SCALE-003 is NOT STARTED.

## Architecture and ownership

Before: one local execution-enabled lifespan supervisor, two fixed asyncio
consumers, each shielding a bounded SQLite claim then executing one job.
Empty/error claims wait on the stop Event for at most poll 500 ms. Admissions
commit through the async private router's threadpool service with no wake
relationship. Successful owners immediately loop, without polling between
queued jobs. SQLite v7 is the only queue authority; eligible ordering remains
`created_at ASC, job_id ASC`, under writer RLock/BEGIN IMMEDIATE and revision CAS.
Provider/tool work occurs outside the claim transaction.

After: the supervisor additionally owns **one payload-free Event flag**.
Authorized queued HTTP admission calls an injected composition callback after
durable create returns to the HTTP event loop. The callback looks up the
existing lifespan owner; it never creates a worker or references a job payload.
The owner accepts hints only on its running loop while healthy; missing/stopped/
foreign-thread/foreign-loop hints are ignored. A notification exception is
sanitized and cannot undo admission. Fixed consumers wake and use unchanged
authoritative claims. Existing waiters can all wake, bounded by N; no admission
task, pending list, queue mirror or timer is added. Busy owners drain SQLite
normally; hints coalesce until consumed. Lost hints and non-HTTP admissions
remain discoverable by periodic polling. Stop/failure wakes sleepers while the
existing stop authority, shielded claim reconciliation, grace, cancellation,
restart interruption and no ambiguous-effect replay remain intact.

Defaults remain **workers 2 / poll 500 ms / grace 5000 ms**. DB-SCALE guarded
initialization, independent owned connections, short WAL snapshots and writer
serialization are untouched. Schema **v7/WAL/NORMAL/busy5000ms**, routes **90**.
Agent remains one attempt/max_retries0/deadline60s/primary under historical
`key5_only`; Generator's bounded primary/fallback429 behavior and CRED's two
active credentials are unchanged. No frontend, dependency, lockfile, migration,
index, cache, provider policy or Agent budget change.

## Protocol, provenance and measured scope

[Protocol](WORKER_002_PROTOCOL.md): `worker-002-v1`, scheduler facts
`worker-002-scheduler-facts-v1`, inherited `scale-002-benchmark-v1`,
`obs-001-attribution-v1`, `db-scale-001-v1`. Before/after each have **26 points /
78 trials**, three per point, four warmup jobs + four warmup reads excluded.
Real TCP/HTTP/SSE, real production worker/service/repository and actual SDK
construction with synthetic transport only; no live Groq. Workloads/bindings,
SCALE/OBS hashes and environment match; no checkpoint mixing. Before runtime
was tracked-clean and untouched; ignored driver bytes were promoted identically
for the committed tracked-clean after runtime. Combined driver SHA256:
`78f7e55b8671d0b5f8557e44b46ec3534f27e88374af3a58e34815085a9e32e2`.

Windows 10.0.26300, Python 3.12.7, SQLite 3.45.3, 24 logical CPUs,
16,890,322,944 bytes RAM. FastAPI 0.115.0, Starlette 0.38.6, HTTPX 0.28.1,
Uvicorn 0.32.0, Groq 1.5.0, Pydantic 2.13.4. CPU and sampled working-set RSS
combine the same-process server/client; they do not isolate API engine costs.
Sequential idle-confirmed singles intentionally bias toward a full remaining
poll; staggered schedules may drift when admission is slower than their interval.
No real quota, production SLA, arbitrary-host fairness or deployment claim.

Queue wait remains durable create commit → running commit. Occupancy intersections
are independent job-time overlaps, **not an additive causal partition**. Executor
entry defines serving; claims, telemetry and loop scheduling also consume time.
Global next-attempt delay is an opportunity fact; an already ongoing claim may
find a row earlier. First/second commits are relative to the first create, not
per-consumer notice timestamps. No future owner is assigned to a queued row.
Median-of-three trial percentiles are reported; p50 needs 2 / p95 needs 20 / p99 needs 100.
Missing percentiles remain unavailable. Every point has fewer than 100 measured
job lifecycles; no job queue/service/E2E p99 claim is made.

## Findings and retained tradeoffs

- Default idle single queue p50/p95 **475.494/502.753 → 5.513/9.340ms**;
  the before queue overlaps any idle consumer by **99.564%**, with **zero full
  serving-capacity overlap**. Global next-attempt p95 **492.769→2.924ms**.
  Low-load poll contribution is reproduced across 100/250/500/1000ms. This is
  repeatable local wake improvement, not a guarantee of an exact row notice time.
- Staggered 100/250/750ms queue p95 **402.286/456.894/481.481 →
  7.362/9.598/6.797ms**. At 50ms, queue p95 **667.530→346.374ms** and full
  serving overlap **48.046→59.574%**: the supposedly instant SDK still has
  real local service/DB/telemetry work, so arrivals can saturate two consumers.
- One-consumer burst first claims 1/5/10/25/50 move from roughly 485/495/493/447/474ms
  to **7/21/36/24/17ms**. Burst 25 queue p95 **1558.556→1035.128ms**. Burst 50
  is a retained counterexample: queue p95 **2422.872→2536.370ms**, throughput
  **17.714→16.925jobs/s**, and create client/server p95
  **275.359/140.909→347.385/200.986ms**. Earlier service overlaps admission
  writes; initial claim max **10.333→25.887ms**, later max **6.420→5.640ms**,
  writer-wait p95 **94.460→73.906ms**. The hint removes idle waiting; it cannot
  remove finite admission/serving costs or promise universal tail improvement.
- Research queue p95 **3693.558→3667.924ms**, throughput **2.211→2.243jobs/s**;
  service p95 **880.696→915.828ms**. Mixed queue p95
  **11162.564→10199.134ms**, throughput **1.871→2.057jobs/s**, service p95
  **1073.412→1099.260ms**. After, queue overlaps full serving capacity
  **93.976/92.093%**, any idle consumer **0.008/0.004%**, and any provider
  **90.144/88.473%**. Active utilization **0.957/0.928**; provider peak 2.
  This supports bounded service capacity as the strongest remaining queue
  bottleneck, with provider occupancy significant. Provider overlap does not
  prove all capacity waits on providers, or isolate engine/network time.
- Mixed first/second commits **669.739/689.074→11.772/19.494ms**; claim lock
  p95 **182.367→21.611ms**, inclusive claim p95 **234.363→61.074ms**; later
  max **80.379→73.003ms**. Research create p95 and claim lock p95 increase
  **60.302→83.062ms** client and **3.673→14.194ms** lock. All jobs progress;
  no sustained starvation, busy error or duplicate owner is reproduced. Unequal
  finite progress and initial write overlap remain, not a perfect fairness claim.
- At 250 ms provider delay, after workers 1/2/4/8 yield **1.763/3.282/5.566/8.471jobs/s**,
  while simultaneous provider calls are **1/2/4/8**. At 0 ms they yield
  **16.336/15.190/15.414/13.120jobs/s**: more workers do not consistently help.
  With 8, instant API p95 **426.840ms**, loop lag p95 **97.120ms** and service
  p95 **550.263ms**. Default 2 instant service p95 **105.101→208.454ms** is a
  retained service-tail regression during overlapping admission/execution,
  while queue/E2E p95 improve **1632.397/1814.683→1320.357/1400.310ms** and
  total write-wait p95 falls **47.753→40.763ms**. Inclusive service costs are
  not pure engine measurements. Never choose a larger default from wait-only
  throughput; real provider operational bounds remain unestablished.
- Idle 4s empty checks/sec **3.496→3.507**, 14 empty claims each measured trial,
  accepted hints 0, provider calls 0. CPU seconds **0.094→0.016**, RSS
  **838.359→822.891MiB**, loop lag **12.006→11.965ms**. No idle CPU/task/DB
  regression is observed; CPU deltas include host sampling noise. Sparse single
  throughput rises, so empty checks/sec during admission rises: default
  **3.631→24.320**, with 39 empty checks for 20 jobs after and two fixed tasks.
  That is bounded companion checks per admission in a shorter window, not spin.
- Coalescing is explicit: burst 50 accepts 50 hints, coalesces 48 (**96%**) in each
  trial; default research 20/18 (**90%**), mixed 25/23 (**92%**). One hint can
  wake both existing idle consumers (20 sequential admissions produce 40 wakes).
  Restart admits 20 jobs with zero measured hint attempts and all complete.
  Separate barrier tests prove poll discovery after the initial empty startup
  claim even when every hint disappears.

## Candidate decisions and excluded diagnostics

Retain immediate payload-free admission Event: baseline supports idle waiting,
low-load benefit repeats, fixed tasks/durability and all correctness gates pass;
idle and default DB wait do not meaningfully regress. Keep poll 500 ms as fallback.
Reject shorter 100/250ms polling as a new default: controls reduce poll-only wait
but do not match the hint's low-load result and increase empty-check frequency.
Reject 4/8 workers as new defaults: wait throughput improves while provider
concurrency and local/API/loop costs grow. No dynamic tuning is added.

An **excluded diagnostic** tested one 20 ms pending timer per supervisor, three
trials each at single 500/burst 50/mixed 25 (same measured runtime, fixed tasks,
no production edit). All correctness/missing/drop counters pass. Compared with
immediate hint, queue p95 is **9.340→43.458ms** single,
**2536.370→2395.828ms** burst 50, **10199.134→10884.988ms** mixed. Claim max
**11.723/25.887/73.003→10.907/42.863/141.318ms** respectively. Mixed
throughput **2.057→1.983jobs/s**. This timing control does not establish a
beneficial default delay; reject debounce and leave no timer code in production.
Event-based coalescing counters do not observe the diagnostic pending timer and
are excluded from this comparison. Diagnostic results are not checkpoint-merged.

The initial smoke restart fixture briefly published an intentionally stopped
pool as current owner, yielding `unhealthy_pool`; removing the owner
during the composition gap repaired the harness, not production assertions.
That incomplete smoke is excluded; corrected before/after eight-kind smokes pass.
Two initial new-test assertions used an incorrect page attribute / miscounted
step events as claim events; corrected field/type checks pass. No P0/P1/P2
product defect remains; these P3 harness/test issues are recorded, not hidden.

## Correctness and release

All 156 canonical trials have zero in every inherited correctness counter:
lost_jobs, duplicate_durable_id, duplicate_execution, duplicate_provider_execution,
decision_count_mismatch, capacity_violation, invalid_lifecycle, event_ordering,
duplicate_claim, duplicate_terminal, queued_cancel_executed, research_coverage,
terminal_status_mismatch, database_issues, sqlite_busy, sqlite_error, claim_failure,
inflight_cancel_executed_extra_work, unexpected_failure_or_retry,
mutation_after_terminal, unhealthy_pool, missing_events, duplicate_events,
ordering_violations, resume_failures, connection_failures. OBS missing_api,
missing_workers and dropped are zero. Each temporary database explicitly reopens
at v7 with integrity ok and no active owner after stop. Peak owners/tasks/provider
calls stay within configured capacity. Notification failures cannot change 201;
public/execution/access refusal reaches neither private service nor notifier.

Twenty new tests cover coalescing/task bounds, empty-queue return to idle,
lost-hint poll, fresh restart, wrong thread/loop, cancellation/eligibility,
saturated progress, one-owner release with oldest eligible ordering, actual
lifespan HTTP hint + SDK/SSE/resume/terminal idempotency, workers disabled,
notification after commit and safe failure, refusal boundaries and numeric
observer interval/budget semantics. Existing DB/CAS/claim/snapshot/connection,
DATA-004/005, OBS, Agent, cancellation/recovery, provider/CRED/Generator tests
are rerun without live network or weakened assertions.

| Gate actually run | Result |
| --- | --- |
| Baseline focused workers/Agent/OBS/DB/provider/CRED | 267 passed / 1 inherited warning, 25.69s |
| Initial numeric observer tests | 4 passed, 0.36s |
| Corrected before and after eight-kind smokes | 8 complete points each / zero correctness/missing/drop |
| Candidate focused | 287 passed / 1 inherited warning, 24.43s |
| Broad DATA-004/005/transfer/Agent/workers/DB/OBS/provider/CRED/Generator + new tests | **656 passed / 1 inherited warning**, 36.38s |
| Primary full backend at measured runtime | **1919 passed / 188 warnings / 0 failures**, 123.17s |
| Measured-runtime data-free full backend | **1885 passed / 34 expected skips / 148 warnings / 0 failures**, 88.97s |
| Compile/import, public startup (corpus/model stubs, real composition) | PASS; no private DB or worker |
| Product API method/path inventory | 90; no added route |
| SQLite explicit reopen / runtime configuration / integrity | v7 / WAL / NORMAL / busy5000ms / ok |
| Exact-final committed clean full suite, focused gate, compile/probes and normal push | Mandatory closure; literal SHA/results in closing report |

Primary and clean full suites run serially. Baseline primary 1899 / 188 warnings,
clean 1865 / 34 skips / 148 warnings; final increment is exactly 20 tests with no warning
growth. Frontend is untouched; 94 files / 818 tests and TypeScript/build PASS are inherited.

Exact final documentation SHA clean validation and normal main push are mandatory
release conditions; the closing report records the literal final SHA, commands,
clean results and local/upstream/remote equality. Failure blocks release.

## Files, safety and known limitations

Created protocol/receipt, two benchmark modules and two test modules. Modified
three runtime modules plus README, ARCHITECTURE, PROJECT_STATE and scaling roadmap.
Deleted none. Runtime commit `8f5d9a8`:
`perf(worker): reduce durable queue wake latency`; measurement/docs commit is
identified in the closing report. Main-only, no new branch/PR/history rewrite.
Reviewed scalar tables below are the only exported measurement content. Raw
reports/logs/SQLite/diagnostics remain ignored `.local/worker-002/`. No secrets,
real bearer/key, transcript, raw provider content, generated corpus, build output
or screenshots enter Git. Intentional synthetic secret sentinels stay in tests.
The same 12 unrelated untracked paths stay untouched; tracked/staged tree is clean
after commits. Local data and `.env` are untouched. No source depends on ignored
harnesses; committed imports and data-free execution are verified.

Known limitations remain Collections/model-test browser bearer wiring staged,
native zoom manual/unverified, inherited frontend bundle warning, inherited
backend warnings, optional Ragas, single-process/local topology and no production
SLA/quota certification. Frontend 94 files / 818 tests, TypeScript/build PASS are
inherited, not rerun. The finite burst/admission and service-tail costs above are
explicit retained limitations. Three trials do not establish statistical
significance or guarantee fairness for every external deployment.

## Exactly one recommended next task

**CAPACITY-001 — bounded Agent service capacity and provider concurrency policy.**
Scope a hermetic decomposition of provider occupancy, local tools/DB/telemetry
service time and finite admission/service overlap; define operational concurrency
limits and cancellation/deadline/resource acceptance before considering a default
change. Use the demonstrated research/mixed full-capacity overlap and 1/2/4/8
tradeoffs; establish real-provider limits through a separately approved operational
protocol, not this campaign. Counter-evidence is strong local/API degradation at
8 and unresolved inclusive costs; caching/engine dominance is not proven.
This task is recommended only, NOT STARTED. Implement no next task, no SCALE-003,
distributed workers, Redis/Postgres, priorities or new provider retries. STOP.

## Comparable WORKER-002 measurements

All cells are before → after. Milliseconds except throughput, CPU seconds, fractions and MiB. Median of three trial statistics; unavailable —. No pooled percentiles.

## Durable lifecycle and throughput

| Point | Queue p50 | Queue p95 | Service p50 | Service p95 | E2E p50 | E2E p95 | Jobs/s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-poll-100 | 68.974 → 4.790 | 99.665 → 5.742 | 41.387 → 36.922 | 55.458 → 43.962 | 114.472 → 41.756 | 144.404 → 48.065 | 7.537 → 17.194 |
| single-poll-250 | 225.889 → 5.227 | 256.353 → 7.383 | 39.161 → 38.266 | 46.098 → 51.635 | 268.257 → 43.493 | 295.843 → 58.956 | 3.507 → 15.800 |
| single-poll-500 | 475.494 → 5.513 | 502.753 → 9.340 | 39.141 → 39.943 | 49.974 → 72.440 | 516.403 → 45.922 | 543.970 → 84.486 | 1.879 → 12.553 |
| single-poll-1000 | 972.849 → 5.034 | 1000.774 → 7.349 | 38.304 → 38.116 | 49.204 → 45.779 | 1013.352 → 43.075 | 1038.656 → 56.417 | 0.970 → 14.280 |
| stagger-50 | 588.266 → 167.970 | 667.530 → 346.374 | 81.439 → 85.616 | 108.545 → 151.901 | 673.347 → 260.876 | 752.811 → 424.203 | 11.887 → 14.373 |
| stagger-100 | 178.150 → 5.513 | 402.286 → 7.362 | 79.431 → 36.897 | 108.120 → 42.570 | 271.893 → 42.563 | 523.478 → 48.842 | 9.718 → 10.262 |
| stagger-250 | 202.323 → 5.993 | 456.894 → 9.598 | 76.029 → 38.029 | 132.789 → 44.106 | 278.920 → 43.927 | 542.252 → 74.241 | 3.940 → 4.166 |
| stagger-750 | 203.892 → 5.821 | 481.481 → 6.797 | 38.936 → 38.550 | 48.272 → 51.296 | 242.130 → 44.238 | 517.173 → 57.032 | 1.355 → 1.399 |
| burst-1 | — → — | — → — | — → — | — → — | — → — | — → — | 1.920 → 19.301 |
| burst-2 | 505.210 → 8.883 | — → — | 34.792 → 33.690 | — → — | 541.871 → 49.852 | — → — | 3.378 → 21.002 |
| burst-5 | 603.834 → 156.321 | — → — | 41.720 → 37.789 | — → — | 658.223 → 192.983 | — → — | 6.292 → 16.554 |
| burst-10 | 652.773 → 212.217 | — → — | 35.011 → 35.795 | — → — | 686.268 → 246.230 | — → — | 10.467 → 18.148 |
| burst-25 | 989.950 → 609.170 | 1558.556 → 1035.128 | 35.107 → 33.955 | 43.691 → 37.450 | 1023.908 → 641.110 | 1600.819 → 1068.884 | 13.975 → 19.733 |
| burst-50 | 1423.015 → 1437.513 | 2422.872 → 2536.370 | 34.721 → 34.130 | 39.612 → 38.452 | 1456.344 → 1472.862 | 2461.029 → 2568.894 | 17.714 → 16.925 |
| research-10-250 | 3355.503 → 3481.627 | 3693.558 → 3667.924 | 826.948 → 846.011 | 880.696 → 915.828 | 4155.016 → 4351.589 | 4563.877 → 4545.979 | 2.211 → 2.243 |
| mixed-25-250 | 6583.942 → 5766.865 | 11162.564 → 10199.134 | 912.438 → 882.719 | 1073.412 → 1099.260 | 7425.045 → 6565.424 | 12081.321 → 11196.186 | 1.871 → 2.057 |
| workers-1-delay-250 | 7185.075 → 6766.949 | 13383.260 → 12899.388 | 549.709 → 547.462 | 591.986 → 601.896 | 7716.185 → 7298.917 | 13932.319 → 13445.765 | 1.708 → 1.763 |
| workers-2-delay-250 | 3902.304 → 3551.222 | 6732.345 → 6419.328 | 561.055 → 563.690 | 601.057 → 633.842 | 4417.221 → 4187.869 | 7263.583 → 6976.591 | 3.186 → 3.282 |
| workers-4-delay-250 | 2034.274 → 1805.379 | 3741.296 → 3269.647 | 610.680 → 594.666 | 719.240 → 699.400 | 2727.866 → 2380.521 | 4393.736 → 3876.554 | 5.216 → 5.566 |
| workers-8-delay-250 | 1023.161 → 911.943 | 1873.622 → 1713.333 | 650.354 → 735.023 | 737.012 → 850.031 | 1683.643 → 1626.530 | 2610.634 → 2478.370 | 7.874 → 8.471 |
| workers-1-delay-0 | 976.671 → 668.640 | 1468.630 → 1268.938 | 33.658 → 35.727 | 39.098 → 139.993 | 1009.657 → 708.142 | 1505.746 → 1304.665 | 14.999 → 16.336 |
| workers-2-delay-0 | 1075.213 → 776.261 | 1632.397 → 1320.357 | 79.391 → 84.875 | 105.101 → 208.454 | 1159.089 → 864.239 | 1814.683 → 1400.310 | 12.545 → 15.190 |
| workers-4-delay-0 | 891.777 → 718.265 | 1468.141 → 1200.219 | 160.555 → 172.276 | 220.916 → 299.668 | 1075.338 → 880.200 | 1610.357 → 1347.366 | 13.706 → 15.414 |
| workers-8-delay-0 | 734.018 → 615.129 | 1146.723 → 1110.912 | 301.030 → 378.622 | 391.746 → 550.263 | 920.074 → 947.217 | 1482.999 → 1400.985 | 15.391 → 13.120 |
| idle | — → — | — → — | — → — | — → — | — → — | — → — | — → — |
| restart | 536.230 → 629.040 | 1156.120 → 1149.608 | 85.763 → 85.906 | 104.111 → 108.487 | 630.294 → 713.453 | 1242.831 → 1212.025 | 14.328 → 14.234 |

## Admission / claim fairness

| Point | Create client p50 | Create client p95 | Create server p50 | Create server p95 | Claim lock p50 | Claim lock p95 | First claim commit | Second claim commit | Claim max | Later claim max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-poll-100 | 6.611 → 6.947 | 8.480 → 8.993 | 5.372 → 5.717 | 7.267 → 7.567 | 0.008 → 0.002 | 0.014 → 0.003 | 68.927 → 4.790 | 195.626 → 62.193 | 13.972 → 5.767 | 13.972 → 5.767 |
| single-poll-250 | 6.925 → 7.579 | 8.837 → 11.278 | 5.667 → 6.172 | 7.566 → 9.518 | 0.007 → 0.002 | 0.013 → 0.004 | 250.219 → 5.847 | 534.172 → 71.767 | 13.146 → 8.268 | 13.146 → 8.268 |
| single-poll-500 | 6.590 → 7.630 | 8.561 → 13.271 | 5.421 → 6.257 | 7.357 → 10.828 | 0.008 → 0.002 | 0.014 → 0.004 | 482.175 → 6.043 | 1026.274 → 66.604 | 12.600 → 11.723 | 12.600 → 11.723 |
| single-poll-1000 | 6.688 → 7.210 | 8.172 → 11.267 | 5.502 → 5.937 | 6.316 → 9.703 | 0.006 → 0.002 | 0.014 → 0.003 | 975.821 → 4.959 | 2002.391 → 65.272 | 13.176 → 8.795 | 13.176 → 8.795 |
| stagger-50 | 13.377 → 36.132 | 59.993 → 68.018 | 10.833 → 31.061 | 52.441 → 58.866 | 3.077 → 3.298 | 8.076 → 13.945 | 480.121 → 5.835 | 499.938 → 59.552 | 25.245 → 44.088 | 24.605 → 44.088 |
| stagger-100 | 20.786 → 10.809 | 86.145 → 15.645 | 19.549 → 8.538 | 72.953 → 12.869 | 2.882 → 0.002 | 7.512 → 0.004 | 475.934 → 4.804 | 482.753 → 89.153 | 29.205 → 6.752 | 29.205 → 6.752 |
| stagger-250 | 13.251 → 12.318 | 47.871 → 16.308 | 10.318 → 9.563 | 43.587 → 13.341 | 0.008 → 0.003 | 7.794 → 0.004 | 460.870 → 5.899 | 468.611 → 279.345 | 26.016 → 8.446 | 25.910 → 6.667 |
| stagger-750 | 11.848 → 12.133 | 16.644 → 16.510 | 9.551 → 9.803 | 12.626 → 13.686 | 0.007 → 0.003 | 0.016 → 0.004 | 474.395 → 4.992 | 1011.534 → 757.188 | 14.295 → 6.489 | 14.295 → 6.489 |
| burst-1 | — → — | — → — | — → — | — → — | — → — | — → — | 485.296 → 7.296 | — → — | 10.364 → 6.380 | — → — |
| burst-2 | 9.348 → 9.268 | — → — | 7.470 → 7.729 | — → — | 0.002 → 0.003 | — → — | 505.210 → 8.883 | 553.873 → 61.538 | 11.572 → 8.381 | — → — |
| burst-5 | 21.391 → 23.101 | — → — | 15.918 → 16.143 | — → — | 0.003 → 0.003 | — → — | 494.938 → 21.436 | 550.046 → 80.932 | 12.832 → 20.744 | 5.192 → 5.780 |
| burst-10 | 39.738 → 41.506 | — → — | 30.877 → 31.624 | — → — | 0.002 → 0.002 | — → — | 493.021 → 35.953 | 540.293 → 98.435 | 9.952 → 32.487 | 5.609 → 6.212 |
| burst-25 | 92.662 → 154.389 | 139.782 → 180.195 | 67.997 → 99.191 | 89.390 → 121.477 | 0.002 → 0.002 | 0.004 → 0.003 | 446.796 → 24.104 | 499.285 → 184.743 | 22.559 → 26.343 | 22.559 → 5.725 |
| burst-50 | 177.199 → 215.242 | 275.359 → 347.385 | 118.036 → 127.542 | 140.909 → 200.986 | 0.002 → 0.002 | 0.004 → 0.003 | 474.059 → 16.966 | 523.486 → 341.625 | 10.333 → 25.887 | 6.420 → 5.640 |
| research-10-250 | 23.149 → 27.495 | 60.302 → 83.062 | 20.431 → 23.929 | 46.823 → 70.598 | 0.002 → 2.258 | 3.673 → 14.194 | 428.434 → 14.802 | 473.390 → 18.337 | 22.692 → 53.240 | 22.692 → 41.645 |
| mixed-25-250 | 201.153 → 136.738 | 495.919 → 427.799 | 174.928 → 106.156 | 443.478 → 326.334 | 2.529 → 0.003 | 182.367 → 21.611 | 669.739 → 11.772 | 689.074 → 19.494 | 297.063 → 73.003 | 80.379 → 73.003 |
| workers-1-delay-250 | 97.596 → 125.505 | 144.884 → 193.042 | 72.280 → 95.598 | 88.875 → 129.738 | 0.002 → 0.002 | 0.004 → 0.006 | 488.228 → 21.505 | 1046.403 → 661.347 | 10.978 → 28.011 | 5.364 → 6.645 |
| workers-2-delay-250 | 100.769 → 132.056 | 146.375 → 178.123 | 72.051 → 100.290 | 90.363 → 110.968 | 0.003 → 2.474 | 3.910 → 4.971 | 463.241 → 14.844 | 478.361 → 22.461 | 19.849 → 31.535 | 19.849 → 22.029 |
| workers-4-delay-250 | 100.349 → 186.085 | 149.805 → 200.085 | 72.761 → 146.991 | 95.442 → 171.845 | 2.212 → 0.007 | 12.521 → 25.670 | 451.288 → 22.959 | 468.839 → 29.827 | 33.170 → 112.587 | 33.117 → 105.203 |
| workers-8-delay-250 | 128.600 → 285.712 | 159.600 → 298.657 | 98.963 → 219.601 | 111.331 → 247.433 | 5.881 → 8.798 | 17.779 → 40.640 | 182.793 → 44.552 | 367.443 → 58.448 | 77.252 → 170.704 | 77.252 → 170.704 |
| workers-1-delay-0 | 93.944 → 139.525 | 141.966 → 179.024 | 68.830 → 103.425 | 93.689 → 122.606 | 0.002 → 0.002 | 0.005 → 0.007 | 489.744 → 19.080 | 539.511 → 202.815 | 8.739 → 27.698 | 4.855 → 8.377 |
| workers-2-delay-0 | 96.400 → 146.125 | 139.975 → 214.091 | 68.827 → 118.426 | 89.467 → 151.206 | 3.226 → 3.146 | 4.849 → 7.797 | 468.908 → 15.385 | 473.336 → 21.024 | 30.288 → 102.309 | 30.288 → 34.862 |
| workers-4-delay-0 | 113.663 → 232.397 | 167.239 → 251.842 | 86.684 → 192.772 | 111.602 → 200.359 | 0.006 → 3.709 | 13.427 → 23.616 | 8.514 → 23.442 | 195.140 → 32.193 | 58.265 → 110.273 | 58.265 → 110.273 |
| workers-8-delay-0 | 91.753 → 288.351 | 139.143 → 426.840 | 65.254 → 223.517 | 90.909 → 329.908 | 8.312 → 13.447 | 25.821 → 44.555 | 249.724 → 28.878 | 254.431 → 35.320 | 125.505 → 304.304 | 125.505 → 304.304 |
| idle | — → — | — → — | — → — | — → — | — → — | — → — | — → — | — → — | — → — | — → — |
| restart | 73.534 → 78.116 | 111.671 → 121.695 | 54.662 → 57.468 | 76.520 → 81.188 | 3.251 → 3.255 | 5.387 → 5.963 | 116.479 → 120.563 | 119.879 → 124.465 | 25.434 → 28.068 | 24.514 → 28.068 |

## Resources and provider bounds

| Point | CPU seconds | RSS MiB | Loop lag p95 | API client p95 | Write lock p95 | Provider peak | Active owner peak | Utilization |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single-poll-100 | 1.219 → 1.078 | 763.094 → 759.949 | 18.207 → 8.274 | 8.480 → 8.993 | 3.118 → 4.318 | 1.000 → 1.000 | 1.000 → 1.000 | 0.178 → 0.356 |
| single-poll-250 | 1.172 → 1.125 | 769.457 → 768.441 | 15.482 → 9.400 | 8.837 → 11.278 | 2.496 → 4.585 | 1.000 → 1.000 | 1.000 → 1.000 | 0.077 → 0.356 |
| single-poll-500 | 1.109 → 1.219 | 771.957 → 771.230 | 12.040 → 11.171 | 8.561 → 13.271 | 2.109 → 5.140 | 1.000 → 1.000 | 1.000 → 1.000 | 0.045 → 0.307 |
| single-poll-1000 | 1.141 → 0.984 | 774.504 → 773.074 | 11.917 → 10.752 | 8.172 → 11.267 | 1.884 → 4.505 | 1.000 → 1.000 | 1.000 → 1.000 | 0.021 → 0.318 |
| stagger-50 | 0.891 → 1.031 | 777.152 → 776.230 | 25.754 → 16.985 | 59.993 → 68.018 | 12.599 → 16.259 | 2.000 → 1.000 | 2.000 → 2.000 | 0.555 → 0.735 |
| stagger-100 | 0.922 → 1.062 | 778.293 → 776.602 | 15.543 → 17.684 | 86.145 → 15.645 | 9.304 → 4.376 | 1.000 → 1.000 | 2.000 → 1.000 | 0.409 → 0.212 |
| stagger-250 | 1.203 → 1.172 | 779.457 → 778.066 | 16.446 → 13.608 | 47.871 → 16.308 | 7.765 → 4.649 | 1.000 → 1.000 | 2.000 → 1.000 | 0.157 → 0.090 |
| stagger-750 | 1.438 → 1.438 | 779.422 → 778.355 | 12.021 → 12.022 | 16.644 → 16.510 | 2.879 → 4.672 | 1.000 → 1.000 | 1.000 → 1.000 | 0.030 → 0.030 |
| burst-1 | 0.062 → 0.047 | 781.395 → 778.684 | — → — | — → — | — → — | 1.000 → 1.000 | 1.000 → 1.000 | 0.075 → 0.730 |
| burst-2 | 0.109 → 0.062 | 781.035 → 777.992 | 11.869 → — | — → — | — → — | 1.000 → 1.000 | 1.000 → 1.000 | 0.137 → 0.769 |
| burst-5 | 0.297 → 0.297 | 784.156 → 781.805 | 12.109 → — | — → — | 7.603 → 13.800 | 1.000 → 1.000 | 1.000 → 1.000 | 0.323 → 0.761 |
| burst-10 | 0.469 → 0.453 | 788.234 → 785.500 | 11.378 → 11.212 | — → — | 21.319 → 25.382 | 1.000 → 1.000 | 1.000 → 1.000 | 0.404 → 0.770 |
| burst-25 | 1.203 → 1.109 | 800.133 → 796.652 | 11.521 → 6.646 | 139.782 → 180.195 | 45.216 → 30.896 | 1.000 → 1.000 | 1.000 → 1.000 | 0.586 → 0.806 |
| burst-50 | 2.219 → 2.172 | 808.695 → 804.508 | 8.874 → 9.177 | 275.359 → 347.385 | 94.460 → 73.906 | 1.000 → 1.000 | 1.000 → 1.000 | 0.686 → 0.831 |
| research-10-250 | 1.969 → 1.875 | 812.277 → 799.895 | 18.678 → 18.400 | 57.169 → 83.052 | 9.537 → 15.452 | 2.000 → 2.000 | 2.000 → 2.000 | 0.921 → 0.957 |
| mixed-25-250 | 12.781 → 10.562 | 835.551 → 828.281 | 19.781 → 20.076 | 185.806 → 163.276 | 221.143 → 41.946 | 2.000 → 2.000 | 2.000 → 2.000 | 0.858 → 0.928 |
| workers-1-delay-250 | 1.609 → 1.766 | 836.004 → 831.246 | 14.766 → 13.367 | 144.884 → 193.042 | 43.181 → 43.436 | 1.000 → 1.000 | 1.000 → 1.000 | 0.952 → 0.980 |
| workers-2-delay-250 | 1.344 → 1.438 | 835.844 → 824.820 | 19.912 → 17.488 | 146.375 → 178.123 | 48.402 → 24.501 | 2.000 → 2.000 | 2.000 → 2.000 | 0.891 → 0.936 |
| workers-4-delay-250 | 1.172 → 1.375 | 836.465 → 830.406 | 23.066 → 20.361 | 149.805 → 200.085 | 50.920 → 35.541 | 4.000 → 4.000 | 4.000 → 4.000 | 0.812 → 0.856 |
| workers-8-delay-250 | 1.156 → 1.312 | 836.668 → 833.750 | 29.100 → 49.996 | 159.600 → 298.657 | 54.019 → 53.051 | 8.000 → 8.000 | 8.000 → 8.000 | 0.692 → 0.768 |
| workers-1-delay-0 | 1.188 → 1.203 | 836.699 → 833.801 | 11.264 → 11.683 | 141.966 → 179.024 | 49.303 → 33.006 | 1.000 → 1.000 | 1.000 → 1.000 | 0.584 → 0.824 |
| workers-2-delay-0 | 1.156 → 1.047 | 836.703 → 833.746 | 21.059 → 21.589 | 139.975 → 214.091 | 47.753 → 40.763 | 2.000 → 1.000 | 2.000 → 2.000 | 0.589 → 0.753 |
| workers-4-delay-0 | 1.062 → 1.062 | 836.727 → 835.648 | 28.641 → 43.715 | 167.239 → 251.842 | 42.967 → 37.662 | 3.000 → 3.000 | 4.000 → 4.000 | 0.541 → 0.688 |
| workers-8-delay-0 | 1.109 → 1.453 | 837.410 → 835.828 | 52.497 → 97.120 | 139.143 → 426.840 | 50.018 → 49.284 | 5.000 → 5.000 | 8.000 → 8.000 | 0.527 → 0.605 |
| idle | 0.094 → 0.016 | 838.359 → 822.891 | 12.006 → 11.965 | — → — | — → — | 0.000 → 0.000 | 0.000 → 0.000 | 0.000 → 0.000 |
| restart | 0.938 → 0.906 | 831.293 → 831.941 | 23.704 → 19.919 | 111.671 → 121.695 | 43.163 → 39.162 | 1.000 → 1.000 | 2.000 → 2.000 | 0.706 → 0.684 |

## Queue overlap percentages (independent, not additive)

| Point | Full serving capacity % | Any idle consumer % | Any claim % | Any provider % | Global next attempt p95 | Successful claim p95 | Later claim p95 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-poll-100 | 0.000 → 0.000 | 98.381 → 30.709 | 10.580 → 70.911 | 0.000 → 0.000 | 90.115 → 1.887 | 12.449 → 5.472 | — → — |
| single-poll-250 | 0.000 → 0.000 | 99.327 → 31.333 | 3.356 → 69.332 | 0.000 → 0.000 | 249.631 → 2.720 | 12.442 → 7.989 | — → — |
| single-poll-500 | 0.000 → 0.000 | 99.564 → 54.779 | 1.696 → 45.428 | 0.000 → 0.000 | 492.769 → 2.924 | 12.046 → 8.793 | — → — |
| single-poll-1000 | 0.000 → 0.000 | 99.778 → 29.051 | 0.779 → 55.819 | 0.000 → 0.000 | 988.108 → 2.205 | 12.640 → 6.849 | — → — |
| stagger-50 | 48.046 → 59.574 | 23.106 → 0.355 | 15.956 → 20.315 | 2.067 → 1.012 | 428.848 → 96.240 | 21.371 → 37.408 | — → — |
| stagger-100 | 26.496 → 0.000 | 59.606 → 35.654 | 13.147 → 66.091 | 0.667 → 0.000 | 387.667 → 2.763 | 25.819 → 6.275 | — → — |
| stagger-250 | 2.658 → 0.000 | 92.816 → 35.500 | 4.252 → 66.831 | 0.041 → 0.000 | 448.263 → 2.858 | 24.711 → 6.667 | — → — |
| stagger-750 | 0.000 → 0.000 | 99.360 → 35.009 | 3.105 → 65.386 | 0.000 → 0.000 | 471.617 → 2.753 | 11.446 → 6.096 | — → — |
| burst-1 | 0.000 → 0.000 | 98.150 → 45.083 | 1.688 → 54.255 | 0.000 → 0.000 | — → — | — → — | — → — |
| burst-2 | 3.827 → 67.518 | 93.940 → 2.524 | 2.274 → 23.562 | 0.022 → 0.387 | — → — | — → — | — → — |
| burst-5 | 17.638 → 72.949 | 77.815 → 0.231 | 3.124 → 18.102 | 0.119 → 0.710 | — → — | — → — | — → — |
| burst-10 | 27.525 → 79.899 | 65.155 → 0.209 | 4.125 → 12.306 | 0.237 → 0.758 | — → — | — → — | — → — |
| burst-25 | 50.139 → 83.684 | 37.342 → 0.055 | 6.914 → 8.213 | 0.432 → 0.985 | 429.506 → 164.426 | 5.747 → 5.725 | 4.841 → 5.443 |
| burst-50 | 64.489 → 80.621 | 21.439 → 0.009 | 7.316 → 6.719 | 0.675 → 0.736 | 441.613 → 303.459 | 4.950 → 5.640 | 4.902 → 4.593 |
| research-10-250 | 88.040 → 93.976 | 7.785 → 0.008 | 2.202 → 3.525 | 92.070 → 90.144 | 720.912 → 940.595 | 21.219 → 41.645 | — → — |
| mixed-25-250 | 81.227 → 92.093 | 3.871 → 0.004 | 9.608 → 4.833 | 78.582 → 88.473 | 1207.744 → 1126.657 | 234.363 → 61.074 | 64.265 → 49.570 |
| workers-1-delay-250 | 92.951 → 98.251 | 5.615 → 0.004 | 0.851 → 0.870 | 84.096 → 88.875 | 467.123 → 626.340 | 5.364 → 7.102 | 5.265 → 6.140 |
| workers-2-delay-250 | 85.914 → 95.548 | 10.596 → 0.008 | 2.422 → 3.297 | 83.260 → 90.026 | 448.627 → 623.939 | 17.387 → 22.471 | 17.387 → 19.996 |
| workers-4-delay-250 | 74.929 → 85.926 | 19.028 → 0.015 | 5.292 → 7.684 | 77.762 → 94.760 | 432.438 → 573.429 | 33.117 → 105.203 | 33.064 → 84.921 |
| workers-8-delay-250 | 43.980 → 66.681 | 35.381 → 3.463 | 20.865 → 27.182 | 81.759 → 90.866 | 348.722 → 490.284 | 69.363 → 170.704 | 69.363 → 170.704 |
| workers-1-delay-0 | 47.442 → 83.536 | 41.119 → 0.038 | 5.756 → 7.272 | 0.424 → 0.803 | 471.872 → 175.836 | 4.855 → 8.377 | 4.182 → 6.685 |
| workers-2-delay-0 | 38.208 → 63.747 | 36.237 → 0.029 | 16.322 → 22.628 | 1.644 → 2.268 | 454.485 → 222.786 | 25.220 → 31.492 | 25.220 → 31.097 |
| workers-4-delay-0 | 13.535 → 34.631 | 42.085 → 0.055 | 28.981 → 39.444 | 5.817 → 7.525 | 273.096 → 312.746 | 55.374 → 108.521 | 55.374 → 108.521 |
| workers-8-delay-0 | 8.109 → 23.328 | 55.515 → 0.503 | 35.651 → 70.845 | 11.246 → 26.881 | 236.752 → 349.476 | 107.909 → 234.292 | 107.909 → 182.085 |
| idle | — → — | — → — | — → — | — → — | — → — | — → — | — → — |
| restart | 60.952 → 52.347 | 0.000 → 0.000 | 16.878 → 22.499 | 3.102 → 2.505 | 96.875 → 105.238 | 19.485 → 26.989 | — → — |

## Notification / idle counters

Measured counters per trial (startup/shutdown whole-trial shown separately). Before had zero signal attempts and signal wakes.

| Point | Accepted hints | Coalesced hints | Signal wakes | Poll timeouts | Empty claims | Empty checks/s before → after | Whole startup/shutdown |
| --- | --- | --- | --- | --- | --- | --- | --- |
| single-poll-100 | 20/20/20 | 0/0/0 | 40/39/40 | 0/1/0 | 39/39/39 | 14.602 → 33.270 | 2:2/2:2/2:2 |
| single-poll-250 | 20/20/20 | 0/0/0 | 40/40/40 | 1/0/0 | 40/39/39 | 6.822 → 30.532 | 2:2/2:2/2:2 |
| single-poll-500 | 20/20/20 | 0/0/0 | 40/40/40 | 0/0/0 | 39/39/39 | 3.631 → 24.320 | 2:2/2:2/2:2 |
| single-poll-1000 | 20/20/20 | 0/0/0 | 40/40/40 | 0/0/0 | 39/39/39 | 1.887 → 27.635 | 2:2/2:2/2:2 |
| stagger-50 | 20/20/20 | 17/17/15 | 4/4/6 | 0/0/0 | 3/3/5 | 0.578 → 2.124 | 2:2/2:2/2:2 |
| stagger-100 | 20/20/20 | 0/0/1 | 40/40/36 | 0/0/0 | 39/39/35 | 1.449 → 19.779 | 2:2/2:2/2:2 |
| stagger-250 | 20/20/20 | 0/0/0 | 40/40/40 | 0/0/0 | 39/39/39 | 2.950 → 8.106 | 2:2/2:2/2:2 |
| stagger-750 | 20/20/20 | 0/0/0 | 40/40/40 | 38/38/38 | 77/77/77 | 3.724 → 5.381 | 2:2/2:2/2:2 |
| burst-1 | 1/1/1 | 0/0/0 | 1/1/1 | 0/0/0 | 0/0/0 | 0.000 → 0.000 | 1:0/1:0/1:0 |
| burst-2 | 2/2/2 | 0/0/0 | 1/1/1 | 0/0/0 | 0/0/0 | 0.000 → 0.000 | 1:0/1:1/1:1 |
| burst-5 | 5/5/5 | 3/3/3 | 1/1/1 | 0/0/0 | 0/0/0 | 0.000 → 0.000 | 1:1/1:1/1:1 |
| burst-10 | 10/10/10 | 8/8/8 | 1/1/1 | 0/0/0 | 0/0/0 | 0.000 → 0.000 | 1:1/1:1/1:1 |
| burst-25 | 25/25/25 | 23/23/23 | 1/1/1 | 0/0/0 | 0/0/0 | 0.000 → 0.000 | 1:1/1:1/1:1 |
| burst-50 | 50/50/50 | 48/48/48 | 1/1/1 | 0/0/0 | 0/0/0 | 0.000 → 0.000 | 1:1/1:1/1:1 |
| research-10-250 | 20/20/20 | 18/18/18 | 3/3/3 | 0/0/0 | 3/2/3 | 0.220 → 0.334 | 2:2/2:2/2:2 |
| mixed-25-250 | 25/25/25 | 23/23/23 | 3/3/3 | 1/1/1 | 4/4/4 | 0.223 → 0.326 | 2:2/2:2/2:2 |
| workers-1-delay-250 | 25/25/25 | 23/23/23 | 1/1/1 | 0/0/0 | 0/0/0 | 0.068 → 0.000 | 1:1/1:1/1:1 |
| workers-2-delay-250 | 25/25/25 | 23/23/23 | 3/3/3 | 0/1/1 | 3/3/2 | 0.254 → 0.371 | 2:2/2:2/2:2 |
| workers-4-delay-250 | 25/25/25 | 23/23/22 | 5/2/6 | 1/0/3 | 8/5/8 | 0.623 → 1.745 | 4:4/4:4/4:4 |
| workers-8-delay-250 | 25/25/25 | 21/21/21 | 13/13/13 | 0/0/0 | 14/12/11 | 3.751 → 4.037 | 8:8/8:8/8:8 |
| workers-1-delay-0 | 25/25/25 | 23/23/23 | 1/2/1 | 0/0/0 | 0/2/0 | 0.522 → 0.000 | 1:1/1:1/1:1 |
| workers-2-delay-0 | 25/25/25 | 23/23/23 | 3/3/3 | 0/0/0 | 2/2/4 | 0.496 → 1.201 | 2:2/2:2/2:2 |
| workers-4-delay-0 | 25/25/25 | 23/23/23 | 5/3/4 | 0/0/0 | 4/5/7 | 1.611 → 3.111 | 4:4/4:4/4:4 |
| workers-8-delay-0 | 25/25/25 | 21/23/21 | 13/6/14 | 0/0/0 | 12/8/13 | 3.973 → 6.748 | 8:8/8:8/8:8 |
| idle | 0/0/0 | 0/0/0 | 0/0/0 | 14/15/16 | 14/14/14 | 3.496 → 3.507 | 2:2/2:2/2:2 |
| restart | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/1/0 | 0.707 → 0.000 | 4:4/4:4/4:4 |
