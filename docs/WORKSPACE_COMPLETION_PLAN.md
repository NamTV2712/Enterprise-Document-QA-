# Enterprise Document QA workspace completion plan

This is the executable handoff for the bilingual SEC research workspace. It
keeps the product decisions from the merged Vietnamese proposal while recording
only evidence that exists in this repository. Repository documentation is in
English; the product supports English and Vietnamese.

## Scope lock

- React/Vite frontend, FastAPI backend, local Qdrant, and the existing corpus.
- Personal research data remains local to the browser. No authentication,
  cloud sync, multi-user administration, private-document upload, fake model
  selector, Web Search, or PDF pagination is in scope.
- UI and answer language are English/Vietnamese. Query translation is not an
  additional LLM request.
- The enterprise blue/slate light/dark palette is applied without changing the
  existing workspace layout.
- Provider budget for this round is at most 120 real requests, including retry,
  correction, calibration, and unknown outcomes. The official benchmark and
  canonical corpus/index are immutable.
- Do not merge or deploy automatically. Do not commit `.env`, `data/`, model
  caches, checkpoints, or generated diagnostics.

## Baseline and source identity

| Item | Recorded value | Status |
|---|---|---|
| Branch | `codex/bilingual-research-workspace` | PASS |
| Starting commit | `e86685fbcc195dcad04f8d9f2d7be01a7dd53797` | PASS |
| Existing backend gate | 716 tests plus `compileall` | PASS (baseline) |
| Existing frontend gate | 100 tests, typecheck, build, contrast | PASS (baseline) |
| Existing browser gate | 94 Chromium/Firefox checks, one worker on Windows | PASS (baseline) |
| Current frontend gate | 107 tests, typecheck, lint, production build | PASS |
| Current browser gate | 102 Chromium/Firefox checks, one worker on Windows | PASS |
| Existing HTTP/SSE gate | 14 checks | PASS (baseline) |
| Provider A | Historical ledger stopped after quota/429 | INCOMPLETE |
| Provider B | `window_03` stopped at 24/60 and `window_04` stopped at 39/60 after 429 | INCOMPLETE |
| Backend Docker receipt | `data/diagnostics/local_release_receipt_bilingual_workspace.json` | PASS (previous source) |

Every new run must use a unique diagnostic run ID. Existing receipts are not
overwritten or reclassified.

## Requirement tracking

Statuses are limited to `TODO`, `IN_PROGRESS`, `PASS`, `FAIL`, `BLOCKED`, and
`INCOMPLETE`. A milestone is not PASS merely because a related test count is
green.

