# Current Planning Status

Checkpoint 09, TEST-001, API-001, DATA-001, UI-001, UI-002, API-002, DATA-002 and UI-003: COMPLETE. UI-003's A-F receipts are below. The next dependency-ready task per the master-plan priority ordering is API-003 (not started).

## Last Completed Checkpoint

UI-003-F — Chat/Research conversation pages and hooks. UI-003 is COMPLETE
(sub-checkpoints A through F). Exact next action: API-003 (requires explicit
user authorization to begin).

TEST-001 remains complete. Its pre-existing failures are frozen below so later tasks can distinguish them from regressions.

Checkpoint 09 persisted the complete master plan, standalone Appendix A and checkpoint and validated coverage, dependencies, API consistency and change scope.

Checkpoints 01–08 were completed in the prior planning conversation. Their repository/reference analysis and architecture, product, backend, evaluation, testing and task-graph decisions are preserved in the master plan. They were not restarted or repeated during this checkpoint.

## Completed Work

- Reconstructed the completed specification into master-plan sections 1–22 and its full implementation graph.
- Extracted complete Appendix A into the standalone nine-reference gap matrix.
- Preserved architecture, APIs, persistence/migration, Stitch, native/Ragas/TruLens, testing, visual-validation and risk decisions.
- Recorded the existing dirty tree before document writes: 71 tracked modified files plus pre-existing untracked work. No existing work was reverted.
- Ran the existing hermetic backend, frontend, production-build, standard browser, local HTTP/SSE and integration HTTP/SSE checks for TEST-001.
- Recorded exact commands, results, existing failure signatures and the unchanged source-tree boundary below.

## Remaining Work

TEST-001 has no remaining work. At its completion, rebuild implementation had not started and API-001 required a separate instruction. Its frozen results below remain the compatibility baseline.

## Important Decisions Already Made

- Single-user local-first workspace; public server workspace read-only, browser-local saving retained.
- Protect private reads/writes with explicit local capabilities; no browser-bundled secrets.
- Preserve evidence/revision/variant identity, existing readers, cancellation, bilingual behavior and browser migration compatibility.
- Distinguish discovery Search from diagnostic Retrieval and production structured promotion.
- SQLite with explicit migrations, one authoritative repository, backup/preview/idempotent import and retained originals.
- Pipeline stages isolated; required table enrichment; no automatic canonical promotion.
- Native evaluation authoritative; exact frozen context/bindings and budget accounting; optional isolated Ragas later; TruLens deferred.
- No fabricated accounts, sharing, model switching, quotas, metrics, pipeline history or published reports.
- Reuse Stitch project 3773610233677432915 with 12 exports; local nine screenshots authoritative.

## Files Inspected

Inherited planning evidence includes AGENTS.md, PROJECT_STATE.md, README.md, ARCHITECTURE.md, TODO.md, docs/frontend/DESIGN.md, docs/frontend/FRONTEND_CONTRACT.md, major frontend composition/controllers/storage/readers, backend API/document/inspection/evaluation boundaries, scripts/manifests and existing tests. This was a boundary audit, not a line-by-line inspection of every source file. PROJECT_HANDOFF.md was absent.

Checkpoint 09 only checked target-file existence and repository status/diff, then wrote and validated the three planning files. It did not restart the audit or re-inspect screenshots. Earlier production-build reference tests passed 15/15 Chromium; that historical result is not a test of future implementation. Earlier ignored artifacts under frontend/test-results/rebuild-plan-audit/ were not regenerated here.

## Reference Images Inspected

All nine were individually inspected during completed planning:

1. rag-workbench-master-reference-dark.png — Chat, 1254 × 856.
2. research-ui-reference-dark-v1.png — Research, 1586 × 992.
3. documents-ui-reference-dark-v1.png — Documents, 1586 × 992.
4. search-ui-reference-dark-v1.png — Search, 1586 × 992.
5. retrieval-ui-reference-dark-v1.png — Retrieval, 1586 × 992.
6. collections-ui-reference-dark-v1.png — Collections, 1586 × 992.
7. models-ui-reference-dark-v1.png — Models, 1586 × 992.
8. pipeline-ui-reference-dark-v1.png — Pipeline, 1586 × 992.
9. evaluation-ui-reference-dark-v1.png — Evaluation, 1586 × 992.

## Backend Gaps Found

Persistent conversations/typed collections/imports; catalog facets/statistics; discovery snapshots/count scope; additive trace metadata; model/dataset registries; durable staged jobs; private evaluation execution and comparable public-report aggregates; terminal content-free telemetry; bounded sanitized logs; protected allowlisted settings. These gaps are mapped to proposed API contracts and implementation tasks in the master plan.

## Frontend Decisions

Keep React/Vite/TypeScript/Tailwind/Lucide/Bun and proven domain logic. Introduce router/query-cache boundaries, shared primitives, thin routed pages, legacy-link adapter and responsive shell. Preserve stream/epoch ownership outside server-state caching. Recompose existing reader engines. Validate all nine native layouts plus responsive widths, themes, locales, states and zoom.

## Backend Decisions

Incrementally extract routers/services with compatible wire contracts. Built-in SQLite, no ORM/Redis/queue service. Keep ranking/prompts/chunk IDs/index/official benchmark unchanged. Separate protected private jobs from public validated reports. No optional evaluation dependencies in serving requirements. Preserve independent deployment, CPU-only Docker PyTorch and local-Qdrant single-worker behavior.

## Open Questions

No unresolved planning/product decision blocked persistence of Checkpoint 09. At Checkpoint 09 completion, implementation had not started; API-001 and DATA-001 are now the completed rebuild implementation tasks.

## TEST-001 Compatibility Baseline

Status: COMPLETE WITH DOCUMENTED PRE-EXISTING FAILURES. The baseline is suitable for regression comparison because no production or test source was changed during TEST-001. A future task must preserve every passing gate and must not increase the known failure set.

Runtime used: Python 3.12.7, pytest 9.0.3 and Bun 1.3.14. Ordinary pytest used the repository default marker expression `not live_network`. Browser fixtures allowed localhost only. No SEC, Hugging Face, Groq, Qdrant Cloud or other live provider was invoked.

| Command | Exact result |
| --- | --- |
| `.venv\Scripts\python.exe -m pytest -q` | PASS — 793 passed, 0 failed, 188 warnings in 94.54s. Covers API, retrieval, ingestion helpers, document/PDF identity and compatibility. |
| `bun run lint` in `frontend` | PASS — `tsc --noEmit`, 0 TypeScript errors. |
| `bun run test` in `frontend` | PASS — 63 files, 324 tests, 0 failed in 23.74s. Expected DOMException stderr is emitted by storage failure/recovery cases that pass. |
| `bun run build` in `frontend` | PASS — Vite production build, 2,017 modules transformed, completed in 7.04s. |
| `bunx playwright test --project=chromium --workers=1 --retries=0` in `frontend` | PASS — 115 passed, 2 intentionally skipped, 0 failed in 3.6m. |
| `bunx playwright test --project=firefox --workers=1 --retries=0` in `frontend` | BASELINE FAILURE — 114 passed, 2 intentionally skipped, 1 failed in 4.6m. Failure: `evidence inspector uses the remaining-width mode and closes without losing citation identity`; the second 1024px reopen did not expose the dialog within 10s. |
| `bunx playwright test e2e/regression.spec.ts --project=firefox --workers=1 --retries=0 --grep "evidence inspector uses the remaining-width mode and closes without losing citation identity"` in `frontend` | PASS — focused rerun 1/1 in 7.6s (test body 2.3s), classifying the full-suite result as an existing timing-sensitive failure. The original failure remains part of the baseline. |
| `bun run test:e2e-local -- --workers=1 --retries=0` in `frontend` | PASS — 6/6 in 19.0s across Chromium and Firefox. Covers real local HTTP stage events, exact reader identity, readiness and unknown-chunk non-substitution using the provider-free harness. |
| `bun run test:e2e-integration -- --workers=1 --retries=0` in `frontend` | Baseline run discovered 16 tests. The first two Chromium cases each timed out at 60s; the run was stopped to avoid repeating the same timeout cascade. Remaining cases and Firefox counterparts were then completed with the two commands below. |
| `bun run test:e2e-integration -- --workers=1 --retries=0 --grep-invert "health readiness and ticker discovery\|retrieval lab receives"` in `frontend` | BASELINE FAILURE/PASS — 10 passed and 2 failed in 2.4m. The cited-answer case passed transport/source rendering but timed out looking for the obsolete `Open source 1` control in both browsers. |
| `bun run test:e2e-integration -- --project=integration-firefox --workers=1 --retries=0 --grep "health readiness and ticker discovery\|retrieval lab receives"` in `frontend` | BASELINE FAILURE — 2/2 failed at 60s. Together with the first run this completes the 16-case matrix: 10 passed, 6 failed (5 passed/3 failed per browser). |
| `git diff --check` | PASS — exit 0 and no whitespace errors; Git emitted only existing LF-to-CRLF conversion warnings. |

Pre-existing integration failures, identical by browser:

1. Health/scope: the Company control exists, but the current workbench subtree intercepts the click after the scope surface opens; timeout at `integration.spec.ts:65`.
2. Retrieval navigation: the test expects `Open navigation|Expand navigation` while the current expanded navigation is already present; timeout at `integration.spec.ts:72`.
3. Cited-answer handoff: answer, source list and excerpt render, but the test then expects the old `Open source 1` answer control; timeout at `integration.spec.ts:91`. This mismatch was already documented in the repository before TEST-001.

The standard Firefox inspector failure is timing-sensitive because its unchanged focused rerun passed. None of these is a rebuild regression: they occurred before API-001/UI-001 and TEST-001 changed no implementation or test code. Do not silently treat them as green; future work must either preserve the recorded count or resolve them in an explicitly scoped task.

Baseline task semantics: entry is the existing Research and tool routes; intent is question-to-cited-answer, source/evidence inspection, exact reader handoff, durable local storage and provider-free retrieval. Submitted scope and selected evidence remain distinct. Existing controllers own requests/epochs/cancellation; IndexedDB/localStorage schema v4 owns browser persistence; answer/source/document/hash/revision/variant tuples own identity; notifications remain operation-scoped; app/pane/reader/overlay scroll ownership is covered by the passing standard browser suite. Recovery coverage includes interrupted streams, expired sessions, failed storage, tombstones, stale/unknown sources and fallback readers.

## Exact Next Action

UI-001 — implement the planned tokens/fonts/primitives foundation. This is only the recorded next task; it has not started. Do not begin UI-002, DATA-002, DATA-003, DATA-004 or API-002 as part of DATA-001.

## Files Created or Modified

Created by this step:

- docs/UI_REBUILD_MASTER_PLAN.md
- docs/UI_REFERENCE_GAP_MATRIX.md
- docs/UI_REBUILD_PLAN_CHECKPOINT.md

No pre-existing file was modified by this step. No source, package manifest, lockfile, requirements, application configuration, dependency installation or data/ change was made. Git status and diffs were inspected; the three files above are new, untracked planning documents. The 71 pre-existing tracked modifications and all pre-existing untracked work were preserved.

TEST-001 source-controlled documentation change:

- `docs/UI_REBUILD_PLAN_CHECKPOINT.md` — updated with this baseline receipt.

No production application, test source, package manifest, lockfile, requirements file, configuration or `data/` file was changed by TEST-001. Test execution refreshed ignored build/test output under `frontend/dist/`, `frontend/dist-integration/`, `frontend/dist-local/`, `frontend/test-results/` and `frontend/e2e/screenshots/`. The existing PDF browser test also refreshed these pre-existing untracked diagnostic files:

- `frontend/.audit-runtime/pdf-viewer-1440x900.png`
- `frontend/.audit-runtime/pdf-viewer-1920x1080.png`
- `frontend/.audit-runtime/pdf-viewer-720x900.png`

The existing V5.1 capture test refreshed eight external diagnostic screenshots under `C:/Users/Nam/.gemini/antigravity/brain/0db42795-fbb7-4e1c-9754-1905253a84df/screenshots/`: `live_workbench_final.png`, `workbench-1440x900-four-pane.png`, `workbench-1440x900-dark.png`, `workbench-1920x1080-dark.png`, `workbench-1280x856-dark.png`, `workbench-1440x900-light.png`, `workbench-1024x768-tablet.png` and `workbench-390x844-mobile.png`. These are generated diagnostic outputs from the pre-existing test definitions, not source changes.

## Validation Receipt

- All three requested documents exist and are UTF-8 readable.
- Master plan has sections 1–22 in order and the complete 33-task graph.
- All nine reference filenames appear in all three documents; every screen has detailed matrix rows. Appendix A contains 81 feature rows, including shared chrome.
- Every task dependency resolves to a defined task; the dependency graph is acyclic. Optional Ragas remains conditional.
- All 56 proposed API method/path pairs are unique. Table fields are complete; public/local/execution access boundaries, protected event streams and published/private evaluation separation are consistent with the contract rules. This is specification validation, not endpoint implementation testing.
- Git no-index diffs for each new document were inspected; whitespace checks passed. No files were staged or committed.
- Combined SHA-256 fingerprint of the existing tracked/untracked file paths and contents, excluding these three new documents, is unchanged: 822cbecf6bd6561294e6b4b33730e5c44229e38bccd66c64f341175bb13129d9.
- TEST-001, API-001 and DATA-001 are complete. No UI-001, DATA-002, DATA-003, DATA-004, API-002 or later implementation has started.

## API-001 Quota-Safe Progress

### Active Task

API-001 — local workspace capability/access boundary. Status: COMPLETE.

### Last Completed Sub-checkpoint

API-001-D — compatibility/regression tests passed, final Git review completed and the API-001 gate recorded.

### Completed Work

- Confirmed default deployment is public and current public query, reader, retrieval, health and evaluation routes have no workspace authentication dependency.
- Pre-implementation inspection confirmed CORS used an exact configured origin list and excluded the Authorization request header.
- Confirmed trusted forwarding headers affect rate-limit identity only. API-001 local access now uses `request.client.host` directly and does not call that proxy resolver.
- Selected a fail-closed dependency boundary with three explicit capabilities: public/provider-free, protected local workspace, and execution/jobs.
- Selected strict bearer parsing plus constant-time comparison, loopback socket-peer enforcement, exact local Host/Origin checks, and a redacted protected configuration-status response.
- Kept private write/execution verification in focused dependency tests until DATA-001 creates real private mutations/jobs.
- Added public-by-default settings, secret-typed dedicated token configuration, local Origin/Host allowlists and a separately disabled execution flag.
- Added explicit public/provider-free, protected local workspace and execution/job dependencies. Private access uses the socket peer directly, exact Host/Origin matching and constant-time bearer comparison.
- Added protected `GET /system/configuration-status` with allowlisted capability flags only.
- Allowed the Authorization header through existing exact-origin CORS so an authorized local browser can call private routes; other CORS behavior remains unchanged.
- Documented safe environment defaults without placing any secret in a `VITE_*` variable.
- Added focused hermetic access-matrix tests for public access, private reads/writes, bearer failures/success, direct-loopback enforcement, forwarding-header spoofing, exact Origin/Host behavior, secret redaction and disabled execution.
- Re-ran the focused matrix after removing its regex-literal warning, then passed the combined workspace/API/trusted-proxy suite.
- Preserved the TEST-001 public CORS origin/method defaults while adding only the `Authorization` request header needed by the local bearer boundary.
- Hid all Pydantic settings input values in validation-error text so workspace and provider credentials cannot leak through startup exceptions.
- Passed the full hermetic backend suite with the TEST-001 warning count unchanged and no regression.
- Updated the public setup/status documentation and living project journal for the completed API-001 milestone.
- Reviewed the complete dirty working tree and API-001 diffs, ran whitespace validation and confirmed no frontend credential configuration was added.

### Remaining Work

API-001 has no remaining work. DATA-001, its next dependency-graph task, is now complete.

### Files Modified

- `.env.example` — documented explicit public/local mode, dedicated secret, exact local allowlists and disabled execution.
- `configs/settings.py` — added validated fail-closed workspace settings.
- `src/api/access.py` — added capability grants and local/execution access dependencies.
- `src/api/app.py` — wired the public capability marker, protected configuration status and required CORS Authorization allowance.
- `tests/test_api.py` — updated the existing exact CORS expectations required by bearer authentication.
- `tests/test_workspace_access.py` — added the focused hermetic access matrix and redaction/configuration validation.
- `README.md` — documented the protected status route and safe local-workspace environment contract.
- `PROJECT_STATE.md` — recorded the completed API-001 milestone and validation receipt.
- `docs/UI_REBUILD_PLAN_CHECKPOINT.md` — corrected stale task state and persisted API-001-A/B/C/D.

No package manifest, lockfile, requirements file, frontend source, data artifact, corpus, index, dependency or unrelated production route was changed by API-001. The pre-existing dirty worktree was preserved.

### Tests Already Run and Exact Results

- `.venv\Scripts\python.exe -m compileall -q configs/settings.py src/api/access.py src/api/app.py` — PASS (exit 0).
- `.venv\Scripts\python.exe -m pytest -q tests/test_workspace_access.py` — PASS: 27 passed, 0 failed in 5.96s; one API-001 test regex warning was then corrected. One unrelated ReportLab deprecation warning remained.
- `.venv\Scripts\python.exe -m pytest -q tests/test_workspace_access.py tests/test_api.py tests/test_trusted_proxy.py` — PASS: 109 passed, 0 failed, 5 warnings in 7.67s.
- `.venv\Scripts\python.exe -m pytest -q tests/test_workspace_access.py tests/test_api.py tests/test_trusted_proxy.py` after adding validation-error redaction coverage — PASS: 110 passed, 0 failed, 5 warnings in 27.09s.
- `.venv\Scripts\python.exe -m pytest -q` — PASS: 821 passed, 0 failed, 188 warnings in 107.38s.
- `.venv\Scripts\python.exe -m compileall -q configs/settings.py src/api/access.py src/api/app.py tests/test_workspace_access.py` — PASS (exit 0).
- `rg -n -i "local_workspace_token|workspace[_ -]?token|provider[_ -]?(key|token|credential)" frontend` — PASS: no credential configuration or secret reference; only unrelated CSS class/comment matches for `workspace-token`.
- `git diff --check` — PASS (exit 0); output contains only pre-existing LF-to-CRLF conversion warnings.

Compared with frozen TEST-001, the full backend result increased from 793 to 821 passing tests solely because API-001 added 28 focused cases. Failures remain 0 and warnings remain 188. No TEST-001 backend behavior regressed. Frontend/build/E2E checks were not rerun because API-001 changed no frontend source or public response contract; their frozen results and documented pre-existing failures remain authoritative.

### Known Failures

Only the frozen TEST-001 failures recorded above: one timing-sensitive full-suite Firefox inspector failure with a passing focused rerun, plus six stale integration UI-expectation failures. API-001 introduced no regression or new failure.

### Decisions Made

- `WORKSPACE_MODE=public` remains the safe default; local mode must be explicit and requires a non-empty strong dedicated token.
- The workspace token uses a secret settings type and must never appear in response/status/log/exception/fixture text or any `VITE_*` variable.
- Browser requests to private capabilities require an exact allowlisted local Origin; non-browser clients may omit Origin but still require loopback peer, exact local Host and bearer token.
- Host/origin names are exact, with no suffix/wildcard matching. Local allowlists admit only `localhost` or loopback IP literals.
- Public mode returns an unavailable capability before credential processing. Missing and malformed/invalid credentials share one deterministic authentication response.
- Execution capability requires successful local workspace access plus a separate disabled-by-default setting.
- Settings validation error rendering omits all input values, preventing unrelated provider credentials loaded from the environment from appearing when local-mode validation fails.
- The existing public CORS origins and methods remain unchanged; only the exact `Authorization` request header was added.

### Exact Next Action

At API-001 completion, DATA-001 was the recorded next task. DATA-001 is now complete; its final state is recorded below.

## DATA-001 Quota-Safe Progress

### Active Task

DATA-001 — SQLite persistence foundation and migration framework. Status: COMPLETE.

### Last Completed Sub-checkpoint

DATA-001-D — full regression validation passed, documentation updated and Git diff/status reviewed.

### Completed Work

- Read the saved persistence/API contracts and confirmed the required default paths are `.local/workbench/workspace.sqlite3` and `.local/workbench/runs/{run_id}/`.
- Inspected API-001 settings/access dependencies, the existing browser schema-v4/tombstone ownership, current in-memory conversation/cache stores, repository ignore rules and all existing SQLite usage (none in production).
- Preserved browser persistence as the public-mode authority; DATA-001 will not connect SQLite to an endpoint, API startup or browser dual-write path.
- Selected built-in `sqlite3`, one connection per operation, `foreign_keys=ON`, WAL where supported, bounded busy timeout, short explicit transactions and a process-local re-entrant write lock.
- Selected deterministic contiguous migrations with version/name/checksum receipts. Each migration commits its schema receipt last in the same transaction; failures roll back without advancing the version.
- Selected three schema stages: core versioned records/tombstones/import receipts/allowlisted settings; research domains; then job and content-free operational event foundations.
- Selected opaque ID validation, UTC timestamps, canonical JSON, explicit expected-revision conflicts and tombstones that prevent silent resurrection.
- Selected configuration-controlled path validation that permits the planned `.local` default or an explicit absolute path, rejects `data/` and canonical corpus/index/evaluation roots, and never derives filesystem paths from entity/job IDs.
- Added `.local/` to Git ignores and documented the database, run-directory and bounded busy-timeout settings.
- Added validated `.local/workbench/workspace.sqlite3` and `.local/workbench/runs` settings without creating runtime paths during import or public startup.
- Added three deterministic, contiguous migrations covering schema receipts, versioned records/tombstones/imports/allowlisted settings, research-domain table foundations, and jobs/steps/events/content-free telemetry foundations.
- Added a connection/transaction layer with per-connection foreign keys, WAL, normal synchronous mode, a bounded busy timeout, integrity checks, short explicit transactions and a process-local serialized write lock.
- Added fail-closed checks for unversioned tables, malformed migration metadata, gaps, checksum/name drift and future schema versions. Migration receipts are inserted last inside the same transaction.
- Added a shared per-database process lock so writes from multiple repository/database instances serialize before entering SQLite, while SQLite still enforces the bounded cross-process busy timeout.
- Added schema-shape verification so a database with valid-looking migration receipts but missing required tables fails closed.
- Added a repository protocol and atomic SQLite implementation for opaque versioned records, expected-revision conflicts and tombstones that block silent resurrection.
- Added canonical finite JSON serialization, allowlisted entity types, opaque ID validation, credential-field rejection and configured-secret-value rejection.
- Added 32 focused DATA-001 tests covering the required creation, migration, rollback, compatibility, isolation, concurrency, revision, tombstone and redaction cases.
- Passed the combined persistence/API-001 compatibility gate and the complete hermetic backend suite without increasing the warning count.
- Confirmed the repository root contains no `.local/` runtime directory or database artifact after validation.
- Documented the configuration, isolation and deferred-workflow boundary in README and recorded the completed milestone in PROJECT_STATE.

