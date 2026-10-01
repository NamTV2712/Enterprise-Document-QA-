# FINAL MASTER EXECUTION PLAN — SEC RAG WORKSPACE

## 1. Authoritative scope and supersession rules

This MASTER PLAN is the authoritative specification for **remaining work**. Goal mode must use:

1. This plan.
2. `docs/implementation-progress.md`.
3. Current repository.
4. Current git status/diff.

Previous plans remain historical references, not competing execution instructions.

This plan:

- Preserves completed PLAN V2 functionality.
- Replaces conflicting navigation, evidence-layout and validation instructions.
- Incorporates unfinished template and contextual-command safeguards.
- Adds incremental frontend/backend verification.
- Does not authorize production implementation during this planning turn.

Preserve existing B IDs. Newly identified work uses unused appended IDs. Do not renumber historical P/A tasks.

Use these path aliases throughout this specification:

- `R`: `D:/Project/Enterprise_Document_QA`
- `F`: `D:/Project/Enterprise_Document_QA/frontend`
- Component paths beginning `components/` resolve under `F/src/`.
- Hook and library paths resolve under `F/src/hooks/` and `F/src/lib/`.

The implementation agent should save this approved plan as:

`R/docs/frontend/FINAL_MASTER_EXECUTION_PLAN.md`

No such file was created in this planning turn.

## 2. Current verified repository state

### Current binding and evidence

- HEAD inspected: `c3ccc51`.
- Existing dirty implementation remains present across App, components, styles, tests and checkpoint.
- Existing untracked files, including `harness_stacks.txt`, must be preserved.
- `git diff --check` passed.
- Fresh focused tests: **4 files, 11 tests passed**:
  - Navigation preference.
  - Template dialog.
  - Command palette.
  - SearchWorkspace.
- No listener was found on checked ports 3000, 4173, 8000, 8765 or 8766 during this review.
- Settings inspection reported only safe facts:
  - `GROQ_API_KEY5` present.
  - Qdrant mode: local.
  - Local store exists.
  - Proposed local production-preview origin `http://localhost:4175` is not currently allowed.

### Prior-turn evidence retained, not presented as newly rerun

- Production Chromium targeted tests: 3 passed.
- Library search p95: 54.13 ms, 100 samples.
- 200-message composer p95: 32.20 ms, 100 samples.
- HTTP/fragmented-SSE integration: 14 passed across Chromium/Firefox.
- Browser inspection at 1272 × 587 CSS px reproduced navigation overlay and low-contrast menu.
- Historical full-suite receipts include Chromium twice, Firefox and 737 backend tests.

### Task reconciliation

| Existing task/domain | Status | Decision |
|---|---|---|
| P0–P4 implemented foundations | `[x]` implementation preserved | Do not restart architecture, storage, retrieval or reader construction |
| A01.1 reconciliation | `[~]` | Superseded by B01.1’s current reconciliation |
| A01.2 semantic registry | `[x]` core mapping | Keep registry; finish only remaining tool-header consumers under B04.2 |
| A02.1 interaction tokens | `[-]` | Preserve system; correct confirmed foreground misuse |
| A02.2 palette keyboard model | `[x]` | Preserve; do not rebuild combobox/listbox |
| A03.1 navigation preference | `[x]` | Preserve key and schema |
| A03.2 responsive navigation | `[~]` | B01.2–B01.7 replace conflicting layout requirements |
| A04.1 overview | `[-]` | Ordering exists; remaining copy/density corrections under B04.2 |
| A04.2 explanations | `[-]` | Existing functionality retained; precise semantics under B04.1/B04.2 |
| A05.1 template schemas | `[x]` | Preserve validation/renderers |
| A05.2 template application | `[-]` | Missing conflict validation and parameter-derived scope |
| A05.3 contextual commands | `[-]` | Real callbacks exist; displayed-variant context is incomplete |
| A06.1 persistence race | `[x]` historical verified receipt | Do not restore delayed completion saving |
| A06.2 final closure | `[!]` | Does not establish remaining reflow, integration and actual-zoom gates |
| B tasks from previous extension | `[ ]` | No implementation receipts found |
| Actual browser zoom | `[!]` | Still requires direct verification |
| Local real-backend workflow | `[!]` | Not exercised in this review |
| Bounded live-provider workflow | `[!]` conditional | Run only at the designated gate |

A passing existing test does not prove coverage of newly identified missing behavior.

## 3. Corrections discovered during final self-review

1. **Harness coverage was overstated.**  
   Its normal fake stream emits sources/tokens/done, not the stage-event sequence needed to verify PipelineExecution. Add test-only stage fixtures.

2. **Harness can overwrite a pre-existing file.**  
   `harness_server.py` opens `harness_stacks.txt` under the default working directory. Always supply a task-owned temporary directory.

3. **Integration preview may reuse the wrong server.**  
   Existing integration configuration allows reuse. Isolate test outputs and prohibit unverified reuse.

4. **Template Apply is not conflict-safe.**  
   App directly replaces draft/scope without validating the conversation/draft/scope captured when customization opened.

5. **Template company does not reach scope.**  
   Template scopes contain `ticker: null`; validated company parameters are not passed back to App. Single-company templates must apply the selected searchable ticker.

6. **Palette “current answer” can mean the wrong answer.**  
   App chooses the newest completed message, while selected variants live inside ChatMessage. Introduce a narrow transient displayed-answer context.

7. **Retrieval Lab has a related stale-configuration risk.**  
   It guards request IDs, but controls can change while a request is active; export uses current question text rather than necessarily the trace’s submitted question.

8. **Reader neighbor requests lack explicit cancellation.**  
   `openNearby` calls the cache without a signal. Add task-owned cancellation while preserving shared-cache semantics.

9. **Draft persistence skips streaming.**  
   Simply enabling the textarea does not establish recoverable next-draft behavior. B03.2 must test and complete this boundary.

10. **Header collapse was not executable enough.**  
    This plan specifies exactly which controls remain visible and where others go.

11. **Drawer preservation needs an explicit rule.**  
    Remounting between inline and portal presentation may reset reader state. Preserve selected source and reader navigation state across mode changes without creating duplicate readers.

12. **Backend/frontend connection lacked a CORS/build contract.**  
    Local verification now uses a dedicated production preview, explicit API base, temporary exact-origin allowance and process ownership.

## 4. Locked architecture and product decisions

Keep:

- React, TypeScript, Tailwind, installed Lucide.
- Existing navigation/icon registries and UI primitives.
- Existing state owners, conversation schema and persistence.
- Indexed excerpts—not a complete filing/PDF viewer.
- Existing retrieval, ranking, prompts, provider policy and Qdrant semantics.

Do not introduce:

- Docker/deployment changes.
- New state, query, UI, animation or chart framework.
- New production endpoint.
- New storage architecture.
- Navigation drag-resize.
- Fake data, confidence, coverage, timings or pipeline stages.

Retain the current approved navigation groups. Do not revert them to an older information architecture described in a skill.

### Ownership decisions

- `useNavigationLayout`: persisted desktop expanded/compact preference.
- `App.tsx`: responsive mode, navigation drawer, evidence visibility, selected evidence and displayed-answer context.
- `ChatMessage`: displayed variant selection remains local; reports its display context through a typed callback.
- `ChatInput`/conversation hook: existing draft ownership.
- `ContextPanel`: source/reader presentation.
- `DocumentViewer`: requests and local reader controls, with presentation-state preservation across panel-mode changes.
- Feature owner callbacks perform actions; CommandPalette only dispatches them.

No new `AppShell.tsx` replacement framework is required.

## 5. Runtime/backend operating contract

### A. Inspect before starting

From `R`:

1. Inspect listeners on 8000, 8765, 8766, 4173 and 4175.
2. For occupied ports, inspect PID, executable and narrowly relevant command-line information. Do not dump complete process environments.
3. Reuse a real backend only if:
   - It is the intended project application.
   - Health/readiness and expected API schema match.
   - Its corpus/configuration is compatible.
   - Live-provider policy is known before any generation call.
