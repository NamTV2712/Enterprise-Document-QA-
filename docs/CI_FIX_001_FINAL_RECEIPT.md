# CI-FIX-001 release receipt

Date: 2026-10-01. Branch: `main`. Scope: CI contract determinism only.
Starting SHA: `eb962e8acd4f5a94dff3d49713a9bc5f27ea499b`.
Fix SHA: `21537c1479c73a9933c80e8ec126ee34bdd94e8e`
(`fix(ci): stabilize backend and frontend release contracts`).
Browser correction SHA: `8b28b76604bfc0e04df68223438dec6724c7716f`
(`fix(ci): correct browser suite ownership and timing checks`).
The final release SHA is the remaining-fixture and receipt closure commit containing this
receipt. Its literal SHA, exact-SHA run IDs/conclusions, clean-checkout results
and push equality are recorded in the closing report after committing it.
This receipt cannot contain its own Git object ID. That final gate is mandatory.

## Fresh starting-SHA GitHub evidence

| Workflow | Run / job | Result |
| --- | --- | --- |
| [Backend CI](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/runs/36838503344) | 36838503344 / test 110291634616 | FAILURE: 1884 passed, 34 skipped, 1 failed, 149 warnings |
| [Frontend CI](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/runs/36838503350) | 36838503350 / test 110291635015 | FAILURE: 93 files / 817 tests passed; one cancellation test failed |
| Frontend HTTP/SSE | Same frontend run / http-integration 110291634573 | SUCCESS |