### Remaining Work

DATA-001 has no remaining work. UI-001 is next in the implementation priority graph, but it has not started.

### Files Modified

- `.gitignore` — ignores local workspace database, WAL/SHM and run artifacts through `.local/`.
- `.env.example` — documents safe workspace persistence defaults.
- `configs/settings.py` — validates workspace paths and bounded SQLite busy timeout.
- `src/workspace/__init__.py` — defines the local persistence package boundary.
- `src/workspace/migrations.py` — defines deterministic migrations 1–3 and sequence validation.
- `src/workspace/database.py` — implements local-only construction, integrity/migration checks, WAL connections and transaction handling.
- `src/workspace/repository.py` — implements repository contracts, revision/conflict primitives, tombstones and secret guards.
- `tests/test_workspace_persistence.py` — adds the focused DATA-001 persistence matrix.
- `README.md` — documents SQLite configuration, path isolation and deferred workflow boundaries.
- `PROJECT_STATE.md` — records the completed DATA-001 milestone and validation receipt.
- `docs/UI_REBUILD_PLAN_CHECKPOINT.md` — persisted DATA-001-A/B/C/D.

No application router, frontend source, package manifest, lockfile, requirements file, dependency, canonical data, evaluation artifact, corpus or index file was changed by DATA-001.

### Tests Already Run and Exact Results

- Temporary-database smoke script: PASS — public settings rejected local construction; fresh schema migrated to version 3; repeat initialization stayed at version 3; `foreign_keys=1`; `journal_mode=wal`.
- `.venv\Scripts\python.exe -m compileall -q configs/settings.py src/workspace` — PASS (exit 0).
- `.venv\Scripts\python.exe -m pytest -q tests/test_workspace_persistence.py` — first run: 28 passed, 1 failed in 1.01s because the path-isolation assertion expected the later canonical-data error while the implementation rejected the same unsafe path earlier as outside `.local`; implementation ordering was clarified and no write occurred.
- `.venv\Scripts\python.exe -m pytest -q tests/test_workspace_persistence.py` — PASS after the assertion/validation refinement: 29 passed, 0 failed in 0.96s.
- `.venv\Scripts\python.exe -m pytest -q tests/test_workspace_persistence.py` — PASS after shared-lock, missing-schema and configured-secret coverage: 32 passed, 0 failed in 1.12s.
- `.venv\Scripts\python.exe -m pytest -q tests/test_workspace_persistence.py tests/test_workspace_access.py tests/test_api.py tests/test_trusted_proxy.py` — PASS: 142 passed, 0 failed, 5 warnings in 24.86s.
- `.venv\Scripts\python.exe -m pytest -q` — PASS: 853 passed, 0 failed, 188 warnings in 72.32s.
- `.venv\Scripts\python.exe -m compileall -q configs/settings.py src/workspace tests/test_workspace_persistence.py` — PASS (exit 0).
- `git diff --check` — PASS (exit 0); output contained only the existing LF-to-CRLF conversion warnings.
- Repository runtime-path check — PASS: `.local/` is absent; all test databases were isolated under pytest temporary directories.

Compared with API-001, the backend result increased from 821 to 853 passing tests solely because DATA-001 added 32 focused tests. Failures remain 0 and warnings remain 188. No API-001 or TEST-001 backend behavior regressed.

### Known Failures

Only the frozen TEST-001 UI/E2E failures already recorded above. The one focused DATA-001 development assertion mismatch was resolved before the passing 32-test gate; DATA-001 introduced no regression or new failure.

### Decisions Made

- Runtime database creation is explicit and local-only; importing settings or starting the public API must not create `.local/` or expose private state.
- The schema establishes later domain tables without implementing browser import, collection CRUD or durable job orchestration.
- Telemetry columns are content-free by construction; research content belongs only in research-domain records. Tokens, provider keys and authorization values are rejected by repository payload guards and are never workspace settings.
- Corrupt databases, malformed migration metadata, checksum/name drift, version gaps and versions newer than supported fail closed.

### Exact Next Action

UI-001 — implement the tokens/fonts/primitives foundation. Do not start it without a new instruction; DATA-001 is complete and this task stops here.

## UI-001 Quota-Safe Progress

### Active Task

UI-001 — shared semantic tokens, typography and accessible primitive foundation. Status: COMPLETE.

### Last Completed Sub-checkpoint

UI-001-D — full frontend, two-browser and nine-reference validation passed; final Git review and checkpoint completed.

### Completed Work

- Re-read the master-plan design system, standalone nine-reference matrix, saved implementation checkpoint, AGENTS.md, PROJECT_STATE.md, frontend design and contract documents, and the repository-local rag-ui-ux skill guidance.
- Confirmed all nine authoritative reference images remain present under `docs/ui-references/`; their completed planning analysis was preserved rather than repeated.
- Inspected the current token/base/motion layers, existing accessible `ModalDialog`, `SelectField` and `SegmentedControl`, test setup, frontend package scripts and representative existing page-level component patterns.
- Confirmed the current token layer already contains reader/workbench compatibility aliases that UI-001 must preserve.
- Defined an additive shared-UI boundary: tokens and primitives may own presentation, controlled interaction state, focus behavior and local overflow only. They will not own requests, persistence, evidence identity, routing, global notifications or application state.
- Defined the primitive entry as composition by later page tasks or an isolated test/showcase. Intent is reusable research-workspace presentation; scope, selected evidence and source identity are supplied by callers and remain unchanged.
- Defined overlay scroll ownership as the existing body lock plus an independently scrolling modal/drawer body; data-table wrappers and split/detail panes own only their internal overflow.
- Selected an Inter-first local/system UI stack because no licensed Inter font asset exists in the repository and dependency/network changes are outside UI-001. Filing text keeps the serif role and identifiers/diagnostics keep the monospace role.
- Identified five principal risks and controls: token alias regressions (retain aliases and run the full frontend gate), primitive overflow (responsive wrappers/min-width zero), modal/focus regressions (reuse tested `ModalDialog`), state communicated by color alone (icons/text/ARIA/selected markers), and small touch targets or motion sensitivity (44px mobile targets and reduced-motion rules).
- Added semantic typography, spacing, radius, control-height, focus, transition and layer tokens; aligned the dark palette with the master-plan reference values while retaining existing compatibility aliases.
- Added the complete UI-001 primitive set: Panel, PageHeader, MetricCard, SearchField, FilterBar, Select alias, Tabs, Badge, StatusBadge, IconButton, EmptyState, LoadingSkeleton, ScoreBadge, Pagination, ChartCard, Modal, Drawer, DataTable, DetailRail, SplitPane and EvidenceCard.
- Kept primitives controlled and domain-neutral. Modal/Drawer reuse `ModalDialog`; Select reuses `SelectField`; no request, route, storage, evidence or global application owner changed.
- Added responsive stacking, mobile 44px controls, visible focus, forced-colors selected outlines, reduced-motion skeleton behavior, table/pane overflow containment and text/icon/ARIA state cues.
- Added focused tests for the full shared export vocabulary, semantic table/region labeling, keyboard tabs, controlled search/pagination, non-color evidence selection and modal/drawer focus/close behavior.
- Replaced the initial skeleton gradient with a solid semantic opacity pulse to retain the no-gradient design rule, and verified provided input IDs, unique tab IDs and status-tone ownership.
- Ran the complete Chromium and Firefox browser matrices. Both passed all 115 active cases with two intentional provider/reader skips; the frozen Firefox timing-sensitive inspector failure did not reproduce.
- Ran and visually reviewed the nine final dark reference receipts side-by-side at their configured native/reference sizes. UI-001 aligns the shared palette, density, borders, typography and focus language; page composition and data-density gaps remain assigned to UI-002 and later page tasks.
- Re-ran the final Chromium reference receipt after the last primitive refinement: all 15 cases passed, accounting for Chat, Research, Documents, Search, Collections, Retrieval, Models, Pipeline and Evaluation plus compact light-theme preservation.
- Reviewed Git status/diff and the complete UI-001 source boundary. Existing unrelated dirty work was preserved; no dependency, route, page, backend, persistence, reader, request-controller or corpus/index source was changed.

### Remaining Work

UI-001 has no remaining work. UI-002 is the next task in the dependency graph and has not started.

### Files Modified

- `docs/UI_REBUILD_PLAN_CHECKPOINT.md` — activated UI-001 and recorded sub-checkpoint UI-001-A.
- `frontend/src/styles/tokens.css` — added UI-001 semantic scales and aligned the dark reference palette while preserving compatibility roles.
- `frontend/src/styles/primitives.css` — added isolated shared primitive, responsive, focus and reduced-motion styles.
- `frontend/src/index.css` — imports the shared primitive stylesheet.
- `frontend/src/components/ui/Foundation.tsx` — added controlled accessible shared primitives.
- `frontend/src/components/ui/Foundation.test.tsx` — added focused UI-001 component, behavior and accessibility coverage.
- `frontend/src/components/ui/index.ts` — added the shared UI export boundary and Select alias.
- `frontend/src/components/ui/SelectField.tsx` — exported its existing prop interface for the shared boundary.
- `PROJECT_STATE.md` — recorded the completed UI-001 milestone and validation receipt.

Planned UI-001 source files: `frontend/src/styles/tokens.css`, `frontend/src/styles/primitives.css`, `frontend/src/index.css`, `frontend/src/components/ui/Foundation.tsx`, `frontend/src/components/ui/Foundation.test.tsx`, `frontend/src/components/ui/index.ts`, and a minimal type-export adjustment in `frontend/src/components/ui/SelectField.tsx`. No page, route, backend, package, lockfile, reader, storage or request-controller file is in scope.

### Tests Already Run and Exact Results

- `bun run lint` in `frontend` — initial UI-001-B run failed with 5 TypeScript errors confined to the new Foundation typings (native `title` collisions on four interfaces and one close-button ref attached to a non-forwarding component). The interfaces and close control were corrected without changing existing code behavior.
- `bun run lint` in `frontend` after correction — PASS: `tsc --noEmit`, 0 TypeScript errors.
- `bunx vitest run src/components/ui/Foundation.test.tsx src/components/ui/ModalDialog.test.tsx src/components/ui/SelectField.test.tsx` — initial UI-001-C run: 7 passed, 1 failed because the new test asserted the inner status text span rather than its badge parent; rendered component behavior was correct.
- The same targeted Vitest command after correcting the selector — PASS: 3 files, 8 tests, 0 failed in 1.34s.
- `bun run test` in `frontend` — PASS: 64 files, 329 tests, 0 failed in 13.66s. This is the frozen 324-test suite plus 5 focused UI-001 cases; expected storage-failure DOMException stderr remained unchanged.
- `bun run build` in `frontend` — PASS: Vite production build, 2,017 modules transformed, completed in 15.40s.
- `bunx playwright test --project=chromium --workers=1 --retries=0` in `frontend` — PASS: 115 passed, 2 intentionally skipped, 0 failed in 3.7m.
- `bunx playwright test --project=firefox --workers=1 --retries=0` in `frontend` — PASS: 115 passed, 2 intentionally skipped, 0 failed in 4.3m. The frozen timing-sensitive Firefox inspector failure did not reproduce in this full run.
- Final post-refinement `bun run lint` — PASS: `tsc --noEmit`, 0 TypeScript errors.
- Final post-refinement targeted Vitest command — PASS: 3 files, 8 tests, 0 failed in 1.62s.
- Final post-refinement `bun run build` — PASS: 2,017 modules transformed, completed in 3.78s.
- `bunx playwright test e2e/reconciliation-reference.spec.ts --project=chromium --workers=1 --retries=0` after final refinement — PASS: 15 passed, 0 failed in 53.2s; all nine reference filenames and compact light preservation were exercised.
- `git diff --check` — PASS (exit 0); output contained only the existing LF-to-CRLF conversion warnings.

The frozen TEST-001 frontend baseline remains 324 unit tests passing, production build passing, Chromium 115 passing with 2 intentional skips, and the documented timing-sensitive Firefox/integration failures.

### Known Failures

The six frozen TEST-001 integration failures were not rerun because UI-001 changed no API contract or integration harness; they remain documented pre-existing failures. The prior full-suite Firefox timing-sensitive inspector failure did not reproduce: the unchanged case passed as part of the 115-test Firefox gate. The temporary UI-001-B compile errors and UI-001-C assertion-selector mismatch were corrected before their passing targeted gates and are not final failures. UI-001 introduced no regression or new failure.

### Decisions Made

- Build the foundation additively and do not migrate existing page compositions during UI-001.
- Reuse `ModalDialog` for modal/drawer mechanics and `SelectField` for the Select primitive instead of creating competing focus/listbox implementations.
- Require accessible names for icon-only buttons and search/select controls; communicate status and selection with text/icon/ARIA in addition to color.
- Keep the shared primitives domain-neutral and controlled. Later UI tasks bind real API, persistence, route and evidence behavior.
- Preserve the current dirty tree and do not alter the existing nine-reference planning conclusions.
- Do not package an unverified font binary. Use the Inter-first stack until a licensed repository asset is deliberately added by a later authorized task.
- Treat the side-by-side reference review as a UI-001 shared-language receipt; it does not close the already planned page-composition gaps assigned to UI-002 and subsequent page tasks.

### Exact Next Action

UI-002 — implement the planned router, application shell and legacy-link adapter now that both UI-001 and DATA-001 are complete. Do not begin it without a new instruction; UI-001 stops here.

## UI-002 Quota-Safe Progress

### Active Task

UI-002 — explicit frontend routing, application shell, responsive navigation/header composition and legacy URL compatibility. Status: IN PROGRESS.

### Last Completed Sub-checkpoint

UI-002-A — current navigation/App ownership inspected; route mapping and compatibility strategy recorded; exact files to change identified.

### Completed Work

- Re-read the master plan, reference gap matrix, completed UI-001 checkpoint, AGENTS.md, project state, frontend design/contract, package manifest and the repository-local rag-ui-ux guidance.
- Inspected App URL ownership, every `setActiveView` transition, conversation selection/open flows, evidence hash parsing/writing, current navigation registry, sidebar drawer focus restoration, header controls, command palette, V5 application/workbench shell, responsive CSS, Vercel configuration and all nine reference assets.
- Confirmed the current app owns navigation through local `activeView` state plus `?view=` replacement and manual `popstate`/`hashchange` listeners. Evidence deep links are revision-bound hashes and must remain parsed by the existing domain owner.
- Confirmed the current V5 shell already preserves the critical domain boundaries: App owns route/document identity, the workbench controller owns presentation only, and existing hooks/components own requests, cancellation, persistence, evidence and reader behavior.
- Selected a persistent BrowserRouter boundary around App plus an explicit route registry/resolver. The App compatibility surface remains mounted across route changes; pathname/query/hash and parameters become router-owned without moving domain state into the router.
- Selected one-time legacy translation for root `?view=` URLs. Known views map to the new route, unknown query keys and exact evidence hashes survive, unsupported view values remain visible and do not loop, and browser back/forward is driven by router location rather than manual listeners.
- Selected explicit truthful adapters for incomplete destinations: Datasets and Logs resolve to unavailable/deferred shells; nested document, collection, pipeline-run and evaluation-run parameters remain in the route contract without fabricating loaded domain records. Existing implemented domains continue through compatibility adapters.
- Selected a route-aware grouped sidebar with Workspace, Build, Evaluate and Manage groups. Architecture and legacy System remain inbound-compatible but leave primary navigation; Users, API Keys, subscription/upgrade, sharing and model-switching controls remain absent.
- Selected master-plan desktop widths: expanded navigation 216px at 1600+, approximately 184px at 1440–1599, 160px at 1280–1439 and 158px at 1025–1279; compact rail remains 56px and <=1024 remains a focus-restoring drawer.
- Selected an exact React Router dependency addition only. TanStack Query and all unrelated packages remain out of scope.

### Remaining Work

- UI-002-B: add React Router, explicit route contracts and the legacy URL/deep-link compatibility adapter; add focused route tests.
- UI-002-C: implement the route-aware grouped shell/sidebar/top bar and responsive geometry using UI-001 tokens/primitives without migrating page domains.
- UI-002-D: validate direct production loads, legacy/back-forward/hash behavior, two-browser compatibility and all nine non-page reference receipts; review diff/status and record the gate.

### Files Modified

- `docs/UI_REBUILD_PLAN_CHECKPOINT.md` — activated UI-002 and recorded sub-checkpoint UI-002-A.

Planned UI-002 boundary: `frontend/package.json`, `frontend/bun.lock`, new route contract/adapter files and tests under `frontend/src/app/`, `frontend/src/App.tsx`, `frontend/src/lib/workspace.ts`, `frontend/src/lib/commandRegistry.ts`, `frontend/src/components/CommandPalette.tsx`, `frontend/src/components/Sidebar.tsx`, `frontend/src/components/WorkspaceHeader.tsx`, `frontend/src/lib/i18n.tsx`, scoped shell styles, `frontend/vercel.json`, focused route/shell tests, `PROJECT_STATE.md`, and this checkpoint. Existing page-domain, request, persistence, evidence, reader and backend files remain out of scope.

### Tests Already Run and Exact Results

None for UI-002-A; this was an inspection/design checkpoint. The frozen UI-001 baseline remains 64 Vitest files / 329 tests, Chromium 115 passed with 2 skips, Firefox 115 passed with 2 skips, production build passing and nine-reference receipt 15/15.

### Known/Pre-existing Failures

The six frozen TEST-001 integration expectation failures remain pre-existing. UI-002 may legitimately supersede their stale navigation wording, but any changed assertion must retain equivalent compatibility coverage. No UI-002 regression exists at sub-checkpoint A.

### Decisions Made

- Keep App mounted across route changes so URL translation never regenerates answers or resets domain controllers.
- Derive the compatibility `WorkspaceView` from the router location; use route navigation for all future view transitions and preserve exact conversation/evidence identity when a nested route or hash supplies it.
- Preserve all unknown meaningful query parameters during legacy translation and preserve the complete hash byte-for-byte.
- Use route-aware links and `aria-current` for navigation. Deferred destinations may explain their unavailable capability but must not display invented content.
- Keep theme, locale, real scope, backend readiness and observed model identity in the top bar; keep command entry provider-free until explicitly submitted through an existing domain flow.

### Exact Next Action

UI-002-B — add the React Router dependency, explicit route registry/resolver, one-time legacy adapter and focused route compatibility tests. Do not begin UI-003, API-002, DATA-002, DATA-003, DATA-004 or later tasks.

## UI-002-B Quota-Safe Checkpoint

### Active Task

UI-002 — explicit frontend routing, application shell, responsive navigation/header composition and legacy URL compatibility. Status: IN PROGRESS.

### Last Completed Sub-checkpoint

UI-002-B — React Router route contract, legacy adapter and focused compatibility coverage implemented.

### Completed Work

- Added `react-router-dom` 7.18.4 as the sole UI-002 dependency and updated the Bun lockfile.
- Added the complete explicit route registry for Chat, Research, Documents, Search, Collections, Retrieval, Models, Pipeline, Reranker, Evaluation, Analytics, Datasets, Settings and Logs, including every required parameterized detail/run route.
- Wrapped the existing App owner in a persistent BrowserRouter without moving request, cancellation, persistence, evidence, reader or conversation ownership into the router.
- Replaced local `activeView` URL mutation and manual popstate/hash listeners with a route resolver and router navigation.
- Added one-time root `?view=` translation that preserves duplicate/unknown query parameters and exact hashes, fails closed for unknown legacy views, and avoids redirect loops.
- Bound nested conversation routes to exact stored conversation IDs. Missing IDs produce a truthful notice and never select a fallback conversation.
- Preserved evidence hashes while promoting legacy evidence links to nested Research conversation routes.
- Updated navigation command metadata to derive from the shell route registry.
- Added EN/VI copy for every new route/group label and truthful deferred-destination description.
- Updated existing App/navigation contract assertions to reflect semantic route links and isolate test URL state.

### Remaining Work

- UI-002-C: complete the route-aware grouped sidebar/header shell, responsive desktop widths, truthful local-workspace identity and deferred route presentation; add focused shell tests.
- UI-002-D: add/execute direct-load, legacy, back-forward, hash, two-browser, production-build and nine-reference validation; inspect the final diff/status.

### Files Modified

- `frontend/package.json`
- `frontend/bun.lock`
- `frontend/src/app/routes.ts`
- `frontend/src/app/routes.test.ts`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/lib/commandRegistry.ts`
- `frontend/src/lib/workspace.test.ts`
- `frontend/src/components/CommandPalette.tsx`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/lib/i18n.tsx`
- `docs/UI_REBUILD_PLAN_CHECKPOINT.md`

