# SCALE-001 durable background execution receipt

Status: **COMPLETE** — implementation and verification. The exact final
committed HEAD, its final clean-checkout gate and normal upstream push are
reported in the final chat release receipt. Branch:
`codex/bilingual-research-workspace`. Starting HEAD:
`b13fff6affc919a19f13bda3ddc730c319a705c2`. Implementation commit:
`a2002a3fc426a59a2e2b1a506483104fc6c98c19`
(`feat(scale): add bounded durable background workers`). The browser-only
revision-boundary correction is `769be884bff86a4a9090ef3aff8caa558810b727`
(`test(scale): synchronize cancellation with claimed revision`).

This optional milestone preserves completed required, AGENT-001–006, UI-014,
TEST-005 and PROVIDER-001 work. SCALE-002 and SCALE-003 remain not started.

## Execution ownership and architecture

Previously Agent POST attached `service.run` to a response BackgroundTasks
object. DATA-004 revision CAS prevented duplicate ownership, but response tasks
had no global capacity bound and startup did not consume queued Agent work.
Now POST only admits/freeze/persists the queued run, returning 201 and its
revision ETag. Execution outlives the request/client. One application-lifespan
WorkerSupervisor owns N fixed asyncio consumers, with one active execution per
consumer and no per-queued-row task. Defaults are N=2, poll=500ms, grace=5000ms.
Configuration bounds: N=1–16, poll=100–5000ms, grace=100–60000ms. Start requires
local workspace mode, workspace execution enabled and worker enabled. Public
startup opens no workspace database; importing modules starts no tasks. Tests
opt into workers explicitly. Empty/failed claims wait on a shutdown-aware event.

The explicit closed ExecutorRegistry registers exactly
`agent / bounded_agent_run` in production. Persisted strings never import code.
AgentJobExecutor resolves current runtime configuration after successful claim
and hands the claimed snapshot to AgentDurableService.execute_claimed. That
service uses the existing bounded AgentOrchestrator, tool registry, strict
production decision adapter, research authority and terminal result writer.
There is no second decision loop or worker-owned Agent business logic. The
legacy CAS-based service.run remains an internal compatibility/test entry;
production HTTP does not schedule it.

DATA-004 SQLite remains the sole job/state/event authority. Each claim selects
one oldest eligible queued row by created_at ASC then job_id ASC in a single
BEGIN IMMEDIATE transaction, then uses the existing revisioned transition/event
implementation. Selection and queued→running/event commit succeed or roll back
together. Synchronized independent repository contenders produce one owner,
one running event and revision 2. Existing jobs_listing_idx supports indexed
reverse traversal; EXPLAIN shows SEARCH, not a table scan. No schema/index or
migration change is needed. No provider/tool work runs inside a claim transaction.

With capacity 2, both 4-row and 80-row barriers measured exactly two active
executors and two persistent worker tasks. Remaining payloads stay durable;
the pool does not preload a queue or create one execution task per row. Claim
helper tasks exist only for bounded in-progress SQLite operations. Synchronous
admitted tool adapters run through asyncio.to_thread and are awaited per owner;
a blocked catalog leaves HTTP responsive. This bounds durable execution owners,
not a global provider/thread resource quota.

## Cancellation, shutdown, restart and crash windows

Queued cancellation commits cancelled before ownership, producing zero provider
or tool calls. Running cancellation records cancelling and remains cooperative;
stale revisions return 409. An in-flight call is not falsely reported instantly
cancelled. After its boundary, cancellation prevents additional work and commits
the existing terminal semantics. SSE sequence/cursor/resume and native evaluation
still read DATA-004 events/results; finite SSE closure does not imply completion.

Shutdown sets the stop signal before waiting: no subsequent claim is dispatched.
Owners finishing during grace retain their terminal result; never-claimed queued
work stays queued. At expiry, pending async execution is cancelled and unresolved
owned running/cancelling work is reconciled to interrupted, never cancelled or
requeued. Pending SQLite claim operations are shielded until completion and any
newly committed ownership is reconciled; a cancelled await cannot abandon a
thread that might later commit. Bounded SQLite busy operations/reconciliation
can extend cleanup beyond the configured execution grace. Pool tasks are gathered
and application state removed; provider SDK contexts and VectorStore close.

Startup drains existing interrupted recovery before creating consumers. Queued
never-claimed Agent work executes; previously running/cancelling work becomes
interrupted. Tests cover process-loss windows after claim/before the first call
and after a real mocked external effect/before terminal commit. Neither window
replays the ambiguous run. Ordinary executor exceptions are sanitized, reconcile
the active row and leave the pool able to execute the next queued job. Unexpected
worker death stops claims, logs a fixed content-free error and reports unhealthy;
it does not silently respawn or replay. Optional worker_ready is a safe boolean
in the existing health payload; readiness refuses an unhealthy started pool.

