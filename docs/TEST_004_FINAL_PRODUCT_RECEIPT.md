# TEST-004 — Final product receipt

## A — Acceptance plan (2026-09-27)

Starting committed HEAD `e4c6710`, branch
`codex/bilingual-research-workspace`; tracked/staged clean, original12 unrelated
untracked paths preserved. TEST-004 only: no UI-013 cleanup, optional Ragas,
dependency upgrade, live provider or canonical corpus mutation.

Authority: AGENTS, current checkpoint/journal, master-plan TEST-004 (depends on
TEST-002 and TEST-003), API-001/DATA-001…005/API-003…007/EVAL-001…003 and current
frontend contracts. Master defines browser/integration suites across widths,
locales and two browsers, without prescribing named final journeys. TEST-003
retains native nine-reference authority; no full visual matrix repeat unless a
shared visual repair requires it. Native zoom125/150/200 is external manual /
unverified, separate from viewport checks.

Clean reproducibility: managed detached worktree at starting HEAD, no `.env`,
data/DB/build/cache/untracked source. Install frontend with pinned Bun and frozen
lockfile; use a declared provisioned Python interpreter, inspect required imports,
compile and inventory83 unique routes. Run focused then full hermetic backend,
TypeScript/full Vitest/build. Recheck final committed HEAD after any code repair.
Provisioned packages do not establish from-scratch dependency installation or
live model availability; record environment and limits rather than infer them.

| Final journey | Real wiring and focused complementary evidence |
| --- | --- |
| A Public knowledge | Documents/facets/stats→Search POST/snapshot paging→Retrieval/Reranker→canonical excerpt/reader; actual HTTP routes, bounded corpus fixture dependency only |
| B Chat/Research | Submit→real SSE/nonstreaming transport→answer/source→reader; byte-fragmented UTF-8, session/variant identity, failure/read-only/stale safeguards |
| C Local workspace | Explicit memory-only connection→real protected configuration/SQLite; Collections CRUD/member/note/activity/export/conflict/tombstone/atomicity through real API; demonstrate existing staged browser wrapper refusal honestly |
| D Registries/Pipeline | Real configured/runtime/unknown Models and dataset provenance; connect→one queued staging ID/five pending steps→finite events/current-revision cancel; no worker/provider/corpus promotion |
| E Native Evaluation | Six v1 definitions/public analytics→real frozen durable job paths with deterministic provider boundary only→budget/cancel/interrupted/results; null/zero/false/privacy projections preserved |
| F Operations | Real terminal requests→same DB Analytics/Logs→Settings transfer/presentation→disconnect/reload credential loss; safe content-free telemetry, opaque cursors |

Focused tests prove migration versions/fresh/reopen/WAL/FK/busy timeout, supported
upgrade and deterministic collection race barriers; transfer canonical digest,
bounded body/version/conflicts and exclusion of job/telemetry histories. API-001
negatives cover missing/wrong bearer, exact Host port, Origin/peer, forwarding,
execution gates and public no-DB/no-existence leakage. Synthetic secrets only.

Production frontend browser journeys must use actual local HTTP handlers, not
Playwright response mocks; model/retrieval/provider doubles are explicitly scoped
test dependencies. Collect unexpected page errors, rejected promises, assets,
HTTP5xx and React/chunk failures; intentional asserted status errors are allowed.
Chromium/Firefox, EN/light and VI/dark, desktop1440×900, compact1024×768,
phone390×844 and short1440×700, focused whole-page axe and screenshots. Route
direct/sidebar/Back/Forward and high-risk stale/duplicate protections supplement
these compact journeys. No performance/SLA or blanket security/WCAG claim.

UI semantics: App owns canonical route/document and memory-only connection;
domain controllers own submitted requests/epochs/selected IDs, SQLite owns
private workspace/job/telemetry truth, browser stores own saved conversations and
presentation. Source readers retain answer/source/document/revision identity.
Primary intent is question→answer→source→reader or catalog→document reader;
recovery distinguishes refused capability, missing/expired record, conflict,
unknown/unavailable, partial answer and terminal job state. Scroll owners remain
workspace/list/reader/overlay; notifications clear with the owning operation.

Five risks: accidentally consuming developer credentials/corpus; accepting route
mocks as runtime proof; weakening local access for browser convenience; claiming
staged capability or fake job success; validating old commits after repair.
Mitigations: clean isolated tree/temp stores and offline guard; real HTTP audit;
unchanged bearer/Host/Origin controls; explicit expected refusal/semantic checks;
final-HEAD replay and selective artifact audit. Every reproduced release blocker
gets a failing focused regression before the smallest correction.

Known baseline: backend1384/188 warnings/83 routes (TEST-002); frontend90/790;
TEST-003 browsers300, existing506.91kB bundle warning, native zoom unverified,
staged real Collections/model-test bearer integration. These were historical
inputs, not TEST-004 results.

