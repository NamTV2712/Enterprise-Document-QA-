# UX-AGENT-001 final receipt

Date: 2026-10-02. Main-only starting HEAD:
`f607d2a56073555269fb619218678b5715ea8517`.
The final commit is resolved by `git log -1 --format=%H -- docs/UX_AGENT_001_FINAL_RECEIPT.md`.
Exact final verification, push equality and Backend CI run ID are reported in the closing report.
Release is complete only after those gates pass.
Implementation commit: `2ff9d08d34f902b7be5c578956d7aeb15ab14604` —
`feat(research): unify Quick and durable Agent conversations`.

## Product and execution boundaries

Before, Chat, Research and Agent were separate primary user-facing concepts.
Research is now the primary conversation workspace, with **Quick** selected by
default and an explicit **Deep Research** choice. `/chat`, `/research`, saved
conversation links and browser Back/Forward remain compatible. `/agent` and
`/agent/runs/:runId` retain the full advanced inspector.

Quick uses the existing RAG stream/decomposition, submitted scope, partial-answer
cancellation, citations, focused source reader, follow-ups, saved variants and
persistence. The former comparative-answer switch is labeled Comparative answer
so it cannot be confused with durable Agent execution.

Deep Research submits only the visible, trimmed goal and locale to the existing
generic `POST /agent/runs`. It does not pass Quick filters, previous answers or
hidden history, invent structured objectives, or issue a Quick answer request in
parallel. A configured decision provider requires explicit permission for this
run. Mode, conversation and connection lifetime changes revoke that permission;
an accepted attempt clears it. A provider-unconfigured workspace can create the
existing truthful unavailable run. Navigation never grants execution permission.

**Research deeper** fills the original completed Quick question into the visible
Deep Research composer and focuses it. A separate explicit submission is required.
There is no automatic cross-engine memory or automatic provider execution.

## Message, persistence and authority

Legacy messages without an execution discriminator remain Quick messages.
The optional discriminator is `quick_answer` or
`agent_research { runId, createdAt }`. An Agent message has only its message ID,
assistant sender, empty text and that reference. It contains no cached answer,
state, revision, events, evaluation or private result payload.

Conversation record schema advances **4 to 5**. Storage envelope version 4,
IndexedDB version 2 and existing storage keys remain unchanged. Records v1–v4
migrate without changing Quick meaning; future records remain protected from
older writers. Frontend JSON/Markdown/workspace exports project the same closed
reference. Import preserves the exact run ID while remapping conversation/message
identity. The existing workspace-transfer validator accepts safe v4/v5 records
and rejects malformed run IDs, extra Agent reference fields and cached payloads.
This is compatibility validation, not a DB migration or new endpoint.

DATA-004 remains authoritative for Agent state, result, events, evaluation and
revision. A successful create is linked once to its captured origin conversation,
including a late response after navigation. Deterministic message IDs and run-ID
deduplication prevent duplicate cards. Deleted conversations are not resurrected.
An older queued Quick snapshot retains accepted Agent exchanges; a late repository
refresh cannot replace a newer draft or navigation intent.

Reload without a bearer shows reconnect-required state. Reconnecting reads the
same run ID and never creates a replacement. A 404 retains the reference and shows
unavailable. There is no automatic Quick fallback or retry of provider execution.
Creation/link failures retain the draft and instruct the user to inspect the
Agent workspace before a manual retry; browser persistence and server acceptance
are separate operations, not a distributed transaction.

## Lifecycle and evidence

One accepted run renders one stable Agent card through queued, running,
cancelling and succeeded/failed/cancelled/interrupted states. Existing session
generation, request ownership, abort and SSE deduplication/resumption guards are
reused. The card does not list all runs. Compact activity uses closed tool labels
and distinct evidence-reference counts; cancellation uses the current revision
and reconciles a 409 before another explicit cancel attempt.