Async cancellation cannot hard-kill an already-running Python thread or prove
remote effects stopped. External execution is uncertain after a lost response or
crash. There is no exactly-once external-effect, lease, retry/requeue, distributed
worker, SLA or load-benchmark claim.

## Other namespaces and security

| Namespace | Worker decision | Preserved behavior |
| --- | --- | --- |
| Agent | Eligible exact bounded_agent_run pair | Existing orchestration/provider/research authority |
| Pipeline | Excluded | Staging only, pending steps; no ingestion execution |
| Evaluation | Deliberately excluded | Existing EVAL-003 response-attached synchronous executor; frozen case/attempt/report receipts |
| model_test | Excluded | Provider-free synchronous identity checks, no durable production execution |
| Unknown job type | Excluded | Cannot resolve or execute through the registry |

Evaluation migration would widen its synchronous external-effect and shutdown
receipt contract, so it is outside this milestone. A real staged Pipeline and
Evaluation job remain untouched by the Agent pool. The existing Evaluation
executor subsequently succeeds with exactly two reserved attempts, one generation
and one judging call, preserving its frozen contract.

Local bearer/origin/host/workspace access checks remain before admission. Worker
execution preserves the submitted policy, frozen provider binding, per-run
explicit decision-provider grant and separate RAG-tool grant. All four grant
combinations are covered; denied paths have zero unauthorized transport/tools.
Changed/missing/unsupported runtime binding never silently upgrades a frozen run.
Actual AsyncGroq plus httpx.MockTransport proves search→read→final with current-run
canonical document/chunk references and research objective completion. Native
Agent v1 evaluation remains provider-free with 21 metrics. No credential/client
is serialized into queue payloads, results/events/logs/evaluation/browser storage.
Safe failure codes/messages are fixed; raw exception/provider bodies are omitted.

## API/UI, SQLite and dependencies

Product method/path pairs remain **90**; no route is added or removed. The private
create endpoint remains 201/ETag with a truthful queued snapshot. Production
frontend source/layout/types are unchanged. New browser tests/config and a
test-only offline HTTP-control harness exercise real production pool, API,
SQLite, Agent, SDK adapter and UI. Control endpoints never enter the product app.
Queued, running, cancelling and terminal states, results, events/resume and
21-metric evaluation are visible without refresh. Running/completed screenshots
were inspected; focused Axe/overflow checks passed.

Fresh initialize/reopen returns **v7/v7**. Schema migration receipts are the
version authority; an initial ad hoc diagnostic mistakenly read unused
PRAGMA user_version=0 and was corrected without changing database code.
No runtime/package dependency, requirements or lockfile changed. Clean frontend
installation uses Bun 1.3.14 and bun install --frozen-lockfile (284 packages).
External existing Python 3.12.7 runs clean-checkout backend tests against that
checkout's source, without copying .env, data, corpus, credentials or local DBs.

## Tests actually run

| Gate | Result |
| --- | --- |
| New supervisor/store/registry suite | 28 passed |
| New Agent-worker suite | 23 passed |
| Combined final new tests | 51 passed / 1 inherited dependency warning |
| Shared focused campaign before last four new cases | 486 passed / 1 warning; final full includes all additions |
| Final primary full backend | 1730 passed / 0 failed / 188 warnings |
| Implementation clean full backend | 1696 passed / 34 artifact-dependent skips / 148 warnings |
| Primary frontend | 94 files / 818 tests passed |
| Clean frontend, isolated rerun | 94 files / 818 tests passed |
| Primary + clean TypeScript | PASS |
| Primary + clean production build | PASS, 2079 modules; main chunk 508.63 kB warning |
| SCALE-001 browser, primary + corrected committed clean | 8/8 Chromium + Firefox in each final campaign |
| PROVIDER-001 browser regression | 20/20 Chromium + Firefox, EN/VI, dark/light, phone/desktop |
| Existing TEST-005 browser regression | 12/12 Chromium + Firefox |
| Default browser discovery | 570 tests / 32 files; SCALE-001 excluded |
| Routes, primary + clean | 90 unique product method/path pairs |
| SQLite fresh/reopen, primary + clean | v7/v7 |
| Import/startup gate | No import-time pool; public opens no workspace DB; explicit local gate covered |
| Git diff --check | PASS |

The 28-case suite includes ten configuration-bound cases, exact registry,
stable ordered/indexed claim, synchronized two-repository claim, atomic rollback,
idle/repeated start-stop/task cleanup, two capacity/backpressure cases, single
invocation, queued/stale cancellation, shutdown before claim, grace success,
grace expiry, executor exception, nonterminal return, exclusions, restart,
unexpected worker death and transient claim-error recovery.