4. An unfamiliar process or uncertain local-Qdrant owner is a blocker. Do not kill it or start a second store owner.

### B. Environment preflight

Use `R/.venv/Scripts/python.exe` and `configs/settings.py`.

Report presence/availability only:

- Key5 present.
- Qdrant mode.
- Local store available, or configured remote credentials present.
- Model/cache prerequisites available.
- Required preview origin allowed.

Never print keys, connection credentials, `.env`, full settings objects or raw sensitive logs.

The settings loader reads `.env` relative to the working directory; start from `R`.

### C. Diagnostic real backend

Use the normal application entrypoint, without reload:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --workers 1
```

For a task-owned process:

- Set process-scoped `GROQ_KEY_POLICY=key5_only`.
- Preserve configured allowed origins and append exactly `http://localhost:4175`.
- Do not persist either override to `.env`.
- Capture PID/start time and restore parent-shell environment overrides afterward.
- If using `Start-Process`, use `-WindowStyle Hidden`.
- Stop only a PID started and still owned by this execution.

No ingestion, reindexing, migration, collection creation, cache clearing or model download is part of this plan. Missing dependencies are blockers.

### D. Readiness

- `/health/live` 200: process alive only.
- `/health/ready` 200 with ready state: usable pipeline.
- `/health/ready` 503: not ready.
- Startup exception or unavailable dependency: blocked, not “offline test passed”.

Allow up to 180 seconds for existing cached dependencies to initialize, polling at two-second intervals without spawning another instance. Record timeout rather than silently extending it indefinitely.

### E. Local production frontend

Use a separate output directory:

```powershell
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
bunx vite build --outDir dist-local
bunx vite preview --outDir dist-local --host localhost --port 4175 --strictPort
```

Restore the shell variable after building. Confirm the browser requests port 8000 and receives the expected CORS response. Do not use the developer’s unknown Vite environment as verification evidence.

### F. Provider budget

At B04.1, at most:

- One normal stream.
- One comparative stream.
- One additional request for Stop, only if needed.

These are HTTP request limits, not a claim of one provider call per comparative request.

Record a live-check ledger. Reuse evidence on an unchanged runtime binding. No automatic retry on quota errors. Fail closed if key5-only policy cannot be established.

## 6. Frontend ↔ backend integration strategy

### HERMITIC

Two complementary forms:

- Browser route fixtures for deliberate delays, stale responses and geometry.
- Real FastAPI HTTP/SSE harness with controlled dependencies for transport, schemas, cancellation and errors.

Use repeatedly. Fake fixture data stays test-only and is never described as live corpus evidence.

Before implementation, B02.4 adds deterministic fixtures for:

- Normal/comparative stage events.
- Cache-hit/skipped stages.
- Documents and exact chunk identity.
- Delayed source/neighbor response.
- Interrupted stream and omitted terminal event.
- Readiness transition.

Do not add test controls to production routes.

### LOCAL BACKEND

Production frontend at 4175 against actual app at 8000:

- Health/readiness/system.
- Document catalog and returned chunk IDs.
- Retrieval inspect.
- Search → real results.
- Source → indexed viewer.
- Real CORS and error handling.

No generation is required for these checks.

Use an isolated browser context with synthetic local conversation records referencing **actual returned source IDs**, clearly labeled test scaffolding. This verifies reader contracts without consuming provider quota.

### BOUNDED LIVE

Only at B04.1 after layout, actions, drafting and command work are integrated.

Verify ordinary/comparative stage rendering and Stop. Measure:

- Request start.
- Response headers.
- First stage.
- First token.
- Completion/cancellation.

Do not treat harness timing as inference speed or client/server elapsed-time subtraction as pure network latency.

### Mandatory per-task loop

Implement one coherent task → fast checks → required integration → rendered inspection → console/network review → task-owned fixes → checkpoint.

Do not defer known task failures to B06.1.

## 7. Final workspace/layout contract

### Geometry

- Expanded navigation: 216 px.
- Compact rail: 56 px.
- Desktop: CSS viewport ≥1024 px.
- Below 1024: navigation drawer.
- Navigation drawer: `min(280px, viewport − 32px)`.
- Conversation minimum with inline evidence: 480 px.
- Evidence: preferred existing value, default 384 px, bounded 360–560 px.
- Gap: 16 px.
- Main horizontal padding: 16 px per side.

For workspace width `W` after navigation:

```text
innerWidth = W − 32
inlineAllowed = innerWidth ≥ 480 + 16 + 360
effectiveEvidenceWidth = min(preferredWidth, 560, innerWidth − 496)
```

Inline evidence therefore requires `W ≥ 888`.

Measure the remaining container once. Do not combine unrelated viewport thresholds or arbitrary margins.

```text
Desktop:
[navigation][header                               ]
            [conversation scroller][evidence       ]
            [composer             ][evidence       ]

Evidence closed:
[navigation][header                               ]
            [conversation scroller                ]
            [composer                             ]

Insufficient width:
[navigation][conversation + composer]
             explicit evidence drawer

Mobile:
[header]
[conversation]
[composer]
explicit navigation OR evidence drawer
```

### Responsive results

| CSS width | Navigation | Main width expanded/compact | Evidence when opened |
|---:|---|---:|---|
| 1920 | Persisted desktop mode | 1704 / 1864 | Inline |
| 1440 | Persisted desktop mode | 1224 / 1384 | Inline |
| 1366 | Persisted desktop mode | 1150 / 1310 | Inline |
| 1280 | Persisted desktop mode | 1064 / 1224 | Inline |
| 1024 | Persisted desktop mode | 808 / 968 | Drawer / inline |
| 768 | Drawer | 768 | Drawer |
| 390 | Drawer | 390 | Drawer |
| 320 | Drawer | 320 | Drawer |

Evidence drawer width: `min(560px, viewport − 32px)`, right aligned. It is allowed to obscure content only after an explicit evidence action. Close restores the underlying conversation.

### Combined acceptance states

Test:

A. Expanded navigation + evidence closed.  
B. Compact navigation + evidence closed.  
C. Expanded navigation + inline evidence.  
D. Compact navigation + inline evidence.  
E. Insufficient width + evidence drawer.  
F. Mobile navigation drawer.  
G. Mobile evidence drawer.

For A–D:

- No navigation/content intersection.
- Conversation minimum maintained.
- Composer confined to its column.
- Latest answer scrollable above composer.
- No unexpected page horizontal scroll.

For E–G:

- One active workspace modal.
- Background inert.
- Escape/backdrop/Close work.
- Focus returns.
- Closing removes backdrop/inert state.
- Breakpoint transitions remove obsolete modal state.

### State transitions

- Evidence starts closed.
- Citation/Sources explicitly opens it.
- Closing does not delete selected-source identity.
- Conversation switch closes evidence and clears transient display context.
- Navigation to tools hides conversation evidence without corrupting its identity.
- Returning to desktop converts eligible evidence drawer to inline.
- Navigation drawer always closes on return to desktop.
- Responsive clamping never overwrites saved widths/preferences.

### Header

At ≥768 px: navigation control, status, command access, theme, locale and help remain directly reachable; labels may collapse to icons.

Below 768 px: retain navigation, compact status, command button and “More workspace controls”. The More dialog contains theme choices, locale and help. Close it before opening Help. No duplicate hidden focusable controls.

### Scroll/composer

- Conversation column owns messages scroller and composer sibling.
- Tools retain full-width scrolling.
- ChatInput must not remount on panel changes.
- Bound composer region to 40% of available conversation height on short screens; internal overflow handles expanded scope.
- Include safe-area bottom padding.
- Anchor “scroll to latest” inside the conversation region, not to the browser’s right edge.

## 8. Final chat/research UX contract

### Message order

User: identity → question → optional stored scope snapshot.

Assistant: identity/state → answer/citations → real source count/variant/elapsed metadata → Copy/Sources → secondary actions → execution details.

