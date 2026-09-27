# Engineering audit and bounded repairs — 2026-09-27

## Outcome and recovered state

Four reproduced defects were repaired: one P1 public-metadata disclosure and
three bounded P2 migration/request/streaming races. No P0 was verified in the
inspected scenarios. This is a boundary-oriented audit, not proof that every
source line, deployment, dependency, or security threat is safe.

Start: `codex/bilingual-research-workspace` at `cbfdfda`, 60 ahead / 0 behind the
locally recorded origin ref, without fetching. The pasted UI-008/API-006-next
snapshot is historical. Current source and receipts establish API-006, UI-009,
Pipeline, native Evaluation, UI-011 and DATA-005 as completed. The September 26
audit and its four fixes are existing work, not new achievements here.

The starting tree had 19 tracked dirty entries, 21 untracked entries and no
staging. It includes in-progress UI-012 implementation and 12 older unrelated
untracked paths. Neither group is disposable. This pass does not finish, stage,
or commit that UI-012 feature work.

## Architecture and invariant coverage

AGENTS, current/latest checkpoint and project-state sections, master graph,
README, architecture, frontend contract/design, reference gap matrix, relevant
source and tests were reconciled. Historical results were not treated as new
verification. Core/security/UI skills kept repairs at existing owners; native
evaluation and provenance contracts were checked without quality promotion.

| Boundary | Evidence and authority |
| --- | --- |
| API/access/deployment | FastAPI composition and routers; local mode, direct loopback, exact Host/Origin, bearer, separate execution capability. Forwarded headers affect only explicitly trusted rate-limit identity. Docker disables proxy headers; local Qdrant remains single-worker. Public denial precedes workspace access. |
| Persistence | One workspace SQLite database; per-path write lock, transactions, revisions, conflicts and tombstones. Browser conversation storage is separately owned, not an automatic SQLite-failure fallback. Initialization had the race repaired below. |
| Transfer/Collections | Bounded JSON, canonical digest, stable import mapping, transaction/idempotent receipt, tombstone admission and atomic parent/member/note activity. Collection client still does not attach the local bearer: documented staged architecture, not permission to bypass access. |
| Catalog/readers | Document/chunk/source/representation identities and revisions; local reader admission, conservative exact/stale/ambiguous states; SEC browser URLs require the fixed HTTPS archive host. Derived PDF is not official pagination or a substitute evidence identity. |
| Search/retrieval/generation | Bounded provider-free discovery snapshots and immutable paging; separate inspection stage/score/null semantics; request/citation/answer ownership. No ranking, model, prompt, context, evidence renderer or canonical index change. |
| Registries/Pipeline/Evaluation | Configured/observed/unknown facts, staged durable jobs, revision cancellation and ordered events; frozen evaluation bindings, durable attempt reservation, terminal interrupted recovery, publication distinct from execution. No provider or evaluation campaign ran. |
| Telemetry | Content-free terminal records, canonical job projections, independent severity/outcome, bounded SQL cursor reads, 30-day telemetry/seven-day logs, best-effort source writes. No conventional process-log ingestion or fake cost/quality/resource metrics. |
| Frontend/tests | Canonical routing and app identity; hooks own read/stream lifetimes; browser storage/backup/writer recovery stay with existing owners. Hermetic pytest guard, Vitest fixtures, production Playwright and independent CI gates. Working-tree UI-012 was preserved, not silently incorporated into these commits. |

Required routers, workspace helpers and frontend routes are now tracked. A
static HEAD import audit inspected 129 committed Python files and found zero
missing tracked `src`/`configs` import targets. Import succeeded with 83 unique
API method/path routes. This addresses the historical missing-module claim;
it does not certify a fresh dependency installation or clean-checkout build.
TODO/FIXME/XXX and high-risk sinks were candidate signals, not automatic bugs.

## Verified bugs and repair plan

| ID/severity | Symptom, proof and root cause | Smallest safe repair / protection |
| --- | --- | --- |
| AUD-08 / P1, public metadata | Public `/system/info` returned synthetic Windows/POSIX local cache paths verbatim. Fourteen adversarial regressions failed; safe metadata passed. Fields were key-allowlisted, but runtime model names and build environment values were not value-filtered. No actual credential disclosure was asserted. | Reuse registry's bounded public identifier projection. Preserve safe IDs/response shape; unsafe models are null, unsafe build entries omitted. Fifteen privacy tests plus registry/legacy/OpenAPI checks. |
| AUD-05 / P2, persistence | Two instances captured the same pending receipts; one initialized, the other raised `WorkspaceMigrationError`. Fresh/upgrade tests both failed. Each migration transaction was locked, not the full check-and-apply sequence. Single-process normal startup mitigates exposure, but concurrent initialization was not idempotent. | Hold the existing shared reentrant lock across initialization. Two concurrent fresh/upgrade tests preserve canonical checksums and successful outcomes; existing rollback/corruption/revision tests remain intact. |
| AUD-06 / P2, Search | Late old page success restored the old query; old page error painted an expired banner on the new search; paging could start during submission. Three unit regressions failed. New search aborted the page but did not invalidate its request epoch, and old controls remained active. | Invalidate page epoch on submit; reject aborted completion/error; suspend page/page-size actions during new search. Preserve one POST per search and GET-only paging. Three units and four paired theme/locale browser cases. |
| AUD-07 / P2, streaming | Stop lost the latest token while it was still buffered for the scheduled render. New unit failed. The stop path read rendered message text instead of the current owning buffer; App cleanup then ignored already-stopped messages. | Capture/clear buffer before abort, preserve only matching message's text, keep stopped state. One unit protects owning/unrelated/completed messages and abort; App and paired streaming neighbors pass. |