## B–E — Clean runtime, contracts and feature boundaries (2026-09-28)

Implementation/test HEAD `0609e2ff4fe33a09358d1620e1cf7e648ff30bba` is
validated in a managed detached checkout outside the repository.
This documentation is included in the closure commit; resolve that commit with
`git rev-parse HEAD` at handoff. The checkout starts without `.env`, `data/`,
private DB, or untracked source. A declared Python 3.12.7 test interpreter,
Bun 1.3.14 and Node 24.19.0 were available; this establishes a clean-source
replay using provisioned packages, not a from-scratch backend dependency install.
`bun install --frozen-lockfile` checked 284 packages without a lockfile change.
`src.api.app` imports, source compilation succeeds, and 83 method/path route
pairs are unique. The product server enters real FastAPI lifespan and closes the
store; four new bootstrap tests verify public/no-DB, local/create-and-reopen,
interrupted job recovery, and empty-corpus fail-closed behavior. The normal
hermetic suite requires no external network or provider.

Full clean backend: **1354 passed, 34 skipped, 0 failed, 148 warnings**. The
34 skips are local-corpus-dependent tests in the deliberately data-free checkout;
the same source in the original tree, with its untouched local artifacts, ran
**1388 passed, 0 failed, 188 warnings**. No warning growth against the 188
historical baseline is claimed. Focused final bootstrap, TEST-002, migrations,
transfer, access, collection atomicity, Search, jobs and telemetry: **360 passed,
1 warning**. Tests cover fresh and upgraded SQLite schema, WAL/FK/busy/reopen,
portable canonical digest/round trip/body bounds/conflict and excluded job/log
histories, deterministic collection mutation barriers, durable evaluation steps,
and telemetry null/zero/privacy/cursors. Public mode creates no private DB.

Access/security stayed unchanged: public private routes fail closed without
existence leakage; local routes require bearer, loopback, exact Host port and
allowed Origin, and reject forwarded-header bypass. Focused and full suites
exercise wrong/missing bearer, unsafe metadata/path/control characters,
oversized bodies, malformed cursors and stale revisions. The browser product
journey checks a synthetic token is absent from local/session storage,
IndexedDB, cookies, URL, DOM, exported workspace data and logs; reload loses
the connection. These are bounded test results, not a security certification.

| Surface | TEST-004 validation and current truth |
| --- | --- |
| Chat/RAG | Fresh `/chat` → real SSE → Unicode answer and canonical cited excerpt → document reader; interrupted stream, session expiry/read-only and backend error paths in 16-case HTTP suite. Corpus/retrieval/generation dependencies alone are deterministic. |
| Research | Independent fresh `/research` → `/research/{conversationId}` SSE, completed answer, cited source and reader; direct route and Back/Forward. The test requires a Research-family route rather than relabelling a saved Chat conversation. |
| Documents | Real catalog/stats (2 documents, 4 chunks), source identity/reader handoff; full backend and affected visual fixtures cover absent representation and no invented page/form facts. |
| Search | One POST, canonical 16-hex snapshot ID and one paged GET, reader return without re-POST; 404/410/422/429 and Unicode code-point offsets in hermetic backend/contracts. |
| Retrieval/Reranker | Provider-free real inspect and analyst summary; backend stage/score/status contracts and regular frontend suites cover lexical/dense/fusion/reranker, null timing and negative logits. Reranker also has direct-route smoke, not a tenth visual reference. |
| Collections | Real local protected SQLite create/member/note/update/conflict/activity/export/delete/tombstone plus access negatives; deterministic atomicity tests. The currently staged browser wrapper still receives a truthful 401/refusal after local connection—this gate did not add bearer integration. |
| Models | Real registry returns three roles and distinguishes loaded from unavailable; full contract/component tests retain configured/runtime/unknown identity. The separate model-test bearer browser limitation remains staged. |
| Datasets | Real two-kind registry and direct route; full backend/contract tests retain serving/evaluation provenance and missing/mismatch/empty/unknown distinctions. |
| Pipeline | Real memory-gated POST creates exactly one queued ID with five pending steps, null current progress, finite SSE event read and revision-gated cancellation; no worker execution or promotion is claimed. |
| Evaluation | Six native-v1 definitions, public reports including exact computed zero, real frozen job with attempt-slot budget 3, two durable ordinals 0/1, consumed 2 and private result; full tests cover compare/null delta, cancellation, exhaustion and interruption. No Ragas or exactly-once claim. |
| Analytics | Real terminal query feeds protected server summary; 24h/7d/30d, p50/p95/null and terminal-job semantics covered by backend/frontend tests. |
| Logs | Protected request/job logs, safe content-free detail and opaque cursor; live result omits the question and token, with ordering/severity tests in full suite. |
| Settings | Shared memory connection, truthful controls, portable export/import-preview digest, explicit disconnect and reload loss; no unsupported provider switching or writable retention is claimed. |