| ID | Requirement | Status | Evidence / remaining work |
|---|---|---|---|
| P0 | Audit, source/lock/artifact identity, tracking | IN_PROGRESS | This table and the source handoff exist. Add a fresh bundle/performance manifest and final staged-diff evidence. |
| P1 | Vietnamese/English interpretation and request language binding | PASS (offline) | `src/retrieval/query_normalizer.py`, API/frontend language tests, request snapshots, direct/SSE/decomposed paths. |
| P2 | Durable Library schema, backup, migration, import/export | IN_PROGRESS | Conversation records now write schema v4; backup writes v2 and reads v1; tags, notes, variants, evidence collections, strict reference validation, ID remapping, limits, tombstones, partial results, and import preview/confirm are implemented. Browser crash/quota matrix remains. |
| P2-L | One-tab writer ownership | PASS (offline) | Web Locks ownership, retry, read-only/export state, reload-on-ownership, and two-context Playwright handoff after the first tab closes are green. |
| P3 | Public documents/retrieval/system/evaluation contracts | PASS (offline) | Allowlisted FastAPI routes and provenance-validated public reports are covered by backend contract tests. |
| P4 | Palette, navigation, locale, keyboard, accessibility | IN_PROGRESS | Blue/slate semantic tokens, light/dark state tokens, writer state, source focus styles, animation contrast, and the expanded responsive/reduced-motion/keyboard browser matrix are green (`102/102`). Raw-color audit and 200%/system-theme coverage remain. |
| P5 | Research utilities and evidence journey | PASS (offline) | Templates, palette, Library, bookmarks, notes, collections, tags, variants, feedback categories, Markdown/backup export with preview/confirm, and continue-reading flow are implemented and covered by unit/browser gates. |
| P6 | Evidence contract and Document Explorer | PASS (offline) | Explorer/citations/source search exist; focused citations highlight and scroll to the source, Markdown emits stable local evidence anchors, and reload/export deep-link assertions are green. |
| P7 | Retrieval Lab and architecture showcase | PASS (offline) | Provider-free presets, traces, score-scale disclosure, comparison, JSON/CSV export, public metadata, and no-generation handoff are implemented and tested. |
| P8 | Evaluation dashboard and experiment comparison | PASS (offline) | Public report publisher/API and recorded mode exist. `evaluationComparison.ts` rejects incompatible provenance and computes paired bootstrap (2,000 resamples, seed 42); live fixture rendering and JSON/CSV UI export assertions are green. |
| P9 | Analytics, guided demo, and performance | IN_PROGRESS | Metadata-only analytics, redacted export/clear, and recorded demo exist. Production-build Library search over 100 conversations × 10,000 messages passed 100 warm samples with latest full-freeze p95 `40.84 ms` Chromium / `55.74 ms` Firefox, below 200 ms; only the 3–5 minute guided browser walkthrough remains to be captured. |
| P10 | Offline freeze and 120-fixture acceptance matrix | INCOMPLETE | Existing 40 × EN/VI/accentless fixture source exists. Re-run the expanded browser, HTTP/SSE, migration/lock, publisher, trace-parity, IME, and performance matrix after the current changes. |
| Provider A | Evidence Contract v3, max 60 calls | INCOMPLETE | Historical quota stop is preserved. Fresh `evidence_contract_v3_window_04` preflight passed with zero calls, but execution was not started because only 53 shared slots remained after Provider B retries. |
| Provider B | Bilingual campaign, max 60 calls | INCOMPLETE | Fresh `window_03` stopped at 24/60 and fresh `window_04` stopped at 39/60 with `RateLimitError`/HTTP 429, even after the updated key was accepted by the two-call probe. Never resume either incomplete ledger. |
| P11 | Docker candidate receipt | PASS (previous candidate) | Existing one-worker/local-Qdrant receipt is valid for its recorded source; rebuild only if backend/build inputs change. |
| P12 | Docs, review, CI, PR handoff | IN_PROGRESS | README, plan, and journal are being updated; frontend `107/107`, browser `102/102`, backend `716 passed`, compileall, lint, and production build are green. Final diff/commit/CI handoff remains. Do not merge or deploy. |

## Product acceptance journeys

### Research journey

1. Select a company/section and ask a question in English or Vietnamese.
2. Read the answer and inspect literal filing excerpts; citation focus must
   open, scroll, and visibly highlight the selected source.
3. Save a bookmark/evidence collection, add a local note/tag, and optionally
   save an answer variant with its own request snapshot and evidence.
4. Export Markdown or backup JSON v2, reload, and restore without reusing local
   conversation/session/message/variant/collection IDs.

### Portfolio journey

1. Run the provider-free demo or explicitly labelled recorded demo.
2. Inspect retrieval presets, stages, score scales, selected chunks, and
   comparison rank movement.
3. Inspect published evaluation provenance, cases, gates, and compatible paired
   experiment deltas with uncertainty.
4. Use System/Architecture information to explain corpus, model/index identity,
   runtime trade-offs, limitations, and measured versus local-only analytics.

## Data and writer contract

- Legacy conversation records (v1–v3) are read and normalized to record schema
  v4. Future records remain visible but write-locked and exportable.
- The local envelope uses version 4; older envelope versions remain readable
  and are durably rewritten only after a successful writer-owned write.
- Backup v2 contains conversations, notes, tags, variants, bookmarks, source
  excerpts, and evidence collections. Backup v1 remains readable.
- Invalid types, non-finite numbers, duplicate/unknown references, future
  schemas, malformed tombstones, quota errors, and pending deletion are not
  silently discarded.
- A Web Locks-supported tab must own the Library writer lock before writes.
  Tabs without a reliable lock are read-only/export-only. BroadcastChannel is
  notification only; the receiving tab rereads durable state.

## Theme and interaction contract