- Existing notes, bookmarks, feedback and variant actions remain available.
- Use a native disclosure containing ordinary buttons for secondary actions.
- Do not create a new ARIA menu framework.
- Keep Retry for errors.
- Do not relabel saved variants as regenerated answers.
- Export remains through the existing conversation export workflow.

### Displayed-answer context

Add transient App context:

```text
conversationId
messageId
variantId | null
```

ChatMessage reports it on focus/click within the answer and when changing variant. Variant selection itself remains in ChatMessage.

- Palette Copy uses this context.
- If none exists, default to newest completed original answer.
- Resolve and validate against current messages/variants at invocation.
- Deleted/unavailable targets fail closed with a notice.
- Sources/Save use the exact evidence selection.
- Changing conversations clears this context.

### Template application

Opening captures:

- Conversation ID.
- Draft value.
- Scope value.
- Locale.

Cancel/Escape/backdrop does not modify them.

Apply:

1. Validate current parameters and final length.
2. Verify captured conversation/draft/scope/locale still match.
3. If changed, retain current application state and show “Research context changed; reopen this template”.
4. Otherwise atomically apply draft and parameter-derived scope.
5. Close and focus composer.
6. Never auto-send.

Single-company templates apply their validated company ticker. Dependency comparison keeps `ticker: null`, both companies in the question, and the existing comparative preset. Preserve each template’s existing section/topK.

No year-coverage promise: a syntactically valid year does not establish an indexed filing exists.

### Drafting while streaming

- Textarea remains editable.
- Send remains blocked while a request/preflight is active.
- Enter cannot erase or submit the next draft.
- Stop/completion preserves it.
- Use existing draft persistence and sanitation; never persist live partial message arrays as completed history.
- Reload/switch tests must prove next-draft recovery.
- No queued-send feature.

## 9. Performance and latency contract

Separate:

| Layer | Measurement |
|---|---|
| Backend | Reported embedding/retrieval/decomposition/generation stages |
| Provider | Provider-bound wait where independently observable |
| Network/protocol | Request start, headers, SSE delivery |
| Frontend | React commits, Markdown completion, layout/paint |
| Perceived UX | Disabled draft, weak feedback, hidden content, layout shift |

Current tested Library/input budgets pass. Other paths remain unmeasured, not proven slow.

### Workloads and budgets

- Warm controls/input p95 ≤100 ms, at least 30 samples.
- Warm view switch p95 ≤200 ms excluding network.
- Library search p95 ≤200 ms, existing 100-conversation workload.
- 200-message composer workload.
- 60-second stream with simultaneous typing.
- Twenty panel/palette mount cycles.
- Source switching and reader cold/warm paths.
- Final Markdown render.
- Scope changes and obsolete request rejection.

### Required optimization loop

Baseline p50/p95 → attribute hotspot → smallest patch → identical workload → three comparable runs → retain/revert.

No virtualization, batching changes, state library or broad memoization without measured evidence and a task-specific contract. B02.3 can finish `[x] NO CODE CHANGE REQUIRED`.

Existing 80 ms batching and plain-text streaming remain unchanged by default.

Motion:

- Colors/borders: 140 ms.
- Drawer transform/opacity: 180 ms.
- Navigation width: at most 180 ms, retained only if measured acceptable.
- No `transition: all`.
- Reduced motion removes spatial/width animation.
- Never animate high-frequency streaming/list updates.

## 10. RAG utilities / visualization scope

| Item | Scope | Real source and user question |
|---|---|---|
| Citation/source/reader access | CURRENT CYCLE | Source identity: “What supports this claim?” |
| Execution list refinement | CURRENT CYCLE | StageEvent/ExecutionTrace: “What is happening?” |
| Notes/bookmarks/variants discoverability | CURRENT CYCLE | Existing persisted records |
| Corpus/scope helpers | CURRENT CYCLE | Health/supported metadata and current filters |
| Retrieval Lab correctness | CURRENT CYCLE | Submitted RetrievalTrace identity |
| Brand and interactive polish | CURRENT CYCLE | No data dependency |
| Source grouping summary | USEFUL NEXT | Selected answer’s sources—not corpus coverage |
| Rank movement/timing bars | USEFUL NEXT | Existing retrieval rank/timing fields |
| Financial trend chart | DEFERRED | Current VisualAnswer is one metric, not a series |
| Corpus composition chart | DEFERRED | Requires complete aggregate data |
| Saved workflows/pins/presets | DEFERRED | Additional persistence/product decisions |
| Full PDF, fake confidence, decorative graph | NOT RECOMMENDED | Unsupported or disproportionate |

Pipeline rules:

- Only reported stages.
- Label counters.
- Running client timer says “elapsed in this view”.
- Completed duration uses server value.
- Do not sum overlapping stages.
- Resolve children only through real parent IDs.
- No invented reranking stage or progress percentage.

Brand: original compact filing/search silhouette, optional single evidence connection; 16 px simplifies details; static monochrome-compatible SVG; no permanent glow; existing lockup text unchanged.

## 11. Final dependency graph

Exact order:

```text
B01.1
→ B02.4
→ B02.1
→ B01.2
→ B01.3
→ B01.7
→ B01.4
→ B01.5
→ B01.6
→ B02.2
→ B02.5
→ B03.1
→ B03.2
→ B03.3
→ B03.4
→ B04.1
→ B04.2
→ B05.1
→ B02.3
→ B06.1
```

All IDs carry prefix `V2-`.

Hard dependencies are listed per task. Order remains fixed even where dependencies are softer.

### Blocker routing

- B02.4 harness defect blocks runtime-facing implementation gates; only isolated contrast/brand work is safe.
- Layout implementation failure blocks B01.5/B01.6 and subsequent chat-layout work.
- Local backend unavailable: hermetic implementation may continue in order, but affected tasks remain `[-]/[!]`; B06.1 cannot close.
- Provider quota: continue non-provider tasks; record conditional live gate unavailable, never retry repeatedly.
- Native zoom unavailable: continue other work; final mandatory zoom gate remains `[!]`.
- Unexplained persistence or identity regression blocks dependent mutation work.
- B02.3 needs baseline evidence; no baseline means no optimization.

Do not treat an external verification blocker as a reason to create infrastructure.

## 12. Detailed executable task specifications

### Shared task contracts

These clauses apply to every task below.

**FAST:** from `F`, `bun run lint`; `git diff --check` from `R`.

**UNIT:** `bun run test -- <listed test paths>` from `F`.

**H:** provider-free browser fixture plus HTTP/SSE test where specified.

**L:** production preview 4175 against verified real backend 8000.

**LIVE:** bounded ledger from §5, only at B04.1.

**Receipt:** task/status, starting HEAD/diff binding, files, change summary, commands/results, integration level, inspected screenshots/states, process ownership, performance evidence, blockers, next task.

**Global preservation:** §15.

**Global forbidden refactor:** frameworks, schemas, backend semantics, unrelated cleanup, broad state moves.

Every `[x]` requires its specified gate, not merely implementation.

### V2-B01.1 — Reconcile and establish master checkpoint

- **Current state:** Conflicting historical checkboxes/receipts.
- **Target state:** Single remaining-work ledger.
- **Why:** Prevent restart and false completion.
- **Dependencies:** None.
- **Hard/soft gate:** Hard entry gate.
- **Inspect first:** Checkpoint, attached plan, git status/diff.
- **Files to modify:** `R/docs/implementation-progress.md`.
- **Files to create:** Master-plan file named in §1.
- **Frontend/backend:** Documentation.
- **State owner:** Checkpoint.
- **Data/API contract:** No application mutation.
- **Implementation contract:** Append reconciliation; preserve history; mark supersessions explicitly.
- **Allowed refactor:** Documentation organization only.
- **Forbidden refactor:** Any source edit.
- **Must preserve:** Historical IDs and dirty work.
- **Edge cases:** Later user edits, missing artifacts.
- **Integration gate:** NONE.
- **Fast validation:** FAST, `rg -n "V2-B" docs`.
- **Targeted validation:** Unique IDs and complete order.
- **Runtime validation:** None.
- **Browser validation:** None.
- **Performance validation:** None.
- **Accessibility validation:** None.
- **Acceptance:** No ambiguous next task or duplicate authority.
- **Rollback boundary:** New documentation slice.
- **Checkpoint receipt:** Include preserved task list.
- **Next task:** B02.4.