### Tests Already Run and Exact Results

- `bunx vitest run src/app/routes.test.ts` — PASS: 1 file, 26 tests, 0 failed in 1.34s.
- Initial `bun run lint` after the partial route file appeared — FAIL: 15 new TypeScript errors (14 missing i18n keys and one legacy-view narrowing error); all were confined to incomplete UI-002-B additions and corrected.
- `bun run lint` after routing/App integration — PASS: `tsc --noEmit`, 0 errors.
- Initial focused App/navigation run — route/workspace/palette suites passed; App had 7 failures because pre-router tests queried navigation buttons and shared `window.location` between cases. Assertions were updated to verify the new semantic links and test setup now resets the URL.
- `bunx vitest run src/App.test.tsx` after correction — PASS: 1 file, 23 tests, 0 failed in 5.07s.

### Known/Pre-existing Failures

The frozen TEST-001 integration failures remain outside UI-002. No final UI-002-B failure remains. Browser/full-suite validation is pending UI-002-D.

### Decisions Made

- Keep `WorkspaceView` as the internal domain compatibility vocabulary while using route IDs as shell and command-palette identity.
- Keep nested route parameters available without fabricating document, collection, pipeline-run or evaluation-run records.
- Represent Datasets, Logs and unknown routes with explicit unavailable content instead of mapping them to invented data.
- Preserve the current route family when opening a conversation from Chat or Research.
- Use semantic links with `aria-current` for shell navigation while routing clicks through the existing cancellation/cleanup boundary.

### Exact Next Action

UI-002-C — finish the grouped responsive shell, truthful header identity, route availability styling and focused shell coverage. Do not begin UI-003, API-002, DATA-002, DATA-003, DATA-004 or later tasks.

## UI-002-C Quota-Safe Checkpoint

### Active Task

UI-002 — explicit frontend routing, application shell, responsive navigation/header composition and legacy URL compatibility. Status: IN PROGRESS.

### Last Completed Sub-checkpoint

UI-002-C — route-aware grouped application shell and responsive navigation implemented; unit/build gate passing.

### Completed Work

- Replaced the legacy view-button sidebar with route-aware semantic links and `aria-current` state derived from the explicit router contract.
- Implemented the required Workspace, Build, Evaluate and Manage navigation groups.
- Exposed truthful availability metadata for the existing Reranker compatibility surface and deferred Datasets/Logs routes.
- Added explicit unavailable panels for Datasets, Logs, unknown paths and unsupported legacy views; no product records or capabilities are fabricated.
- Updated route transitions to preserve the existing stream-cancellation and evidence/document cleanup boundary.
- Replaced the fake question-mark account identity with a truthful Local workspace / Local session label and local-device icon.
- Implemented the planned desktop navigation widths: 216px at 1600+, 184px at 1440–1599, 160px at 1280–1439, 158px at 1025–1279, compact 56px and drawer navigation at 1024px or below.
- Added production-host SPA fallback configuration while preserving immutable asset caching.
- Added a UI-002 browser specification covering every direct route, legacy translation, unknown routes, history, active links and drawer focus restoration.
- Migrated existing browser navigation assertions from legacy buttons/view IDs to semantic links/route IDs without weakening the underlying journeys.

### Remaining Work

- UI-002-D: run the targeted routing browser receipt, full Chromium and Firefox matrices, nine-reference receipt, production direct-route verification and final diff/status checks; resolve only UI-002 regressions.

### Files Modified

- UI-002-B files listed above.
- `frontend/src/components/WorkspaceHeader.tsx`
- `frontend/src/styles/components.css`
- `frontend/vercel.json`
- `frontend/e2e/ui-routing.spec.ts`
- Existing navigation assertions in `frontend/e2e/fixtures.ts`, `frontend/e2e/integration.spec.ts`, `frontend/e2e/reconciliation-reference.spec.ts`, `frontend/e2e/regression.spec.ts`, `frontend/e2e/v5-02-shell.spec.ts`, `frontend/e2e/v5-07-handoffs.spec.ts`, `frontend/e2e/workspace-performance.spec.ts`, and `frontend/e2e/app.spec.ts`.

### Tests Already Run and Exact Results

- `bun run lint` — PASS: `tsc --noEmit`, 0 errors.
- `bun run test` — PASS: 65 files, 355 tests, 0 failed in 12.80s. This is the UI-001 329-test baseline plus 26 UI-002 route-contract cases; expected storage-failure DOMException stderr remains unchanged.
- `bun run build` — PASS: Vite production build, 2,029 modules transformed, completed in 10.84s.

### Known/Pre-existing Failures

The frozen TEST-001 integration expectation failures remain outside UI-002. No UI-002 unit, typecheck or build regression exists. Browser validation is pending UI-002-D.

### Decisions Made

- Use a stable visible availability mark for partial/deferred navigation while keeping all destinations navigable and explainable.
- Keep header controls limited to real scope, readiness, observed model identity, theme, language, settings, help and the truthful local workspace identity.
- Preserve the legacy internal WorkspaceView registry for domain panels and compatibility tests; shell navigation and commands use route IDs.
- Configure the deployment host to return `index.html` for route requests so BrowserRouter direct loads work in production.

### Exact Next Action

UI-002-D — execute the focused and full two-browser routing/shell gate, nine-reference receipt, direct production-load check, Git review and final checkpoint. Do not begin UI-003, API-002, DATA-002, DATA-003, DATA-004 or later tasks.

## UI-002-D Final Checkpoint

### Active Task

UI-002 — explicit frontend routing, application shell, responsive navigation/header composition and legacy URL compatibility. Status: COMPLETE.

### Last Completed Sub-checkpoint

UI-002-D — full route, shell, two-browser, direct-production-load, nine-reference and Git validation passed; final checkpoint recorded.

### Completed Work

- Completed the explicit React Router contract for all required list/detail destinations: `/chat`, `/chat/:conversationId`, `/research`, `/research/:conversationId`, `/documents`, `/documents/:documentId`, `/search`, `/collections`, `/collections/:collectionId`, `/retrieval`, `/models`, `/pipeline`, `/pipeline/runs/:runId`, `/reranker`, `/evaluation`, `/evaluation/runs/:runId`, `/analytics`, `/datasets`, `/settings`, and `/logs`.
- Kept the existing App and domain controllers mounted across navigation. Request/cancellation, frontend persistence, evidence selection, reader state, conversation state, and compatibility ownership were preserved.
- Completed one-time legacy `?view=` translation with exact hash and unknown-query preservation, deterministic handling of unsupported legacy values, canonical nested conversation links, and no redirect loop or query generation.
- Completed the route-aware Workspace, Build, Evaluate, and Manage sidebar groups with semantic links, `aria-current`, availability labels, required responsive widths, and the existing focus-restoring drawer at 1024px and below.
- Completed the truthful local workspace/session header and retained only real scope, readiness, observed model, theme, locale, settings, help, and command surfaces. No fake user/profile, subscription, upgrade, sharing, API-key, or model-switch control was added.
- Added truthful unavailable states for deferred Datasets and Logs routes and unknown routes. Parameterized destinations retain their route identity without fabricating domain records.
- Added the production SPA fallback so every canonical route loads directly from the Vite preview/deployment host while static assets retain their cache policy.
- Added focused route unit coverage and browser coverage for all 20 route patterns, legacy links, exact evidence hashes, unknown query parameters, browser back/forward, active navigation, direct production loads, and drawer focus restoration.
- Corrected browser-gate regressions found during validation: migrated remaining legacy navigation selectors, preserved citation focus after evidence close, and suppressed a stale prior evidence hash while selecting a new source. These changes retain the existing evidence owner and eliminate the source-selection race without changing the deep-link contract.
- Verified the final complete Chromium and Firefox matrices, the focused nine-reference receipt, TypeScript, all frontend unit tests, the production build, Git status/diff, and whitespace validity.
- Preserved the dirty worktree and all unrelated API-001, DATA-001, PDF/workbench, documentation, audit, screenshot, and local artifact work. No file was reverted or removed.

### Remaining Work

UI-002 has no remaining work. API-002 is the next unfinished task in the master-plan priority/dependency graph. UI-003 remains blocked on DATA-002 as well as this now-complete UI-002 task.

### Files Modified

UI-002 created or modified the following files:

- `frontend/package.json` — added the explicit React Router dependency.
- `frontend/bun.lock` — recorded the React Router dependency resolution; other pre-existing lockfile changes were preserved.
- `frontend/src/app/routes.ts` — added the route registry, resolver, route helpers, navigation groups, availability state, and legacy URL translator.
- `frontend/src/app/routes.test.ts` — added focused route/legacy compatibility coverage.
- `frontend/src/App.tsx` — integrated the persistent BrowserRouter, route-derived compatibility view, nested conversation identity, truthful unavailable states, navigation, and evidence-hash race/focus preservation.
- `frontend/src/App.test.tsx` — updated App navigation coverage for semantic routes and isolated URL state.
- `frontend/src/components/Sidebar.tsx` — implemented grouped route links, active state, and availability markers.
- `frontend/src/components/CommandPalette.tsx` — routed navigation commands through canonical destinations.
- `frontend/src/components/WorkspaceHeader.tsx` — replaced the placeholder identity with truthful local workspace/session copy.
- `frontend/src/lib/commandRegistry.ts` — derived route commands from the canonical route registry.
- `frontend/src/lib/workspace.test.ts` — updated compatibility registry assertions for canonical routing.
- `frontend/src/lib/i18n.tsx` — added English and Vietnamese route, group, availability, and local workspace strings.
- `frontend/src/styles/components.css` — added planned navigation widths and availability presentation.
- `frontend/vercel.json` — added SPA route fallback while preserving asset headers.
- `frontend/e2e/ui-routing.spec.ts` — added direct-load, legacy, history, active-state, and drawer-focus acceptance coverage.
- `frontend/e2e/app.spec.ts`, `frontend/e2e/fixtures.ts`, `frontend/e2e/integration.spec.ts`, `frontend/e2e/reconciliation-reference.spec.ts`, `frontend/e2e/regression.spec.ts`, `frontend/e2e/v5-02-shell.spec.ts`, `frontend/e2e/v5-06-layout.spec.ts`, `frontend/e2e/v5-07-handoffs.spec.ts`, `frontend/e2e/workspace-layout.spec.ts`, and `frontend/e2e/workspace-performance.spec.ts` — migrated route/navigation assertions and fixtures to the canonical shell without weakening their domain journeys.
- `PROJECT_STATE.md` — recorded the completed UI-002 milestone and validation receipt.
- `docs/UI_REBUILD_PLAN_CHECKPOINT.md` — recorded UI-002-A through UI-002-D and the final gate.

No backend, persistence, canonical data, retrieval, evaluation, reader representation, corpus/index, package other than `react-router-dom`, or unrelated production source file was modified by UI-002.

### Tests Already Run and Exact Results

- `bunx vitest run src/app/routes.test.ts` — PASS: 1 file, 26 tests, 0 failed in 1.34s.
- `bun run lint` during UI-002-B — initial partial integration failed with 15 new TypeScript errors (14 missing translation keys and one legacy-view narrowing error); all were corrected within UI-002-B.
- `bunx vitest run src/App.test.tsx` after migrating the App tests — PASS: 1 file, 23 tests, 0 failed in 5.07s.
- First `bun run test` UI-002-C gate — PASS: 65 files, 355 tests, 0 failed in 12.80s.
- First `bun run build` UI-002-C gate — PASS: 2,029 modules transformed in 10.84s.
- `bunx playwright test e2e/ui-routing.spec.ts --project=chromium --workers=1 --retries=0` — PASS: 3 tests, 0 failed. This includes direct production-preview loads for every required route pattern.
- First full Chromium gate — 9 UI-002 migration/regression failures were exposed among 120 cases; remaining cases passed or retained the two intentional skips. Legacy selectors, shell-width expectations, and focus/selection behavior were corrected.
- Second full Chromium gate — 3 evidence-selection/deep-link race failures remained among 120 cases; the stale-hash suppression and authoritative close/focus handling were corrected.
- Final `bunx playwright test --project=chromium --workers=1 --retries=0` — PASS: 118 passed, 2 intentionally skipped, 0 failed in 3.8m.
- Final `bunx playwright test --project=firefox --workers=1 --retries=0` — PASS: 118 passed, 2 intentionally skipped, 0 failed in 4.4m.
- Final `bunx playwright test e2e/reconciliation-reference.spec.ts --project=chromium --workers=1 --retries=0` — PASS: 15 passed, 0 failed in 50.6s. The receipt explicitly covers the global shell plus Research, Documents, Search, Collections, Retrieval, Models, Pipeline, and Evaluation reference images, accounting for all nine authoritative screens, and verifies compact light-theme preservation.
- Final `bun run lint` — PASS: `tsc --noEmit`, 0 TypeScript errors.
- Final `bun run test` — PASS: 65 files, 355 tests, 0 failed in 25.70s. Expected storage-failure DOMException stderr from deliberate fallback tests remains unchanged.
- Final `bun run build` — PASS: Vite production build, 2,029 modules transformed in 5.11s.
- Final `git diff --check` — PASS (exit 0); output contained only existing LF-to-CRLF working-copy warnings.
- Final `git status --short` and scoped diff review — completed. The large pre-existing dirty tree remains intact; UI-002 files are listed above and no unrelated work was reverted.

### Compatibility Baseline Comparison

- UI-001 baseline: 64 Vitest files / 329 tests, Chromium 115 passed plus 2 intentional skips, Firefox 115 passed plus 2 intentional skips, and a passing 2,017-module production build.
- UI-002 final: 65 Vitest files / 355 tests, Chromium 118 passed plus 2 intentional skips, Firefox 118 passed plus 2 intentional skips, and a passing 2,029-module production build.
- Delta: 26 focused route unit tests and 3 routing/browser acceptance cases were added. Existing active browser cases continue to pass in both engines. The module-count increase reflects React Router and its integration.
- The six frozen TEST-001 integration expectation failures were not treated as UI-002 regressions. UI-002's relevant compatibility journeys passed in the final unit, Chromium, Firefox, and production-direct-load gates.

### Known/Pre-existing Failures

The six TEST-001 integration expectation failures remain frozen and pre-existing. The two skipped browser cases per engine remain the intentional provider-free local-backend readiness and P08 reader-baseline checks. Expected DOMException stderr in storage fallback unit tests remains deliberate coverage. The temporary TypeScript, stale selector, width expectation, and evidence hash/focus failures found during UI-002 were corrected and do not remain in the final gate. UI-002 introduced no known regression.

### Decisions Made

- `react-router-dom` 7.18.4 is the only UI-002 dependency addition. No TanStack Query or unrelated package was added.
- Keep routing as the URL/navigation owner while the existing App/hooks/components retain request, cancellation, persistence, evidence, reader, and product state ownership.
- Preserve exact query/hash identity during legacy translation and evidence transitions; do not trust fallback records when a parameterized route names a missing conversation or domain entity.
- Keep all planned shell destinations explicit. Where a capability is deferred, show that state truthfully instead of hiding the route or fabricating data.
- Use the required responsive shell dimensions and existing focus-restoring drawer lifecycle rather than migrating page compositions during UI-002.
- Treat the nine-reference run as a shell/routing compatibility receipt. Page-specific composition gaps remain assigned to their later UI tasks.
- Select API-002 next from the recorded master-plan ordering. UI-003 cannot start until DATA-002 is also complete.

### Exact Next Action

API-002 — perform the compatible backend router extraction while preserving the frozen wire behavior. Do not begin API-002 without a new instruction. Do not begin DATA-002, UI-003, or any later task as part of UI-002.

## API-002 Quota-Safe Progress

### Active Task

API-002 — behavior-preserving incremental extraction of existing FastAPI transport groups. Status: IN PROGRESS.

### Last Completed Sub-checkpoint

API-002-A — current route inventory, dependency ownership, extraction boundaries, compatibility risks, and exact planned files recorded.

### Completed Work

- Re-read the master plan, reference matrix, completed UI-002 checkpoint, AGENTS.md, PROJECT_STATE.md, relevant backend architecture documentation, API tests, and the repository-local rag-core guidance.
- Inspected the current 2,249-line `src/api/app.py`, all 38 application routes in registration order, lifespan-created state, middleware, exception handling, limiter ownership, API-001 dependencies, schema definitions, document/reader/PDF helpers, retrieval/query/SSE handlers, session/cache operations, and public evaluation report transport.
- Captured the pre-extraction route order and complete OpenAPI contracts for the 14 planned moved paths in `%TEMP%/enterprise_qa_api002_before.json`; this artifact is outside the repository and contains no secrets or runtime data.
- Confirmed lifespan owns one `_state` mapping containing the single pipeline, decomposer, vector store, document indexes, corpus facts, and supported tickers. Router factories will receive callbacks/references to those owners and will not construct runtime models, stores, pipelines, readers, or evaluation services.
- Selected safe route groups: health/configuration, supported tickers, system information, published evaluation reports, sessions, cache controls, and metrics.
- Selected a dedicated schema module for the existing query, decomposed-query, cache-test, and retrieval-inspection Pydantic models. `app.py` will re-export the imported classes so existing test/harness imports remain compatible.
- Identified compatibility-sensitive routes to leave in `app.py`: all query and SSE routes, retrieval inspection, document catalog/chunks, structured/original readers, PDF representation/mapping/content, and chunk-location endpoints.
- Confirmed router inclusion must occur at the exact former decorator positions to preserve complete route order, including static/dynamic evaluation precedence and the query-stream position after cache routes.

### Remaining Work

- API-002-B: create schema/router modules; extract the first health/corpus/system/evaluation groups; compare route registration and focused contracts.
- API-002-C: extract sessions/cache/metrics, verify late-bound telemetry/state ownership, add strict route/order/OpenAPI/provider-free contract tests, and review remaining `app.py` ownership.
- API-002-D: run focused API-002, API-001, DATA-001, existing API, compile/import, full hermetic backend, diff/status, and whitespace gates; record the final route inventory and baseline comparison.

### Routes Moved

None yet. API-002-A is the inspection/design checkpoint.

### Routes Intentionally Left

- `/query`, `/query/decomposed`, `/query/decomposed/stream`, and `/query/stream` — preserve rate limits, timeouts, cancellation, session memory, exact SSE events, and shared RAG/decomposer ownership without transport refactoring.
- `/retrieval/inspect` — preserve provider-free retrieval stage semantics and direct access to the authoritative pipeline/retriever while API-005 remains out of scope.
- `/documents`, `/documents/{document_id}`, `/documents/{document_id}/chunks`, `/chunks/{chunk_id}`, and all nested original/structured/PDF/reader/location routes — preserve established document indexes, reader/provenance identity, artifact binding, static/dynamic ordering, and current partial PDF work in the dirty tree.

### Files Modified

- `docs/UI_REBUILD_PLAN_CHECKPOINT.md` — activated API-002 and recorded sub-checkpoint A.

Planned API-002 files: `src/api/app.py`, new `src/api/schemas.py`, new router package/modules under `src/api/routers/`, new `tests/test_api_router_contracts.py`, `PROJECT_STATE.md`, and this checkpoint. No frontend, configuration, dependency, persistence, corpus/index, data, evaluation artifact, or workspace runtime database file is in scope.

### Tests Executed and Exact Results

- Pre-change import/OpenAPI inventory script — PASS: imported the FastAPI app, recorded all 38 application routes in order, and captured OpenAPI contracts for all 14 planned moved paths.
- No behavioral test has run yet for API-002-A. The frozen DATA-001 baseline remains 853 passed, 0 failed, 188 warnings.

### Known/Pre-existing Failures

The six frozen TEST-001 external integration expectation failures remain pre-existing and outside the hermetic backend gate. No API-002 regression exists at sub-checkpoint A.

### New Regressions

None.

### Decisions Made

- Use small router factories with callbacks to the existing application-owned state rather than a new service locator or duplicate runtime construction.
- Preserve late binding for the mutable `app_module.telemetry` test seam through a getter; preserve the shared `_state` dictionary identity used by tests and the deterministic HTTP/SSE harness.
- Keep existing domain services authoritative. API-002 introduces transport organization only and no future API-003+ contracts.
- Compare both route order and generated OpenAPI operations before/after extraction; add explicit precedence tests for `/evaluation/runs` before `/evaluation/runs/{run_id}` and `/session/{session_id}` before its nested history path.

### Exact Next Action

API-002-B — create the schema/router package and extract health/configuration, supported-tickers, system-info, and published-evaluation routes at their current registration positions, then verify route order and focused contracts. Do not begin API-003, DATA-002, UI-003, or any later task.

## API-002-B Quota-Safe Checkpoint

### Active Task

API-002 — behavior-preserving incremental extraction of existing FastAPI transport groups. Status: IN PROGRESS.

### Last Completed Sub-checkpoint

API-002-B — schema boundary and first safe health/corpus/system/evaluation router groups extracted; registration and focused contracts verified.

### Completed Work

- Added the dedicated `src/api/schemas.py` module with the existing query, source, interpretation, decomposed-query, cache-test, and retrieval-inspection models unchanged. `src.api.app` imports/re-exports these classes, preserving current harness/test imports.
- Added router factories that receive application-owned callbacks/state instead of constructing runtime services.
- Extracted health liveness/readiness/legacy health and the protected API-001 configuration-status route with the original dependencies and errors.
- Extracted supported-tickers with its threadpool boundary intact. The first focused run exposed that passing the loader directly broke the existing monkeypatch seam; the app now supplies a late-bound callback and the concurrency test passes.
- Extracted allowlisted system information without moving corpus or model ownership.
- Extracted validated published evaluation listing/detail in static-before-dynamic order with the same filters, report root, validation, and 404 semantics.
- Verified all 38 application routes retain identical index, path, methods, endpoint name, and declared status code.
- Compared the generated OpenAPI operations for all 14 planned moved paths with the saved pre-change artifact. Three initial description-only differences were restored; the final comparison is exactly equal.
- Python compilation and imports pass for the new schema/router boundary.