The issues are independent. Commit order prioritizes the disclosure boundary,
then persistence and the two frontend lifetime repairs. No redesign, fallback
writer, auth weakening, dependency change or roadmap implementation was needed.

## Commits

- `762bda6` — `fix(api): filter private values from public system metadata`:
  system router and new privacy tests.
- `da2a2a5` — `fix(data): serialize workspace initialization across instances`:
  database owner and persistence regressions.
- `fbf433b` — `fix(ui): isolate search paging from newer submissions`:
  Search component, unit tests and existing browser spec.
- `ec0ef58` — `fix(ui): preserve buffered answer tokens when stopping`:
  research-session hook and unit test.

Documentation closure is separate; its hash belongs in git history/the final
handoff, not a self-referential field in this document.

## Tests actually run

Commands ran at repository root unless marked frontend.

| Command/gate | Actual result |
| --- | --- |
| `.venv\Scripts\python.exe -m pytest tests -q --tb=short` before fixes | 1217 passed / 0 failed / 188 warnings |
| Same full backend after migration repair | 1219 passed / 0 failed / 188 warnings |
| Same full backend after all repairs | 1234 passed / 0 failed / 188 warnings, 82.81s |
| Focus: persistence, transfer/domain/API, jobs, telemetry/domain/API, access | 151 passed / one existing warning |
| Focus: system privacy, registries, router/OpenAPI, legacy API | 103 passed / five existing warnings |
| Final persistence-only gate | 34 passed |
| Frontend `bun run test` before audit fixes | 85 files / 684 tests passed |
| Frontend final `bun run test` | 85 files / 688 tests passed, no failures |
| Frontend focus: Search, research-session, App | 48 passed |
| Frontend `bun run lint` | Passed (`tsc --noEmit`; no separate ESLint script) |
| Frontend `bun run build` and Playwright production builds | Passed; existing >500 kB bundle warning remains |
| Frontend `bunx playwright test e2e/ui-006-search.spec.ts e2e/app.spec.ts --grep 'UI-006 discovery search\|asked question streams\|stream that ends\|next draft stays' --workers=1` | Final **30 passed**, 15 Chromium + 15 Firefox, 53.4s |
| Compile/import, route collisions, working/staged diff checks | Passed; 83 routes, no collisions |

Before production edits: two new migration tests failed; three Search and one
Stop regression failed; fourteen unsafe-metadata cases failed while the safe
case passed. No assertions/timeouts were weakened or failures deleted.

An initial 24-case Search browser run passed behavior but screenshot review
caught a wrong theme storage key in the new fixture. A follow-up run exposed
four test-only failures from asserting a nonexistent `data-theme` attribute;
the actual app uses the `dark` class. The fixture now uses the existing `theme`
key and asserts the actual class. Final 30-case execution passed without product
CSS changes or hiding failures. Production screenshots were inspected at
1586x992 dark/EN and 390x844 light/VI; the existing Search suite covers additional
1440/1280/1024/short-wide views, keyboard/contrast, snapshot reuse and readers.
Screenshots remain ignored. Native browser zoom was not verified.

The full frontend counts include existing uncommitted UI-012 tests. They certify
the tested worktree, not a claim that UI-012 was committed or a HEAD-only build.

## Remaining issues, safety and next action

- P3 Unicode snippets remain confirmed: `Straße revenue` returns `[8,15]` and
  highlights `evenue`. Casefold expansion and Python code-point/JS UTF-16 mapping
  need an explicit shared contract. Ranked evidence and stored content are not
  corrupted; defer this bounded display repair after the higher-priority work.
- Collections bearer integration remains an explicitly staged feature. Extend
  the memory-only owner and private client allowlist in its own authorized task;
  never persist/embed a token or weaken the backend boundary.
- Migration lock is in-process. Concurrent multi-process upgrades are not
  certified; current local serving/recovery assumes one process.
- Existing heading-order/documentation cleanup, bundle warning and backend
  dependency/parser warnings remain separate follow-ups, not new regressions.
- No exhaustive penetration/dependency scan, Docker rebuild, clean installation,
  full browser/reference suite, alternate proxy deployment, native zoom, live
  SEC/provider call or official benchmark was performed. Identifier projection
  is a bounded allowlist, not universal credential detection.

All pre-existing tracked/untracked work is retained. Final status returns to the
same 19 dirty tracked entries and 21 untracked entries, with no staging; audit
changes alone are committed. Only authored docs and explicit code/test paths
were staged. No database/WAL/SHM, secrets, canonical data, provider outputs,
screenshots, bundles, caches, `.audit-runtime`, `.mimosa` or harness dumps were
committed. Mixed README/checkpoint files were staged by audit-only additions.

API-006 is complete and must not restart. Next: resume the existing UI-012
validation/documentation/closure in its own scope, then the graph's TEST-002
and TEST-003 gates. No feature task was begun during this audit.
