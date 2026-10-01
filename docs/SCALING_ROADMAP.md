# Scaling roadmap

This is a separate optional roadmap. Required product, Agent and PROVIDER-001
milestones remain complete. Starting HEAD: `b13fff6affc919a19f13bda3ddc730c319a705c2`.

| Task | Scope | Status |
| --- | --- | --- |
| SCALE-001 | Bounded background workers / durable Agent execution | COMPLETE |
| SCALE-002 | Load, concurrency and capacity characterization | COMPLETE |
| OBS-001 | Content-free performance attribution and fixed hermetic measurements | Implementation validated; campaign/release pending |
| SCALE-003 | Evidence-backed caching and resource optimization | Not started |

## SCALE-001-A: ownership audit and contract

At the starting HEAD, Agent POST queued then attached `service.run` to Starlette's response
background tasks. Each request can create another execution; DATA-004 CAS
prevents duplicate claims, but no global pool bounds task creation. Queued
Agent work has no startup consumer. Evaluation similarly attaches its existing
synchronous, provider-backed case executor to the response; its per-case attempt
reservations/report commits are a separate EVAL-003 contract. Pipeline staging
never executes ingestion. Model tests synchronously read runtime identities
without inference and do not create durable jobs.

SCALE-001 consumes only `agent / bounded_agent_run`. Evaluation stays on its
existing EVAL-003 executor: moving synchronous external effects would widen the
shutdown/case-receipt contract. The new worker must never claim evaluation,
pipeline, model_test or an unknown job type. No dynamic imports or second Agent
loop. One closed executor registry dispatches into AgentDurableService and the
unchanged bounded AgentOrchestrator.

DATA-004 remains the only durable authority. Claim oldest eligible work by
`created_at ASC, job_id ASC` in one serialized BEGIN IMMEDIATE transaction,
reusing the revisioned state transition and event authority. Existing
`jobs_listing_idx(namespace,state,created_at DESC,job_id DESC)` supports reverse
index traversal; no migration/index is needed. Claim releases the transaction
before executor/provider work. Terminal states never requeue.

One lifespan-owned asyncio pool starts only in local mode with workspace
execution enabled and workers enabled. Conservative defaults: two workers,
500ms polling, five-second shutdown grace; hard bounds enforced. Public startup
does not open SQLite. Import starts no worker. Tests explicitly start the pool.
Fixed worker tasks consume one job each; durable queued rows provide backpressure
without one task per queued row. Empty/error polls wait on a shutdown-aware event.

Queued cancellation is immediately terminal. Running cancellation remains
cooperative through the existing durable cancellation signal. Shutdown stops
new claims, allows bounded grace, then cancels owned async execution and marks
unresolved owned work interrupted. In-flight external effects are uncertain;
this is not forced provider cancellation or exactly-once external execution.
SQLite operations retain the existing bounded busy timeout/write discipline.
Queued never-claimed work remains eligible after restart. Claimed running or
cancelling work is interrupted at startup; no automatic replay, even if a crash
occurred before the first call or after an effect but before result commit.

## Verification checkpoints

- A: audit, eligibility, claim/index, startup/shutdown/restart, test plan.
- B: supervisor/registry/store claim; deterministic race, idle and capacity tests.
- C: Agent dispatch, execution-time binding, permission matrix, cancellation.
- D: request-independent API/SSE and built worker-backed browser journey;
  Pipeline/Evaluation/model-test exclusions.
- E: bounded task/backpressure and full shared/Agent/provider regressions.
- F: full suites, routes/v7, final committed clean checkout, secret/artifact audit,
  exact normal upstream push, COMPLETE and STOP.

Use events/barriers for races and blocked executors. Do not run primary and
clean full backend suites concurrently: the existing HTTP fixtures probe the
same starting ports. Live provider smoke is not retried. No SLA/load claim,
distributed worker, broker, lease or automatic retry is part of SCALE-001.

## B/C checkpoint

Store claim reuses DATA-004's transaction-local transition implementation.
The explicit registry and supervisor are in `src/workspace/executors.py` and
`worker.py`. Agent POST no longer attaches a response background task. A
lifespan-owned pool resolves provider/runtime configuration after claim and
calls `execute_claimed` on the existing Agent coordinator. Synchronous tool
adapters are awaited through bounded per-owner thread offloading, so corpus
discovery does not monopolize the event loop. A cancelled async await cannot
forcibly terminate an already-running Python thread/provider effect; shutdown
marks the uncommitted run interrupted and discards late output.

Initial worker/Agent-worker gates: 47 passed / one inherited dependency warning.
Tests include synchronized transaction claims, capacity two with 4/80 queued
rows, fixed task count, idle wait, shutdown grace/expiry, pending-claim shutdown,
API response/client completion while provider is blocked, four permission
combinations, production SDK mocked-HTTP search/read/final, execution-time
binding drift, cancellation races, and actual process-loss windows before call
and after effect/before commit. Three initial test-fixture errors were corrected:
the permission fixture needed an explicit ask_rag allowlist, and the native
report uses dataclass serialization. No production assertion was weakened.

