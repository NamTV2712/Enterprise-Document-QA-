# SCALE-002 benchmark protocol

Protocol: **scale-002-benchmark-v1**. Starting product SHA:
`009b04e699bc9e61b4dd37722076e1ad6237c567`. This characterizes the current
development environment. It certifies no production SLA or maximum user count.
Production defaults, dependency files, routes (90), schema (v7), Agent/provider
semantics and completed milestones remain unchanged.

## Architecture audit and boundaries

Real FastAPI routes, middleware, API-001 Host/Origin/loopback/bearer/execution
authorization, DATA-004, WorkerSupervisor, closed Agent executor, frozen plan,
AgentOrchestrator, tools, event persistence, cancellation and native evaluation
remain in the measured path. Existing request telemetry stays enabled. The
DATA-005 route catalog excludes Agent routes, so no persisted Agent request
telemetry write cost is claimed. No duplicate production telemetry is added.
The only production eligible executor remains `agent / bounded_agent_run`.
Pipeline, Evaluation and model-test remain excluded.

Use actual TCP loopback HTTP (Uvicorn and httpx), not buffered ASGITransport or
browsers as load generators. The client and server share one process/event loop;
CPU/RSS and loop lag therefore include both. One API process uses the existing
serialized RLock, SQLite WAL/NORMAL, 5000ms busy timeout and BEGIN IMMEDIATE
claims. Other-process/multi-host contention is outside this protocol.

### Modes

- **hermetic (required/default):** production application lifespan with the
  existing TEST-004 synthetic corpus/model dependencies. Real Groq 1.5.0 SDK
  and strict decision adapter call httpx.MockTransport. The model itself never
  executes tools; the existing registry/orchestrator does. Canonical synthetic
  AAPL/MSFT document/chunk identities are used. No corpus/model download.
- **artifact (optional):** full production local corpus/index/retriever/reader
  bootstrap, replacing only Generator and decision transport. Requires local
  index, manifest and source availability, offline cached models, and exclusive
  local Qdrant access. Uses the first catalog document/ticker for bounded local
  evidence. The chosen search/read path exercises corpus discovery/BM25 and chunk
  reading; initialized dense/reranker components do not establish measured
  dense/reranker performance. Results are a separate artifact-dependent series,
  never mixed with hermetic results. Missing prerequisites are a recorded skip. Startup failure
  is recorded rather than represented as successful performance evidence.
  The CLI launches artifact mode as an isolated child with an external command
  deadline (campaign budget + 120s), so synchronous cached-model startup cannot
  prevent wall-time termination. Async trial/startup deadlines remain internal.
  Bind the artifact series to the local index manifest SHA256 without its path.

Both modes install the existing offline socket guard for their entire lifetime.
Only loopback sockets are possible. Credentials are synthetic; inherited provider
keys, fallback keys and cloud credentials are replaced. Provider clients use
MockTransport, trust_env=False for product HTTP, and max_retries=0. No live
Groq smoke/load/retry, external HTTP or user workspace history is involved.

## Instrumentation and time semantics

Use time.perf_counter for all elapsed/client/commit durations. UTC durable
timestamps remain unchanged and are only lifecycle correlation facts. A
benchmark-only sqlite3.Connection subclass observes the existing job_events
INSERT statements, buffers content-free job/sequence/type/state identities,
and records monotonic time immediately **after successful commit**. Rollback
discards its pending observations. No extra query is added to each commit.
The production connection factory, SQL, locks, transactions and result are
otherwise preserved. Wrappers observe claim duration, RLock wait, executor
ownership, tool invocation and mocked transport await. These add small overhead;
the campaign does not subtract or claim to eliminate it.

- Queue wait: created-event commit → successful running-claim commit.
- Service: running-claim commit → terminal-event commit.
- End-to-end: created-event commit → terminal-event commit.
- Validate end-to-end = queue wait + service using the same monotonic clock.
- Claim: claim_next_job entry → returned successful claim, including lock/DB
  access. Empty polls are not successful-claim latency samples.
- Write transaction: after BEGIN IMMEDIATE → commit completion, excluding the
  earlier Python lock wait. Lock wait includes existing initialization/write
  lock acquisitions; it is not exclusively claim waiting.
