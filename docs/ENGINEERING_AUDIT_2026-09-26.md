# Post-rebuild engineering audit — 2026-09-26

## Outcome and recovered state

Four verified correctness/integration defects were repaired in three scoped
commits. No verified P0 was found. The checked boundaries and regression gates
are healthy enough to return to the planned UI-011 task; this is not a claim
that every source line, dependency, deployment, or security threat was audited.

The starting checkout was `codex/bilingual-research-workspace` at `8dfdb3f`,
52 commits ahead / 0 behind its locally recorded origin ref (no fetch/push).
Tracked and staged diffs were empty. Twelve unrelated untracked paths remained.
The supplied recovery's `1858924`, API-006-next, and 136-entry dirty tree were
historical. Current source, tracked module inventory, recent commits, and the
latest checkpoint establish completion through EVAL-003 and UI-011 next.
The historical clean-checkout blocker was already addressed by the recorded
source-closure commits; required routers, workspace helpers, frontend app routes,
and evaluation modules are tracked now. No separate checkout/build was performed
here, so this pass does not renew that earlier clean-build receipt.

## Architecture and invariant coverage

This was a boundary-oriented source/test audit, not an exhaustive file summary.
AGENTS, README, architecture, master task graph, reference gap matrix, frontend
contracts/design, and current/latest journal and checkpoint records informed it.
Older journal receipts were treated as history, not newly measured results.
The core/security/UI/evaluation skills kept fixes at their existing owners.

| Boundary | Current owner and inspected contract |
| --- | --- |
| Application/access | `src/api/app.py` composes lifecycle, CORS, routers and shared pipeline state; `access.py` requires local mode, loopback peer, exact Host-port/Origin, bearer, and separate execution capability. Public-mode workspace denial happens before repository access. Forwarded headers do not participate in application authorization. |
| Deployment | Independent Vite frontend/FastAPI backend; Docker excludes frontend, installs CPU PyTorch, and disables Uvicorn proxy headers. Local Qdrant and local job recovery assume one process. A different server/proxy configuration was not penetration-tested. |
| Persistence | Workspace database owns SQLite lifecycle/migrations/serialized transactional writes; repositories own revision CAS and tombstones. Browser conversation storage remains a separate authority, not an automatic SQLite failure fallback. |
| Transfer/collections | JSON-only bounded validation, canonical Python/TypeScript digest fixtures, stable imported identities, rollback and idempotent receipts; parent/member/note writes and activity are atomic. Tombstones prevent resurrection. Local collections routes stay protected. |
| Corpus/readers | Catalog/document/chunk and source/representation identities feed readers; PDF/structured/normalized are representations, not substitute evidence identities. SEC browser URL sanitizer admits the fixed HTTPS archive host, not user paths. Source/reader regressions are included in the full backend suite. |
| Search | Provider-free lexical discovery owns bounded snapshots, immutable paging, TTL and bounded candidate counts. Search is distinct from generation and diagnostic retrieval. Unicode display ranges have the remaining issue below. |
| Retrieval/generation | Inspection reports separate score families, nullable values and skipped/not-executed stages; display changes do not rerun it. Serving retrieval/generation and submitted evidence stay outside this repair. No ranking, model, prompt or index semantics changed. |
| Registries/Pipeline | API-006 reports configured/observed/unknown facts, not fake availability. DATA-004 owns jobs/revisions/events/cancellation/recovery. API-007 stages queued isolated records without executing canonical ingestion or promotion. |
| Evaluation | Native protocol/definitions/bindings own metric semantics and denominators. Public publications/analytics are separate from private frozen jobs. Attempt reservation is durable before transport; restart marks ambiguous running work interrupted, not resumed. No report publication or official promotion occurred. |
| Frontend | `App.tsx` and canonical routes coordinate selected identity; hooks own stream/reader lifetimes; page epochs reject stale reads. The memory-only app session explicitly authenticates private Pipeline only. Collections paging stays in its existing component and one current API page. |
| Tests | Hermetic pytest socket guard; Vitest browser-state fixtures; production-build Playwright localhost fixtures; CI has independent backend/frontend gates. Tests and fixture assumptions were checked before updating contracts. |

TODO/FIXME/XXX and high-risk input/transaction/path/request code were inspected
as candidate evidence, not automatically promoted into defects. No source
finding justified dependency upgrades, mass formatting, architecture replacement,
canonical regeneration, or changing measured retrieval decisions.

## Verified issues and prioritized repair plan

