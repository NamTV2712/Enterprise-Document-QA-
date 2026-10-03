# FINAL-IMPROVE — current improvement round closure

Date: 2026-10-03. Branch: `main`. This is the canonical summary for the current
optional improvement round; historical receipts retain their own measurements.

## 1. Scope and closure statement

Release reconciliation and regression validation, with one reproduced reduced-motion
release blocker repaired by a single CSS selector and a strengthened browser case.
The closure also changes documentation and adds only the exact receipt path to
both existing CI filters. Completion becomes
effective only when the closing report proves both fresh workflows successful on
the final pushed SHA, normal push equality, clean tracked/staged trees and all
preservation gates. A pending, failed, cancelled or timed-out workflow blocks it.

## 2. Starting SHA and evidence populations

Starting SHA:
`35a600359d6f78a684dfd206972af78fea90760a`.
Local `main` and freshly fetched `origin/main` matched before work.
Accepted committed runtime candidate after the bounded fix:
`93ed516ff86a2588d533f1604db2646e823e8d65`.

Historical UX implementation numbers 96/843 and 540/4 were intermediate candidate
results. Accepted UX at the starting SHA has 96/844 and 542/4. This closure reran
the gates below; historical campaigns are not presented as new measurements.

## 3. Final SHA

Resolve the closure commit with:

```powershell
git log -1 --format=%H -- docs/IMPROVEMENT_FINAL_RECEIPT.md
```

The final report records its literal SHA and exact workflow IDs/conclusions.
All runtime source, tests, configuration, dependencies and lockfile blobs at the
closure commit are identical to the accepted `93ed516` candidate. Backend blobs
are also identical to the starting SHA. Exact-final clean lightweight verification
and fresh full remote release gates bind the documentation closure to that SHA.

## 4. Final architecture

Research owns the explicit Quick/Deep choice. Quick retains existing RAG,
streaming, cancellation, session memory, citations and follow-ups. Deep creates
one durable Agent run and one conversation reference/card. DATA-004 SQLite is
the Agent state/result/events/revision authority. The full inspector remains
`/agent/runs/:runId`. DATA-005 owns content-free telemetry. A single lifespan
supervisor owns fixed consumers over the durable queue; no distributed topology.

## 5. Improvement sequence and before/after

| Milestone | Delivered boundary | Final status |
| --- | --- | --- |
| CRED-001 | Primary/fallback consolidation and frozen binding compatibility | COMPLETE |
| OBS-001 | Bounded content-free attribution with explicit sampled populations | COMPLETE |
| DB-SCALE-001 | Guarded initialization and short pinned WAL snapshots | COMPLETE |
| WORKER-002 | Durable admission wake hint plus polling fallback | COMPLETE |
| CI-FIX-001 | Semantic OpenAPI contracts and deterministic frontend fixtures/focus/timing | COMPLETE |
| CAPACITY-001 | Measured bounded capacity and truthful operating policy | COMPLETE |
| UX-AGENT-001 | Unified Research, separate execution engines and safe durable references | COMPLETE |
| FINAL-IMPROVE | Cross-layer closure and exact-final release gates | COMPLETE upon section 1 publication gates |

Before, repeated initialization serialized read factories, low-load admission
waited for polling, capacity boundaries were unclear, CI contracts/fixtures could
be nondeterministic, and Chat/Agent were separate entry experiences. After,
factories reuse guarded validation, reads pin independent snapshots, queued
admission hints wake bounded consumers, defaults stay two, attribution is bounded
and content-free, semantic contract verification rejects real changes, and users
explicitly choose Quick/Deep in Research. Agent authority remains server-owned.

Historical DB-SCALE mixed event-append wait p95 was 350.401→4.180ms, with a
retained admission-tail tradeoff. WORKER-002 idle-confirmed queue p95 was
502.753→9.340ms; saturated queues and some tails remain. These are the bounded
local campaigns in their receipts, not new benchmarks or provider/SLA promises.

## 6. Credential policy