### V2-B02.4 — Make integration tooling safe and sufficient

- **Current state:** Harness lacks normal stage fixtures, may overwrite stack file, and permits server reuse.
- **Target state:** Repeatable isolated H/L verification.
- **Why:** Integration must precede feature changes.
- **Dependencies:** B01.1.
- **Hard/soft gate:** Hard runtime-test gate.
- **Inspect first:** `F/playwright*.config.ts`, `F/e2e/integration.spec.ts`, `R/tests/integration/harness_server.py`, API event schemas.
- **Files to modify:** Integration config/spec, harness, regular Playwright exclusion rules.
- **Files to create:** `F/playwright.local.config.ts`, `F/e2e/workspace.local.spec.ts`.
- **Frontend/backend:** Test-only both.
- **State owner:** Isolated harness and browser contexts.
- **Data/API contract:** Production routes unchanged; fixtures use current DTOs.
- **Implementation contract:** Add deterministic stage/document/neighbor fixtures; temp stack directory; fail on occupied unowned ports; separate integration/local build outputs; local tests never start backend automatically.
- **Allowed refactor:** Test setup/fixtures/config.
- **Forbidden refactor:** Production routes or real data changes.
- **Must preserve:** Existing fragmentation/cancellation tests.
- **Edge cases:** Stale preview, port collision, Windows Python path.
- **Integration gate:** HERMITIC.
- **Fast validation:** FAST.
- **Targeted validation:** Existing harness Python tests.
- **Runtime validation:** H health, stream, stage and chunk identity.
- **Browser validation:** One fixture answer and reader visibly rendered.
- **Performance validation:** No real provider calls; no unnecessary fixture delays.
- **Accessibility validation:** Existing modal/answer accessibility remains testable.
- **Acceptance:** Tests cannot hit developer backend accidentally; stage/reader workflows are covered; pre-existing stack file untouched.
- **Rollback boundary:** Test infrastructure patch.
- **Checkpoint receipt:** Ports, output paths, fixture modes.
- **Next task:** B02.1.

### V2-B02.1 — Capture baseline and real-runtime feasibility

- **Current state:** Input/Library evidence exists; other costs unmeasured.
- **Target state:** Attributed baseline plus L readiness.
- **Why:** Avoid speculative optimization.
- **Dependencies:** B02.4.
- **Hard/soft gate:** Hard before optimization; local availability may block only L evidence.
- **Inspect first:** App, ChatMessage, palette, ContextPanel, API, existing performance tests.
- **Files to modify:** Checkpoint.
- **Files to create:** `F/e2e/workspace-performance.spec.ts`.
- **Frontend/backend:** Diagnosis both.
- **State owner:** Test instrumentation.
- **Data/API contract:** Synthetic datasets; real endpoint results separately labeled.
- **Implementation contract:** Run §9 workloads; start/reuse L by §5; verify documents/retrieval without generation.
- **Allowed refactor:** Test instrumentation only.
- **Forbidden refactor:** Optimization.
- **Must preserve:** User Library and runtime data.
- **Edge cases:** Missing model, store lock, cold lazy load.
- **Integration gate:** LOCAL BACKEND, preceded by H.
- **Fast validation:** FAST.
- **Targeted validation:** Existing performance specs.
- **Runtime validation:** L health/system/documents/retrieval.
- **Browser validation:** Panel/palette/composer workflows.
- **Performance validation:** p50/p95, ≥30 samples, environment recorded.
- **Accessibility validation:** Keyboard and reduced-motion workloads.
- **Acceptance:** Each area measured or explicitly unverified; no false backend speed claim.
- **Rollback boundary:** Profiling tests.
- **Checkpoint receipt:** Baseline table and blockers.
- **Next task:** B01.2.

### V2-B01.2 — Reflow desktop navigation

- **Current state:** Sidebar independently uses 1280 breakpoint.
- **Target state:** Inline ≥1024; drawer below.
- **Why:** Screenshot 1.
- **Dependencies:** B02.4; B02.1 baseline attempted.
- **Hard/soft gate:** Hard layout prerequisite.
- **Inspect first:** App, Sidebar, WorkspaceHeader, `useNavigationLayout`, CSS.
- **Files to modify:** Those components/CSS and App tests.
- **Files to create:** None.
- **Frontend/backend:** Frontend.
- **State owner:** App effective mode; existing preference hook.
- **Data/API contract:** Existing preference key unchanged.
- **Implementation contract:** One breakpoint owner; inline flex sibling; no desktop backdrop/fixed sidebar.
- **Allowed refactor:** Navigation-mode props and related CSS.
- **Forbidden refactor:** Navigation registry or conversation state rewrite.
- **Must preserve:** Routes, stored preference, active markers.
- **Edge cases:** Open drawer crossing breakpoint, storage event, zoom.
- **Integration gate:** HERMITIC.
- **Fast validation:** FAST.
- **Targeted validation:** App/navigation hook tests.
- **Runtime validation:** H conversation loaded.
- **Browser validation:** 1024/1272/1280/1440, both themes/locales.
- **Performance validation:** Expand/collapse timing.
- **Accessibility validation:** Names, tooltips, 44 px rail targets, focus return.
- **Acceptance:** Desktop main bounds never intersect navigation.
- **Rollback boundary:** Mode props/CSS.
- **Checkpoint receipt:** Geometry and preference checks.
- **Next task:** B01.3.

### V2-B01.3 — Correct navigation foreground states

- **Current state:** Dark menu foreground uses border alias.
- **Target state:** Semantic text/surface/border states.
- **Why:** Screenshot 2.
- **Dependencies:** B01.2.
- **Hard/soft gate:** Hard visual acceptance.
- **Inspect first:** WorkspaceHeader, tokens, related dark:text-slate-300 usages.
- **Files to modify:** Header/CSS; confirmed same-role errors in ChatMessage/SubQueriesPanel only.
- **Files to create:** None.
- **Frontend/backend:** Frontend.
- **State owner:** Existing control state.
- **Data/API contract:** None.
- **Implementation contract:** Explicit text token; 44 px targets; hover/open/pressed/focus styling.
- **Allowed refactor:** Confirmed foreground misuse.
- **Forbidden refactor:** Global slate alias redefinition.
- **Must preserve:** Theme system.
- **Edge cases:** Forced colors, disabled, touch.
- **Integration gate:** NONE.
- **Fast validation:** FAST.
- **Targeted validation:** Header through App tests.
- **Runtime validation:** None.
- **Browser validation:** Both themes, all control states.
- **Performance validation:** Color/border transitions only.
- **Accessibility validation:** Text 4.5:1; icon/control 3:1; visible focus.
- **Acceptance:** Recognizable without hover; computed foreground is not border token.
- **Rollback boundary:** Control styles.
- **Checkpoint receipt:** Contrast pairs.
- **Next task:** B01.7.

### V2-B01.7 — Make narrow-header controls explicit