| ID | Severity | Evidence/root cause | Smallest solution and regression risk |
| --- | --- | --- | --- |
| AUD-04 | P1, API/browser integration | `/evaluation/jobs` requires `Idempotency-Key`, but CORS omitted it. Hermetic approved-origin preflight returned 400. | Add exactly that header; six tests check success plus forbidden origin/method/header and unauthorized creation without DB access. Small middleware blast radius; no auth weakening. |
| AUD-01 | P1, publication identity | Duplicate validated legacy/native IDs yielded 409 for list/detail but 200 for native results/compare/failures/trends. Selected reader/history bypassed collision validation. Four new tests reproduced it. | Apply a shared ambiguity rejection at selected read/history admission, before filtering. Keep the public reader and report protocols unchanged. Risk: ambiguous histories now correctly fail closed. |
| AUD-02 | P2, API contract | Native list output used `complete`, but the list status selector accepted only legacy literals and `incomplete`; valid query returned 422. | Add `complete`, preserve legacy promotion meanings, reject invented selectors. Explicitly assert/normalize that one OpenAPI addition before the original digest comparison. Low additive compatibility risk. |
| AUD-03 | P2, Collections navigation | "Show more" replaced, rather than appended, an API page; no Previous control existed; button eligibility compared a page length with the full total. Favorites overwrote its active total with all-collection totals. | Keep one page, add bounded Previous/Next, separate active/all counts and reconcile a page beyond a shrinking set. Preserve selection/epochs/revisions/persistence. Two unit and four paired-browser regressions cover no writes and filtered/terminal navigation. |

Execution order put independent CORS/access repair first in the commit series,
then tightly coupled evaluation reader/selector repair, then Collections. None
depends on implementing UI-011 or adding a global authentication transport.
All candidates had focused failing regressions before their production change.
Intermediate test-fixture mistakes were corrected against existing contracts,
not by changing production behavior or hiding deterministic failures.

## Fixes and commits

- `7a3e596` — `fix(api): admit evaluation idempotency preflights`:
  `src/api/app.py`, `tests/test_evaluation_jobs_cors.py`.
- `05f87ce` — `fix(eval): reject ambiguous publications across analytics`:
  `src/api/routers/evaluations.py`, `tests/test_native_evaluation_analytics_api.py`,
  `tests/test_api_router_contracts.py`. Includes the missing native completeness
  filter as one tightly coupled public-evaluation contract repair.
- `d1519a3` — `fix(ui): bound collection paging to the active result count`:
  `frontend/src/components/collections/CollectionsWorkspace.tsx`, its unit test,
  and `frontend/e2e/ui-008-collections.spec.ts`.

The documentation closure separately updates README, PROJECT_STATE, checkpoint,
the frontend paging contract, and this authored report. Its hash is in the final task handoff/git history;
no self-referential commit hash is inserted into its own contents.

## Validation actually run

Commands below ran from the repository root unless the frontend directory is
specified. Counts are this session's results, not inherited baselines.

| Gate/command | Actual result |
| --- | --- |
| `.venv\Scripts\python.exe -m pytest tests -q --tb=short` before changes | 1168 passed, zero failures, 188 warnings |
| Same full backend command after final code changes | **1179 passed, zero failures, 188 warnings**, 95.01s |
| Focused `test_native_evaluation_analytics_api.py test_native_evaluation_analysis.py test_public_report.py test_native_metric_api.py test_api_router_contracts.py` | 41 passed, one existing warning |
| Focused `test_evaluation_jobs_cors.py test_evaluation_jobs.py test_collections_cors.py test_workspace_access.py` | 63 passed, one existing warning |
| `bun run test src/components/collections/CollectionsWorkspace.test.tsx` in `frontend` | 25 passed |
| Final `bun run test` in `frontend` | **80 files / 541 tests passed**, zero failures |
| `bun run lint` in `frontend` | Passed (`tsc --noEmit`); there is no separate ESLint gate in this package |
| Production build through Playwright webServer (`bun run build`) | Passed; existing >500 kB bundle warning remains |
| `bunx playwright test e2e/ui-008-collections.spec.ts --grep 'bounded collection pagination' --workers=1` | 4 passed: desktop dark/EN and mobile light/VI in Chromium and Firefox |
| `bunx playwright test e2e/ui-008-collections.spec.ts --grep-invert 'receipts\|zoom' --workers=2` | **38 passed**, 19 per browser; existing neighboring route, reader, mutation, conflict, tombstone, unavailable, export, keyboard and responsive flows |
| `.venv\Scripts\python.exe -m compileall -q src tests` | Passed |
| App import and APIRoute method/path inventory | Passed; 80 routes, no collisions |
| Working/staged `git diff --check` | Passed before each commit |