The terminal answer appears once, with existing document/chunk reader access and
a small summary. Generic goals truthfully have no structured objective coverage
or gap report. Structured historical runs reuse their server summary. Collapsed
details reuse safe activity/research/evaluation sections and a full-run link;
their heading IDs are unique per message. The advanced inspector remains intact.

## Security

The shared local-workspace bearer is memory-only. The connection password input
is cleared before awaiting verification. Consent is not persisted. No token enters
localStorage, sessionStorage, IndexedDB, URL, text DOM, conversation export or
workspace backup. The browser journey inspects actual storage after connection,
create, persistence, reload and reconnect with a synthetic token sentinel; it
also checks the exact closed reference keys. Export/import unit tests exercise
poisoned cached result/event/credential fields. All tests are hermetic; no live
Groq quota or live provider calls were used.

## Required behavioral coverage

| # | Behavior | Evidence |
| --- | --- | --- |
| 1 | Quick default | Conversation hook and production browser |
| 2 | Explicit Quick/Deep mode switch | Hook consent resets; EN/VI keyboard matrix |
| 3 | Quick sends RAG only | Unified browser journey; existing App stream tests |
| 4 | Deep creates exactly one run without parallel Quick | Double-send hook assertion; exact browser POST body |
| 5 | Exact run-ID message link | Library origin-link tests; browser card/reference audit |
| 6 | Queued/running/terminal | Browser fixture advances the same run |
| 7 | One card/result per run | Browser counts card and terminal answer; link deduplication |
| 8 | Revision cancellation | Browser checks If-Match 3/4 and conflict reconciliation |
| 9 | Late run/event isolation | Existing Agent hook ownership tests; new origin navigation/revocation tests |
| 10 | Restore without bearer | Browser reload requires reconnect |
| 11 | Reconnect same ID | Browser rehydrates without another create |
| 12 | 404 retains reference | Browser removes server fixture, reconnects and audits storage |
| 13 | Legacy conversation | Existing v1–v4 migration/library/browser cases |
| 14 | Quick persistence | Existing library/store/App suites and partial normalization test |
| 15 | Safe Agent reference persistence | Poisoned projection tests and real browser storage audit |
| 16 | Safe export | JSON/Markdown/workspace projection and backend reject tests |
| 17 | Explicit Research deeper | Browser checks populated question and zero creates before submit |
| 18 | Open full run | Browser exact Agent run route and Back |
| 19 | `/chat` and `/research` compatibility | Cancellation journey on `/chat`; unified journey on `/research`; route tests |
| 20 | Direct advanced Agent inspector | Existing Agent unit/browser/local harness suites |
| 21 | EN/VI compact UI | Two-browser 7-width × 2-locale × 2-theme matrix; VI phone card |
| 22 | Keyboard mode/details | Enter selects mode with retained focus and opens native details |

## Reproduced defects and bounded repairs

- A late repository refresh overwrote a newer Research deeper draft. Recheck
  draft/message identity, operation epoch and pending local intent after the read.
- A queued older Quick snapshot dropped an accepted Agent reference. A regression
  first failed, then passed after retaining missing accepted exchanges.
- The new composer height made fixed follow-up tiles obscure citation controls
  at narrow reference widths. Put those existing tiles inside the conversation
  scroller, make the Quick hint accessible without consuming visual height, and
  show the existing expired-session notice once. Existing citation and shell
  geometry expectations pass without changing budgets or expected pane modes.
- Two existing dark overview text colors had 3.15/3.16 contrast. Reuse the existing
  accent-text token for those labels. No global token or contrast-threshold change.
- One VI phone fixture initially used a URL parameter that does not select the
  product locale. Seed the existing locale preference; both browsers then pass.
- A held create response redirected newer Search navigation back to Research.
  The new browser regression failed on both engines before the fix. Bind the
  optional post-create navigation to current browser history, and check the actual
  browser URL before the existing history-adoption effect opens a conversation.
  Retain the safe run reference in its origin. A React location ref alone was
  insufficient during a suspended route: the 1960d03 candidate had 541 passes,
  four existing skips and one Chromium late-navigation failure. A deterministic
  barrier now holds both the POST and Search module; the previous compiled code
  fails on both engines. Both barriers are released in finally. After the complete
  browser-history/URL fix, all 22 UX cases pass, including the suspended-route case.

