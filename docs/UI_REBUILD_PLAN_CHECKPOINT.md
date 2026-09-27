# Current Planning Status

## TEST-004 complete — Full product validation (2026-09-28)

TEST-004-A through H COMPLETE. [Final receipt and per-feature matrix](TEST_004_FINAL_PRODUCT_RECEIPT.md)
supersede the historical in-progress A entry below. Starting HEAD `e4c6710`;
source/test repair commits `defec4f6` and `0609e2f`; this checkpoint and receipt
are in a separate closure commit. Managed detached data-free checkout imports
the real app, compiles, has 83 unique routes, installs 284 frozen frontend
packages and serves the built frontend against real FastAPI public/local
handlers and a temporary SQLite workspace. No `.env`, provider, canonical
`data/`, untracked source or generated artifact is required.

- B: Full clean backend **1354 passed/34 skipped/148 warnings/0 failed**;
  every skip requires absent git-ignored local corpus/evaluation artifacts.
  Untouched original checkout ran **1388 passed/188 warnings/0 failed**.
  Focused persistence/migrations/transfer/access/atomicity/Search/jobs/logs/
  TEST-002/bootstrap: **360 passed/1 warning**; public mode creates no DB.
- C: Real Documents→Search snapshot→reader→provider-free Retrieval and fresh
  Chat and Research-family SSE→citation→reader journeys pass. 16/16 separate
  HTTP/session tests cover partial/unavailable/decomposed paths.
- D: Protected SQLite Collection CRUD/conflict/tombstone, truthful staged
  browser refusal, Models/Datasets registry and Pipeline one queued run/five
  steps/events/cancel pass. Existing Collections/model-test browser bearer
  integration remains staged; API-001 was not weakened.
- E: Six native-v1 metrics, exact zero, frozen budget/two-step Evaluation
  result, server Analytics/Logs privacy/cursors and Settings transfer/reload
  credential loss pass. No Ragas or live provider.
- F: Final production-like suite **24/24** (12/engine), 14 direct routes,
  Back/Forward, A–F journeys, 96 responsive combinations, 120 whole-page
  axe analyses with zero reported A/AA violations and zero body/root overflow.
  Selected generated screenshots inspected but untracked.
- G: Four reproduced P2 visual/interaction defects repaired with focused
  failing regressions; test-only selector/isolation/SSE assertions corrected.
  TEST-002 browser contracts **4/4**, focused TS/component contracts **118/118**,
  affected TEST-003 Chat/Research/Evaluation native/responsive **30/30**,
  local reader/identity suite **6/6**. Final clean source HEAD `0609e2f`
  has zero deterministic acceptance failures.
- H: TypeScript PASS, full Vitest **90 files/792 passed**, build PASS/2074
  modules (existing ~506.92 kB warning). README/DESIGN drift corrected;
  artifact/secret/lockfile checks and final closure-HEAD replay recorded in
  receipt/handoff. The original 12 unrelated untracked paths remain; no
  task-created DB, screenshot, trace, dist, credential or data is committed.

Limitations: provisioned backend interpreter is not a fresh package install;
native zoom125/150/200 is manual/unverified; no production SLA, broad WCAG or
security certification. The actual master-plan graph has UI-013 after TEST-004.
**Exact Next Action = UI-013 — Cleanup/documentation. STOP: UI-013 not started.**

## TEST-004-A — Final product acceptance plan (2026-09-27)

IN PROGRESS. [Final acceptance/journey matrix](TEST_004_FINAL_PRODUCT_RECEIPT.md)
records current HEAD `e4c6710`, clean-checkout/import/build and real HTTP/SQLite
integration strategy, access/migrations/transfer/privacy gates, six compact
product journeys, both browsers/locales/width sanity, final-HEAD revalidation
and artifact audit. Existing TEST-003 visual authority and known native zoom /
staged bearer limitations stay explicit. No live providers, data mutation,
new capability, dependency changes, optional Ragas or UI-013 cleanup authorized.

## TEST-003 complete — Nine-reference visual validation (2026-09-27)

TEST-003-A through H are COMPLETE. [Authoritative matrix and measured receipt](TEST_003_VISUAL_RECEIPT.md)
accounts for Collections, Documents, Evaluation, Models, Pipeline, Chat,
Research, Retrieval and Search: eight1586×992 references and Chat1254×856.
All nine native baselines preceded production repairs; final native Chromium
and Firefox images and side-by-side comparisons were inspected. Truthful data,
established readable pane minimums and accessible density explain documented
B/D/E deviations; no fake screenshot facts or tenth Reranker reference.

Implementation: `acd9487` (bounded visual/accessibility and source-fact repairs).
Search dark button2.27→4.71:1 (rest/hover/keyboard-focus); BM25 label4.32→8.25.
Shared connection/selected-text/light-subtle/state roles pass affected consumers.
Splitter controls are independent; phone targets44px/input text16px, useful
reader content and existing Back recovery are protected. Guessed source pages
and missing-section Risk Factors fallback are removed, without a DTO/API change.

Actual final gates: TypeScript PASS; Vitest90 files/790 passed; production build
PASS (2074 modules, existing506.91kB aggregate warning). Browser300/300 passed:
90 visual,204 focused domain/route/shell/contracts,6 layout;150 each engine.
The visual campaign measures648 populated responsive combinations (nine widths,
dark/light × EN/VI × both engines), exact body/root overflow0;162 whole-page
axe A/AA analyses report0 violations. Keyboard, mobile and manual image review
supplement axe; this is not blanket WCAG certification. Native zoom125/150/200
is explicitly external manual / UNVERIFIED, not simulated through viewports.

Backend unchanged: historical TEST-0021384/188 warnings/83 routes NOT rerun.
Original12 unrelated untracked paths preserved. Selective source/test/textual
documentation commits only; no screenshot/report/trace/dist/secret/runtime DB/
canonical data artifact. Working/staged diff checks PASS. No deterministic
regression remains; interrupted sweeps are UNKNOWN and excluded. Real staged
Collections/model-test bearer integration and build/backend warnings remain.

Graph verified at master-plan TEST-004 row: depends on TEST-002 and TEST-003;
UI-013 follows it. Exact Next Action = TEST-004 — Full product validation.
STOP: TEST-004 has not started. Earlier TEST-003-A and TEST-002 entries below
retain their historical meaning and are superseded by this closure.

## TEST-003-A — Native reference plan (2026-09-27)

IN PROGRESS. [Plan and authoritative matrix](TEST_003_VISUAL_RECEIPT.md) records
the exact nine PNGs, verified native dimensions, canonical routes/selected states,
image geometry/type/surfaces, semantic ownership and comparison tolerance policy.
All nine images inspected; production unchanged. Native baseline captures precede
repairs. Both browsers, responsive/theme/locale/accessibility and honest external
native-zoom limitation are required. No TEST-004 or new product capability.

## TEST-002 complete — Cross-layer contracts (2026-09-27)

TEST-002-A through G are COMPLETE. The earlier in-progress plans/reproduction
notes below are historical. [Full contract matrix, defects, commands and limits](TEST_002_CONTRACT_RECEIPT.md).

Implementation: `7d1c937` (shared contract suite and Unicode offsets) and
`59c56f2` (Collection list refusal). 53 named method/path/access pairs, 26
selected response/OpenAPI references, 11 body models, 31 compiler-resolved
Python/TS literal unions, 52 real-client transports and seven shared responses.
Existing canonical transfer fixtures/algorithms are reused. Durable SQLite→HTTP
checks retain job/step/revision/budget/result and telemetry null/zero/false facts.

Repaired CL-01 casefold/UTF-16 snippet range drift, CL-02 list 404 incorrectly
shown as record-not-found in the save dialog, and CL-03 zero-based step fixture
drift. No new feature/provider/dependency/codegen/serving-data change.

Actual final gates: backend 1384 passed / 188 warnings / zero failures; 83 routes.
Vitest 89 files / 788 passed; TypeScript passed; production build passed with the
existing aggregate chunk warning. Selected backend 351 passed; focused frontend
230 passed plus affected components 76 passed. Browser contracts 4/4 (two per
browser), light/EN desktop and dark/VI phone; screenshots inspected. Diff checks
passed. Whole-page dark Search contrast is not certified: unchanged button and
BM25 label findings remain for the visual branch. No native zoom claim.

Tracked/staged tree began clean plus the same 12 unrelated untracked paths;
those paths remain preserved. Only TEST-002-owned source/tests/docs are committed,
not generated reports/images/databases/secrets. Collections/model-test bearer
integration remains staged, with truthful refusal; API-001 is not weakened.

The actual dependency graph confirms TEST-003 as the remaining visual branch
before TEST-004. Exact Next Action: TEST-003 — Nine-reference visual validation.
STOP: TEST-003 was not implemented.

## TEST-002-E — CL-02 verified repair plan (2026-09-27)

IN PROGRESS. P2 surface-specific refusal defect: CollectionTargetDialog uses
the record-level 404 mapping for GET /collections. The new component regression
fails deterministically: it renders Collection not found plus creation controls
instead of the private capability-unavailable state. API-001 and the existing
CollectionsWorkspace list handling are authoritative. Reuse listUnavailableFailure
only in the dialog's list catch; leave record/mutation 404 untouched. No auth
integration, backend access change, persistence fallback or new control. Risk:
misclassifying record errors, covered explicitly by the regression. Validate the
component, Collections neighbors and two-browser Search save handoff.

Browser diagnostics: reduced-motion settles the established entry animation.
Light Search passes whole-page axe; dark Search still reports existing primary
button (2.27:1) and BM25 label (4.32:1) contrast. Neither owns snippet offsets;
no CSS was changed. Retain this finding for the visual gate, not a CSS redesign
in TEST-002. Contract browser assertions cover the repaired renderer/dialog;
whole-page visual certification remains outside this task.

CL-03 test-fixture drift: the independent UI evaluationJob fixture supplies
step ordinals 1/2, while DATA-004 persists and validates 0/1. The new parity test
fails 1/12; real SQLite→EVAL-003 HTTP checks pass with names execute_cases /
aggregate_report and ordinals 0/1. Correct the synthetic fixture only to index;
do not change durable storage or invent a presentation contract. Risk is limited
to test expectations, covered by full Vitest and existing browser fixtures.

## TEST-002-B/C/D — Shared contract evidence (2026-09-27)

IN PROGRESS; not a completion receipt. Shared test-only catalogs now bind 53
named method/path/access pairs (selected request/response models, revision and
resume headers), 31 independent Python/actual compiler-resolved TS unions,
and 49 real frontend request examples checked against live backend parameters.
Focused results before response work: Python 134 passed / one warning; Vitest
80 passed / two files; TypeScript passed. No runtime schema package/codegen.

The response fixture adds registry unknown/null/zero, log outcome vs severity,
null vs measured-zero duration, native computed-zero/false/unavailable/NA and
finite Pipeline/Evaluation events. Python uses explicit UTF-8 fixture reads.
Test-harness errors (pytest reserved parameter name, jsdom setup and initial
event-owner lookup) were corrected without changing production behavior.

Verified defect CL-01: discovery offsets. Two Python regressions fail on
`Straße` because casefold expands the original text; two TS regressions fail
on astral prefixes because JS slicing uses UTF-16. API ranges are half-open
Unicode code-point positions in the returned original text, not folded text
or UTF-16. Smallest repair: map folded match positions back to original code
points in `build_snippet`; slice by code point in `snippetSegments`. Ranking,
query semantics, original text, bounds and IDs stay unchanged. Shared fixtures
are the regression authority; build and focused two-browser Search follow.

UI semantics: Search submission → ranked excerpt card → API-owned literal
match highlights; open/save handoffs retain the same chunk/document identity.
Success marks the intended original word; empty/no-match/retry behavior is
unchanged. Existing page/card/reader hierarchy, request epochs, recent-query
storage and page/local scroll owners remain authoritative. Review risks:
casefold expansion, astral splitting, truncated-window offsets, accidental
text alteration and changing ranking/provider behavior. No CSS/control changes.

Remaining: persistence→HTTP semantics, expanded negative/error/SSE checks,
transfer reuse, affected full gates and requirement-by-requirement closure.
Exact Next Action: CL-01 bounded repair and focused regression proof.

## TEST-002-A — Cross-layer contract plan (2026-09-27)

IN PROGRESS, recorded before implementation. Start HEAD `7d178f2`, clean
tracked/staged tree and the same 12 unrelated untracked paths. TEST-002 only;
no TEST-003 visual campaign, optional Ragas, new routes/settings or codegen.

Authority and required boundary matrix:

| Surface | Authority and contract pairs | Required evidence |
| --- | --- | --- |
| Access | API-001 dependencies/settings → routes → memory session/private clients | Named public/local/execution classification; 401/403/404; no public bearer or token URL/storage; preflight is not authorization |
| Documents/Search/Retrieval | Catalog/discovery/trace domain → API DTOs → clients/types/reader handoffs | Exact document/chunk/snapshot IDs; paging/query encoding; 404/410; range semantics; skipped/null timing and raw score families |
| Collections | DATA-003 repository → router payload/requests → typed clients | Four member kinds; canonical IDs/revisions; PATCH body vs DELETE query revision; conflict/tombstone/export semantics |
| Registries | API-006 configured/observed/provenance owners → DTOs → unions | Configured/load/availability independent; unknown/null/count-zero; corpus/evaluation discrimination and provenance states |
| Pipeline | DATA-004 jobs + API-007 staging → DTOs → client/SSE | Canonical run/revision; five stages/order; If-Match; queued/cancelling/interrupted; numeric event resume, close is not success |
| Native metrics/analytics | EVAL-001 protocol + EVAL-002 analysis → public DTOs → Evaluation client/types | Protocol v1/six metric IDs; computed/unavailable/not_applicable; 0/false/null; candidate_minus_baseline; eligibility/groups/four failure categories |
| Evaluation jobs | Frozen plan + durable store/coordinator → EVAL-003 DTOs → private client | Canonical job/revision; two steps; provider_attempt_slot; budget exhaustion; cancellation/interruption/event/results and hidden-text projection |
| Telemetry/Logs | DATA-005 SQLite terminal facts/canonical jobs → DTOs → operational transport/UI | Three ranges/two intervals/five metrics; severity vs outcome; opaque cursor/order; null duration vs measured zero |
| Settings/transfer | Existing configuration/registry/transfer owners → redacted DTOs → safe projection and browser actions | Only supported facts/actions; no operational mutation API; memory auth; existing Python/TS backup digest/identity/revision fixtures |

Strategy: extend rather than replace the existing hermetic suites. One compact
test-only catalog will bind selected route/path/method/access/request/response
facts and independent Python/TypeScript enum owners. Backend tests inspect live
registered routes/OpenAPI and canonical domain literals; frontend tests inspect
actual compiler-resolved unions and capture real wrapper requests. Small shared
edge responses connect backend validation to frontend parsing/rendering where
useful; preserve existing transfer canonicalization fixtures/algorithm. No
generated OpenAPI snapshot, shared runtime schema package or provider call.

Existing backend router tests cover registration/ownership, but most frontend
fixtures are independent of backend schema validation. Close that gap, then
selected persistence→domain→HTTP semantic tests and client mutation/error/SSE
checks. Reproduce any mismatch before correcting its authoritative owner.
Collections and model-test bearer attachment remain staged product integration;
test truthful refusals without weakening access or adding that roadmap feature.

Escalation: new Python/Vitest tests → affected existing contract slices →
TypeScript/full Vitest → full hermetic backend. Build/browser only for relevant
runtime changes. Audit explicit staging/artifacts and update current records.
Exact Next Action: TEST-002-B/C catalog and route/schema/union/request parity.

## UI-012 complete — Analytics, Logs and Settings (2026-09-27)

UI-012-A through H are COMPLETE. Implementation: `5c41f7f` (`feat(ui):
integrate server analytics logs and supported settings`). Documentation closure
is a separate commit. The older UI-012-A/foundation notes and audit receipts
below describe their historical state and are preserved.

Analytics is DATA-005 server truth: protected summary and UTC timeseries,
24h/7d/30d, hour/day and all five metrics. Rates retain numerator/denominator,
duration known/unknown populations preserve null and measured zero, and jobs
retain namespace/outcome aggregation. Observations are not interpolated or
smoothed and have a bounded table equivalent. The browser-local Analytics
writer/store/range modules and obsolete tests are retired; stored history is
untouched. Range changes read summary/series; metric/interval changes read
series only. Explicit Refresh, no polling.

Logs consumes protected `GET /logs`: seven-day API records, not process logs.
Request/job category, returned severity and domain outcome remain independent.
Category/level/cursor are URL-owned; filters reset cursor; page limit is 50.
Opaque cursors pass unchanged, API order is retained, and detail disclosures
perform no request. No hidden research/provider/credential fields enter state.

Settings support matrix: theme/language are editable browser preferences;
backup preview/confirmed import/export and writer recovery reuse existing
owners. Connection reuses the UI-010 memory-only session, clears its input on
submit, shares across routes and clears on disconnect/reload. Protected
configuration status is read-only; public system/model reads have no bearer.
Provider presence/unknown availability is not health. Fixed 30-day telemetry
and seven-day Logs policy are read-only. No workspace-settings mutation API
exists; no fake Save/retention/log-clear/model/provider/key controls were added.
Architecture/help remains `/settings?panel=architecture`.

Read lifetimes use abort plus monotonic epochs and selection/session identity,
including A→B→A. Error bodies are never reflected; extra JSON fields are
projected away before state. Public/private unavailable, unauthorized, denied,
backend failure, invalid selectors, real empty and unmeasured are distinct.
Analytics/Logs query selectors and direct routes preserve Back/Forward.

Actual final validation on the committed implementation:

- Task-focused Vitest: transport 27, Analytics 19, Logs 13, Settings 12 and
  shared session 3 = 74/74 across five files.
- Full Vitest: 85 files / 688 tests passed; TypeScript `bun run lint` passed.
- Playwright production builds passed (existing aggregate >500 kB warning).
- `e2e/ui-012-operations.spec.ts` + `e2e/ui-routing.spec.ts`: 34/34,
  17 Chromium + 17 Firefox (28 UI-012 + six route/shell cases), 51.9s.
- Changed guided-navigation regression: 2/2, one per browser, 12.0s.
- Selected Pipeline/Evaluation shared-session neighbors: 6/6, three per browser,
  16.1s. No broader reference or integration campaign is claimed.
- Both browsers: all three routes at 1586×992, 1440×900, 1280×856, 1024×768,
  768×900, 390×844, 1440×700, 1366×768 and 1920×1080; light/EN and dark/VI,
  reduced motion, focus/reachable lower actions and zero body/root overflow.
  Focused workspace axe A/AA scans returned zero violations.
- Screenshots inspected for each route at desktop light/EN and phone dark/VI,
  including scrolled lower content. Cards stack, log records stay readable and
  the bucket table/pagination/help actions remain reachable.

No dedicated Analytics/Logs/Settings reference exists in the nine-PNG inventory.
`evaluation-ui-reference-dark-v1.png` (1586×992) informed shared chrome/card
language only, not borrowed metrics or a parity target. Native browser zoom
125/150/200% remains an external manual check; viewport tests do not certify it.

UI-012 changes no backend, dependencies, canonical data, provider execution or
official benchmark. The separate intervening audit committed backend/privacy
and frontend race fixes; its final backend is 1234 passed / 188 warnings / 83
unique API method/path routes, not a UI-012 test-count increase. UI-011's
historical frontend baseline was 84 files / 619 tests; current 85 / 688 includes
the audit's four frontend regressions.

Artifact/index review and diff checks passed. Only explicit UI-012 source,
tests and docs were staged. Screenshots, traces, bundles, DB/WAL/SHM, caches,
real credentials and all 12 unrelated untracked paths remain excluded.
Original UI-012 start: clean tracked/staged tree + 12 unrelated untracked paths.
Post-audit resumption: 19 tracked dirty + 21 untracked, no staging.
Final closure: clean tracked/staged tree + the same 12 unrelated untracked paths.

Known limits: fixed read-only operational policy; Logs is not process-log
ingestion; descriptive provider flags do not probe health; native zoom remains
manual; existing bundle/parser/dependency warnings and the audit's separate
Unicode-highlight/Collections-auth/multi-process caveats are unchanged.

Exact Next Action: TEST-002 — Cross-layer contracts, verified from the master
graph. TEST-003 follows the completed UI dependencies; TEST-004 waits on both.
Optional EVAL-004/Ragas is not required. STOP: none of these tasks was started.

## Current engineering audit and repairs (2026-09-27)

This audit started at `cbfdfda`, with 19 tracked dirty entries, 21 untracked
entries and no staged changes. API-006 is already complete. UI-012 work was
already in progress in the worktree and remains uncommitted; this audit neither
completes nor commits it. Historical completion receipts below are unchanged.

Four independently reproduced defects are repaired in scoped commits:

- AUD-08 / P1: public system metadata disclosed raw local model-cache paths and
  unsafe build values. `762bda6` reuses the registry identifier allowlist;
  rejected model values become null and unsafe build values are omitted.
- AUD-05 / P2: separate database instances could apply the same pending
  migration snapshot. `da2a2a5` holds the existing per-path reentrant lock
  across the complete initialization operation.
- AUD-06 / P2: old Search page success/error could overwrite a newer search;
  old paging could start during submission. `fbf433b` invalidates its epoch,
  checks abort, and suspends paging until the new snapshot settles.
- AUD-07 / P2: Stop discarded answer tokens awaiting the render flush.
  `ec0ef58` preserves the owning message's buffer before stopping and clears it.

Actual final gates: frontend 85 files / 688 tests, TypeScript and production
build PASS; affected backend slices 151 and 103 passed; paired-browser Search
and streaming gate 30/30. Final full backend result is recorded in the authored
[audit report](ENGINEERING_AUDIT_2026-09-27.md).
No P0 was verified; these checks are not exhaustive security assurance.

Existing UI-012 and unrelated dirty work remain preserved. Collections bearer
integration remains staged; the known Unicode highlight defect remains P3;
migration serialization is in-process, not a multi-process migration protocol.
Next action: return to UI-012 validation/documentation/closure under its own
scope, then the graph's cross-layer/visual gates. Do not restart API-006.

## UI-012-A — Exact operational product contract (2026-09-27)

### UI-012-B/C/D/E — Implemented foundation and focused verification

Typed transport now consumes DATA-005 summary/timeseries/logs, protected
configuration status, public system facts, and public `/models` descriptive
provider flags. Transport constructs allowlisted objects before React state,
preserves null/zero, caps timeseries at 720, validates identities and returns
status-only errors without reflecting API bodies. Shared abort/epoch reads are
range/filter/cursor/refresh/session bound and hide stale data during render.
Analytics shows exact rate populations, measured/unknown durations, namespace
and outcome job counts; UTC points have a table and no connecting/interpolated
line. Logs preserves API order, category/severity/outcome and opaque cursors;
details are presentation-only. Settings reuses app presentation/storage/import
owners and the memory-only session, with read-only policy/capability/provider
flags. Provider presence/unknown availability is never health. No backend edit.

Retired browser Analytics writer, range/store modules and obsolete tests;
historical browser storage is left untouched. Updated route/copy ownership.
Focused first pass: 70/70 including the existing three shared-session tests;
subsequent provider transport addition yields 68 task-focused tests. TypeScript
and build passed. Initial full Vitest had the previously recorded 5-second App
history timeout; isolated App rerun passed and full rerun passed 85 files / 681
tests without changing timeout/assertions. Build retains the existing aggregate
chunk warning. Rendered Chromium exposed select accessible names including
their options; explicit control names fixed that. Screenshot review also added
the missing shared secondary-button geometry. Browser validation is ongoing;
these observations are not a completion claim.

RECORDED BEFORE IMPLEMENTATION. Starting HEAD `cbfdfda`; tracked/staged tree
clean, all 12 unrelated untracked paths preserved. Only UI-012 is authorized.

Routes: `/analytics`, `/logs`, `/settings`, retaining `/settings?panel=architecture`.
Analytics reads protected DATA-005 summary and timeseries. URL selectors are
`range=24h|7d|30d`, `interval=hour|day`, and the five backend metric identities.
Summary preserves outcome counts, rate numerator/denominator, known/unknown
duration populations and terminal-job namespace/outcome counts. Timeseries plots
only returned UTC buckets, at most 720; null is absent measurement, zero is real.
An accessible table accompanies unsmoothed observations. Explicit refresh only.

Logs reads protected `GET /logs`, category request/job, level info/warning/error,
limit 50 and unmodified opaque cursor. Category/level/cursor live in URL history;
filter changes reset cursor. Server order is retained. Row disclosures show only
projected safe facts; severity, outcome, job identity and request correlation
remain distinct. Seven-day API projection excludes conventional process logs.