### Remaining Work

- API-002-C: focus-test and finalize the staged sessions/cache/metrics extraction; add dedicated route-order/OpenAPI/unknown-resource/provider-free contract coverage and verify dependency/state ownership.
- API-002-D: execute API-001, DATA-001, existing API, full hermetic, compile/import, diff/status, and whitespace gates; record final inventory and baseline comparison.

### Routes Moved

- `GET /health/live`
- `GET /system/configuration-status`
- `GET /health/ready`
- `GET /health`
- `GET /supported-tickers`
- `GET /system/info`
- `GET /evaluation/runs`
- `GET /evaluation/runs/{run_id}`

Session and cache/metrics routers are present in the working tree but remain part of the pending API-002-C focused compatibility gate.

### Routes Intentionally Left

The API-002-A list is unchanged: query/SSE, retrieval inspection, documents/chunks, structured/original readers, PDF routes, and chunk-location routes remain in `app.py` because their transport is tightly coupled to compatibility-sensitive domain/state behavior.

### Files Modified

- `src/api/app.py`
- `src/api/schemas.py`
- `src/api/routers/__init__.py`
- `src/api/routers/health.py`
- `src/api/routers/corpus.py`
- `src/api/routers/system.py`
- `src/api/routers/evaluations.py`
- `src/api/routers/sessions.py`
- `src/api/routers/cache.py`
- `docs/UI_REBUILD_PLAN_CHECKPOINT.md`

No frontend, dependency manifest, configuration, persistence, corpus/index, data, public evaluation artifact, or workspace runtime database file was changed.

### Tests Executed and Exact Results

- `.venv\\Scripts\\python.exe -m compileall -q src/api` — PASS, exit 0.
- Import smoke for `src.api.app`, `src.api.schemas`, `src.api.routers.health`, and `src.api.routers.cache` — PASS: `imports-ok`.
- Route/OpenAPI comparison — PASS: 38/38 route registrations equal; 14/14 moved-path OpenAPI operations exactly equal after restoring original descriptions.
- First focused health/corpus/system/evaluation run — 12 passed, 1 failed, 79 deselected. The failure was the existing supported-ticker loader monkeypatch/concurrency seam captured too early by the router factory.
- Same focused command after late-binding the loader — PASS: 13 passed, 79 deselected, 1 pre-existing ReportLab deprecation warning in 6.94s.

### Known/Pre-existing Failures

The frozen TEST-001 external integration expectation failures remain outside this hermetic gate. The ReportLab deprecation warning is part of the 188-warning DATA-001 baseline.

### New Regressions

None remaining. The supported-ticker test-seam regression was found and corrected within API-002-B.

### Decisions Made

- Preserve exact OpenAPI descriptions as part of the observable contract, even though the initial differences were documentation-only.
- Keep existing app-module test seams late-bound when tests/harnesses intentionally replace their owners.
- Count session/cache/metrics as complete only after the API-002-C focused gate proves validation, rate limiting, telemetry replacement, threadpool behavior, and route order.

### Exact Next Action

API-002-C — finish and focus-test sessions/cache/metrics extraction, add dedicated route and OpenAPI regression coverage, and verify the remaining app-owned runtime boundaries. Do not begin API-003, DATA-002, UI-003, or later tasks.

## API-002-C Quota-Safe Checkpoint

### Active Task

API-002 — behavior-preserving incremental extraction of existing FastAPI transport groups. Status: IN PROGRESS.

### Last Completed Sub-checkpoint

API-002-C — remaining safe sessions/cache/metrics extraction and strict structural/contract coverage completed.

### Completed Work

- Completed extraction of in-memory session clear/history routes through the authoritative application-owned pipeline callback. Session validation order, messages, status codes, snapshots, and TTL fields are unchanged.
- Completed extraction of cache stats, content-free metrics, cache clear, and cache similarity test routes. Configuration gates, rate-limit decorator, threadpool embedding boundary, response rounding, and the mutable telemetry test seam are preserved.
- Added `tests/test_api_router_contracts.py` with the exact ordered 38-route inventory, method/path uniqueness, moved-route module ownership, schema re-export identity, frozen moved-route OpenAPI contract hash, static-before-dynamic evaluation precedence, validation/404 behavior, request-ID preservation, and provider-free execution checks.
- Corrected the initial new-test harness mistake that entered the production lifespan and attempted model initialization. The tests now use the established lifespan-free `TestClient` pattern; the offline socket guard blocked the attempted external connection and no provider request completed.
- Verified the 14 moved endpoints use six coherent router owners and retain the same application route indices.
- Verified Pydantic schemas are imported from the new schema module while remaining available under `src.api.app` for compatibility.
- Verified no router constructs a Qdrant store, embedder, reranker, generator, RAG pipeline, reader, PDF store, or evaluation service. All existing application/domain owners remain singular.
- Measured `src/api/app.py` at 1,933 lines versus 2,249 before API-002, an approximate 316-line / 14% reduction. Reduction was not used to justify moving compatibility-sensitive routes.

### Remaining Work

- API-002-D only: run the complete focused API-002 gate, API-001 security suite, DATA-001 persistence suite, existing API suite, Python compile/import checks, full hermetic backend suite, and Git diff/status/whitespace review; update project state and record the final gate.

### Routes Moved

- Health/configuration: `GET /health/live`, `GET /system/configuration-status`, `GET /health/ready`, `GET /health`.
- Corpus metadata: `GET /supported-tickers`.
- System information: `GET /system/info`.
- Published evaluation reports: `GET /evaluation/runs`, `GET /evaluation/runs/{run_id}`.
- Sessions: `DELETE /session/{session_id}`, `GET /session/{session_id}/history`.
- Cache/metrics: `GET /cache/stats`, `GET /metrics`, `POST /cache/clear`, `POST /cache/test`.

### Routes Intentionally Left

- Query/SSE: `/query`, `/query/decomposed`, `/query/decomposed/stream`, `/query/stream` remain together with sanitization, retrieval normalization, rate limiting, timeout/cancellation, session writes, provider error mapping, and exact SSE event sequencing.
- Retrieval inspection: `/retrieval/inspect` remains with its provider-free pipeline trace behavior; API-005 extensions were not introduced.
- Documents/readers/PDF: `/documents`, `/documents/{document_id}`, `/documents/{document_id}/chunks`, `/chunks/{chunk_id}`, every original/structured reader route, every derived PDF route, and both chunk-location routes remain with the shared indexes, viewer/provenance services, artifact identity, and existing dirty-tree PDF work.

### Files Modified

- `src/api/app.py`
- `src/api/schemas.py`
- `src/api/routers/__init__.py`
- `src/api/routers/health.py`
- `src/api/routers/corpus.py`
- `src/api/routers/system.py`
- `src/api/routers/evaluations.py`
- `src/api/routers/sessions.py`
- `src/api/routers/cache.py`
- `tests/test_api_router_contracts.py`
- `docs/UI_REBUILD_PLAN_CHECKPOINT.md`

No frontend, dependency, configuration, persistence, corpus/index, data, public evaluation artifact, or workspace runtime database file was changed.

### Tests Executed and Exact Results

- First focused router/session/cache command — 16 passed, 2 failed, 51 deselected, 1 warning. Both failures were confined to the new test module entering the production lifespan; the hermetic socket guard blocked a Hugging Face connection attempt and the local Qdrant single-worker lock prevented the second startup.
- Same focused command after adopting the established lifespan-free test pattern — PASS: 18 passed, 51 deselected, 1 pre-existing ReportLab warning in 6.16s.
- Prior API-002-B route/OpenAPI comparison remains PASS: exact 38-route order and exact 14-path OpenAPI operations.

### Known/Pre-existing Failures

The six frozen TEST-001 external integration expectation failures remain pre-existing. The ReportLab deprecation warning remains in the DATA-001 baseline warning set.

### New Regressions

None remaining. The two failed new tests were test-fixture errors, not application contract failures; both were corrected before the passing API-002-C gate.

### Decisions Made

- Freeze the moved OpenAPI operations with a SHA-256 digest generated from the saved pre-extraction contract, alongside readable route/method/order assertions.
- Use the same lifespan-free TestClient pattern as `tests/test_api.py` so ordinary validation remains hermetic and never initializes production models/providers.
- Stop extraction at the six safe router owners. Further movement would combine API-002 with query/SSE, retrieval, provenance, or PDF refactoring and is intentionally deferred.

### Exact Next Action

API-002-D — execute all required focused, security, persistence, existing API, full hermetic, compilation/import, and Git gates; resolve only API-002 regressions, then record the final inventory and select the next task from the saved graph. Do not begin API-003, DATA-002, UI-003, or later work.

## API-002-D Final Checkpoint

### Active Task

API-002 — behavior-preserving incremental extraction of existing FastAPI transport groups. Status: COMPLETE.

### Last Completed Sub-checkpoint

API-002-D — focused, security, persistence, existing API, full hermetic, import/compile, route/OpenAPI, and Git gates passed; final inventory recorded.

### Completed Work

- Completed API-002 as an incremental structural extraction with no new product endpoint or future API schema.
- Kept `src/api/app.py` responsible for FastAPI creation, the single lifespan/bootstrap path, `_state`, middleware, exception handling, limiter/telemetry ownership, router registration, and compatibility-sensitive route glue.
- Moved the existing Pydantic request/response classes to `src/api/schemas.py` and re-exported them through imports in `src.api.app` so current direct imports, harness behavior, validation, serialization, schema names, and generated references remain compatible.
- Registered every router at the exact former route-decorator position. All 38 application routes retain identical path, method, index, endpoint name, and declared status code.
- Verified the saved pre-change OpenAPI operations for all 14 moved paths are exactly equal after extraction.
- Preserved API-001 exactly: liveness keeps the public/provider-free dependency; configuration status keeps the protected local-workspace dependency; loopback, host/origin, bearer-token, forwarded-header, redaction, and execution distinctions continue through the established access module.
- Preserved the one-worker local-Qdrant assumption and avoided all new runtime construction. Router modules contain no vector-store, embedder, reranker, generator, pipeline, reader, PDF store, provider client, or network client construction.
- Preserved exact session, cache, metrics, public-evaluation, build-metadata, CORS, request-ID, validation, error, status, and rate-limit behavior.
- Left all SSE endpoints in `app.py`; their event shapes, ordering, completion/error behavior, timeout/disconnect handling, cancellation, request epochs, and pipeline logic were not refactored.
- Updated README architecture inventory, ARCHITECTURE.md ownership guidance, PROJECT_STATE.md, and this quota-safe checkpoint.
- Inspected the final dirty working tree and scoped diff. All pre-existing frontend, API-001, DATA-001, PDF/workbench, audit, screenshot, and local artifact changes remain present and unreverted. API-002 did not modify any frontend file, dependency manifest, configuration, corpus/index, evaluation artifact, `data/`, or workspace runtime database.

### Remaining Work

API-002 has no remaining work. DATA-002 is the next unfinished item in the saved priority/dependency graph. API-003 and UI-003 were not started.

### Routes Moved

- Health/configuration router: `GET /health/live`, `GET /system/configuration-status`, `GET /health/ready`, `GET /health`.
- Corpus router: `GET /supported-tickers`.
- System router: `GET /system/info`.
- Published-evaluation router: `GET /evaluation/runs`, `GET /evaluation/runs/{run_id}`.
- Session router: `DELETE /session/{session_id}`, `GET /session/{session_id}/history`.
- Cache/metrics router: `GET /cache/stats`, `GET /metrics`, `POST /cache/clear`, `POST /cache/test`.

### Routes Intentionally Left

- `/query`, `/query/decomposed`, `/query/decomposed/stream`, `/query/stream` — kept with sanitization, normalization, shared burst/daily/decomposed limits, pipeline/decomposer ownership, provider error mapping, timeouts, cancellation, session writes, and exact SSE sequencing.
- `/retrieval/inspect` — kept with provider-free retrieval trace construction and authoritative pipeline access; no API-005 behavior was added.
- `/documents`, `/documents/{document_id}`, `/documents/{document_id}/chunks`, and `/chunks/{chunk_id}` — kept with the application-built document/chunk indexes and duplicate-identity behavior.
- `/documents/{document_id}/original`, every `/reader` route, every `/pdf` route, `/chunks/{chunk_id}/original-location`, `/chunks/{chunk_id}/reader-location`, and original content/search — kept with current source revision, provenance, representation, mapping, reader, and PDF artifact ownership. Moving them safely would require a separate identity/service-boundary change beyond API-002.

### Files Modified

- `src/api/app.py` — imports/registers extracted routers and shared schemas; retains bootstrap and compatibility-sensitive routes.
- `src/api/schemas.py` — new stable transport schema module.
- `src/api/routers/__init__.py` — new router package marker.
- `src/api/routers/health.py` — new health/configuration router.
- `src/api/routers/corpus.py` — new supported-ticker router.
- `src/api/routers/system.py` — new allowlisted system-information router.
- `src/api/routers/evaluations.py` — new validated public-report router.
- `src/api/routers/sessions.py` — new in-memory session router and existing validator.
- `src/api/routers/cache.py` — new cache/metrics router.
- `tests/test_api_router_contracts.py` — new structural, ordering, OpenAPI, precedence, provider-free, and header regression coverage.
- `README.md` — updated the source-tree description for the API package.
- `ARCHITECTURE.md` — documented application/router/runtime ownership.
- `PROJECT_STATE.md` — recorded the completed API-002 milestone.
- `docs/UI_REBUILD_PLAN_CHECKPOINT.md` — recorded API-002-A through API-002-D.

### Tests Executed and Exact Results

- Pre-change inventory script — PASS: 38 application routes recorded in order and OpenAPI operations saved for 14 planned moved paths.
- `.venv\\Scripts\\python.exe -m compileall -q src/api` and explicit new-module import smoke — PASS.
- Focused API-002-B health/corpus/system/evaluation gate after correcting late binding — PASS: 13 passed, 79 deselected, 1 warning in 6.94s.
- Focused API-002-C router/session/cache gate after correcting the new test harness — PASS: 18 passed, 51 deselected, 1 warning in 6.16s.
- `.venv\\Scripts\\python.exe -m pytest -q tests/test_api_router_contracts.py` — PASS: 5 passed, 0 failed, 1 warning in 9.15s.
- `.venv\\Scripts\\python.exe -m pytest -q tests/test_workspace_access.py tests/test_trusted_proxy.py` — PASS: 46 passed, 0 failed, 1 warning in 9.41s.
- `.venv\\Scripts\\python.exe -m pytest -q tests/test_workspace_persistence.py` — PASS: 32 passed, 0 failed in 1.13s.
- `.venv\\Scripts\\python.exe -m pytest -q tests/test_api.py` — PASS: 64 passed, 0 failed, 5 warnings in 12.27s.
- `.venv\\Scripts\\python.exe -m pytest -q` — PASS: 858 passed, 0 failed, 188 warnings in 114.20s.
- Final `.venv\\Scripts\\python.exe -m compileall -q src/api tests/test_api_router_contracts.py` — PASS, exit 0.
- Final route/OpenAPI comparison — PASS: 38/38 route registrations equal and 14/14 moved-path OpenAPI operations exactly equal.
- Router dependency scan — PASS: no expensive runtime/provider/network constructors or clients in `src/api/routers/` or `src/api/schemas.py`.
- Final API-002 whitespace scan — PASS: no trailing whitespace in created/modified API-002 source, test, or checkpoint files.
- Final `git diff --check` — PASS (exit 0); output contains only the existing LF-to-CRLF working-copy warnings.
- Final `git status --short` and scoped diff review — completed; the pre-existing dirty tree is preserved and the API-002 files are listed above.

### Baseline Comparison

- DATA-001 baseline: 853 backend tests passed, 0 failed, 188 warnings.
- API-002 final: 858 backend tests passed, 0 failed, 188 warnings.
- Delta: exactly five new API-002 structural contract tests. Existing backend tests all continue to pass and warning count is unchanged.

### Known/Pre-existing Failures

The six frozen TEST-001 external integration expectation failures remain documented and were not promoted into the hermetic backend baseline. All required API-002 backend gates have zero failures. Existing ReportLab, Requests dependency, BeautifulSoup/lxml, and XML-parsing warnings account for the unchanged 188-warning baseline.

### New Regressions

None. During implementation, one supported-ticker monkeypatch seam and two new-test lifespan mistakes were found and corrected. The hermetic network guard blocked the one attempted Hugging Face connection during the erroneous test setup; no external connection or provider call completed, and the final tests do not enter production lifespan.

### Decisions Made

- Stop after extracting the six safe route owners and the existing schema declarations. Do not force query/SSE, retrieval, document, reader, or PDF extraction merely to reduce line count.
- Treat full route order and generated OpenAPI descriptions as compatibility contracts.
- Retain late-bound callbacks for supported-ticker loading and telemetry because the existing tests/harness deliberately replace those owners.
- Keep public evaluation routes read-only and validated; no evaluation jobs, Ragas, or new report contract was introduced.
- Select DATA-002 next because the saved graph orders it immediately after API-002 and its DATA-001 dependency is complete. UI-003 remains blocked on DATA-002.

### Exact Next Action

DATA-002 — implement the planned browser import/repository adapter on top of the completed DATA-001 persistence foundation. Do not begin DATA-002 without a new instruction. Do not begin API-003, UI-003, or any later task as part of API-002.

## DATA-002 Quota-Safe Progress

### Active Task

DATA-002 — recoverable browser-to-SQLite import/export and explicit repository authority foundations. Status: IN PROGRESS.

### Last Completed Sub-checkpoint

DATA-002-A — actual browser schemas, SQLite/import foundation, protected API boundary, migration/export ownership, authority strategy, risks, and exact implementation files inspected and recorded.

### Completed Work

- Re-read the DATA-002 instruction, master-plan persistence/API/task-graph decisions, reference matrix, AGENTS.md, PROJECT_STATE.md, frontend contract, completed API-002 checkpoint, DATA-001 persistence implementation, API-001 access dependency, browser storage code, existing backup validators, and focused tests.
- Confirmed current conversation storage uses schema v4 records in IndexedDB plus a versioned localStorage envelope, durable tombstones, revision-aware merging, writer coordination, answer variants, bookmarks, notes, and complete message/source/document bindings. Legacy v1/v2 conversation inputs remain read-only migration sources and are normalized by the existing loader.
- Confirmed evidence storage supports the actual v1 shape (no `schemaVersion`) and v2 shape, with item notes and exact conversation/message/document/source/revision/hash bindings. Favorites are a separate version-1 localStorage string-ID array. No other versioned research-record browser store exists.
- Confirmed existing legacy backup utilities randomize identities when importing into browser storage, so DATA-002 will introduce a separate portable workspace envelope that preserves source identity and revisions without changing the existing browser-import contract.
- Confirmed DATA-001 provides WAL, foreign keys, serialized writes, bounded busy handling, migrations, generic versioned records/tombstones, and idempotent import receipt storage. DATA-002 will use those tables without adding SQLite schema or implementing DATA-003 domain CRUD.
- Selected one portable envelope with canonical JSON SHA-256 digest, source schema metadata, counts, normalized research records, favorites, tombstones, and unsupported-source descriptors. Export timestamps are metadata and excluded from the deterministic source digest.
- Selected deterministic opaque SQLite IDs derived from backup kind plus legacy ID. Original IDs and payloads remain in an import wrapper so workspace export can reproduce canonical browser semantics and stable mappings.
- Selected explicit conflict rules: exact live duplicates skip; higher workspace revisions win; equal-revision content differences are conflicts; incoming higher live revisions may replace older workspace imports; any existing tombstone prevents record resurrection; a newer incoming tombstone suppresses an older live record.
- Selected a protected router for preview/import/export using the existing API-001 local-workspace dependency. Public mode, non-loopback peers, invalid Host/Origin, and missing/invalid bearer tokens remain denied before database access.
- Selected a frontend authority session contract with explicit `browser` or `sqlite` authority, availability/disconnected state, one writer, no fallback after a failed SQLite write, and no dual write. Existing Chat/Research controllers remain on browser storage until UI-003.

### Remaining Work

- DATA-002-B: implement the versioned frontend backup builder/parser/digest, read-only browser snapshot/favorites helpers, backend envelope validation, non-mutating preview, protected preview/export routes, and focused validation tests.
- DATA-002-C: implement transactional/idempotent import, stable mappings, conflict/tombstone rules, receipts, workspace round-trip export, protected import route, explicit frontend repository authority adapters, and focused rollback/idempotency/authority tests.
- DATA-002-D: run focused security/storage/round-trip tests, API-001, DATA-001, full hermetic backend, frontend storage/full unit/type/build gates, targeted browser storage coverage, Git/diff/artifact checks, and record the final gate.

### Supported Legacy Schemas

- Conversation records: schema v4 canonical records, including revision, notes, bookmarks, answer variants, messages, sources, and document/evidence identity; durable conversation tombstones.
- Evidence collections: v1 (implicit schema) and v2, including evidence item notes and provenance bindings.
- Collection favorites: `sec_qa_collection_stars_v1` string-ID array.
- Legacy conversation v1/v2 inputs are supported through the existing v4 normalization/merge path; unsupported/future or malformed sources remain untouched and are reported rather than silently rewritten.

### Files Modified

- `docs/UI_REBUILD_PLAN_CHECKPOINT.md` — activated DATA-002 and recorded sub-checkpoint A.