An interrupted full browser attempt is excluded. A completed earlier candidate
had 548 passes, four existing skips and six failures: two outdated Chat-primary
navigation assertions, two citation obstructions and two shell geometry failures.
The navigation expectations follow the deliberate primary-navigation change;
the real layout defects were repaired. The focused repair candidate had 58
passes and two VI fixture failures; the corrected UX suite has 20 passes.
No test timeout, retries, CI budget, performance budget or skip was weakened.

A further complete four-worker browser candidate had 554 passes, four existing
skips and two input-performance failures: Chromium 200-message p95 100.70ms and
Firefox warm-input p95 125ms against the unchanged 100ms budgets. A heavy backend
import probe overlapped the latter case; contention is plausible but not proven,
and cannot explain the earlier Chromium case by itself. Both performance cases
and the corrected PDF output paths then passed in an isolated one-worker run
(six cases across both browsers). Final full-matrix verification uses the
existing workflow's one-worker setting; no product/performance-budget workaround
or automatic retries were introduced.

The preservation audit found an existing PDF browser test wrote three fixed
screenshots into the unrelated `frontend/.audit-runtime/` directory. Those
`pdf-viewer-{1440x900,1920x1080,720x900}.png` files no longer match their initial
hashes. No original copy was found among 1,189 local PNGs. The test now uses
Playwright's per-test `outputPath`, preserving assertions, budgets and coverage.
The user explicitly accepted this three-diagnostic-file exception on 2026-10-02.
All other baseline files retain their original hashes.

## Validation and release gates

| Gate | Result |
| --- | --- |
| Baseline | Backend 1949; clean 1915 + 34 skips; frontend 94 files / 819 tests |
| Backend workspace-transfer focused | 24 passed |
| Primary full backend | 1958 passed / 188 warnings / zero failed; 178.59s |
| Frontend focused | 114 passed; new library race suite 14 passed |
| Primary frontend TypeScript / full unit / build | PASS / 96 files, 843 tests PASS / PASS |
| Build warning | Final main chunk 527.28 kB (implementation 527.07 kB); warning retained |
| New UX production Chromium/Firefox | Expanded final suite 22 passed; all seven required widths in EN/VI light/dark |
| Token contrast | PASS, unchanged thresholds |
| Isolated performance / PDF output regression | 6 passed, one worker, both browsers |
| Complete implementation-SHA regular browser matrix | 540 passed / 4 existing skips / zero failed, one worker, 17.8m |
| Complete final-SHA regular browser matrix | Required after the suspended-route fix; literal result in closing report |
| Real HTTP/SSE | 16 passed, Chromium/Firefox, real FastAPI and fragmented SSE proxy |
| Existing Agent shell sweep / local product harness | 32 passed, Chromium/Firefox |
| Durable Agent product harness | 12 passed, Chromium/Firefox; real Agent routes, events, evaluation and cancellation |
| Exact-final clean backend | Full suite required; literal SHA/counts in closing report |
| Exact-final clean frontend | Frozen install, TypeScript, full unit and build required; closing report |
| Implementation-SHA clean backend | 1924 passed / 34 artifact-dependent skips / 149 warnings, 103.50s |
| Implementation-SHA clean frontend | Frozen install / TypeScript / 96 files, 843 tests / production build / token contrast PASS |
| Import/public startup/route/SQLite/worker checks | Required final gates; closing report |
| Preserved-file/secret/artifact audit | Required final gates; closing report |
| Exact-final GitHub Backend CI | SUCCESS required; exact SHA/run ID in closing report |
| GitHub Frontend CI | Explicitly waived by the user for UX-AGENT-001 on 2026-10-02 |

