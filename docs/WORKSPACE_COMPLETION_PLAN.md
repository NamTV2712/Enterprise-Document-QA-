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
- On 2026-09-07 the user explicitly authorized a key5-only continuation until
  the key/provider quota is exhausted. This is recorded as an execution
  override to the earlier 120-request round cap; every fresh campaign still
  uses its own bounded ledger and incomplete ledgers remain closed.
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
| Current browser gate | 106 Chromium/Firefox checks, one worker on Windows | PASS |
| Existing HTTP/SSE gate | 14 checks | PASS (baseline) |
| Provider A | Fresh key5-only `window_07_key5`, 48/60 | PASS / GO |
| Provider B | Fresh key5-only `window_06_key5`, 52/60 | FAIL / NO-GO |
| Backend Docker receipt | `data/diagnostics/local_release_receipt_bilingual_workspace.json` | PASS (previous source) |

Every new run must use a unique diagnostic run ID. Existing receipts are not
overwritten or reclassified.

## Requirement tracking

Statuses are limited to `TODO`, `IN_PROGRESS`, `PASS`, `FAIL`, `BLOCKED`, and
`INCOMPLETE`. A milestone is not PASS merely because a related test count is
green.

| ID | Requirement | Status | Evidence / remaining work |
|---|---|---|---|
| P0 | Audit, source/lock/artifact identity, tracking | PASS (offline) | Clean source, lock, asset, performance, and final-diff evidence is recorded in `data/diagnostics/workspace_completion_manifest_final.json`; the receipt reports `provider_calls=0`, clean worktree, passing diff check, and p95 below 200 ms. |
| P1 | Vietnamese/English interpretation and request language binding | PASS (offline) | `src/retrieval/query_normalizer.py`, API/frontend language tests, request snapshots, direct/SSE/decomposed paths. |
| P2 | Durable Library schema, backup, migration, import/export | PASS (offline) | Conversation records write schema v4; backup writes v2 and reads v1; tags, notes, variants, evidence collections, strict reference validation, ID remapping, limits, tombstones, partial results, and import preview/confirm are implemented and covered by the full browser freeze. |
| P2-L | One-tab writer ownership | PASS (offline) | Web Locks ownership, retry, read-only/export state, reload-on-ownership, and two-context Playwright handoff after the first tab closes are green. |
| P3 | Public documents/retrieval/system/evaluation contracts | PASS (offline) | Allowlisted FastAPI routes and provenance-validated public reports are covered by backend contract tests. |
| P4 | Palette, navigation, locale, keyboard, accessibility | PASS (offline) | Blue/slate semantic tokens and compatibility aliases now drive both themes; decorative gradients/glows were removed from the shell and primary workspace surfaces. The expanded responsive/reduced-motion/keyboard/system-theme/contrast matrix is green (`106/106`) across Chromium and Firefox, including 320/390/640/1440 layouts. |
| P5 | Research utilities and evidence journey | PASS (offline) | Templates, palette, Library, bookmarks, notes, collections, tags, variants, feedback categories, Markdown/backup export with preview/confirm, and continue-reading flow are implemented and covered by unit/browser gates. |
| P6 | Evidence contract and Document Explorer | PASS (offline) | Explorer/citations/source search exist; focused citations highlight and scroll to the source, Markdown emits stable local evidence anchors, and reload/export deep-link assertions are green. |
| P7 | Retrieval Lab and architecture showcase | PASS (offline) | Provider-free presets, traces, score-scale disclosure, comparison, JSON/CSV export, public metadata, and no-generation handoff are implemented and tested. |
| P8 | Evaluation dashboard and experiment comparison | PASS (offline) | Public report publisher/API and recorded mode exist. `evaluationComparison.ts` rejects incompatible provenance and computes paired bootstrap (2,000 resamples, seed 42); live fixture rendering and JSON/CSV UI export assertions are green. |
| P9 | Analytics, guided demo, and performance | PASS (offline) | Metadata-only analytics, redacted export/clear, recorded demo, and the provider-free guided portfolio route are covered. Production-build Library search over 100 conversations × 10,000 messages passed 100 warm samples with p95 `42.69 ms` Chromium / `54.08 ms` Firefox, below 200 ms. |
| P10 | Offline freeze and 120-fixture acceptance matrix | PASS (offline) | All 120 authored EN/VI/accentless variants execute through the normalizer contract with period-preservation and comparison assertions. Full backend, frontend, browser, HTTP/SSE baseline, migration/lock, publisher, trace-parity, IME, theme, and performance evidence is green; unchanged backend-only gates retain their prior receipt. |
| Provider A | Evidence Contract v3, max 60 calls | PASS / GO | Fresh key5-only `evidence_contract_v3_window_07_key5` completed at `48/60`; calibration passed, both replicates passed, legacy comparison completed, and `candidate_decision=GO`. `window_05_key5` was stopped at 21/60 after an accidental five-key launch; `window_06_key5` was closed at 36/60 after a runner bug, and neither is resumed. |
| Provider B | Bilingual campaign, max 60 calls | FAIL / NO-GO | Fresh key5-only `bilingual_evaluation_v1_window_06_key5` completed `52/60` with zero transport errors, but both replicates failed semantic gates (dependency/risk and language/period cases). This is a quality NO-GO, not a quota interruption; do not spend calls selecting a better replicate. |
| P11 | Docker candidate receipt | PASS (previous candidate) | Existing one-worker/local-Qdrant receipt is valid for its recorded source; rebuild only if backend/build inputs change. |
| P12 | Docs, review, CI, PR handoff | PASS | README, plan, and journal are updated; frontend `107/107`, browser `106/106`, backend `718 passed`, compileall, lint, and production build are green. Branch `codex/bilingual-research-workspace` is pushed at the final handoff commit; Backend CI #73 and Frontend CI #44/#45 passed. PR #3 remains open; do not merge or deploy. |

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
queries and enforces p95 < 200 ms. The production-build browser measurement is
now also green for the same fixture: p95 `42.69 ms` in Chromium and
`54.08 ms` in Firefox.