Planned DATA-002 implementation files: new `src/workspace/transfer.py`, new `src/api/routers/workspace_transfer.py`, `src/api/app.py`, `src/workspace/__init__.py`, new backend transfer/API tests, new `frontend/src/lib/workspaceBackup.ts` and tests, new `frontend/src/lib/workspaceRepository.ts` and tests, new `frontend/src/lib/collectionFavorites.ts` and tests, minimal export-snapshot additions to `conversationStore.ts` and tests, and a compatibility-only favorite helper import in `CollectionsConsole.tsx`. No package, lockfile, migration, DATA-003 collection CRUD, Chat/Research controller, corpus/index, evaluation artifact, Qdrant, or `data/` file is in scope.

### Tests Run with Exact Results

- No DATA-002 behavioral test has run at sub-checkpoint A. The frozen API-002 backend baseline remains 858 passed, 0 failed, 188 warnings. The frozen UI-002 frontend baseline remains 355 Vitest tests, Chromium 118 passed plus 2 skipped, Firefox 118 passed plus 2 skipped, and reference receipt 15/15.

### Known/Pre-existing Failures

The six frozen TEST-001 integration expectation failures remain pre-existing. No DATA-002 regression exists at sub-checkpoint A.

### New Regressions

None.

### Decisions Made

- Keep browser originals untouched; DATA-002 exposes export/preview/import foundations and never clears or silently migrates IndexedDB/localStorage.
- Keep research content out of telemetry and logs. Validation errors contain bounded structural detail only and never echo imported content or configured secrets.
- Use strict total-size, record-count, identifier, text-size, depth, and secret-field/value validation. Do not accept paths as IDs or deserialize executable types.
- Keep preview read-only after normal explicit local database initialization; it writes neither records nor preview receipts.
- Keep the portable workspace format separate from the existing end-user conversation backup format so legacy browser import behavior remains compatible.

### Exact Next Action

DATA-002-B — implement and test the portable backup/digest/validation boundary plus protected non-mutating preview and export foundations. Do not begin DATA-003, UI-003, API-003, or any later task.

## DATA-002-B Quota-Safe Checkpoint

### Active Task

DATA-002 — recoverable browser-to-SQLite import/export and explicit repository authority foundations. Status: IN PROGRESS.

### Last Completed Sub-checkpoint

DATA-002-B — versioned portable backup, bounded validation/digest, read-only browser capture, protected non-mutating preview, and workspace export foundations implemented and focus-tested.

### Completed Work

- Added the portable `enterprise-document-qa.workspace` version-1 envelope with source schema versions, source counts, export timestamp, deterministic SHA-256 digest, canonical conversation/collection/item records, favorites, tombstones, and unsupported-source descriptors.
- Added strict total-size, count, opaque-ID/path, finite-JSON, depth/node, text-size, source-version, relationship, count, digest, and credential-field/value validation on the backend. The frontend applies the matching portable-envelope and digest boundary without reading any browser-exposed secret configuration.
- Added a read-only conversation export snapshot over the already-loaded/reconciled schema-v4 repository. It exports canonical live records and tombstones without triggering load, reconciliation, migration, deletion, or writes and reports unreadable/future sources without copying their unknown raw bytes.
- Added the actual version-1 collection-favorites storage helper and moved the current Collections console to that helper without changing visible behavior.
- Added browser backup construction for schema-v4 conversations, evidence collection v1/v2 records, item notes, favorites, tombstones, variants, and exact answer/source/document/revision/hash bindings. Existing legacy browser backup/import utilities remain unchanged.
- Added protected `POST /workspace/imports/preview`, `POST /workspace/imports`, and `GET /workspace/export` routes. API-001 authorization runs before service/database access; public mode cannot create/open the local workspace through these routes.
- Added non-mutating SQLite preview reporting supported/unsupported counts, duplicates, conflicts, tombstones, creates, updates, skips, deterministic mappings, digest, and compatibility.
- Added portable workspace export for DATA-002-owned records and safe unsupported counts for non-transfer records; it never exports settings, provider credentials, bearer tokens, telemetry content, or arbitrary workspace payloads.

### Remaining Work

- DATA-002-C: finish cross-runtime digest/round-trip verification, audit import conflict/tombstone behavior and authority state, and complete any corrections exposed by focused tests.
- DATA-002-D: run required backend/frontend full gates, targeted browser storage coverage, artifact/diff/security audits, baseline comparison, project-state update, and final checkpoint.

### Supported Legacy Schemas

Conversation v4; evidence collection v1/v2; collection favorites v1; conversation tombstones v1; notes, bookmarks, variants and source/evidence/document bindings embedded in those supported records. Existing conversation v1/v2 inputs remain handled by the established loader's normalization to v4.

### Files Modified

- `src/workspace/transfer.py`
- `src/workspace/__init__.py`
- `src/api/routers/workspace_transfer.py`
- `src/api/app.py`
- `tests/test_workspace_transfer.py`
- `tests/test_workspace_transfer_api.py`
- `tests/test_api_router_contracts.py`
- `frontend/src/lib/collectionFavorites.ts`
- `frontend/src/lib/collectionFavorites.test.ts`
- `frontend/src/lib/conversationStore.ts`
- `frontend/src/lib/conversationWorkspaceExport.test.ts`
- `frontend/src/lib/workspaceBackup.ts`
- `frontend/src/lib/workspaceBackup.test.ts`
- `frontend/src/lib/workspaceRepository.ts`
- `frontend/src/lib/workspaceRepository.test.ts`
- `frontend/src/components/CollectionsConsole.tsx`
- `docs/UI_REBUILD_PLAN_CHECKPOINT.md`

No dependency manifest, lockfile, migration, DATA-003 collection CRUD, Chat/Research controller, corpus/index, evaluation artifact, Qdrant, or `data/` file was changed.

### Tests Run with Exact Results

- Initial focused backend run exposed one implementation error (`hashlib.compare_digest` instead of `hmac.compare_digest`) and consequently reported 17 failures; the constant-time comparison call was corrected.
- `.venv\\Scripts\\python.exe -m pytest -q tests\\test_workspace_transfer.py tests\\test_workspace_transfer_api.py tests\\test_api_router_contracts.py tests\\test_workspace_access.py tests\\test_workspace_persistence.py` — PASS: 83 passed, 0 failed, 1 warning in 9.11s.
- `bunx vitest run src/lib/workspaceBackup.test.ts src/lib/workspaceRepository.test.ts src/lib/collectionFavorites.test.ts src/lib/conversationWorkspaceExport.test.ts src/lib/conversationStore.test.ts src/lib/evidenceCollections.test.ts src/lib/conversationExport.test.ts src/components/CollectionsConsole.test.tsx` — PASS: 8 files, 76 tests, 0 failed in 2.78s. Expected storage-failure DOMException stderr remains deliberate coverage.
- `bun run lint` — PASS: `tsc --noEmit`, 0 errors.
- `.venv\\Scripts\\python.exe -m compileall -q src\\workspace src\\api` plus import/route smoke — PASS; three workspace transfer routes registered.

### Known/Pre-existing Failures

The six frozen TEST-001 integration expectation failures remain pre-existing. Expected browser-storage DOMException stderr remains deliberate test coverage.

### New Regressions

None in the passing focused gates. The temporary constant-time-comparison implementation error was corrected before this checkpoint.

### Decisions Made

- Digest canonicalization excludes only `exported_at` and `digest`; research identity/content, source schemas, counts, tombstones and unsupported descriptors are digest-bound.
- Preview never inserts a preview receipt. Import receipts are committed only in the same transaction as imported records.
- Portable collection records and evidence-item records are separate so item identity, parent mapping, notes, provenance, and future DATA-003 ownership remain explicit.
- Unknown raw browser bytes are left in place and represented by bounded metadata only; they are not copied into a trusted portable record.

### Exact Next Action

DATA-002-C — complete the transactional/idempotent import and one-writer repository-authority gate, including cross-runtime digest and round-trip checks. Do not begin DATA-003, UI-003, API-003, or later work.

## DATA-002-C Quota-Safe Checkpoint (activation + audit)

### Active Task

DATA-002 — recoverable browser-to-SQLite import/export and explicit repository authority foundations. Status: IN PROGRESS.

### Last Completed Sub-checkpoint

DATA-002-C-A — activation audit completed; stale header reconciled; no source changed yet.

### Completed Work

- Re-read the DATA-002-C instruction, master-plan persistence/API decisions, AGENTS.md, frontend contract, DATA-002-B checkpoint, `src/workspace/transfer.py` (976 lines), `src/workspace/repository.py`, `src/workspace/database.py`, `src/api/routers/workspace_transfer.py`, `src/api/access.py`, `frontend/src/lib/workspaceBackup.ts`, `frontend/src/lib/workspaceRepository.ts`, and the existing DATA-002-B tests.
- Confirmed DATA-002-B already implements: single-transaction import with digest-bound idempotent receipt (`workspace_imports` lookup), plan-based actions (create / replace_older / duplicate / conflict / blocked_by_tombstone / tombstone_create / tombstone_replace / tombstone_duplicate / tombstone_conflict), full rollback via `WorkspaceDatabase.transaction` (`except BaseException: rollback`), deterministic `stable_legacy_id` mapping, secret-field/value rejection, and protected preview/import/export routes. Existing tests already cover: validation, idempotent repeat import, injected-failure rollback, duplicate/conflict/newer-revision preview+import, tombstone preservation/no-resurrection, import→export→import round trip, secret rejection, and API-001 access protection (404 public / 401 missing token / 403 non-loopback).
- Audit findings to close in C (not yet implemented):
  1. Cross-runtime digest: Python `json.dumps(sort_keys=True)` orders keys by Unicode code point, while the TS `canonicalWorkspaceJson` sorts object keys with `Array.prototype.sort()` (UTF-16 code units); these diverge when payload object keys mix astral-plane characters with U+E000–U+FFFF characters. Python emits integral floats as `5.0`/`1e+21`/`1e-07` while ECMAScript `JSON.stringify` emits `5`/`1e+21`/`1e-7`; Python emits non-integer floats with up to 17 significant digits while ECMAScript uses shortest-round-trip. A backup containing a lone surrogate escape parses in both runtimes but crashes Python `compute_backup_digest` with `UnicodeEncodeError` (unhandled 500) while TS silently replaces it with U+FFFD; integers above 2^53 lose exactness in JS.
  2. Canonical record ordering: TS `createWorkspaceBackup` orders records with `localeCompare` (locale-collation dependent) while Python `build_workspace_backup` orders with code-point `sorted`; one canonical ordering must be defined.
  3. Focused tests still missing: deterministic legacy-ID mapping across independent databases, foreign/non-owned existing record classified as conflict without overwrite (the incomparable-revision case), conflicting import must not regress a newer authoritative record, export `unsupported` accounting for non-portable rows, unpaired-surrogate fail-closed behavior, cross-runtime digest fixtures, HTTP-level idempotent receipt, and additional authority-gate cases (constructor availability check, write-time availability check, accumulated unsaved operations/deep-copy export, concurrent single-writer dispatch, explicit re-switch after disconnect).
- Reconciled the stale top-level header (was: "UI-002 is ACTIVE … API-002 has not started") to reflect the true state; historical task receipts below are unchanged.

### Remaining Work

- DATA-002-C implementation: define and apply the one canonical representation (code-point key ordering on both runtimes, ECMAScript-compatible number serialization, fail-closed unpaired surrogates, canonical record ordering) without weakening validation; add all missing focused backend/frontend/cross-runtime/round-trip tests; run focused validation; record receipts.
- DATA-002-D: final full gates (separate sub-checkpoint; not started).

### Files Modified

- `docs/UI_REBUILD_PLAN_CHECKPOINT.md` — reconciled the stale header and recorded this activation checkpoint.

No source, test, dependency, lockfile, or `data/` file has been changed by DATA-002-C so far. Baselines: backend 876 passed / 0 failed / 188 warnings; frontend 367 Vitest tests passing, TypeScript clean.

### Tests Run with Exact Results

- None in DATA-002-C yet. The takeover audit already measured the full hermetic suite this session: backend `pytest -q` 876 passed / 0 failed / 188 warnings; frontend `bun run test` 69 files / 367 tests passed; `bun run lint` clean.

### Known/Pre-existing Failures

The six frozen TEST-001 integration expectation failures remain pre-existing and untouched.

### New Regressions

None.

### Decisions Made (provisional, to be finalized by the C receipt)

- One canonical representation for the v1 portable format: object keys ordered by Unicode code point; numbers serialized with ECMAScript `Number::toString` semantics (integral floats as integers; shortest-round-trip non-integers); unpaired surrogates rejected fail-closed on both runtimes; records/favorites/tombstones ordered by code-point comparison of their identifiers. All real DATA-002-B backups (ASCII identifiers, integral counts/timestamps/revisions, provider-produced float scores) remain digest-identical under these rules.
- The shared deterministic fixture lives once at `tests/fixtures/workspace_transfer_roundtrip.json` and is read by both pytest and Vitest; it carries the browser-side backup envelope, the expected cross-runtime digest, and the Python-side export envelope.

### Exact Next Action

DATA-002-C-B — implement the canonical representation changes (backend transfer guard + frontend canonicalization/ordering) and the missing transactional/idempotency/conflict/tombstone focused tests, then checkpoint again before running focused validation.

## DATA-002-C0 Quota-Safe Checkpoint (recovery + partial C-B verification)

### Active Task

DATA-002 — recoverable browser-to-SQLite import/export and explicit repository authority foundations. Status: IN PROGRESS (C active).

### Current Stage

DATA-002-C0 — state recovered after an interrupted prior session; partial DATA-002-C-B work identified and verified.

### Last Completed Action

Ran the existing DATA-002-B focused gate after recovering the interrupted session: `.venv\Scripts\python.exe -m pytest -q tests\test_workspace_transfer.py tests\test_workspace_transfer_api.py tests\test_workspace_persistence.py tests\test_workspace_access.py tests\test_api_router_contracts.py` — PASS: 83 passed, 0 failed, 1 warning in 29.25s.

### Recovered State (uncheckpointed prior work, now owned by C)

- `src/workspace/transfer.py` (mtime 2026-09-19 23:16) already implements the C10 backend canonical representation: `_js_number_text` ECMAScript number serialization, `_emit_canonical`/`_canonical_json` with Unicode-code-point key ordering, fail-closed unpaired-surrogate rejection in `compute_backup_digest`/`_validate_json_tree`, and the safe-integer (2^53-1) guard.
- `frontend/src/lib/workspaceBackup.ts` (mtime 2026-09-19 23:16) already implements the matching frontend canonicalization: `compareUnicodeCodePoints` (replacing `localeCompare`/UTF-16 ordering for object keys and record ordering), `canonicalWorkspaceJson`, fail-closed `UNPAIRED_SURROGATE` validation, and the same safe-integer guard.
- The prior session was interrupted before writing the C-focused tests, the shared fixture, or a checkpoint for that edit burst; this checkpoint claims the recovered work.

### Completed Work

- Verified the uncheckpointed canonicalization edits pass the existing DATA-002-B focused gate (83 passed above).
- Re-read the C-A findings list and mapped each finding to its remaining artifact.

### Remaining Work (exact)

1. Shared deterministic fixture `tests/fixtures/workspace_transfer_roundtrip.json` (three backups: minimal; Vietnamese/Unicode + nested metadata with integral floats, 1e-7-scale numbers, and astral-versus-U+E000 keys; revision/tombstone/evidence identity) read by both pytest and Vitest.
2. Backend focused module `tests/test_workspace_transfer_canonical.py`: cross-runtime fixture digests, deterministic legacy-ID mapping across independent databases, foreign/non-owned record conflict without overwrite, no regression of a newer authoritative record, export `unsupported` accounting, unpaired-surrogate fail-closed, ECMAScript number-serialization units.
3. HTTP-level idempotent receipt and unpaired-surrogate 400 tests in `tests/test_workspace_transfer_api.py`.
4. Frontend focused tests: fixture digest via canonical JSON, code-point ordering divergence (astral vs U+E000), unpaired-surrogate rejection, integral-float canonical form; authority-gate cases (constructor availability, write-time availability, accumulated unsaved/deep-copy export, concurrent single-writer dispatch, explicit re-switch after disconnect, browser-failure non-disconnect semantics).
5. Focused validation (backend + frontend), then C1-C6 receipt stages and the C final gate.

### Files Modified So Far (C0)

- `docs/UI_REBUILD_PLAN_CHECKPOINT.md` (this checkpoint; top header reconciled).

### Tests Run with Exact Results

- Backend focused gate: 83 passed, 0 failed, 1 warning in 29.25s (command above).
- No new C tests exist yet; no frontend tests run in C0 yet.

### Known/Pre-existing Failures

- The six frozen TEST-001 integration expectation failures remain pre-existing and untouched.

### New Regressions

- None.

### Decisions Made

- The uncheckpointed 2026-09-19 23:16 canonicalization edits are treated as valid DATA-002-C-B partial work after the focused gate passed; they are checkpointed here instead of being re-derived.
- C1-C6 stage receipts will be appended incrementally as each stage completes and validates.

### Exact Next Action

Create the shared fixture and the backend focused canonical test module, then run them before touching the frontend tests.

## DATA-002-C Quota-Safe Checkpoint (C1-C6 implementation + focused validation)

### Current Stage

C6 complete. DATA-002-C implementation and focused validation are done; only the C final gate audit remains.

### Completed Work (by stage)

- C1 transactional import/rollback: the digest-bound single-transaction import with plan-based actions and full rollback is covered by the DATA-002-B rollback and idempotency tests; the recovered canonicalization edits preserved them (all 83 B focused tests pass).
- C2 mapping/idempotency/conflict/revision/tombstone: `tests/test_workspace_transfer_canonical.py` adds deterministic legacy-ID mapping across independent databases, foreign/non-owned record conflict without overwrite, no-regression of a newer authoritative record, non-portable export accounting, and revision-deterministic tombstone semantics (older tombstone conflicts with newer live; newer tombstone deletes older live).
- C3 repository authority/one-writer: `frontend/src/lib/workspaceRepository.test.ts` adds constructor-availability, write-time-availability (no writer call, no unsaved record), browser-failure non-disconnect semantics, unsaved accumulation with deep-copy export, concurrent single-writer dispatch ordering, and explicit re-switch after disconnect.
- C4 cross-runtime canonical digest: shared deterministic fixture `tests/fixtures/workspace_transfer_roundtrip.json` (minimal; Vietnamese/Unicode + nested metadata with integral floats, 1e-7 exponents, astral-vs-U+E000 keys, safe-integer bound; revision/tombstone/evidence identity) is read by both pytest and Vitest. Python's `compute_backup_digest` reproduces each stored digest, and the TypeScript canonicalizer reproduces the same digests from the same envelopes, so any future drift fails one side.
- C5 round-trip: the B round-trip test plus the fixture identity tests confirm semantic preservation of conversation/message/variant/evidence/source/document/favorite/tombstone identities.
- C6 focused validation: results below.

### Implementation Detail (canonical representation, recovered + completed)

- Recovered from the interrupted 2026-09-19 23:16 session and now checkpointed: Python `_js_number_text` (ECMAScript number serialization), `_emit_canonical`/`_canonical_json` (code-point key ordering), fail-closed unpaired surrogates; TypeScript `compareUnicodeCodePoints` key/record ordering (replacing `localeCompare`), `canonicalWorkspaceJson`, fail-closed `UNPAIRED_SURROGATE`, safe-integer guard.
- Completed in this session: Python `_validate_json_tree` now rejects floats at or above 2^53 like the TypeScript validator (every double at or above 2^53 is integral and unsafe), so both runtimes accept exactly the same numbers.

### Files Created

- `tests/fixtures/workspace_transfer_roundtrip.json`
- `tests/test_workspace_transfer_canonical.py` (23 tests)

### Files Modified

- `src/workspace/transfer.py` (float safe-range parity guard; canonicalization itself was the recovered C-B work)
- `tests/test_workspace_transfer_api.py` (conversation helper; HTTP idempotent-receipt and unpaired-surrogate-400 tests; `_request` content passthrough)
- `frontend/src/lib/workspaceBackup.test.ts` (fixture digest, code-point ordering, ECMAScript number contract, surrogate rejection)
- `frontend/src/lib/workspaceRepository.test.ts` (six authority-gate tests)
- `docs/UI_REBUILD_PLAN_CHECKPOINT.md` (C0 and this receipt; top header reconciled)

### Tests Run with Exact Results

- Backend focused gate: `.venv\Scripts\python.exe -m pytest -q tests\test_workspace_transfer_api.py tests\test_workspace_transfer_canonical.py tests\test_workspace_transfer.py tests\test_workspace_persistence.py tests\test_workspace_access.py tests\test_api_router_contracts.py` — PASS: 108 passed, 0 failed, 1 warning in 7.82s.
- Frontend focused gate: `bunx vitest run src/lib/workspaceBackup.test.ts src/lib/workspaceRepository.test.ts src/lib/conversationStore.test.ts src/lib/conversationStore.snapshot.test.ts src/lib/collectionFavorites.test.ts src/lib/conversationExport.test.ts src/lib/evidenceCollections.test.ts src/components/CollectionsConsole.test.tsx src/lib/conversationWorkspaceExport.test.ts` — PASS: 9 files, 98 tests, 0 failed.
- `bun run lint` (`tsc --noEmit`) — PASS, 0 errors.
- `.venv\Scripts\python.exe -m compileall -q src tests` — PASS.

### Known/Pre-existing Failures

- The six frozen TEST-001 integration expectation failures remain pre-existing and untouched.

### New Regressions

- None.

### Decisions Made

- Digests in the shared fixture are produced by the Python canonicalizer; the TypeScript side must (and does) reproduce them, making the fixture a drift detector instead of two independently hardcoded expectations.
- Unpaired surrogates and unsafe numbers fail closed on both runtimes; the HTTP contract returns 400 with a structural message.
- `exported_at` deliberately stays in the TypeScript digest payload input so the test proves the digest excludes it.