- Run throughput: succeeded jobs / first measured creation to last measured
  terminal commit. Expected failed/cancelled jobs are separately counted.
- HTTP throughput: successful measured requests / client workload interval.
  Breakdown by endpoint preserves admission/read/evaluation/SSE costs.
- Research verifies results and 21-metric evaluation through HTTP after each
  terminal result; workflow interval includes those requests. Durable run time
  ends at terminal commit, rather than late evaluation scheduling.
- SSE delivery: committed event → received frame, including TCP/client cost
  and documented pull/reconnect scheduling, not provider latency.

The SDK profiles are **synthetic** artificial delay per decision HTTP call:
instant **0ms**, moderate **250ms**, optional slow **1000ms**. An observed
transport await can exceed that value under load. These are not Groq timings.
Worker execution uses read→final (two calls), research uses search→read→final
(three calls). Corpus/retrieval stages in hermetic mode are synthetic; this
campaign cannot identify a production retrieval/reranker bottleneck.

## Warmup, trials and statistics

Each trial uses a fresh temporary database and fresh application lifespan.
Warmup creates four jobs (admission leaves them queued), completes them where
workers are enabled, then exercises all four read endpoints. SSE/mixed also
warms one subscription. The read campaign uses 20 warmup terminal rows so list
responses and shared warm storage are represented. Warmup initializes imports,
SQLite/schema, worker startup, HTTP pools, tool fixtures and SDK paths.
All warmup operations and timing samples are excluded from measurement.
Cold imports/startup are not included in steady-state latency; no cold-start
claim is made. Four warmup reads are additional to the configured job count.

Use three measured trials at every primary scenario. Preserve trial boundaries;
summaries are **medians of per-trial statistics**, never pooled heterogeneous
requests, worker capacities, latency profiles or trials. Nearest-rank percentile
is sorted sample at ceil(p*n), one-based. p50 requires ≥2 samples, p95 ≥20,
p99 ≥100. Smaller samples return null/insufficient_samples, including any p99
from 20/25/50-run scenarios. No exact time assertion is a functional test.

Safe report binding includes protocol, exact git SHA, committed-harness flag,
harness SHA256, configuration, fixture/mode, OS family/version, Python/SQLite/
dependency versions, logical CPU count and total RAM when the Windows API can
provide it. It contains no hostname, username, private path, header, credentials,
goal/evidence content or provider transcript. JSON forbids NaN/Infinity.

## Primary matrix and load model

| Profile | Definition | Clients | Operations per trial | Workers | Synthetic delay |
| --- | --- | --- | --- | --- | --- |
| Admission | POST /agent/runs, worker disabled; access/validation/freeze/SQLite/response | 1,5,10,25,50,100 | 200 | 2 configured, 0 executing | 0ms; zero model calls |
| Read | Rotate list/detail/result/terminal evaluation evenly | 1,5,10,25,50,100 | 200 (50 per endpoint) | 2, warm fixture idle | 0ms |
| Worker baseline | Closed-loop create→terminal, read→final | 1,2,5,10,25,50 | 20; 25/50 at levels 25/50 | 2 | 0 and 250ms |
| Worker sweep | Hold client/workload/delay constant | 25 | 25 | 1,2,4,8 | 0 and 250ms |
| Research | Closed-loop create→search→read→final→result/evaluation | 1,2,5,10,25,50 | 20; 25/50 at levels 25/50 | 2 | 0 and 250ms |
| SSE | Finite batches/reconnect on one live research run + suffix resume | 1,10,25,50 | One subscriber per client | 2 | 250ms |
| Mixed | Each lane creates, reads list+detail, subscribes until terminal, reads result+evaluation | 5,25,50 | 5/25/50 jobs, one per client | 2 | 250ms |
| Cancellation | Six admitted jobs; cancel two queued and one in-flight; stale revision refusal | 6 | 6 jobs | 2 | 250ms + explicit release barrier |
| Degraded | First measured synthetic goal selects one HTTP 503, no retry; following jobs drain | 10 | 20 jobs | 2 | 250ms |

