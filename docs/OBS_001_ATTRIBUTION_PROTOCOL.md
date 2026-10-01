# OBS-001 attribution protocol

Protocol: **obs-001-attribution-v1**. This is an optional measurement extension;
the required roadmap, Agent extension, PROVIDER-001 and SCALE-001/002 remain
complete. No optimization, production load certification or quality score.

## Runtime and authority

`ENABLE_PERFORMANCE_ATTRIBUTION=false` is the default. Opt in on the server in
local workspace mode. Authorized Agent HTTP requests and successful Agent worker
claim/execution cycles emit one terminal summary after product locks are released.
Unauthorized/public requests cannot open a private store through this feature.
No import-time worker starts. Workers remain two, polling 500ms, grace 5000ms.

DATA-005's existing `telemetry_events` table stores `performance_terminal` rows,
record schema 1, closed route/source classification and typed protocol metadata.
SQLite stays v7: no migration, second database, dependency or new endpoint.
Summaries retain 30 days and share existing pruning. Raw monotonic intervals are
ephemeral and never persisted. Existing request/quality populations and public
`/metrics` stay separate. Protected `/analytics/summary` adds `performance`, a
bounded aggregation of at most the latest 10,000 eligible terminal summaries;
`truncated` explicitly identifies that ceiling. Legacy operational job projections
exclude Agent jobs, which their pipeline/evaluation/model-test schema cannot
represent; unknown/corrupt namespaces still fail closed.

## Timing and bounds

`perf_counter_ns` intervals become finite milliseconds. All phase, operation,
outcome and source classifications are closed; no arbitrary metadata, payload,
SQL, exception, header, prompt, answer, evidence, provider content, rationale,
credential, machine identity or absolute path is captured. Safe server request
correlation or opaque job identity binds a summary; private analytics publishes
aggregates without those identities. Correlation validation reuses DATA-005's
configured-secret guard. The existing durable frozen goal/product answer contract
is unchanged: content-free attribution does not erase legitimate product data.

Maximum 128 spans per API request, 512 per worker run, 64 phase/operation groups,
16,384 UTF-8 bytes per summary; duration bound 24 hours. Deferred observations
have the same hard span limit. Excess observations increment a bounded dropped
counter. The root span is retained; a dropped trace has no inferred remainder.
Context variables follow thread offloading and reset on errors/cancellation;
closed traces discard late observations. Instrumentation locks only protect
short bounded in-memory appends, never product work. DB observations are buffered
locally and emitted after the outer existing reentrant serialization lock releases.

Spans are **inclusive** and can overlap or nest. Do not add their durations or
percentiles to recover a total. API remainder subtracts the union of clipped
observed intervals from exactly one API root; it is available only without drops.
Root total runs from middleware entry through final body send returning. It
includes response processing/scheduling but does not measure physical delivery.
DATA-005 persistence happens afterwards and is outside that root; its cost is
included in benchmark CPU/throughput and can influence subsequent work. Sink
failures log only a fixed safe code and never rewrite the product response.
No durable row is written for an empty/error worker poll. Abrupt shutdown can
lose an in-memory partial trace; product interruption/recovery remains authoritative.

## Phase taxonomy

| Family | Phases | Meaning |
| --- | --- | --- |
| API | `api.total`, `api.access`, `api.validation`, `api.freeze`, `api.admission`, `api.read`, `api.service_init` | ASGI total, owned access, protected-value validation, frozen-plan construction, create/read coordinators and factory initialization. Framework DTO validation/response serialization remains in total/remainder. |
| SQLite | `workspace.serialized_wait`, `workspace.critical_section`, `workspace.connection_open`, `workspace.transaction`, `workspace.read`, `workspace.initialize` | Wait for existing Python lock; holding its boundary; connection plus PRAGMAs; BEGIN through commit/rollback; yielded read connection work; integrity/schema/receipt initialization. |
| Worker | `worker.cycle`, `worker.claim`, `worker.service`, `worker.poll_wait`, `worker.queue_wait` | Successful iteration, claim including thread scheduling, execution/reconciliation, last completed idle sleep before that claim. Queue wait is computed by benchmark commit observer. |
| Agent | `agent.decision`, `agent.provider`, `agent.persist_result` | Decision request/parse boundary, actual SDK await and result/CAS persistence. |
| Tools | `agent.tool.search_documents`, `agent.tool.inspect_retrieval`, `agent.tool.read_document`, `agent.tool.ask_rag` | Closed known invocation including policy/input/output checks and success/failure. Unknown tool names cannot become phase names. |
| Services | `retrieval.search`, `retrieval.inspect`, `generator.transport` | Existing adapter service boundary and normal Generator completion transport; no deep BM25/dense/reranker refactor. |
| Evaluation/SSE | `evaluation.compute`, `sse.read_events`, `sse.serialize`, `sse.send` | Native 21-metric compute, event read/view, per-frame JSON construction, awaited ASGI send contribution. |

