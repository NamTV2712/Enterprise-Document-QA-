# DB-SCALE-001 repository comparison protocol

Campaign **db-scale-001-v1**. Workload/statistics **scale-002-benchmark-v1**;
attribution **obs-001-attribution-v1**. This is a bounded local repository task,
not a quality evaluation, production capacity/SLA claim or SCALE-003 cache task.

## Audit and candidate boundaries

Before: each operation owns a short-lived SQLite connection. Read connections
do not take the Python writer RLock. Authorized service factories nevertheless
call full integrity/schema initialization on every request under that RLock.
This puts even read/SSE factories behind other initializers and writes. Writers
already keep provider/tools/HTTP/sleeps outside transactions; no rewrite is needed.

Candidate: factories call `ensure_initialized()`. A weak per-canonical-path state
shares one complete validation receipt, bound to file identity and the exact
migration tuple. Cold callers synchronize through a separate reentrant initialization
guard; full validation still takes the existing writer boundary and nested migration
transactions. Warm receipt checks do not take either lock or open a connection.
Missing/replaced files, unsupported file identity or another migration contract
cannot use the receipt. Last live owner release discards it. No global initialized
boolean, job/event/result cache, persistent connection, pool or lifecycle authority.

Explicit `initialize()` always performs full integrity/schema/receipt validation,
publishes only on success and invalidates on failure. Reopen/audit uses it. Ordinary
writes do not invalidate a receipt: it describes initialization, not contents.
External in-place schema edits are not checked on every hot request; use explicit
validation/restart. Replacing a live database concurrently with active operations
is unsupported. Public mode still rejects construction before opening storage;
imports start no database/pool. The local lifespan retains its live repository.

Job detail/list/event reads use their own explicit read transaction so multi-query
rows, steps, counts and events represent one committed snapshot. The snapshot ends
when the connection closes, before HTTP frame serialization or network sending.
Connections are never shared across threads/cursors. A setup failure also closes
the just-created handle. WAL/NORMAL, busy timeout 5000ms and schema v7 remain.

Writes retain the same canonical-path RLock and transaction-local helpers,
`BEGIN IMMEDIATE`, revisions/CAS, claim ordering, strict events and terminal
immutability. Startup recovery still interrupts ambiguous owned work, preserves
queued work and never replays external effects. DATA-004/005 remain authorities.
Portable backup keeps its existing snapshot and private-history exclusions.

SQLite documents concurrent WAL readers/writers and transaction snapshots in
[WAL concurrency](https://www.sqlite.org/wal.html#concurrency) and
[isolation](https://www.sqlite.org/isolation.html). Deterministic repository tests
verify that behavior with these actual connections and PRAGMAs.

## Measurement

Reuse `obs_001.trial` and `obs_001.summarize`; the DB driver adds bounded safe
scalar initialization counters, not new phase meanings. One canonical campaign
is five enabled points / 15 trials:

| Scenario | Clients | Operations | Workers | Synthetic provider delay |
| --- | ---: | ---: | ---: | ---: |
| Read | 50 | 200, rotating list/detail/result/evaluation | 2 | 0ms |
| Mixed | 25 | 25 research jobs plus reads/evaluation/SSE | 2 | 250ms |
| SSE | 25 | 25 subscribers, one research job | 2 | 250ms |
| Research | 10 | 20 jobs | 2 | 250ms |
| Admission control | 50 | 200 creates, consumers disabled | 2 configured | 0ms |

Three trials each, four warmups excluded; fresh temporary SQLite per trial. Real
loopback HTTP/access/routers/SQLite/workers/Agent/SDK protocol remain. Only corpus
and external provider transport are synthetic. No live Groq/SEC or canonical data
mutation. Startup/warmup/reopen are excluded from duration/resource populations.

Initialization counters deliberately cover the **whole trial including startup,
warmup and reopen**: `ensure_calls`, explicit `initialize_calls`, and
`expensive_initializations` (`_initialize_locked` entries). Ensure can call
initialize, so do not add those two call counters. Counters use a short local lock
and retain no path/DB identity; expensive path entries are not assumed successful
until trial correctness/integrity passes. Race tests separately prove per-store
once publication, isolation, rollback/retry and no partial-schema reads.

Baseline runs on starting SHA with the unchanged committed OBS/SCALE harness,
through a byte-fingerprinted ignored driver. The identical driver is then committed
for after measurements; report driver/harness SHA256 and runtime SHA separately.
Do not merge checkpoints. Canonical after requires committed tracked-clean runtime.
Commands (project interpreter, no private files needed):

```powershell
.venv\Scripts\python.exe -m scripts.benchmarks.db_scale_001 --smoke --stage diagnostic --output .local/db-scale-001/smoke.json
.venv\Scripts\python.exe -m scripts.benchmarks.db_scale_001 --stage after --output .local/db-scale-001/after.json
```

Driver deadline 1200s; inherited OBS trial deadline 120–240s plus at most 90s
startup/shutdown allowance. Failed checkpoints remain incomplete with fixed safe
failure categories; CLI emits no raw exception. No raw report/DB/log is committed.

Nearest-rank sample minima p50=2, p95=20, p99=100; unavailable is null, not zero.
Summaries are medians of per-trial statistics, never pooled or best-trial selection.
Report before/after, absolute delta and relative delta where denominator/population
supports it. Per-source/route/operation populations remain distinct. Shared
client/server/capture CPU/RSS/loop measurements, ordered trials, random durable API
sampling and three-trial populations limit causal precision; no confidence interval.

## OBS comparability

`workspace.serialized_wait` still measures the same writer RLock acquisition;
`workspace.transaction` still measures BEGIN through commit/rollback and includes
Python work. Neither is redefined. Full initialization spans retain validation
semantics, now including the cold initialization guard; warm factories emit no
initialization span. Warm read/SSE routes therefore have **no writer-wait samples**,
reported unavailable/eliminated boundary, never fabricated zero-duration spans.
Read spans keep their connection scope, now including explicit BEGIN where needed.
No timing version change: these are reduced calls and stronger snapshot behavior.

API totals/remainder stay ASGI entry → final awaited body send; remainder uses
interval union. Paired signed client-minus-server is not network latency. SSE
event commit → client frame differs from finite server batch processing; never
subtract their unpaired percentiles. Queue/service/E2E remain monotonic event
commit boundaries, not wall-clock elapsed durations. Deferred observations remain
outside the writer lock; telemetry cannot become write serialization authority.
Sampling, retention, metadata/span bounds and secret protections are unchanged.

## Acceptance

All lost/duplicate jobs/claims/execution, revisions/events, terminal mutation,
SSE ordering/missing/resume, capacity, SQLite busy/error/integrity and missing/dropped
attribution counters must be zero. Every trial reopens the same DB at v7 and has
zero active rows after shutdown. Admission intentionally leaves queued work.

Retain only repeatable target wait reduction with correctness and no unexplained
material latency/throughput regression. Validate deterministic initializers, readers,
read-during-write snapshots, CAS/claim/event/cancel races, bounded fairness, actual
Agent/SSE overlap, restart/recovery, backup and OBS/CRED/provider regressions.
Then full backend, exact-final-HEAD clean release, secret/artifact audit, receipt,
normal main push and SHA equality/0-0. Choose exactly one evidence-backed next task
but implement none. Required roadmap/SCALE-001/002/OBS stay complete; SCALE-003 is
not started. STOP after verified release.