Worker sweep's worker=2 points reuse the identical baseline point rather than
manufacturing extra measurements. Stateless lanes send the next request after
the previous response. Worker/research lanes hold one outstanding run until
terminal (and research result/evaluation) before submitting their next run;
the requested run concurrency is not merely admission fanout. SSE connections
are finite batches under the existing contract, polled every 100ms until an
actual terminal frame, then checked against durable IDs and resumed after ID 3.
Mixed ratio per job is one create, two initial reads, two terminal reads and
one subscriber with variable batch/resume requests. It is a declared test
mixture, not inferred production traffic.

Full-run 100, workers 16, and the slow profile are optional escalation, not
required matrix points. Record every level actually run and any deviation.
Primary heavy work is bounded at 50 concurrent clients and 8 workers.

## Safety and correctness gates

Each trial deadline is min(240s, max(30s, 30s + 3 * jobs * expected decision
calls * configured synthetic seconds / workers)). HTTP deadline is 30s,
application startup 60s, shutdown wait 15s, campaign command budget ≤1800s by
default (hard CLI maximum 7200s). Each command checkpoints before/after every
trial with incomplete status until all required trials finish. Incomplete/failed
trials cannot contribute an aggregate. Stop further escalation after unexpected
5xx, deadline/drain failure, unhealthy pool, SQLite failure, event corruption,
resource instability or invalid instrumentation. Do not blindly rerun a live
process just because observing output timed out.

Every successful trial verifies unique durable IDs, job count/no loss, one
claim/owner, correct exact decision-call count/no retry, capacity bound,
contiguous ordered event sequences, legal state transitions, expected terminal
states, research coverage, no evaluation mutation, SSE duplicate/missing/order/
resume counters and controlled cancellation. Queued cancellation means zero
execution; in-flight cancellation permits its one held call and no tool work.
After stopping workers, reopen the **same** database, initialize v7, run
integrity_check and verify expected rows/no active jobs. No timing threshold
is promoted into product correctness.

Resource sampling uses time.process_time CPU seconds/core equivalents,
Windows working-set samples if available, and a 20ms benchmark-only loop-lag
probe. RAM/CPU includes client/server and reused imports; it is not an isolated
production worker measurement. Missing/too-few samples are explicitly unavailable.
Benchmark logging is suppressed; structured failure counters and fixed failure
categories remain. These numbers do not include production log-volume costs.

## Reproduction and release

Use the existing interpreter from the repository root:

```powershell
.venv/Scripts/python.exe -m scripts.benchmarks.scale_002 --profile admission --concurrency 1,5,10,25,50,100 --operations 200 --trials 3 --output .local/benchmarks/scale-002/admission.json
.venv/Scripts/python.exe -m scripts.benchmarks.scale_002 --profile worker --concurrency 25 --workers 1,2,4,8 --provider-latency-ms 0,250 --operations 25 --trials 3 --output .local/benchmarks/scale-002/worker-sweep.json
```

CLI also supports --profile, --mode, --warmup, --poll-ms and bounded campaign
time. Results must stay under ignored .local/benchmarks/scale-002; temporary DBs
never touch canonical data or user workspace DB. Commit the tested harness
before the primary campaign. Bind results to that runtime SHA. Re-run affected
profiles after a harness/performance-relevant correction; documentation-only
closure does not invalidate measurements. Commit only summaries/protocol/tests,
never raw JSON, databases/WAL/SHM, traces, transcripts or private artifacts.

Functional gates: statistic/protocol/harness tests, eight small profile smokes,
SCALE-001 and Agent/provider regressions, full backend, routes/v7 and diff audit.
Final committed clean checkout must import and run the statistic tests, one
small admission and worker-backed hermetic run, offline guard, startup/stop,
same DB integrity/reopen and full clean backend without .env/data/credentials/
prior output/untracked source. Do not repeat the expensive matrix for a docs-only
commit. Finish a summarized receipt, roadmap and project journal, push the exact
validated SHA normally, verify upstream/remote, and **STOP**. SCALE-003 remains
not started; optimization is a recommendation requiring a new request.