### Exact Next Action

Run the DATA-002-C final gate (git status/diff/diff --check audit), mark DATA-002-C COMPLETE, then continue automatically into DATA-002-D full gates.

## DATA-002-D0 Quota-Safe Checkpoint (C verified complete; final gate plan)

### Active Task

DATA-002 (D active). DATA-002-C is COMPLETE per the C1-C6 receipt above; `git diff --check` exited clean (only pre-existing CRLF notices).

### Final Gate Plan (exact commands, run in this order)

1. D1 backend: `.venv\Scripts\python.exe -m pytest -q` — expect 901 passed (876 baseline + 25 new focused C tests), 0 failed, 188 warnings.
2. D2 frontend: `bun run lint`, `bun run test` — expect 379 passed (367 baseline + 12 new C tests), `bun run build`.
3. D3 browser: `VITE_API_BASE_URL=http://127.0.0.1:8000 bun run test:e2e -- --workers=1 --retries=0` (Chromium + Firefox; UI-002 baseline 118 passed / 2 intentional skips each) then the nine-reference receipt `bunx playwright test reconciliation-reference.spec.ts --project=chromium --workers=1` (baseline 15/15).
4. D4 audits: security/storage/artifact/diff.
5. D5 documentation: checkpoint + PROJECT_STATE.md.

If quota ends mid-gate, the next agent resumes from the last recorded gate result; completed gates are never re-run.

## DATA-002-D1 Quota-Safe Checkpoint (backend final gate)

### Completed Work

- Full hermetic backend suite: `.venv\Scripts\python.exe -m pytest -q` — PASS: 901 passed, 0 failed, 188 warnings in 76.75s.
- Baseline comparison: 876 → 901 passed (+25 = 23 canonical + 2 API focused tests), 0 failed, warnings unchanged at 188.

### Exact Next Action

D2 frontend gates: `bun run lint`, `bun run test`, `bun run build`.

## DATA-002-D2 Quota-Safe Checkpoint (frontend final gate)

### Completed Work

- `bun run lint` (`tsc --noEmit`) — PASS, 0 errors.
- `bun run test` — PASS: 69 files, 379 tests, 0 failed (367 baseline + 12 new DATA-002-C tests).
- `bun run build` — PASS: production bundle built in 7.18s.

### Exact Next Action

D3 browser gates (long-running): rebuild with `VITE_API_BASE_URL=http://127.0.0.1:8000` baked in, then `bun run test:e2e -- --workers=1 --retries=0` (Chromium + Firefox, UI-002 baseline 118 passed / 2 intentional skips each), then `bunx playwright test reconciliation-reference.spec.ts --project=chromium --workers=1` (nine-reference receipt, baseline 15/15). If quota ends before D3 completes, the browser gate result is UNKNOWN and must be re-run; D1/D2 results above stand.

## DATA-002-D3/D4 Quota-Safe Checkpoint (browser, reference, and audit gates)

### D3 Browser Results

- Combined first run (`VITE_API_BASE_URL=http://127.0.0.1:8000 bun run test:e2e -- --workers=1 --retries=0`): 234 passed, 2 failed, 4 skipped in 8.4m. Both failures were Firefox-only (`regression.spec.ts:65` evidence inspector; `workspace-layout.spec.ts:305` layout matrix A-G); Chromium was fully green (118 passed / 2 intentional provider-dependent skips).
- Investigation per the goal: focused Firefox rerun of both tests — PASS (2/2, 22.8s). Full Firefox project rerun — PASS: 118 passed, 2 skipped in 4.4m. The two failures are the documented pre-existing timing-sensitive full-suite Firefox class (TEST-001: "focused rerun passes"); DATA-002-C changed no page-render code, and no test was modified to hide anything.
- Final browser state matches the frozen UI-002 baseline: Chromium 118 passed / 2 skipped; Firefox 118 passed / 2 skipped.
- Nine-reference receipt: `bunx playwright test reconciliation-reference.spec.ts --project=chromium --workers=1` — PASS: 15/15.

### D4 Audit Results

- Security: public mode returns 404/404/404 for preview/import/export (`test_public_mode_cannot_preview_import_or_export_private_workspace`); missing token 401 and remote peer 403 with Forwarded headers ignored (`test_local_routes_require_api001_token_and_loopback`); secret-looking keys and configured credential values rejected by `_validate_json_tree`/`validateJsonTree` on both runtimes; transfer errors are structural (`_safe_transfer_error`); import receipts carry mappings/counts only (no research payload). Unpaired surrogates and unsafe numbers fail closed with HTTP 400. No provider credentials, workspace token, or research content in backups, logs, or telemetry. No executable deserialization anywhere (pure JSON). Imported IDs can never be filesystem paths (path-segment rejection tests).
- Storage: browser originals intact — no DATA-002 code path writes browser storage; conversation schema v4, evidence collections v2, favorites v1, tombstones, and answer-variant/evidence/source/document identities are the only supported formats and are validated fail-closed.
- Artifacts: repository scan found no stray workspace.sqlite3/WAL/SHM, no test DBs, no debug dumps (tests use `tmp_path`; no `.local/` was created; public mode never opens the database).
- Diff: DATA-002 session changes are limited to `src/workspace/transfer.py` (float safe-range guard), `tests/fixtures/workspace_transfer_roundtrip.json` (new), `tests/test_workspace_transfer_canonical.py` (new), `tests/test_workspace_transfer_api.py` (helper + 2 tests), `frontend/src/lib/workspaceBackup.test.ts` and `frontend/src/lib/workspaceRepository.test.ts` (new tests), plus checkpoint/PROJECT_STATE documentation. No dead debug code, no fake data, no dependency or lockfile change by DATA-002 (zero new dependencies; bun.lock/requirements.txt untouched this session).

### Exact Next Action

D5 documentation: PROJECT_STATE.md entry; then D6 DATA-002 COMPLETE and next-task selection from the master graph.

## DATA-002-D5/D6 Final Checkpoint (documentation + DATA-002 COMPLETE)

### Completed Work

- PROJECT_STATE.md gained the newest entry "DATA-002 workspace import/export completion (2026-09-20)" with the canonical-representation contract, focused-coverage inventory, all gate results, and the next-task decision.
- This checkpoint document carries the full quota-safe receipt trail: C0 (recovery), C1-C6 (implementation + focused validation), D0-D4 (gate plan, backend, frontend, browser/reference/audits), and this D5/D6 close-out.
- Dependency audit: DATA-002 added zero dependencies (no package.json, bun.lock, or requirements.txt change).
- Supported browser storage formats verified as they really exist: conversation schema v4 (IndexedDB `enterprise-document-qa` v2 + localStorage mirror `sec_qa_library_v3`), evidence collections v2, collection favorites v1, conversation tombstones, and answer-variant/evidence/source/document identity fields inside records. No legacy format is claimed beyond these.

### Task Status

DATA-002 COMPLETE (sub-checkpoints A, B, C, D).

### Final Receipt Counts

- Backend: 901 passed / 0 failed / 188 warnings (baseline 876 + 25).
- Frontend Vitest: 69 files / 379 passed / 0 failed (baseline 367 + 12); `tsc --noEmit` clean; production build passed.
- Chromium: 118 passed / 2 intentional skips / 0 failed. Firefox: 118 passed / 2 intentional skips / 0 failed (after the documented timing-sensitive first-run investigation).
- Nine-reference receipt: 15/15 passed. `git diff --check`: clean.

### Known/Pre-existing Issues (unchanged)

- Six frozen TEST-001 integration expectation failures in `frontend/e2e/integration.spec.ts`.
- The timing-sensitive full-suite Firefox class documented by TEST-001 (observed once in D3; focused and full-rerun both pass).

### New Regressions

- None.

### Exact Next Action

UI-003 — Chat/Research conversation pages and hooks (dependencies UI-002 and DATA-002 are satisfied; it is the first dependency-ready task in the master-plan priority ordering). API-003 and DATA-003 are also dependency-ready. Do not start UI-003 without explicit user authorization.

## UI-003-A Quota-Safe Checkpoint (recovery, ownership map, reference mapping)

### Active Task

UI-003 — Chat/Research conversation pages and hooks (dependencies UI-002 + DATA-002 satisfied).

### Current Stage

A complete — recovery, ownership mapping, reference identification, and file plan recorded. No source changed yet in UI-003.

### Verified Current State (repository evidence)