The 23-case Agent suite covers request/client-independent creation and single
provider owner, four permission combinations, real SDK mocked-HTTP research/final,
cancel after claim/before admission, queued cancel, runtime binding drift,
blocked-SDK shutdown/resource cleanup, two process-loss windows, five startup
gates, pending SQLite-claim shutdown, lifespan restart, actual Pipeline/Evaluation
exclusion and blocking synchronous-tool responsiveness/cancellation. Events,
resume and provider-free evaluation are asserted within these journeys.

Full backend passes also include these unchanged/module-level counts (subsets,
not additional runs to add to the total): Agent tools 19, orchestration 25,
research 21, security 73, durability 16, API 5, native evaluation 29 = **188**
AGENT-001–006 cases; production provider 88 + provider API 8 = **96**;
DATA-004 jobs 27; workspace persistence 34/access 29; Pipeline staging 17;
Evaluation jobs 23 + CORS 6. All passed in the primary full run.

A first clean SCALE browser run passed 7/8: Firefox clicked cancellation after
claim (revision 2) but before the UI received execution-step revision 3. The API
correctly refused 409 and the UI reloaded with a conflict notice. The test now
waits for the blocked provider boundary's authoritative revision to reach the UI;
there is no refresh, retry, product change or weakened cancellation assertion.
The browser-only test commit records this correction; the committed clean
rerun passed **8/8** in Chromium/Firefox with zero focused Axe/overflow violations.

Initial test/harness failures are retained as evidence: three new fixture errors
(explicit ask_rag allowlist/dataclass serialization), one browser ambiguous
locator, Firefox reserved-port refusal (4190→4191), and TEST-005 launched with
system Python missing slowapi (select existing .venv interpreter). No assertions,
security settings or dependencies were weakened. One clean frontend run under
concurrent backend/build load timed out an existing App history test (817 pass,
1 timeout at 5000ms); the unmodified isolated full rerun passed all 818, including
the same case in 1997ms. No unresolved final failure remains.

## Baseline → final

| Measure | Starting baseline | Final verified |
| --- | --- | --- |
| Primary backend | 1679 / 188 warnings | 1730 / 188 warnings |
| Clean backend | 1645 / 34 skips / 148 warnings | 1696 / 34 skips / 148 warnings |
| Product routes | 90 | 90 |
| SQLite | v7 | v7 |
| Frontend | 94 files / 818 tests | 94 files / 818 tests |

## File scope and audit

Created **10**, modified **14**, deleted **0** across the milestone:

Created:

- docs/SCALING_ROADMAP.md
- docs/SCALE_001_FINAL_RECEIPT.md
- src/workspace/executors.py
- src/workspace/worker.py
- tests/test_workspace_worker.py
- tests/test_agent_worker.py
- tests/worker_helpers.py
- tests/integration/scale_product_server.py
- frontend/playwright.scale.config.ts
- frontend/e2e/scale-001.spec.ts

Modified:

- .env.example
- configs/settings.py
- src/workspace/jobs.py
- src/agent/durable.py
- src/agent/registry.py
- src/api/app.py
- src/api/routers/agent_runs.py
- src/api/routers/health.py
- tests/test_agent_api.py
- tests/test_agent_provider_api.py
- frontend/playwright.config.ts
- README.md
- ARCHITECTURE.md
- PROJECT_STATE.md

The same 12 unrelated untracked paths remain untouched: .audit-runtime/,
.mimosa/, .zcodeignore, PROJECT_CONTEXT.md, frontend/.audit-runtime/,
frontend/.mimosa/, frontend/e2e/capture-ui-round.mjs, probe-box.mjs,
probe-contrast.mjs, v5-1-visual-capture.spec.ts, harness_stacks.txt, screenshots/.
They are excluded from commits. Staged intended-file credential comparison
against configured .env values found zero matches; forbidden generated-artifact
scan found zero. No .env, data, SQLite/WAL/SHM, logs, screenshots, traces,
dependencies, builds or unrelated files are committed. No production debug route
is added. Managed verification worktrees are archived after their final gate.

## Limitations and next action

Collections/model-test browser bearer limitations, manual native zoom,
optional Ragas and the inherited >500 kB build warning remain. The prior optional
live-provider smoke timed out; SCALE-001 uses hermetic SDK transport and makes no
new live-provider availability claim. Workers are process-local; local Qdrant
serving still requires one API worker. No distributed coordination or throughput/
latency/SLA guarantee is established. In-flight effects may finish after async
cancellation; ambiguous work becomes interrupted and is never automatically replayed.

README and ARCHITECTURE document effective settings, ownership and limitations;
PROJECT_STATE and the separate scaling roadmap close SCALE-001. The final
release receipt provides the full documentation commit SHA, final committed clean
verification, normal git push command/result, matching HEAD/upstream/remote and
0/0 ahead-behind. **STOP.** The next optional action is SCALE-002 load/concurrency/
SLA benchmark design only after an explicit new request; it is not implemented.