- **Current state:** Command access is hidden below md; narrow controls compete.
- **Target state:** Header contract in §7.
- **Why:** Previous plan left collapse decisions to implementer.
- **Dependencies:** B01.3.
- **Hard/soft gate:** Hard narrow-layout gate.
- **Inspect first:** WorkspaceHeader, ModalDialog, header CSS.
- **Files to modify:** Header/CSS/tests.
- **Files to create:** None.
- **Frontend/backend:** Frontend.
- **State owner:** Header More-open state.
- **Data/API contract:** Reuse theme/locale/help callbacks.
- **Implementation contract:** Below768 retain four controls; More uses existing dialog; close before Help; no duplicate focusable copies.
- **Allowed refactor:** Header presentation.
- **Forbidden refactor:** New navigation/menu framework.
- **Must preserve:** Existing keyboard shortcut and theme preference.
- **Edge cases:** 320 px, VI, 200% zoom, disabled reset.
- **Integration gate:** NONE.
- **Fast validation:** FAST.
- **Targeted validation:** App/header tests.
- **Runtime validation:** None.
- **Browser validation:** 320/390/768.
- **Performance validation:** No added fetch.
- **Accessibility validation:** Focus trap/return, labels, 44 px.
- **Acceptance:** All essential controls reachable without horizontal scrolling.
- **Rollback boundary:** Header collapse slice.
- **Checkpoint receipt:** Narrow screenshots and tab order.
- **Next task:** B01.4.

### V2-B01.4 — Unify evidence modes and lifecycle

- **Current state:** Viewport rail, automatic rendering, incomplete neighbor cancellation.
- **Target state:** One closed/inline/drawer inspector with preserved identity/state.
- **Why:** Sidebar/evidence width competition and mobile reader access.
- **Dependencies:** B01.2, B02.4.
- **Hard/soft gate:** Hard before composer/message integration.
- **Inspect first:** App evidenceTarget, ContextPanel/DocumentViewer, documentCache, ModalDialog.
- **Files to modify:** App, ContextPanel, CSS and tests.
- **Files to create:** `F/src/components/ContextPanel.test.tsx` if absent.
- **Frontend/backend:** Frontend.
- **State owner:** App selection/open; ContextPanel reader presentation state.
- **Data/API contract:** Exact existing IDs and cache API.
- **Implementation contract:** Apply width formula; one mounted reader; Close; preserve reader search/page/text scale across inline↔drawer; cancel neighbor subscription on replacement/unmount; clean resize listeners/pointercancel.
- **Allowed refactor:** Lift only reader presentation state needed across portal remount.
- **Forbidden refactor:** Cache architecture, source schema, fallback substitution.
- **Must preserve:** Exact citation/variant/chunk association.
- **Edge cases:** Missing source, removed variant, late neighbor result, resize during drag.
- **Integration gate:** LOCAL BACKEND, preceded by H.
- **Fast validation:** FAST.
- **Targeted validation:** ContextPanel/App/cache tests.
- **Runtime validation:** L source→chunk→neighbor; H late-response rejection.
- **Browser validation:** Modes C–G; selected source retained.
- **Performance validation:** Source switch and resize baseline.
- **Accessibility validation:** Trap/return, separator bounds, close.
- **Acceptance:** One reader; ≥480 conversation inline; no stale neighbor content.
- **Rollback boundary:** Inspector presentation/lifecycle slice.
- **Checkpoint receipt:** H and L identity evidence.
- **Next task:** B01.5.

### V2-B01.5 — Attach composer to conversation geometry

- **Current state:** Composer outside conversation/evidence grid.
- **Target state:** Message scroller plus composer within primary column.
- **Why:** Protect answer and composer dimensions.
- **Dependencies:** B01.4.
- **Hard/soft gate:** Hard layout gate.
- **Inspect first:** App wrappers, scroll refs/effects, ChatInput CSS.
- **Files to modify:** App/ChatInput/CSS/tests.
- **Files to create:** None.
- **Frontend/backend:** Frontend.
- **State owner:** Existing draft owner; conversation scroll ref.
- **Data/API contract:** No send changes.
- **Implementation contract:** §7 geometry; preserve ChatInput instance; scope overflow bounded; local scroll-to-latest anchor.
- **Allowed refactor:** Conversation wrappers/scroll ownership.
- **Forbidden refactor:** Tool state or persistence changes.
- **Must preserve:** Near-bottom follow and reading older answers.
- **Edge cases:** Multiline, scope open, short viewport, zoom.
- **Integration gate:** HERMITIC.
- **Fast validation:** FAST.
- **Targeted validation:** App/ChatInput tests.
- **Runtime validation:** H streaming and long conversation.
- **Browser validation:** A–G, short/multiline drafts.
- **Performance validation:** No smooth scroll per token.
- **Accessibility validation:** Focus/caret survives reflow.
- **Acceptance:** Latest answer can be fully scrolled above composer.
- **Rollback boundary:** Geometry/scroll slice.
- **Checkpoint receipt:** Bounds and focus evidence.
- **Next task:** B01.6.

### V2-B01.6 — Lock combined layout acceptance

- **Current state:** Overflow test insufficient.
- **Target state:** Automated A–G coverage.
- **Why:** Prevent repeated screenshot regressions.
- **Dependencies:** B01.4, B01.5, B01.7.
- **Hard/soft gate:** Hard before chat presentation completion.
- **Inspect first:** Existing regression specs/fixtures.
- **Files to modify:** Duplicate old assertions only.
- **Files to create:** `F/e2e/workspace-layout.spec.ts`.
- **Frontend/backend:** Tests.
- **State owner:** Isolated browser fixtures.
- **Data/API contract:** H sources/stages.
- **Implementation contract:** Rectangle intersections, hit tests, modal cleanup, focus and preference assertions.
- **Allowed refactor:** Tests only.
- **Forbidden refactor:** Lowering requirements.
- **Must preserve:** Existing widths.
- **Edge cases:** Breakpoint transition with modal open.
- **Integration gate:** HERMITIC.
- **Fast validation:** FAST.
- **Targeted validation:** Layout spec Chromium/Firefox.
- **Runtime validation:** H answer and evidence.
- **Browser validation:** §14 full layout matrix.
- **Performance validation:** Stable final geometry after transition.
- **Accessibility validation:** Keyboard A–G.
- **Acceptance:** No retries or uninspected screenshots.
- **Rollback boundary:** Test file.
- **Checkpoint receipt:** Matrix cells and zoom gap.
- **Next task:** B02.2.

### V2-B02.2 — Reject obsolete Search responses

- **Current state:** No abort/identity guard.
- **Target state:** Latest submitted request only.
- **Why:** Wrong-scope late results.
- **Dependencies:** B02.4; B01.6 for integrated browser gate.
- **Hard/soft gate:** Hard correctness.
- **Inspect first:** SearchWorkspace/runSearch, inspectRetrieval.
- **Files to modify:** SearchWorkspace/tests.
- **Files to create:** None.
- **Frontend/backend:** Frontend.
- **State owner:** Search request controller/sequence.
- **Data/API contract:** Existing optional AbortSignal.
- **Implementation contract:** Abort/invalidate on scope change/unmount; guard success/error/finally; same-scope refresh retains labeled previous results; changed scope clears.
- **Allowed refactor:** Request lifecycle.
- **Forbidden refactor:** Retrieval parameters/API.
- **Must preserve:** Submit-only retrieval.
- **Edge cases:** Late success/failure, offline, double click.
- **Integration gate:** LOCAL BACKEND, preceded by H.
- **Fast validation:** FAST.
- **Targeted validation:** SearchWorkspace tests.
- **Runtime validation:** H delayed responses; L retrieval results.
- **Browser validation:** Change scope mid-request.
- **Performance validation:** Request counts; no keystroke calls.
- **Accessibility validation:** Status and preserved focus.
- **Acceptance:** Old response cannot mutate new scope state.
- **Rollback boundary:** Search lifecycle.
- **Checkpoint receipt:** Abort/result identity.
- **Next task:** B02.5.

### V2-B02.5 — Bind Retrieval Lab results to submitted configuration