- DATA-002 COMPLETE per the D5/D6 receipts; checkpoint header names UI-003 as the next dependency-ready task; git HEAD 3464793 with the intentionally dirty rebuild tree (160 paths).
- Route model (`frontend/src/app/routes.ts`): `/chat` and `/chat/:conversationId` resolve to workspaceView `conversation`; `/research` root resolves to `overview` (with `?mode=conversation` override); `routeForWorkspaceView("conversation", { currentRouteId })` already preserves the chat/research family. Legacy root translation and evidence-hash preservation are covered by `routes.test.ts` and `e2e/ui-routing.spec.ts`.
- Conversation composition is an inline block in `App.tsx` (~lines 2480-2628): a hardcoded "Research" header for BOTH families, the `ChatMessage` thread (already reconstructed to the references on 2026-09-15: badges, citations, action rows, execution stages, variants, feedback, notes), a follow-up chips strip, and the shared `ChatInput` composer (scope + comparative/decomposition controls already exist and map to the reference's "Deep Research" intent).
- Domain controllers stay authoritative: `useConversationLibrary` (browser authority: IndexedDB v4 + writer lock + storageMode/writerStatus/saveIndicator), `useAnswerActions`, `useResearchSession`, stage events, `handleSendMessage` capturing `RequestSnapshot` (ticker/section/topK/comparative/language — but NOT mode today).
- `ConversationRecord` has NO mode field; no conversation/request captures chat-vs-research mode today. This is the primary functional gap vs master plan section 7 ("Conversations share mode chat or research … Requests capture mode and submitted scope").
- DATA-002 authority contract at runtime: browser repository is the only writer; the SQLite workspace is reachable only through the protected local-mode import/export routes; no dual-write path exists. UI-003 must preserve this.

### Reference Mapping (authoritative local screenshots)

- Chat → `docs/ui-references/rag-workbench-master-reference-dark.png` (1254x856): left workbench rail; chat thread with assistant answer card (badge, citations, action row); Pipeline Execution stages panel; composer with scope + hybrid/deep-research controls; Sources pane + Document Viewer (source/document composition remains UI-004 scope).
- Research → `docs/ui-references/research-ui-reference-dark-v1.png` (1586x992): ~200px nav / 620 research / 340 sources / 420 reader; serif filing answers with amber citation highlights; Follow-up tiles; Insights metric tiles; Related Questions.
- Fake reference elements to OMIT (truthful-UI policy): GPT-4o/model selector, Web search toggle, Users/API Keys, Upgrade CTA, storage-quota meter, account/profile, confidence scores. Real equivalents that DO exist and may be surfaced: model_used label, stage events, citation counts, retrieved-chunk counts, answer language, decomposition flag.

### Implementation Plan (exact files)

1. `frontend/src/types.ts`: add `ConversationMode = "chat" | "research"`; optional `RequestSnapshot.mode`.
2. `frontend/src/lib/conversationStore.ts`: optional `ConversationRecord.mode` (schemaVersion stays 4; DATA-002 payload validator permits extra optional keys — verified against `src/workspace/transfer.py` conversation validation which checks required fields, not exact payload keys).
3. `frontend/src/components/conversation/ConversationPageHeader.tsx` (new): mode-aware header extracted from the inline block (Chat: compact/direct; Research: research header + History).
4. `frontend/src/components/conversation/FollowUpTiles.tsx` (new): research-mode follow-up tiles (reference tile geometry); chat keeps compact chips.
5. `frontend/src/components/conversation/ResearchInsightsRow.tsx` (new): real-fields-only insight tiles (citations count, retrieved chunks, model used, answer language) from the latest completed assistant message; hidden when no completed answer exists.
6. `frontend/src/components/conversation/ConversationPageShell.tsx` (new): page shell owning header + scroll structure + follow-ups + composer slot; receives the thread as children so App.tsx keeps domain/answer-action wiring; accepts scroll refs.
7. `App.tsx`: replace the inline conversation block with `ConversationPageShell`; capture mode at send time into `requestSnapshot.mode` and stamp `conversation.mode`; conversation selection navigates to the stored mode's family (route family wins for presentation when no stored mode).
8. `frontend/src/lib/i18n.tsx`: en/vi labels for new surfaces.
9. Tests: focused unit tests for the three new components + mode resolution; `App`-level mode capture/no-regeneration assertions; new hermetic browser spec `frontend/e2e/ui-003-conversation-modes.spec.ts` (chat vs research presentation, no duplicate stream requests on family navigation, follow-up tile fills composer without submitting).

### Stitch Strategy

Stitch MCP is available; one bounded candidate-generation attempt will be made for the Research composition (insights row + follow-up tiles arrangement) before implementation. The local screenshots remain the authority; any Stitch scaffold is compared and then re-implemented with project primitives (UI-001 tokens, existing reconstructed design system). If Stitch is slow/unavailable, proceed from screenshots (goal permits).

### Tests Run with Exact Results

- None yet in UI-003 (read-only recovery).

### Known/Pre-existing Failures

- Six frozen TEST-001 integration expectation failures; timing-sensitive Firefox full-suite class. Unchanged.

### Exact Next Action

Attempt the bounded Stitch candidate for Research composition, then implement the mode model + new conversation components (files 1-8) and focused unit tests.

## UI-003-B/C/D Quota-Safe Checkpoint (Chat + Research composition, mode model, integration)

### Current Stage

B, C, and D complete. E (visual comparison) is the active sub-checkpoint.

### Completed Work

- Mode model: `ConversationMode = "chat" | "research"` added to `types.ts`; `RequestSnapshot.mode` optional; `ConversationRecord.mode` optional (schema stays 4); `conversationModeFromMessages` derives the mode from the first submitted request; `buildConversationRecord` precedence is explicit input → existing record → stored messages, so a conversation keeps its started mode across later saves. Strict normalization rejects an unknown mode value instead of coercing it. `recordFingerprint` includes mode so a merge cannot silently drop it.
- Route family: `routeForWorkspaceView` accepts an explicit `family`; `navigateWorkspaceRoute` takes an optional family; conversation-select, evidence deep-link, open-message, open-variant, and continue-research paths all reopen in the stored conversation's family. New conversation: chat start lands on `/chat`, research start keeps `/research`.
- New components under `frontend/src/components/conversation/`: `ConversationPageHeader` (mode-aware identity + New Chat/New Research + History; the reference's dead overflow button is deliberately not shipped), `ResearchInsightsRow` (tiles only from real answer fields; retrieval score is labelled a retrieval score), `FollowUpTiles` (research tiles, chat chips; selection only fills the composer), `ConversationPageShell` (header + scroll + insights + follow-ups + composer slot; App keeps the thread, request, evidence, and scroll ownership).
- `App.tsx`: inline conversation block replaced by the shell; `latestCompletedAnswer` memo feeds both follow-ups and insights; mode is stamped into `requestSnapshot` at send time; mode-aware empty states.
- Styles: `console.css` gained conversation follow-up tile, insight tile, and mobile grid rules.
- i18n: 16 new en/vi keys.

### Tests Run with Exact Results

- `bun run test` — PASS: 70 files / 397 tests (379 baseline + 18 new: 11 component, 3 store, 4 App).
- `bun run lint` (`tsc --noEmit`) — PASS, 0 errors.

### Verified Invariants (focused tests)

- Chat and Research render distinct compositions on their routes; the stored mode wins over a mismatched URL family.
- A question asked on `/chat` stores `mode: "chat"` in both the message request snapshot and the conversation record.
- Opening a stored conversation from the Library navigates to its own family and issues no stream/decomposed request (no regeneration).

### Remaining Work

- E: rendered visual comparison against `rag-workbench-master-reference-dark.png` (Chat) and `research-ui-reference-dark-v1.png` (Research) at the target viewports; responsive and accessibility checks.
- F: full validation gate (build, Chromium + Firefox suites, nine-reference receipt, diff audit, docs).

### Exact Next Action

Build the production bundle with the fixture API base URL and capture Chat/Research screenshots at 1440x900, 1280x856, 1024x768, and 390x844 for comparison.

## UI-003-E Quota-Safe Checkpoint (visual comparison, responsive, composer truthfulness)

### Completed Work

- Composer truthfulness (UI-003 owns the composer): removed two dead controls that only existed to mirror the reference — the `Web` search button (no web capability exists) and the `Attach document` paperclip (no handler). `Hybrid Search` is now a static badge describing the real BM25+dense+RRF+rerank stack instead of a dead dropdown.
- Header: subtitle yields below 640px so the mode title is never truncated; title/subtitle/icon switched from dark-only literals to semantic tokens after the rendered light-theme capture showed the title invisible (`text-white` on a token-aliased light surface). This was a real defect caught by the render-then-look gate, not a cosmetic preference.
- New hermetic browser spec `frontend/e2e/ui-003-conversation-modes.spec.ts` (7 tests, Chromium): route composition, chat streaming keeps chat composition, research insight tiles + follow-up composer-only behavior, and per-viewport receipts with a body/root horizontal-overflow assertion.
- Receipts captured at 1440x900, 1280x856, 1024x768, and 390x844 (chat empty, chat answer, research answer, research insights) under the git-ignored `frontend/test-results/ui-003/`.

### Visual Comparison Result (vs the authoritative local references)

- Research (`research-ui-reference-dark-v1.png`): accent identity tile + mode title + subtitle + New Research/History header; question card with scope caption; answer card with Answer badge, source count/duration meta, inline canonical citations, secondary citation markers, action row (sources/Copy/Regenerate/Add to notes/More/thumbs); Pipeline Execution stage panel with total duration; follow-up tile strip; composer with scope + retrieval badge + Deep Research switch. Matches the reference composition; the reference's right-hand Sources/Document region is UI-004 ownership and is not claimed here.
- Chat (`rag-workbench-master-reference-dark.png`): direct mode title and New Chat action, same thread composition, compact follow-up chips rather than research tiles, empty state with sample questions.
- Justified deltas: no model selector, Web toggle, attachments, account, storage meter, upgrade CTA, or confidence scores (capabilities that do not exist); Insights tiles appear only with real values, at the end of the thread.
- Responsive: no body/root horizontal overflow at any of the four widths; mobile header keeps the mode title readable; follow-up tiles collapse to two columns; drawer/composer remain usable.

### Tests Run with Exact Results

- `bunx playwright test e2e/ui-003-conversation-modes.spec.ts --project=chromium --workers=1 --retries=0` — PASS: 7 passed.
- `bunx vitest run src/components/ChatInput.test.tsx` — PASS: 3 passed after the composer cleanup.

### Remaining Work

- F: production build, full Chromium and Firefox suites, nine-reference receipt, diff/artifact audit, documentation, then UI-003 COMPLETE.

### Exact Next Action

Run the frontend unit suite and typecheck, then the production build, then the full Chromium suite (long-running; checkpoint recorded before starting).

## UI-003-F1 Quota-Safe Checkpoint (unit, build, Chromium)

### Completed Work

- `bun run lint` (`tsc --noEmit`) — PASS, 0 errors.
- `bun run test` — PASS: 70 files / 397 tests (379 baseline + 18 new).
- `bun run build` — PASS (production bundle, 3.20s).
- Full Chromium suite (`VITE_API_BASE_URL=http://127.0.0.1:8000 bunx playwright test --project=chromium --workers=1 --retries=0`) — PASS: 125 passed, 2 intentional skips, 0 failed (3.9m). Baseline was 118 passed / 2 skipped; the +7 is the new UI-003 spec.

### Exact Next Action

Run the full Firefox suite (long-running; checkpoint recorded before starting), then the nine-reference receipt, then the diff/artifact audit and documentation.

## UI-003-F2 Quota-Safe Checkpoint (Firefox, reference receipt, audits, Stitch outcome)

### Browser Gates

- Full Chromium suite — PASS: 125 passed, 2 intentional skips, 0 failed (3.9m). Baseline 118/2; +7 = new UI-003 spec.
- Full Firefox suite, first run — 124 passed, 1 failed, 2 skipped. The failure was `regression.spec.ts:65` (evidence inspector remaining-width mode).
- Investigation per protocol: the exact focused test failed once and then passed three consecutive focused runs; all selectors it depends on (`.conversation-message-scroll`, `.composer-shell`, `.message-answer-layout`, `#sidebar-toggle`, evidence-inspector dialog) are preserved by the UI-003 shell, and the same test failed once in the DATA-002-D3 run before any UI-003 change. This is the frozen TEST-001 timing-sensitive Firefox inspector class, not a UI-003 regression.
- Full Firefox rerun — PASS: 125 passed, 2 intentional skips, 0 failed (5.5m).
- Nine-reference non-regression receipt (`reconciliation-reference.spec.ts --project=chromium`) — PASS: 15/15, matching the frozen baseline exactly.

### Stitch Usage and Outcome

- Stitch MCP was used as authorized: a UI-003 probe project ("EDQA UI-003 Research Composition Probe") was created and a bounded generation was requested for the follow-up/insights/related composition. The generation call timed out at the MCP boundary and completed server-side afterward (one screen, "Research Workbench Column"); its HTML download URL returned HTTP 400 to an unauthenticated fetch, so no Stitch scaffold was imported into the repository.
- Result: the implementation was built from the authoritative local screenshots plus UI-001 tokens/primitives, exactly as the goal's fallback requires. No Stitch-generated code, markup, or fake content exists anywhere in the repository.

### Diff and Artifact Audit

- `git diff --check` — clean (CRLF notices only, pre-existing).
- UI-003 files: `frontend/src/App.tsx`, `frontend/src/types.ts`, `frontend/src/lib/conversationStore.ts` (+ its test), `frontend/src/lib/i18n.tsx`, `frontend/src/components/ChatInput.tsx`, `frontend/src/app/routes.ts`, `frontend/src/styles/console.css`, plus new `frontend/src/components/conversation/` (4 components + 1 test) and `frontend/e2e/ui-003-conversation-modes.spec.ts`.
- Dependencies: UI-003 added none (`package.json`/`bun.lock`/`requirements.txt` diffs belong to earlier rebuild tasks: react-router-dom, pdfjs-dist, reportlab).
- Artifacts: no screenshots, debug dumps, temp files, secrets, or Stitch scaffold in source directories. The UI-003 receipts live under the git-ignored `frontend/test-results/ui-003/`; `frontend/e2e/screenshots/` is also git-ignored and pre-existing.
- No backend file was touched by UI-003, so the backend suite is unchanged and was not rerun.

### Exact Next Action

Write the UI-003 completion documentation (PROJECT_STATE.md entry + this checkpoint's F receipt), then mark UI-003 COMPLETE and select the next dependency-ready task from the master graph without starting it.

## UI-003-F3 Final Checkpoint (UI-003 COMPLETE)

### Task Status

UI-003 COMPLETE (sub-checkpoints A through F).

### Final Gate Results

- TypeScript: `bun run lint` (`tsc --noEmit`) — PASS, 0 errors.
- Unit: `bun run test` — PASS: 70 files / 397 tests (379 baseline + 18 new).
- Build: `bun run build` — PASS.
- Chromium: 125 passed / 2 intentional skips / 0 failed (baseline 118/2, +7 new spec).
- Firefox: 125 passed / 2 intentional skips / 0 failed after the documented focused-then-full rerun of the frozen TEST-001 timing-sensitive inspector test.
- Nine-reference receipt: 15/15 (baseline unchanged).
- `git diff --check`: clean.
- Backend: untouched by UI-003; the 901-test baseline stands.

### Files Created

- `frontend/src/components/conversation/ConversationPageHeader.tsx`
- `frontend/src/components/conversation/ResearchInsightsRow.tsx`
- `frontend/src/components/conversation/FollowUpTiles.tsx`
- `frontend/src/components/conversation/ConversationPageShell.tsx`
- `frontend/src/components/conversation/ConversationPage.test.tsx`
- `frontend/e2e/ui-003-conversation-modes.spec.ts`

### Files Modified

- `frontend/src/App.tsx` (shell integration, mode capture and family-aware navigation, mode-aware empty states, shared latest-answer memo)
- `frontend/src/types.ts` (`ConversationMode`, `RequestSnapshot.mode`)
- `frontend/src/lib/conversationStore.ts` (record mode, derivation, strict validation, merge fingerprint) + `conversationStore.test.ts`
- `frontend/src/lib/i18n.tsx` (16 en/vi keys)
- `frontend/src/components/ChatInput.tsx` (removed dead Web/attach controls; hybrid badge)
- `frontend/src/app/routes.ts` (explicit conversation family)
- `frontend/src/styles/console.css` (follow-up tile, insight tile, mobile grids)
- `frontend/src/App.test.tsx` (4 mode tests)
- `docs/UI_REBUILD_PLAN_CHECKPOINT.md`, `PROJECT_STATE.md`

### Dependencies

None added or changed by UI-003.

### Known/Pre-existing Issues

- Six frozen TEST-001 integration expectation failures and the timing-sensitive Firefox inspector class; both unchanged and documented above.
- Public API routes remain unauthenticated (documented limitation, unchanged).

### New Regressions

None.

### Exact Next Action

API-003 — Catalog facets/stats (dependency API-002 is satisfied; it is the next entry in the master-plan priority ordering). DATA-003 and UI-004 are also dependency-ready. Do not start API-003 without explicit user authorization.

## API-003-A/B/C Quota-Safe Checkpoint (contract, aggregation, routes)

### Active Task

API-003 — Catalog facets/stats. Status: IN PROGRESS (A, B, C implemented and focused-tested).

### Contract Confirmed From The Master Plan

- `GET /documents/facets` (public, provider-free) — "Facet counts/scope", contract test "Filter consistency".
- `GET /documents/stats` (public) — "Counts/availability/timestamp", contract test "Unknown versus zero".
- `GET /documents` extended with the plan's filter set; "Register static document facets/stats routes before dynamic document paths" is implemented literally (see route order below).
- Existing shared contracts honoured: `Page<T>: items, total, page, page_size`; "DocumentSummary, facets and statistics derive from the same catalog".

### Real Metadata Ownership (verified before designing)

- Catalog source: `_document_rows` over loaded embedded chunk metadata (startup-built, `_state["document_rows"]`). Row fields: document_id, ticker, filing_date, report_date, accession_number, sections, chunk_count, source_url.
- Stored chunk fields: accession_number, chunk_id, chunk_index, embedding, filing_date, report_date, section, text, ticker, token_count — **no per-filing form type**, and neither `*_sections.json` (accession_number, cik, filing_date, report_date, sections, ticker) nor the index manifest records one. `download_filings` requests `form_type="10-K"` but does not persist it.
- Decision (recorded, evidence-backed): the catalog exposes the recorded dimensions **company (ticker), year (filing_date), section** and reports `filing_type` as `unknown` with a reason instead of exposing a facet or a constant that no stored artifact supports. `report_dates` follows the same availability rule.

### Implementation

- New `src/api/catalog.py` (provider-free pure aggregation): `SUPPORTED_SECTIONS` (now the single source, re-exported by `app.py`), `filing_year`, `filter_documents`, `sort_documents` (stable with a document_id tiebreaker), `build_facets`, `build_stats`, `dimension_availability` (empty catalog ⇒ `unknown` + reason, never a fabricated zero).
- Facet count basis is explicit: `all_filters_except_own_dimension`, so a facet reports what selecting one of its values would leave while the other filters stay applied.
- Section facets count per membership: a document with several sections contributes to each, so a section facet does not sum to the document total (asserted per value instead).
- New `src/api/routers/catalog.py` with `create_catalog_router(get_rows)`; `app.py` registers it immediately after `/documents` and before `/documents/{document_id}` so the static paths can never resolve as a document id. Readiness returns 503 (matching the sibling document routes) instead of reporting an empty corpus.
- `/documents` gains `year`, `sort`, `direction` (additive; unsupported sort ⇒ 422 listing the supported fields) and reuses the shared filter/sort helpers so the catalog, facets, and stats agree.
- Typed response models added to `src/api/schemas.py` for both new endpoints.
- Route-order contract updated in `tests/test_api_router_contracts.py` (two entries inserted before the dynamic document route) plus a new ownership test proving the catalog routes belong to `src.api.routers.catalog`; the frozen pre-extraction OpenAPI hash test is untouched.

### Tests Run with Exact Results

- `.venv\Scripts\python.exe -m pytest -q tests\test_catalog_facets.py tests\test_api_router_contracts.py tests\test_api.py` — PASS: 88 passed, 0 failed (18 new catalog tests included).

### Remaining Work

- D: explicit scope/security/provider-free regression pass (the focused module already asserts provider-free and privacy) and this commit.
- E: full hermetic backend suite, diff/artifact audit, documentation, final commit.

### Exact Next Action

Commit the API-003 implementation and tests, then run the API-001/DATA-002 regression set before the full backend gate.

## API-003-D Quota-Safe Checkpoint (scope, security, provider-free, regressions, first commit)

### Active Task

API-003 — Catalog facets/stats. Status: IN PROGRESS (D complete; E is the full gate).

### Completed Work

- Scope semantics reuse the existing model exactly: ticker (existing param pattern), section membership, filing year derived from the recorded filing date, filing date, search, plus the new stable sort/direction. No second filter system was introduced.
- Access: both new routes are public (plan: `P`), allowlisted, provider-free. They require a loaded pipeline and return the boundary's own 503 otherwise, so a not-ready server cannot report an empty corpus. Nothing private is reachable: the focused tests assert that `/documents`, `/documents/facets`, and `/documents/stats` responses contain no conversation/session/workspace/token/credential/sqlite wording.
- Provider-free proof: the endpoint tests assert the injected pipeline mock received **zero** calls (`mock_calls == []`), i.e. no model, provider, store, or reader was touched while answering a catalog request.
- Route order: `/documents`, `/documents/facets`, `/documents/stats`, `/documents/{document_id}` — the static routes precede the dynamic one, exactly as the plan requires, and the contract test freezes that order.

### Commit

- `3ba64d7` — `feat(api): add catalog facet aggregation and statistics service` — 3 files, 780 insertions: `src/api/catalog.py`, `src/api/routers/catalog.py`, `tests/test_catalog_facets.py`. Staged content was scanned for secrets before committing (none).
- Shared boundary files remain in the working tree (`src/api/app.py` wiring, `src/api/schemas.py` models, `tests/test_api_router_contracts.py` entries): each already carries earlier uncommitted rebuild content (API-002 extraction, DATA-002 wiring, reader/PDF routes), so committing them inside API-003 would mix a completed prior task's work into this commit. They are recorded here for the dedicated backend cleanup commit. The API-003 endpoints are wired and fully validated in the working tree.
- A scanner hook reported an incomplete pre-commit scan (`scanner_enobufs`); staged files were manually checked for credential patterns and the final audit below re-runs the checks. No security claim is made beyond what was actually verified.

### Tests Run with Exact Results

- `.venv\Scripts\python.exe -m pytest -q tests\test_catalog_facets.py tests\test_api_router_contracts.py tests\test_workspace_access.py tests\test_workspace_transfer.py tests\test_workspace_transfer_api.py tests\test_workspace_persistence.py tests\test_api.py` — PASS: 168 passed, 0 failed.

### Exact Next Action

Run the full hermetic backend suite (checkpoint recorded before starting; the result is UNKNOWN if the session ends during it).

## API-003-E Final Checkpoint (full gate, real-corpus proof, audits, API-003 COMPLETE)

### Task Status

API-003 COMPLETE.

### Full Gate Results

- Full hermetic backend suite: `.venv\Scripts\python.exe -m pytest -q` — PASS: **920 passed, 0 failed, 188 warnings** in 108.75s. Baseline was 901 passed / 0 failed / 188 warnings; the increase is the 18 focused catalog tests plus one route-ownership contract test. Warning count is unchanged.
- Python compile/import: `.venv\Scripts\python.exe -m compileall -q src configs tests scripts` — PASS.
- `git diff --check` — clean (pre-existing CRLF notices only).
- Artifact audit: no SQLite/WAL/SHM, temp file, debug dump, or generated index was produced by API-003 (tests use `tmp_path`; the catalog paths are read-only).

### Real-Corpus Verification (no provider, no model initialization)

Aggregation was replayed directly over the on-disk embedded chunks (`_document_rows` → `build_facets`/`build_stats`) and matches the documented corpus exactly:

- 50 documents, 50 companies, 10,053 chunks.
- Sections: business 50, risk_factors 50, mdna 46, financial_statements 46, financial_table 50 — matching README's "46 filings with all four target sections and 4 degraded but searchable".
- Filing years: 2026 (42) and 2025 (8); every document records a filing date and a report date.
- `filing_type` reports `unknown` with its reason (no stored artifact records one) instead of a fabricated constant.
- Company facet sums to the document total (consistency True); a ticker-scoped request returns that company's document count.

### Documentation

- `PROJECT_STATE.md` gained the API-003 entry (routes, facets, statistics, scope, access, real-corpus result, gates, commit).
- This checkpoint records the contract, the metadata-ownership evidence, the deliberate `filing_type` omission, and both commit receipts.

### Dependencies

None added or changed. `src/api/catalog.py` uses only the standard library plus `configs.tickers`.

### Commits

- `3ba64d7` `feat(api): add catalog facet aggregation and statistics service` — `src/api/catalog.py`, `src/api/routers/catalog.py`, `tests/test_catalog_facets.py` (780 insertions).
- Final commit of this task (recorded below after creation) — API-003 wiring in the shared boundary files plus the task documentation.

### Known/Pre-existing Issues

- Six frozen TEST-001 frontend integration expectation failures and the timing-sensitive Firefox inspector class; unchanged and unrelated.
- Public API routes remain unauthenticated (documented limitation); the catalog routes are read-only and provider-free.

### New Regressions

None.

### Exact Next Action

API-004 — Discovery snapshots (dependencies API-002 and API-003 are satisfied; it is the next entry in the master-plan priority ordering). Do not start API-004 without explicit user authorization.

## API-003 Final Commit Receipt

- `3ba64d7` — `feat(api): add catalog facet aggregation and statistics service` — `src/api/catalog.py`, `src/api/routers/catalog.py`, `tests/test_catalog_facets.py` (3 files, 780 insertions).
- `a0f7a80` — `feat(api): expose catalog facets and statistics endpoints` — `src/api/app.py`, `src/api/schemas.py`, `tests/test_api_router_contracts.py`, `PROJECT_STATE.md`, `docs/UI_REBUILD_PLAN_CHECKPOINT.md` (5 files, 3599 insertions). The commit body states plainly that the shared boundary files also landed the earlier validated rebuild content they already carried (API-002 extraction, DATA-002 wiring, reader/PDF routes), because those files could not be split without corrupting a 962-line diff.
- Verified after committing: both commits touch only the files above; no `frontend/`, `src/workspace/`, `scripts/`, or `data/` path is included in either. Focused tests re-run green after the commits (24 passed).
- Note on tooling: the pre-commit hook reported an incomplete security scan (`scanner_enobufs`). Staged content was scanned manually for credential patterns and secrets (clean); no broader security claim is made here.
- Remaining dirty tree is the preserved earlier rebuild work (frontend UI-003 additions, API-001 access/reader/PDF modules, workspace persistence, docs plans, tool state directories such as `.mimosa/` and `.audit-runtime/`), plus the two API-003-documented shared-file decisions above.

### API-003 Status

COMPLETE. Exact next action: API-004 — Discovery snapshots (dependencies API-002 and API-003 satisfied). Do not start without explicit user authorization.

## API-004-A Quota-Safe Checkpoint (recovery, exact contract, plan)

### Active Task

API-004 — Discovery snapshots. Status: ACTIVE (A complete; implementation not started).

### Verified Current State

- API-003 COMPLETE with commits `3ba64d7` and `a0f7a80`; backend baseline 920 passed / 0 failed / 188 warnings; frontend 397 tests untouched by API-003.
- Checkpoint header still names API-003 as next because the API-004 goal arrived afterwards; the master graph confirms API-004 follows API-003 (`| API-004 | Discovery snapshots | API-002, API-003 | Search/retrieval filters | Prefilter/bounded/stable | UI-004 |`), so API-004 is the correct Exact Next Action.

### Exact API-004 Contract (read from the master plan, not invented)

| Method | Path | Request | Response | Service | Access | Contract test |
| --- | --- | --- | --- | --- | --- | --- |
| POST | `/search` | Query/mode/filters/grouping/page size | DiscoverySnapshot first page | Discovery/bounded memory | P | Prefilter |
| GET | `/search/{search_id}` | Page/page size | Snapshot page/scope/expiry | Discovery/bounded memory | P | Expired/stale |

Supporting contract text from the plan:

- "Page<T>: items, total, page, page_size. Discovery also states count_scope, snapshot identity and expiry; **bounded totals never imply corpus totals**."
- "DocumentSummary, facets and statistics derive from the same catalog. **DiscoverySnapshot owns stable ranked/grouped pages**."
- Search page plan: "Backend/API: bounded snapshots, prefilters, scoped facets, expiry"; risk register: "Search overstates counts → Snapshot/bounds/count scope"; tests: "prefilters, expiry, empty pages and research/open/save handoffs".
- Gap matrix: Search grouping needs "Group metadata"; highlights need "Safe rendering" reusing existing safe-highlight behaviour; counts need "Snapshot/count scope"; the plan's earlier decision "Separate discovery Search from diagnostic Retrieval" and "provider-free discovery" as a public posture.

### Real Metadata/Text Source (mapped, no invention)

- Discovery runs over the already-loaded serving corpus in memory: `_state["pipeline"].retriever._all_chunks` (chunk text + document/ticker/section/filing metadata) and the retriever's prebuilt `rank_bm25.BM25Okapi` index plus its `_tokenize` function. Both already exist at startup, so discovery makes **no model call**: no embedder, reranker, generator, provider, Qdrant write, or SEC access.
- Scope filtering reuses API-003: `filter_documents` selects the allowed document ids for ticker/section/year/filing_date, and discovery only scores chunks inside that document set, so discovery scope and catalog counts cannot drift.

### Design Decisions (recorded before coding)

- Ranking: BM25 lexical score over indexed chunk text (`engine.key = "bm25_lexical"`), labelled as a ranking signal with an explicit definition — never confidence or accuracy. Ties break on `chunk_id` then `document_id` so the order is deterministic.
- Modes: one supported value `keyword`. The plan's "natural language" mode would need query embedding, which is outside API-004's provider-free boundary, so an unsupported mode fails with the project's 422 validation style rather than silently doing something else.
- Grouping: `group_by` = `document` (default; one ranked card per filing with its best matching chunks) or `chunk` (flat hits). Group metadata comes from real chunk/document fields.
- Snippets: bounded plain text excerpt from the real chunk text with character ranges for the frontend to highlight safely; no HTML, no fabricated prose.
- Bounds: query 2–200 characters after trimming; page size 1–50 (default 20); candidate ceiling 200 ranked results per snapshot; snapshot TTL 900 s with at most 50 resident snapshots and deterministic eviction of the earliest expiring entry; snapshot ids are opaque `search-<16 hex>` tokens validated by pattern (never a filesystem path).
- Counts: `count_scope = "bounded_candidates"` plus the explicit ceiling, so a bounded total can never be read as a corpus total; zero matches return an empty page with truthful scope metadata rather than an error or placeholder rows.
- Rate limiting: the POST scan is limited through the existing slowapi conventions with a new `SEARCH_RATE_LIMIT` setting (default `30/minute`), matching the other bounded public routes; the cheap snapshot GET is not limited.
- Snapshot state is in-process only (single-worker topology), with an injectable clock so TTL tests never sleep.

### Files Planned

- New: `src/api/discovery.py` (service, scoring, snippets, snapshot store), `src/api/routers/search.py`, `tests/test_discovery_search.py`.
- Modified: `src/api/app.py` (register the search router), `src/api/schemas.py` (discovery request/response models), `configs/settings.py` + `.env.example` (search rate limit), `tests/test_api_router_contracts.py` (route order/ownership), plus task docs.

### Tests Run with Exact Results

- None yet for API-004 (recovery only). API-003's focused suite was re-verified green at the end of the previous task.

### Known/Pre-existing Issues

- Six frozen frontend integration failures; timing-sensitive Firefox class; public routes unauthenticated by design.

### Exact Next Action

Implement `src/api/discovery.py` (query normalization, BM25 scoring over the filtered corpus, bounded grouping/snippets, snapshot store with TTL and eviction) and its focused unit tests.

## API-004-B/C/D Quota-Safe Checkpoint (domain, snapshots, routes, tests)

### Completed Work

- `src/api/discovery.py`: deterministic query normalization (whitespace + casefold, 2–200 chars), Unicode-aware literal highlight terms, bounded snippet with safe character ranges, BM25-based ranking over the filtered corpus, document/chunk grouping, and a bounded snapshot store (TTL 900 s, at most 50 entries, evicts the earliest expiring entry, injectable clock, never extends a TTL on read).
- Matching rule (a real defect found by the focused tests): BM25 alone cannot decide "match", because a term present in a large share of the corpus has a non-positive inverse document frequency and scores zero. Discovery now matches on **actual term presence** and ranks with the BM25 score, so a common word still returns its chunks and a zero score is never reported as "absent". The retriever exposes this read-only via `bm25_terms_present`, alongside `bm25_scores`, and `tokenize_query` so scoring stays in the index tokenizer's space without duplicating it.
- `src/api/routers/search.py`: `POST /search` (typed body, `SEARCH_RATE_LIMIT` default 30/minute, 422 for unsupported mode/grouping/validation from either Pydantic or the service) and `GET /search/{search_id}` (paged snapshot; unknown id → 404, expired id → 410). Registered after the document/reader routes and before `/system/info`.
- Typed schemas in `src/api/schemas.py` for the request and the snapshot page (items/total/page/page_size plus `count_scope`, snapshot identity, `expires_at`, engine identity with an explicit definition).
- `configs/settings.py` + `.env.example`: `SEARCH_RATE_LIMIT=30/minute`.
- Route-order and ownership contract updated for the two new routes.

### Implementation Note (recorded because it cost a debugging cycle)

`src/api/routers/search.py` must not use `from __future__ import annotations`: the slowapi limiter wraps the endpoint, and the wrapper's module globals cannot resolve a postponed string annotation, so FastAPI silently degraded the typed `body` into a required query parameter. The module documents this constraint inline; the existing cache router avoids it for the same reason.

### Tests Run with Exact Results

- `.venv\Scripts\python.exe -m pytest -q tests\test_discovery_search.py` — PASS: 26 passed, 0 failed.
- `.venv\Scripts\python.exe -m pytest -q tests\test_api_router_contracts.py tests\test_discovery_search.py tests\test_catalog_facets.py tests\test_api.py tests\test_workspace_access.py` — PASS: 143 passed, 0 failed.

### Remaining Work

- E: explicit security/provider-free/API-003 consistency receipt (already asserted inside the focused module) and the first commit.
- F: full hermetic backend suite, real-corpus replay, audits, documentation, final commit.

### Exact Next Action

Commit the API-004 implementation and tests, then run the real-corpus discovery replay before the full backend gate.

## API-004-E Quota-Safe Checkpoint (security, provider-free, consistency, real corpus, first commit)

### Commit

- `a56c39a` — `feat(api): add provider-free discovery search snapshots` — 9 files, 1786 insertions: `src/api/discovery.py`, `src/api/routers/search.py`, `tests/test_discovery_search.py`, plus the API-004 hunks in `src/api/app.py`, `src/api/schemas.py`, `tests/test_api_router_contracts.py`, `src/retrieval/hybrid_retriever.py`, `configs/settings.py`, `.env.example`. Staged content was scanned for credential patterns (clean).
- Ownership note: the first three files were committed by API-003, so their diffs here are entirely API-004. `configs/settings.py`, `.env.example`, and `src/retrieval/hybrid_retriever.py` still carried earlier validated rebuild content; a selective-hunk staging helper was written and blocked by the security hook (correctly, for using argv-derived subprocess paths), so the commit body discloses that those files' earlier content landed with it. The alternative — leaving `settings.py` uncommitted — would have made the commit fail at import time on a missing setting.
- A scanner hook again reported an incomplete pre-commit scan (`scanner_enobufs`); no broader security claim is made beyond the manual checks.

### Security / Provider-Free / Consistency Evidence

- Provider-free: the focused module asserts the retriever's embedder, cross-encoder, model lock, and the pipeline's generator are never touched by a search, and the service only reads `bm25_scores`/`bm25_terms_present` over the prebuilt index.
- Public read class with no workspace reach: discovery responses are asserted to contain no conversation/session/workspace/token/credential/sqlite wording, and snapshot ids are opaque `search-<16 hex>` tokens validated by pattern (a path-like id is rejected as unknown).
- API-003 consistency: for four scopes, `POST /search` reports the same `scope.documents` as `GET /documents/facets`, and the facet payload is API-003's own aggregation rather than a copy.
- Bounds: query 2–200 chars, page 1–50, candidate ceiling 200, per-snapshot TTL 900 s, at most 50 resident snapshots with earliest-expiring eviction, `SEARCH_RATE_LIMIT=30/minute` enforced through the shared limiter (tested to 429 with the project's `client_rate_limited` body).

### Real-Corpus Replay (no model, no provider, no network)

Discovery was replayed over the on-disk corpus (10,053 chunks / 50 documents, BM25 built in 1.6 s):

- `Microsoft Cloud revenue` → 15 matched documents, top MSFT `mdna` chunk.
- `AWS revenue growth` → top hit is `AMZN_000101872426000004_mdna_0012`, the chunk carrying `AWS 107,556 128,725`, i.e. the same evidence the evaluation pipeline depends on.
- `Apple risk factors` with `ticker=AAPL` → 1 scoped document, 62 matching chunks, all AAPL.
- `quantum computing` → BAC/GS mdna and risk-factor chunks.
- `Doanh thu` (Vietnamese) → 0 matches, truthfully: the filings are English, so a Vietnamese term has no lexical match and the response reports `no_matches` rather than inventing rows.
- Queries whose match set exceeds 200 report `limited_by_ceiling: true` with `count_scope: bounded_candidates`, so a bounded total can never be presented as a corpus total.

### Tests Run with Exact Results

- `tests/test_discovery_search.py` — 26 passed.
- `tests/test_api_router_contracts.py tests/test_discovery_search.py tests/test_catalog_facets.py tests/test_api.py tests/test_workspace_access.py` — 143 passed.

### Exact Next Action

Run the full hermetic backend suite (checkpoint recorded before starting; the result is UNKNOWN if this session ends during it), then the audits and documentation.

## API-004-F Final Checkpoint (full gate, audits, API-004 COMPLETE)

### Task Status

API-004 COMPLETE.

### Full Gate Results

- Full hermetic backend suite: `.venv\Scripts\python.exe -m pytest -q` — PASS: **947 passed, 0 failed, 188 warnings** in 100.30s. Baseline 920 / 0 / 188; the increase is 26 focused discovery tests plus one route-ownership contract test, and the warning count is unchanged.
- Python compile/import: `.venv\Scripts\python.exe -m compileall -q src configs tests scripts` — PASS.
- `git diff --check` — clean (pre-existing CRLF notices only).
- Artifact audit: no snapshot dump, cache dump, SQLite/WAL/SHM, temporary JSON, or debug output was created by API-004 (tests use injected in-memory services; the store never touches disk).
- Dependency audit: none added or changed. `src/api/discovery.py` uses the standard library plus the project's existing `rank_bm25` index through the retriever; no new package for TTL, hashing, pagination, or text matching.

### Commits

- `a56c39a` — `feat(api): add provider-free discovery search snapshots` — 9 files, 1786 insertions (discovery service, search router, typed schemas, retriever read-only helpers, `SEARCH_RATE_LIMIT`, focused tests, route-order contract). The body discloses that `configs/settings.py`, `.env.example`, and `src/retrieval/hybrid_retriever.py` also landed the earlier validated rebuild content they already carried.
- Final documentation commit recorded below with its hash.

### Known/Pre-existing Issues

- Six frozen frontend integration expectation failures and the timing-sensitive Firefox inspector class; unchanged and unrelated to API-004.
- Public routes remain unauthenticated by design (documented limitation); discovery is read-only, provider-free, and workspace-isolated.
- Tooling note: the pre-commit hook repeatedly reported an incomplete security scan (`scanner_enobufs`); staged content was checked manually for credential patterns. No broader security claim is made.

### New Regressions

None.

### Exact Next Action

API-005 — Inspection metadata (dependencies API-002 and the settled filter ownership from API-003/API-004 are satisfied; it is the next entry in the master-plan table). Do not start API-005 without explicit user authorization.

## API-005-A Quota-Safe Checkpoint (recovery, exact contract, ownership audit)

### Active Task

API-005 — Inspection metadata. Status: ACTIVE (A complete; implementation not started).

### Verified Current State

- API-004 COMPLETE with commits `a56c39a` (implementation) and `4a2fbad` (docs); API-003 commits `3ba64d7`/`a0f7a80`. Backend baseline 947 passed / 0 failed / 188 warnings; frontend untouched at 397 tests.
- The master-plan table row after API-004 is API-005 (`| API-005 | Inspection metadata | API-002 | Retrieval trace | Legacy/production unchanged | After filter ownership settled |`), so API-005 is the correct Exact Next Action; the "filter ownership settled" prerequisite is satisfied by API-003/API-004.
- No partial API-005 work exists: the only API-005-relevant dirty files are the ones this run will touch.

### Exact API-005 Contract (read from the master plan)

- `POST /retrieval/inspect` — **existing endpoint**, extended: "Existing request **plus document/date**"; response is a **Versioned Trace**; service "Inspection/**no new persistence**"; access class **P** (public); contract test "**Legacy/production compatibility**".
- Retrieval page plan: "Backend/API: **additive document/date filters and versioned trace**"; risks: "inspection confused with production structured promotion"; tests: "legacy compatibility, unchanged production, raw scores"; done: "named stage semantics **including not-executed stages**".
- Gap-matrix Retrieval rows that API-005 owns: **Counts (P0)** "actual counts"; **Structured promotion (P0)** → "not in inspection" must become "**Observer metadata only**" with a "**Not-executed label**"; **Stage scores (P1)** → "**Semantics metadata**"; **Document filters (P1)** → "**Eligible document IDs**"; **Selected/dropped (P1)** → "**Known reasons only**"; **Evidence preview (P1)** already covered by the existing `text_preview`.
- The plan also records the established correction: "Inspection already exposes most stage scores but differs from production structured promotion."

### Existing Ownership Mapped (audit result)

- Route: `POST /retrieval/inspect` in `src/api/app.py` (rate-limited 10/minute, public, injection-pattern check, Unicode sanitize, query normalization, ticker detection). It already post-processes the trace to add `document_id` per candidate and wraps it with `query_interpretation`. It stays at the application boundary — the goal explicitly allows not forcing extraction when retrieval behaviour is at risk.
- Domain: `HybridRetriever.inspect()` in `src/retrieval/hybrid_retriever.py` already measures real stage timings with `perf_counter`, exposes `preset`, `query`, `filters{ticker,section}`, `top_k`, `candidate_pool`, `models{embedding,reranker,rrf_k}`, `stages[{name, elapsed_ms, skipped?}]`, `candidates[{chunk_id, ticker, section, filing_date, citation, text_preview, bm25_score/rank, dense_score/rank, lexical_rank, fusion_rank, rrf_score, cross_encoder_score, final_rank, selected}]`, `selected_chunk_ids`, `candidate_count`, `selected_count`, `elapsed_ms`. It is documented as separate from production retrieval and does not alter `retrieve_with_embedding`.
- Request schema: `RetrievalInspectRequest` (question, ticker, section, top_k 1–10, candidate_pool 10–50, preset ∈ {bm25, dense, hybrid, hybrid_rerank}).
- Tests: `tests/test_hybrid_retriever_inspect.py` (3 tests, model-free retriever double), `tests/test_api.py` route test, `tests/test_api_router_contracts.py` frozen order.

### Planned Additions (additive only; no existing key changes)

1. Request: `document_id`, `filing_date`, `year` (path-safe pattern and bounded values) — the plan's "document/date" filters, matching API-003/API-004 scope semantics.
2. Retriever trace: `trace_version` (`retrieval-trace-v1`), `score_semantics` (per score family: family, scale, definition, plus an explicit not-interchangeable note), stage `status` (`executed`/`skipped`/`not_executed`) alongside the legacy `skipped` flag, and `production_parity` marking structured promotion as **not executed** with its reason.
3. Per-candidate `dropped_reason` for non-selected candidates, limited to reasons that are provably known from the trace itself (`ranked_below_top_k`, `outside_candidate_pool`, `not_in_selected_preset_stage`); unknown reasons stay null rather than invented.
4. Route: an additive `scope` block with the effective filter values, the eligible document count, and a bounded eligible-document-id list (truncation flagged) computed from the canonical catalog and document-id helpers.
5. `chunk_filter` predicate passed into `inspect()` from the route so the stages run over the restricted pool, rather than post-filtering a trace whose ranks describe a wider scope.

### Files Planned

- New: `tests/test_retrieval_inspect_metadata.py`.
- Modified: `src/retrieval/hybrid_retriever.py` (additive trace fields + optional restriction predicate), `src/api/app.py` (request params, scope block, predicate), `src/api/schemas.py` (request fields), plus task docs.

### Tests Run with Exact Results

- None yet for API-005 (recovery/audit only).

### Known/Pre-existing Issues

- Six frozen frontend integration failures; timing-sensitive Firefox class; public routes unauthenticated by design. The pre-commit security hook reports `scanner_enobufs`; only manual credential-pattern checks are claimed.

### Exact Next Action

Implement the additive trace metadata in `HybridRetriever.inspect()` plus the route request/scope additions, then write the focused metadata and semantic-equivalence tests.

## API-005-B/C/D/E Quota-Safe Checkpoint (trace metadata, route, equivalence, safety)

### Completed Work

- `HybridRetriever.inspect()` (additive only; existing keys and values untouched):
  - `trace_version` = `retrieval-trace-v1` on every trace, including the empty-query early return.
  - `score_semantics`: one entry per score family that the preset actually produced, each with `family`, `scale`, and `definition`, plus a note stating the families are **not** comparable with one another and that none is a confidence/accuracy/probability.
  - `production_parity`: structured financial-row promotion and lexical-ladder merging into the final evidence are reported as `not_executed` with the reason, so a trace can never be read as production output (the gap matrix's P0 "not-executed label").
  - Stage `status` for every stage (`executed` / `skipped` / `not_executed`) alongside the legacy `skipped` flag, plus a `reason` and `elapsed_ms: null` for a stage that did not run — a duration is never implied for a stage that never ran.
  - A named `structured_promotion` stage carrying the not-executed label.
  - Per-candidate `dropped_reason`, restricted to reasons the trace can prove: `ranked_below_top_k`, `outside_candidate_pool`, `not_in_selected_preset_stage`; a selected candidate reports `null`.
  - An optional `chunk_filter` predicate so the document/date restriction is applied to the eligible pool **before** the stages run, including the dense stage's store results (otherwise the trace would have reported dense candidates outside the requested scope).
- Route `POST /retrieval/inspect` (kept at the application boundary, per the goal): accepts `document_id`, `filing_date`, and `year`; builds the restriction from the canonical `_document_id` and `catalog.filing_year` rules; adds `filter_values` (the effective filters, including the inferred ticker) and a bounded `scope` block (`documents`, `eligible_document_ids` capped at 200 with `truncated`, or a truthful unavailable reason when the catalog is not readable).
- `RetrievalInspectRequest` gained the three additive fields with path-safe and range validation.
- Frontend: one minimal additive type change (`stages[].elapsed_ms` became `number | null`, optional `status`/`reason`), because the backend now truthfully reports a null duration for a stage that did not run. `tsc` clean; no UI behaviour change (the Retrieval panel already renders a non-numeric duration as "Not reported").

### Tests Run with Exact Results

- `.venv\Scripts\python.exe -m pytest -q tests\test_retrieval_inspect_metadata.py` — PASS: 22 passed, 0 failed.
- `tests/test_hybrid_retriever_inspect.py` — PASS: 3 passed (two assertions updated from a positional `stages[-1]` to a by-name lookup, because a not-executed stage is appended; the assertions themselves keep the same expectations).

### Real Defects Found By The New Tests

1. The dense stage consulted the vector store directly, so a document/date restriction silently missed dense candidates. Fixed by filtering the store results through the same predicate.
2. A question naming a company infers the ticker (existing production behaviour) and therefore composes with explicit document/date filters; the tests now assert that composition instead of assuming filters replace it.

### Remaining Work

- F: full hermetic backend suite, audits, documentation, commits.

### Exact Next Action

Run the focused regression set (inspect, api, router contract, catalog, discovery), then the full backend suite after a checkpoint.

## API-005-F Pre-Gate Checkpoint (focused regression green; full suite next)

- Focused regression set: `tests/test_retrieval_inspect_metadata.py tests/test_hybrid_retriever_inspect.py tests/test_api.py tests/test_api_router_contracts.py tests/test_catalog_facets.py tests/test_discovery_search.py` — PASS: 140 passed, 0 failed.
- Frontend typecheck after the additive trace-type change — PASS, 0 errors.
- About to run: `.venv\Scripts\python.exe -m pytest -q` (full hermetic backend suite). Baseline 947 / 0 / 188. If this session ends during that command the result is UNKNOWN and must be re-run; the focused results above stand.

## API-005-F Final Checkpoint (full gate, audits, API-005 COMPLETE)

### Task Status

API-005 COMPLETE.

### Full Gate Results

- Full hermetic backend suite: `.venv\Scripts\python.exe -m pytest -q` — PASS: **969 passed, 0 failed, 188 warnings** in 106.22s. Baseline 947 / 0 / 188; the increase is the 22 focused inspection-metadata tests, and the warning count is unchanged.
- Focused regression set (inspect metadata, retriever inspect, api, router contracts, catalog, discovery) — 140 passed.
- Python compile/import: `compileall -q src configs tests scripts` — PASS.
- Frontend: `bun run lint` (tsc) clean and `bun run test` 70 files / 397 tests passed after the minimal additive trace-type change.
- `git diff --check` — clean; artifact audit — no trace/query dump, DB file, or debug output created by API-005.
- Dependency audit: none added or changed.

### Commits

- Recorded below after creation; the working tree's API-005-owned changes are `src/retrieval/hybrid_retriever.py`, `src/api/app.py`, `src/api/schemas.py`, `tests/test_retrieval_inspect_metadata.py` (new), `tests/test_hybrid_retriever_inspect.py` (two positional assertions replaced by by-name lookups), `frontend/src/types.ts` (additive), and the task documentation.

### Known/Pre-existing Issues

- Six frozen frontend integration failures and the timing-sensitive Firefox inspector class; unrelated to API-005.
- Public routes remain unauthenticated by design; `/retrieval/inspect` is read-only, provider-free, and workspace-isolated.
- Tooling: the pre-commit hook reports an incomplete security scan (`scanner_enobufs`); only manual credential-pattern checks on staged content are claimed.

### New Regressions

None.

### Exact Next Action

UI-004 — Source/document composition (dependencies UI-003 and the reader/inspection surfaces are satisfied; it is the next table row after API-005). Do not start UI-004 without explicit user authorization.

## UI-004-A/B Quota-Safe Checkpoint (references, geometry parity, receipts)

### Active Task

UI-004 — Source/document composition. Status: IN PROGRESS (B implemented; C-F next).

### Authoritative References Identified

- `docs/ui-references/rag-workbench-master-reference-dark.png` (1254x856): navigation ~150px | conversation ~493px | "Retrieved Sources" ~335px | "Document Viewer" ~262px, all four visible at once.
- `docs/ui-references/research-ui-reference-dark-v1.png` (1586x992): navigation 200 | research 620 | sources 340 | reader 420.
- Both show: sources rail = header + count badge + sort + filter, numbered cards (rank chip, document name, score, excerpt, section + page chips, "View all sources"); document viewer = document header with page navigation and icon actions, paper preview with highlighted passages, tabs (Highlighted Chunks / Page Content / Metadata), and a selected-chunk card with score, page and context action.

### Gap Found And Closed (B)

The old geometry only produced the four-pane workbench above 1384px of content, so the 1280/1254 reference widths fell back to a contextual overlay — the reference composition was unreachable at its own reference width. Fixed by:

- `WORKBENCH_PANE_LIMITS`: sources 332 default (300-400), document 400 default (272-560) — matching the reference rails.
- `WORKBENCH_LAYOUT_CONSTRAINTS`: research minimum 430.
- New `deriveEffectivePaneWidths`: sources keep their preferred width while the document pane narrows into the remaining room before the layout changes mode, and `WorkbenchLayout` now feeds those effective widths to the CSS tracks so the rendered geometry always matches the mode decision.
- Tests updated deliberately (not to hide regressions): `workbench.test.ts` now asserts the reference composition at 1254 and 1280, the shrink-to-fit rule, and the new limits; `useWorkbenchPreferences.test.tsx` follows the new clamp. Both cite the reference as the reason.

### Receipts Captured (deterministic fixtures, no provider)

`frontend/e2e/ui-004-source-document.spec.ts` (3 tests, Chromium, all passing) asserts the four-pane mode at 1440 and at the 1254 reference width, that the sources rail lists the answer's real sources, and that no body/root horizontal overflow appears at 1254/1280/1440/1024/390. Screenshots: `frontend/test-results/ui-004/evidence-{1254x856,1280x856,1440x900,1024x768,390x844}-chromium.png`.

### Visual Comparison Result (rendered vs reference)

- Four-pane composition now matches the reference structure at its own width: navigation, conversation, retrieved-sources rail (header + count + filters + numbered cards with rank chip, document name, score badge, excerpt, section chip and page), and the document pane (document identity, representation tabs, real reader content with the selected evidence highlighted).
- Justified deltas: the reference's paper preview and page numbers correspond to an official PDF representation that this corpus does not admit (the live path is an explicit `DERIVED_PDF`), so the document pane shows the real structured/normalized readers; the reference's page-level navigation is therefore omitted rather than fabricated. Source cards additionally expose real per-source actions (copy, open document, save evidence) and an advanced-ranking disclosure.
- Known cosmetic limitation (no reference target): at 390px the evidence sheet's content can scroll horizontally inside the panel; body/root overflow is asserted zero.

### Remaining Work

- C/D: source-rail and document-pane chrome polish if the gates allow; integration invariants are already asserted (no regeneration, real identity, no overflow).
- E/F/G: full unit suite, build, Chromium/Firefox gates, nine-reference receipt, docs, commit.

### Exact Next Action

Run the full frontend unit suite and production build (checkpoint recorded before these long commands).

## UI-004-C/D Quota-Safe Checkpoint (integration invariants, spec contract updates)

### Completed Work

- Integration invariants asserted in the new spec: the evidence surface opens from a real citation, the sources rail lists the answer's real sources, the four-pane composition is the active mode at 1440 and at the 1254 reference width, and no body/root horizontal overflow appears at 1254/1280/1440/1024/390. The answer stream is not re-requested when a source is selected (the spec asserts the mode and rail directly; the existing v5-05 sync and workspace regression specs continue to cover identity handoff).
- Real drift found and fixed while updating the specs: `ContextPanel` hardcoded the pane reset/fallback widths (304 / 440) instead of using `WORKBENCH_PANE_LIMITS`, so the double-click reset and the null-preference fallback disagreed with the documented defaults. Both now read the documented limits.
- Spec contract updates (reference-driven, disclosed):
  - `v5-06-layout.spec.ts`: the 1440 target now asserts the reference four-pane geometry (research 508 / sources 332 / document 400 and two 8px splitters); 1920 asserts research 956; the dock is exercised at the wide-but-short 1920x700 target where it remains the honest presentation (with its Sources/Document tab switcher); the 768-tall note records that the measured container excludes the 56px toolbar so the four-pane height floor needs the reference's 856-tall viewport; resizer limits are 300-400 and the drag delta (356) and reset default (332) follow the new limits.
  - `v5-03-sources.spec.ts`: the pane switcher is now conditional, because four-pane shows both panes at once and therefore has no switcher; the dock/overlay presentations still exercise it.
- Every changed assertion carries a comment citing the reference or the contract it now follows.

### Tests Run with Exact Results

- `bunx playwright test e2e/v5-06-layout.spec.ts e2e/v5-03-sources.spec.ts e2e/ui-004-source-document.spec.ts --project=chromium --workers=1 --retries=0` — PASS: 7 passed, 0 failed.
- `bun run lint` (tsc) — PASS.
- `bun run test` — PASS: 70 files / 398 tests.
- `bun run build` — PASS.

### Remaining Work

- E/F/G: full Chromium and Firefox gates, nine-reference receipt, frontend contract documentation update for the new geometry, artifact/diff audit, commit, documentation.

### Exact Next Action

Run the full Chromium suite (checkpoint recorded before this long command), then Firefox and the nine-reference receipt.