Only `GROQ_API_KEY` and optional `GROQ_API_KEY_FALL_BACK` are current credentials.
`pool` deduplicates primary then fallback for normal generation. Historical
`key5_only` remains the primary-only frozen identity. Numbered slots are not
reintroduced. Neither credential value is exposed or committed.

## 7. Provider policy

Agent decisions retain one HTTP attempt, SDK `max_retries=0`, a 60s total
deadline, no fallback rotation and no response repair/retry loop. Explicit
decision and RAG permissions are independent. Strict structured decisions never
execute tools directly; the closed registry/orchestrator owns execution. No live
Groq/SEC request or model download was required by closure validation.

## 8. Database policy

Guarded initialization binds a live canonical file/migration contract; explicit
initialize revalidates. Readers own short-lived independent connections and
multi-query reads pin WAL snapshots. Canonical writer serialization,
`BEGIN IMMEDIATE`, CAS/revision, ordered events and atomic oldest eligible claim
remain. Provider/tool work stays outside transactions. SQLite remains v7.

## 9. Worker and capacity policy

Default workers **2**, configured range **1–16**, historical benchmark samples
**1/2/4/8**, ordinary recommendation **1–2**. Fixed consumers, payload-free
coalesced admission hints, 500ms fallback poll and 5000ms shutdown grace remain.
SQLite is queue authority; lost hints/restart still discover queued work.
No per-job task explosion, production provider concurrency gate or Groq quota
certification. Larger synthetic worker counts do not justify a larger default.

## 10. Unified Research and persistence

Quick is the default and never creates an Agent run. Explicit Deep creates one
run/card and uses durable lifecycle/cancellation. No duplicated Chat final answer
or hidden Quick history/filter transfer. Research deeper fills a draft and
requires explicit submission. Reload clears the connection; reconnect reads the
same run, and 404 preserves a safe unavailable reference. Back/Forward and late
create/suspended-route ownership remain safe. The full inspector opens that ID.

Conversation record **v5**, storage envelope **v4**, IndexedDB **v2**. Legacy
Quick records, deletion/tombstones, writer restrictions and draft/reference races
remain covered. Closed reference projection excludes Agent state/result/events/
evaluation/revision/credentials from browser persistence and exports.

## 11. Security and evaluation invariants

The shared local bearer is memory-only. A fresh task-owned two-browser probe
connects, creates, saves, navigates Back/Forward, reloads, reconnects and downloads
actual JSON/Markdown exports. It checks localStorage, sessionStorage, all IDB
stores, conversation records, URL, history state, DOM and input values. No bearer
appears there, in the downloads or console/page-error logs. Exports keep the run
reference, omit the private result and never recreate a run. Post-connect and
post-export screenshots were inspected; no credential is rendered.

Existing provider/API tests prove configured primary/fallback/bearer sentinels
absent from responses, results, events, evaluation and captured logs. Status-only
frontend errors do not parse/reflect raw error bodies. Provider logging excludes
private SDK payload/header diagnostics. API-001 public/private/Host/Origin/
loopback/bearer/execution checks remain; public startup opens no private DB/pool.

OBS remains opt-in/default disabled, at most 128 API/512 worker spans, 64 groups
and 16KiB summaries, 30-day DATA-005 retention, sampled API/all successful worker
population. No goal/prompt/answer/evidence/provider body/reasoning/credential/
Authorization/SQL/hostname/user identity enters attribution. Native Agent
evaluation is provider-free with **21 unchanged metrics**, DATA-004 terminal
result authority, explicit unavailable/not-applicable and no overall score.

## 12. CI and release invariants

Both full existing workflows are required on the final SHA. Only four filter
entries add `docs/IMPROVEMENT_FINAL_RECEIPT.md` to push/PR paths. Jobs, runners,
timeouts, tests, budgets, retry and skip behavior are unchanged. Local browser
gates use one worker and zero retries. Existing CI retry configuration is not
used to excuse a failed/unstable result. OpenAPI omitted versus explicit
`additionalProperties=true` is normalized; real semantic changes still fail.
Prior cancellation, late-event, fixture ownership, focus restoration, stable
Markdown, warm-navigation and delayed-readiness negative regressions remain.

## 13. Exact local test commands, checkouts and results