Before the evaluation fix the new analytics group had five expected failures
(four unexpected 200s, one unexpected 422). Corrected CORS reproductions had
three unexpected 400s. Before the Collections change its two new unit cases
failed on missing backwards navigation and the incorrect Favorites "Show more".

The initial full frontend run had **538 pass / 1 fail**, a 5-second timeout in
`App request cancellation > session history can switch between conversation and
overview`. Focused execution passed in 689 ms; final full execution passed in
1871 ms without timeout changes. This supports a load-sensitive classification,
not a silent assertion change or a claim that the first run passed.

Initial new browser failures were investigated: the new test used an incorrect
locale storage key, then scanned during entry animation. Using existing
`sec_qa_locale`, reduced motion and the existing settled-paint gate produced
green paired WCAG-tagged scans without changing CSS or existing assertions.
A separate best-practice heading-order warning is recorded below. Real 1440x900
dark/EN and 390x844 light/VI screenshots were inspected: paging controls are
reachable, bounds truthful, and no body/root horizontal overflow. Keyboard
return and browser fixture request logs prove read-only navigation. The UI skill
kept one-page state ownership and existing design/persistence boundaries.

Not rerun: full browser/reference receipts, all theme/locale/width combinations,
native browser chrome zoom, Docker, clean-checkout installation/build, live SEC,
models/providers, or the official benchmark. Screenshot/axe evidence is not a
claim of whole-product WCAG conformance or security assurance.

## Remaining findings and intentional limitations

- **P3 / Unicode snippet highlighting:** a read-only domain reproduction of
  `build_snippet('Straße revenue', ('revenue',))` returned `[8,15]` and highlighted
  `evenue`. Casefold expands `ß` before computing original-text offsets; separate
  Python code-point/JavaScript UTF-16 indexing also lacks an explicit mapping.
  Fix separately with shared Unicode fixtures and an explicit offset contract.
  This is a display defect; ranked/selected evidence identity and stored text
  were not corrupted. It was lower priority than access/identity/paging.
- **P3 / card heading order:** an unfiltered Axe best-practice scan found
  `h1` followed by `.collection-card__title` `h3`. Existing heading markup was
  unchanged. Follow up with a page-level semantic heading review; WCAG-tagged
  scans of the settled affected journey passed.
- **Staged architecture / Collections authorization:** the normal collection
  client does not attach the private bearer. UI-010's explicit contract scopes
  token attachment to Pipeline; connecting there does not authorize Collections.
  The page truthfully reports unavailable/unauthorized. A separate feature must
  extend the memory-only connection owner to an explicitly allowlisted private
  client and define browser-vs-SQLite authority; never embed/persist credentials
  or add a global bearer to public calls. No security bypass was introduced.
- **Intentional execution boundaries:** staging is not ingestion execution or
  promotion; private evaluation completion is not public publication; interrupted
  attempts are not silently replayed; provider weight revision/global quota
  coordination/exactly-once external calls are not guaranteed.
- **P3 / historical documentation:** planning-era headers and older architecture
  prose still describe historical states. Current checkpoint/project-state
  records and task dependencies supersede them. No historical receipts rewritten.

No measured performance regression justified optimization. This audit is not a
dependency vulnerability scan, exhaustive SSRF/prompt-injection review, or proof
against alternate reverse-proxy/server configuration. No P0 was verified in the
inspected/tested scenarios.

## Dirty tree, data integrity, and next action

Before: zero tracked changes, zero staged changes, 12 unrelated untracked paths.
After the code commits: the same original 12 paths and clean tracked source.
Final documentation closure is followed by another status/diff audit.

Preserved: `.audit-runtime/`, `.mimosa/`, `.zcodeignore`, `PROJECT_CONTEXT.md`,
`frontend/.audit-runtime/`, `frontend/.mimosa/`, the four ad-hoc frontend e2e
diagnostic/capture files, `harness_stacks.txt`, and `screenshots/`.
Only explicitly named task-owned files were staged. No reset, clean, restore,
stash, mass add, canonical regeneration, secret dump, or external push was used.
Browser/pytest generated results remained ignored. No runtime DB/WAL/SHM, data
artifact, provider output, scanner state, cache, screenshot, or dependency change
was committed. All network/model behavior remained hermetic/provider-free.

**Next:** UI-011 — Evaluation under a separate feature request. API-006 is already
complete and must not be restarted. No new hygiene blocker was reproduced.
The remaining P3 items and staged auth extension belong to separately bounded
work; they do not require weakening the verified private boundary.