- **Current state:** Request ID exists; controls/export can diverge from running trace.
- **Target state:** Clear submitted configuration and invalidation.
- **Why:** Same correctness issue in an adjacent requested tool.
- **Dependencies:** B02.2.
- **Hard/soft gate:** Hard correctness.
- **Inspect first:** RetrievalLabPanel/runInspection/downloadTrace.
- **Files to modify:** RetrievalLabPanel and tests.
- **Files to create:** Dedicated unit test if absent.
- **Frontend/backend:** Frontend.
- **State owner:** Lab request ID/controller and submitted snapshot.
- **Data/API contract:** Existing trace fields.
- **Implementation contract:** On query/filter/preset/comparison change, invalidate/abort active inspection and clear mismatched traces; comparison belongs to same snapshot; export uses trace query/configuration.
- **Allowed refactor:** Request/snapshot handling only.
- **Forbidden refactor:** Rank computation or trace format changes.
- **Must preserve:** Presets, exports and comparison functionality.
- **Edge cases:** Change between first/second comparison response; route exit.
- **Integration gate:** LOCAL BACKEND, preceded by H.
- **Fast validation:** FAST.
- **Targeted validation:** Lab request tests.
- **Runtime validation:** H delayed comparison; L provider-free inspect.
- **Browser validation:** Edit config during loading, export completed result.
- **Performance validation:** No automatic inspect on change.
- **Accessibility validation:** Loading and invalidated-result explanation.
- **Acceptance:** Display/export always describes its submitted query.
- **Rollback boundary:** Lab request snapshot.
- **Checkpoint receipt:** Comparison/export checks.
- **Next task:** B03.1.

### V2-B03.1 — Refine research message hierarchy

- **Current state:** Competing actions and evidence columns.
- **Target state:** §8 hierarchy and single workspace inspector.
- **Why:** Serious research presentation.
- **Dependencies:** B01.6.
- **Hard/soft gate:** Hard source/action continuity.
- **Inspect first:** ChatMessage displayed fields/actions.
- **Files to modify:** ChatMessage/CSS/tests.
- **Files to create:** None.
- **Frontend/backend:** Frontend.
- **State owner:** Existing message/variant state.
- **Data/API contract:** Real metadata only.
- **Implementation contract:** Answer first; Copy/Sources primary; secondary disclosure; standalone source fallback remains when no inspector callback.
- **Allowed refactor:** Presentation and direct duplication removal.
- **Forbidden refactor:** New regeneration/export workflow.
- **Must preserve:** All existing actions and variant citations.
- **Edge cases:** No source, old metadata, stopped/error answer.
- **Integration gate:** LOCAL BACKEND, preceded by H.
- **Fast validation:** FAST.
- **Targeted validation:** ChatMessage tests.
- **Runtime validation:** L source/reader; H variants/actions.
- **Browser validation:** Original/variant, notes/bookmark/error.
- **Performance validation:** No duplicated source trees.
- **Accessibility validation:** Button/disclosure keyboard paths.
- **Acceptance:** Existing actions reachable; correct displayed sources open.
- **Rollback boundary:** Message presentation.
- **Checkpoint receipt:** Action parity.
- **Next task:** B03.2.

### V2-B03.2 — Enable recoverable drafting during streaming

- **Current state:** Textarea and draft-persist path are restricted during stream.
- **Target state:** Editable durable next draft, no concurrent send.
- **Why:** Perceived responsiveness.
- **Dependencies:** B03.1, B02.4.
- **Hard/soft gate:** Hard persistence/cancellation gate.
- **Inspect first:** ChatInput submit, App preflight/finalization, useConversationLibrary draft persistence/sanitization.
- **Files to modify:** ChatInput, narrowly scoped App/hook code and tests.
- **Files to create:** None.
- **Frontend/backend:** Frontend.
- **State owner:** Existing draft owner.
- **Data/API contract:** Existing schema and sanitized stored messages.
- **Implementation contract:** §8 draft rules; persist draft through existing writer while excluding incomplete response data; no clear on failed preflight.
- **Allowed refactor:** Draft/editability/save boundary only.
- **Forbidden refactor:** Persistence rewrite or completion debounce restoration.
- **Must preserve:** Epochs, writer locking, Stop.
- **Edge cases:** IME, reload, switch, Stop, late done, 500 chars.
- **Integration gate:** LOCAL BACKEND plus H; live stream verified later at B04.1.
- **Fast validation:** FAST.
- **Targeted validation:** ChatInput/App/library tests.
- **Runtime validation:** H stream/Stop/reload; L session/readiness contract.
- **Browser validation:** Type throughout 60-second fixture stream.
- **Performance validation:** p95 ≤100 ms.
- **Accessibility validation:** Send-disabled explanation; textarea focus retained.
- **Acceptance:** Next draft survives completion/Stop/reload without concurrent request.
- **Rollback boundary:** Draft-specific patch.
- **Checkpoint receipt:** Persistence and timing results.
- **Next task:** B03.3.

### V2-B03.3 — Complete template application safeguards

- **Current state:** No opening snapshot; static null ticker applied.
- **Target state:** Conflict-safe, parameter-derived Apply.
- **Why:** Unfinished A05.2.
- **Dependencies:** B03.2.
- **Hard/soft gate:** Hard draft safety.
- **Inspect first:** App openTemplateQuestion/handleApplyTemplate, TemplateQuestionDialog, researchTemplates.
- **Files to modify:** Those files/tests.
- **Files to create:** None.
- **Frontend/backend:** Frontend.
- **State owner:** App opening snapshot; dialog field values.
- **Data/API contract:** Typed Apply payload with validated question/scope; no schema migration.
- **Implementation contract:** §8 Apply sequence; errors preserve dialog/current draft; selected company reaches scope.
- **Allowed refactor:** Apply payload and snapshot validation.
- **Forbidden refactor:** Generic forms or template rewrite.
- **Must preserve:** Locale, cancellation, 5–500 guard and reserved placeholders.
- **Edge cases:** Conversation deleted, cross-tab change, ticker removed, empty metadata.
- **Integration gate:** HERMITIC.
- **Fast validation:** FAST.
- **Targeted validation:** Template/dialog/App tests.
- **Runtime validation:** H proves no request on select/Apply; submitted request uses applied scope.
- **Browser validation:** Cancel/conflict/valid Apply, EN/VI.
- **Performance validation:** No added fetch.
- **Accessibility validation:** Errors associated with fields; initial/return focus.
- **Acceptance:** No unintended draft replacement; correct ticker; no auto-send.
- **Rollback boundary:** Apply contract.
- **Checkpoint receipt:** Conflict and payload assertions.
- **Next task:** B03.4.

### V2-B03.4 — Bind commands to displayed answer identity

- **Current state:** Latest answer used regardless of displayed variant.
- **Target state:** §8 transient context and invocation validation.
- **Why:** Unfinished A05.3.
- **Dependencies:** B03.1, B01.4, B03.3.
- **Hard/soft gate:** Hard source/mutation identity.
- **Inspect first:** App contextualCommands, ChatMessage selectedVariantId, commandRegistry/CommandPalette.
- **Files to modify:** App/ChatMessage/registry types/tests.
- **Files to create:** None.
- **Frontend/backend:** Frontend.
- **State owner:** App transient display context; existing variant owner.
- **Data/API contract:** ID-only context; resolve current records before action.
- **Implementation contract:** Copy exact displayed text; inspect/save exact selected evidence; unavailable target gives notice; palette does not own mutations.
- **Allowed refactor:** Typed callback/context plumbing.
- **Forbidden refactor:** Variant persistence or global state framework.
- **Must preserve:** Keyboard palette model and existing saveEvidence behavior.
- **Edge cases:** Deleted/changed variant while palette open; conversation switch.
- **Integration gate:** LOCAL BACKEND, preceded by H.
- **Fast validation:** FAST.
- **Targeted validation:** App/ChatMessage/palette tests.
- **Runtime validation:** H identity races; L selected source→reader.
- **Browser validation:** Older answer and saved variant Copy/Sources.
- **Performance validation:** Do not publish context on every token.
- **Accessibility validation:** Focused answer defines context; no pointer-only selection.
- **Acceptance:** No newest-answer substitution.
- **Rollback boundary:** Display-context plumbing.
- **Checkpoint receipt:** Target IDs and action parity, without user content.
- **Next task:** B04.1.