Primary backend and the first focused gates ran at starting
`35a600359d6f78a684dfd206972af78fea90760a`; backend source/test/configuration blobs
are identical in the accepted candidate. Clean accepted backend, frontend,
browser/harness/security gates below ran at committed source-clean candidate
`93ed516ff86a2588d533f1604db2646e823e8d65`.
`P` = `D:\Project\Enterprise_Document_QA`.
`C` = `D:\Project\Enterprise_Document_QA\.local\final-improve\clean`.
`A` = `P\.local\final-improve\audit` (ignored task-owned evidence).
`P-Python` = `P\.venv\Scripts\python.exe`.
`C-Python` = `P\.local\ci-fix-001\requirements-env\Scripts\python.exe`.
Backend runs set `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`; clean runs set
`PYTHONPATH=C`. Primary and clean full backends ran serially.

| Checkout | Exact command | Actual result | Evidence under A |
| --- | --- | --- | --- |
| P | `P-Python -m pytest tests/ -q` | 1958 passed, 188 warnings, 0 failed; 204.71s | `backend-primary.log` |
| C | `C-Python -m pytest tests/ -q` | 1924 passed, 34 expected artifact skips, 149 warnings, 0 failed; 94.40s | `backend-clean-accepted.log` |
| C/frontend | `bun install --frozen-lockfile` | PASS; unchanged frozen dependencies/lockfile | `frontend-install-accepted.log` |
| C/frontend | `bun run lint` | TypeScript PASS | `frontend-typescript-accepted.log` |
| C/frontend | `bun run test` | 96 files / 844 tests PASS; 12.95s | `frontend-unit-accepted.log` |
| C/frontend | `bun run build` | PASS; main chunk 527.24 kB, warning retained | `frontend-build-accepted.log` |
| C/frontend | `bun e2e/token-contrast.mjs` | all declared pairs PASS | `frontend-contrast-accepted.log` |
| P and C | respective Python `-m compileall -q src scripts configs` | PASS | `compile-primary.log`, `compile-accepted.log` |
| P and C | respective Python `A/contracts.py` | import/public worker gate, routes, fresh/reopen integrity and worker range PASS | `contracts-primary.log`, `contracts-accepted.log` |

Focused backend command 1 (P-Python, P, `-q`) named these exact test files:
`tests/test_db_scale_concurrency.py tests/test_db_scale_benchmark.py
tests/test_db_scale_agent_sse.py tests/test_capacity_001.py
tests/test_credential_consolidation.py tests/test_agent_provider.py
tests/test_agent_provider_api.py tests/test_agent_evaluation.py
tests/test_performance_attribution.py tests/test_performance_integration.py
tests/test_api_router_contracts.py tests/test_workspace_access.py
tests/test_terminal_telemetry.py tests/test_terminal_telemetry_api.py
tests/test_workspace_worker.py`: **362 passed / 1 inherited warning**
(`backend-focused.log`). Command 2: `P-Python -m pytest
tests/test_worker_wake.py tests/test_worker_scheduler_benchmark.py
tests/test_agent_worker.py -q`: **43 passed / 1 inherited warning**
(`worker-focused.log`). These cover the existing DB/worker/capacity/OBS/CRED/
provider/evaluation/API invariants without rerunning historic campaigns.

Focused frontend: `bun run test
src/components/conversation/useConversationAgent.test.tsx
src/hooks/useConversationLibrary.test.tsx src/lib/conversationStore.test.ts
src/lib/conversationStore.snapshot.test.ts src/lib/assistantExecution.test.ts
src/lib/conversationExport.test.ts src/lib/localWorkspaceSession.test.tsx
src/lib/agentApi.test.ts src/components/ui/SelectField.test.tsx src/App.test.tsx`:
**10 files / 135 tests PASS** (`frontend-focused.log`).

Environment: Windows, Python 3.12.7, SQLite 3.45.3, clean Pydantic 2.10.0,
FastAPI 0.115.0, Groq 1.5.0; primary Pydantic 2.13.4; Bun 1.3.14,
Node 24.19.0. Declared backend environment `pip check` passes. Different inherited
warning populations are disclosed rather than merged. Clean source has no `.env`,
private data or credentials; every harness database is temporary.