Settings support matrix: browser theme and EN/VI language are editable through
existing app owners; backup/export/import and storage recovery reuse existing
conversation owners; local connect/disconnect reuse UI-010 memory-only session.
Protected `/system/configuration-status` supplies deployment/capability flags.
Public `/system/info` supplies only explicitly projected safe current facts.
No `/workspace/settings` GET/PATCH exists (router inventory/source confirms the
master's planned routes have not been implemented). Thus operational retention
30 days / logs 7 days is read-only and no server Save, retention toggle, provider
switch, model switch, arbitrary configuration, user or key manager is created.
Provider/model details link to UI-009 rather than duplicate registry controls.
No backend addition is required by this capability-based UI-012 scope.

References: all nine local PNGs match the gap-matrix inventory. None is dedicated
to Analytics, Logs or Settings. Evaluation's 1586×992 reference was inspected
only for established shared chrome, compact cards/table and disclosure language;
there is no screenshot-parity target or borrowed metric. Existing design tokens
and completed shell are the visual authority for these three pages.

Task semantics: enter a direct route, inspect terminal operations or current
configuration, explicitly connect for private reads, select scope/filter or
refresh, see server facts; recover with reconnect/retry without false empties.
Hierarchy: heading/source boundary, controls, access state, then metrics/chart
or log list, or grouped Settings. Components own page queries; app owns route,
theme/storage and session; transport projects fields before state. No new store.
AbortController plus monotonic epoch and selection/session identity guard every
read and cleanup. Errors belong to that read. Page content owns scrolling;
bounded tables scroll locally; mobile logs become cards and settings stack.

State matrix: disconnected, connecting, loading, ready, real empty, null-duration,
401 unauthorized, 403 denied, 404 private unavailable, 422 invalid selectors,
503/network unavailable, unexpected response, refreshing and read-only. No
inaccessible state becomes zero. Self-review risks: null/zero confusion; stale
range/filter/session replies; unsafe extra JSON fields; dead settings controls;
compact layout/long-ID overflow.

Planned files: operational typed client/types/fixtures/query hook; Analytics
replacement; Logs page; Settings page/shared connection; narrow App/routes/copy
integration; focused client/component/lifetime/privacy tests; dedicated hermetic
Playwright suite; docs. Legacy browser Analytics will lose dashboard authority
and its unnecessary event writer will be retired without deleting stored user data.

Gates: focused tests → TypeScript → full Vitest → build → Chromium/Firefox;
route/shell neighbors, light/dark EN/VI axe, reduced motion and rendered review
at 1586×992, 1440×900, 1280×856, 1024×768, 768×900, 390×844, 1440×700
(plus skill widths 1366/1920). Zero body/root overflow. Native browser zoom is
a separate manual gate if automation cannot operate browser chrome. Audit exact
tracked artifacts/secrets; commit intended files and preserve all unrelated work.

Exact Next Action: UI-012-B through E implementation and focused validation.
After full acceptance verify TEST-002 from the graph and stop before starting it.

Implementation through EVAL-003 is COMPLETE. Historical receipts remain below;
the latest EVAL-003-A..G and post-rebuild audit receipts are at the end. The next dependency-ready task
per the master-plan graph is UI-011 — Evaluation (not started).

## Last Completed Checkpoint

EVAL-003-G — Frozen budgeted native jobs. EVAL-003 is COMPLETE
(sub-checkpoints A through G). Exact next action: UI-011 — Evaluation;
do not begin it as part of EVAL-003 closure.

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

## UI-004-E/F/G Final Checkpoint (gates, audits, UI-004 COMPLETE)

### Task Status

UI-004 COMPLETE.

### Gates

- `bun run lint` (tsc) — PASS.
- `bun run test` — PASS: 70 files / 398 tests (397 baseline + 1 net new after the contract updates).
- `bun run build` — PASS.
- Chromium full suite — PASS: 128 passed, 2 intentional skips, 0 failed (baseline 125/2; +3 is the new UI-004 spec).
- Firefox full suite — PASS: 128 passed, 2 intentional skips, 0 failed.
- Nine-reference non-regression receipt — PASS: 15/15, unchanged.
- `git diff --check` — clean; artifact audit — no stray screenshot, dump, or runtime file from UI-004 (the pre-existing `.audit-runtime/` pdf-viewer captures belong to an earlier audit and were left untouched and uncommitted).
- Backend untouched, so its 969 / 0 / 188 baseline stands.

### Commit

- `64cf364` — `feat(ui): compose the reference four-pane source and document workbench` — 26 files, 3493 insertions. Scope verified: frontend and documentation only; no `src/`, `data/`, `scripts/`, or tool-scratch path is included. The body discloses the mixed ownership: the workbench shell files were uncommitted from the earlier validated rebuild and cannot be split from this change because the app cannot build without them.

### Dirty-Tree Result

- 165 → 153 dirty paths. UI-004-owned work is committed; unrelated prior rebuild work (other feature components, hooks, libs, styles) is preserved.

### Known/Pre-existing Issues

- Six frozen frontend integration expectation failures; timing-sensitive Firefox class (not observed in this run).
- Cosmetic limitation with no reference target: at 390px the evidence sheet's content can scroll horizontally inside the panel; body/root overflow is asserted zero.

### New Regressions

None.

### Exact Next Action

UI-005 — Documents (dependencies UI-002 and API-003 are satisfied; it is the earliest undone dependency-ready row in the master-plan table). Do not start UI-005 without explicit user authorization.

## UI-005-A Quota-Safe Checkpoint (recovery, scope, reference measured, ownership mapped)

### Active Task

UI-005 — Documents. Status: ACTIVE (A complete; implementation started).

### Verified Current State

- UI-004 COMPLETE (`64cf364`); backend 969 / 0 / 188; frontend 70 files / 398 tests; Chromium and Firefox 128 passed / 2 skipped; nine-reference receipt 15/15. Dirty tree ≈154 paths.
- Master-plan row: `| UI-005 | Documents | UI-002, API-003 | Documents feature | Filter/select/read/save | API-004 |` — dependencies satisfied, so UI-005 is the correct Exact Next Action.
- `frontend/src/types.ts` still holds the previously disclosed mixed uncommitted work (UI-003/API-005 hunks); this task adds catalog types to it and will follow the same disclosure rule.

### Master-Plan Scope (read, not inferred)

- Visual: "filters/statistics/table/detail rail with four tabs".
- Frontend: "type/year/sort/page-size/selection/collection picker".
- Done: "real counts and exact document identity across actions".
- Gap-matrix rows owned here: company/content search, type/year/section filters, counts (metric cards), sort/page-size/pagination, selectable table, detail tabs (P1), summary as an **honest label** with no LLM invention (P2), representation/preview (P0), "Add to collection" partial (no server document collection yet), "Import/My documents" (P3 → hide).
- The `type` filter is explicitly out of reach: API-003 established that no stored artifact records a per-filing form type, and this goal repeats that it must not be hardcoded.

### Documents Reference Measured

`docs/ui-references/documents-ui-reference-dark-v1.png` — 1586x992, roughly 215 navigation | 960 main | 410 detail rail:

- Main header: icon tile + "Documents" + subtitle, with page actions at the right.
- Search row: full-width input plus Clear/Search controls.
- Filter row: four selects (Company/Ticker, Filing Type, Year, Section) plus an ownership toggle.
- Stats row: four metric cards (totals, companies, chunks, and a success percentage).
- Table card: "Documents (N)" + subtitle, "Sort by [Filing Date (Newest)]" and "[20 per page]" at the right; columns checkbox, Company (logo + name), Ticker, Filing Type, Filing Date (sorted), Sections, Chunks, Actions (open, inspect, bookmark); dense rows with a selected/hover treatment; footer "Showing 1-10 of N" plus numbered pagination.
- Detail rail: "Document Details" header with identity (company, AAPL, date) and an external-link action; tabs Overview / Sections (N) / Representations / Metadata; Overview holds a summary block, a metadata grid, a Representations block with Available/Unavailable cards, a white Document Preview, and three actions.

Truthful deltas to implement (recorded before coding): no Import/Manage actions (no upload or ownership capability), no ownership toggle, no Filing Type filter or column, no processing-success metric (no contract measures it), no brand logos (a ticker-derived letter avatar instead), no per-row bookmark (no server-side document collection yet), the summary becomes an honest factual label rather than generated prose, and "Fiscal Year End"/"Total Pages" are replaced by the recorded report date.

### Existing Ownership Mapped

- `frontend/src/components/DocumentExplorerPanel.tsx` (758 lines) already renders the page header, search, ticker/section filters, a table with pagination, and a detail rail whose four tabs (Overview / Sections / Representations / Metadata) already match the reference. It also owns loading/error/retry, focus helpers, chunk browsing and the reader manifest.
- `frontend/src/lib/api.ts` already exposes the catalog list, chunks, original/reader/PDF routes; it did not yet expose API-003's `/documents/facets`, `/documents/stats`, or the `year`/`sort`/`direction` parameters, which this task added.
- The reader/document workspace composition from UI-004 is reused rather than rebuilt (the panel's "Open document workspace" action and the `/documents/:documentId` route hand off to it).

### Planned Files

- Modified: `frontend/src/lib/api.ts` (catalog client), `frontend/src/types.ts` (catalog types), `frontend/src/components/DocumentExplorerPanel.tsx` (header density, stats, filters, sort/page size, table columns), `frontend/src/styles/console.css` (reference density/chips), plus focused tests and a new `frontend/e2e/ui-005-documents.spec.ts`.
- Backend: none expected; API-003 already exposes every field the truthful composition needs.

### Exact Next Action

Implement the api client + types (done), then the panel's stats row, filter row (year + facet counts + clear), sort and page-size controls, and the table columns.

## UI-005-F/G Final Checkpoint (gates, audits, UI-005 COMPLETE)

### Task Status

UI-005 COMPLETE.

### Delivered Composition

The Documents page now reads API-003 as its catalog truth instead of computing
anything from the loaded page of rows:

- `getDocumentStats` feeds the four metric cards (documents, companies, chunks,
  form type) and the filing-year range hint. The form-type card reports
  `Unknown` with API-003's own reason, because no stored artifact records one.
- `getDocumentFacets` feeds the filter options, so each option carries API-003's
  count under its documented basis `all_filters_except_own_dimension`. The year
  select only exists once the facet reports the dimension as recorded; a filter
  with no recorded values is not rendered as a dead control.
- The list request gained `year`, `sort`, `direction`, and `page_size`; sorting
  and page size are real query parameters (sort by filing date newest/oldest,
  ticker A-Z, chunks most; 10/20/50 rows), and the request cache key covers them.
- The table lost its Type column, the detail rail lost its form-type badge, the
  Overview summary is a factual label, and the Metadata tab reports the
  unavailable form type with its reason. Nothing on the page names a form type.
- `Clear filters` resets search, company, section, year, and page in one action.
- Reference elements with no capability behind them stay absent: Import
  Documents, Manage Sources, the header overflow menu, the ownership toggle, the
  processing-success metric, and the sidebar storage meter.

### Gates

- `bun run lint` (tsc) — PASS.
- `bunx vitest run` — PASS: 70 files / 403 tests (398 baseline + 5 new panel tests).
- `bun run build` — PASS.
- `frontend/e2e/ui-005-documents.spec.ts` — PASS on Chromium and Firefox: 10/10.
- Full hermetic browser gate at 4 workers — PASS: 262 passed, 4 skipped, 4 failed.
  All four failures are the frozen load-sensitive timing class
  (`regression.spec.ts:65` evidence inspector, `regression.spec.ts:1033`
  composer p95 budget, `workspace-performance.spec.ts:176` synthetic baselines);
  each passes when re-run in isolation on both browsers (6/6), and none touches
  the Documents page.
- The same full gate at 12 workers produced 25 failures; every one was
  re-verified. The only systematic cause was the fixture gap below, now fixed;
  the rest are the same timing class under full-machine load.
- `bun run lint` after the fixture change — PASS.

### Fixture Gap Found And Closed

The default `/documents` fixture did not answer `GET /documents/stats` or
`GET /documents/facets`, so every existing journey that mounts the Documents
route failed loudly with `Unexpected API request in test`. The fixture now
answers both routes for the default single-document corpus and keeps the richer
12-row dataset behind `catalog: true`, so the other journeys' exact
expectations are unchanged.

### Receipts

`frontend/test-results/ui-005/` — 12 PNG receipts (six viewports x two
browsers): 1586x992 (reference-native), 1440x900, 1280x856, 1024x768, 390x844,
and 1440x700 (short). The receipt test asserts the panel is actually painted
(computed opacity > 0.99) before capturing, because the console view-entry
animation starts at opacity 0 and would otherwise yield a blank receipt; the
screenshots are taken with `animations: "disabled"` for the same reason. At
1280px and wider the test also asserts the detail rail sits beside the table
rather than below it, matching the reference.

### Real Defects Found By The New Tests

- A blank 1586x992 chromium receipt: the first capture raced the
  `console-fade-up` entry animation. Fixed in the receipt procedure, not by
  weakening the assertion.
- `Unknown` broke mid-word in the narrowest stat card. Added
  `.console-stat__value--status` (1rem) in `console.css`; a Tailwind
  `text-base` cannot win here because unlayered component CSS beats Tailwind's
  utility layer in this build.
- The filter row order now follows the reference (Company, Year, Section).

### Commit Scope And Mixed Ownership

UI-005-owned paths: `frontend/src/components/DocumentExplorerPanel.tsx`,
`frontend/src/components/DocumentExplorerPanel.test.tsx`,
`frontend/src/lib/api.ts`, `frontend/src/types.ts`,
`frontend/e2e/fixtures.ts`, `frontend/e2e/ui-005-documents.spec.ts`,
`docs/UI_REBUILD_PLAN_CHECKPOINT.md`, `PROJECT_STATE.md`,
`docs/frontend/FRONTEND_CONTRACT.md`.

`frontend/src/types.ts`, `frontend/e2e/fixtures.ts`, and
`DocumentExplorerPanel.tsx` also carry earlier validated rebuild work that
cannot be split by hunk, and it is disclosed in the commit body. The two UI-005
rules in `frontend/src/styles/console.css` remain uncommitted with that shared
rebuild stylesheet (1751 lines, never tracked, imported by the dirty
`index.css`); they are `.console-header-select` and
`.console-stat__value--status`, and they travel with the stylesheet when it is
committed.

### Known/Pre-existing Issues

- The frozen load-sensitive timing class above, and the six frozen frontend
  integration expectation failures recorded before UI-004.
- Under full-machine load the same specs fail more often; isolation is the
  documented way to tell them apart from a real regression.
- `PipelineConsole.tsx` passes `text-base` alongside `console-stat__value` for
  its readiness word; that override cannot win for the same layering reason.
  Left untouched as outside UI-005 scope.

### New Regressions

None found. Every failure in the full gate was reproduced as a load-sensitive
timing flake or was the fixture gap, which is fixed.

### Exact Next Action

UI-006 — Search. The master-plan table orders it immediately after UI-005 and
both of its dependencies are complete (`UI-002` router/shell, `API-004`
discovery snapshots). `UI-007` (Retrieval/Reranker, needs `API-005`, complete)
and `DATA-003` (Typed collections, needs `DATA-001`/`DATA-002`, complete) are
also dependency-ready. Do not begin any of them without a new instruction.

## UI-006-A Quota-Safe Checkpoint (recovery, contract, reference, real-data probe)

### Active Task

UI-006 — Search. Status: ACTIVE (A complete; implementation starting).

### Recovery Verified

- HEAD `a4c76ea` (UI-005) on `codex/bilingual-research-workspace`; dirty tree 148
  paths. UI-001…UI-005, API-001…API-005, DATA-001/DATA-002, TEST-001 complete.
- No partial UI-006 work exists: the only UI-006 text in the repository before
  this run was the UI-005 "Exact Next Action" line.
- Master-plan row: `| UI-006 | Search | UI-002, API-004 | Search feature |
  Group/facet/expiry/handoff | Collections backend |`. Both dependencies are
  complete, so UI-006 is the correct Exact Next Action.
- The current Search page is the **old diagnostic substitute**: the existing
  page calls `POST /retrieval/inspect` (API-005) with hybrid/dense/BM25 presets
  and renders a trace, not discovery search. The gap matrix records exactly this
  gap (`| Search | Keyword/natural language | Yes | Diagnostic substitute |
  Inspection | Primitives | Discovery | Discovery service | P1 |`). It is
  replaced, not preserved.

### Master-Plan UI-006 Scope (read, not inferred)

- Visual: ranked highlighted cards and metrics/facets/recent rail.
- Reuse: safe highlights, source presentation, reader/handoffs.
- Frontend: keyword/hybrid discovery, grouping/pagination; remove engineering
  presets from the primary flow.
- Backend/API: bounded snapshots, prefilters, scoped facets, expiry.
- Persistence: browser recent queries, explicit saves, temporary snapshots.
- Risks: bounded candidate counts represented as whole corpus totals.
- Tests: prefilters, expiry, empty pages and research/open/save handoffs.
- Done: scoped counts and stable snapshot navigation.
- Gap-matrix rows owned here: discovery query (P1), collection/type/date filters
  (P1), grouping (P1), highlights (P1), count/latency/score scope (P0), facets
  rail (P1), recent/saved (P2), research/open/save actions (P1), pagination (P1).

### API-004 Contract (verified in source, not assumed)

`POST /search` (`src/api/routers/search.py`, rate limit `30/minute`) and
`GET /search/{search_id}`.

- Request: `query` (2..200 chars), `mode` (`Literal["keyword"]`), `group_by`
  (`"document" | "chunk"`), `ticker`, `section`, `year`, `filing_date`, `page`,
  `page_size` (1..50).
- Response: `search_id`, `query{text,normalized,mode}`, `grouping{group_by,
  group_count,hit_count}`, `engine{key,version,definition}`, `scope{ticker,
  section,year,filing_date,documents,count_scope,candidate_ceiling,
  limited_by_ceiling,matched_documents,matched_chunks}`, `items` (groups or
  hits), `total`, `page`, `page_size`, `facets` (API-003 `CatalogFacet`s for the
  scope), `created_at`, `expires_at`, `ttl_seconds`.
- Hit: `chunk_id`, `document_id`, `ticker`, `section`, `filing_date`,
  `report_date`, `chunk_index`, `score`, `snippet{text,ranges,truncated}`.
- Group: `document_id`, `ticker`, `filing_date`, `report_date`, `sections`,
  `best_score`, `hit_count`, `hits`.
- Bounds: `CANDIDATE_CEILING = 200`, `SNIPPET_MAX_LENGTH = 240`,
  `SNIPPET_MAX_RANGES = 8`, `SNAPSHOT_TTL_SECONDS = 900`, `MAX_SNAPSHOTS = 50`,
  `DEFAULT_PAGE_SIZE = 20`, `MAX_PAGE_SIZE = 50`.
- Count semantics: `total` is the pageable length of the **bounded** set;
  `count_scope` is `bounded_candidates` or `no_matches`; `limited_by_ceiling`
  says discovery stopped at the ceiling. `matched_documents`/`matched_chunks`
  are the bounded set's own totals.
- Ranking: BM25 lexical only (`engine.key = bm25_lexical`, v1). The engine
  definition states the score is a ranking signal, explicitly **not** confidence,
  accuracy, or probability.
- Facets: API-003 aggregation for the same scope, so a facet counts **documents
  in scope** under `all_filters_except_own_dimension`, never matches.
- Errors: 422 validation, 404 unknown snapshot, 410 expired snapshot, 429 rate
  limit. No sort parameter exists; order is the engine's deterministic
  score-then-id order.

### Search Reference Measured

`docs/ui-references/search-ui-reference-dark-v1.png` — 1586x992, the same shell
as the Documents reference: 220px navigation, 56px top bar, then approximately
390px of right rail and ~980px of main column.

- Main header: search icon tile + "Search" + subtitle, with three page actions
  ("Search Examples", "Saved Searches", overflow) that have no capability here.
- "Search Query" card: label, a tall query field with a clear control, a
  "Search in" chip row of collections/filing types, a filter row (Company, Date
  Range, Document Type, Section), an "Advanced Filters" button, and a prominent
  "Search" submit button.
- Results toolbar: "Showing 1-10 of 248 results (0.8s)", "Sort by Relevance",
  a "Group by document" toggle, and "10 per page".
- Result cards: left rank box, score pill, meta chips (company, filing, section,
  page), a heading line, a two-line snippet with inline highlight marks, then
  "Use in Research", "Open Document", "Save as Evidence" and an overflow.
- Right rail: "Search Overview" 2x2 metric tiles (companies searched, results
  found, search latency with engine name, top result score with a qualitative
  label), "Refine Search" (quick-filter chips with counts, a companies select,
  filing-type checkboxes, a date-range select), "Recent Searches" (query text,
  relative time, result count, "View all").

Truthful deltas recorded before coding: no page actions (no examples, saved
searches, or overflow capability), no "Search in" collection/type chip row
(collections are DATA-003 and no filing-type dimension exists), no Document Type
filter, no "Advanced Filters" button (every real filter is already in the row),
no sort select (API-004 has no sort parameter — order is the engine's), no
latency tile (latency is not exposed), no qualitative "High relevance" label,
no filing-type checkboxes, no "View all" for recents, and no page ("p. 12")
metadata (the corpus has no page numbers). The reference's per-document cards
correspond to API-004's chunk ordering; our grouped card is one filing with its
`hit_count`, and the ungrouped card is one chunk.

### Real-Corpus Probe (provider-free, read-only)

`scripts/diagnostics/ui006_discovery_probe.py` (new, this task) loads the real
embedded chunks and builds the same BM25 index the retriever builds at startup,
then runs the real `DiscoveryService`. Real results:

- 10,053 chunks, 50 documents, 50 tickers, 5 sections (business 50,
  risk_factors 50, mdna 46, financial_statements 46, financial_table), filing
  years 2026 (42 documents) and 2025 (8).
- `"cloud revenue"` → 15 grouped filings, 200 bounded hits,
  `limited_by_ceiling: true`, top group MSFT with `best_score` 10.703384 and
  `hit_count` 43; snippets carry a leading "…" and ranges that index into the
  returned text.
- `"supply chain"` chunk mode → 200 hits across 33 documents, page 2 returns a
  different deterministic page.
- `"zzqqxx nonexistentterm"` → `count_scope: no_matches`, `total: 0`.
- `query="cloud revenue", ticker=AAPL, year=2026` → `scope.documents: 0`, so
  zero matches: the date filter is a real, observable axis because AAPL's filing
  in this corpus is a 2025 filing.

Consequence for the UI: `limited_by_ceiling` is true for ordinary queries, so
the count label must always read as a bounded discovery count plus the ceiling
note, and the rail's facet counts must be labelled as scope documents.

### Existing Implementation Mapped

- The old `SearchWorkspace` component + test — the diagnostic page being
  replaced and deleted.
- `frontend/src/lib/api.ts` — no discovery client exists yet; it already owns
  `ApiError` (status/code/retryAfterSeconds) and `apiFetch`, so the new client
  functions reuse them and no new dependency is needed.
- `frontend/src/types.ts` — no discovery types yet.
- `frontend/src/App.tsx` — mounts the page at `/search` with `onUseQuestion`,
  `onOpenDocument` (document workspace), `onOpenSource` (standalone evidence
  reader), `onSaveEvidence`, `onScopeChange`.
- Preserved contracts: `article.console-result` per result, visible labels "Use
  in Research" / "Open Document" / "Save as Evidence", focus ids
  `search-document-workspace-<chunk>`, `[data-workbench-route-origin='search']`,
  and "Back to Search" focus restoration.
- `frontend/e2e/fixtures.ts` — mocks only `/retrieval/inspect` for Search today;
  it gains hermetic `POST /search` and `GET /search/{id}` handlers built from
  the real shapes recorded above (no provider, no corpus).

### Shared-File Ownership

`frontend/src/types.ts`, `frontend/src/lib/api.ts`, `frontend/e2e/fixtures.ts`
already carry earlier validated rebuild work that cannot be split by hunk; new
UI-006 additions go into them and will be disclosed. The shared untracked
`frontend/src/styles/console.css` (1751 lines) is **not** claimed by UI-006:
new Search styles go into a new UI-006-owned `frontend/src/styles/search.css`,
while existing `console-*` primitives are reused rather than re-implemented.

### Stitch Strategy

One Stitch generation for the Search composition (query card, filter row,
result cards, metrics/refine/recent rail) as a structural second opinion, then
reconcile against the reference screenshot, which wins. Demo data from Stitch
is discarded; nothing renders from it. Result recorded in UI-006-B.

### Planned Files

- New: the new `frontend/src/components/search/` page set (page, query card,
  result card, snippet renderer, rail), `frontend/src/lib/searchModel.ts`,
  `frontend/src/styles/search.css`, `frontend/e2e/ui-006-search.spec.ts`.
- Modified: `frontend/src/lib/api.ts`, `frontend/src/types.ts`,
  `frontend/src/App.tsx` (mount the new page), `frontend/src/index.css` (import
  the new stylesheet), `frontend/e2e/fixtures.ts`, the three e2e specs that
  drive the old Search selectors, checkpoint/PROJECT_STATE/FRONTEND_CONTRACT.
- Deleted: the old `SearchWorkspace` component and its test (replaced).
- Backend: none planned; API-004 already exposes every field the reference needs.

### Exact Next Action

UI-006-B: add the typed API-004 client and types, build the reference Search
page (query card, filters, results, rail) on the snapshot lifecycle, keep the
preserved identity/handoff contracts, and capture the first receipt.

## UI-006-B/C/D/E Checkpoint (page, snapshot lifecycle, results, handoffs)

### Active Task

UI-006 — Search. Status: B, C, D, E complete; F/G/H remain.

### Files Created

- `frontend/src/lib/searchModel.ts` — pure Search helpers (page ranges in the
  snapshot's own unit, ceiling note, score formatting, range-based snippet
  segmentation, scope summary, recent-search storage, error classification).
- `frontend/src/components/search/DiscoverySearchPage.tsx` — the page and its
  snapshot lifecycle.
- `frontend/src/components/search/SearchQueryCard.tsx` — query field, real
  filter axes, submit.
- `frontend/src/components/search/SearchResultCard.tsx` — one ranked result.
- `frontend/src/components/search/SearchResultSnippet.tsx` — safe range
  highlighting.
- `frontend/src/components/search/SearchRail.tsx` — overview, refine, recent.
- `frontend/src/styles/search.css` — UI-006-owned Search styles.
- `frontend/src/lib/searchModel.test.ts` (15 tests),
  `frontend/src/components/search/DiscoverySearchPage.test.tsx` (15 tests),
  `frontend/e2e/ui-006-search.spec.ts` (9 tests).
- `scripts/diagnostics/ui006_discovery_probe.py` — real-corpus probe (kept: it
  is the evidence source for the fixture shapes and it is provider-free).

### Files Modified

- `frontend/src/types.ts` — discovery types (client-owned, mixed-history file).
- `frontend/src/lib/api.ts` — `createDiscoverySearch` (POST, the only snapshot
  write) and `getDiscoverySnapshot` (GET, paging without re-searching).
- `frontend/src/App.tsx` — mounts the new page; the old page's global-scope
  callback was removed with it.
- `frontend/src/index.css` — imports the new stylesheet.
- `frontend/e2e/fixtures.ts` — hermetic `POST /search` + `GET /search/{id}`
  handlers (per-test snapshot store, 404/410 options, derived facets).
- `frontend/e2e/v5-07-handoffs.spec.ts`, `frontend/e2e/regression.spec.ts`,
  `frontend/e2e/reconciliation-reference.spec.ts` — Search selectors and the
  saved-evidence label updated for the rebuilt page.

### Files Deleted

- `frontend/src/components/SearchWorkspace.tsx` and its test — the replacement
  is the new page set above.

### Snapshot Lifecycle (implemented, tested)

- Typing only edits a draft: no request at all, proven by unit and browser
  tests (`calls.posts` stays empty while the field changes).
- One submit creates exactly one snapshot (`POST /search`); the page renders the
  snapshot's own `query.text` and `scope`, so unsubmitted typing can never
  relabel the results on screen.
- Paging and page-size changes call `GET /search/{search_id}` on the same
  snapshot (`page_size` is a GET parameter), never a second POST.
- Opening a result, saving evidence, switching detail state, and rerendering
  issue no POST.
- A newly committed query, filter scope, or grouping is a new snapshot: the
  grouping switch is part of the stored snapshot, so it POSTs again with the
  same submitted query and scope.
- Draft filters are instantly visible but only apply on the next submit; the
  page says so ("New filters apply on the next search").
- Stale responses cannot win: request-id guards plus `AbortController` per
  request, covered by a test that resolves an older submission after a newer
  one.
- Reload does not silently re-run the query: snapshots stay runtime-only, and
  the page honestly returns to its initial state.

### Results, Counts, Score Semantics

- Every card comes from API-004: real `chunk_id`, `document_id`, ticker,
  section, filing date, `hit_count`, `score`, and the snippet with its ranges.
- Highlights are the API's ranges sliced into React nodes; no HTML from the
  response is interpreted, and Unicode/Vietnamese text survives intact.
- Counts are bounded and labelled as bounded: the toolbar and footer show
  "Showing 1–20 of 22 filings", and when `limited_by_ceiling` is true the card
  states that discovery ranked the first N candidates rather than claiming a
  corpus total. No fabricated total appears anywhere.
- Scores are shown as raw BM25 numbers labelled `BM25`; there is no percentage,
  no confidence, and no qualitative relevance label. The engine's own
  definition is reachable in the rail.
- The rail's metric tiles read the snapshot's real scope: companies in scope,
  result filings (with the other unit's matching count), matching excerpts with
  the ceiling state, and the top BM25 score with the engine identity.
- The rail's section chips are API-003 scope counts, labelled "Sections in
  scope (N filings)"; zero-count sections are not offered.
- No-match snapshots render the submitted query, the real scope, and a
  no-sample-result empty state.

### Error And Expiry States

`410` renders an expired-snapshot message with an explicit "Run the search
again" action and keeps the previous results visible; `404` renders the unknown
snapshot state; `429` reports the rate limit once and never retries in a loop;
`422` shows the API's own validation message. None of them collapses into an
empty result list.

### Handoffs And Routes Preserved

- `article.console-result` stays the result container, with the visible labels
  "Use in Research", "Open Document", "Save as Evidence" and the accessible
  names `Open document workspace` / `Save evidence`.
- Focus ids stay `search-document-workspace-<chunk>`, the workbench still marks
  `[data-workbench-route-origin='search']`, and "Back to Search" restores focus
  to the opener (verified by the existing V5-07 spec, which now drives the new
  page).
- "Open Document" hands the reader the exact `chunk_id`/`document_id` and the
  URL stays `/search`, so no second identity scheme was invented.
- The page issues no conversation, workspace, or provider write: the only write
  is the explicit Save evidence action, asserted by a request listener.

### Tests Actually Run

- `bunx vitest run src/lib/searchModel.test.ts src/components/search/DiscoverySearchPage.test.tsx`
  — 30/30 pass (2 files).
- `bunx vitest run` — 71 files / 422 tests pass.
- `bun run lint` (tsc) — clean after every edit.
- `bunx playwright test e2e/ui-006-search.spec.ts` — 9 tests, pass on Chromium
  and Firefox (18/18).
- `bunx playwright test e2e/v5-07-handoffs.spec.ts` — 4/4 pass.
- `bunx playwright test e2e/regression.spec.ts:441` — pass.
- `bunx playwright test e2e/reconciliation-reference.spec.ts --project=chromium`
  — 15/15 pass, so the nine-reference receipt still holds with the rebuilt
  Search page (r3-search and r4-library included).

### Real Defects Found By The Tests

- The V5-07 and regression handoff specs addressed `Save evidence` /
  `Open document workspace` without scoping; with a ranked list of results those
  names are legitimately ambiguous. The specs now scope to the card they open,
  which is what those flows always meant.
- The Search fixture initially returned excerpts whose chunk identities the
  reader fixtures cannot resolve. The best-ranked fixture excerpt is now the
  fixture catalog chunk (`AAPL_fixture_revenue_0`), so a result handoff lands on
  a real fixture chunk.
- `searchModel` time formatting compares the reader's local calendar day; the
  first test used fixed UTC instants and was wrong on this UTC+7 machine. The
  test now builds local dates.

### Stitch Result (recorded honestly)

One generation was requested for the Search composition in the existing
high-fidelity project. The MCP client timed out at its 30s limit, no new screen
was created (the project still lists the same screens as before this run), and
the asset download reported success without writing to any path reachable on
this host. Stitch therefore contributed no structure to this page; the
reference screenshot remained the only visual authority, which is also the
documented precedence. The two pre-existing Search screens in that project
predate this run and were not used as design input.

### Remaining Work

UI-006-F (responsive/a11y pass and the visual comparison loop), UI-006-G
(tsc/lint/full Vitest/build), UI-006-H (controlled Chromium/Firefox gates,
nine-reference receipt, artifact/diff audit, docs, commit).

### Exact Next Action

Run the visual comparison loop against
`docs/ui-references/search-ui-reference-dark-v1.png` at the reference viewport,
list the largest remaining deltas, fix what is fixable truthfully, then run the
UI-006-G/H gates.

## UI-006-F/G/H Final Checkpoint (visual loop, gates, audits, UI-006 COMPLETE)

### Task Status

UI-006 COMPLETE.

### Visual Comparison Loop Result

Compared `frontend/test-results/ui-006/search-1586x992-chromium.png` against
`docs/ui-references/search-ui-reference-dark-v1.png` (1586x992) across two
iterations. Matched: page header identity (icon tile, title, subtitle), the
query card with its label, tall field, clear affordance, filter row and primary
Search button with the trailing arrow, the results toolbar (count line, engine
chip, grouping switch, rows-per-page select), the ranked cards (rank box, meta
chips, bold heading, highlighted excerpt, three actions, right-aligned score
pill), and the right rail's three-card composition (overview tiles, refine
filters, recent searches).

Deltas closed this round: a duplicated section chip that repeated the card's own
heading, a zero-count section chip the reference never shows, and the rail
metric tiles' surface (which also fixed a contrast finding).

Deltas that stay, each recorded as a truthful deviation rather than copied:
no page-level actions (no examples, saved searches, or overflow capability); no
collection/type chip row or Document Type filter; no Advanced Filters button;
no sort selector because the engine owns the order; the engine chip replaces the
reference's "Sort by Relevance"; the cards' heading is the excerpt's section
because API-004 exposes no document heading; the score pill shows a raw BM25
number instead of the reference's 0-1 relevance value; the rail's fourth tile
reports the top BM25 score with the engine identity instead of a fabricated
latency; the bounded-count strip is an explicit caveat the reference does not
have; and the query field starts empty with a placeholder example instead of the
reference's prefilled question, so nothing on first load looks submitted.

### Responsive And Accessibility Result

Receipts at 1586x992, 1440x900, 1280x856, 1024x768, 390x844 and 1440x700 pass
with body/root horizontal overflow at 0 at every width. At 390px the query card
stacks, the filters stay full-width, the toolbar wraps, and the cards remain
readable; the rail moves below the results. Accessibility: the query field is a
real labelled control inside a real form, Enter submits it (asserted), filters
keep their own labels, the result actions keep accessible names, and an
`axe-core` scan over `main` for contrast, label, button-name, link-name and
input-field-name rules reports no serious or critical violations. Scanning
mid-animation measured blended colors, so the scan disables motion first — the
same trap the receipt capture guards against.

### Gates (UI-006-H)

- `bun run lint` (tsc) — PASS.
- `bunx vitest run` — PASS: 71 files / 422 tests (403 baseline; the replaced
  Search test file left, 30 new Search tests arrived).
- `bun run build` — PASS.
- `bunx playwright test e2e/ui-006-search.spec.ts` — PASS: 9 tests, 18/18 with
  both engines.
- Controlled full gate, 4 workers — `bunx playwright test --config
  playwright.config.ts --workers=4`: **281 passed, 4 skipped, 5 failed**. All
  five failures were re-run in isolation and passed (7/7 focused reruns):
  `workspace-performance.spec.ts:176` (chromium + firefox synthetic baselines),
  `regression.spec.ts:65` (firefox evidence inspector),
  `app.spec.ts:153` (firefox template apply),
  `ui-004-source-document.spec.ts:63` (firefox composition receipt). None of
  them touches Search, and all belong to the documented load-sensitive class.
- Nine-reference receipt — PASS: all 15 surfaces on both engines (30/30),
  including `r3-search` and `r4-library`, which now drive the rebuilt page.
- UI-006's own 20 engine-runs inside the gate — all pass.

### Browser Worker Counts Recorded

UI-006 spec runs at the default worker count; the full gate ran at 4 workers
(12 workers is not a correctness baseline in this repository, per the recorded
policy). Focused isolation reruns used 1–2 workers.

### Artifact / Diff / Dependency Audit

- Dependency audit: UI-006 added **no** dependency. `frontend/package.json` and
  `bun.lock` show only the pre-existing rebuild entries (`pdfjs-dist`,
  `react-router-dom`), untouched by this task. No search, table, state, or
  highlight package was introduced.
- Artifact audit: no Playwright traces, videos, dumps, or scratch specs are
  staged; `frontend/test-results/` is git-ignored. The temporary contrast
  diagnostic spec used during the a11y pass was deleted. The Stitch download
  wrote no file into the repository.
- Secret audit: no credentials or keys in any new or modified file.
- `git diff --check` — clean.

### Commit Scope And Mixed Ownership

UI-006-owned paths: the new `frontend/src/components/search/` set,
`frontend/src/lib/searchModel.ts` (+ test), `frontend/src/styles/search.css`,
`frontend/e2e/ui-006-search.spec.ts`,
`scripts/diagnostics/ui006_discovery_probe.py`, the deletion of the replaced
`SearchWorkspace` component and its test, plus the UI-006 hunks in
`frontend/src/types.ts`, `frontend/src/lib/api.ts`, `frontend/src/App.tsx`,
`frontend/src/index.css`, `frontend/e2e/fixtures.ts`,
`frontend/e2e/regression.spec.ts`, `PROJECT_STATE.md`,
`docs/frontend/FRONTEND_CONTRACT.md` and this checkpoint.

Mixed ownership disclosed:
- `frontend/src/types.ts`, `frontend/src/lib/api.ts`, `frontend/e2e/fixtures.ts`
  and `frontend/e2e/regression.spec.ts` already carried earlier validated
  rebuild work that cannot be split by hunk.
- `frontend/e2e/v5-07-handoffs.spec.ts` and
  `frontend/e2e/reconciliation-reference.spec.ts` are still-untracked specs
  from earlier tasks; UI-006 re-pointed their Search selectors and the saved
  evidence label, and those edits stay with those files rather than being
  claimed here.
- The shared untracked `frontend/src/styles/console.css` was **not** modified by
  UI-006: the new Search styles live in the UI-006-owned
  `frontend/src/styles/search.css`.

### Known/Pre-existing Issues

- The load-sensitive browser class above (five specs), unchanged by UI-006.
- The six frozen frontend integration expectation failures recorded before
  UI-004 (excluded from the default gate).
- `frontend/src/styles/console.css` remains a large shared untracked stylesheet
  that the committed application depends on.

### New Regressions

None. Every gate failure was reproduced as a load-sensitive flake in isolation,
and the rebuilt page's own suites are green on both engines.

### Exact Next Action

The master-plan table orders `UI-007 — Retrieval/Reranker` (dependencies
`UI-002` and `API-005`, both complete) directly after `UI-006`, with
`DATA-003 — Typed collections` (`DATA-001`/`DATA-002`, complete) also
dependency-ready. Do not begin either without a new instruction.

### Commit And Post-Commit Records

- `622512f` — `feat(ui): rebuild discovery search on API-004 snapshots` — 22
  files, 4398 insertions, 810 deletions. Scope verified: frontend sources,
  frontend tests/specs, one diagnostics script and documentation only; no
  `src/` application code, `data/`, `requirements.txt`, or tool-scratch path is
  included. The body discloses the mixed ownership listed above.
- Dirty tree: 148 → 143 paths. UI-006-owned work is committed; the untracked
  rebuild specs (`v5-07-handoffs`, `reconciliation-reference`) and the shared
  `console.css` remain preserved.
- Pre-commit Mimosa scan could not complete (`scanner_enobufs`), so the scan was
  re-run after the commit: it completed with a seal
  (`sha256:5dc941cf7d0dc7bbfef869b6c11f1cf6d72253fc2098af302ba64c91bfad9f55`)
  and 202 findings, **all** of them static-analysis hits inside generated
  minified bundles under `frontend/dist-integration/` and
  `frontend/dist-local/`. **Zero** findings name any UI-006 file, and no
  credential is present in the committed changes. This is not a
  repository-wide clean security bill.
- Reference receipt: `frontend/test-results/ui-006/` (git-ignored) holds the
  Search receipts, including `search-1586x992-<engine>.png` for the
  reference-native comparison and `search-{no-match,expired}-<engine>.png` for
  the distinct states.

## UI-007-A Quota-Safe Checkpoint (recovery, contract, references, API-005 mapped)

### Active Task

UI-007 — Retrieval/Reranker. Status: ACTIVE (A complete; implementation
starting).

### Recovery Verified

- HEAD `edb7068` (UI-006 record) on `codex/bilingual-research-workspace`; dirty
  tree 143 paths. UI-001…UI-006, API-001…API-005, DATA-001/DATA-002, TEST-001
  complete. No partial UI-007 work exists.
- Master-plan row: `| UI-007 | Retrieval/Reranker | UI-002, API-005 | Engineering
  features | Same pool/raw scores | UI-006 |` — both dependencies complete, so
  UI-007 is the correct Exact Next Action.

### Master-Plan UI-007 Scope (read, not inferred)

- Retrieval: visual "engineering controls, four metrics, ranked table, excerpt
  preview"; frontend "stage columns, selected/dropped filters, diagnostic
  labels"; backend/API "additive document/date filters and versioned trace";
  persistence "explicit saves only; queries are not telemetry"; risks
  "inspection confused with production structured promotion"; tests "legacy
  compatibility, unchanged production, raw scores"; done "named stage semantics
  including not-executed stages".
- Reranker: visual "fusion/cross-encoder comparison from one trace"; reuse
  "inspection trace and model identity"; frontend "rank movement, raw scores,
  metadata/query context, accessible plot/table"; risks "scores treated as
  probabilities or unequal pools compared"; tests "negative scores, ties,
  skipped stage, same-pool identity"; done "actual scores from the same
  candidates".
- Gap-matrix rows owned here: query/preset/parameters (P1), document filters
  (P1), counts (P0), stage scores (P1), structured promotion / not-executed
  label (P0), selected/dropped (P1), evidence preview (P1), export/save/open
  (P1).

### Retrieval Reference Measured

`docs/ui-references/retrieval-ui-reference-dark-v1.png` — 1586x992. Same shell
as the other references: 204px navigation, 56px top bar, ~972px main column,
~390px right rail.

- Page header: icon tile + "Retrieval" + subtitle, with three page actions
  ("Query Examples", "Saved Searches", overflow) that have no capability here.
- "Retrieval Query" card (~160px tall): a bold label, a full-width query field
  (~44px) holding the submitted question, one filter row of three ~44px selects
  (Company, Document/Section, Search Preset), an "Advanced Filters" button, and
  a primary "Run Retrieval →" button.
- Metric row: four cards (~235x90) each with an icon, a large value, a bold
  label and a 12px hint: "128 Candidates Retrieved / From 12 document sections",
  "20 Selected Results / Top relevant chunks", "1.8s Retrieval Latency / 0.6s
  search + 1.2s rerank", "Reranker Active / bge-reranker-v1.5 / Re-ranked 128
  candidates".
- "Retrieved Results" card: header with title/subtitle and right-side controls
  ("Show only top results" toggle, "Relevance" select, "20 per page" select); a
  table with #, Score, Content Preview, Source, Page and Actions columns; ~64px
  rows where the first row is selected (tinted, bordered); a score pill on each
  row; a footer with "Showing 1–5 of 128 results" and a numbered pager.
- Rail "Evidence Preview": document identity line (company, filing, form/FY),
  a section eyebrow, a section heading, the highlighted excerpt, a
  "Relevance to query" bar with a value, "Related topics" chips, and an actions
  row (Open in Document, Save as Evidence, overflow).

### Reranker Reference

**There is no reranker reference screenshot.** `docs/ui-references/` holds nine
images and none is a reranker; the gap matrix states it explicitly ("Reranker,
Analytics, Datasets and Settings are additionally specified in the master plan,
without inventing extra reference screenshots"). The Reranker page is therefore
built from the master-plan bullets above and reuses the Retrieval page's own
visual language, with the same-pool guarantee as its acceptance criterion.

Truthful deltas recorded before coding: no page actions; no "Advanced Filters"
button (the real request bounds stay inline as labelled controls); no page
column (the corpus records no page numbers); no "Relevance" percentage bar and
no qualitative relevance wording; no "Related topics" chips; the latency card's
breakdown is derived from the trace's own stage durations rather than invented;
the reranker identity shown is the trace's reported model, and when the reranker
stage did not run the card states that instead of naming a model.

### API-005 Contract (verified in source)

`POST /retrieval/inspect`, rate limit `10/minute`.

- Request: `question` (5..500), `ticker`, `section` (five canonical values),
  `document_id` (opaque token), `filing_date` (YYYY-MM-DD), `year`, `top_k`
  (1..10, default 5), `candidate_pool` (10..50, default 10), `preset`
  (`bm25` | `dense` | `hybrid` | `hybrid_rerank`, default `hybrid_rerank`).
- Response: `query_interpretation` plus `trace`, where the trace carries
  `trace_version` (`retrieval-trace-v1`), `preset`, `query`, `filters`,
  `top_k`, `candidate_pool`, `models{embedding, reranker, rrf_k}`,
  `score_semantics{applies_to_preset, note, families}`, `production_parity`,
  `stages[]`, `candidates[]`, `selected_chunk_ids`, `candidate_count`,
  `selected_count`, `elapsed_ms`, and route-added `filter_values` and `scope`.
- Stages: `embedding`, `bm25`, `dense`, `lexical_ladder` (`executed` with a
  duration), `reranker` (`executed` or `skipped`, with `skipped` and `reason`),
  and `structured_promotion` (`not_executed` with `elapsed_ms: null` and a
  reason).
- Candidates: `chunk_id`, route-injected `document_id`, `ticker`, `section`,
  `filing_date`, `citation`, `text_preview`, `bm25_score`/`bm25_rank`,
  `dense_score`/`dense_rank`, `lexical_rank`, `fusion_rank`, `rrf_score`,
  `cross_encoder_score`, `final_rank`, `selected`, `dropped_reason`.
- Score families are explicitly distinct and non-comparable: `bm25_score`
  (lexical, unbounded positive), `dense_score` (store's own similarity scale),
  `rrf_score` (fusion, sum of reciprocal ranks, not comparable across queries),
  `cross_encoder_score` (reranker logit, only comparable within one pool). The
  API states none of them is a confidence, accuracy, or probability.
- `dropped_reason` is one of `ranked_below_top_k`, `outside_candidate_pool`,
  `not_in_selected_preset_stage`, or null — null means the trace cannot prove a
  reason, so the UI must not invent one.
- `scope`: `{documents, eligible_document_ids (bounded), truncated, reason}` —
  the truncated flag must be surfaced rather than presenting a bounded list as
  complete.
- `production_parity`: `structured_promotion` and
  `lexical_ladder_merge_into_final` both `not_executed`, with the reason that
  inspection exposes ranking stages only.

### Existing Implementation Mapped

- `frontend/src/components/RetrievalLabPanel.tsx` (605 lines) owns `/retrieval`
  today: query textarea, ticker/section/preset, top-k and candidate-pool range
  fields, a compare-preset feature (two POSTs), analyst/advanced mode tabs, four
  stat cards, a table with optional stage columns, an evidence rail with stage
  chips, and JSON/CSV export. It predates API-005's newer fields: no
  `trace_version`, `score_semantics`, `production_parity`, `scope`,
  `filter_values`, `dropped_reason`, and no `not_executed` stage handling.
- `/reranker` currently resolves to `workspaceView: "retrieval"` (route
  `availability: "partial"`), so it renders the same retrieval page today.
- `frontend/src/lib/api.ts` owns `inspectRetrieval` (question, ticker, section,
  top_k, candidate_pool, preset) — it does not yet send `document_id`,
  `filing_date`, or `year`.
- `frontend/src/types.ts` has `RetrievalCandidate`/`RetrievalTrace`/
  `RetrievalInspectResponse` with stages (including `status`) but not the newer
  trace fields.
- Preserved contracts: `RetrievalWorkspaceTarget` (`kind: "retrieval"`), focus
  ids `retrieval-document-workspace-<chunk>`, `[data-workbench-route-origin='retrieval']`,
  the submit accessible name "Run retrieval", the "Provider-free" chip, and the
  `retrieval-analyst-summary` test id asserted by V5-07.
- `frontend/e2e/fixtures.ts` mocks `/retrieval/inspect` with a minimal trace
  (one AAPL candidate, one stage, no semantics/parity/scope) that UI-007
  replaces with the full API-005 shape while keeping that candidate identity.

### OpenCode Invocation Verified

- CLI present: `opencode` 1.18.32. Non-interactive form verified by running it:
  `opencode run "<message>" -m opencode/muse-spark-1.3-contributor-free
  --variant xhigh --dir "D:/Project/Enterprise_Document_QA"`.
- `opencode models` lists `opencode/muse-spark-1.3-contributor-free`, and both
  a plain run and a `--variant xhigh` run returned the requested sentinel text,
  so Muse Spark 1.3 with XHigh reasoning is available as requested.
- Delegation rule for this task: sequential, bounded, presentational work only
  (components/CSS/fixtures/tests), never semantics, and OpenCode never commits.

### Stitch Strategy

One generation attempt for the Retrieval composition, recorded whatever the
result; the reference screenshot wins over any Stitch output, and no Stitch
demo data may reach the app. If it times out (as in UI-006), the work continues
without it.

### Planned Files

- New: `frontend/src/lib/traceModel.ts` (+ tests),
  `frontend/src/components/retrieval/*` (Retrieval page parts),
  `frontend/src/components/reranker/*` (Reranker page),
  `frontend/src/styles/retrieval.css`, `frontend/e2e/ui-007-retrieval.spec.ts`.
- Modified: `frontend/src/types.ts`, `frontend/src/lib/api.ts`,
  `frontend/src/App.tsx` (+ `src/app/routes.ts` for the reranker view),
  `frontend/src/index.css`, `frontend/e2e/fixtures.ts`, the existing retrieval
  tests and specs that address the old page, checkpoint/PROJECT_STATE/
  FRONTEND_CONTRACT.
- Backend: none planned.

### Exact Next Action

UI-007-B: extend the typed trace model and client to the full API-005 contract,
add the pure trace helpers and their focused tests, then rebuild the Retrieval
page.

## UI-007-B/C/D/E/F/G/H Checkpoint (trace model, both pages, delegation, gates)

### Active Task

UI-007 — Retrieval/Reranker. Status: B–H complete; I (controlled full gates,
audits, docs, commits) running.

### Typed Trace Model And Client (B)

- `frontend/src/types.ts`: `RetrievalTrace` gained `trace_version`,
  `score_semantics`, `production_parity`, `scope`, `filter_values`; the stage
  status is the named `RetrievalStageStatus`; candidates gained
  `dropped_reason`; the request body is the typed `RetrievalInspectRequest`.
- `frontend/src/lib/api.ts`: `inspectRetrieval` now takes that request type, so
  the additive API-005 `document_id`/`filing_date`/`year` filters are sendable.
- `frontend/src/lib/traceModel.ts` (new, pure): per-preset primary score key,
  family labels, score formatting that keeps the family's own scale, duration
  formatting that never turns a null into `0 ms`, stage status reading,
  latency breakdown from executed stages only, reranker identity only when the
  stage ran, dropped-reason labels, candidate status, rank movement from the
  trace's own ranks, same-pool detection, available score families, view-order
  options limited to reported families, deterministic ordering with ties, page
  geometry, and scope phrasing that keeps a bounded list bounded.
- `frontend/src/lib/traceModel.test.ts` (new): 19 tests covering every rule
  above, including negative logits, ties, missing scores, and a bounded scope.

### Retrieval Page (C)

`frontend/src/components/retrieval/*` replaces the old `RetrievalLabPanel`
(deleted with its test): `RetrievalPanel`, `RetrievalQueryCard`, `StageSummary`,
`TraceDisclosures`, `EvidencePreviewRail`, and the delegated `CandidateTable`.
`frontend/src/styles/retrieval.css` is page-owned and reuses the console
primitives.

Composition against `retrieval-ui-reference-dark-v1.png` (1586x992): page header
with the provider-free chip; the "Retrieval Query" card with its label, query
field, filter row, real pool bounds, "Use in Research" and the primary
"Run Retrieval →"; the submitted-configuration strip with the existing JSON/CSV
export; four metric cards (candidates retrieved with the derived section count,
selected results, inspection latency with the real per-stage breakdown, reranker
state with the trace's model or the stage's own reason); the ranked results card
whose score column is headed with the family in use; the stage list; and the
truth disclosures. The rail previews the top-ranked candidate until a row is
picked, and shows that candidate's own per-family scores, rank lineage, status,
and its dropped reason when the trace supplied one.

Removed as unsupported or superseded: the analyst/advanced mode tabs (they hid
information rather than adding capability), the compare-preset feature (two
POSTs for a feature the Reranker page now owns properly from one trace), and the
reference's "Advanced Filters" button (the real bounds stay inline and labelled).

### Reranker Page (D)

`frontend/src/components/reranker/RerankerPanel.tsx` (new) is mounted at
`/reranker`, which until now rendered the retrieval page with the navigation
availability set to "partial". The route availability is now "available" and
the reference-receipt spec asserts that.

Composition follows the master-plan bullets (there is no reranker screenshot):
one trace answers both questions, so the fusion order (`rrf_score`,
`fusion_rank`) and the cross-encoder order (`cross_encoder_score`, `final_rank`)
come from the same pool in one response and the page never reranks a second
time. It shows the reranker stage status, its duration or the explicit
"Not reported", the model only when the stage ran, how many of the pool's
candidates carry a reranker score, the comparison table (final rank, candidate,
fusion rank with a movement track, reranker score, movement, status, actions),
and the query context. Negative logits stay negative, a missing score says "No
score", and a preset that never reranks reports the stage as skipped with the
API's reason instead of drawing an absent score.

### Query Lifecycle, Races, Identity (E)

- Typing only edits a draft; one submit is exactly one `POST /retrieval/inspect`
  (unit and browser tests count the requests).
- An unchanged configuration cannot be submitted twice while a run is open,
  while an edited configuration can be committed immediately: the previous
  request is aborted and its late response is ignored by the request-id guard.
  A browser test holds the first request open, submits a second, then releases
  the first and asserts the newer trace survives.
- Selecting a candidate, changing the view order, changing the page size,
  paging, opening the disclosures, and opening a document issue no further
  request.
- Identity stays canonical: rows are keyed and selected by `chunk_id`, the
  reader handoff carries `chunk_id`/`document_id` with
  `returnFocusId: retrieval-document-workspace-<chunk>`, and "Back to Retrieval"
  restores focus to the opener (V5-07 now drives the rebuilt page).
- No workspace, conversation, or provider write: the page performs one POST and
  the explicit save action only.

### Delegation (OpenCode / Muse Spark 1.3 XHigh)

One bounded task was delegated: the presentational `CandidateTable` component,
the page-owned stylesheet skeleton, and its focused tests, with the exact props
contract, the reused console classes, and explicit "do not" rules supplied in
the task. Invocation:
`opencode run "<task>" -m opencode/muse-spark-1.3-contributor-free --variant xhigh --dir <repo>`.
OpenCode reported lint clean and 8 passing tests and did not commit.

Primary review found and fixed one semantic defect before accepting it: the
score pill's emphasis used the row's position *on the page* rather than its
position in the displayed order, so page two's first row looked like the top
result. It now uses the absolute displayed position. The remaining helpers (page
geometry, status labels, score formatting, ordering) were already delegated to
`traceModel` and reused rather than re-implemented. After the fix the delegated
suite passes unchanged, and the panel-level suites were written by the primary
agent.

### Tests Actually Run

- `bunx vitest run` — 74 files / 460 tests pass (baseline 74 / 460 after the
  old panel's tests were replaced by the new suites).
- Focused: `traceModel` 19, `CandidateTable` 8, `RetrievalPanel` 15,
  `RerankerPanel` 7 — 49 tests, all passing.
- `bun run lint` (tsc) — clean after every edit; `bun run build` — pass.
- `bunx playwright test e2e/ui-007-retrieval.spec.ts --workers=4` — 14/14 pass
  (seven tests on Chromium and Firefox), including a twelve-receipt viewport
  loop.
- At the default 14 workers the same spec failed every Chromium test by timing
  out; at 4 workers all pass, which is the documented load-sensitive class and
  the reason the policy fixes a controlled worker count.
- `bunx playwright test e2e/v5-07-handoffs.spec.ts` — 4/4 pass after scoping the
  save action to the row the flow opens.
- `e2e/regression.spec.ts` retrieval test — updated to the new, better
  behaviour (a completed trace is kept and labelled as differing from the
  draft) and passing.

### Receipts

`frontend/test-results/ui-007/` (git-ignored): retrieval and reranker receipts
at 1586x992, 1440x900, 1280x856, 1024x768, 390x844 and 1440x700 on both
engines, plus the populated retrieval view, the reranker comparison, and the
skipped-stage state.

### Remaining Work

UI-007-I: controlled full Chromium/Firefox gate, nine-reference receipt,
artifact/diff/dependency audit, documentation, commits, then select the next
task and stop.

### Exact Next Action

Read the controlled gate results, classify any failure (isolate before calling
it a regression), then finish the audits, docs and commits.

## UI-007-I Final Checkpoint (gates, audits, commits, UI-007 COMPLETE)

### Task Status

UI-007 COMPLETE.

### Visual Comparison Result

Retrieval was compared against
`docs/ui-references/retrieval-ui-reference-dark-v1.png` (1586x992) at the
reference viewport: the page header, the "Retrieval Query" card with its label,
query field, filter row and primary "Run Retrieval →" button, the four metric
cards, the ranked results table with its score column, and the right-rail
evidence preview all sit where the reference puts them. Deltas that stay, each
recorded as a truthful deviation: five real filter controls plus the inline pool
bounds replace the reference's three controls and its dead "Advanced Filters"
button; the query card carries the submitted-configuration strip with the
existing export; the metric hints report real stage durations instead of a
fabricated split; the score column is headed with the score family in use and
there is no page column because the corpus records no page numbers; and two
truth surfaces the reference does not have (the stage list and the score/parity
disclosures) follow the results card.

Reranker has no reference screenshot, so it was reviewed against the master-plan
bullets on the same shell: the comparison table names the fusion rank, the
reranker score, and the rank movement, the stage card reports status, duration
and the model only when the stage ran, and a preset without the cross-encoder
shows the skipped state with the API's reason.

### Gates (UI-007-I)

- `bun run lint` (tsc) — PASS.
- `bunx vitest run` — PASS: 74 files / 460 tests (422 baseline + 49 new − 11
  from the replaced panel's suite).
- `bun run build` — PASS.
- `bunx playwright test e2e/ui-007-retrieval.spec.ts --workers=4` — PASS: 14/14
  (both engines). The same spec at the default worker count times out every
  Chromium test, which is the documented load-sensitive class.
- Controlled full gate, 4 workers:
  `bunx playwright test --config playwright.config.ts --workers=4` →
  **296 passed, 4 skipped, 4 failed**. Failures:
  `regression.spec.ts:971` (chromium Library search p95),
  `regression.spec.ts:1039` (chromium composer p95),
  `regression.spec.ts:65` (firefox evidence inspector),
  `workspace-performance.spec.ts:176` (firefox synthetic baselines). All four
  pass in isolation (6/6 across both engines), none touches Retrieval or
  Reranker, and all belong to the documented load-sensitive class.
- Nine-reference receipt — PASS 30/30 (15 surfaces on both engines), including
  `r5-retrieval`, which now drives the rebuilt page.
- Earlier in the same gate run the r5 receipt failed because the receipt
  asserted a single "Save evidence" control; the rebuilt table has one per row.
  The receipt now targets the first row, which is what it always meant.

### Commit

- `cb6a6ea` — `feat(ui): rebuild retrieval and add the reranker comparison view`
  — 25 files, 4944 insertions, 767 deletions. Scope verified: frontend sources,
  tests and specs plus documentation only; no backend, `data/`, dependency, or
  tool-scratch path is included, and no dependency was added (the
  `package.json`/`bun.lock` diff is the pre-existing rebuild entries).
- Ownership: the one-line reranker navigation-availability change stays in the
  still-untracked `frontend/src/app/routes.ts`, and the UI-007 edits in the
  still-untracked `e2e/v5-07-handoffs.spec.ts` and
  `e2e/reconciliation-reference.spec.ts` ride with those files; all three are
  disclosed in the commit body. The commit was rebuilt to exclude `routes.ts`
  after it was initially staged, so no file's ownership is claimed wholesale.
- Dirty tree: 143 → 141 paths.

### Artifact / Dependency Audit

- No Playwright traces, videos, dumps, or scratch specs are staged;
  `frontend/test-results/` is git-ignored and holds the receipts.
- No new dependency; no secrets in any new or modified file.
- `git diff --check` — clean (one trailing blank line in the contract document
  was removed before committing).

### Security Scan

The pre-commit Mimosa scan could not complete (`scanner_enobufs`). The scan was
re-run after committing: it sealed with 202 findings, all inside generated
minified bundles under `frontend/dist-integration/` and `frontend/dist-local/`,
and **zero** name any UI-007 file. This is not a repository-wide clean security
bill.

### Known/Pre-existing Issues

- The load-sensitive browser class above (four specs), unchanged by UI-007.
- The six frozen frontend integration expectation failures recorded before
  UI-004 (that config is excluded from the default gate).
- The shared untracked `frontend/src/styles/console.css` and
  `frontend/src/app/routes.ts` remain uncommitted dependencies of the committed
  application.

### New Regressions

None. Every gate failure was reproduced as a load-sensitive flake in isolation,
and the rebuilt pages' own suites are green on both engines.

### Exact Next Action

The master-plan table orders `DATA-003 — Typed collections` (`DATA-001` and
`DATA-002`, both complete) next for the Collections surface, with
`API-006 — Model/dataset registries` (`API-002`, complete) and
`UI-008 — Collections` (needs `DATA-003` and `UI-004`) also on the graph. Do not
begin any of them without a new instruction.

## DATA-003-A Checkpoint (recovery, exact contract, persistence mapped)

### Active Task

DATA-003 — Typed collections. Status: ACTIVE (A complete; implementation
starting).

### Recovery Verified

- HEAD `2d75091` on `codex/bilingual-research-workspace`; dirty tree 142 paths.
  UI-001…UI-007, API-001…API-005, DATA-001/DATA-002, TEST-001 complete. No
  partial DATA-003 work exists (no collections router, no typed collection
  module, and the collection tables are created but unused).
- Master-plan row: `| DATA-003 | Typed collections | DATA-001, DATA-002 |
  Collections repository/router | Mixed assets/conflicts | UI-006 |` — both
  dependencies complete, so DATA-003 is the correct Exact Next Action, and it
  unblocks `UI-008 — Collections`.

### Exact DATA-003 Contract (read from the master plan, not assumed)

The plan's shared-contract section states it directly:

- `Collection`: **id/name/description/tags/favorite/private visibility/revision/
  timestamps**.
- `CollectionItem`: **kind is `document`, `evidence`, `answer` or `note`** with
  typed snapshot/reference.
- `EvidenceRef`: document/chunk/source IDs, content hash, revisions and
  representation/location when known.
- `Receipt` identifies committed operations; **tombstones prevent
  resurrection**; activity records real operations.
- Mutations return committed revisions; **revision preconditions and 409
  conflicts**; imports are idempotent; **opaque IDs never accept arbitrary
  filesystem paths**.

Owned API surface (access class `L` = protected local workspace, reads
included): `GET/POST /collections`, `GET/PATCH/DELETE /collections/{id}`,
`GET/POST /collections/{id}/items`, `DELETE /collections/{id}/items/{item_id}`,
`POST/PATCH/DELETE /collections/{id}/notes[/{note_id}]`,
`GET /collections/{id}/activity`, `GET /collections/{id}/export`. The contract
tests named there: stable filters, bounds, identity, concurrency, atomic
deletion, mixed assets, duplicate/stale, parent ownership, conflict, actual
history, portable export.

Completion criteria from the plan: Collections is "list/cards and
contents/notes/activity/settings details", persistence covers
"documents/evidence/answers/notes and actual activity", risks are "import loss,
duplicates, conflicts and stale references", tests are "idempotency, failed
writes, conflicts, tombstones, missing sources", done is "lossless round trip
with honest stale/source-gone state", and priority row 5 marks Collections/import
as requiring a lossless round trip.

### Current Persistence Mapped

- DATA-001 (`src/workspace/database.py`, `migrations.py`, `repository.py`):
  SQLite with WAL, foreign keys, busy timeout, serialized writes, versioned
  checksummed migrations, integrity checks, and a **generic versioned-record
  store** `workspace_records(entity_type, entity_id, revision, payload_json,
  created_at, updated_at)` plus a generic `tombstones` table and
  `workspace_imports` receipts. `SQLiteVersionedRecordRepository` provides
  `get`/`create`/`replace`/`delete`/`get_tombstone` with canonicalised payloads,
  secret-field rejection, revision preconditions → `RecordConflictError`,
  tombstones → `RecordDeletedError`, and an injectable clock.
- Migration v2 `research_domain_foundation` already creates `collections`,
  `collection_items` (with `item_kind CHECK IN ('document','evidence','answer',
  'note')`), `notes` and `activity_events`. **No application code reads or
  writes those four tables** — only `tests/test_workspace_persistence.py` proves
  the schema and its foreign keys exist. They are unused foundation tables.
- DATA-002 (`src/workspace/transfer.py`): the workspace backup envelope
  (`version 1`) carries `conversations`, `collections`, `evidence_items`,
  `favorites`, `tombstones`, `unsupported`, `source_schemas`, `source_counts`
  and a canonical digest. Import maps legacy kinds to entity types
  (`conversation`, `collection`, `collection_item`), writes the **wrapped**
  payload `{workspace_transfer_version, source_kind, legacy_id,
  source_schema_version, data}` into `workspace_records`, is transactional with
  rollback, idempotent by source digest, blocks tombstoned records, refuses to
  overwrite newer revisions, and records a receipt with id mappings.
  `export_backup` reads `workspace_records` and **skips any row that is not
  wrapped with `workspace_transfer_version == 1`**, counting it as unsupported.
- Browser domain (`frontend/src/lib/evidenceCollections.ts`): `EvidenceCollection
  {schemaVersion: 2, id, name, items[], createdAt, updatedAt}` and
  `EvidenceItem {id, citation, excerpt, chunkId?, ticker?, section?,
  filingDate?, …, savedAt}`, with `MAX_COLLECTIONS = 50` and
  `MAX_ITEMS_PER_COLLECTION = 100`. The transfer's legacy validators require
  exactly those spines: a collection payload needs `schemaVersion 2`, a
  non-empty `name`, no `items` key, and `createdAt`/`updatedAt` equal to the
  record timestamps; an evidence item needs `citation` and `excerpt` strings and
  `savedAt == created_at == updated_at`.
- Frontend canonicalization (`frontend/src/lib/workspaceBackup.ts`) validates the
  envelope with exact top-level keys, requires `payload.id === legacy_id` on
  every record, and computes the same digest, so a new envelope section would
  break that parity contract.

### Design Decision (the load-bearing one)

Typed collections are persisted **through the DATA-001 versioned-record store**,
not by writing the four unused foundation tables:

- Entity types: `collection`, `collection_item`, `collection_note`, plus
  `collection_activity` for real recorded operations.
- Collection and item records carry the store's existing transfer wrapper
  (`workspace_transfer_version == 1`, `source_kind`, `legacy_id`,
  `source_schema_version`, `data`), so the **existing DATA-002 export/import
  round-trips typed collections and their items with no format change, no
  version bump, no canonicalization change and no digest change**. The typed
  truth lives inside `data` and is unwrapped by the domain before it leaves the
  repository.
- The typed payload keeps the legacy spine the envelope validators require.
  Collections carry their real name/description/tags/favorite/private and
  timestamps; items carry the real `citation`/`excerpt`/`savedAt` supplied by the
  caller (the server never invents a citation). Items are immutable except
  deletion — the plan gives them only POST and DELETE — which keeps
  `updated_at == created_at` true, as the item spine requires.
- Notes get their own entity type because the plan gives them PATCH (they are
  editable) and an optional EvidenceRef ("bound/unbound"). The envelope has no
  note record type, so notes are not carried by the workspace backup today; they
  are fully carried by `/collections/{id}/export`. This limitation is recorded
  rather than fixed by changing the canonical backup format, which this task
  forbids changing casually.
- Activity is append-only and is written **without** a transfer wrapper, so an
  export classifies it as an unsupported source instead of silently dropping it
  or corrupting the envelope: truthful about this build's backup coverage.
- Revisions, conflicts, tombstones and no-resurrection come from DATA-001; the
  domain adds kind/membership/bounds validation, receipts and unwrapping.
- The unused `collections`/`collection_items`/`notes`/`activity_events` tables
  stay unused; no migration is added, deliberately.

### Planned Files

- New: `src/workspace/collections.py` (typed domain + SQLite-backed repository),
  `src/api/routers/collections.py` (protected `L` routes),
  `tests/test_collections_domain.py`, `tests/test_collections_repository.py`,
  `tests/test_collections_transfer.py`, `tests/test_collections_api.py`.
- Modified: `src/workspace/__init__.py` (exports), `src/api/schemas.py`
  (additive models), `src/api/app.py` (router registration), checkpoint and
  PROJECT_STATE.
- Frontend: additive types only if a real compatibility need appears; UI-008 owns
  the Collections interface.

### Exact Next Action

DATA-003-B: implement the typed domain (collection, item, note, activity models
with validation, membership rules, bounds and receipts) and its focused tests
before touching persistence.

## DATA-003-B/C/D/E/F Checkpoint (domain, persistence, transfer, HTTP contract)

### Active Task

DATA-003 — Typed collections. Status: B–F complete; G (full gate, audits,
docs, commits) running.

### Typed Domain (B)

`src/workspace/collections.py` (new) is the whole domain:

- Item kinds are exactly the plan's four — `document`, `evidence`, `answer`,
  `note` — and each declares the identity its reference must carry: a document
  needs a `document_id`, an answer needs a conversation/message/answer identity,
  evidence needs a real `EvidenceRef` (at least one of document/chunk/source
  identity), and a note may be unbound or bound to an `EvidenceRef`. Nothing is
  inferred from a reference's shape and nothing is coerced: the caller's declared
  kind decides the rule and an incompatible reference is refused deterministically.
- Collections carry name/description/tags/favorite/**private**/revision and
  timestamps; notes are editable and may be bound or unbound; items are immutable
  references or snapshots (the plan gives them only create and delete).
- Bounds are enforced here: 50 collections, 100 members per collection, 50 notes,
  500 activity rows, 200-char names, 2 000-char descriptions, 20 tags of 64
  characters, bounded citation/excerpt/note text, and a bounded reference tree
  (depth 12, 500 values) that rejects non-JSON values. Identifiers are opaque and
  path-hostile (`..`, `/`, `\`, NUL and over-long values are refused).
- Errors are one small family the HTTP layer can map: not found, deleted,
  conflict, limit, domain error.

### Persistence (C) — no migration, deliberately

- Typed collections, items, notes and activity are stored in the DATA-001
  versioned-record store, so revisions, revision preconditions, tombstones,
  no-resurrection, canonical payloads and secret-field rejection are inherited
  rather than re-implemented.
- Records carry the DATA-002 transfer wrapper (`workspace_transfer_version`,
  `source_kind`, `legacy_id`, `source_schema_version`, `data`), and the typed
  truth lives in `data`. Notes carry their own workspace marker and activity
  carries another, because the envelope has no record type for either; both stay
  outside the portable kinds on purpose.
- Storage keys are the transfer's own deterministic mapping
  (`stable_legacy_id`), so a collection and its items keep one key across
  create, restart, export, import and repeated import; importing a backup into
  the workspace that produced it cannot duplicate anything.
- The four unused foundation tables from migration v2 stay unused: writing them
  would create a second source of truth and break the export path. **No
  migration was added and no schema changed**, which is recorded as deliberate.
- `src/workspace/repository.py` gained one allowlisted entity type
  (`collection_activity`) for append-only recorded operations; nothing else in
  DATA-001 changed.

### Behavior (D)

Revision increments on every update; a stale revision is a `409` and never
overwrites; deleting is atomic and tombstones the collection *and* its members
and notes; a deleted record reports itself as gone (`410`), re-deleting it is not
a conflict, and recreating it is refused; item deletion requires the collection
that actually owns it; duplicate identifiers are conflicts rather than silent
merges; listing supports search/tags/favorite/sort/page with the favorite filter
honouring both `true` and `false`; activity records real operations, is bounded,
and is pruned oldest-first instead of failing a committed write; export carries
the collection's truth as JSON or Markdown without mutating anything.

### Transfer (E)

Six tests drive the real envelope: typed collections and their members export
inside the existing `version 1` format with the same canonicalization and digest,
`validate_workspace_backup` accepts the result, import into a fresh workspace
restores names, tags, favorite, private, kinds, references, snapshots and
revisions, a repeated import returns the stored receipt unchanged and creates
nothing, re-importing an older backup cannot resurrect a tombstoned collection,
and an older backup cannot overwrite a newer revision. Notes and activity are
reported as an unsupported source in that same envelope — truthful about this
build's backup coverage rather than a silent drop.

### HTTP Contract (F)

`src/api/routers/collections.py` (new) serves the plan's collection surface under
the API-001 `L` grant, reads included: list/create/get/patch/delete collections,
list/add/delete items, list/add/patch/delete notes, list activity, and export.
Domain outcomes map to `404` (unknown), `410` (tombstoned), `409` (revision
conflict), `422` (bounds, kind, membership and request-model validation).
Twelve API tests drive the real ASGI app over a real SQLite workspace, including
the access boundary (public mode answers 404 and never creates the private
database, non-loopback is 403, unauthenticated reads are 401) and the bounds.

### Tests Actually Run

- `pytest tests/test_collections_domain.py tests/test_collections_repository.py
  tests/test_collections_transfer.py tests/test_collections_api.py` — 49 pass.
- DATA-001/DATA-002 focused regressions
  (`test_workspace_persistence`, `test_workspace_transfer`,
  `test_workspace_transfer_api`, `test_workspace_transfer_canonical`,
  `test_workspace_access`, `test_workspace_matrix`) — 105 pass, 1 warning (a
  pre-existing third-party `ast.NameConstant` deprecation).
- Full hermetic backend suite — running at checkpoint time; recorded in G.

### Remaining Work

DATA-003-G: full backend suite result, compile/import checks, `git diff --check`,
artifact/dependency audit, documentation, commits, then select the next task.

### Exact Next Action

Read the full-suite result, classify any failure, then finish the audits, docs
and commits.

## DATA-003-G Checkpoint (commit, clean-checkout proof, audits, next task)

DATA-003 — Typed collections. Status: **COMPLETE**. Commit
`d0ffd91 feat(data): add typed collections over the versioned workspace store`
— 17 files, +5362/-2: the typed domain (`src/workspace/collections.py`), its
protected HTTP surface (`src/api/routers/collections.py`, request models in
`src/api/schemas.py`, route registration in `src/api/app.py`), the four test
modules, the route-inventory contract update, and the two documents.

The same commit also carries the still-untracked predecessor modules this
surface imports at module scope (`src/workspace/database.py`,
`migrations.py`, `repository.py`, `transfer.py`, `__init__.py`, and
`src/api/access.py`). Nothing else was swept in: the rest of the rebuilt API
surface (`src/api/sec_urls.py`, `pdf_*`, the sibling routers) remains untracked,
so a clean checkout of this commit still cannot import `src.api.app`. That is a
property of this branch's accumulated uncommitted rebuild, not of DATA-003, and
it is recorded in the commit body as well.

### Gates Run

- Full hermetic backend suite: 1018 passed, 0 failed, 188 warnings (baseline
  before DATA-003: 969 passed / 0 failed / 188 warnings — +49 tests, warnings
  unchanged).
- Focused DATA-003 tests: 49 pass (18 domain, 13 repository, 6 transfer, 12 API)
  plus the route-inventory contract.
- Focused DATA-001/DATA-002 regressions: 105 pass.
- `compileall` and direct import checks pass; `git diff --check` reports no
  whitespace errors (CRLF conversion notices only); no runtime artifacts
  (`*.sqlite3`, `*.db`, `*.wal`, `*.shm`, debug or scratch files) were added, and
  the scanned/generated directories (`frontend/dist-*`,
  `frontend/playwright-report/`) stay gitignored.

### Clean-Checkout Proof

A detached worktree at `d0ffd91` (`git worktree add --detach … d0ffd91`) was
used to check what the commit supports on its own:

- 37 domain/repository/transfer tests pass there, and
  `src.workspace.collections`, `src.workspace.transfer`,
  `src.api.access` and `src.api.routers.collections` all import, so the DATA-003
  surface is self-contained apart from the untracked siblings noted above.
- The API-level modules (`test_collections_api.py`,
  `test_api_router_contracts.py`) cannot be collected in that worktree because
  `src.api.app` imports the untracked sibling modules. They pass in the working
  tree, where the full suite was run.
- The temporary worktree was removed afterwards; `git worktree list` shows only
  the main checkout.

### Post-Commit Security Audit

Mimosa deep scan (job `scan-job-muc4xujj-423103b106bb0b0b`, scan
`scan-2026-09-22T03-49-58.894Z-12e92579cdfd`, seal
`sha256:73d868fda65910240a597cd3a09b2421ac85bdb967d79d25cd812a8e225dc0fe`,
static-only, verdict effect none): 307 findings repo-wide (65 high, 242
medium), 97 packages scanned with 7 matched packages / 29 advisories / 4
unknown. Findings by location:

- 303 of 307 are inside generated bundles that are scanned as source
  (`frontend/dist-local/assets/*`, `frontend/dist-integration/assets/*`,
  `frontend/playwright-report/trace/*`) — minified vendor JS, not our code.
- 3 medium cross-file taint hypotheses on `frontend/src/App.tsx:2562/2565/2568`
  point at a URL-to-`child_process` path inside a minified code-mirror bundle;
  not DATA-003-owned, not reachable from the collections surface.
- 1 high SQL-injection finding at `src/workspace/database.py:138` — the
  `PRAGMA busy_timeout` statement. Reviewed: the interpolated value is
  `busy_timeout_ms`, an `int` that the class validates to 100..30000 and that
  settings clamp with `Field(default=5000, ge=100, le=30_000)`; it comes from
  operator configuration, never from a request, and SQLite accepts no bind
  parameter for PRAGMA, so no injection path exists. No code change made, and
  the file is DATA-001's, not DATA-003's.

**No DATA-003-owned file carries a finding.**

### Disclosure

`src/api/app.py` and `src/workspace/repository.py` were already dirty from
predecessor tasks before DATA-003 touched them; the diff carries that
inseparable earlier work (`app.py` gained the DATA-001/DATA-002 wiring lines
alongside the collections router registration, and `repository.py` is the
DATA-001 file that needed the one allowlisted entity type). `PROJECT_STATE.md`
and this checkpoint file are shared journals whose staged hunks are exclusively
the DATA-003 sections.

### Next Task Selection (from the master plan)

`docs/UI_REBUILD_MASTER_PLAN.md` §21 orders the graph and lists the task table.
With DATA-003 complete, its dependents are evaluated in table order:
`DATA-003` (496) → `UI-008 Collections` (497) → `API-006 Model/dataset
registries` (498). `UI-008` declares dependencies `UI-002, DATA-003, UI-004` —
all three are complete (UI-002 shell/router, DATA-003 typed collections, UI-004
source/document composition), so `UI-008` is the first dependency-ready task in
the saved priority order. `API-006` depends only on `API-002` and is ready too,
but it follows `UI-008` in the ordering and is not the next entry.

### Exact Next Action

**UI-008 — Collections** (dependencies `UI-002`, `DATA-003`, `UI-004`; area:
Collections feature; gate: save/export/reopen/stale). Do not implement it, and
do not begin `API-006`, `UI-009`, `DATA-004`, `DATA-005`, or any later task
without explicit authorization.


## UI-008-A Checkpoint (recovery, contract, reference measured, decisions)

UI-008 — Collections. Status: ACTIVE (A complete; implementation ahead). Started
2026-09-22 on branch `codex/bilingual-research-workspace`, HEAD `ffc5955` with
140 dirty paths (historical rebuild work, preserved untouched).

### Recovery Evidence

- `git log --oneline -3` → `ffc5955`, `d0ffd91` (DATA-003), `2d75091`.
- `git status --porcelain | wc -l` → 140 dirty paths (the same untracked/mixed
  rebuild surface DATA-003 disclosed; this recovery created none).
- No partial UI-008 work exists: `/collections` still renders the pre-rebuild
  `CollectionsConsole`, and no frontend module touches the DATA-003 routes.

### Exact UI-008 Contract (from the master plan, not inferred)

Master plan §21 row: `UI-008 Collections, dependencies UI-002 / DATA-003 /
UI-004, area "Collections feature", gate "Save/export/reopen/stale"`. All three
dependencies are complete, so UI-008 is dependency-ready.

§9 Collections page plan: "Visual: list/cards and contents/notes/activity/
settings details. Reuse: snapshots, export and source verification. Frontend:
CRUD, mixed typed items, tags/favorites, notes/private settings. Backend/API:
SQLite repository; browser repository in public mode. Persistence: documents/
evidence/answers/notes and actual activity. Risks: import loss, duplicates,
conflicts and stale references. Tests: idempotency, failed writes, conflicts,
tombstones, missing sources. Done: lossless round trip with honest
stale/source-gone state."

Appendix A (`docs/UI_REFERENCE_GAP_MATRIX.md`) rows owned here: cards/list/
search/sort (P1), description/tags/favorite as persistent fields (P1), mixed
typed items document/answer/note (P1), notes/activity with actual events (P1),
add/remove/export as real CRUD (P1), and **shared visibility deferred to P3**
(sharing is out of scope, never faked). The Documents row "Add to collection |
Picker | Document item" and the Search row "save actions | Collection
persistence" are the picker/save work this task is expected to provide.

§11 (persistence): "No silent dual writes"; "public mode keeps browser
persistence". §9's backend line allows a browser repository in public mode.

### Authoritative Reference Measured

`docs/ui-references/collections-ui-reference-dark-v1.png` — 1586 × 992, the
same shell as Documents/Search/Retrieval. Measured on the real PNG with
PIL/numpy edge scans (column and row transitions), not estimated:

- Navigation 0–209, top bar 0–56 (shell), content padding ≈ 15 px.
- Main column x ≈ 224–974 (≈ 750 px); right rail x ≈ 987–1570 (≈ 583 px);
  right margin ≈ 16 px; column gap ≈ 13 px.
- Page header band ≈ y 75–145: icon tile + "Collections" (≈ 26 px semibold) +
  subtitle, with a toolbar on the same band (search field ≈ 22.5 rem wide,
  "Last updated" select, a two-button grid/list toggle, primary "New
  Collection").
- Tab row ≈ y 160–196: "All Collections" with a count badge (active: white
  text, blue underline, blue badge), "Shared with Me", "Favorites".
- Collection cards: four at y 213–372, 385–548, 561–722, 734–895 — height
  ≈ 160 px, gap ≈ 13 px, radius ≈ 14 px, 1 px border, the selected card
  brighter. Anatomy: 48 px coloured icon tile, name + star, two-line
  description, tag-chip row with "+N", a right-aligned meta block ("12 items",
  "Updated 2 hours ago / by Nguyen"), and an action row ("Open →", "Share",
  "Export", "+ Add Documents").
- Rail: header card (56 px icon tile, name + star, description, "…" and "×"),
  a three-cell stat strip (items, updated, "Private / Only you"), the tab row
  (Contents, Notes, Activity, Share, Settings), "Evidence Items (12)" with an
  "+ Add Documents" button, ≈ 52 px item rows (badge tile, title, "SEC Filing ·
  p. 12-24" subtitle, right-aligned date, "…"), a centred "View all 12
  items →", then a two-column bottom area (Insights & Notes | Recent Activity
  timeline).

### Current Collections Implementation Mapped

- `frontend/src/app/routes.ts`: `/collections` and `/collections/:collectionId`
  exist (UI-002), both mapping to the `library` workspace view; the navigation
  item is `available`.
- `frontend/src/App.tsx` renders `CollectionsConsole` for `activeView ===
  "library"` with a `librarySlot` (the `ConversationLibrary` element) and the
  Ctrl/Cmd+K conversation-search handoff.
- `frontend/src/components/CollectionsConsole.tsx` (390 lines) is the
  pre-rebuild page: browser collections (`lib/evidenceCollections`), favourites
  in `lib/collectionFavorites`, and no detail tabs, notes, activity, settings or
  typed items.
- `lib/evidenceCollections.ts`, `lib/workspaceRepository.ts`,
  `lib/workspaceBackup.ts`, `components/EvidenceCollectionsPanel.tsx` and
  `components/ConversationLibrary.tsx` are the DATA-002 legacy browser
  repository/adapter surface and stay in place.
- `frontend/src/lib/api.ts` has no collections client and `types.ts` no
  collections types: the rebuild never talked to the protected routes.
- Impacted existing specs: `components/CollectionsConsole.test.tsx` (Ctrl/Cmd+K
  handoff), `e2e/ui-routing.spec.ts` (route resolution),
  `e2e/regression.spec.ts` (empty browser collections), and the untracked
  nine-reference receipt `e2e/reconciliation-reference.spec.ts`, whose r4
  surface drives Search → "Save evidence" → Collections → "Open" and asserts
  `#collections-title` plus `.console-rowlist__row`.

### DATA-003 HTTP Contract Mapped (the only collection truth)

From `src/api/routers/collections.py` and `src/workspace/collections.py`:

- `GET /collections?search&tags&favorite&sort&direction&page&page_size` →
  `{items:[{collection_id,name,description,tags,favorite,private,revision,
  created_at,updated_at,item_count}],total,page,page_size}`; `sort` is one of
  name, updated_at, created_at, item_count; `page_size` is capped at 100.
- `POST /collections` `{name (1-200), description (≤2000), tags (≤20), favorite,
  private, collection_id?}` → the committed collection at revision 1.
- `GET /collections/{id}`; `PATCH /collections/{id}` `{revision (≥1), name?,
  description?, tags?, favorite?, private?}` (stale revision → 409);
  `DELETE /collections/{id}?revision=` → receipt
  `{operation,entity_type,entity_id,revision,deleted_at}`.
- `GET /collections/{id}/items?kind&page&page_size` → items
  `{item_id,collection_id,item_kind,citation,excerpt,reference,revision,
  created_at,updated_at,snapshot?}`; `POST …/items` `{item_kind,
  citation (≤500), excerpt (≤10000), reference?, snapshot?, item_id?}`;
  `DELETE …/items/{item_id}?revision=`.
- Notes: `GET/POST /collections/{id}/notes` `{text (1-10000), evidence_ref?,
  note_id?}`; `PATCH/DELETE …/notes/{note_id}` (PATCH carries `revision`); note
  payloads hold `note_id,collection_id,text,revision,created_at,updated_at,
  evidence_ref?`.
- `GET /collections/{id}/activity` → `{activity_id,collection_id,entity_type,
  entity_id,event_type,occurred_at}` newest first, bounded at 500 per
  collection; events are collection_created|collection_updated|
  collection_deleted|item_added|item_removed|note_added|note_updated|
  note_removed.
- `GET /collections/{id}/export?format=json|markdown` → the JSON document or
  `{format:"markdown",content}`; a read, so it mutates nothing.
- Membership is typed: `document` needs `reference.document_id`; `answer` needs
  one of conversation_id|message_id|answer_id; `evidence` needs at least one of
  document_id|chunk_id|source_document_id|conversation_id|message_id plus
  string-typed provenance fields; `note` may be unbound. Identifiers must match
  the domain's identifier pattern; the collection's own id is
  `stable_legacy_id("collection", legacy_id)`.
- Statuses: 404 unknown (and every route in public mode), 410 tombstoned, 409
  revision conflict, 422 bounds/kind/membership/validation; 401 without the
  local bearer token, 403 off-loopback or a denied Host/Origin (API-001).

### Decisions With Rationale

1. **No browser-side collections repository in this task.** The plan mentions one
   for public mode, but the goal forbids duplicating collection business logic in
   React and DATA-003 is the single writer. A non-local context therefore renders
   a truthful unavailable state derived from the real response (404 unavailable
   in this mode, 401 token required, 403 not this machine) — never a fake empty
   list.
2. **Conversations are preserved, not deleted.** `ConversationLibrary` (with the
   on-device evidence panel and backup) moves behind a "Conversations" tab on the
   same route and keeps the Ctrl/Cmd+K handoff and the `?tab=conversations` deep
   link, because the shell sidebar is the only other surface and this task may not
   regress a working capability.
3. **"Shared with Me", "Share" and the per-card "by Nguyen" owner are omitted.**
   Sharing is explicitly deferred (P3) and a local single-user workspace has no
   owner; cards and the rail show real fields instead (item count, updated time,
   tags, privacy flag).
4. **The evidence-save action is repointed to DATA-003.** Documents/Search/
   Retrieval/Reranker already offer "Add to Collection" / "Save evidence" against
   the browser store; once this page shows workspace collections those controls
   would be lying. The App-level `handleSaveRetrievedEvidence` gets an explicit
   target dialog (existing collections plus create-new) that POSTs a real
   `evidence` item, while the conversation-surface call sites keep their
   on-device behaviour (their panel is still visible in the Conversations tab).
   No dual writes.
5. **`returnView` gains `"library"`.** UI-004's document handoff type is a
   three-value union; opening a document member from Collections is a real fourth
   origin, added additively so the App's `returnView !== activeView` guard keeps
   working.
6. **Activity and notes come from the API only.** No synthesised events, and a
   note renders as its text plus real timestamps (the model has no title field,
   so none is invented).

### Stitch Strategy

One bounded Stitch generation will be requested for the Collections composition
(card list plus the rail with its tabs and stat strip). The local screenshot
remains authority #1 and wins over any Stitch output; a timeout is recorded
honestly and the work continues from the reference, exactly as UI-006 recorded.
No Stitch demo data enters the repository.

### Planned Files

- New: `src/lib/collectionModel.ts` (+ test) for the typed client model, status
  mapping, kind labels, relative time and card/rail derivations; `src/lib/api.ts`
  and `src/types.ts` additions for the DATA-003 endpoints;
  `src/components/collections/` (`CollectionsWorkspace.tsx`,
  `CollectionsToolbar.tsx`, `CollectionCard.tsx`, `CollectionDetail.tsx`,
  `CollectionContents.tsx`, `CollectionNotes.tsx`, `CollectionActivity.tsx`,
  `CollectionSettings.tsx`, `CollectionTypeBadge.tsx`, `AddItemsDialog.tsx`,
  `CollectionTargetDialog.tsx`); `src/styles/collections.css`;
  `e2e/ui-008-collections.spec.ts`; component tests beside the new components.
- Replaced: `src/components/CollectionsConsole.tsx` and its test by
  `CollectionsWorkspace`; `App.tsx` wiring and the repointed save handler.
- Touched additively: `src/types.ts` (`returnView: "library"`),
  `src/lib/i18n.tsx` (new keys in both locales).

### Exact Next Action

UI-008-B: add the typed DATA-003 client surface, build the Collections
list/rail composition, and capture the first reference-native screenshot.

## UI-008-B/C/D/E Checkpoint (client, composition, behavior, responsive/a11y)

UI-008 — Collections. Status: B–E complete; F–H in progress.

### Completed Work

**Client surface (B).** `frontend/src/lib/api.ts` gained the typed DATA-003
surface (`listCollections`, `getCollection`, `createCollection`,
`updateCollection`, `deleteCollection`, `listCollectionItems`,
`addCollectionItem`, `deleteCollectionItem`, `listCollectionNotes`,
`addCollectionNote`, `updateCollectionNote`, `deleteCollectionNote`,
`listCollectionActivity`, `exportCollection`) over the existing `apiFetch` /
`throwApiError` pair, so a status and the server's bounded detail survive to the
page. `frontend/src/types.ts` gained the collection/item/note/activity/receipt
and request types plus `returnView: "library"` on `CatalogWorkspaceTarget`.
`frontend/src/lib/collectionModel.ts` (+ 25 unit tests) owns the derivations:
status→state mapping, kind/activity labels, relative time with an honest null,
member counts, tag overflow, privacy wording, the per-kind reference builders,
and `itemOpenTarget` (document/evidence/answer/unavailable).

**Composition (B/E).** `frontend/src/components/collections/`:
`CollectionsWorkspace` (page: tab row, list, dialogs, selection route, request
epochs), `CollectionsToolbar`, `CollectionCard`, `CollectionDetail` (rail),
`CollectionContents`, `CollectionNotes`, `CollectionActivity`,
`CollectionSettings`, `CollectionTypeBadge`, `CollectionActionMenu`,
`AddItemsDialog`, `CollectionTargetDialog`, `CollectionFormDialog`,
`ExportDialog`; page-owned `frontend/src/styles/collections.css` reuses the
console primitives (buttons, inputs, chips, alerts, empties, underline tabs) so
no second design system appears. `App.tsx` renders the workspace, owns the
`/collections/:collectionId` selection route (`handleSelectCollectionRoute`),
the `?tab=conversations` initial tab, and the repointed save flow. The old
`CollectionsConsole` and its test were deleted.

**Behavior (C/D).** Typed list + rail with Contents/Notes/Activity/Settings,
per-kind filter through the API, member open handoff (documents → catalogue
reader with the new `library` origin, evidence → the stored snapshot through the
existing evidence reader, answers → their conversation message, notes → the
Notes tab, otherwise a stated reason), create/rename/settings/favourite/delete,
member removal, notes CRUD, activity, JSON/Markdown export, conflict (409),
tombstone (410), unavailable (404/401/403) and refused-member (422) states,
per-resource request epochs, and no write from browsing.

**Responsive/a11y (E).** Receipts at 1586x992 (reference-native), 1440x900,
1280x856, 1024x768, 390x844 and 1440x700 with zero body/root horizontal
overflow; axe scan (color-contrast, label, button-name, link-name,
aria-input-field-name) clean at the reference viewport; modal dialogs with
focus trapping and Escape; keyboard tab/tablist operation. Two dark-theme
contrast defects this page exposed were fixed in `collections.css`: primary
buttons now use the button token (white on `--primary` measured 3.38:1) and the
selected card's description uses the stronger text tone (measured 4.16:1).

### Visual Comparison (reference loop)

`docs/ui-references/collections-ui-reference-dark-v1.png` (1586x992) was
measured with PIL/numpy edge scans, then the rendered page was captured at the
same viewport and compared: iteration 1 showed a two-column card grid and a
light-theme, half-painted capture (entry animation), iteration 2 fixed the
default density to the reference's single-column rows, added the items glyph to
the card meta, stopped repeating a member's citation as its own provenance line,
widened the rail to the measured 583 px and added stat-strip glyphs. Remaining
deltas are capability-driven and deliberate: no Share tab or "Shared with Me",
no owner line, no storage/plan chrome, and the tabs/labels of the rail use this
product's wording.

### Tests Actually Run

- `bunx vitest run src/lib/collectionModel.test.ts` — 25 pass.
- `bunx vitest run src/components/collections/CollectionsWorkspace.test.tsx` — 11 pass.
- `bunx vitest run` (full unit suite) — 75 files / 495 tests pass, `tsc --noEmit` clean.
- `bunx playwright test e2e/ui-008-collections.spec.ts` — 15/15 Chromium, 15/15
  Firefox (16 tests × 2 engines reported as 32 passed).

### Remaining Work

UI-008-F (build), G (focused engine gates), H (controlled full gates, reference
receipt, artifact audit, documentation, commits).

### Exact Next Action

Run the controlled full browser gates and the reference receipt, then finish the
artifacts and commits.

## UI-008-F/G/H Checkpoint (gates, audits, commits)

UI-008 — Collections. Status: F–H complete.

### Gate Results (controlled worker count 4 for full runs, 2–3 focused)

- Full unit suite: 75 files / 495 tests pass (baseline 74 / 460, +1 file / +35
  tests), `tsc --noEmit` clean, production build green (the browser gates build
  the bundle through `webServer`).
- Focused spec: `e2e/ui-008-collections.spec.ts` 15 tests × 2 engines, all pass.
- Controlled full Chromium: 165 passed, 2 skipped, 1 failed —
  `regression.spec.ts:1039` (the documented load-sensitive performance budget;
  isolated rerun passes at p95=46.4 ms against a 100 ms budget).
- Controlled full Firefox: 163 passed, 2 skipped, 3 failed —
  `regression.spec.ts:65`, `regression.spec.ts:656`,
  `workspace-performance.spec.ts:176`. All three pass in isolation (verified
  in this task), and `:65`/`:176` are the recorded load-sensitive class from
  UI-006/UI-007. None of them touches the collections surfaces.
- Reference receipt (`e2e/reconciliation-reference.spec.ts`, both engines):
  30/30, with the r4 library surface now driving the real save flow
  (Search → Save evidence → create the collection in the target dialog →
  Collections → open → member row) instead of the removed browser-store console.
- Receipts captured under the git-ignored `frontend/test-results/ui-008/`:
  six viewports × two engines plus the reference-native comparison image.

### Artifact Audit

No Playwright traces, videos, reports, debug dumps, runtime databases or
WAL/SHM files were added to the source tree; `frontend/test-results/` and
`frontend/playwright-report/` are git-ignored. No credentials or bearer tokens
exist in the frontend (the local workspace token is deliberately not held by the
browser build). The only new stylesheet is page-owned; the shared
`frontend/src/styles/console.css` was not modified. `git diff --check` is clean
for every staged file.

### Files

Created: `frontend/src/lib/collectionModel.ts` (+ test),
`frontend/src/components/collections/` (13 components + the workspace test),
`frontend/src/styles/collections.css`, `frontend/e2e/ui-008-collections.spec.ts`.
Modified: `frontend/src/types.ts`, `frontend/src/lib/api.ts`,
`frontend/src/App.tsx`, `frontend/src/index.css`,
`frontend/src/components/workbench/RouteDocumentContext.tsx`,
`frontend/src/components/DocumentWorkspace.tsx` (the additive `library` origin),
`frontend/e2e/fixtures.ts` (the collections fixture), plus the two untracked
specs the flow changed (`e2e/reconciliation-reference.spec.ts`,
`e2e/v5-07-handoffs.spec.ts`).

Removed: `frontend/src/components/CollectionsConsole.tsx` and its test.

### Disclosure

`e2e/reconciliation-reference.spec.ts` and `e2e/v5-07-handoffs.spec.ts` stay
untracked, as UI-007 disclosed them; their UI-008 edits ride in the working tree
and are exercised by the receipt and handoff gates. Unrelated pre-existing
dirt (`components/DocumentWorkspace.test.tsx`, `components/EvidenceCollectionsPanel.tsx`,
`tests/fixtures/workspace_transfer_roundtrip.json`) was left untouched.

### Exact Next Action

Commits are recorded below; then read the master plan and set the next task
without implementing it.

### UI-008 Closure (commits, gates, next task)

Commits: `493513e feat(ui): rebuild collections on the typed workspace API`,
`8357e44 test(ui): cover the collections workspace with fixtures and browser
gates`, `431f351 docs: record the UI-008 collections workspace closure`. The
dirty-path count moved from 140 to 136; every remaining path is the historical
predecessor work this task preserved, including the two untracked specs it
updated (`e2e/reconciliation-reference.spec.ts`, `e2e/v5-07-handoffs.spec.ts`)
and the unrelated `components/DocumentWorkspace.test.tsx`,
`components/EvidenceCollectionsPanel.tsx` and
`tests/fixtures/workspace_transfer_roundtrip.json` dirt it did not touch.

Final numbers: unit suite 75 files / 495 tests (from 74 / 460), `tsc` clean,
build green; UI-008 spec 15 tests × 2 engines all passing; controlled full
Chromium 165 passed / 2 skipped / 1 failed (`regression.spec.ts:1039`, isolated
rerun p95 = 46.4 ms against a 100 ms budget) and controlled full Firefox 163
passed / 2 skipped / 3 failed (`regression.spec.ts:65`, `:656`,
`workspace-performance.spec.ts:176`, each passing in isolation); reference
receipt 30/30; backend untouched at 1018 / 0 / 188.

### Next Task Selection (from the master plan)

`docs/UI_REBUILD_MASTER_PLAN.md` §21 orders the graph and its task table. With
UI-008 complete, the next entries are `API-006 Model/dataset registries`
(dependency API-002, complete; parallel opportunity UI-008, now finished) and
then `UI-009 Models/Datasets` (dependencies UI-002 and API-006). Repository
evidence confirms no registry service exists yet: the API has no registry
router, `src/api/routers/system.py` exposes only the configured embedding and
reranker identity, and the Models page is still the pre-rebuild
`ModelsConsole`. API-006 is therefore the next dependency-ready task in the
saved priority order.

### Exact Next Action

**API-006 — Model/dataset registries** (dependency `API-002`, area "Registry
services", gate "Actual config/manifests"). Do not implement it, and do not
begin `UI-009`, `DATA-004`, `API-007`, `UI-010` or any later task without
explicit authorization.

### Post-Commit Security Audit (UI-008)

Mimosa deep scan (job `scan-job-muc7shvg-90001b3d74ff2ee8`, scan
`scan-2026-09-22T05-09-48.249Z-a4092b62c778`, seal
`sha256:9746254a4d9ffc15cc698b25c1a3d54d58e8442f5c90fa6d2754e17bca4fd1e2`,
static-only, verdict effect none): 307 findings repo-wide, of which 303 are
inside generated bundles that are scanned as source (`frontend/dist-local`,
`frontend/dist-integration`, `frontend/playwright-report/trace`). The four
source findings are identical to the pre-UI-008 baseline recorded with DATA-003:
three medium cross-file taint hypotheses on `frontend/src/App.tsx` that point at
a minified code-mirror bundle, and one high SQL-injection finding on
`src/workspace/database.py`'s `PRAGMA busy_timeout` (interpolates an int clamped
to 100..30000 from operator configuration, not reachable from a request).

No UI-008 file — page, rail, dialogs, model, client, stylesheet, spec or fixture
— carries a finding. The staged UI-008 changes were inspected for secrets: the
browser build holds no bearer token, no credential and no workspace path, and no
fixture contains a real credential. This is not a repo-wide clean bill: the
generated-bundle noise and the four pre-existing source findings remain.

### Stitch Result (recorded honestly)

After the implementation had already been measured and iterated against the
authoritative screenshot, one bounded Stitch generation was requested in the
existing high-fidelity reconstruction project
(`projects/3773610233677432915`, design system "Enterprise Document QA —
High-Fidelity Screenshot Reconstruction") for the Collections composition, with
the measured geometry (220 nav / ~750 main / ~583 rail), the card and rail
anatomy, and the explicit omissions (no sharing, owner, storage meter or plan
controls). The generation completed and described exactly that composition, so
it independently corroborates the structure — but per the documented precedence
the local screenshot remains authority #1 and no Stitch output, markup or demo
content was imported into the repository. The page was built from the measured
reference, the UI-001 tokens and the console primitives.

## REPAIR-R1-R4 Checkpoint (verified repair plan, in progress)

Status: ACTIVE. HEAD before repairs `1858924` (UI-008 complete, API-006 paused).
Dirty tree: 59 tracked modifications + 77 untracked entries = 136 paths, 0
staged; the historical work is intentional and preserved.

### Verified Findings (re-checked against current source, not assumed)

- **R1 (P0)** — `src/workspace/collections.py:756` `delete_collection` loops over
  `_children(ITEM_ENTITY_TYPE)` and `_children(NOTE_ENTITY_TYPE)` and deletes each
  child through `_delete`, and every `_delete` goes through
  `SQLiteVersionedRecordRepository.delete` (`src/workspace/repository.py:322`),
  which opens **its own** `database.transaction(write=True)` and commits. The
  parent revision check therefore happens *last*, after the children are already
  committed. `_children`/`_scan` also read outside any write transaction, and
  `record_activity` is another independent commit. The same shape exists in
  `create_collection` (list-check → create → activity), `add_item`/`add_note`
  (get parent live check → capacity count → create → activity), `update_*` and
  `delete_item`/`delete_note`: checks and writes are separate transactions, so a
  tombstone or a capacity race can interleave between them.
- **R2 (P1)** — `src/api/app.py:655` configures CORS with
  `allow_methods=["GET", "POST", "DELETE"]`. `PATCH` is missing, so a browser
  preflight for `PATCH /collections/{id}` (rename/settings) and
  `PATCH /collections/{id}/notes/{id}` is answered `400 Disallowed CORS method`
  even though both routes exist and the UI uses them.
- **R3 (P1)** — the collection card's overflow menu ("Delete collection") and the
  rail's overflow menu call the delete handler straight away; only the rail's
  Settings tab asks for confirmation first. Two of three entry points therefore
  write without confirmation.
- **R4 (P2)** — `CollectionsWorkspace.tsx` `loadSelection` only bumps
  `selectionEpoch`/aborts in its *network* branch. The cached-collection branch
  (`inPage`) and the cleared branch (`!selectedCollectionId`) return without
  invalidating an in-flight read, so a slower response for collection A
  overwrites the cached selection B (and the cleared state). Mutation callbacks
  (`handleToggleFavorite`, `handleRename`, `handleDeleteFromList`) also capture a
  collection by closure and mutate `selected`/navigate with no lifetime guard.

### Planned Order and Files

R1 → R2 → R3 → R4, each with focused regression tests before/with the fix and a
separate commit. R1: `src/workspace/repository.py`,
`src/workspace/collections.py`, `tests/test_collections_atomicity.py` (new). R2:
`src/api/app.py`, access/CORS tests. R3/R4:
`frontend/src/components/collections/*` (+ the shared confirmation dialog),
`frontend/src/lib/collectionModel.ts` if needed, `e2e/ui-008-collections.spec.ts`.

### Recorded Baseline (Codex audit, actually verified there)

187 focused backend tests (collections, access, transfer, catalog,
retrieval-inspection metadata, original viewer, discovery Search) and 23 focused
frontend tests with `bun run lint` (`tsc --noEmit`) passing. Historical broader
baseline: backend 1018 passed / 0 failed / 188 warnings; frontend 75 files / 495
tests. The historical numbers are not re-run results.

### Exact Current Action

R1 — write a regression test that reproduces the stale-delete cascade against the
current code, then introduce connection-scoped versioned-record operations so one
logical collection mutation is one SQLite write transaction.

## REPAIR-R1–R4 Closure — 2026-09-22

Status: **COMPLETE**. The repairs were applied in the required R1 → R2 → R3 →
R4 order. API-006 was not started. HEAD before repairs was `1858924`.

### REPAIR-R1 — COMPLETE

- Root cause: collection mutations composed independently committing
  versioned-record operations, so validation, child/note cascades, activity, and
  parent tombstoning did not share a transaction. Stale deletes could mutate
  children, and parent/capacity checks could race the write they guarded.
- Repair: `src/workspace/repository.py` now exposes connection-scoped internal
  get/create/replace/delete/tombstone operations while retaining the public
  one-transaction APIs. `src/workspace/collections.py` composes each logical
  mutation inside one SQLite write transaction, validates the live parent and
  expected revision before cascading, and serializes capacity check + insert.
- Coverage: `tests/test_collections_atomicity.py` uses controlled barriers/events
  and injected failures to cover stale-delete preservation, activity, atomic
  success/rollback, tombstoned-parent rejection, add/delete and capacity races,
  reopen durability, revision semantics, and transfer compatibility.
- Result: new atomicity suite `11/11`; combined Collections persistence,
  repository/domain/API, DATA-001, DATA-002, and DATA-003 regression `135/135`.
- Commit: `ebb8823 fix(workspace): make collection mutations atomic`.

### REPAIR-R2 — COMPLETE

- Root cause: CORS permitted GET/POST/DELETE but omitted PATCH even though
  collection and note updates use PATCH.
- Repair: `src/api/app.py` adds only `PATCH` to the existing explicit method
  allowlist. Origin/header/Host/loopback/private-mode and bearer enforcement are
  unchanged; a successful preflight does not authorize the real request.
- Coverage: `tests/test_collections_cors.py` exercises the ASGI preflight and
  denied Origin/header/PUT cases plus missing/wrong bearer requests.
- Result: focused access/CORS/Collections contract selection `50/50` (60
  deselected).
- Commit: `6220b18 fix(api): allow collection PATCH preflights`.

### REPAIR-R3 — COMPLETE

- Root cause: list and detail menu actions invoked deletion directly while only
  Settings confirmed.
- Repair: `CollectionDeleteDialog` and `CollectionsWorkspace` provide one
  deletion owner for list, detail, and Settings. Confirmation captures ID,
  revision, and name; Cancel/Escape are write-free, pending state prevents a
  second submit, 409 remains visible without retry/overwrite, and the shared
  modal owns initial/return focus with bilingual copy.
- Result: the combined collection/model/client frontend slice passed `64/64`;
  final component coverage is included in the `23/23` workspace suite. Browser
  coverage now proves list Cancel/Escape/focus, detail conflict/exact revision,
  and one successful Settings DELETE.
- Commit: `60562d5 fix(frontend): confirm collection deletion consistently`.

### REPAIR-R4 — COMPLETE

- Root cause: only the network selection branch invalidated the prior read;
  cached and cleared branches allowed late A data to overwrite B or a newer A
  lifetime, and mutation completions had no selection-lifetime ownership check.
- Repair: selection route generations advance synchronously on every route
  identity change, every read branch first invalidates/aborts the prior epoch,
  detail UI is keyed by lifetime, and read/mutation callbacks must match the
  live generation and collection identity before changing detail, drafts,
  errors/loading, or navigation. AbortError remains non-user-facing; a server
  mutation may still complete and safely refresh list data.
- Result: `CollectionsWorkspace.test.tsx` `23/23`, including cached B, clear,
  A1→B→A2, notes/activity, draft, loading/error, late mutation, and delayed
  navigation cases.
- Commit: `47c4ea6 fix(frontend): guard collection async state by selection lifetime`.

### REPAIR-FINAL — COMPLETE

- Additional browser receipt commit:
  `8aa5af4 test(frontend): cover collection delete repair journeys`.
- Full hermetic backend: `1035 passed`, `0 failed`, `188 warnings`; warning count
  did not grow from the recorded baseline.
- Full frontend: final controlled Vitest `75 files / 507 tests`, all passed.
  An earlier unconstrained run produced one load-sensitive failure in the
  pre-existing App route-change cancellation test; its immediate focused rerun
  passed, and the final controlled full run passed all 507 tests.
- TypeScript: `bun run lint` passed. Production build: `2060` modules
  transformed and build passed; only the existing chunk-size advisory remained.
- Production-like UI-008 browser matrix with one worker: Chromium `18/18`,
  Firefox `18/18`, `36/36` total. The first draft of the new conflict assertion
  incorrectly queried modal-hidden background content (`34/36`); the corrected
  modal-semantic assertion passed focused `4/4` and then full `36/36`.
- `git diff 1858924..HEAD --check` and the final staged-diff checks are clean
  apart from normal Windows LF/CRLF notices. No task-created SQLite/WAL/SHM,
  debug/log/report, screenshot, trace/video, build output, or runtime directory
  is committed. Existing ignored/untracked artifacts were preserved.
- Dirty tree: recorded start `59` tracked modifications + `77` untracked entries
  (`136` paths), `0` staged. Closure returns to the same `136` unrelated paths
  and `0` staged after the repair/checkpoint commits; no historical path was
  reset, cleaned, stashed, or mass-staged.

### Remaining Boundaries and Exact Next Action

The browser still does not own or persist the local bearer token; the planned
memory-only local connection/token owner remains staged architecture. No token
was hardcoded or placed in localStorage/IndexedDB, and API-001 was not weakened.

The verified clean-checkout issue remains: committed runtime code imports
dependencies that are still untracked, so a fresh clone is not self-contained.
Do not solve this by mass-staging the historical worktree.

Roadmap status: UI-008 remains the latest completed product task; no roadmap
feature is in progress. **Exact next action: `REPAIR-005 — Restore
clean-checkout/runtime dependency closure`.** After that separate task is
completed, roadmap work may resume with API-006. Do not begin either task as
part of this closure.

## REPAIR-005 — Clean-checkout/runtime dependency closure

### REPAIR-005-A — Recovery and investigation start

Status: ACTIVE. Starting HEAD is `1585444` on
`codex/bilingual-research-workspace`. The active tree matches the recorded
handoff: 59 tracked modifications, 77 untracked entries, 136 status paths, and
0 staged files. All are being treated as potentially intentional until
classified.

Known failure: the committed application is not source-complete in a clean
checkout. Tracked backend composition imports untracked modules including the
PDF representation/generator, SEC URL helper, and router package; the tracked
frontend entry graph also resolves through multiple untracked source files in
the active tree. This stage records the failure as unproven until reproduced
from a detached worktree at `1585444`.

Investigation method: reproduce `import src.api.app` in a temporary detached
worktree; statically trace Python and TypeScript imports from tracked runtime and
committed tests; inspect non-import assets/manifests and history; classify each
required untracked candidate as source, test/contract, authority, future work,
artifact, diagnostic, or mixed ownership; then stage only evidence-backed
closure batches. The final proof will use a second clean detached worktree at
the resulting committed HEAD. No file is staged at REPAIR-005-A, and API-006 is
explicitly out of scope.

### REPAIR-005-B — Dependency graph and candidate classification

Status: COMPLETE. A detached worktree at `1585444` reproduced the backend
failure from source-only state:
`ModuleNotFoundError: No module named 'src.api.sec_urls'` while importing
`src.api.app`. Running from the active checkout had initially contaminated the
namespace-package search path; rerunning with the detached worktree as the
process directory produced the authoritative failure. The same checkout's
TypeScript graph reported missing route, conversation, workbench, reader,
source-presentation, SEC URL, console, and stylesheet modules plus companion
type/prop mismatches where committed call sites relied on completed-but-dirty
tracked edits.

Classification:

- **A — required source closure:** `src/api/sec_urls.py`,
  `src/api/pdf_generator.py`, `src/api/pdf_representation.py`, and the untracked
  router package files for cache, corpus, evaluations, health, sessions,
  system, and workspace transfer (plus `routers/__init__.py`). These are direct
  imports of committed `src/api/app.py`, principally introduced by `a0f7a80`;
  ReportLab and the additive PDF reader manifest/model fields are their required
  tracked companions. Frontend source closure comprises `src/app/routes.ts`,
  the current Models/Pipeline route components, PDF viewer, conversation shell
  components, UI foundation exports, workbench/reader hooks, SEC/source/deep-link
  helpers, DATA-002 browser workspace helpers, legacy-seed guard, and the
  workbench/console/primitives/PDF styles. Documented tracked companion edits in
  `frontend/src`, the package/lock manifests, SPA rewrite, and `.local/` ignore
  rule belong to already-completed UI-001–UI-008, V5, PDF, and DATA work and are
  needed for the committed call sites/types to agree.
- **B — required test/contract closure:** the backend PDF, SEC URL, API-001,
  DATA-001, DATA-002 and transfer canonicalization suites and shared JSON
  fixture; the corresponding tracked API/harness adjustments; frontend route,
  foundation, conversation, workbench, reader, deep-link, SEC URL, legacy-seed,
  workspace backup/repository, collection-favorite, and API tests; and completed
  browser contracts for UI routing, UI-003, V5-00/02/04/05/07, PDF viewer, and
  the nine-reference receipt. Existing tracked browser/test edits that target
  these completed contracts are part of the same test closure.
- **C — documentation/reference authority:**
  `docs/UI_REBUILD_MASTER_PLAN.md`, `docs/UI_REFERENCE_GAP_MATRIX.md`,
  `docs/frontend/V5_WORKBENCH_CONTRACT.md`, and the nine specifically named
  reference PNGs under `docs/ui-references/`. Tracked README, architecture,
  frontend design, and implementation journal edits describe the same completed
  source and remain documentation candidates rather than runtime inputs.
- **D — unfinished future work:** no candidate source file implements API-006,
  UI-009, DATA-004, or later work. `ModelsConsole.tsx` and
  `PipelineConsole.tsx` are classified A because committed routes import their
  existing read-only/current-state placeholders; they contain no registry,
  switching, durable-job, or pipeline mutation implementation.
- **E — generated/tool/runtime artifact:** `.audit-runtime/`, `.mimosa/`, both
  frontend equivalents, `screenshots/`, `harness_stacks.txt`, generated build
  and browser outputs, databases/WAL/SHM, caches, logs, traces, videos,
  `node_modules`, and virtual environments remain excluded.
- **F — obsolete/ad-hoc diagnostic:** `frontend/e2e/capture-ui-round.mjs`,
  `probe-box.mjs`, `probe-contrast.mjs`, `.zcodeignore`, and the stale
  `PROJECT_CONTEXT.md` handoff are not required by the current build or test
  graph. `frontend/e2e/v5-1-visual-capture.spec.ts` is also excluded: it is a
  one-off capture script with a developer-specific absolute output path, not a
  portable test contract.
- **G — ambiguous mixed ownership:** resolved. The tracked dirty frontend
  source/tests named by completed checkpoint receipts are eligible companion
  closure; unrelated artifact/diagnostic paths above are not. No source file
  requires splitting future API-006 behavior from current behavior.

Planned coherent batches: backend runtime; backend tests/contracts; frontend
runtime and completed companion source; frontend tests/contracts; authoritative
planning/reference assets; final checkpoint/project-state closure. No files
were staged while building this inventory.

### REPAIR-005-C — Backend source closure

Status: COMPLETE. Commit `1931f87` (`fix(repo): restore backend runtime source
closure`) adds the eleven missing backend modules and the tracked ReportLab/PDF
reader contract companions. A staging check caught and removed one extra blank
line at EOF before the commit was amended; `git show --check` is clean.

Focused source validation passed `51/51` across router inventory, PDF pipeline,
SEC URL safety, document sources, original viewer, structured document, and
structured location tests. A clean detached worktree at
`D:\Project\Enterprise_Document_QA-repair005-backend`, commit `1931f87`, then
imported `src.api.app`, every current router module, the PDF generator/store,
and SEC URL helper exclusively from that worktree; the application composed 63
routes. The active checkout was not used as a Python source path for this proof.

### REPAIR-005-D — Test and frontend closure

Status: COMPLETE. Commit `0114cb6` (`test(repo): restore backend contract
closure`) adds the PDF, SEC URL, local-access, workspace persistence/transfer,
and canonical transfer tests plus their shared fixture and harness companions.
Its focused backend contract gate passed `251/251`; `git show --check` is clean.

Commit `05df347` (`fix(repo): restore frontend runtime source closure`) restores
the completed application routing, conversation/workbench, reader/PDF,
workspace, source/deep-link, console, style, dependency, and deployment
companions required by the committed frontend graph. TypeScript and the
production build passed before commit with `2060` modules transformed; the only
build diagnostic was the existing chunk-size advisory. Commit `59dfaa9`
(`test(repo): restore frontend contract closure`) adds the matching unit,
component, and maintained browser contracts. The active-tree Vitest gate passed
`75` files / `507` tests before that test commit. The ad-hoc capture/probe files
and developer-path visual-capture spec remain excluded.

### REPAIR-005-E — Documentation and reference authority

Status: COMPLETE. Commit `17dafe2` (`docs(repo): restore rebuild authorities
and references`) adds the master dependency plan, reference-gap matrix, V5
workbench contract, and the nine named PNG reference authorities, and commits
their existing README, architecture, design, and implementation-journal
companions. Every reference file has the PNG signature. A developer-specific
source path in the V5 contract was replaced with the repository-relative copy;
staged secret/path and whitespace checks found no actionable finding.

### REPAIR-005-F — Clean-checkout proof and closure

Status: COMPLETE. A new detached worktree at commit `17dafe2` was used for all
proof commands. `src.api.app`, every restored router, the PDF generator/store,
and SEC URL helper imported from the detached worktree itself, and FastAPI
composed `63` routes. The focused backend cross-layer gate passed `341/341`.
The complete hermetic backend suite passed `1001`, skipped `34`, and reported
`148` warnings with no failures. `pytest -rs` confirmed that every skip was for
an unavailable git-ignored evaluation artifact or local filing/corpus.
TypeScript (`bun run lint`) passed, the production build passed with `2060`
modules transformed, and clean-checkout
Vitest passed `75` files / `507` tests. The build emitted only the existing
chunk-size advisory.

No browser matrix was rerun because REPAIR-005 changes repository membership,
not the already-active runtime behavior that previously passed the focused
production-like UI-008 browser gate. No provider, SEC, Hugging Face, Groq, or
Qdrant network call was made. API-006 and later registry/job behavior were not
implemented.

Repository hygiene: five coherent source/test/authority commits close the
runtime graph without mass staging. Generated output, runtime databases,
scanner state, screenshots, debug probes, stale handoff material, and the
developer-specific capture test remain untracked and preserved. The final
documentation commit records the proof and project-state transition; no
historical receipt was rewritten.

Roadmap status: REPAIR-005 is complete. The clean-checkout blocker no longer
precedes product work. The browser still lacks the planned memory-only local
connection/token owner; API-001 remains unchanged, and Collections continues to
show its truthful unavailable/unauthorized state until that staged integration
is implemented. Subject to normal task scoping, the next product task remains
`API-006 — Model/dataset registries`.

## API-006 — Model/dataset registries

### API-006-A — Exact contract and authority map

Status: ACTIVE. Starting HEAD is `2a651fc` on
`codex/bilingual-research-workspace`; the tracked tree is clean, the 12
classified untracked artifact/diagnostic entries remain preserved, and nothing
is staged.

The master-plan contract resolves to these additive routes:

- `GET /models?role=generator|embedding|reranker` — public (`P`), allowlisted,
  provider-free configured/runtime registry;
- `POST /models/{id}/tests` — execution-gated (`J`) bounded local
  `runtime_identity` test with no provider request, inference, model download,
  or cache mutation;
- `GET /datasets?kind=corpus|evaluation` — public (`P`), provider-free registry
  summaries;
- `GET /datasets/{id}` — public (`P`) coverage and provenance detail, with 404
  for an unknown opaque registry ID.

Stable model IDs are the canonical roles `generator`, `embedding`, and
`reranker`, returned in that order. Each entry separates configured identity
and revision from observed runtime identity and revision, and reports
configuration, load, and availability independently. Remote generator
reachability remains `unknown` unless an explicit provider operation proves it;
ordinary reads never perform that operation. Embedding/reranker availability is
reported only from an already-loaded local runtime object. An absent revision
is `unknown`, not an empty version claim.

Model authorities are the existing Generator default/runtime identity,
`Settings.embedding_model_*`, `Settings.reranker_model_*`, and the already
constructed application pipeline. Credential inspection is reduced to a
boolean configuration fact and no value/alias is serialized. No setting object,
provider client, model cache path, or device path is exposed.

Stable dataset IDs are `serving-corpus` and `evaluation-test-set`, ordered
corpus then evaluation. Serving counts and year coverage reuse API-003
`build_stats` over the application-owned catalog. Index provenance is
allowlisted from the configured Qdrant index manifest and checked against
catalog chunk totals plus the configured embedding binding; missing, invalid,
or mismatched manifests produce explicit degraded provenance rather than fake
zero/healthy data. The evaluation dataset derives only aggregate coverage and a
deterministic content fingerprint from `src.evaluation.test_set.TEST_SET`; it
does not expose questions or ground truth. Dataset is not collection, document,
search snapshot, retrieval preset, or evaluation report.

Planned files: a typed registry model module, a provider-free registry domain
service, a thin registry router, app composition and route-contract updates,
focused API-006 tests, then README/architecture/current project records. No
frontend runtime file, retrieval/generation algorithm, corpus/index artifact,
workspace schema, or future UI-009/DATA-004/API-007 behavior is in scope.

### API-006-B — Registry domain and typed contracts

Status: COMPLETE. `src/api/registry_models.py` defines explicit model,
configuration/load/availability, dataset summary/detail/coverage, provenance,
and bounded-test response models. `src/api/registry.py` assembles them in fixed
model-role and dataset order from injected existing authorities. It constructs
no model, provider client, store, reader, workspace database, or remote request.
The initial focused API-006 file passes `14/14` tests.

### API-006-C — Model registry and redaction boundary

Status: COMPLETE. The three canonical model IDs are `generator`, `embedding`,
and `reranker`. Configured identity/revision, observed runtime
identity/revision, load state, credential-presence state, and availability are
separate fields. Generator reachability remains unknown without a provider
probe; already-loaded local embedding/reranker objects may report available
only when their public identity and configured revision agree. The default
generator ID was lifted into a shared constant without changing its value or
generation behavior.

The public-identifier allowlist rejects absolute/local paths, file/credential
URLs, traversal segments, backslashes, control/unsupported characters, and
common secret-token prefixes. Secret-bearing settings are inspected only for a
boolean credential fact. Adversarial tests inject provider secrets, a private
model-cache path, an unsafe runtime identity, and unsafe manifest metadata and
prove none are serialized. Reads also use model/provider mocks that fail if
embedding, reranking, or generation is invoked.

### API-006-D — Dataset registry and provenance

Status: COMPLETE. `serving-corpus` reuses API-003 `build_stats` for document,
company, chunk, year, section, and configured-company semantics. Its Qdrant
index manifest is shape-checked, public-field allowlisted, and reconciled with
catalog chunk count, configured embedding ID/revision, and a recomputed loaded
corpus fingerprint. Missing, invalid, hash/binding-mismatched, unavailable, and
genuinely empty states are distinct. `evaluation-test-set` exposes only stable
aggregate category/priority/ticker/section coverage and a deterministic SHA-256
revision over the source-controlled `TEST_SET`; question and ground-truth text
are not returned.

### API-006-E — Router, access, and focused regression

Status: COMPLETE. `src/api/routers/registries.py` owns the four additive routes
and one execution-gated operation: public `GET /models`, public
`GET /datasets`, public `GET /datasets/{id}`, and local execution-gated
`POST /models/{id}/tests`. The bounded test checks configuration/runtime
identity only and reports `provider_executed=false`; it performs no inference,
network access, provider call, download, or cache mutation. Public mode returns
the existing fail-closed 404 for that `J` route. The API-002 route inventory now
records 67 application routes and retains the frozen legacy extracted-route
OpenAPI digest.

Focused API-006 + API-001/API-002/API-003 + manifest/embedding/index + model
regressions pass `175/175` with five existing warnings. Compile/import checks
pass, and direct application inspection reports exactly the four registry paths
above. No frontend file is changed.

Implementation and focused tests are committed as `de907a7`
(`feat(api): add truthful model and dataset registries`). The full hermetic
backend gate is the next operation; until it completes, API-006 remains active
and its result is unknown.

### API-006-F — Full gate, audit, and closure

Status: COMPLETE. The full hermetic backend suite in the main worktree passed
`1050/1050` with zero failures and 188 existing dependency/parser warnings in
132.90 seconds. The count is higher than the clean-checkout REPAIR-005 baseline
because this checkout retains the deliberately excluded local corpus/evaluation
artifacts; no skip was forced and no canonical data was changed. The focused
registry file passes `14/14`; the cross-layer API-006 regression gate passes
`175/175`. Compile/import and 67-route inspection passed. No frontend file
changed, so TypeScript, Vitest, build, and browser gates were correctly not run.

The API-006 delta contains no provider response, environment dump, credential,
authorization value, database, log, scanner state, generated build output,
cache, report, or real private/developer path. Synthetic secret/path strings
exist only in redaction tests. All 12 pre-existing excluded untracked
artifact/diagnostic entries remain untracked and preserved. Ordinary registry
reads made no network, SEC, Groq, Hugging Face, Qdrant Cloud, inference,
download, or cache-mutating call. The implementation commit is `de907a7`
(`feat(api): add truthful model and dataset registries`); the public contract,
architecture, project-state, and validation record is `4fd5577`
(`docs(api): record registry contracts and validation`).

API-006 is complete without model/dataset mutation or frontend work. The master
dependency graph at `docs/UI_REBUILD_MASTER_PLAN.md` places `UI-009 —
Models/Datasets` immediately after API-006; that is the exact next action and it
has not started.

## UI-009 — Models/Datasets

### UI-009-A — Contract, reference, ownership, and baseline map

Status: ACTIVE. Starting HEAD is `ed22100` on
`codex/bilingual-research-workspace`; tracked and staged state are clean and all
12 deliberately excluded artifact/diagnostic entries remain preserved.

Owned routes are the existing direct `/models` and `/datasets` shell routes.
The master plan defines a configured/runtime model registry with role filtering,
allowlisted details, and bounded supported local tests, plus a corpus/evaluation
dataset registry with coverage, provenance, and distinct missing/degraded
states. There is no model or dataset detail URL in the route plan, so selection
and detail stay page-local; direct route, sidebar, Back, and Forward behavior
remain under UI-002. Backend IDs (`generator`, `embedding`, `reranker`,
`serving-corpus`, and `evaluation-test-set`) are the only selection keys.

Models reads `GET /models` and its optional role filter. Its explicit Test
action, owned by the Models reference and gap matrix, calls only
`POST /models/{id}/tests` with `runtime_identity`; it is never automatic,
prevents duplicate submission, displays `provider_executed`, and treats
401/403/404/422 separately from an unavailable/failed check. It does not add a
token editor or imply provider reachability. Configured identity/revision,
observed runtime identity/revision, load, availability, and credential presence
remain separate. Unsupported reference controls—routing mutation, fallback,
cost optimization, performance routing, A/B testing, add/default/enable,
playground, comparison, latency, accuracy, cost, throughput, context window,
and dimensions—are omitted.

Datasets reads `GET /datasets` and optional kind filtering, then
`GET /datasets/{id}` for the selected summary. Corpus and evaluation details
use their discriminated coverage contracts. Availability, provenance status,
reason code/text, recorded zero, unknown/null, missing manifest, invalid
manifest, mismatch, unavailable catalog, and empty catalog remain distinct.
Evaluation renders aggregate coverage and deterministic revision only; no
question, expected answer, ground truth, or judge label is exposed. There are
no upload, delete, reindex, mutation, or job actions.

`models-ui-reference-dark-v1.png` is the sole UI-009 screenshot authority and
is 1586×992. Measured geometry: 205px grouped navigation, 58px top bar, content
beginning near x=224/y=80 with roughly 16px outer gutters; the upper region is
a 766px main card plus a 570px secondary card separated by about 10px; the
registry begins near y=470 and runs to the bottom with approximately 52px rows,
10–14px card padding, 8–12px control gaps, 8–10px radii, compact tabs, and a
blue selected state. UI-009 reuses that hierarchy—header, role/filter strip,
dense selectable registry, and a detail/test surface—but replaces every mock
control and metric with API-006 facts. Datasets has no reference screenshot per
`UI_REFERENCE_GAP_MATRIX.md`; it will reuse the Models registry/detail visual
language and current semantic tokens without fabricating screenshot data.

Task semantics: entry is a direct/sidebar Models or Datasets route; intent is
to inspect real runtime configuration or corpus/evaluation provenance;
available evidence is the corresponding API-006 response; primary interaction
is selection/filtering, with a separately explicit bounded model identity test;
success is a selected record whose facts and explanations match the response;
recovery is retry, filter reset, or selection of another record. List request
epochs own filter results; dataset-detail epochs own selected dataset results;
the model-test request is bound to the selected model ID. Abort and identity
checks prevent stale completions from repainting a newer selection. Nothing is
persisted and the page scroll remains the shell's workspace scroll owner.

Information hierarchy is page identity → filters/summary → selectable registry
→ selected detail/provenance → bounded action/result. Desktop uses a main/detail
split; compact widths stack detail after the registry; mobile uses cards rather
than squeezing a table. Required states are loading, empty, error/retry,
selected, unknown, unavailable, degraded, missing/invalid/mismatch, test
pending/result/refusal, and read-only. Risks under review: accidentally equating
configured with available; presenting unknown as false; showing reference-only
fake metrics/actions; stale list/detail/test results crossing identities; and
desktop tables causing page overflow or inaccessible mobile detail.

Planned files are exact API-006 types/wrappers and tests, page-owned Models and
Datasets components/tests/styles, minimal route/App composition, a dedicated
hermetic UI-009 Playwright spec/fixtures, and current checkpoint/project/frontend
contract records. No backend, package dependency, data artifact, DATA-004 job,
Pipeline execution, or unrelated frontend journey is in scope.

### UI-009-B — Typed clients, routes, and base surfaces

Status: COMPLETE. Exact frontend representations now cover every API-006 model
and dataset response field and preserve the backend unions for role, load,
availability, dataset kind, coverage discriminator, and provenance status.
The shared API client owns all six consumed request shapes (`GET /models`, its
role-filtered form, bounded model test POST, `GET /datasets`, its kind-filtered
form, and selected dataset detail) and forwards `AbortSignal`. `/datasets` is
now an available first-class workspace view instead of the old deferred
Evaluation placeholder. The initial API/route/component focus passes `47/47`.

### UI-009-C — Models state semantics and bounded action

Status: COMPLETE. The old `/system/info` diagnostic substitute is replaced by
the API-006 registry. Rows/cards use backend IDs, fixed backend role ordering,
and separate configured, runtime, load, availability, credential, and revision
facts. Page load and filtering perform GETs only. The explicit runtime identity
button is duplicate-protected, aborts when selection changes, renders
`provider_executed=false`, and classifies 401/403/404/422 separately. Tests
cover ordering, missing facts, unknown availability, selection, no automatic
POST, duplicate prevention, access refusal, and late filter response rejection.

### UI-009-D — Datasets detail, provenance, and race ownership

Status: COMPLETE. `DatasetsWorkspace` renders the API-owned corpus and
evaluation summaries and fetches detail only for the selected backend ID.
Corpus coverage distinguishes recorded zero, unknown, missing, invalid,
mismatch, unavailable, and degraded reason text; evaluation displays only
aggregates plus revision and explicitly states that questions/ground truth are
not sent to the browser. Detail/list requests have independent abort/epoch
ownership. Component tests cover corpus/evaluation discrimination, zero versus
unknown, 404 versus empty, kind filtering, no mutations, and both late-success
and late-failure rejection.

### UI-009-E — Visual, responsive, and accessibility loop

Status: COMPLETE. Direct comparison at the Models reference-native 1586×992
viewport preserves the measured 205px navigation, 58px topbar, x≈224/y≈80
content boundary, compact tabs, dense selected rows, 8–12px gaps, 8–10px
radii, blue selection, and dark registry/detail surfaces. The largest necessary
difference is contractual: the reference's routing/benchmark/mutation cards
are replaced by API-006 summaries and allowlisted detail. Datasets has no local
reference and uses the same established language without a fabricated visual
baseline.

Dark receipts were inspected at 1586×992, 1440×900, 1280×856, 1024×768,
768×900, 390×844, and 1440×700. Models changes from table to cards at 800px;
detail stays in document flow and reachable at every width. All measured
body/root overflows are zero. The visual loop exposed and fixed compact-table
compression plus light/dark status and secondary-text contrast. Focused axe
checks over both registry main regions now report no critical or serious
violations, with reduced motion enabled for deterministic inspection.

### UI-009-F — TypeScript, unit suite, and production build

Status: COMPLETE. TypeScript passes. The final full Vitest run passes `77/77`
files and `521/521` tests. An earlier full run under simultaneous build load
observed one new assertion reading its selected-detail shell before payload
paint and one pre-existing Collections timing assertion; the new assertion was
corrected to await the payload, the pair then passed `29/29`, and the isolated
final full run is green. Production build passes with 2061 modules and the
existing >500 kB chunk advisory only.

### UI-009-G — Browser and routing gates

Status: COMPLETE. The hermetic UI-009 Playwright fixture mirrors the API-006
schema and permits no real backend/provider traffic. The final dedicated spec
passes Chromium `7/7` and Firefox `7/7`. It covers direct loads, role/kind
filters, typed rows/cards, selection/detail, unknown and not-loaded semantics,
explicit identity test and provider flag, no browsing POST, execution-gate
refusal, degraded/missing/mismatched provenance, evaluation-safe aggregates,
Back/Forward, accessibility, both desktop/mobile compositions, all required
receipt widths, and zero overflow. The controlled UI-002 routing regression
passes `6/6` across Chromium and Firefox.

### UI-009-H — Audit, commits, and closure

Status: COMPLETE. Runtime and test implementation is commit `b35e1b5`
(`feat(ui): build truthful model and dataset registries`). The backend, package
graph, corpus/index data, route count, and API-006 contract are unchanged.
Public/frontend contracts, the project journal, and validation record are
commit `34b5b72` (`docs(ui): close UI-009 registry workspace`).
Production contains no reference fixture data, fake health/benchmark/cost
metric, secret, key, environment dump, private path, provider call, or dataset
mutation. Playwright screenshots/traces/videos, `dist`, test results, and audit
material are ignored and uncommitted. The 12 pre-existing excluded
artifact/diagnostic entries remain untracked and preserved.

UI-009 is complete. The dependency/priority graph places `DATA-004 — Durable
jobs` immediately after UI-009 and before API-007. That is the exact next
action; DATA-004 has not started.

## DATA-004 — Durable jobs

### DATA-004-A — Exact contract and persistence map

Status: ACTIVE. Starting HEAD is `9a2bf66` on
`codex/bilingual-research-workspace`; tracked and staged state are clean and the
same 12 deliberately excluded artifact/diagnostic entries remain untracked.

The saved master contract and DATA-001 migration v3 define three durable job
namespaces: `pipeline`, `evaluation`, and `model_test`. DATA-004 does not define
the future registered pipeline/evaluation job-type vocabulary, so `job_type`
remains a bounded opaque type owned by later consumers. It does define these
job states exactly: `queued`, `running`, `cancelling`, `cancelled`, `succeeded`,
`failed`, and `interrupted`. Ordered step states are `pending`, `running`,
`cancelled`, `succeeded`, `failed`, `skipped`, and `interrupted`. Terminal job
states are cancelled/succeeded/failed/interrupted and never transition again.

Legal job transitions are queued→running, running→succeeded/failed/interrupted,
running→cancelling on a cancellation request, cancelling→cancelled when a
worker acknowledges the stop, and cancelling→interrupted during restart
reconciliation. A queued cancellation is immediately cancelled because no
work has started. A running job cannot become cancelled without the distinct
cancelling acknowledgement boundary. No retry/requeue transition exists; a
retry is a new job request and identity. The contract defines no lease,
heartbeat, worker identity, distributed claim, deletion, retention cleanup, or
background scheduler, so DATA-004 adds none. Atomic queued→running plus expected
revision is the only claim-like primitive and two contenders cannot both win.

Creation accepts a caller idempotency key but stores only its SHA-256 digest.
Within a namespace, the same key and canonical request returns the same stable
opaque persisted job ID; reuse for a different type/configuration/payload/
artifacts/ordered-step definition is a deterministic conflict. Job IDs are
random opaque UUID-based IDs and are distinct from idempotency/correlation
identity. Every job or step mutation requires an expected revision and advances
the job revision; stale writers fail rather than overwrite.

Progress is stage plus an optional current/total pair. Both counts are absent
when unknown; when present total is positive and `0 <= current <= total`. No
percentage is persisted or inferred. Results are finite canonical JSON objects;
failure is a bounded allowlisted code and sanitized message. Payloads, results,
failure text, stage/type names, step definitions, and artifact references are
bounded. Credential-like keys/values, configured secrets, control characters,
and machine-specific absolute paths are rejected. Pickle/executable formats are
forbidden.

DATA-001 already supplies the one authoritative SQLite database, foreign keys,
WAL, busy timeout, process serialization, `BEGIN IMMEDIATE`, UTC timestamps,
checksum-tracked migrations, and fail-closed schema validation. Migration v3
created `jobs`, `job_steps`, and `job_events`, but it lacks idempotency, request
payload, current progress, result, sanitized failure message, and multiple
logical artifact references. DATA-004 therefore requires a new additive v4
migration. New columns are nullable for upgrade safety; new DATA-004 records
carry an explicit record schema version, while any pre-existing ambiguous v3
row fails closed instead of being discarded or silently reinterpreted. No
historical migration is changed.

Restart policy is explicit reconciliation, not repository-open side effects:
queued work remains queued; running or cancelling jobs become interrupted in
one transaction, their running steps become interrupted, pending steps remain
pending, and one ordered event records the recovery. This method is for the
single future coordinator startup boundary; merely opening another repository
cannot interrupt live work. Creation, transitions, progress, step updates,
cancellation, and recovery each update state/revisions/timestamps plus their
event in one transaction. Deterministic injected failures must roll the whole
logical operation back.

Jobs and job artifacts remain local/private until explicit cleanup. DATA-004
adds no HTTP route and does not construct the workspace in public mode. Jobs
remain excluded from the DATA-002 portable backup: that envelope contains
research records, not private execution history or run artifacts. There is no
browser writer, JSON file, second database, worker loop, provider invocation,
pipeline/evaluation execution, or frontend work.

Planned files: additive migration v4, a typed/testable durable-job domain and
SQLite repository exported from `src.workspace`, focused state/persistence/
rollback/restart/concurrency/migration/authority/transfer tests, then current
README/project/checkpoint records. API-007 and every execution adapter remain
out of scope.

### DATA-004-B — Migration and durable repository

Status: COMPLETE. Additive migration v4 extends the existing v3 job tables; no
historical migration was edited. It adds the DATA-004 record marker,
idempotency digest, canonical payload/result, logical artifact references,
stage/current/total progress, sanitized failure message, cancellation time,
event progress stage, and deterministic idempotency/listing indexes. A v3→v4
test preserves an existing legacy row, verifies every new column/index, and
proves the repository refuses to reinterpret that ambiguous row.

`src/workspace/jobs.py` provides the typed domain, pure transition validators,
and `SQLiteJobRepository`. Creation, state mutation, progress, step mutation,
cancellation/acknowledgement, recovery, and event pagination all share the
authoritative `WorkspaceDatabase` transaction boundary. Public settings still
cannot construct storage. Implementation is commit `986aca8` (`feat(data): add
durable job persistence`).

### DATA-004-C — Concurrency, ordering, and interruption

Status: COMPLETE. Every mutation requires the caller's expected revision and
advances the job revision. Step mutation also checks its own revision. SQLite
`BEGIN IMMEDIATE`, the existing bounded busy timeout/process lock, revision
predicates, and unique namespace/idempotency digest prevent split ownership.
The deterministic two-contender test produces exactly one start and one
conflict without sleeps. Job listing is created-time/job-ID stable; steps use
ordinal/job-ID order; events use monotonic per-job sequence and support bounded
after-sequence pagination.

Opening a repository has no recovery side effect. Explicit recovery leaves
queued work alone and atomically interrupts only running/cancelling jobs plus
running steps; pending steps remain pending. A second recovery is empty.
Deterministic injected failures after each mutation point prove that job, step,
revision, timestamp, and event changes roll back together.

### DATA-004-D — Safety, privacy, and compatibility

Status: COMPLETE. Payload/result/failure/progress/type/step/artifact/list bounds
are enforced before write. Canonical JSON rejects non-finite or executable
object data; recursive guards reject credential-shaped keys, configured secret
values, credential text, control characters, and absolute Windows/POSIX paths.
Only SHA-256 idempotency digests are stored. Artifact references are portable
opaque logical identifiers, never paths.

DATA-002 export reads only its allowlisted research-record domains. An explicit
test creates a durable job, exports the workspace, proves no jobs/events enter
the envelope, and proves the job is unchanged. Public mode creates no `.local`
state. No route, provider call, worker, browser persistence, deletion, retry,
lease, heartbeat, cleanup, or frontend surface exists.

### DATA-004-E — Validation gates

Status: COMPLETE. Focused durability plus persistence/transfer/collection/
access/matrix regressions pass `151/151` with one existing dependency warning.
The full hermetic backend suite passes `1077/1077` with `188` warnings, matching
the starting warning count while adding 27 passing DATA-004 tests to the
1050-test baseline. Compile/import checks pass; the exported repository imports
from `src.workspace`; the FastAPI application remains at 67 routes; and
`git diff --check` passes. Ruff is not installed, so no Ruff pass is claimed.
No network, SEC, Groq, Hugging Face, Qdrant Cloud, pipeline, evaluation, or
provider operation ran.

### DATA-004-F — Audit and closure

Status: COMPLETE. Runtime/test implementation is commit `986aca8`. Tracked
changes are limited to the additive migration, durable-job domain/repository,
workspace exports, focused tests, and current README/project/checkpoint records.
No generated database, run artifact, cache, report, screenshot, trace, build
output, secret, local path, canonical `data/` artifact, or frontend file is
included. The same 12 pre-existing excluded artifact/diagnostic entries remain
untracked and preserved.

Known limitations are the task boundary: concrete job-type registries belong to
their future consumers; a future coordinator must call restart recovery once;
and no retention/deletion policy exists because the saved contract does not
define one. DATA-004 is complete. The dependency/priority graph identifies the
exact next action as `API-007 — Pipeline staging`; it has not started.

## API-007 — Pipeline staging

### API-007-A — Contract and domain map

Status: COMPLETE. API-007-A records the contract and domain map before
implementation. Its starting HEAD was `3df8323` (`docs(data): close durable
jobs milestone`) on `codex/bilingual-research-workspace`; tracked/staged state
was clean when A began, and the same 12 top-level excluded
artifact/diagnostic entries remained preserved. At that point the untracked
`src/api/pipeline_models.py` and `src/api/pipeline.py` drafts had no router, app
wiring, registered route, or focused API test. Those statements record A's
starting state and are superseded by the completed B-F implementation below.

The API-007-B..F continuation began from actual checkout HEAD
`c44a5a85a3eaa3c18cee2d0fc76c753f44b17098`, after preserving
`195e79b fix(api): bound workspace import request reads` and
`c44a5a8 fix(security): enforce configured workspace host ports`. The working
checkpoint and API-007 drafts were preserved; no unrelated excluded paths
were staged or changed.

The master API table owns these six operations, in this order and with these
access classes: `GET /pipeline` (P: static definition/capabilities),
`GET /pipeline/runs` (L: filtered/pageable private history),
`POST /pipeline/runs` (J: stage a durable run with no canonical writes),
`GET /pipeline/runs/{id}` (L: durable run/step/artifact/status detail),
`POST /pipeline/runs/{id}/cancel` (J: truthful DATA-004 cancellation state),
and `GET /pipeline/runs/{id}/events` (L: ordered resumable SSE using
`Last-Event-ID`). These are the full API-007 Pipeline surface needed by
UI-010; no other Pipeline route is specified. P means public/provider-free; L
means API-001 local workspace access; J means L plus the existing execution
capability. Therefore run creation/cancellation require the existing
`require_execution_access` grant even though creation itself performs no
execution. Private reads require `require_local_workspace_access`.

The canonical pipeline definition is `sec_10k_ingestion`, deliberately
separate from the serving `RAGPipeline`. There is one registered definition,
one staging profile named `isolated` (the sole isolation mode stated by the
plan), and registered input IDs are ticker symbols from `configs.tickers.TICKERS`.
The post-download document identity remains the existing
`ticker:accession_number`; it is not conflated with a ticker input, job ID,
step ID, or request identity. The request carries only a non-empty, unique list
of registered ticker IDs and the required `isolated` staging profile. It has no
client-supplied pipeline type, arbitrary stage subset, filesystem path,
document body, model override, or execution option because none is specified
by API-007.

The deterministic durable step order comes from the real ingestion scripts
and the master plan's required table enrichment before embedding/indexing:
`download_filings` (SEC acquisition plus section extraction),
`chunk_filings`, `add_table_chunks`, `embed_chunks`, `index_chunks`. These are
build stages, not the serving query's retrieval/fusion/reranking/generation
stages. The current scripts target canonical `data/` locations, so API-007
will not import or invoke them. The future isolated worker adapter is not
implemented here. Staging persists the safe request through DATA-004, creates
one `pipeline` job with job type `sec_10k_ingestion`, state `queued`, and all
five steps `pending`; it reports no result, artifact, count, percentage, or
progress until such facts exist. Initial artifact references are empty.

The master says job creation is idempotent but defines no HTTP idempotency
header or request field, and the task explicitly forbids inventing one. Exact
canonical request content (definition, profile, configured input order, and
server-computed configuration fingerprint) will therefore supply the internal
DATA-004 idempotency identity: replaying the same request returns the same
durable job; a different valid request has a different request identity. No
raw request key is received or stored. Configuration fingerprinting covers the
registered pipeline/stage order and configured embedding identity/revision;
no environment dump or credential enters the job. The durable job ID is the
run resource ID, step IDs are the persisted DATA-004 step IDs, and the
idempotency digest is not exposed as any of those identities.

Run list responses use the master `Page<T>` shape (`items`, `total`, `page`,
`page_size`) and bounded status/page filters. Detail is an explicit allowlist
projection of the durable job, steps, artifact references, progress, and
sanitized failure fields; it does not expose raw JSON, arbitrary result data,
paths, or settings. Unknown/unregistered input and unknown run IDs return 404;
invalid request fields return 422; stale revision, idempotency, or state
conflicts return 409. Cancellation uses the master revision-precondition rule
via `If-Match`; queued cancellation becomes cancelled immediately, while an
already-running job reports `cancelling` until acknowledged. Events replay in
per-job sequence after the sequence conveyed in `Last-Event-ID`, then close so
the client can reconnect and resume from persisted DATA-004 history.

Ordinary definition/read/staging operations invoke no ingestion script, SEC,
Groq, embedding, reranker, Qdrant, filesystem acquisition, or canonical index
mutation. Public mode returns the existing local-workspace 404 before storage
construction; local reads use API-001 bearer/Host/Origin/loopback checks; the J
routes also fail when execution is disabled. No database migration is
required: DATA-004 v4 contains every initial job, step, event, payload, revision
and cancellation field needed. UI-010/frontend files are out of scope.

The planned implementation files were the typed pipeline service and models,
`src/api/routers/pipeline.py`, minimal app wiring, exact route-contract
inventory, hermetic tests, README, PROJECT_STATE, and this checkpoint. The
six-route, stage-only, privacy, persistence, access, and full-backend gates are
recorded in API-007-B..F. The master graph names `UI-010 — Pipeline` as the
expected successor; it is re-verified at closure and is not started here.

### API-007-B — Typed staging domain and DATA-004 projection

Status: COMPLETE. The preserved drafts are now the typed provider-free
`sec_10k_ingestion` service. Requests are strict and allow only a non-empty list
of configured ticker IDs plus `staging_profile=isolated`; duplicate IDs are
422 and an unknown but syntactically valid ticker is 404. Input validation is
available as a pure function, so the HTTP handler can reject invalid requests
before it constructs the private job repository.

The service computes a SHA-256 configuration fingerprint from the registered
pipeline revision, fixed stage order, table-enrichment ordering, and configured
embedding identity/revision. It uses canonical request content plus that
fingerprint as DATA-004's internal idempotency key; no client header, request
key, or raw key storage was added. Creation persists a `pipeline` namespace,
`sec_10k_ingestion` job in `queued` state with the five real ordered ingestion
steps pending and no result, progress, or artifact references. Replays return
the same DATA-004 job; a distinct request or configuration binding yields a
distinct run identity.

Run and event responses are explicit typed allowlists. Run projection checks
the namespace, job type, payload shape, and exact ordered stage names, and
turns unsafe/malformed persisted data into a safe workspace-unavailable
response rather than a client-validation error. Arbitrary payload/result data,
settings, absolute paths, and credentials are not projected.

### API-007-C — Routes, access classes, and transport

Status: COMPLETE. Six routes are registered after the API-006 registries and
before evaluation routes, in master-plan order: `GET /pipeline` (P),
`GET /pipeline/runs` (L), `POST /pipeline/runs` (J),
`GET /pipeline/runs/{run_id}` (L), `POST /pipeline/runs/{run_id}/cancel` (J),
and `GET /pipeline/runs/{run_id}/events` (L). The application-owned service
factory opens/migrates DATA-004 only after the protected route's dependency
has granted access. Definition reads remain static and provider-free.

Job state filters use DATA-004's typed state vocabulary, history is bounded and
uses the master `Page<T>` shape, run resources expose a quoted numeric `ETag`,
and cancellation requires the current revision in `If-Match`. Stale revisions
map to 409; queued cancellation immediately becomes cancelled, while running
cancellation truthfully remains cancelling. Event responses are finite,
ordered SSE batches capped at 100 records; each frame uses the per-run numeric
sequence as its SSE ID, and `Last-Event-ID` resumes strictly after that
sequence. `If-Match` and `Last-Event-ID` are explicitly allowed by CORS and
`ETag` is exposed to browser clients; the origin and method policies are
otherwise unchanged.

### API-007-D — Isolation and runtime boundary

Status: COMPLETE. The definition route requires only the public/provider-free
grant; history/detail/events require API-001 local workspace access; create
and cancel require local execution capability. The new factory remains lazy,
and tests prove public mode returns 404 and disabled execution fails before
private database construction or mutation. API-001 host-port, loopback,
Origin, bearer-token, and forwarding-header protections are reused without
weakening their boundary.

No ingestion script is imported or called. No SEC request, file acquisition,
embedding, reranking, Qdrant operation, canonical corpus/index write, worker,
coordinator, scheduler, retry, or promotion path was added. DATA-004 v4 is
sufficient; there is no migration. Frontend/UI-010, a browser-held credential
owner, and evaluation work remain outside this task.

### API-007-E — Contract and regression validation

Status: COMPLETE. The focused API-007 plus DATA-004/API-001/API-006/access
regression group passes `117/117` with one existing ReportLab warning. This
includes strict request validation before repository construction, duplicate
request reuse and an eight-contender same-request race, configured-fingerprint
binding, allowlisted run projection, local/public/execution access, the full
create/list/detail/cancel/reopen lifecycle, stale revision conflicts, both
queued and running cancellation states, numeric SSE resume, the 100-event
response bound, CORS preflight for `If-Match`/`Last-Event-ID`, and exposed
`ETag`.

The full hermetic backend suite passes `1100/1100` with `188` warnings, matching
the existing full-suite warning count. Python compile checks pass. The route
contract and runtime inventory report exactly `69` application routes, of
which the six new Pipeline routes match the master-plan order. `git diff
--check` passes. Ruff is unavailable in the repository environment, so no Ruff
result is claimed. No provider/network operation, UI/frontend test, canonical
data write, or new migration was run or introduced.

### API-007-F — Audit and closure

Status: COMPLETE. The implementation and README are commit `c9735f5`
(`feat(api): expose isolated pipeline staging`). The final implementation
staging was limited to the README, API service/models/router/app, route
inventory, and focused tests; the checkpoint and PROJECT_STATE closure are
separately recorded. No frontend file, canonical `data/` artifact, migration,
worker/coordinator, generated database, cache, report, screenshot, or local
runtime output is included. The same 12 unrelated excluded artifact/diagnostic
entries remain untracked and preserved; nothing from them was staged.

The master dependency/priority graph confirms `UI-010 — Pipeline` as the exact
next product task after API-007; UI-010, auth-owner work, and EVAL were not
started. The memory-only local connection/token owner remains staged
architecture and is not a separate predecessor row in the master graph; it
must be handled or explicitly scoped at the UI-010 boundary before browser
local-workspace access can be claimed. API-007 is complete and stops here.

## UI-010 — Pipeline workspace

### UI-010-A — Contract, ownership, and visual plan

Status: RECORDED BEFORE IMPLEMENTATION. This continuation starts from
`3eecebd` (`docs(api): close API-007 pipeline staging`) with a clean tracked
worktree; the 12 pre-existing untracked diagnostic/reference entries remain
user-owned and are out of scope. UI-010 is the next priority-graph task after
API-007. EVAL-001 is its successor and is not in scope here.

**Product and ownership boundary.** Replace the current serving-corpus snapshot
in `frontend/src/components/PipelineConsole.tsx` with the provider-free staged
ingestion workspace. Keep query/retrieval diagnostics in
`PipelineExecution.tsx` untouched. The visible workflow is the API-defined
`sec_10k_ingestion` pipeline, not the serving `RAGPipeline`. Stage requests
only create an isolated `queued` DATA-004 record. The browser must never claim
that a worker ran, that stages completed, or that staged output was promoted.
No worker, provider call, canonical corpus write, script invocation, new
persistence, migration, schedule, retry, or promotion control is authorized.

**API contract.** Implement only API-007's six routes and access classes:
public anonymous `GET /pipeline`; private `GET /pipeline/runs`;
execution-gated `POST /pipeline/runs`; private `GET
/pipeline/runs/{run_id}`; execution-gated revision-conditional `POST
/pipeline/runs/{run_id}/cancel` (`If-Match`); and private ordered finite SSE
`GET /pipeline/runs/{run_id}/events` (`Last-Event-ID`). Use the exact response
DTOs and registered input IDs/staging profiles from the API. Render the five
ordered steps exactly: `download_filings`, `chunk_filings`,
`add_table_chunks`, `embed_chunks`, `index_chunks`. The screenshot's sixth
`Validate` node and all sample run identities, metrics, durations, users,
alerts, and completion claims are reference-only, not product data. Progress
remains unknown unless the server provides it; stage creation starts with five
pending steps and no artifacts.

**Credential ownership.** UI-010 owns the missing app-level local-workspace
session owner. Keep a single bearer only in React/app memory, acquire it only
after explicit entry and successful authenticated `GET
/system/configuration-status`, clear it on Disconnect/unmount/reload, and
never use storage, URL, logs, analytics, or build-time configuration. The
credential entry is password-masked and reset after connect/failure. Add
Authorization only to explicitly private Pipeline requests; never attach it
to `GET /pipeline` or unrelated public API calls. Distinguish 401 (token
rejected), 403 (host/origin or execution access denied), 404 (capability/public
mode or unknown run), 409 (stale state/revision), 422 (request refused), and
network/503 unavailable. An invalid credential must not be described as an
empty history. Do not weaken API-001 checks or attempt to exchange a token
with a non-loopback/private service implicitly.

**Visual receipt and component plan.** Authoritative visual input is
`docs/ui-references/pipeline-ui-reference-dark-v1.png` (1586×992). Measured
landmarks: shared app bar y=0–59; navigation rail x=0–207; content begins near
x=223; Pipeline title/actions occupy y≈72–132; four reference metric cards
occupy y≈148–243; flow panel y≈259–557; run history y≈573–978; detail rail
x≈1227–1574 from y≈73. Preserve the reference's dark navy/blue surfaces,
compact aligned cards, ordered connected stage nodes, dense but readable run
history, and persistent selected-run detail at wide desktop. Keep the existing
global V5 app shell/header/navigation; don't recreate the screenshot's
fictional account, storage/upgrade controls, schedule/templates, unsupported
tabs or row actions. Use four summary cards only for server-backed run totals
and definition facts; mark unavailable values as unavailable instead of
inventing success rates, throughput, processing counts, timing, or readiness.
The page component owns list/detail/stream and transient selection UI; the
canonical `/pipeline/runs/:runId` URL owns run selection. A shared
`LocalWorkspaceSessionProvider` mounted above `App` owns the ephemeral token;
`PipelineConsole` owns its explicit connect/disconnect form and obtains the
ephemeral token through the shared owner for typed API calls. Keep Pipeline
copy English/Vietnamese.

**States and interactions.** Cover public definition loading/unavailable,
private disconnected/connecting/unauthorized/denied, list loading/empty/error,
unknown deep-linked run, selected queued/running/cancelling/cancelled/
succeeded/failed/interrupted states, unknown/partial progress, staging pending
/accepted/refused, cancel pending/accepted/conflict, SSE replay/connected
finite-close/reconnecting/error, and retry. Use server detail as state truth;
refresh it after each bounded event batch. Resume from the highest valid
sequence. Abort/clean up detail and event fetches on route, selected ID, token,
and unmount changes; guard responses with a selection-generation epoch so
A→B→A cannot let stale A#1 overwrite A#2. Don't convert a clean finite SSE
close into job failure. Cancellation sends the current run revision, disables
duplicate requests while pending, preserves 409 as a conflict, and shows
`cancelling` separately from `cancelled`.

**Responsive and accessibility plan.** Keep the reference's two-column
main/detail layout at wide desktop; at compact desktop stack the header and
metrics, reduce stage-card width with safe wrapping/scrolling inside the stage
flow only, and give details a bounded collapsible/drawer surface; on mobile use
one column with details following the selected run and no page-level horizontal
overflow. Preserve readable input/table labels, keyboard-reachable controls,
visible focus, 44px interactive targets, semantic status text/icons, and
reduced-motion behavior. Keep the table scroll region local, not the page.
Connect dialog/input owns focus restoration; route changes announce selected
run state without stealing focus.

**Persistence and test plan.** The only intended persistence is the already
existing backend durable DATA-004 staged job. The browser token, selected input
draft, SSE cursor, and view/session state are not persisted. Add hermetic unit
tests for memory-only auth and redaction, public/private header isolation,
exact route/query/body/If-Match/SSE cursor behavior, event framing and
reconnect, all server state/error mappings, duplicate-stage prevention,
revision conflicts, route deep links/back-forward, cleanup and A→B→A stale
response rejection. Add Playwright fixtures for direct `/pipeline` and
`/pipeline/runs/:id`, public/unavailable/authenticated/stage/cancel/reconnect
flows, memory reset on reload, keyboard semantics, and wide/compact/tablet/
mobile/no-overflow visual checks in Chromium and Firefox. Gate in order:
focused API/auth tests, focused component tests, TypeScript, full Vitest,
production build, focused Chromium and Firefox, then route/shell regression and
visual comparison. Keep browser artifacts outside Git.

### UI-010-B — Shared local session and typed API

Status: COMPLETE. `LocalWorkspaceSessionProvider` is mounted above `App` and
owns the only runtime credential. Its `tokenRef` is not placed in React state,
context values, browser storage, URLs, or logs; consumers receive a getter.
Connect verifies a candidate with protected `GET /system/configuration-status`
before accepting it, and Disconnect/invalidation/reload clear it. The typed
Pipeline client covers the public definition, private list/detail, exact stage
and revision-cancel POSTs, and bounded ordered SSE with numeric cursor resume.
The public request never carries Authorization. Focused client 5/5 and session
3/3 tests passed.

### UI-010-C — Page and staging

Status: COMPLETE. The former serving snapshot is replaced by the API-007
five-stage definition, server-backed metric cards, durable run list with
filter/pagination, canonical `/pipeline/runs/:runId` detail, and an explicit
isolated staging dialog. Submission is ref-guarded against double click; only
the returned server ID/revision/state enters the UI. A queued run shows five
pending server steps and unknown progress as “Not reported.” No provider,
worker, corpus, promotion, or artifact behavior was introduced.

### UI-010-D — Lifecycle, SSE, cancellation, races

Status: COMPLETE. A selection-generation epoch and AbortControllers own list,
detail, event, stage, and cancel lifetimes. The selected run has one finite
SSE owner; batches are ordered and resume from the last accepted sequence.
Server detail is reconciled after events. Old A and old A#1 after A→B→A#2
cannot repaint the current selection. Finite close is not completion. Cancel
sends the current quoted revision and paints the API response: a running run
remains `cancelling` until backend acknowledgement; queued cancellation may
be immediately `cancelled`. A 409 is shown and refreshed, never force-retried.
Focused Pipeline component tests passed 10/10.

### UI-010-E — Visual, responsive, accessibility

Status: COMPLETE. The 1586×992 captured populated receipt was compared with
`pipeline-ui-reference-dark-v1.png`. The reference has a 207px sidebar, 59px
topbar, metric cards y≈148–243, flow y≈259–557, history y≈574+, and right
detail x≈1227/y≈73. The current shared shell uses a 184px sidebar; after a
visual correction, the UI-010 detail begins at y≈72, with metrics y≈143–238,
flow y≈252–575 and history y≈591. The smaller horizontal offset and stage
height derive from the existing shell and truthful five-node copy. The sixth
reference node, fake timings/metrics, schedule, and execution controls were
not copied. Captures cover initial, queued, selected, cancelling, unavailable,
1586×992, 1440×900, 1280×856, 1024×768, 768×900, 390×844, and 1440×700;
the mobile selected detail was separately scrolled into view. Body/root
horizontal overflow is zero in the tested widths. Scoped WCAG 2/2.1 A/AA
axe scan reports zero Pipeline violations; controls retain text state, focus,
44px targets, and reduced-motion support. Receipts remain ignored under
`frontend/test-results/` and are not committed.

### UI-010-F — Unit, type, build

Status: COMPLETE. `bun run lint` (`tsc --noEmit`) passed. `bun run test`
passed 80 files/539 tests, up from the UI-009 baseline 77/521. `bun run build`
passed with only the existing >500kB chunk advisory. One parallelized Vitest
attempt passed all 539 assertions but exited with two unrelated
`DocumentExplorerPanel` teardown timer errors while browser workers also ran;
the isolated rerun exited 0 with no uncaught errors.

### UI-010-G — Browser and route/reference gates

Status: COMPLETE. Dedicated hermetic UI-010 Playwright passed Chromium 8/8 and
Firefox 8/8 with 2 workers across the final combined run. Coverage includes public
read and private gate, public unavailable mode, connect/reload credential
loss, execution-disabled read-only mode, exactly-one queued stage despite two rapid clicks, five pending steps,
selected details, ordered SSE/reconnect, stale old-run event isolation,
revision conflict, requested vs acknowledged cancellation, canonical routing,
Back/Forward, visual widths, zero overflow, and Pipeline axe. Shared route and
reference Chromium regression passed 18/18 with 2 workers after the old
Pipeline snapshot fixture was updated to the API-007 contract.

### UI-010-H — Scope, audit, and closure

Status: COMPLETE. Implementation commit `c1318cd` (`feat(ui): build truthful
pipeline staging workspace`); this documentation closure follows in the next
commit. No backend code, `data/` contents, secrets, or provider execution changed. A
source audit found no localStorage, sessionStorage, IndexedDB, cookie, URL,
or console credential write path in the UI-010 owner, client, or page. Test
tokens are synthetic; generated screenshots/traces, `dist`, diagnostics, and
the 12 pre-existing unrelated untracked paths remain unstaged. Public mode
never reports a fabricated empty private history. Known limitation: API-007
only stages and replays durable records; it does not supply an execution
worker, real progress/timings/artifacts, or promotion. The inherited shared
header has a borderline contrast chip outside the Pipeline axe scope; no
Pipeline-specific violation remains.

### Exact Next Action

The actual master-plan priority row after `UI-010 — Pipeline` is `EVAL-001 —
Metrics/native protocol` (evaluation services). Do not begin EVAL-001 during
UI-010 closure.

## EVAL-001 — Native metrics/protocol

### EVAL-001-A — Resolved contract and bounded architecture map

Status: RECORDED BEFORE IMPLEMENTATION. Recovery found HEAD `1460986`
(`docs(ui): close UI-010 pipeline workspace`) and a clean tracked tree;
the same 12 unrelated untracked paths remain user-owned. The master-plan
dependency/priority graph assigns EVAL-001 after UI-010, with EVAL-002 next.
EVAL-001 does not own comparison, trends, failures, evaluation jobs/workers,
the Evaluation UI, optional Ragas, or provider execution.

**Canonical metric registry.** Section 12 of the master plan names exactly
`native.faithfulness`, `native.answer_relevancy`, `native.context_precision`,
`native.citation_index_validity`, `native.keyword_recall_proxy`, and
`native.fallback_correctness`. The first three retain the existing
`RAGEvaluator` judge prompt/parser semantics: grounded-claim fraction,
answer-to-question/ground-truth relevance, and fraction of useful retrieved
chunks. They are *recorded* precomputed judge scores, never generated by the
provider-free protocol. Citation index validity is the existing fraction of
`Source N` references whose numbers are in range; it is **not** claim support.
Keyword recall proxy is the fraction of explicit required keywords found in
the exact rendered context (whitespace-insensitive matching), **not** Recall@K.
Fallback correctness is the existing bool comparison of the answer's fallback
phrase against the test case's `expects_fallback`; its aggregate is a success
rate. All six are higher-is-better and have valid computed values in `[0,1]`;
boolean per-case fallback remains bool. Stable metric IDs are separate from
display labels. EVAL-001 introduces explicit semantic metric version `1` for
these unchanged definitions, and a distinct native protocol schema version
`1`; any future semantic change requires a metric-version bump.

**Inputs and outputs.** One canonical case input carries a stable case ID,
the answer if generation completed, the exact rendered evidence used for
generation/metrics/judging, explicit required keywords/fallback expectation
where present, and precomputed judge scores only when their complete judge
binding is supplied. Missing generation/evidence/judge prerequisites produce
typed unavailable results; an absent citation or absent keyword requirement
is not applicable, never numeric zero. A report contains the six definitions,
per-case results, six aggregates, complete denominators (`computed`,
`unavailable`, `not_applicable`, total), dataset/model/retrieval/context/judge
bindings, deterministic case/metric ordering, protocol version, and a digest
over canonical JSON. Empty case sets are rejected rather than published as
zero. Aggregate means use only computed cases and existing final four-decimal
reporting convention without per-case early rounding; no mixed-binding or
incomplete aggregate can be called official.

**Dataset and compatibility.** API-006's `evaluation-test-set` identity,
`evaluation-test-set-v1` version, and SHA-256 revision over the ordered full
`TestCase` dataclass payload are canonical. EVAL-001 will extract/reuse that
exact revision helper rather than minting another dataset revision. Existing
Phase 2 checkpoint/result schemas and public report schema v1 are historical
formats; they are not silently upgraded, renamed, or accepted as native
protocol v1. The new parser fails closed on unknown versions/corrupt digest.
Existing report routes and official N=30 metrics remain unchanged. A later
publication/comparison task must explicitly adapt eligible native reports;
this task provides the typed deterministic domain contract it can consume.

**Safety and planned files.** Add a small provider-free native metric/report
domain module and focused hand-computable tests; share the API-006 dataset
revision function without altering its bytes; add only an EVAL-001 metric
definition route if the exact public plan contract warrants it after tests.
Use `src/retrieval/canonical_json.py` for JSON bytes, strict finite/ID/version
validation, bounded metadata, and no path/secret fields. No data artifacts,
provider calls, index changes, frontend code, execution jobs, or Ragas.

### EVAL-001-B — Metric definitions and identity

Status: COMPLETE. `src/evaluation/native_protocol.py` defines the six exact
master-plan `native.*` IDs in stable order, each at explicit semantic version
`1`. Definitions expose label, existing meaning, ratio/boolean value kind,
mean/success-rate aggregate kind, higher-is-better direction, `[0,1]` range,
precomputed-judge or deterministic source, and required inputs. Duplicate or
malformed IDs/versions are rejected. Public provider-free `GET
/evaluation/metrics` exposes definitions, protocol version, and capabilities
through an explicit response model. The route contract is updated in place;
no execution endpoint is added.

### EVAL-001-C — Per-case and aggregate truth

Status: COMPLETE. Case computation reuses the existing native citation-index,
keyword-proxy, and fallback functions on the exact rendered evidence. The
three judge metrics are accepted only as bound precomputed scores, never
computed through a provider call in this layer. A completed generation and
judge result must carry their per-case bindings and matching rendered-context
SHA-256 values. Computed zero/false, unavailable, and not-applicable are
separate typed states with reason codes. Aggregates count computed,
unavailable, and not-applicable cases explicitly, exclude noncomputed cases
from the denominator, use stable `math.fsum` over sorted unrounded values, and
round only the final mean/success rate to four decimals. Empty sets and
duplicate case IDs fail closed. Provider-free preflight reports bound versus
unjudged eligible cases and `core_provider_calls=0`; it does not price or
execute future judging.

### EVAL-001-D — Report/provenance/compatibility

Status: COMPLETE. The private `native-evaluation` report schema is version 1.
It separates registry definitions, per-case results, aggregates, report
status, and binding. Binding includes native engine/version; API-006 dataset
ID/version/revision; generator model/prompt/binding; retrieval/config,
embedding, reranker, and context fingerprints; optional judge
model/prompt/binding. Case output retains only an ID and context hash, not
question/answer/truth/evidence. Identical logical inputs have sorted case
and metric order and the same canonical JSON bytes/digest. Parse verifies
schema, metric meanings/versions, finite values, reason/status pairs,
denominators/aggregates, and digest; malformed or unknown future/legacy
formats fail closed. API-006 now imports one extracted revision helper whose
canonical JSON bytes match its previous ordered-full-`TestCase` algorithm.
The historical Phase 2 result/checkpoint and public-report-v1 parsers/routes
remain untouched; no old score is silently reinterpreted or republished.

### EVAL-001-E — Focused/regression gates and security

Status: COMPLETE. Small hand-computable fixtures cover each deterministic
metric, exact judge-score recording, zero versus unavailable, missing truth,
not-applicable cases, denominator and no-early-rounding behavior, reorder
invariance, dataset binding, per-case evidence/binding drift, unsupported
versions, corrupt/double-key/non-finite JSON, bad IDs and provenance,
oversized/empty/duplicate inputs, and provider-free operation. The final
focused native/evaluation/registry/API-005/route group passed 151/151 with
one pre-existing warning. No Ragas dependency,
worker, job runner, UI file, data artifact, provider call, or index mutation
was introduced. The public legacy evaluation regression remains green.

### EVAL-001-F — Full validation, audit, and closure

Status: COMPLETE. Implementation commit `a20b77c` (`feat(eval): define native
metric report protocol`); this checkpoint and the protocol/README/project-state
documentation belong to the following closure commit. The
final native protocol/API group passed 27/27. The final hermetic backend
suite passed **1127/1127, zero failures, 188 warnings**, versus the stated
pre-EVAL-001 baseline of 1100/1100 with 188 warnings. Python compile/import
passed. The FastAPI application has 70 routes (69 before EVAL-001), with only
the planned public `GET /evaluation/metrics` added. The 151-test focused
group covers EVAL-001, legacy evaluation/public reports, API-006 dataset
registry, API-005 retrieval inspection semantics, and route contracts.
`git diff --check` passed before staging and `git diff --cached --check`
passed for the implementation commit; the documentation closure is checked
separately below.

The audit found no change to frontend, `requirements.txt`, `data/`, provider
configuration, retrieval/index implementation, jobs, or legacy public report
formats. The new domain report stores hashes and allowlisted identifiers,
not question/answer/truth/evidence content, secrets, arbitrary environment
data, or private paths. Synthetic test IDs/model names are not credentials.
No runtime evaluation outputs, model caches, scanner state, screenshots, or
generated test reports are intended for commits. The same 12 pre-existing
untracked paths remain outside task scope. Known limitation: EVAL-001 defines
and validates native reports but intentionally does not migrate historical
Phase 2/public-v1 reports or schedule/price future judging. A complete native
report is not automatically an admitted official benchmark. No new
deterministic regression or warning growth was observed.

Documentation-closure staged diff and committed file list were audited for
EVAL-001 scope; `git diff --cached --check` passed. No runtime artifact,
credential, local dataset, cache, screenshot, or unrelated untracked file was
staged.

### Exact Next Action

The actual master-plan dependency/priority row after EVAL-001 is
`EVAL-002 — Compare/trends/failures`. Do not begin EVAL-002, EVAL-003,
UI-011, or optional EVAL-004 during this closure.

## EVAL-002 — Compare, trends, and failures

### EVAL-002-A — Resolved contract before implementation

Status: RECORDED BEFORE IMPLEMENTATION. Recovery found HEAD `716bb84`, a
clean tracked tree, and the same 12 unrelated untracked paths. The master
plan assigns EVAL-002 to **public reports**, after EVAL-001 and before
EVAL-003. Its exact route rows are `GET /evaluation/runs/{id}/results`,
`POST /evaluation/compare`, `GET /evaluation/metrics/trends`, and
`GET /evaluation/failures`; all are public reads, even the compare POST. Existing
public list/detail and metric-definition routes remain. EVAL-003 owns jobs,
budgets, cancellation, and execution; UI-011 and Ragas remain out of scope.

**Source and version boundary.** The existing fixed, allowlisted
`data/public_evaluations` directory currently does not exist. Its `.json`
files are historical public-report-v1, with a different metric schema and
potential case text. They cannot be interpreted as native-evaluation/v1.
EVAL-002 will read explicitly placed, immutable `*.native.json` publication
envelopes from that same directory, never crawl `data/` or create a second
database. An envelope supplies a timezone-aware `published_at` order key and
one complete, digest-validated EVAL-001 report; EVAL-002 provides no
publication writer or automatic promotion. Legacy list/detail behavior is
preserved, while native list/detail and new analytics remain explicitly
version-discriminated. Missing source yields empty lists, not invented runs.
Invalid selected artifacts, unsupported versions, or digest mismatches fail
closed; source report payloads are never changed.

**Eligibility and comparison.** Baseline and candidate are explicit IDs;
`delta = candidate - baseline` for computed higher-is-better aggregate or
paired-case values. No relative percent, significance, winner, or overall
score is produced. Metric identity/version, dataset ID/version/revision,
case-ID universe, *computed case coverage for each metric*, and
evidence-context binding must match for numeric aggregate deltas. Judge metrics
additionally require the same judge model and prompt definition; opaque
per-run generation/judge/retrieval bindings
may differ because candidate changes are the point, but both sides retain
their full provenance and denominators. A changed case universe is shown
through baseline-only/candidate-only pairs and an ineligible aggregate delta,
not a fabricated paired score. Unavailable and not-applicable stay null;
incomplete reports are explicitly non-official even where individual
computed values remain analytically comparable. The master plan does not
define a statistical threshold or cross-metric weighting.

**Trends and failures.** Trends use only published native envelopes, ordered
by `published_at`, run ID, then digest; each stored report contributes at
most one point. Compatibility groups include the dataset/version/revision,
case universe, computed metric coverage, context binding, metric ID/version,
and (for judge metrics) judge model/prompt. No interpolation, smoothing,
forecast, or implied time
from the native report itself. Failures are limited to directly observable
native facts: computed false fallback expectation, computed citation-index
fraction below 1, computed required-keyword fraction below 1, and a separate
unavailable-prerequisite finding. There is no judge-score quality threshold
or hallucination label. Detail exposes only stored safe case IDs/hashes,
metric results, and bindings—never hidden case text. Results, findings, and
trend points use bounded deterministic pagination; unknown filters/sorts
are rejected. These conservative pagination/category/group rules fill gaps
not numerically fixed by the master-plan rows and are documented as EVAL-002
protocol choices, not pre-existing benchmark semantics.

### EVAL-002-B — Comparison and compatibility

Status: IMPLEMENTED, focused tests passing. `src/evaluation/native_analysis.py`
consumes only digest-validated `NativeReport` values and EVAL-001 definitions;
it defines no new metrics or thresholds. Explicit baseline/candidate
comparison uses `candidate_minus_baseline` absolute deltas. It preserves both
original aggregate records and denominators, pairs cases by ID, shows
baseline-only/candidate-only cases, and exposes null deltas with stable
reasons for unavailable, not-applicable, and incompatible values. Dataset
identity/revision or context-binding mismatch is a conflict. Metric/judge
definition, case-universe, or per-metric computed-coverage drift suppresses
numeric aggregate deltas. Generator/retrieval and opaque judge run bindings
remain visible, not falsely required equal. A complete-comparison
eligibility flag is distinct from official promotion.

### EVAL-002-C — Failures and case privacy

Status: IMPLEMENTED, focused tests passing. Failure categories are only
fallback expectation mismatch, invalid citation index, missing explicit
required keyword, and separately `unavailable_prerequisite`. No arbitrary
judge-score cutoff, hallucination label, claim-support assertion, Recall@K,
or model-failure label for missing prerequisites was introduced. Findings
sort by category/case/metric and contain only EVAL-001 case IDs, context
hashes, metric IDs/statuses/values/reasons. Case comparison/results also
remain text-free. Computed zero and false survive analysis and API schema
validation. Missing cases are never paired by position.

### EVAL-002-D — Published history and trends

Status: IMPLEMENTED, focused tests passing. `src/evaluation/native_publication.py`
recognizes only bounded `*.native.json` envelopes in the existing configured
public directory. It adds timezone-aware publication ordering metadata to a
complete EVAL-001 report, validates every digest and filename, rejects
unsupported/corrupt/ambiguous input, and never writes or publishes artifacts.
The historical public-report-v1 reader explicitly skips native filenames.
Trend grouping fingerprints dataset, case universe, computed coverage,
context binding, metric identity/version, and judge definition where needed.
Points order by publication time/run ID/digest; one run yields one point,
and an absent directory yields no points. No mtime ordering, interpolation,
smoothing, forecast, or fabricated history.

### EVAL-002-E — Public API, bounds, and provider-free gates

Status: IMPLEMENTED, focused tests passing. The four master-plan public
analytics routes have explicit Pydantic response models and thin handlers.
Existing list/detail can expose version-discriminated native publications
while preserving legacy report payloads; native detail omits the case array
and the dedicated results route pages it. Duplicate native/legacy run IDs
fail closed. Results, case comparisons, findings, and trend points paginate
with 50 default/100 maximum. Report discovery is capped at 1,000 files and
50 MB; each file is bounded near EVAL-001's 2 MB report limit. Category,
metric, page, date-range, and binding-group filters validate explicitly.
Selected corrupt reports yield conflict, unknown reports not-found, and
invalid request parameters validation errors. Tests prove no Authorization
dependency, no raw case text in responses, read-only source bytes, and no
network/provider call in the domain. The API adds no evaluation execution,
job coordinator, worker, frontend code, or Ragas.

### EVAL-002-F — Validation and closure

Status: COMPLETE pending the documentation closure commit. Implementation is
`78b726e` (`feat(eval): add native report comparison and analysis`) plus
`40dd144` (`fix(eval): validate analytics sort and query selectors`); this
checkpoint, protocol guide, README, and project-state receipt form the next
scoped documentation commit. The final EVAL-002/EVAL-001/public-report/API-005/
route focus group passed **84/84**, with one existing dependency warning.
The final hermetic backend suite passed **1146/1146, zero failures, 188
warnings**, versus the EVAL-001 baseline 1127/1127 and 188 warnings. An
earlier full run passed 1144/1144 before two final source/trend edge tests;
the final count supersedes it. The full 1146-test suite was rerun after the
sort/query validation change. Python compile/import passed, and the route
inventory is **74** versus 70 before EVAL-002; only the four planned public
read/analysis routes were added. Route name, method, response model, access,
order, and collision regressions passed. `git diff --check` and the staged
implementation diff check passed.

The file audit found no frontend, dependency, DATA-004 job, execution,
provider, retrieval, index, `data/`, Ragas, or legacy public-report schema
change. The code commit includes only the domain/publication reader,
evaluation API models/router, legacy-reader filename exclusion, and tests.
Synthetic tests use temporary publications and keep source bytes unchanged;
no real native report is currently published. No runtime evaluation result,
secret, hidden dataset dump, question/answer/evidence text, absolute machine
path, log, scanner state, cache, or screenshot was staged. The same 12
pre-existing unrelated untracked entries remain user-owned. The new
publication envelope's timestamp is explicit metadata, not a cryptographic
claim about execution time; the native report digest remains unchanged.
Legacy public-report-v1 has no adapter into native analytics. No new
deterministic regression or warning growth was observed. The documentation
closure stages exactly `PROJECT_STATE.md`, `README.md`, this checkpoint, and
`docs/EVALUATION_ANALYTICS_PROTOCOL.md`; its staged diff check passed. The
final tracked-tree audit is reported in the handoff after that commit.

### EVAL-003-A — Contract and bounded execution choices

Status: CONTRACT RECORDED before implementation; closure receipts follow.
The master plan specifies
exactly six private routes: `GET/POST /evaluation/jobs`,
`GET /evaluation/jobs/{id}`, `GET /evaluation/jobs/{id}/results`,
`POST /evaluation/jobs/{id}/cancel`, and `GET /evaluation/jobs/{id}/events`.
Reads are L; creation/cancellation are J. Creation is the only execution
trigger; no start/resume endpoint is planned. DATA-004 owns job identity,
revisions, events, optimistic claims, cancellation, and recovery. The
evaluation runner owns only frozen-case work and private result/provenance.

The plan does not prescribe a numeric budget, mode vocabulary, worker pool,
artifact-registration API, or step names. EVAL-003 adopts a bounded
explicit native contract: a bounded registered Phase 1 retrieval artifact,
the six EVAL-001 metric identities/versions, native engine v1, one provider-
backed generation/judge mode, and an integer budget of provider attempt
slots. A request preflight reserves capacity for a generation
draft, at most one shared answer-completion correction, and one judge call
per frozen case. No automatic transport or case retries are introduced.
Every transport invocation consumes one slot atomically before invocation,
including a reservation whose transport outcome is unknown after a crash.
This is a conservative upper bound on actual transport calls, not a claim
that every consumed slot reached the provider. The exact original
artifact bytes and selected case inputs are frozen under a digest identity;
model, dataset revision, prompt/context/judge/retrieval fingerprints and
budget are persisted without credentials. Execution refuses a changed
runtime binding instead of silently using new definitions. Cases run in
frozen order with stable content-derived IDs. Completed private case results
and consumed attempts survive cancellation/failure/restart.

The durable steps are `execute_cases` and `aggregate_report`; freezing and
preflight finish before the queued job is committed. Progress is committed
cases / frozen case count. Cancellation is observed between attempts/cases;
an in-flight call can finish. A queued cancellation is terminal immediately;
a running cancellation is acknowledged only after the worker stops. The
DATA-004 restart policy marks running/cancelling jobs terminal `interrupted`;
there is no implicit resume or provider replay. Queued jobs remain queued
and are retried only by an explicit equivalent creation request. A provider
call may complete before its result commits, so budget remains consumed and
the result is unknown after a crash; no exactly-once external-call claim.

EVAL-003 produces a private digest-validated EVAL-001 report on complete
success. The master-plan route table has no publication mutation, and EVAL-002
explicitly separates public publication from private execution; therefore
EVAL-003 does not publish into `data/public_evaluations`, make a run official,
or populate trends. Generation uses frozen Phase 1 evidence and shared
Phase 2 prompt/rendering/provider functions, not live retrieval. This is
frozen-evidence parity, **not** full serving-request parity. Later UI-011
consumes the private job and result routes separately from public analytics.

### EVAL-003-B — Frozen plan and validation

Status: IMPLEMENTED. `frozen_job_plan.py` admits only opaque names under the
existing Phase 1 artifact directory, validates schema/self-digest and matching
registered dataset case inputs, and freezes original bytes in private
content-addressed SQLite storage. The job payload binds native protocol/engine,
all six metric versions and definition digest, full API-006 dataset revision,
complete canonical TestCase-derived IDs, ordered case/evidence hashes,
generation/judge models and prompts, retrieval fingerprints, completion
profile, runtime source semantics, and the budget. Sorted finite canonical
serialization supplies its digest; no path/time/secret enters that identity.
Execution reads the frozen case data, never the current dataset. Runtime
semantic drift fails closed. Equivalent creation replays use DATA-004's
hashed idempotency lookup before consulting mutable inputs; conflicting reuse
is a conflict. Metrics are an order-independent complete native set.

### EVAL-003-C — Budget and concurrency

Status: IMPLEMENTED. Unit: `provider_attempt_slot`, not dollars or tokens.
Preflight requires `3 * frozen_case_count <= budget <= 15000`; jobs are capped
at 200 cases/16 MB source bytes to keep DATA-004's snapshot bounded. SQLite
reads the limit and selected case IDs directly from the immutable payload,
then atomically records each reservation before provider invocation. A unique
job/case/phase constraint forbids replay; no consumed reservation is refunded.
Independent jobs may run concurrently, but only one optimistic DATA-004 claim
can own each job. There is no global provider-quota scheduler. Exhaustion is
explicit `budget_exhausted`, never a score or provider-error alias.

### EVAL-003-D — Coordinator, metrics, cancellation

Status: IMPLEMENTED. Creation dispatches a bounded background worker, not a
generic queue. Steps are `execute_cases` and `aggregate_report`. Frozen cases
run in artifact order; generation, completion, local metrics, and judging use
the same rendered evidence. Shared Phase 2 calls disable both SDK/transport
retries, preserve runtime key policy including KEY5-only use, and allow only
one completion correction. EVAL-001 evaluates all local metrics and constructs
the final canonical report without changed definitions/denominators. Zero and
false stay computed. Fixed failure categories distinguish invalid snapshot,
budget, provider, case, report-validation, and infrastructure failures. No
provider error body is persisted. Cancellation stops new reservations; an
already-reserved/in-flight call can finish. Durable valid results remain.
Cancellation/failure terminal revision races are reconciled without replaying
provider work. Progress receipts can lag a case at a crash/cancel boundary;
the results count is authoritative.

### EVAL-003-E — Recovery and publication boundary

Status: IMPLEMENTED. DATA-004 restart recovery marks running/cancelling jobs
terminal `interrupted`, preserving snapshot, attempted slots, cases, and any
already committed valid private report. There is no resume endpoint or
automatic replay. Queued jobs may be redispatched by an equivalent creation
request, which returns the original snapshot even after source changes.
Local workspace startup recovery assumes one serving process. A crash after
provider completion and before result commit leaves an unknown outcome and a
consumed slot; this is not exactly-once external execution. A content-addressed
artifact admitted before a failed job commit may remain unreferenced; no
automatic private artifact deletion/garbage collection was added.

Publication is NOT owned by these six job routes. A complete private EVAL-001
report is validated/digest-checked and inserted atomically in SQLite; no public
file publisher or official promotion is added. EVAL-002 readers/calculations
are unchanged, and normal native trend history remains empty. Frozen Phase 2
evidence parity is explicit, not full live-serving parity.

### EVAL-003-F — API, privacy, regressions

Status: IMPLEMENTED. All six planned routes use typed snapshot/job/case/native
metric schemas and thin service handlers. L reads and J mutations reuse exact
loopback, Host-port, Origin, bearer, and execution gates. Cancellation needs
If-Match; SSE resumes recorded events with Last-Event-ID. Pages and event
batches cap at 100. The private case endpoint alone exposes question/answer/
ground-truth/exact context under L; public analytics never receive them.
DATA-004 credential/path checks also reject escaped credentials and unsafe
private artifact/result fields. This is not a prompt-injection-immunity claim.
No frontend, Ragas, serving corpus/index, evaluation metric, or public-reader
implementation was changed. Schema v5 adds linked private artifact/attempt/
case/report tables to the existing workspace database, not a second job store.

### EVAL-003-G — Validation and closure

Status: COMPLETE. Implementation is `fb85da1` (`feat(eval): add frozen
budgeted native evaluation jobs`); the README/project-state/checkpoint receipt
forms the scoped documentation closure commit reported in the handoff. The
final combined native/job/DATA-004/pipeline/API/access group passed 182/182
with one existing warning; API-006 registry
and shared Phase 2 regressions passed 64/64 with one existing warning. Dedicated
EVAL-003 coverage comprises 22 hermetic tests for freeze/drift/idempotency,
budget/concurrent ownership, cancellation/failure races, native zero/false,
malformed scores, secret/path rejection, aggregation failure, and crashes
after durable case/report commits, multi-case order, and preservation of a
completed case when a later case fails. No live provider calls were made.

The final full hermetic backend passed **1168/1168, zero failures, 188
warnings**, versus 1146/1146 and 188 warnings. Earlier 1157/1165/1166/1167
full runs passed while coverage was being expanded; 1168 is the final count.
Compile/import passed, and the exact APIRoute inventory is **80** versus 74,
with no method/path collisions and the six planned names/models/access
dependencies inspected. `git diff --check` and staged code diff checks passed.
The existing 30-case registered Phase 1 artifact passed a read-only digest/
dataset/privacy/snapshot preflight (11,665-byte snapshot); no provider or data
write was involved. Remote model identity is fixed but its weights are not
provider-revision-pinned. The staged code audit includes 13 intended files,
with no frontend/dependency/data/public-reader/native-protocol change and no
runtime output, database/WAL/SHM, credential, log, trace, screenshot, or cache.
The same 12 unrelated untracked paths remain preserved. The final tracked
tree is checked after the documentation closure commit. Exact next task is
UI-011 by the dependency graph; it is not started.

### Exact Next Action

`UI-011 — Evaluation` (requires UI-002, EVAL-002, EVAL-003). Stop after
EVAL-003 closure; do not implement UI-011 or optional EVAL-004/Ragas here.

## Post-rebuild engineering audit — COMPLETE (2026-09-26)

This separate audit/repair pass started at `8dfdb3f`, with clean tracked source
and 12 preserved unrelated untracked paths. The supplied UI-008/dirty-tree
recovery receipt was historical: API-006 through EVAL-003 and the earlier
clean-checkout source closure are already complete. No roadmap feature was
started. Boundary inspection covered application/access composition, SQLite/
transfer/collections/jobs, catalog/discovery/retrieval/generation/readers,
registries/evaluation, frontend routing/state/persistence/private Pipeline auth,
and test/CI ownership. It is not a per-line or exhaustive security audit.

Verified and repaired:

- AUD-04 / P1: browser preflight rejected evaluation creation's mandatory
  `Idempotency-Key`. Commit `7a3e596` adds only that explicit CORS header; six
  new tests retain forbidden-origin/header/method and authentication boundaries.
- AUD-01 / P1: native results/comparison/failures/trends accepted ambiguous
  legacy/native run IDs that list/detail rejected. Commit `05f87ce` applies
  consistent HTTP 409 rejection to selected reads and history before filtering.
- AUD-02 / P2: filtering the native `complete` status returned 422. The same
  evaluation commit admits it without altering official/legacy/native semantics.
  Four ambiguity cases and one completeness filter regression failed before
  the fix. OpenAPI's original digest is retained after an explicit assertion
  and normalization of the single additive enum value.
- AUD-03 / P2: Collections paging replaced pages under "Show more", had no
  return control or terminal bound, and confused all/Favorites totals. Commit
  `d1519a3` introduces bounded bidirectional paging with active result counts,
  preserves selected identity/epochs/storage, and reconciles a shrinking result
  set. Two unit cases and four production browser cases protect the change.

Final gates: **1179 backend tests passed / 188 existing warnings**; **80 Vitest
files / 541 tests passed**; TypeScript/build/compile/import/diff checks passed;
**80 API routes, no collisions**; focused backend groups **41/41** and **63/63**;
Collections units **25/25**; neighboring Collections browsers **38/38** (19 per
browser). Screenshots at 1440 dark/EN and 390 light/VI were inspected; paired
WCAG-tagged rendered scans, keyboard and overflow checks passed after settled
paint. A preliminary whole-page best-practice scan found an existing h1-to-h3
card-heading warning, left as P3. Initial Vitest session-history timeout passed
isolated and final-full reruns; no timeouts or existing assertions were weakened.
No full browser/reference/zoom, live provider, Docker, or clean-checkout build
was rerun. No canonical artifact, database, secret, cache, trace, log, screenshot,
dependency, ranking/prompt semantics, or official benchmark was staged.

The same 12 unrelated untracked paths remain preserved. Collections token
integration remains explicitly staged by the UI-010 contract; API-001 was not
weakened. Unicode snippet offset/casefold handling and card heading order remain
P3 follow-ups. See [the audit report](ENGINEERING_AUDIT_2026-09-26.md) and the
latest project-state section for evidence and exact validation commands.

### Exact Next Action After Audit

`UI-011 — Evaluation`, under a separate feature request. API-006 is already
complete. No hygiene blocker was reproduced that should precede UI-011; retain
the staged private-auth limitation and schedule the P3 follow-ups separately.

## UI-011-A — Evaluation contract and ownership (2026-09-26)

UI-011 is now in progress, starting at `f3fb42a` with clean tracked/staged
source and the same 12 unrelated untracked paths. The immediately preceding
audit is a completed prerequisite, not a receipt for UI-011. No roadmap work
after Evaluation is authorized here.

### Contract and visual authority

Master-plan sections 9, 10, 12, 14-16 and the task graph define one Evaluation
workspace: definitions, run history/report rail, comparison, trends, failure
analysis, and private frozen job controls. UI-002 already owns `/evaluation`
and `/evaluation/runs/:runId`. A selected publication uses that existing
canonical route. A private canonical job uses the same route with an explicit
`source=job` query discriminator, so job/publication namespaces cannot collide;
the default is a public report for existing links. No new route or resume/
publication endpoint is invented. App owns navigation; the workspace owns
selection-bound reads, filters and drafts. Back/Forward/direct links must prove
this contract in the browser, including a private deep link while disconnected.

Authoritative image inspected: `evaluation-ui-reference-dark-v1.png`,
**1586 x 992**. Pixel geometry from the supplied image (approximate bounds):
sidebar x0-204; topbar y0-56; content origin (221,80), right edge1568. Title and
actions occupy y80-123; metric strip y139-293 has five reference cards with
12px gaps, widths248-304. History x221-1218/y306-721 (997x415), selected rail
x1231-1568/y306-721 (337x415). Lower trend x221-1004/y733-980 (783x247),
failure x1016-1568 (552x247), 12px gap. Panels use ~16px interior spacing,
~8px radii, compact 13-14px metadata, 16px panel headings, 22px page heading,
24px values, and small outlined state chips. History controls are in its header,
with 34px column header, ~54px rows and 42px pager. Charts are secondary to
the run/detail surface. The screenshot has no top-level page tabs; additional
catalog/compare flows will be progressive disclosures or labelled workspace
sections, not an invented selectable evaluation engine.

The screenshot's groundedness/citation accuracy/latency/pass-rate/benchmark,
arbitrary failure labels, sample runs, sparkline improvements, date-range
claims, account/quota and upgrade controls are not production data. Preserve
the composition with six native metrics and actual backend populations;
ratio visuals use fixed [0,1], observations remain separate points/groups.
Shared shell tokens/primitives remain authoritative for existing chrome.
Stitch is optional and has not been used for this task.

### API and state map

- Public anonymous: metrics catalog; mixed native/legacy publication list/detail;
  native results; backend POST comparison; GET grouped trends; GET failures.
  Legacy compatibility remains explicitly labelled and metadata-only; it cannot
  enter native comparison/trends or act as a fallback metric engine.
- Private explicit bearer: the six EVAL-003 list/create/detail/results/cancel/
  finite-SSE routes. Reuse the app-level UI-010 memory-only owner. No global
  bearer transport, persistent token, URL credential or second session owner.
- Creation freezes and queues a registered artifact with native six-metric set,
  provider-backed mode and provider_attempt_slot budget. One logical attempt
  retains one Idempotency-Key; no automatic ambiguous POST retry. Server returns
  canonical ID/revision/frozen binding/state. No optimistic job identity.
- Cancellation uses current If-Match, duplicate protection, visible 409 and
  non-forcing refresh. Requested/cancelling/cancelled are separate. Exactly
  execute_cases and aggregate_report steps; durable progress only; interrupted
  is terminal and has no resume/retry control. Private completion is not public
  publication. Completed durable results remain accessible after stop/failure.
- Metric identity/version/type/meaning and status/denominator are API-owned.
  Zero and false are computed values; null is unavailable/not-applicable, never
  zero. Delta comes only from candidate_minus_baseline. No winner/confidence,
  interpolated/smoothed history, invented failure taxonomy or client evaluator.
- Private raw question, answer, ground truth and rendered evidence are dropped
  in a typed API-boundary projection; only IDs/hashes/metrics reach UI state.

### Task semantics, hierarchy and risk gate

Entry: Tools/Evaluation or canonical selected identity. Intent: inspect native
definitions/public results, compare eligible publications, or explicitly launch
and monitor one private frozen evaluation. Available evidence: API definitions,
published report metadata, durable private receipts. Primary action: New
Evaluation only after local connection and execution capability. Result:
server-canonical queued job/detail. Success is server terminal state, never
stream close or frontend animation. Recovery: reconnect, reload/reconcile,
correct refused inputs; no force-write or unsupported resume.

Component plan: typed evaluation API/DTO module; workspace controller with
independent public list/catalog, selected report/job, compare, trends and
failures lifetimes; metric strip/catalog; history plus detail rail; job creation
dialog; comparison results; trend groups and category analysis. Existing
EvaluationPanel will be replaced after focused replacement contracts exist.
The old client comparison must not remain the native analytics owner.

State matrix: loading/empty/read-only/error/recoverable for every read; queued,
running,cancelling,cancelled,succeeded,failed,interrupted for jobs; separate
budget_exhausted failure; computed/unavailable/not_applicable for metrics;
comparable/incompatible/unavailable/unpaired for comparison. Private unavailable
is not an empty successful list. Public no-history is legitimate.

Request ownership: AbortController plus successor epoch for every asynchronous
state write (including loading/errors/mutations); selected identity and session
generation scope detail/results/events/cancel. A#1-B-A#2 invalidates #1. One
selected event owner resumes ordered finite batches from numeric Last-Event-ID;
duplicates do not repaint and network closure is non-terminal. No new browser
persistence. Notices clear with owning operation/selection. Workspace/page
scroll owns panels; long hashes wrap in disclosures; dialogs own focus/scroll.

Responsive order: title/actions, metrics, list, selected detail, trends/failures,
comparison/catalog as requested; stack rails at compact widths and use labelled
cards on mobile, not squeezed tables. Required captures: native1586x992,
1440x900,1280x856,1024x768,768x900,390x844,1440x700. Body/root overflow zero;
both themes/EN-VI, keyboard/focus/touch/reduced motion and rendered Axe checks.

Five self-review risks: hidden text leakage; native/legacy/job identity
conflation; false/zero/null coercion; stale selection/session/event mutation;
reference mimicry introducing unsupported numbers/states. Each needs direct
regression evidence, not only a full-suite count.

### Planned execution and completion boundary

B: typed client/DTO and privacy/route/header/abort/SSE tests. C: shared session,
jobs/create/detail/events/cancel with canonical route and lifetimes. D: native
catalog/results plus backend compare/trends/failures. E: race tests and
production native-size capture/compare/fix loop. F/G: responsive accessibility,
TypeScript, full Vitest/build, dedicated Chromium/Firefox and route/reference
gates. H: artifact audit, docs, selective commits and requirement-by-requirement
completion receipt. Prefer no backend changes or dependencies. Tests are
synthetic/hermetic and outputs stay ignored. Current completion is unproven;
do not report UI-011 complete until all acceptance gates are evidenced.

Exact Next Action: continue UI-011-B/C, not optional EVAL-004 or DATA-005.

## UI-011-B through D — typed integration and product surfaces (2026-09-27)

- Added one typed `evaluationApi` for the seven public EVAL-001/002 reads and
  six private EVAL-003 job routes. Public calls omit bearer; private calls take
  the UI-010 runtime token explicitly. All reads/mutations accept AbortSignal;
  create owns Idempotency-Key, cancel owns If-Match and events own numeric
  Last-Event-ID. Error bodies are never rendered.
- Private results use a field-by-field boundary projection. Synthetic tests put
  sentinel question/answer/ground-truth/evidence values in transport payloads
  and prove none reach the returned DTO or DOM.
- Replaced the old client-computed/demo Evaluation panel with six native metric
  cards, validated native/legacy history and selected rail, safe paged results,
  backend comparison, grouped point-only trends, the exact four failure groups,
  and private list/create/detail/results/cancel/events. No dependency or backend
  change was needed.
- Private creation adopts only the server canonical ID/state/revision/frozen
  snapshot. The UI names provider_attempt_slot, exactly two backend steps,
  durable/unknown progress, publication separation, budget exhaustion, and
  terminal interruption without a retry/resume action.

Focused contract receipt: API **35/35**, metrics/results **11/11**, job/event/
cancel **17/17**, public async lifetimes **6/6**, workspace **13/13**; total
Evaluation-focused Vitest **82/82**.

## UI-011-E/F — races, visual loop, responsive and accessibility (2026-09-27)

Every selected report/job/result page and compare/trend/failure request has an
abort owner plus successor guard. Job session/selection/page lifetimes reject
A#1→B→A#2 detail, results, event, error and cancel writes. Event batches are
ordered/deduplicated; finite close/network failure does not alter durable job
state. Creation is synchronously duplicate-protected and keeps its logical key
for ambiguous transport outcomes.

The production fixture was captured and inspected at all required sizes. At
1586×992 the implementation preserves the reference's dense metric strip and
history/selected-detail composition, while six real native definitions and
labelled feature tabs consume more vertical space than its five unsupported
metric cards. 1024/768 stack detail, 390 uses one-card/mobile flow, and every
required viewport has body/root overflow 0. Both themes and EN/VI were captured.
The workspace uses the shared keyboard Tabs primitive (Arrow/Home/End), labelled
panels, 44px controls, non-color statuses, visible focus, reduced motion and
trend table equivalents. Axe found one selected-row dark metadata contrast at
4.16:1; switching that selected metadata to `--text-secondary` cleared the
final A/AA scan.

Final frontend gates: TypeScript PASS; production build PASS (existing aggregate
chunk-size warning only); full Vitest **84 files / 619 tests PASS**.

## UI-011-G — production browser and reference gates (2026-09-27)

Dedicated `ui-011-evaluation.spec.ts` covers all 24 requested browser areas plus
Vietnamese semantics with hermetic data and no provider calls. Final paired run:
**24/24** (**12 Chromium + 12 Firefox**). It captures default/catalog, selected
report, incompatible compare, empty/real trends, failures, private unavailable,
queued/running/results, budget/cancel/interrupted, Vietnamese, and seven viewport
states. Canonical report/job routing, paging, Back/Forward, token non-persistence,
private-only authorization, one POST, Last-Event-ID, revision cancellation,
hidden-text projection, axe and overflow are asserted.

Controlled Chromium shell/route/legacy/reference pass: **5/5**; after the one
generic fixture omission was corrected, canonical `ui-routing.spec.ts` passed
**3/3**. The r8 native reference receipt passed. Screenshots/traces/videos remain
under ignored Playwright output and are not staged.

## UI-011-H — artifact audit, commits and closure (2026-09-27)

Implementation commit: `ae81384` — `feat(ui): build native evaluation workspace`.
Backend unchanged. No Ragas/TruLens code, provider call, real credential, raw
evaluation content, `data/` file, DB/WAL/SHM, runtime publication, build output,
browser output or dependency was staged. Fixture tokens and hidden-text sentinels
are synthetic. The same 12 unrelated pre-existing untracked paths were preserved.

README, frontend contract/design, project state and this checkpoint now describe
the implemented public/private boundary, native semantics, routing, tests,
visual decisions and limitations. UI-011 is complete after the documentation
closure commit recorded by the final task receipt.

Exact Next Action: `DATA-005 — Terminal telemetry/logs`. EVAL-004 remains optional
and was not started.

## DATA-005-A — Terminal telemetry/log contract (2026-09-27)

Status: RECORDED BEFORE IMPLEMENTATION. Recovery found HEAD `20cbc6f`, clean
tracked/staged source, and the same 12 unrelated untracked paths. DATA-005 is
the only authorized task; UI-012 and optional EVAL-004/Ragas remain out of
scope.

### Exact ownership and sources

The master plan defines content-free, durable terminal events for later
Analytics and bounded sanitized Logs, not a generic tracing platform. The
persisted source set is the real terminal lifecycle of the allowlisted research
operations `/query`, `/query/decomposed`, their two streaming variants,
`/search`, and `/retrieval/inspect`. Header completion is not terminal for SSE;
stream completion, safe error, timeout, disconnect/cancellation, or incomplete
close owns that terminal boundary. Health/catalog/reader/operational read APIs
are deliberately not noisy telemetry sources.

DATA-004 remains the sole truth for Pipeline, Evaluation, and model-test jobs.
DATA-005 projects terminal `jobs` rows at read time instead of double-writing a
second terminal event. Thus `job_events` remain ordered lifecycle receipts,
`activity_events` remain collection history, and `telemetry_events` contain
only content-free request terminal facts. No frontend/browser telemetry,
provider payload, prompt, document text, query text, session identity, stack
trace, or free-form message enters the server store.

### Record and truth semantics

One immutable persisted record has a server telemetry ID, terminal UTC
`occurred_at`, measured whole-operation `duration_ms` or null, event kind
`request_terminal`, source subsystem, route template, capability,
operational severity, domain outcome, safe correlation ID, optional safe error
code, bounded allowlisted metadata, and 30-day `retention_until`. Stable job
log identity derives from the canonical job ID/revision while the job ID stays
a distinct domain/correlation field.

Outcomes are `succeeded`, `rejected`, `failed`, `cancelled`, or `interrupted`.
Severity is independent: success and client cancellation are informational;
validation/rate-limit rejection and interruption are warnings; server/internal
failure is error. A cancelled or interrupted job is not relabelled failed.
`budget_exhausted` retains the stored failed job outcome but is warning severity
rather than provider/model error. Unknown duration stays null; no cost, token,
provider-health, confidence, resource, throughput, or quality value is inferred.

Correlation accepts only a bounded opaque request ID; invalid client
`X-Request-ID` values are replaced before persistence or response. Metadata is
an allowlist of small typed operational fields, canonical JSON, and never an
arbitrary text/blob sink. Absolute Windows/POSIX paths, credential-shaped keys
or values, control/newline text, configured secrets, and oversized metadata
fail before insert. Terminal insertion is immutable and idempotent by the
server record ID. It is best-effort with respect to the completed request: a
telemetry storage failure emits only a generic application warning and never
rewrites the source outcome or fails the request. No exactly-once claim is made
across process loss before that best-effort write.

### Persistence, retention, query and access

The existing v3 `telemetry_events` placeholder is the single persistence
authority. A new deterministic transactional v6 migration will add the typed
terminal columns and query indexes without rewriting historical migrations.
Every repository read/write hides expired telemetry and prunes it at the next
repository operation. Telemetry retention is fixed at 30 days; `/logs` is a
7-day sanitized projection. Existing allowlisted settings remain future UI-012
configuration facts, not mutable DATA-005 policy. Telemetry/job facts remain
outside portable workspace export/import, matching existing job-event and
activity exclusions.

DATA-005 owns the master-plan read routes: protected `GET /analytics/summary`,
`GET /analytics/timeseries`, and `GET /logs`. All reuse API-001 local bearer,
loopback, exact Host/Origin checks. Public mode returns the existing fail-closed
404 without creating/opening the private DB. Summary defines request outcome
rates and duration percentile populations plus terminal job counts. Timeseries
accepts only bounded range/interval/metric enums, returns deterministic UTC
buckets, zero only for measured count populations, and null for a duration
bucket with no samples. Logs accept only category/level/cursor/limit, merge
terminal request rows with read-only terminal job projections, and order by
`occurred_at DESC, record_id DESC` behind an opaque bounded cursor. No arbitrary
sort/filter or unbounded history endpoint is added.

### Planned files and gates

Planned ownership: migration v6; `src/workspace/telemetry.py`; typed API models
and a thin telemetry router; narrow application request/stream integration;
route-contract updates; focused model/redaction/persistence/restart/query/access/
projection tests; then DATA-001/002/004, Pipeline/Evaluation, full hermetic
backend, import, 83-route, diff, artifact and secret gates. Frontend files and
dependencies remain unchanged.

Exact Next Action: DATA-005-B/C domain, sanitization, migration, repository and
focused tests. Do not implement UI-012 or EVAL-004.

## DATA-005-B/C — Structured records, sanitization, migration and query (2026-09-27)

Implementation commit `2fd839a` (`feat(data): add terminal telemetry
foundation`) adds `SQLiteTelemetryRepository` and `TelemetryService` over the
existing workspace database. Migration v6 is additive, checksum-tracked and
transactional; it does not rewrite v1-v5. A v5 database upgrades in place and
legacy placeholder rows remain outside the typed `request_terminal` population.
Fresh/reopened databases report schema 6.

The immutable request record contains only server identity, terminal UTC time,
allowlisted subsystem/route/capability, separate severity/outcome, safe
correlation, optional safe code, measured duration or null, and canonical small
metadata. Zero duration remains zero and unknown remains null. Credential-shaped
or configured-secret values, Authorization/cookie-style fields, Windows/POSIX
absolute paths, controls/newlines, unsupported fields and oversized metadata
are rejected before insert. An unsafe client request ID is replaced before it
can be echoed or stored. Synthetic adversarial values are tests, not credentials.

Telemetry retention is 30 days; expired rows are hidden and pruned at the next
repository operation. Logs expose seven days without creating a second table.
Request log pages and terminal-job candidates are independently bounded in SQL,
then merged by `occurred_at DESC, record_id DESC`; the opaque cursor preserves
that exact secondary identity. Summary and timeseries accept only 24h/7d/30d,
hour/day and five named metrics, with a maximum 720 buckets. Empty percentile
populations are null; count populations may be zero.

## DATA-005-D — Terminal source integration and duplication semantics (2026-09-27)

The request middleware now replaces unsafe request IDs and records route
templates rather than actual dynamic paths. Non-streaming allowlisted research
operations persist after the real response is formed. Both query generators own
their terminal record in `finally`: done, safe error, timeout,
disconnect/cancellation and incomplete close are distinct, and SSE header return
does not stop the clock. Client cancellation is informational, validation and
rate-limit rejection warning, internal/server failure error. No raw question or
provider body enters the record.

One server telemetry ID makes repeated identical insertion idempotent and a
conflicting stale insertion fails without rewriting history. Persistence is
best-effort after the source outcome; injected storage failure returns the
unchanged real response and logs only a generic warning. A process loss before
that write can omit a record, so no exactly-once claim is made.

Pipeline/Evaluation/model-test terminal facts are projected from DATA-004
`jobs`; no telemetry double-write occurs. The projection preserves canonical
job ID/revision/state/failure code. Succeeded, cancelled, interrupted, generic
failed and `budget_exhausted` cases are covered. Cancelled remains info,
interrupted warning, generic failure error and budget exhaustion warning;
unmeasured job duration remains null. Restart/reopen and transfer tests prove
records survive locally while telemetry/jobs/job events remain absent from
portable backup.

## DATA-005-E — Protected HTTP reads and access boundary (2026-09-27)

The thin telemetry router adds exactly three local-workspace reads:

- `GET /analytics/summary?range=24h|7d|30d`
- `GET /analytics/timeseries?range=...&interval=hour|day&metric=...`
- `GET /logs?category=request|job&level=info|warning|error&cursor=...&limit=...`

All reuse API-001 local bearer, loopback socket, exact Host and optional exact
Origin checks. Public mode and unauthorized access fail before service creation;
public mode creates no DB and reveals no telemetry existence. Invalid selectors,
cursors and bounds return 422. Response models are strict. The final route
inventory is 83 unique method/path pairs and 83 unique names, with all three
owned by `src.api.routers.telemetry`.

## DATA-005-F — Validation, audit and closure (2026-09-27)

Actual gates:

- DATA-005 domain/persistence/projection/query: **24/24**.
- DATA-005 HTTP/access/lifecycle: **13/13**; the focused legacy route-template
  metrics check also passed, for **37/37** new DATA-005 tests overall.
- DATA-001/002/004, access, Pipeline, Evaluation jobs, router and legacy API
  regression slice: **256/256**, five pre-existing warning instances.
- Full hermetic backend: **1217 passed, 0 failed, 188 warnings**. Baseline was
  1179/0/188, so warnings did not grow.
- Compile/import PASS. Route inventory **83**, collision/name checks PASS.
  `git diff --check` PASS.

Frontend files/tests/build were not touched or rerun. No provider call, Ragas,
external telemetry dependency, canonical data mutation, runtime DB/WAL/SHM,
runtime log, provider dump, screenshot, report, cache, scanner state, or real
credential is part of the implementation commit. The expected synthetic secret,
path and control-shaped strings exist only in hermetic redaction tests. The same
12 unrelated pre-existing untracked paths remain preserved.

Known limits are explicit: best-effort request-terminal persistence is not
cross-process exactly-once; retention is fixed until UI-012 owns the supported
settings; process logger output is not ingested; there is no cost/token/resource/
provider-health/quality aggregation; and UI-012 has not yet replaced the
browser-local Analytics compatibility surface.

README, architecture, project state and this checkpoint now record the
implemented authority, sources, access, retention, query contract, tests and
limitations. DATA-005 is complete after the documentation closure commit
recorded by the final task receipt.

Exact Next Action: `UI-012 — Analytics / Logs / Settings`. Optional EVAL-004
remains skipped; do not start either task during DATA-005 closure.