### V2-B04.1 — Verify honest execution presentation

- **Current state:** Stage list exists; counters/timing provenance unclear.
- **Target state:** §10 semantics over real events.
- **Why:** Explain RAG activity honestly.
- **Dependencies:** B03.2, B03.4, B02.4.
- **Hard/soft gate:** H/L hard; live conditional on prerequisites.
- **Inspect first:** PipelineExecution, StageEvent/ExecutionTrace, harness fixtures.
- **Files to modify:** PipelineExecution/tests.
- **Files to create:** PipelineExecution test if absent.
- **Frontend/backend:** Frontend.
- **State owner:** Local running timer.
- **Data/API contract:** Existing events only.
- **Implementation contract:** Labeled counters; running-time label; server final duration; child relationship only with valid parent; unknown stage neutral.
- **Allowed refactor:** Presentation.
- **Forbidden refactor:** Backend instrumentation/stage invention.
- **Must preserve:** Request-local ordering/cancellation.
- **Edge cases:** Cache, skipped, cancelled, out-of-order, trace-only.
- **Integration gate:** LOCAL + BOUNDED LIVE, preceded by H.
- **Fast validation:** FAST.
- **Targeted validation:** Pipeline/ChatMessage tests.
- **Runtime validation:** H all paths; L readiness; live ledger ordinary/comparative/Stop.
- **Browser validation:** Stage changes, preserved draft and citations.
- **Performance validation:** Timings separated by layer; local 250 ms timer only.
- **Accessibility validation:** Announce stage change, not every timer tick.
- **Acceptance:** UI matches events; no fake progress/timing.
- **Rollback boundary:** Pipeline presentation.
- **Checkpoint receipt:** H/L/live levels separately.
- **Next task:** B04.2.

### V2-B04.2 — Finish concise discoverability and metadata parity

- **Current state:** Overview/helpers exist; some misleading copy/local icon consumers remain.
- **Target state:** Truthful compact helpers and registry-consistent tool identity.
- **Why:** Remaining A01.2/A04 requirements.
- **Dependencies:** B04.1 implementation.
- **Hard/soft gate:** Local metadata gate hard.
- **Inspect first:** OverviewPanel, workspace metadata, tool introductions, ContextPanel descriptions.
- **Files to modify:** Those presentation files/i18n; no broad panel rewrite.
- **Files to create:** None.
- **Frontend/backend:** Frontend.
- **State owner:** Existing health/scope data.
- **Data/API contract:** Reported searchable counts; no configured fallback.
- **Implementation contract:** Heading→corpus→scope→service→≤4 templates→≤3 recents; precise offline/readiness/ranking copy; tool icon/descriptions consume registry.
- **Allowed refactor:** Copy, intro metadata consumption, compact spacing.
- **Forbidden refactor:** New fetch/polling or features.
- **Must preserve:** Existing guides and routes.
- **Edge cases:** Missing/stale metadata, EN/VI.
- **Integration gate:** LOCAL BACKEND, preceded by H.
- **Fast validation:** FAST.
- **Targeted validation:** App/registry tests.
- **Runtime validation:** L counts match response; H offline/unknown.
- **Browser validation:** 1440×900 and320, both themes/locales.
- **Performance validation:** No additional request.
- **Accessibility validation:** Critical help not tooltip-only.
- **Acceptance:** First template row above composer at1440×900; no fake readiness estimate.
- **Rollback boundary:** Intro/copy slice.
- **Checkpoint receipt:** API-to-visible-data checks.
- **Next task:** B05.1.

### V2-B05.1 — Refine compact brand

- **Current state:** Filing/check mark.
- **Target state:** Original filing/search compact mark and unchanged lockup.
- **Why:** Screenshot 3.
- **Dependencies:** B01.7; execute after B04.2.
- **Hard/soft gate:** Visual gate.
- **Inspect first:** BrandMark/tests/CSS.
- **Files to modify:** Those files.
- **Files to create:** None.
- **Frontend/backend:** Frontend.
- **State owner:** None.
- **Data/API contract:** Existing component API.
- **Implementation contract:** §10 mark; simplified16px; currentColor fallback; no permanent glow.
- **Allowed refactor:** Brand geometry/styles.
- **Forbidden refactor:** Product renaming or icon-system changes.
- **Must preserve:** Existing callers and accessible lockup.
- **Edge cases:** Rail, forced colors, zoom.
- **Integration gate:** NONE.
- **Fast validation:** FAST.
- **Targeted validation:** BrandMark tests.
- **Runtime validation:** None.
- **Browser validation:**16/24/32/48px Light/Dark/mono.
- **Performance validation:** Static SVG, no filters/animation.
- **Accessibility validation:** Decorative SVG hidden beside name.
- **Acceptance:** Legible silhouette; no copied reference composition.
- **Rollback boundary:** Brand component.
- **Checkpoint receipt:** Size matrix.
- **Next task:** B02.3.

### V2-B02.3 — Retain only measured optimization

- **Current state:** Baseline plus completed UI changes.
- **Target state:** Budgets met with justified code or no-change decision.
- **Why:** Smoothness without speculative refactor.
- **Dependencies:** B02.1 and preceding implementation tasks.
- **Hard/soft gate:** Hard measurement gate.
- **Inspect first:** Baseline and updated traces.
- **Files to modify:** Only attributed hotspot/tests.
- **Files to create:** None by default.
- **Frontend/backend:** Frontend.
- **State owner:** Unchanged.
- **Data/API contract:** Unchanged.
- **Implementation contract:** §9 loop. Stabilize message-row props only if measured; coalesce resize or remove width animation if measured. Other architecture changes require a scoped follow-up decision.
- **Allowed refactor:** One evidenced hotspot.
- **Forbidden refactor:** Broad memoization, virtualization, batching/framework changes.
- **Must preserve:** All §15 contracts.
- **Edge cases:** Noise, cold load, final Markdown.
- **Integration gate:** HERMITIC; rerun affected L gate if a runtime-facing file changes.
- **Fast validation:** FAST.
- **Targeted validation:** Hotspot tests.
- **Runtime validation:** H same workload.
- **Browser validation:** Same before/after state.
- **Performance validation:** Three comparable p50/p95 runs.
- **Accessibility validation:** Focus/reduced motion after change.
- **Acceptance:** Improvement beyond noise without regression, or no-code-change receipt.
- **Rollback boundary:** Single optimization patch.
- **Checkpoint receipt:** Before/after/retain-or-revert.
- **Next task:** B06.1.

### V2-B06.1 — Close integrated product gates

- **Current state:** Task receipts accumulated incrementally.
- **Target state:** One unchanged final binding verified.
- **Why:** Product completion exceeds compilation.
- **Dependencies:** All mandatory task gates.
- **Hard/soft gate:** Final hard gate.
- **Inspect first:** Master/checkpoint/diff/results.
- **Files to modify:** Checkpoint; task-owned test gap only.
- **Files to create:** None.
- **Frontend/backend:** Both verification.
- **State owner:** Existing owners.
- **Data/API contract:** No changes.
- **Implementation contract:** §17; failures return to owning task.
- **Allowed refactor:** None opportunistically.
- **Forbidden refactor:** Scope expansion or test weakening.
- **Must preserve:** §15.
- **Edge cases:** Quota, native zoom, intermittent failures.
- **Integration gate:** LOCAL + conditional BOUNDED LIVE, plus H.
- **Fast validation:** Full static/build.
- **Targeted validation:** Full unit/component.
- **Runtime validation:** H/L and live ledger review.
- **Browser validation:** §14 and actual zoom.
- **Performance validation:** Final production budgets.
- **Accessibility validation:** Complete changed-surface matrix.
- **Acceptance:** §18 satisfied; no unresolved mandatory gate.
- **Rollback boundary:** Route failures to task patches.
- **Checkpoint receipt:** Final evidence index and completion status.
- **Next task:** None only after definition of done.

## 13. Task-by-task integration gate matrix