## 14. Exact browser results

The starting-SHA full matrix failed: **541 passed / 4 inherited skips / 1 failed**,
20.6m (`browser-full.log`). Chromium Models Axe measured blended low-contrast
colors during `console-fade-up`. Global reduced-motion duration shortening still
left 50/100/150ms entrance delays; console children were missing from the existing
animation-disable rule. Three unchanged isolated passes are diagnostic, not a
release gate. A strengthened existing UI-009 case fails deterministically before
the fix with `animation-name=console-fade-up` instead of `none` (`registry-before.log`).

Commit `93ed516ff86a2588d533f1604db2646e823e8d65` adds only that child selector to
the reduced-motion rule. Normal motion retains its animation. The same existing
case now checks route readiness, no animation and opacity 1 before the unchanged
Axe scan. All **14 Models/Datasets Chromium/Firefox cases pass**, 28.1s
(`registry-after.log`), including Axe and viewport overflow. Production screenshots
were inspected. The full renewed suite below covers all nine shared console
consumers. No timeout, test retry, skip, contrast threshold or performance budget
was relaxed. This is a reproduced reduced-motion contract/release defect, not a
palette or layout redesign.

When advancing the task-owned checkout, Git first refused the two copied source
changes. Their normalized content was verified against the fix commit, only those
two files were staged there, and detached checkout advanced safely. Commands that
started before that transition (`*-candidate.log`) are diagnostic only; accepted
gates (`*-accepted.log`) started at the committed candidate.

From C/frontend: `bunx playwright test --workers=1 --output=A/browser-accepted-results`
(with A expanded to its absolute path): **542 passed / 4 inherited skips / 0 failed, 16.3m**
(`browser-accepted.log`). Committed inventory is 546 cases in Chromium/Firefox.
Four inherited skips are the two real-backend-only performance cases per engine,
not removed product tests. The suite includes the 22 UX cases and focused Quick,
Deep/cancel/reconnect, Research deeper, citation, inspector and navigation journeys,
EN/VI/light/dark, keyboard, narrow shells, Axe/overflow and unchanged performance
budgets. Screenshots are real production-build output, retained only under A or
the ignored clean checkout. No historical untracked spec is discovered.

Accepted Chromium synthetic warm composer input p95 **14.10ms** stays below the
unchanged 100ms budget; warm view switch p95 **63.30ms** stays below 200ms
(`browser-accepted.log`, 40 input / 30 navigation observations). These are local
frontend checks, not production load/SLA or provider quota measurements.
Firefox uses the same populations/budgets: input p95 **29.00ms**, warm view
switch p95 **42.00ms**, both PASS. Scope-editor timing, simultaneous typing
over a 60-second stream, and real provider/network timings remain unverified
in this synthetic frontend baseline; existing lifecycle tests are separate.

Extra security command: `bunx playwright test -c A/security.config.ts`, run from
C/frontend with the absolute config path and `--output=A/security-accepted-results`:
**2 passed / 0 failed, 14.1s**, zero retries (`security-accepted.log`). An initial task-owned config launch failed before any
test because its webServer cwd resolved to A; the corrected probe explicitly uses
C/frontend. This was a diagnostic configuration issue, with no product/test gate
weakened and no passing result claimed for the first launch.

## 15. Exact HTTP/SSE and Agent harness results

From C/frontend, `HARNESS_PYTHON=C-Python`, `PYTHONPATH=C`, offline flags enabled:

| Exact command (A expanded) | Actual result | Evidence under A |
| --- | --- | --- |
| `bunx playwright test -c playwright.integration.config.ts --output=A/http-accepted-results` | 16 passed / 0 failed, 26.0s | `http-accepted.log` |
| `bunx playwright test -c playwright.agent-sweep.config.ts --output=A/agent-sweep-accepted-results` | 32 passed / 0 failed, 1.1m | `agent-sweep-accepted.log` |
| `bunx playwright test -c playwright.agent-product.config.ts --output=A/agent-product-accepted-results` | 12 passed / 0 failed, 48.0s | `agent-product-accepted.log` |