SQLite transaction/read spans include Python work inside those connection scopes,
not just SQLite engine CPU. Connection opening/PRAGMAs and initialization are
separate and may dominate critical-section hold. SQLite busy wait can occur
inside those scopes. Measurements distinguish lock waiting from database-boundary
work; they cannot prove pure engine execution time without deeper profiling.

Operations: `none`, `job_create`, `job_claim`, `job_transition`, `job_step`,
`job_read`, `job_list`, `job_event_read`, `job_event_append`, `job_cancel`,
`job_recover`. Outcomes: `completed`, `rejected`, `failed`, `cancelled` describe
the timed callable, not an inferred durable job state. Caught failures may yield
a completed coordinator span; durable outcome is checked separately.

## Queue/poll authority

SCALE-002's existing test connection subclass observes authoritative job-event
commits using monotonic time: created commit to successful running/claim commit
is queue wait, claim to terminal commit is service, created to terminal is E2E.
The observer attaches through the repository-owned connection factory, without
patching SQLite internals. No production map grows with queued rows. Production
wall-clock timestamps still correlate lifecycle facts; they are never treated as
monotonic elapsed durations after restart. `worker.queue_wait` is reserved for
that closed concept; the benchmark reports `queue_wait_ms` from commit boundaries,
and production summaries do not fabricate this span. Poll sleep is an observation
of the last idle interval, not the time this particular job spent in the queue.

## Fixed campaign

Commit runtime/harness/tests before canonical measurements. Run:

```powershell
.venv\Scripts\python.exe -m scripts.benchmarks.obs_001 --smoke --output .local/obs-001/smoke.json
.venv\Scripts\python.exe -m scripts.benchmarks.obs_001 --output .local/obs-001/campaign.json
```

No `.env`, live provider, network corpus or `data/` mutation is needed. Real
loopback TCP, production access/routers/services/SQLite/lifespan/pool/SDK protocol
are retained; only corpus and external provider transport are deterministic.
Existing SCALE-002 correctness gates, warmup and workloads are reused.

| Anchor | Clients | Operations | Workers | Synthetic delay |
| --- | ---: | ---: | ---: | ---: |
| Admission | 50 | 200 creates | 2 (disabled consumer) | 0ms |
| Reads | 50 | 200 reads, 50 each list/detail/result/evaluation | 2 | 0ms |
| Research | 10 | 20 jobs | 2 | 0ms |
| Research | 10 | 20 jobs | 2 | 250ms |
| Mixed | 25 | 25 jobs with reads/SSE/evaluation | 2 | 250ms |
| SSE | 25 | 25 subscribers, one research job | 2 | 250ms |

Three measured trials per anchor, four warmup operations excluded, instrumentation
disabled then enabled with the same workloads. Four separate low-concurrency
worker campaigns: one client, 20 sequential jobs, 100/250/500/1000ms temporary
polling, three trials each. Ordered campaigns are not randomized; cache/machine
noise and same-process client/server coupling limit causal overhead claims.
Deadlines: per-trial workload bound plus at most 90s startup/shutdown allowance;
campaign 1800s by default, max 3600s. Checkpoints stay incomplete until all gates
pass. At most 4096 traces/client correlations and 65,536 spans per trial;
budget/dropped/missing observations block a canonical result.

Nearest rank p50 requires two, p95 twenty, p99 one hundred samples; unavailable
is null, never NaN/Infinity. Per-trial phases use individual inclusive spans;
durable analytics uses inclusive phase total per terminal, explicitly labelled.
Campaign statistics are medians of per-trial statistics, never pooled percentiles.
Per-route operation groups are separate. Server totals pair to exact client
requests through safe correlation IDs. `client_observed_minus_server_ms` is signed
and can include client/event-loop/scheduling overhead: **not network latency**.
SSE commit-to-client-frame delivery and server batch work have different windows;
compare them separately, not by subtracting unrelated percentiles. CPU/RSS/lag
scope is the combined server/client process. Enabled volume includes actual
DATA-005 writes; disabled still runs the common no-op boundary wrappers and
SCALE-002 observers, so the comparison is the opt-in capture/persistence cost.

Correctness gates cover ownership/capacity/provider attempts, durable outcomes,
event order, SSE duplicates/missing/resume, mutation after terminal, database
busy/integrity, same-database reopen v7 and zero active jobs after shutdown.
No optimization follows measurement automatically. The final receipt selects
one next task from the evidence and records uncertainty.