The user's instruction **“có thể bỏ CI frontend”** is a new waiver for this task.
It overrides the original UX-AGENT-001 GitHub Frontend CI success requirement;
the historical CAPACITY waiver is not carried over. Local frontend, browser,
HTTP/SSE and Agent harness gates remain required. Frontend workflow configuration
is unchanged. A waived/incomplete/failed CI run is never reported as successful.
Backend workflow gains only this receipt in its push/PR path filters so final
documentation triggers the unchanged full Backend CI gate.

The first local HTTP/SSE attempt aborted during the production build with a
Windows Node/libuv `UV_HANDLE_CLOSING` assertion, before any test ran. A fresh
unchanged invocation completed all 16 cases. The aborted attempt is retained
as an infrastructure failure, not a passing integration run.
A later regular-suite startup at 1960d03 encountered the same Windows native
assertion before any browser test. Its log is separate from the completed 541/1/4
candidate above. Standalone builds and subsequent fresh startup pass; no runtime,
timeout, retries or workflow change is used to conceal either startup abort.

The implementation-SHA detached checkout contains neither `.env` nor `data/`.
It uses the declared-requirements environment (Pydantic 2.10.0), separate from
the primary environment (2.13.4). Clean and primary full backend suites run
serially. Compile/import checks and offline observations confirm 90 method/path
pairs, no worker at import/public startup, v7/WAL/NORMAL/5000ms and native worker
validation for all 1–16 values with invalid values rejected. The full backend
suite also covers the real public/local application lifespan with offline model
boundaries, readiness, index creation, cleanup and public DB refusal.

Primary browser candidates include 16 cases from the unchanged unrelated
untracked visual-capture spec. The source-clean browser gate naturally excludes
that uncommitted file and ran all 544 committed cases before the late-navigation
regression was added (546 final cases); no test filter or skip
was added to achieve this difference.
Those untracked capture cases generated screenshots in their preconfigured
external diagnostic directory. They are not committed or used as authoritative
clean-gate evidence; the final source-clean run does not execute that local script.

No dependency or lockfile changes, endpoint additions, DB migration/index changes,
retrieval/planner/provider algorithm changes or worker-policy changes. Routes stay
**90 method/path pairs** (80 distinct paths), SQLite **v7 / WAL / NORMAL / 5000ms**,
worker default **2**, supported hard range **1–16**, ordinary recommendation **1–2**.
New source files are the conversation Agent hook/card, mode/connection/copy/style
components, execution-reference helper, two focused test files and one browser
spec. Modified files are existing App/composer/shell/Agent/library/store/export/
backup contracts, relevant expectations and the workspace-transfer validator/tests,
plus README, ARCHITECTURE, frontend design/contract, PROJECT_STATE, the existing
scaling roadmap, backend receipt filter and task-only ignore rule. Deleted files:
none. No AGENTS.md change.

The same 12 unrelated paths retain their untracked status. Of the 1,694 baseline
files, 1,691 match their original hashes; the three PDF screenshots above are the
disclosed exception. `.env`, `data/`, historical worktrees and prior capacity
artifacts remain unchanged. The audit excludes only the task-owned new
`.audit-runtime/ux-agent-001/` subtree. Raw logs, screenshots and diagnostics remain
ignored. Normal commits/push on main only; fresh fetch
must show the last own remote SHA before each push. No force push/history rewrite.

## Limits and stop boundary

Deep receives only its explicit goal; no hidden conversation memory. Generic
goals have no structured objective-gap report. Server access is required after
reload; a deleted/unavailable server run cannot be reconstructed from the browser.
Native zoom remains manual/unverified. Collections and model-test browser bearer
integration remain staged; Ragas remains optional. Existing backend warnings and
the increased bundle warning remain. No live-provider capacity/SLA claim.

Required roadmap and prior optional milestones stay COMPLETE. **UX-AGENT-001 is
COMPLETE once the exact-final release gates above pass; FINAL-IMPROVE is NEXT.**
Do not start FINAL-IMPROVE, SCALE-003, another UX/performance task or deployment.