## F — Production browser and prior gates

`bun run lint`/TypeScript PASS; full Vitest **90 files, 792 passed, 0 failed**;
focused TEST-002 types/requests/responses plus ScopeEditor and EvaluationPanel
**118 passed**. `bun run build` PASS, 2074 modules; aggregate JS ~506.92 kB
still triggers the historical >500 kB warning. `bun run test:e2e-product`
serves built Vite assets and real FastAPI public/local ports with temporary
SQLite. Playwright only firewalls external origins—it does not fulfill API
responses. Final run **24/24 passed** (12 Chromium, 12 Firefox): A–F, scope
pointer/keyboard, dark report hover/focus and 14 direct routes plus Back/Forward.
It asserts no unexpected page errors, 5xx or required asset failures.

The compact campaign covers desktop1440×900, compact1024×768, phone390×844
and short1440×700 for six routes, EN/light and VI/dark in both engines:
**96 populated viewport combinations**. There were **120 whole-page axe
A/AA analyses with no reported violations**, 120 saved diagnostic screenshots
and zero measured body/root horizontal overflow. Representative Research
reader, mobile Chat, dark Evaluation hover and Pipeline queued screenshots were
inspected; screenshots remain ignored and uncommitted. This is focused sanity,
not native-zoom or blanket WCAG certification. Native 125/150/200 zoom remains
manual/unverified. The changed shared surfaces' TEST-003 native/responsive
references (Chat, Research, Evaluation) passed **30/30**, including 216
populated responsive cases; the prior full300/648 campaign was not repeated.

Prior real-transport suites pass from the clean checkout: HTTP/SSE **16/16**
(8/engine); local indexed-reader/identity **6/6**; TEST-002 browser Unicode
contract **4/4**. A strengthened old SSE test now waits for an actual answer
when `done` is omitted; stale selectors were aligned to current semantic labels.
TEST-002 Python/TS route, enum, null/zero/false, revision, cursor, Unicode and
SSE assertions remain green. No request/response contract changed.

## G — Reproduced defects, repair and replay

All four product defects were P2; each failed in a focused real-browser or
component check before the smallest correction and passed after repair:

1. Chat scope popover was clipped/non-clickable by the composer form's overflow
   and narrow positioning. `ChatInput.tsx`/`components.css` allow the popover
   to occupy the form anchor; pointer hit-testing and two-browser product runs
   pass.
2. Controlled ScopeEditor Escape/outside close changed only internal state and
   could reopen under its still-open owner. It now notifies the owner;
   two focused Vitest regressions and browser keyboard checks pass.
3. Light source score badge had ~1.51:1 text contrast. Semantic success-surface
   and success-text tokens restore readable evidence metadata; focused axe,
   product reader and affected TEST-003 surfaces pass.
4. Dark Evaluation hovered report metadata fell to ~4.16:1. The selected
   hover/focus state now uses the readable secondary-text token; focused
   Firefox axe, final two-browser hover/focus and TEST-003 Evaluation pass.

Test-only corrections aligned legacy reader/source locators, preserved a real
omitted-`done` assertion, and isolated bootstrap environment overrides. An
intermediate sequential Chat→Research test was rejected after one 21/22 clean
run: its second request could be withheld during a conversation transition and
it could relabel an existing Chat conversation. Independent fresh-family tests
now assert both the URL and completed SSE; the final 24/24 run is authoritative.
No deterministic P0/P1/P2 acceptance regression remains.

## H — Artifact, documentation and handoff

TEST-004 production repairs, real-server tests and regressions are in
`defec4f62b59fa108501601a3e10b1a09ef35ada`; independent Chat/Research
test correction in `0609e2ff4fe33a09358d1620e1cf7e648ff30bba`. Closure
documentation is a separate commit. README's real product command and
server-backed Analytics wording, and DESIGN's Search/Models endpoints, were
corrected; ARCHITECTURE and FRONTEND_CONTRACT needed no material change.
No dependency/lockfile, canonical data, `.env`, generated DB/WAL/log/report,
dist, screenshot/trace, cache, provider dump, private key or task credential is
committed. The original 12 unrelated untracked paths are preserved. Final
tracked/staged cleanliness and final-HEAD replay are recorded at handoff.

Limits: the browser Collections/model-test bearer integration remains staged;
the prior aggregate bundle warning and historical backend warnings remain;
native browser zoom is unverified; no live provider, SEC/network, from-scratch
Python dependency installation, production SLA, load, or broad security/WCAG
certification was attempted. The verified dependency graph has TEST-004 after
TEST-002/003 and UI-013 after TEST-004. **Exact Next Action: UI-013 —
Cleanup/documentation. Do not implement it in TEST-004.**