These exercise real local HTTP/SSE fragmentation/abort/late events, event ordering,
numeric Last-Event-ID/run binding, public/local authority, terminal evaluation,
durable cancellation and no ambiguous replay, with deterministic provider fixtures.

## 16. Routes and SQLite

Fresh runtime probes: **90 method/path pairs, 80 distinct paths**, SQLite
**v7 / WAL / synchronous=1 (NORMAL) / busy_timeout=5000ms / integrity_check=ok**
on fresh creation and reopen. Imports start no worker. Public execution-enabled
startup still starts no private worker/database. Real public/local product
lifespans and semantic OpenAPI contracts pass their full-suite/harness gates.

## 17. Dependencies, lockfiles and migrations

One frontend motion selector and five assertions/readiness lines repair the
reproduced reduced-motion defect. No backend source/test, dependency, package/
lockfile, endpoint, migration, schema index, worker/default/budget or provider/
retrieval/model/planner change. ARCHITECTURE
already describes the current owners/policies correctly and is unchanged. README
only reconciles current Research/persistence/status and the retained bundle warning.

## 18. Known limitations

- Main bundle warning about 527.24 kB; inherited backend dependency/parser warnings.
- Native zoom 125/150/200 remains manual/unverified.
- Collections/model-test ordinary browser bearer wiring remains staged.
- Ragas remains optional; no overall native Agent quality score.
- Single-process WorkerSupervisor; no distributed workers or production SLA.
- No live Groq reachability/quota certification or global Generator capacity guarantee.
- Generic Deep goal does not imply hidden structured multi-objective planning.
- Agent reload needs server authority and explicit reconnection.

## 19. Deferred future work

SCALE-003 is **DEFERRED / NOT STARTED**, not an automatic next task. Deployment,
distributed scaling, production capacity/SLA and optional research decisions
remain separately authorized backlog. No further current-round feature is started.

## 20. Git, preservation and artifact audit

Before: tracked/staged clean, exactly 12 historical unrelated untracked paths.
Task-start SHA-256 baseline contains **3958 files**, including `.env` and the
current accepted three diagnostic PNGs. Final verification requires all 3958
unchanged, zero additions/deletions/differences within those roots, and the same
12 untracked paths. Historical worktrees, data and `.env` remain untouched.
All new diagnostics stay ignored under `.local/final-improve/`.

The separate fix commits only the two frontend files. The closure commits only
this receipt, PROJECT_STATE, SCALING_ROADMAP, bounded README corrections and four
CI filter entries. Diff/staged/secret/artifact audits and
`git diff --check` are required. No credentials, `.env`, database/WAL/SHM,
benchmark JSON/CSV, screenshots, trace/video/build output, provider payload or raw
error body enters Git. Fresh fetch precedes normal `git push origin main`;
unexpected upstream movement blocks push. Final report proves local HEAD =
upstream = remote main, ahead/behind **0/0**, tracked/staged clean.

## 21. Exact GitHub workflow run IDs

Historical accepted UX at the starting SHA: Backend **37079190129** completed/
success; Frontend **37079190138** was in progress at task start and ultimately
completed/success (updated 2026-10-03T00:10:12Z). Its prior UX-specific waiver is
historical and does not replace either FINAL-IMPROVE gate. CAPACITY final
`f607d2a56073555269fb619218678b5715ea8517` Backend **36892326330** is success.

The closing report records the literal final SHA, fresh exact-SHA Backend and
Frontend run IDs, terminal `completed/success` conclusions and normal push
equality. This avoids changing the receipt after CI and triggering a self-hash
documentation loop. Older successful runs or Vercel cannot satisfy the gate.

## 22. Current improvement round

**COMPLETE when the final publication evidence in sections 1/20/21 is satisfied.**
CRED-001, OBS-001, DB-SCALE-001, WORKER-002, CI-FIX-001, CAPACITY-001 and
UX-AGENT-001 are COMPLETE. FINAL-IMPROVE closes the round after both fresh
exact-final-SHA CI successes. No further task from the current improvement round
remains after that closure. **STOP.**