UI acceptance keeps `/agent` entry, memory-only connection and existing create
form. DATA-004 owns selected-run state; existing epochs/SSE cursor own reads;
existing sections own scrolling. Verify visible queued, running, cancelling and
terminal states without refresh. Review risks: stale terminal paint, treating
finite SSE closure as completion, hidden queued cancellation, implicit provider
consent, and secret persistence. No production frontend layout/type changes
are planned; a dedicated real pool/API/SDK/SQLite browser harness owns barriers.

## D/E checkpoint

The final primary backend passed **1730 tests / 188 warnings**; the new tests
passed **51/51** (28 supervisor/store/registry and 23 Agent-worker tests).
The shared focused campaign passed 486 before the last four added cases; the
full final run includes those cases. No live provider retry was performed.
Frontend unit tests remain **94 files / 818 tests**, TypeScript and production
build pass. The main chunk warning is inherited (508.63 kB in this build).

The worker-backed product campaign passed **8/8 Chromium/Firefox** with zero
focused Axe violations and overflow; running/completed screenshots were
inspected. Existing PROVIDER-001 browser regression passed **20/20**, covering
EN/VI, light/dark, phone/desktop, unavailable and unsupported provider paths.
Initial SCALE browser failures were an ambiguous locator and Firefox refusing
reserved port 4190; exact text matching and preview port 4191 resolved the
harness errors. Browser security settings and product behavior were unchanged.
The default browser discovery is 570 tests / 32 files and excludes SCALE-001.
Routes remain **90**; fresh/reopened SQLite remains **v7**; import starts no pool.
Existing TEST-005 browser regression passed **12/12**. Its first launch used
the system Python and failed before tests (missing slowapi); selecting the
existing project interpreter resolved the harness setup without dependencies.

## F: completion and release boundary

Implementation commit: `a2002a3fc426a59a2e2b1a506483104fc6c98c19`.
Browser revision synchronization: `769be884bff86a4a9090ef3aff8caa558810b727`.
The committed source-clean backend passed **1696 / 34 skips / 148 warnings**;
clean frontend **94 files / 818 tests**, TypeScript and build passed. The first
concurrent frontend run timed out one existing case; isolated full rerun passed.
Routes remain **90**, initialize/reopen returns **v7/v7**, imports start no pool.
The first clean browser campaign exposed a stale-revision 409 between claim and
step start. The UI correctly reloaded; the test now awaits the held provider's
revision in the UI before requesting cancellation. The corrected committed
clean campaign passed **8/8** in Chromium/Firefox with zero focused Axe/overflow
violations. No product change/retry.

[SCALE-001 receipt](SCALE_001_FINAL_RECEIPT.md) records complete implementation,
verification, file inventory and limitations. The final chat release receipt
records the exact documentation HEAD, its final committed clean gate and normal
upstream push verification. Required/product/Agent/provider milestones stay
complete. At the SCALE-001 release, SCALE-002 and SCALE-003 were not started.

## SCALE-002 A-F: completed characterization

Runtime `23702743ee6e3e807dad4004c68ff77cb6006bef` owns the committed
[protocol](SCALE_002_BENCHMARK_PROTOCOL.md), deterministic loopback CLI and 49
harness tests. The [receipt](SCALE_002_FINAL_RECEIPT.md) records 52 distinct
scenarios/156 complete trials: 153 hermetic plus 3 separate artifact trials.
Admission/read 100, default-worker full runs 50, comparative workers 1/2/4/8,
SSE 50, mixed 5/25/50, cancellation and controlled failure all passed bounded
correctness. An interrupted two-trial worker point stayed incomplete/excluded;
its full three-trial point was rerun. No development or partial timing is pooled.

Admission/read plateau around 60 requests/sec; worker=2 moderate throughput near
3.1 worker / 2.2 research jobs/sec, queue tails rise with outstanding demand.
Eight workers help injected waits; instant local throughput does not consistently
scale. Mixed 50 reaches queue p95 43.64s with substantial Python lock waiting,
shorter transaction time and zero SQLite busy/errors. All 498 subscribers pass
order/resume/terminal checks; all DBs reopen v7/integrity/no active rows.
This is measured development capacity, no production SLA or maximum-user claim.

Final harness 49, focused 196, primary backend 1779/188 warnings and committed
source-clean 1745/34 artifact skips/148 warnings passed. Routes 90/schema 7/default
2/500ms/5000ms preserved. Frontend 94/818/TS/build inherited unchanged; no production
source/config/dependency/lockfile/migration/frontend change. Final documentation
HEAD, its final committed clean CLI/full suite and exact normal push verification
are recorded in final chat. No live provider or optimization was implemented.

Proposed next scope: OBS-001, attribution of Agent API/stream/serialized-access
cost under the retained hermetic fixtures, before choosing caching or a DB change.
Required/Agent/provider/SCALE-001/002 COMPLETE. **SCALE-003 NOT STARTED. STOP.**