- Primary surfaces use `#F6F8FB/#08111E`, `#FFFFFF/#0D1828`,
  `#F4F7FA/#111F32`, and `#EDF2F7/#17283D` for light/dark respectively.
- Brand and focus use readable blue foreground/background pairs; status colors
  have distinct foreground, surface, and border tokens.
- No decorative neon, glow, gradient, pure-black page, or confidence-like
  relevance color scale is allowed.
- Locale changes do not mutate saved history or an in-flight request. Enter and
  Shift+Enter respect Vietnamese IME composition. Reduced motion reveals content
  directly. Skeletons retain layout and live regions announce state changes,
  not every streamed token.

## Offline gates and performance evidence

Run targeted tests while changing code, then run the full freeze from the
repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --disable-warnings
.\.venv\Scripts\python.exe -m compileall -q src tests
Set-Location frontend
bun run test
bun run lint
bun run build
Set-Location ..
```

Browser suites use one worker on the Windows baseline. They must assert visible
content rather than force-clicking through a broken layout. The expanded matrix
adds 320px, 200% zoom, system theme changes, reduced motion, keyboard-only
flows, and serious/critical axe checks.

For the current local browser harness, set the mock API origin explicitly when
an ignored developer `.env.local` points elsewhere:

```powershell
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
bun run test:e2e -- --workers=1
```

The Library fixture is 100 conversations × 10,000 messages. The committed
`conversationSearch.test.ts` measures the warmed search operation over 100
queries and enforces p95 < 200 ms. This is not yet a PASS for full production
render p95; a production-build browser measurement with the same fixture must
be captured before P9/P10 can close.

## Provider accounting and resume policy

- Reserve one ledger slot before every transport attempt. Retry, timeout, 429,
  and unknown outcomes consume the reserved slot; SDK retries remain disabled.
- Campaign A and B are each capped at 60, with a shared cap of 120. Campaign
  IDs do not reset that budget and closed incomplete ledgers are never resumed.
- Calibration must distinguish frozen correct/incorrect samples before sentinel
  calls. A quota or interruption is `INCOMPLETE`, never semantic PASS/FAIL.
- Provider execution is not part of offline CI and there is no public provider
  evaluation button.

### Current execution receipt — 2026-09-07

- The updated Groq key passed two isolated probes (`window_03` and
  `window_04`), each with two HTTP 200 calls and complete generation/judging
  preflight evidence.
- `GROQ_API_KEY5` is configured locally and is already included in the
  generation/judging rotation; key rotation does not increase the shared
  campaign budget.
- A controlled key5-only probe (`window_05_key5`) completed generation and
  judging with HTTP 200, `provider_calls_complete=true`, and both quality and
  acceptance preflight passing. It consumed two additional requests.
- Fresh Provider B execution was attempted only through its bounded runner:
  `bilingual_evaluation_v1_window_03` stopped at `24/60`, and
  `bilingual_evaluation_v1_window_04` stopped at `39/60`, both on provider
  rate limits. The latest status is `INCOMPLETE`, not a semantic result.
- This continuation used `69` real requests (`2 + 24 + 2 + 39 + 2`) out of the
  shared `120` request cap. The fresh Provider A `window_04` manifest was
  registered provider-free but was not executed because a complete 60-call
  campaign would exceed the remaining `51` slots. No provider retry is safe
  without a newly authorized budget/window.

## Handoff checklist

Before final handoff, record actual values rather than estimates for:

- final source SHA, branch, PR and CI run IDs;
- backend/frontend/browser/HTTP gate counts and diagnostic run IDs;
- bundle gzip baseline/final and production Library p95 report;
- Docker image ID, source/model labels, receipt path/hash, and provider call count;
- campaign manifests, ledger hashes/counts, remaining budget, and incomplete reasons;
- screenshots/accessibility evidence for EN/VI × light/dark at required widths;
- known limitations, verified resume commands, and explicit merge/deploy/index
  state.

Current state: `IMPLEMENTATION COMPLETE / OFFLINE VALIDATION GREEN`. The
offline workspace closures and two-tab lock evidence are green; Provider B is
incomplete after rate limits, Provider A has only a fresh preflight, production
Library p95 and the full 120-variant freeze remain open, and the official
benchmark is unchanged.