## Provider accounting and resume policy

- Reserve one ledger slot before every transport attempt. Retry, timeout, 429,
  and unknown outcomes consume the reserved slot; SDK retries remain disabled.
- Campaign A and B are each capped at 60, with the original round shared cap of
  120. The explicit 2026-09-07 user override permits fresh key5-only campaigns
  beyond that historical cap until provider quota stops them; campaign IDs do
  not reset a ledger and closed incomplete ledgers are never resumed.
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
- Fresh key5-only Provider A `evidence_contract_v3_window_07_key5` completed
  `48/60` calls with calibration, two replicates, legacy comparison, and
  reproducibility all complete; its candidate decision is `GO`. Earlier
  `window_05_key5` was stopped at `21/60` after an accidental five-key launch,
  and `window_06_key5` was closed at `36/60` after the legacy runner bug; neither
  incomplete ledger is resumed.
- Fresh key5-only Provider B `bilingual_evaluation_v1_window_06_key5`
  completed `52/60` calls with zero transport errors, but its two replicates
  failed semantic bilingual gates, so its candidate decision is `NO-GO`. This
  is a quality result, not a quota stop; no best-of retry was made.
- Across this continuation, the recorded provider slots are `226`: the prior
  `69` slots, accidental five-key `21`, Provider A `window_06_key5` `36`,
  Provider A `window_07_key5` `48`, and Provider B `window_06_key5` `52`.

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

The final local CI handoff for source `4c26727f50741777ffe8923e1e8bb843fbe1df44`
passed Backend CI #73 and Frontend CI #44/#45. The docs-only finalization below
does not change runtime inputs; the completion manifest is regenerated after
that final commit.

Current state: `OFFLINE WORKSPACE CLOSURE / PROVIDER VALIDATION MIXED`.
Implementation, theme cleanup, the full 120-variant acceptance freeze, guided
portfolio route, and production Library p95 are green. Provider A is `GO`;
Provider B is complete but `NO-GO` on semantic bilingual gates. The official
benchmark and canonical corpus/index remain unchanged.