Backend used Ubuntu 24.04 image `20260920.314.1`, CPython 3.12.14,
CPU-only Torch install followed by `pip install -r requirements.txt`,
`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, and `pytest tests/ -v`.
Frontend used Ubuntu 24.04 image `20260927.320.1`, Bun 1.3.14,
frozen lockfile install, TypeScript, then Vitest. Browser/build steps were
blocked by the unit failure. Both workflow files and all their jobs were audited.

Backend failure: `tests/test_api_router_contracts.py::test_moved_openapi_operations_match_the_pre_extraction_contract`.
Expected digest `5c4098c68832465a2e8db8f3fc6441cb4ce777399d2711976a20145ebf35ae16`;
CI actual `860e11b1afee213e3d467247a26269d38bc6feeedd64538c4e174db6e7d9c73f`.
Frontend failure: `src/App.test.tsx`, "changing routes while a request is pending
aborts the stream and ignores late events", original line 487: unable to find
"Partial before route change", before any navigation assertion.

## Backend cause, structural diff and fix

| Package | Declared | Primary Windows environment | Fresh Windows requirements environment | GitHub starting run |
| --- | --- | --- | --- | --- |
| Python | Workflow 3.12 | 3.12.7 | 3.12.7 | 3.12.14 |
| FastAPI | 0.115.0 | 0.115.0 | 0.115.0 | 0.115.0 |
| Pydantic | 2.10.0 | **2.13.4** | 2.10.0 | 2.10.0 |
| pydantic-core | Pydantic dependency | **2.46.4** | 2.27.0 | 2.27.0 |
| Starlette | FastAPI dependency | 0.38.6 | 0.38.6 | 0.38.6 |
| httpx | Transitive | 0.28.1 | 0.28.1 | 0.28.1 |
| pytest | 9.0.3 | 9.0.3 | 9.0.3 | 9.0.3 |
| AnyIO | Transitive | 4.14.1 | 4.15.1 | 4.15.1 |

The primary environment differs from declared Pydantic. Fresh installation
reproduced the Linux raw digest on Windows; this difference follows dependency
versions rather than platform. There is no repository `pyproject.toml`.
Docker's daemon was unavailable; no Linux infrastructure was introduced.
GitHub provides the authoritative Linux validation.

The structural comparison covers the entire selected contract after its existing
verified additive `complete` status-filter normalization. Exactly 14 differences
occur, all at `responses.200.content.application/json.schema.additionalProperties`:

| Path | Method | Primary 2.13.4 | Declared/CI 2.10.0 |
| --- | --- | --- | --- |
| /cache/clear | POST | true | omitted |
| /cache/stats | GET | true | omitted |
| /cache/test | POST | true | omitted |
| /evaluation/runs | GET | true | omitted |
| /evaluation/runs/{run_id} | GET | true | omitted |
| /health | GET | true | omitted |
| /health/live | GET | true | omitted |
| /health/ready | GET | true | omitted |
| /metrics | GET | true | omitted |
| /session/{session_id} | DELETE | true | omitted |
| /session/{session_id}/history | GET | true | omitted |
| /supported-tickers | GET | true | omitted |
| /system/configuration-status | GET | true | omitted |
| /system/info | GET | true | omitted |

Every difference is a **non-semantic representation change** for these bare
object response schemas: omitted and true both allow extra properties.
[JSON Schema's reference](https://tour.json-schema.org/content/03-Objects/02-Additional-Properties)
defines that default. No path, method, parameter, requiredness, request body,
response status/type/field, ref, title, or security declaration differs.

Choose Option B: normalize only an omitted `additionalProperties` on a direct
object response schema to true in the test representation. Keep false and typed
extra-property schemas, every other field, and the **original** operation digest.
No dependency adjustment or runtime OpenAPI rewrite is needed. Freeze the three
transitively referenced schemas (`CacheTestRequest`, `HTTPValidationError`,
`ValidationError`) as well, so unchanged ref names cannot hide changed fields.
They are identical in both environments; no unrelated OpenAPI fixture is stored.

Twelve focused cases cover the observed equivalence and rejection of changed
path, method, parameter location, requiredness, request body, response status,
type/field, closed or typed extra properties and operation security. The main
fixture assertion also protects referenced request/response fields and constraints.

## Frontend cause and fix

The test confused health readiness with completion of the independent initial
session-history check. Instrumented failures showed an **enabled** send button,
unchanged submitted draft, **zero** stream calls, no signal, and two history calls.
Clicking during `sessionContext=checking` invoked the send preflight; the mock's
empty history correctly classified that preflight as missing and blocked sending.
The expected token had never been emitted. This is a fixture synchronization race,
not evidence of a delayed token flush or a broken abort implementation.

Control the initial history promise, await its invocation, resolve it inside
React `act`, and await that settlement before submitting. Await enabled sending,
assert one entered stream and a visible partial answer, navigate to Research,
and verify the real signal abort. Deliver late token, done, stream-error and
error-callback events explicitly; await the mock's completion inside `act` before
checking absence, route identity and idle request state. No optional callback can
make the late-event assertion vacuous. No sleep, increased timeout, skip or retry
was added. Production frontend and backend implementations are unchanged.

## Stability and local validation

| Gate | Result |
| --- | --- |
| Original cancellation test, 20 isolated runs | 19 pass / 1 fail; normal 9/10, CI flag 10/10 |
| Instrumented diagnosis, 20 isolated runs | 18 pass / 2 fail; both zero stream calls |
| Original normal parallel frontend suite | 94 files / 818 tests PASS |
| Fixed cancellation test, 50 runs | 50/50 PASS; normal 25/25, CI flag 25/25 |
| Uncached OpenAPI generation, primary | 20/20 PASS; one original canonical digest |
| Uncached OpenAPI generation, fresh requirements | 20/20 PASS; identical operation and referenced-schema digests |
| Router contract suite | Primary 22 passed / 1 warning; fresh 22 passed / 2 warnings |
| API/security/cross-layer/Worker/DB/CRED/provider regressions | 569 passed / 5 inherited warnings |
| Three full frontend runs | Each 94 files / 818 tests PASS; includes CI flag and normal parallel workers |
| Primary frozen install / TypeScript / production build | PASS |
| Built browser journey, Chromium + Firefox, retries=0 | 76 passed; actual light desktop and dark mobile screenshots inspected |
| Full primary backend | **1931 passed / 188 warnings**, zero failures |
| Fix-SHA clean backend, fresh declared environment | **1897 passed / 34 expected skips / 149 warnings**, zero failures |
| Fix-SHA clean frontend | Frozen install, TypeScript, serial full 94 files / 818 tests, build PASS |
| Import / compile / routes / fresh + reopened SQLite | PASS; 90 unique routes, v7/WAL/NORMAL/busy5000/integrity ok |

The first cold clean frontend run overlapped fresh backend validation and had an
inherited history-navigation test exceed its existing 5000ms budget (6344ms);
the fixed cancellation test passed. Preserve this negative result. The history
test passed 20/20 isolated investigations; a normal full suite after backend
completion passed, with that test at 1729ms. Aggregate jsdom environment time was
188.13s in the overlapping cold run versus 85.94s in the serial run. Resource
contention is a plausible explanation, not a proven product root cause. No
history-navigation test, timeout, worker setting or workflow retry was changed.
Exact final documentation HEAD receives its own clean suites and Linux CI gate.

## GitHub release evidence

Fix SHA `21537c1479c73a9933c80e8ec126ee34bdd94e8e`:

- [Backend CI 36843208943](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/runs/36843208943): SUCCESS; test job 110306934411, 1897 passed / 34 expected skips / 149 warnings; compile PASS.
- [Frontend CI 36843208925](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/runs/36843208925): FAILURE; unit 94 files / 818 tests, TypeScript, build and contrast PASS; HTTP/SSE job 110306934571 SUCCESS. Browser job 110306934910 exposed 35 additional failures: 515 passed / 35 failed / 4 inherited skips, 554 cases, 27.2 minutes. Existing browser retries did not resolve the failures. This failed candidate is retained as negative evidence.

Browser correction SHA `8b28b76604bfc0e04df68223438dec6724c7716f`:

- [Frontend CI 36848939269](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/runs/36848939269): FAILURE. Test job 110325747432 had 92 files / 816 tests pass and two additional fixture failures described below; the repaired cancellation passed. HTTP integration job 110325747687 SUCCESS: **16 HTTP/SSE cases plus 32 dedicated Agent sweep cases passed**. Browser tests were blocked by units. No failed job was rerun.
- Backend CI does not trigger for these browser-only paths. The backend tree is
  identical to accepted backend SHA `21537c1`; this does not substitute for the
  required final exact-SHA Backend CI gate.
- Committed clean frontend: frozen install, TypeScript, **94 files / 818 tests**,
  production build PASS after the owned diagnostic archive described below.
- Push verified local/upstream/remote equal to the full browser-correction SHA,
  ahead/behind **0/0**.

The final documentation SHA independently receives both complete workflows.

Both workflow path filters now include this receipt. Previously a documentation
closure push could have no exact-HEAD checks. The four path-filter entries fix
that release-gate omission without changing install commands, action versions,
caches or concurrency. The frontend HTTP job also receives the correctly owned
Agent browser suite described below. After recording accepted
fix-SHA results here, the documentation commit must independently reach SUCCESS
for **both complete workflows**. No rerun of failed jobs masks a failure.

## Additional browser blockers and bounded corrections

The repaired unit tests allowed the previously blocked browser suite to run in
full. Its 35 failures have three reproduced causes:

1. **32 Agent shell sweep cases used the wrong harness.** The default Playwright
   configuration discovered `agent-001-sweep.spec.ts` but served port 4173. The
   sweep deliberately allows the dedicated preview at 4177 and fixture backends
   at 8777/8778, so its request guard rejected the wrong preview origin. Keep these
   cases in the existing `playwright.agent-sweep.config.ts`, add the filename to
   the default configuration's dedicated-suite exclusion, and run the dedicated
   configuration as a mandatory step in CI's HTTP integration job. The job
   already installs the required Python harness and both browsers. All 32 cases
   remain required, provider-free and locally passed with **zero retries**.
2. **Two canonical sidebar assertions omitted the accepted Agent route.** Both
   browsers returned exactly the expected route order plus the existing `agent`
   entry between Pipeline and Reranker. Add that entry to the exact-order
   expectation; both focused cases passed with zero retries. No route/UI changes.
3. **One Firefox warm-navigation gate measured assertion backoff.** GitHub p95
   was 242ms (252ms on its existing retry), versus the unchanged 200ms budget;
   Chromium was 126.5ms. Ten local recorded trials reproduced one failure
   (236.5ms), and ten trials without recording also reproduced one (222.3ms).
   Removing trace/video was therefore rejected as a fix. The preserved failing
   trace showed 13 visibility assertions lasting about 95-113ms, while native
   clicks were mostly below 30ms. Playwright's installed assertion implementation
   retries with 20/50/100ms backoff, so the measured elapsed time included polling
   delay after the rendered condition became available.

For the third case, await the same positive-size/visible element condition with
browser animation-frame polling immediately before each existing explicit
visibility assertion. Native clicks, both route conditions, 30 samples, p95
calculation, the 200ms budget, endpoints, trace and video remain unchanged. The
10s wait bound matches the existing suite assertion timeout. There are no sleeps,
new retries or larger budgets. Twenty recorded trials (10 per browser) passed
with zero retries, p95 range **79.10-141.00ms**. A separate experimental paint
probe was unstable and rejected; no paint-speed improvement is claimed. This
corrects the test measurement, not production performance.

The regular suite now owns 522 cases (including four inherited provider-dependent
skips); the dedicated Agent suite owns 32. The original 554-case population is
preserved across the required jobs. Production behavior and dependencies are
unchanged. TypeScript and production builds passed after these test/config edits.

The browser-correction clean validation initially discovered an ignored,
task-owned experimental Playwright probe under `frontend/.local` as a Vitest
suite. Its 818 product tests passed; only that diagnostic file failed to load.
Archive the three owned probe files outside the checkout before the clean gate.
No tracked test or discovery configuration was changed to hide the mistake.

## Remaining unit fixture races exposed by Linux

The second pushed candidate above exposed two more asynchronous test assumptions.
These are retained as release failures, not described as green:

- Pipeline's connection status becomes ready before its run-list response. When
  the empty list renders first, both the header and empty-history section
  intentionally offer `Stage run`; an unscoped single-button query fails. This
  reproduced in **7 of 10** local CI-flag runs of the two affected suites (28
  tests each), including the double-submit case sharing the same assumption.
  Await the `No staged runs yet` heading, then address the button within that
  empty-history section. Double-submit and backend-refusal assertions remain.
- Discovery's submit helper awaited only the API mock call count. Invocation is
  synchronous, while response processing and React snapshot rendering are
  asynchronous; Linux reached the article query while still showing the loading
  state. Await the search button's return from `Searching...` to `Search`, which
  occurs after success or refusal settles. All result identity, snippet, score,
  paging, failure and request-count assertions remain. No production change.

Both corrections synchronize on existing rendered states. No timeout, sleep,
retry, worker or test-count change is introduced. **20/20 affected-suite runs
passed** after these corrections (28 tests each, CI flag); **three additional
full frontend suites each passed 94 files / 818 tests**. TypeScript and production
build passed. Together with the initial repair, six post-fix full frontend suites
passed; no whole-suite rerun was used to mask a failure. The final committed
checkout receives its own serial backend and frontend validation.

## Files, preservation and remaining limits

Modified: `.github/workflows/backend.yml`, `.github/workflows/frontend.yml`,
`frontend/src/App.test.tsx`, `frontend/playwright.config.ts`,
`frontend/src/components/PipelineConsole.test.tsx`,
`frontend/src/components/search/DiscoverySearchPage.test.tsx`,
`frontend/e2e/reconciliation-reference.spec.ts`,
`frontend/e2e/workspace-performance.spec.ts`, `tests/test_api_router_contracts.py`, `README.md`,
`PROJECT_STATE.md`. Added: `tests/fixtures/moved_openapi_schemas.json`, this receipt.
Deleted: none. Three coherent commits: the initial contract fix, the newly exposed
browser gate corrections, and remaining fixture synchronization with release
evidence. The first two fix SHAs are above; the final SHA is in the closing report.
Full diagnostics/environments/logs remain ignored under `.local/ci-fix-001/`.
The task-owned detached clean checkout is removed after final validation;
the historical TEST-004 worktree remains untouched.

Requirements, Bun lockfile/package manifest, migrations, `.env` and `data/` are
unchanged. Only explicitly owned files are staged. Tracked/staged tree closes
clean; the same 12 unrelated untracked paths remain untouched. Their file hashes
and `.env` hash were checked without printing secret contents. No provider call,
secret literal, generated diagnostic, cache, environment or build output is
committed. Full backend suites run serially.

Worker defaults stay 2/500/5000; SQLite durable authority, payload-free hints,
claim order/poll/cancel/restart/shutdown and DB guarded initialization/snapshots/
writer serialization remain intact. Agent provider one-attempt/max_retries=0,
historical primary-only key policy and generator bounded fallback remain intact.

Warnings: primary 188 unchanged; fresh declared clean 149 equals the starting
Linux population. AnyIO 4.15.1 adds the Starlette alias deprecation absent from
primary AnyIO 4.14.1; artifact-dependent skips remove the other warning difference.
ReportLab, BeautifulSoup/lxml and Requests dependency warnings remain. Existing
Node 20 action deprecation/runtime warnings did not cause either failed test;
action upgrades are outside this repair. The current main build warning is
508.63 kB. Collections/model-test browser bearer staging, native zoom manual/
unverified and optional Ragas remain inherited limitations.

Roadmap: CI-FIX-001 release fixes are locally validated. Completion requires the
final exact-SHA gates documented in the closing report. **CAPACITY-001 is NEXT**;
UX-AGENT-001 and FINAL-IMPROVE are NOT STARTED. Required roadmap and previously
completed optional work remain complete. No next task is implemented. STOP after
the final release gate succeeds.