| Task | Required integration |
|---|---|
| B01.1 | NONE |
| B02.4 | H protocol/stages/documents |
| B02.1 | H baseline + L feasibility/readiness/retrieval |
| B01.2 | H loaded conversation/reflow |
| B01.3 | NONE |
| B01.7 | NONE |
| B01.4 | H stale reader + L source/chunk/neighbor |
| B01.5 | H streaming/scroll/composer |
| B01.6 | H combined layout |
| B02.2 | H delayed Search + L retrieval |
| B02.5 | H comparison race + L Lab |
| B03.1 | H variants/actions + L source reader |
| B03.2 | H streaming persistence + L session/readiness |
| B03.3 | H template request payload/no auto-send |
| B03.4 | H context race + L exact selected source |
| B04.1 | H stages + L + bounded live ledger |
| B04.2 | H states + L metadata |
| B05.1 | NONE |
| B02.3 | H; affected L gate if changed |
| B06.1 | Full H/L; conditional live review |

Local gates may reuse the compatible healthy backend, not stale task results after relevant code changes.

## 14. Task-by-task visual/browser validation matrix

| Task group | Immediate visual checks |
|---|---|
| B01.2/B01.3 | Expanded/compact, hover/focus/open/pressed, Light/Dark, EN/VI |
| B01.7 |320/390/768; More, command, locale/theme/help |
| B01.4/B01.5 | A–G; source selection, multiline, scope open, streaming |
| B01.6 | All required widths, themes/locales, focus and hit testing |
| B02.2/B02.5 | Loading, stale request, error, completed result identity |
| B03.1 | Original/variant, sources, notes, bookmark, stopped/error |
| B03.2 | Typing during stream, Stop, reload, switch |
| B03.3 | Empty metadata, validation, Cancel, conflict, Apply |
| B03.4 | Older answer/variant, changed context while palette open |
| B04.1 | Normal/cache/comparative/cancelled/trace-only |
| B04.2 | Real/offline/unknown/stale metadata; first viewport |
| B05.1 |16/24/32/48px, Light/Dark/mono |
| B02.3 | Exact profiled states before/after |
| B06.1 | Consolidated matrix and actual zoom |

All UI tasks inspect rendered production output immediately. Capture is not approval: inspect clipping, overlap, contrast, focus and semantic correspondence.

Actual browser zoom: 100/125/150/200, recording zoom and effective CSS viewport separately. Use manual browser verification if automation cannot establish the actual setting. If neither is available, leave `[!]`.

## 15. Full regression preservation list

Do not reopen or rewrite these functioning systems without a newly reproduced regression:

- Semantic icon registry and differentiated navigation.
- Palette keyboard combobox/listbox.
- Navigation preference key/schema/storage-event handling.
- Conversation schema, IndexedDB/local mirror and writer coordination.
- Immediate completed-exchange persistence.
- Citation/message/variant/source/chunk identity.
- Source-cache TTL/limits and shared request behavior.
- Original/saved variants, notes, feedback and bookmarks.
- Evidence collections and provenance.
- Library search, export, backup/import and multi-tab.
- Stop, request epochs, partial text, stale events.
- Existing template validation and placeholder guard.
- Normal/comparative query contracts.
- Retrieval presets/ranking, prompts and provider selection semantics.
- Qdrant/data/model artifacts.
- Evaluation provenance and official metrics.
- Unrelated dirty files and user browser data.

## 16. Checkpoint / quota resume protocol

After **every** task attempt:

- Record `[x]`, `[-]`, `[ ]`, `[!]` or `[~]`.
- Record actual commands/results, not intended commands.
- Record integration level actually completed.
- Record inspected browser states and artifacts.
- Record owned backend/harness/preview processes.
- Record exact blocker and next task.

Before quota/session end, checkpoint must describe partial edits and remaining checks.

Resume:

1. Read MASTER PLAN and checkpoint.
2. Inspect status/diff.
3. Verify completed-task receipts still apply.
4. Resume the first incomplete task in §11.
5. Do not restart historical phases.

Failure loop:

1. Reproduce.
2. Fix task-owned issue.
3. Rerun failed gate.
4. Do not mark `[x]` while failure remains.
5. External blocker: record `[!]`; continue only independent tasks.
6. Never build infrastructure merely to remove the blocker.

## 17. Final validation gate

### Static/unit/build

From `F`:

```powershell
bun run lint
bun run test
bun run build
```

### Browser

```powershell
bunx playwright test --project=chromium --workers=1 --retries=0
bunx playwright test --project=chromium --workers=1 --retries=0
bunx playwright test --project=firefox --workers=1 --retries=0
```

Regular config must exclude dedicated local-backend specs.

### Provider-free integration

```powershell
bun run test:e2e-integration -- --workers=1 --retries=0
```

B02.4 must ensure isolated build/preview and task-owned stack output.

### Local backend

With §5 backend and local build ready:

```powershell
bunx playwright test -c playwright.local.config.ts --workers=1 --retries=0
```

Default local tests must not invoke generation. Live checks require explicit opt-in and the remaining ledger allowance.

### Backend regression

From `R`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
git status --short
```

### Product gate

Require:

- A–G geometry and focus.
- All listed widths.
- Light/Dark and EN/VI.
- Actual zoom evidence.
- Contrast/keyboard/aria/reduced motion.
- Citation→source→indexed viewer.
- Stop/late events/drafts/variants.
- Notes/bookmarks/collections.
- Library/Search/Documents.
- Backup/import/multi-tab.
- Final production performance.

Run port-sharing suites serially.

No mandatory local/UI/zoom gate may be silently waived. Conditional live unavailability must be documented; it forbids live-performance claims.

## 18. Definition of done

Complete only when:

- Remaining production changes match this master specification.
- Desktop navigation never overlays primary content.
- Evidence and composer behave as one layout system.
- Controls are visible and accessible in both themes.
- Drafts, templates and commands preserve the correct research context.
- Search/Lab/reader reject obsolete results.
- UI reports real data/stages accurately.
- Existing user data and research behavior remain intact.
- Each task has passed its immediate integration and visual gates.
- Final mandatory validation passes on one unchanged binding.
- Performance changes are measured or explicitly unnecessary.
- Checkpoint supports every completion claim.

An unresolved mandatory gate means partial delivery, not Goal completion.

## 19. GOAL MODE — LUNA EXECUTION HANDOFF

**Authority:** This MASTER PLAN governs remaining work. Historical plans supply context only.

**Start:** V2-B01.1.

**Order:**  
B01.1 → B02.4 → B02.1 → B01.2 → B01.3 → B01.7 → B01.4 → B01.5 → B01.6 → B02.2 → B02.5 → B03.1 → B03.2 → B03.3 → B03.4 → B04.1 → B04.2 → B05.1 → B02.3 → B06.1.

**For each task:**

1. Read checkpoint and inspect task-owned diff.
2. Reproduce or establish baseline.
3. Implement the smallest allowed change.
4. Run fast/unit checks.
5. Run assigned H/L/live gate immediately.
6. Inspect rendered UI and console/network.
7. Fix task-owned regressions and rerun.
8. Record receipt and continue automatically.

**Skip:** Only verified-complete tasks whose code and receipts still satisfy this master contract.

**Partial:** Resume remaining acceptance checks; do not redo completed slices.

**Backend:** Verify ownership/readiness before reuse; one local-Qdrant process; no reload, ingestion or `.env` edits; exact temporary CORS origin; key5-only live calls; stop only owned processes.

**Refactor:** Task-bounded only. No framework, schema, retrieval, prompt, provider/deployment or persistence rewrite.

**Performance:** Baseline → attribute → patch → same workload → retain/revert. No-code-change completion is valid.

**Blockers:** Mark `[!]`, retain evidence, follow §11 independent-work rules. Never weaken a gate or create infrastructure implicitly.

**Checkpoint:** Update after every task and before session exit.

**Completion:** Mark Goal complete only when §18 is satisfied and no mandatory gate remains unresolved.

