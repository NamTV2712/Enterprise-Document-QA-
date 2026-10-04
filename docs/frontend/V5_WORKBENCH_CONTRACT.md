# V5 Research Workbench Contract

Status: `V5-00 COMPLETE`
Checkpoint date: 2026-09-13
Branch: `codex/bilingual-research-workspace`

This document is the repository-local contract for the V5 SEC RAG research
workbench sequence. It records the V5-00 baseline and the acceptance rules
that later V5 tasks must preserve. It does not claim that the target
workbench has been implemented.

## Authority and instruction separation

The attached Codex goal objective and its referenced V5 master plan are the
product-direction and execution contract for this sequence. The user's
attached `09-product-reference.png` is visual reference material: it informs
the dark evidence-first composition, persistent sources, document viewer,
highlight treatment, and information density, but it does not authorize
inventing PDF behavior, backend data, retrieval semantics, or unsupported
document representations. Repository `AGENTS.md`, `PROJECT_STATE.md`, and
the frontend design/contract documents remain the operating and compatibility
constraints.

The explicit V5 sequence is frozen as:

`V5-00 → V5-01 → V5-02 → V5-03 → V5-04 → V5-05 → V5-06 → V5-07 → V5-08`

V5-00 is baseline and contract only. No production runtime, API, persistence,
retrieval, generation, corpus, index, Qdrant, model, prompt, or PDF behavior
was changed in this checkpoint. P07 Library continuity is already complete
in the current repository truth and is preserved as-is.

## V5-00 task receipt

- Task ID: `V5-00`
- Status: `[x] COMPLETE`
- Entry point: the current research conversation at `/`.
- User intent: ask a grounded SEC 10-K question, inspect the cited source,
  and open the exact indexed evidence.
- Submitted scope: the existing fixture's all-company/all-section/top-five
  research request and its deterministic answer/evidence response.
- Available evidence: two mocked source cards, source chunks, the existing
  structured/normalized reader fixture data, the source-1 exact identity and
  hash metadata, and the deterministic `LONG_ANSWER` answer fixture.
- Primary action: select an answer citation/source button.
- Current resulting surface: the answer remains in the primary conversation
  column; retrieved sources and the indexed excerpt reader are stacked inside
  one right-side `EvidenceWorkspaceRail`/`ContextPanel`.
- Current success condition: the answer, source excerpt, and reader context
  are visible without page-level horizontal overflow, and existing exact
  reader identity/persistence behavior remains green.
- Recovery behavior: retain the stored excerpt; use the existing retry or
  exact normalized/original/SEC fallback states when available; preserve
  stale, missing, unavailable, read-only, and volatile labels instead of
  substituting nearby evidence.
- Out of scope: direct catalog/search semantics, retrieval tuning, backend
  contracts, corpus/index changes, and representation claims not present in
  the existing data.

## Current ownership and state contract

The baseline ownership map is intentionally recorded before any shell
migration:

```text
App shell
├── global header and primary navigation
├── primary research/conversation workspace
│   ├── draft and submitted-question controls
│   └── answer, citations, pipeline/diagnostic surfaces
└── EvidenceWorkspaceRail
    └── ContextPanel
        ├── retrieved source cards
        └── indexed excerpt / ContextViewer

Separate direct-document route
└── DocumentWorkspace → StructuredDocumentReader / OriginalDocumentReader
```

State and request ownership remains with the existing hooks and stores:

| Concern | Existing owner | V5-00 rule |
| --- | --- | --- |
| Research draft | `useResearchDraft` / current scope editor state | Do not duplicate or move ownership in the baseline. |
| Submitted research session | `useResearchSession` and existing App request lifecycle | Preserve async cancellation, stale-response rejection, and request identity. |
| Citation/source selection | `useEvidenceSelection` and current evidence handoff | The future shell may change presentation, not the semantic owner. |
| Reader state | `useReaderSession` / existing shared reader route | Keep content, location, representation, revision, and hash bound to the same document identity. |
| Library continuity | existing conversation/library stores and persistence adapters | P07 is complete; do not reimplement or regress it. |
| Persistence | existing IndexedDB/localStorage fallback, BroadcastChannel, and Web Locks | No new V5-00 storage schema or writer is permitted. |
| Notifications | action-local existing status/live regions | Do not add global toasts for baseline work. |
| Scroll ownership | primary message scroller, source list, reader content, and bounded overlays | No page-scroll replacement or nested scroll trap in V5-00. |

The identity tuple remains exact rather than display-derived:

`company/ticker + source document identity + revision/hash + chunk/location + representation`

An answer citation must continue to resolve to the exact source and document
revision, or to an explicit stale/missing/unavailable state. A matching title,
page label, or nearby chunk is not sufficient.

## Baseline state matrix

| State | Current evidence | Required future treatment |
| --- | --- | --- |
| Empty overview | Research shell with no submitted answer | Preserve the existing draft and scope affordances. |
| Streaming | Existing answer stream/stage state | Keep the active request owner, cancellation, and partial-answer behavior. |
| Complete | Answer with inline citations and evidence action | Keep citations actionable and identity-bound. |
| Selected | Source button opens the current evidence rail | Surface selection in Sources and Document without losing identity. |
| Reader unavailable | Existing fallback/read-only/volatile states | State the limitation; never fabricate an exact reader/PDF. |
| Stale/missing | Existing snapshot/current-source distinction | Preserve the distinction and exact failure reason. |
| Narrow/short viewport | Existing responsive rail/drawer behavior | Later V5 work must use the responsive modes in this contract. |

## Self-review risks frozen for V5

Every later checkpoint must review these risks before claiming completion:

1. Readable answer/source/document text must not be squeezed below the V5
   typography floors to make four regions fit.
2. Sources and Document must not introduce duplicate fetches, competing
   async owners, or selection state that can outlive a newer request.
3. Highlights and locations must be exact and representation-honest; a
   visual yellow mark cannot imply a PDF or page capability that is absent.
4. Lower document context must be bounded or collapsible so it cannot consume
   the canvas or create a nested scroll trap, including at short heights.
5. Direct catalog/search/document routes must retain their own semantics and
   labels; answer/retrieval labels must not be reused as a fake document
   workspace.
6. Layout decisions must use actual available geometry, not only a
   hard-coded `window.innerWidth` breakpoint.

## Measured current baseline

The new test-only capture is
`frontend/e2e/v5-00-baseline.spec.ts`. It asks the deterministic fixture
question, opens source 1, records geometry, asserts no page horizontal
overflow, and captures a screenshot at each required wide viewport. The
legacy selectors below are evidence of current composition only; they are not
the V5 target API.

| Browser | Viewport | Page scroll width | Nav | Primary column | Current evidence rail | Current source cards | Current reader inside rail |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Chromium | 1440×900 | 1440 | 216×900 | x=232, w=816, y=64, h=836 | x=1064, y=80, w=360, h=800 | 2 | x=1065, y=475.53, w=358, h=403.47 |
| Firefox | 1440×900 | 1440 | 216×900 | x=232, w=816, y=64, h=836 | x=1064, y=80, w=360, h=800 | 2 | x=1065, y=475.55, w=358, h=403.45 |
| Chromium | 1920×1080 | 1920 | 216×1080 | x=232, w=1296, y=64, h=1016 | x=1544, y=80, w=360, h=980 | 2 | x=1545, y=492.38, w=358, h=566.63 |
| Firefox | 1920×1080 | 1920 | 216×1080 | x=232, w=1296, y=64, h=1016 | x=1544, y=80, w=360, h=980 | 2 | x=1545, y=492.40, w=358, h=566.60 |

The baseline screenshots show the current light default and the existing dark
conversation state: navigation plus a primary conversation and one vertical
evidence inspector. They do not show a separate persistent Research, Sources,
and Document pane. At 1440×900 and 1920×1080 the current composition remains
within the viewport, but the primary content is narrow/centered and the right
rail stacks sources above the reader rather than presenting the target
four-region workbench.

## Post-V5 PDF representation extension

The V5 contract deliberately froze PDF behavior while the workbench was being
composed. The subsequent PDF-01 through PDF-06 implementation is a separate,
provenance-bound representation extension: it preserves the V5 layout and
reader ownership while adding an optional PDF tab, backend artifact lifecycle,
mapping sidecar, and PDF.js viewer. It does not change retrieval, generation
prompts, indexing, corpus admission, or the existing Structured/Normalized
fallback. The phase receipt and known renderer limitation are maintained in
`docs/implementation-progress.md`.

Baseline visual evidence:

- Chromium 1440×900 and 1920×1080 baseline captures are generated locally by
  the baseline test; screenshot outputs are ignored and not bundled in a clone.
- Firefox captures have the same measured composition and are written beside
  the Chromium captures by the baseline test.
- Repository visual reference:
  [`rag-workbench-master-reference-dark.png`](../ui-references/rag-workbench-master-reference-dark.png)

## V5 target acceptance contract

These are acceptance requirements for the later implementation tasks, not
V5-00 claims:

- Wide first-run mode visibly contains Navigation, Research, Sources, and
  Document at both 1440×900 and 1920×1080. No fake narrow mode, toolbar-only
  pane, or placeholder counts as success.
- The planned modules are the intended decomposition: `ApplicationWorkspace`,
  `ResearchWorkbench`, `WorkbenchLayout`, `ResearchPane`, `SourcesPane`,
  `SourceCard`, `DocumentPane`, `DocumentContextTabs`, and `PaneResizer`, with
  `useWorkbenchController`, `useWorkbenchPreferences`, and the planned
  workbench/evidence-reader libraries. Existing hooks remain the async owners.
- Pane widths support min/default/max values and actual available geometry.
  The target retains a usable Research region, a Sources region, and a
  Document canvas; the document canvas retains at least 300px where the mode
  allows it.
- Answer and document prose are at least 16px; source text is 13–14px;
  metadata is 13px; diagnostics are 12px only in Advanced; actions are 14px;
  practical interactive targets are 44px. Text is not shrunk to solve fit.
- Document lower context is bounded, collapsible, and secondary. Short
  heights downgrade or collapse secondary content before sacrificing the
  canvas or causing page overflow.
- Responsive behavior is evidence-backed: 1366/1280 use a context dock;
  1024 uses a contextual surface; 768 uses a drawer/dialog; 390 uses a
  single surface. Focus, Escape, keyboard resizer operation, reduced motion,
  light/dark themes, and EN/VI labels remain usable.
- Resizers use rAF-batched CSS-variable preview, commit-only React/storage
  writes, Home/End/Enter/reset keyboard behavior, schema-validated/clamped
  preferences, and no page horizontal overflow.
- Citation → source → document preserves exact identity, revision, hash,
  representation, location, and truthful unavailable/stale/missing fallback.
  Only Structured/Normalized representations are in V5 core; no fake PDF is
  introduced.
- Direct catalog/search/document routes retain source/document semantics and
  do not become answer/retrieval impostors.

## Frozen validation matrix

Commands were run against the current repository before this contract was
written. Results are baseline receipts, not proof of future V5 behavior.

| Area | Command | Result |
| --- | --- | --- |
| Frontend unit/component | `cd frontend; bun run test` | PASS — 48 files, 245 tests. |
| Frontend type check | `cd frontend; bun run lint` | PASS — `tsc --noEmit`. |
| Production build | `cd frontend; bun run build` | PASS — Vite transformed 1,993 modules. |
| Backend syntax | `python -m compileall src scripts configs` | PASS. |
| Backend suite | `python -m pytest tests/ -v` | PASS — 770 passed, 182 existing warnings. |
| Retained browser gate | `bunx playwright test e2e/workspace-layout.spec.ts e2e/regression.spec.ts e2e/structured-document-reader.spec.ts --workers=1 --retries=0` | PASS — 66/66 across Chromium and Firefox. |
| Provider-free local browser gate | `bun run test:e2e-local` | PASS — 6/6. |
| V5-00 capture | `bunx playwright test e2e/v5-00-baseline.spec.ts --workers=1 --retries=0` | PASS — 4/4 across Chromium and Firefox. |
| Token contrast | `bun e2e/token-contrast.mjs` | PASS — all light/dark token pairs meet WCAG thresholds. |
| Default browser suite, serial | `bunx playwright test --workers=1 --retries=0` | 155 passed, 1 Firefox timing/modal failure, 4 intentional skips. The focused retained gate above is the deterministic checkpoint gate. |
| Default browser suite, parallel | `bun run test:e2e` | 136 passed, 16 timing/shared-state failures, 4 skips. This is recorded as an operationally unstable baseline, not a green gate. |
| Real HTTP/SSE integration | `bun run test:e2e-integration` | 12 passed, 2 failed in both engines on the cited-answer assertion: the harness response did not expose the expected `Open source 1` citation button. The existing fixture/test wording mismatch is outside V5-00 and was not changed. |

The backend commands were run with the repository virtual environment where
applicable. Browser preview/test processes self-cleaned. A listener check
after the browser runs found no project listeners on ports 3000, 4173, 4175,
5173, 8000, 8765, or 8766. Existing Codex/browser infrastructure processes
were not killed or repurposed.

## Files and change boundary

V5-00 creates only a test baseline and documentation:

- `frontend/e2e/v5-00-baseline.spec.ts` — deterministic geometry/screenshot
  capture and durable no-overflow assertion.
- `docs/frontend/V5_WORKBENCH_CONTRACT.md` — this contract.
- `docs/implementation-progress.md` — V5-00 checkpoint receipt.
- `PROJECT_STATE.md` — V5-00 current-truth receipt.

No production UI runtime file, backend route/DTO, persistence schema,
retrieval/generation code, model/prompt, corpus/index/Qdrant artifact, or PDF
path changed. The pre-existing untracked `.audit-runtime/` and
`harness_stacks.txt` remain user-owned and untouched. Generated screenshots,
build output, and test reports remain ignored artifacts.

## Known limitations and rollback

- The four-pane V5 target is not implemented at V5-00; the measured current
  rail is the baseline gap.
- The real integration suite has the two existing citation-button failures
  described above. No harness or backend fix is included in this checkpoint.
- Performance claims are limited to the commands above; unverified provider,
  network, long-stream, and memory timings remain unverified.
- The historical manual native browser-chrome zoom gate at 100/125/150/200%
  remains unchanged; CSS viewport checks do not replace it.
- Rollback point: revert the V5-00 documentation and the test-only
  `frontend/e2e/v5-00-baseline.spec.ts` if the baseline receipt itself must be
  removed. Do not touch unrelated dirty files or ignored `data/`.

V5-00 exact next task: `V5-01` — create the typed workbench primitives and
resizer/preference contracts, with no shell migration beyond the approved
primitive boundary.

## V5-01 typed foundation receipt

Status: `V5-01 COMPLETE`
Checkpoint date: 2026-09-13

V5-01 adds the isolated typed foundation that the later shell can consume:

- `lib/workbench.ts` defines `WorkbenchLayoutMode`,
  `ActiveRepresentation`, pane/context types, the existing `WorkspaceTarget`
  alias, V1 pane preference schema, width limits/defaults, actual-geometry
  mode derivation, safe JSON normalization, and the non-destructive
  `sec_qa_context_rail_width_v1` → `sec_qa_workbench_panes_v1` migration.
- `lib/evidenceDeepLink.ts` parses the legacy message/citation hash and the
  V5 variant/conversation/source-key extension, and serializes exact
  selection identity without embedding source content.
- `lib/readerLocationView.ts` adapts existing Structured and Normalized
  location responses while preserving their raw response, and exposes
  idle/resolving/ready/stale/unavailable/error binding states with generation
  guards.
- `useWorkbenchController.ts` owns transient presentation/coordination only:
  layout mode, pane presentation, representation, source filter, document
  context tab, find text, focus return ID, and selected-source binding status.
  It performs no network request and does not replace `useResearchSession`,
  `useEvidenceSelection`, `useReaderSession`, or Library persistence.
- `useWorkbenchPreferences.ts` owns only non-sensitive pane widths/collapse
  preferences, valid cross-tab updates, reset, clamping, and storage-failure
  fallback. It does not persist source content, selection, document contents,
  find text, or fullscreen state.

Focused coverage is in `workbench.test.ts`, `evidenceDeepLink.test.ts`,
`readerLocationView.test.ts`, `useWorkbenchPreferences.test.tsx`, and
`useWorkbenchController.test.tsx` (18 tests). This task made no visible shell
change; the V5-00 rendered baseline remains authoritative until V5-02.

V5-01 validation: focused foundation tests `18/18` passed; the full frontend
Vitest suite passed `53 files / 263 tests`; TypeScript lint passed; the
production build passed with `1,993` transformed modules; and the V5-00
Chromium/Firefox baseline capture passed `4/4`. No backend command, API,
retrieval, model, prompt, corpus, index, Qdrant, reader representation, or
PDF behavior changed.

V5-01 exact next task: `V5-02` — shell, top bar, navigation, and scoped CSS
foundation. V5-02 must consume these seams incrementally and preserve the
current routes/readers until replacement coverage is green.

## V5-02 shell foundation receipt

Status: `V5-02 COMPLETE`
Checkpoint date: 2026-09-13

V5-02 adds the application/workbench composition boundary and a scoped shell
style layer. `App.tsx` now passes the existing `Sidebar`, `WorkspaceHeader`,
route-local `main`, non-conversation composer, and global dialog content
through `ApplicationWorkspace`. The new boundary mounts
`useWorkbenchController` and `useWorkbenchPreferences`; it does not move
request, evidence, reader, Library, or persistence ownership.

`WorkbenchLayout` observes the rendered shell and navigation geometry and
derives the presentation mode from actual available width/height and the V1
pane defaults. In the measured expanded-navigation browser fixtures the
result is `context-dock` at 1440×900 and `four-pane` at 1920×1080. The
current Sources/Document content is intentionally still the legacy
`EvidenceWorkspaceRail`; V5-02 establishes the mode/landmark seam and does
not claim the final four-pane content. The global header is scoped to the
planned 56px bar. Pane widths are exposed as CSS variables for later
first-class pane composition.

### V5-02 change boundary

- FILES CREATED:
  `frontend/src/components/workbench/ApplicationWorkspace.tsx`,
  `frontend/src/components/workbench/ResearchWorkbench.tsx`,
  `frontend/src/components/workbench/WorkbenchLayout.tsx`,
  `frontend/src/components/workbench/ApplicationWorkspace.test.tsx`,
  `frontend/src/components/workbench/WorkbenchLayout.test.tsx`,
  `frontend/src/styles/workbench.css`, and
  `frontend/e2e/v5-02-shell.spec.ts`.
- FILES CHANGED: `frontend/src/App.tsx`,
  `frontend/src/components/Sidebar.tsx`,
  `frontend/src/components/WorkspaceHeader.tsx`,
  `frontend/src/index.css`, `frontend/src/lib/i18n.tsx`, and
  `frontend/src/lib/workspace.ts`.
- FILES REMOVED: none.
- ARCHITECTURE EFFECT: separates the global application frame from the
  route-local research boundary and gives later Sources/Document panes a
  typed layout host. Existing route content and the old rail remain inside
  the host as a deliberate rollback-safe migration step.
- STATE OWNERSHIP EFFECT: the controller and preference hook are mounted at
  the shell boundary. They own only layout/presentation state and pane
  preferences; App, existing research/evidence/reader hooks, Library, and
  persistence remain authoritative for their existing concerns.
- ASYNC OWNERSHIP EFFECT: none. The shell adds no fetch, stream, reader
  request, cancellation path, or duplicate source/document load.
- API/DTO EFFECT: none. No backend file, endpoint, DTO, query, SSE event, or
  request payload changed.
- PERSISTENCE EFFECT: only the V5-01 layout-only preference hook is consumed.
  No content, selection, reader state, find query, or fullscreen state is
  stored by the shell.
- PROVENANCE EFFECT: none. Existing source/document identity and reader
  behavior pass through unchanged; no approximate highlight or fallback was
  added.
- RESPONSIVE EFFECT: the new mode attribute is driven by measured container
  and navigation geometry. The current effective legacy rail/drawer behavior
  remains unchanged while later tasks replace its presentation.
- ACCESSIBILITY EFFECT: semantic `navigation`, `header`, and `research`
  landmarks are exposed with EN/VI labels; the header remains keyboard
  operable and retains 44px-class existing controls. Existing dialog and
  focus-return behavior remains in place.
- PERFORMANCE EFFECT: one ResizeObserver is scoped to the shell layout and
  one layout-mode state update is committed after measurement. No new
  network or global state dependency was added.
- SECURITY/PDF EFFECT: no browser-exposed secret, unsafe HTML, new source
  path, PDF state, PDF control, PDF endpoint, or PDF artifact was introduced.

### V5-02 validation

- Focused shell unit tests: `4/4` assertions across the two new component
  test files (the combined focused shell/App/i18n/workspace run passed
  `5 files / 27 tests`).
- `bun run test`: PASS — `55 files / 265 tests`.
- `bun run lint`: PASS — `tsc --noEmit`.
- `bun run build`: PASS — Vite transformed `2,000` modules.
- `bunx playwright test e2e/v5-02-shell.spec.ts --workers=1
  --retries=0`: PASS — `4/4` across Chromium and Firefox. It verified
  1440×900 and 1920×1080 measured shell geometry, 56px header height,
  mode derivation (`context-dock`/`four-pane`), route compatibility,
  compact navigation, dark theme, Vietnamese labels, landmarks, keyboard
  focus, and no page horizontal overflow.
- Retained compatibility gate:
  `bunx playwright test e2e/workspace-layout.spec.ts e2e/regression.spec.ts
  e2e/structured-document-reader.spec.ts e2e/v5-02-shell.spec.ts
  --workers=1 --retries=0`: PASS — `70/70` across Chromium and Firefox,
  including reader, route, responsive, focus, Library, and performance
  checks. A single isolated Firefox reader rerun also passed `1/1` after an
  earlier long-serial timing timeout; no production reader change was made.
- `git diff --check`: PASS; Git reported only normal LF/CRLF normalization
  warnings for existing journal/source files.

### V5-02 runtime and visual validation

The production preview was inspected at 1440×900 and 1920×1080 in Chromium
after the final 56px-bar change. Navigation, the global toolbar, overview
canvas, scope surface, and composer remained visible and inside the viewport.
The screenshots are the V5-02 shell captures
`frontend/e2e/screenshots/v5-02-shell-1440x900.png` and
`frontend/e2e/screenshots/v5-02-shell-1920x1080.png` (ignored browser
artifacts). This review confirms shell stability and the 56px header; it
does not claim that the final Sources + Document four-pane content is
implemented yet.

Known limitations: the old vertical `EvidenceWorkspaceRail` still presents
Sources and the reader together until V5-03 and V5-04; final pane resizing,
collapse, source filtering, exact synchronization, and route-specific
workbench handoffs remain future tasks. The existing V5-00 integration and
parallel-browser limitations remain unchanged.

Unrelated dirty state was preserved: `.audit-runtime/` and
`harness_stacks.txt` remain untouched, and ignored `data/` was not accessed
or modified. Playwright/Vite preview processes were task-owned and
self-cleaned; the final listener check found no project listeners on ports
`3000`, `4173`, `4175`, `5173`, `8000`, `8765`, or `8766`.

ROLLBACK POINT: remove the V5-02 shell components/tests/style import and
restore the App root composition/header height/data landmarks, while leaving
the V5-01 primitives and V5-00 receipts intact. No data migration or backend
rollback is required.

V5-02 exact next task: `V5-03` — replace the legacy rail's source list with a
first-class Sources pane. Do not remove the legacy rail until replacement
coverage and the required repository-wide reference sweep are green.

## V5-03 first-class Sources pane receipt

Status: `V5-03 COMPLETE`
Checkpoint date: 2026-09-13

V5-03 replaces the production answer source-list renderer with one shared
`SourcesPane`/`SourceCard` implementation. The pane owns source-list rendering,
literal search, citation-order preservation, All/Cited/Saved answer filtering,
section navigation, collapse state, list keyboard navigation, and focus return.
The card renders filing identity, section, readable excerpt, representation/state
facts, Save Evidence, Open document, and an Advanced ranking disclosure. Ranking
scores are never described as confidence. `DocumentViewer` remains the existing
reader/async owner and selected-source detail remains a single-source flow.

### V5-03 change boundary

- FILES CREATED: `frontend/src/components/workbench/WorkbenchContext.tsx`,
  `SourceCard.tsx`, `SourcesPane.tsx`, the focused
  `SourcesPane.test.tsx`, `frontend/src/lib/sourcePresentation.ts`, and
  `frontend/e2e/v5-03-sources.spec.ts`.
- FILES CHANGED: `frontend/src/components/workbench/ApplicationWorkspace.tsx`,
  `frontend/src/components/ChatMessage.tsx`,
  `frontend/src/components/ContextPanel.tsx`,
  `frontend/src/components/EvidenceWorkspaceRail.tsx`, and
  `frontend/src/styles/workbench.css`. The dead source renderer inside
  `ContextPanel` was removed; no file was deleted.
- PRODUCTION REFERENCE SWEEP: no production component imports
  `SourcesPanel.tsx`; its direct compatibility unit tests remain the only
  repository references outside the retained module. `RetrievedSources` and the
  duplicate `ContextPanel` card are no longer runtime render paths. No
  destructive legacy data migration was performed.
- ARCHITECTURE EFFECT: `ApplicationWorkspace` provides the workbench context;
  `SourcesPane` is the first-class source surface and `SourceCard` is the
  single shared source-card renderer. `ContextPanel` composes that pane with
  the existing reader until the later Document-pane task.
- STATE OWNERSHIP EFFECT: the workbench controller owns presentation/filter
  coordination; `App`/`useEvidenceSelection` remains authoritative for exact
  selected answer/source identity. Evidence collection persistence remains owned
  by `evidenceCollections`. The pane does not persist selection, find,
  fullscreen, or reader state.
- ASYNC OWNERSHIP EFFECT: none added. Source cards do not fetch document content.
  `ContextPanel`/`DocumentViewer` retains detail, nearby-chunk,
  abort, retry, and reader-generation ownership.
- API/DTO EFFECT: none. No backend file, endpoint, DTO, query, SSE event, request
  payload, retrieval, model, prompt, index, corpus, Qdrant, or PDF behavior changed.
- PERSISTENCE EFFECT: Save Evidence calls the existing writer and provenance
  snapshot helper. The pane listens to the existing evidence update/storage
  events and derives saved state by exact source identity/content matching;
  no new storage schema or writer was introduced.
- PROVENANCE EFFECT: source order, citation identity, chunk identity, stored
  snapshot metadata, and selected-source handoff remain exact. Stale and
  unavailable states are explicit; no fuzzy source selection or invented
  document/PDF location was added.
- RESPONSIVE EFFECT: the shared pane renders in the existing inline rail and
  drawer surfaces without changing the existing mode thresholds. Catalog/search/
  retrieval origins suppress answer-only category filters; answer origin may
  expose All/Cited/Saved.
- ACCESSIBILITY EFFECT: source cards have stable labels, pressed selection,
  state descriptions, 44px-class action targets, list semantics, and exact
  ArrowUp/ArrowDown/ArrowLeft/ArrowRight/Home/End/Enter behavior. Deep-link
  focus expands the pane and focuses the exact citation target.
- PERFORMANCE EFFECT: one source list computes visible indexes locally; no
  new network request or reader lifecycle was added. Saved-state refresh is
  event-driven and scoped to the supplied source collection.
- SECURITY/PDF EFFECT: no new external URL, unsafe HTML, secret, document
  acquisition path, PDF control, or PDF artifact was introduced.

### V5-03 validation

- `bun run test` — PASS, `56 files / 271 tests`.
- `bun run lint` — PASS, `tsc --noEmit`.
- `bun run build` — PASS, Vite transformed `2,003` modules.
- `bunx playwright test e2e/v5-03-sources.spec.ts --workers=1
  --retries=0` — PASS, `2/2` across Chromium and Firefox.
  It verified the rendered source pane, exact source identity, Save Evidence,
  All/Cited/Saved policy, keyboard End/Enter selection, single-source reader
  handoff, and saved-state filtering.
- V5 baseline compatibility slice
  (`e2e/v5-00-baseline.spec.ts e2e/v5-02-shell.spec.ts
  e2e/v5-03-sources.spec.ts`) — PASS, `10/10` across Chromium and
  Firefox.
- Full serial frontend browser gate
  (`bunx playwright test --workers=1 --retries=0`) discovered
  `166` tests: `160 passed, 4 skipped, and 2 Firefox-only timing
  failures` in pre-existing V4 reader readiness checks. The failed
  `document-workspace` and `structured-document-reader` specs
  passed in an isolated Firefox rerun, `3/3`; no production reader
  change was made.
- `git diff --check` — PASS, with only normal LF/CRLF normalization
  warnings.

### V5-03 runtime and visual validation

The rebuilt production preview was inspected at 1440×900 in Chromium using
`frontend/e2e/screenshots/v5-03-sources-1440x900.png`. The pane stayed inside
the viewport with no horizontal overflow; the source stack, filters, search,
selection styling, Save Evidence action, and reader handoff were visible. The
existing vertical inspector still scrolls the source stack above the reader;
the final independent Sources/Document pane geometry is intentionally deferred
to V5-04/V5-05.

Known limitations: `SourcesPanel.tsx` remains as a compatibility-only module
because its direct tests/embedders are still repository references; production
answer rendering no longer imports it. The answer inspector still uses the
existing `ContextPanel` shell and `DocumentViewer` until the Document
pane replacement and route-handoff tasks. Backend, data, and PDF behavior were
not revalidated because no backend/data/PDF code changed; the prior backend
baseline remains authoritative.

Unrelated dirty state was preserved: `.audit-runtime/` and
`harness_stacks.txt` were untouched, and ignored `data/` was not accessed or
modified. Playwright/Vite preview processes were task-owned and self-cleaned.

ROLLBACK POINT: remove the V5-03 `SourcesPane`/`SourceCard` integration, workbench
context, source-presentation helper, source-pane styles, tests, and focused
browser spec; restore the previous `ChatMessage` fallback and
`ContextPanel` source-list call while leaving V5-00/V5-01/V5-02 and all
backend/data/persistence state intact.

V5-03 exact next task: `V5-04` — establish the first-class Document pane
and preserve the existing reader lifecycle/provenance contract while the
source pane remains the single source-list owner.

## V5-04 shared Document pane and reader adaptation receipt

Status: `V5-04 COMPLETE`
Checkpoint date: 2026-09-13

V5-04 establishes the shared Document pane seam around the existing structured
and normalized readers. Production answer, catalog, and search document
surfaces now enter through `DocumentPane`; the adapter coordinates
workbench representation, lower context tab, find-query, active-pane, and
expand/restore state without taking ownership of document identity or reader
transport. `DocumentWorkspace` remains the compatibility-capable
reader shell underneath that seam.

### V5-04 change boundary

- FILES CREATED: `frontend/src/components/workbench/DocumentPane.tsx`,
  `DocumentContextTabs.tsx`, their focused unit tests, and
  `frontend/e2e/v5-04-document.spec.ts`.
- FILES CHANGED: `DocumentWorkspace.tsx`,
  `StructuredDocumentReader.tsx`,
  `OriginalDocumentReader.tsx`, `ContextPanel.tsx`,
  `App.tsx`, `document-reader.css`, and the hermetic
  `frontend/e2e/fixtures.ts` original-reader routes used by the
  acceptance test.
- PRODUCTION REFERENCE SWEEP: App and ContextPanel no longer import
  `DocumentWorkspace` directly; `DocumentPane` is the
  production document entry point and owns no duplicate target or fetch path.
  The underlying workspace remains available for compatibility consumers and
  direct tests.
- ARCHITECTURE EFFECT: the pane has one authoritative identity/header,
  representation switcher for genuine Structured and Normalized text only,
  embedded reader canvas, local-to-active-representation find controls, and
  Evidence/Metadata/conditional Notes context tabs. Indexed excerpt remains
  evidence context, never a representation tab. Existing legacy
  Document/Indexed excerpt/Metadata tabs remain available only through the
  compatibility-capable workspace mode.
- STATE OWNERSHIP EFFECT: when mounted in ApplicationWorkspace, the existing
  workbench controller owns active representation, context tab, find query,
  and active pane coordination. Direct consumers receive a local fallback.
  Route target state remains in App; source identity and evidence persistence
  remain in their existing owners; expansion is intentionally transient.
- ASYNC OWNERSHIP EFFECT: none added. Structured and normalized readers still
  own their existing manifest/content/search/location requests, abort
  controllers, request IDs, reader generations, coverage, and table truth.
  The pane only passes controlled presentation values through.
- API/DTO EFFECT: none in production. No backend file, endpoint, DTO, query,
  SSE event, retrieval, generation, model, prompt, index, corpus, Qdrant, or
  PDF behavior changed. Test-only fixture routes cover the already-existing
  original-reader contract.
- PERSISTENCE EFFECT: none. Find, representation, context-tab, and
  expand/restore state are not persisted; existing Save Evidence behavior and
  provenance writers remain unchanged.
- PROVENANCE EFFECT: source identity, citation, selected excerpt, revision
  binding, exact/ambiguous/not-found semantics, external SEC links, coverage,
  and fallback messaging remain reader-owned and truthful. No PDF page,
  approximate highlight, or fake document content was added.
- RESPONSIVE EFFECT: the shared shell uses one reader scroll surface plus a
  bounded lower context surface. Container-aware wrapping keeps the
  representation and restore controls usable inside the existing narrow
  evidence inspector; expansion starts below the global 56px bar to avoid
  pointer interception.
- ACCESSIBILITY EFFECT: representation buttons expose `aria-pressed`,
  context tabs use tablist/tab/tabpanel semantics with roving focus and
  Arrow/Home/End navigation, normalized embedded readers expose an explicit
  accessible label, and expand/restore controls expose stateful labels.
- PERFORMANCE EFFECT: no new production request or global listener was
  introduced. The existing reader generation and cancellation paths are
  reused by reference.
- SECURITY/PDF EFFECT: no unsafe HTML, secret, new acquisition path,
  external URL, PDF control, or PDF artifact was introduced. The verified SEC
  link remains the existing reader link.

### V5-04 validation

- `bun run test` — PASS, `58 files / 277 tests`.
- `bun run lint` — PASS, `tsc --noEmit`.
- `bun run build` — PASS, Vite transformed `2,005` modules.
- `bunx playwright test e2e/v5-04-document.spec.ts
  --project=chromium --workers=1 --retries=0` — PASS, `1/1`.
- The same V5-04 spec passed in Firefox, `1/1`; together the
  focused acceptance gate is `2/2`.
- V5-00/V5-02/V5-03/V5-04 serial slice — PASS, `12/12` across
  Chromium and Firefox.
- Existing document-workspace and structured-reader compatibility slice —
  PASS, `6/6` across Chromium and Firefox.
- `git diff --check` — PASS, with only normal line-ending
  normalization warnings.

### V5-04 runtime and visual validation

The rebuilt Chromium preview was inspected at 1440×900 using
`frontend/e2e/screenshots/v5-04-document-1440x900.png`. The
shared pane visibly retains filing identity, representation controls,
Evidence/Metadata context, the normalized reader handoff, and restore
behavior. The narrow contextual surface stayed within the viewport after a
container-query fix for header wrapping. The browser acceptance flow also
verified that the find query survives representation switching, Notes is not
invented, and page/zoom/PDF controls are absent.

Known limitations: the shared Document pane still composes below the existing
vertical `EvidenceWorkspaceRail` when opened from the answer
inspector; independent Sources/Document geometry, resizers, collapse policy,
and exact cross-pane synchronization remain V5-05/V5-06 work. The
compatibility `DocumentWorkspace` module remains intentionally
present. Backend/data/PDF behavior was not rerun because no production path
in those areas changed; the existing baseline remains authoritative.

Unrelated dirty state was preserved: `.audit-runtime/`,
`harness_stacks.txt`, and ignored `data/` were untouched.
Task-owned browser/preview processes self-cleaned.

ROLLBACK POINT: remove the `DocumentPane`/context-tab adapter,
reader controlled-prop seam, V5-04 styles/tests/fixture routes, and the App
and ContextPanel entry-point substitutions; restore the previous
DocumentWorkspace imports while leaving V5-00 through V5-03, backend, data,
reader transport, provenance, and persistence state intact.

V5-04 exact next task: `V5-05` — wire the first-class Sources and
Document panes into the responsive workbench geometry and explicit
source-to-document synchronization contract.

## V5-05 exact synchronization and deep-link receipt

Status: `V5-05 COMPLETE`
Checkpoint date: 2026-09-13

### Task-semantics gate

- INTENT: make a selected citation open the shared Document pane at the
  selected source and preserve that exact identity across Structured and
  Normalized text representations and canonical deep links.
- SCOPE: presentation/controller coordination, existing reader location
  clients, exact identity validation, source-resolution fallback states, and
  hermetic frontend acceptance coverage only.
- OUT OF SCOPE: retrieval, generation, prompts, models, indexes, corpus,
  Qdrant, backend routes/DTOs/SSE, acquisition, persistence schemas, and PDF
  behavior.
- EVIDENCE: source key, chunk ID/hash, document ID, source-set revision,
  source document ID, and document revision are checked before a mark is
  rendered or a source is reported as resolved.
- ACTION/RESULT: `SourcesPane` opens the shared Document pane; `App` resolves
  exact old/new deep-link targets; readers resolve missing live chunk hashes
  through the existing cache and emit generation-guarded status events;
  stale, ambiguous, unavailable, not-found, and error states remain visible
  without an invented highlight or fall-forward selection.
- SUCCESS/RECOVERY: an exact target gets one verified yellow mark in the
  active representation; a mismatch or unavailable identity leaves the
  selected source visible with a truthful reason and no mark. Historical
  snapshots without a hash are unavailable and are never silently refetched
  as current content.
- OWNERS: `App` owns route identity, `DocumentPane`/workbench controller own
  transient coordination, readers own manifest/content/location requests and
  cancellation, the existing API client owns transport, and existing
  evidence persistence/provenance owners remain unchanged.
- SCROLL/FOCUS: exact structured ranges still focus the matching block;
  representation changes retain the selected source and reader status; no
  new page/PDF scroll semantics were introduced.

### V5-05 change boundary and risk review

- CREATED: `frontend/src/hooks/useReaderEvidenceSource.ts` and its tests,
  `frontend/src/lib/api.test.ts`, and
  `frontend/e2e/v5-05-sync.spec.ts`.
- CHANGED: `App.tsx`, `ContextPanel.tsx`, `SourcesPane.tsx`,
  `DocumentWorkspace.tsx`, both reader components and their focused tests,
  `readerLocationView.ts` and tests, `useWorkbenchController.ts`, and the
  hermetic normalized-reader fixtures. No file was deleted.
- HIGH-RISK CHECKS: hash/document-revision drift, late responses after rapid
  source switching, invalid or legacy deep-link fallback, saved snapshots
  without verifiable identity, and direct Documents/Search route compatibility.
  Each is covered by identity guards, request generations/abort signals,
  exact target matching, explicit unavailable state, and browser regression.
- DEEP LINKS: the canonical link retains the legacy evidence base and adds
  encoded conversation, variant, citation, and source-key identity. Unknown
  conversation/message/variant/citation/source targets close or mark the
  evidence target unavailable; they do not select a neighboring or latest
  source.
- API/ASYNC: only existing `getCachedChunkDetail`, structured reader-location,
  and normalized original-location client paths are used. No endpoint, DTO,
  query, SSE, request owner, or server behavior changed. Reader generations,
  request IDs, and abort controllers suppress late results.
- PERSISTENCE/PROVENANCE: no new storage or schema was added. Existing
  saved-evidence snapshots remain authoritative; missing hash metadata is
  treated as unavailable. Source identity, revision binding, SEC links,
  exact/ambiguous/not-found semantics, and coverage messaging remain intact.
- RESPONSIVE/A11Y: V5-05 does not redesign pane geometry; it keeps the
  existing responsive shell and reader scroll surfaces. Status is exposed
  through live reader messages, source actions retain accessible labels, and
  both Structured and Normalized controls remain keyboard-addressable.
- PERFORMANCE/SECURITY/PDF: detail resolution reuses the existing cache and
  adds no global listener or acquisition path. No unsafe HTML, secret, new
  external URL, PDF control, approximate mark, or fabricated page content was
  introduced.

### V5-05 validation receipt

- `bun run test -- --reporter=dot` — PASS, `60 files / 288 tests`.
- `bun run lint` — PASS, `tsc --noEmit`.
- `bun run build` — PASS, Vite transformed `2,007` modules.
- V5-00/V5-02/V5-03/V5-04/V5-05 serial Chromium/Firefox slice — PASS,
  `16/16` with one worker and zero retries.
- V5-05 focused browser flow — PASS in both engines: exact source handoff,
  one structured mark, one normalized mark, canonical source-key link, and
  reload without fall-forward.
- Existing Documents/Search exact-chunk compatibility regression — PASS,
  `2/2` across Chromium and Firefox.
- Focused reader/API coverage includes exact, ambiguous, stale hash,
  not-found/409, unavailable historical snapshot, normalized nested
  identity, old/new deep-link parsing, direct route targets, and rapid source
  switching. `StructuredDocumentReader.test.tsx` passed `6/6` after the race
  guard was added.
- `git diff --check` — PASS; output contains only normal LF/CRLF
  normalization warnings. The final listener check was empty for project
  ports `3000`, `4173`, `4175`, `5173`, `8000`, `8765`, and `8766`.

### V5-05 rendered validation and handoff

The rebuilt Chromium preview was captured and inspected at 1440×900 in
`frontend/e2e/screenshots/v5-05-sync-1440x900.png`. The answer, source
inspector, selected evidence, shared document identity, representation
switcher, and verified reader context were legible and inside the viewport.
Existing V5 shell coverage continues to cover compact navigation, EN/VI,
dark theme, keyboard focus, and responsive widths; V5-05 introduced no
geometry change.

Unrelated dirty work was preserved: `.audit-runtime/`,
`harness_stacks.txt`, and ignored `data/` were untouched. No backend,
retrieval, generation, model, prompt, index, corpus, Qdrant, persistence, or
PDF behavior changed.

ROLLBACK POINT: remove the V5-05 reader-location validation/events, cached
source resolver, canonical target resolution, and focused tests/fixtures;
restore the prior source-open/deep-link handoff while leaving V5-00 through
V5-04, backend, data, reader transport, provenance, persistence, and PDF
behavior intact.

V5-05 exact next task: `V5-06` — implement the responsive Sources + Document
geometry, resizers, collapse policy, and pane-level visual acceptance without
moving reader or backend ownership.

## V5-06 responsive layout, resizers, and collapse receipt

Status: `V5-06 COMPLETE`
Checkpoint date: 2026-09-13

### Task-semantics gate

- INTENT: make the verified Research + Sources + Document workstation real at
  wide desktop sizes, then downgrade by measured available geometry when the
  readable minimums cannot fit.
- SCOPE: workbench composition, navigation default, pane width preferences,
  pointer/keyboard resizers, collapse/restore, bounded document context, and
  hermetic browser validation.
- OUT OF SCOPE: query/SSE, retrieval, generation, models, prompts, indexes,
  corpus, Qdrant, backend/API/DTO behavior, reader transport, provenance
  semantics, persistence schema, acquisition, and PDF behavior.
- OWNERSHIP: `WorkbenchLayout` measures the shell and selects the mode;
  `useWorkbenchPreferences` owns only V1 layout widths/collapse state;
  `PaneResizer` owns transient pointer motion and commits on pointer-up;
  `SourcesPane`, `DocumentPane`, and existing readers retain their content,
  identity, request, cancellation, and persistence boundaries.

### Geometry and responsive contract

- Header remains 56px. Desktop navigation defaults to compact 56px below
  1600px and expanded 216px at or above 1600px when no explicit user
  preference exists; an explicit stored preference remains authoritative.
- Four-pane mode uses Research as the flexible track (minimum 624px at the
  acceptance defaults), Sources 304px (bounded 280–360px), two 8px structural
  splitters, and Document 440px (bounded 400–560px). The splitter pointer hit
  area is 24px without changing its measured 8px track.
- Measured acceptance geometry is exact at 1440×900 with compact navigation:
  Research 624px, Sources 304px, Document 440px, splitters 8px each; and at
  1920×1080 with expanded navigation: Research 944px, Sources 304px,
  Document 440px, splitters 8px each.
- At 1366×768 and 1280×800, the 440px context dock exposes an accessible
  Sources/Document tab switcher and mounts only the active contextual surface.
  At 1024×768 the measured mode is contextual-surface; below 1024 it is a
  drawer or single-surface mode with the existing modal focus lifecycle.
- The mode decision uses actual shell width, measured navigation width,
  requested pane widths, separators, and usable height. Widening a pane beyond
  the available four-pane budget therefore downgrades the presentation rather
  than shrinking research text or creating page overflow.

### Interaction, persistence, and document height contract

- `sec_qa_workbench_panes_v1` stores only schema V1 Sources/Document widths and
  collapse booleans. The old
  `sec_qa_context_rail_width_v1` value migrates once into Sources width,
  clamped to 280–360px, and the old key remains untouched.
- Pointer moves update layout CSS variables in `requestAnimationFrame`; React
  state and storage update only on pointer-up. Pointer cancel restores the
  starting live width. Arrow keys move by 16px; Home/End select min/max; Enter
  or Space collapses/restores; double-click and the menu Reset return to the
  pane default. Wider/Narrower are available without dragging.
- Wide first-run state keeps Sources and Document visible. Explicit collapse
  remembers the prior width and exposes a 44px-class restore target. Selecting
  a source keeps the exact existing identity and reveals the corresponding
  reader without substituting another source.
- The Document reader region has a 300px minimum in the workbench. Its lower
  Evidence/Metadata/Notes context is an explicit collapsible surface with
  `max-height: min(17rem, 32%)`; on a short document track it starts collapsed
  and is capped to a 3.25rem compact header. No page-level overflow workaround
  or drag-only control was added.

### V5-06 change boundary and risk review

- CREATED: `frontend/src/components/workbench/PaneResizer.tsx` and
  `frontend/e2e/v5-06-layout.spec.ts`.
- CHANGED: `ApplicationWorkspace.tsx`, `WorkbenchLayout.tsx`, `ContextPanel.tsx`,
  `DocumentWorkspace.tsx`, `App.tsx`, `useNavigationLayout.ts`,
  `components.css`, `document-reader.css`, `workbench.css`, `README.md`,
  `DESIGN.md`, and hermetic non-Apple reader fixture fallbacks. No production
  backend or reader endpoint changed.
- HIGH-RISK CHECKS: exact 1440/1920 track math, compact/expanded nav drift,
  live resize jank, collapse restoration, short-height context dominance,
  modal focus return, and context-dock tab ownership. These are covered by
  geometry assertions, storage timing checks, keyboard controls, and modal
  transition assertions in both engines.
- REDUCED MOTION: no new motion is required for layout correctness; splitter
  and switcher transitions are disabled under `prefers-reduced-motion`.
- SECURITY/PROVENANCE/PDF: no untrusted HTML, source substitution, new URL or
  acquisition path, secret, PDF control, page semantics, or provenance change
  was introduced.

### V5-06 validation receipt

- `bun run test -- --reporter=dot` — PASS, `60 files / 289 tests`.
- `bun run lint` — PASS, `tsc --noEmit`.
- `bun run build` — PASS, Vite transformed `2,008` modules.
- `bunx playwright test e2e/v5-02-shell.spec.ts --project=chromium` — PASS,
  `2/2`.
- `bunx playwright test e2e/v5-05-sync.spec.ts --project=chromium` — PASS,
  `2/2`; the exact structured/normalized synchronization remained green after
  the four-pane reader mount.
- `bunx playwright test e2e/v5-06-layout.spec.ts --project=chromium` — PASS,
  `3/3`.
- `bunx playwright test e2e/v5-06-layout.spec.ts --project=firefox` — PASS,
  `3/3`.
- The V5-06 browser slice measured no document-level horizontal overflow and
  verified pointer storage remains unchanged during motion, then changes only
  after commit. Project listener checks remained clean after task-owned
  preview/browser cleanup.

### V5-06 rendered validation and handoff

The rebuilt Chromium preview was visually inspected at
`frontend/e2e/screenshots/v5-06-four-pane-1440x900.png` and
`frontend/e2e/screenshots/v5-06-four-pane-1920x1080.png`. Both show the
Research answer, citation-ordered Sources cards, and the shared Document
reader simultaneously with readable text, bounded local scroll regions, and
the existing exact evidence correspondence status. The dock and modal
transitions were checked in the same browser run; Firefox passed the same
interaction matrix.

Unrelated dirty work was preserved: `.audit-runtime/`, `harness_stacks.txt`,
and ignored `data/` were untouched. No backend, retrieval, generation, model,
prompt, index, corpus, Qdrant, reader transport, provenance, persistence, or
PDF behavior changed.

ROLLBACK POINT: remove `PaneResizer`, the workbench sibling composition,
responsive CSS, navigation default, document collapse affordance, and the
V5-06 browser/fixture/docs changes; restore the prior ContextPanel rail
composition while retaining V5-00 through V5-05 and all data/backend/reader
boundaries.

V5-06 exact next task: `V5-07` — integrate Documents, Search, Retrieval Lab,
and Library handoffs through the shared workbench presentation boundary.

## V5-07 route handoffs and analyst return paths

Status: `V5-07 COMPLETE`
Checkpoint date: 2026-09-13

### Task-semantics gate

- INTENT: make Documents, Search, Retrieval Lab, and Library use the shared
  workbench document surface without losing route-local state or the exact
  action that opened the surface.
- SCOPE: typed route targets, catalog/result presentation, Save Evidence
  actions, shared contextual document composition, and return-focus behavior.
- OUT OF SCOPE: retrieval ranking/semantics, generation, models, prompts,
  indexes, corpus, Qdrant, backend/API/DTO behavior, new Library schema,
  persistence migration, reader transport, acquisition, and PDF behavior.
- OWNERSHIP: App remains the route/identity coordinator; each route keeps its
  existing fetch, cache, retrieval, and persistence owner; the workbench
  controller mirrors presentation target and return focus only.

### Handoff contract

- Documents keeps the catalog mounted in Research while a catalog filing is
  open in the shared Document pane. The selected catalog opener is restored
  exactly after Back.
- Search result cards expose filing date and company identity, distinguish
  indexed-excerpt inspection from opening the Document workspace, and expose
  Save Evidence through the existing writer. Search returns to the exact
  result action that opened the document.
- Retrieval Lab preserves Analyst/Advanced diagnostics and score semantics.
  Its document action emits a typed `RetrievalWorkspaceTarget`; Save Evidence
  continues to use the existing source snapshot path and returns to the exact
  candidate action.
- Library reuses the completed P07 saved variant/evidence behavior. Saved
  evidence opens with exact source identity and retains historical snapshot
  truth; current verified-source actions remain distinct from unavailable or
  stale snapshot content. Closing the evidence inspector restores the exact
  Library invoker.
- Route targets use the shared contextual slot at four-pane/context-dock
  widths and the existing modal focus lifecycle at narrower modes. No route
  mounts a second reader or invents a new document schema.

### V5-07 change boundary and risk review

- CREATED: `frontend/src/components/workbench/RouteDocumentContext.tsx` and
  `frontend/e2e/v5-07-handoffs.spec.ts`.
- CHANGED: `App.tsx`, `ApplicationWorkspace.tsx`, `WorkbenchLayout.tsx`,
  `DocumentExplorerPanel.tsx`, `SearchWorkspace.tsx`,
  `RetrievalLabPanel.tsx`, `EvidenceCollectionsPanel.tsx`,
  `DocumentWorkspace.tsx`, `types.ts`, workbench CSS, and focused
  fixtures/tests. The only fixture change adds existing normalized-reader
  identity fields for hermetic route coverage.
- HIGH-RISK CHECKS: route-local state staying mounted, typed retrieval target
  identity, Search indexed-vs-document action semantics, Library snapshot
  truth, shared context placement, and exact focus restoration. These are
  covered by focused unit tests and four end-to-end journeys in both engines.
- ACCESSIBILITY: catalog, result, candidate, and saved-evidence openers have
  stable accessible names/IDs; route Document back controls are the modal
  initial focus target and restore the exact invoker on close.
- SECURITY/PROVENANCE/PDF: no untrusted HTML, new acquisition path, secret,
  source substitution, fuzzy match, PDF control, or fabricated page content
  was introduced. Existing source identity, revision, stale/unavailable, and
  evidence persistence semantics remain authoritative.

### V5-07 validation receipt

- `bun run test -- --reporter=dot` — PASS, `60 files / 291 tests`.
- `bun run lint` — PASS, `tsc --noEmit`.
- `bun run build` — PASS, Vite transformed `2,009` modules.
- `bunx playwright test e2e/v5-07-handoffs.spec.ts --project=chromium` —
  PASS, `4/4`.
- `bunx playwright test e2e/v5-07-handoffs.spec.ts --project=firefox` —
  PASS, `4/4`.
- Existing affected browser compatibility checks passed: the Documents/Search
  exact-chunk regression `1/1` and V5-04 document acceptance `1/1` in
  Chromium after updating only stale context-dock assertions.
- Focused route unit coverage passed `4 files / 35 tests`, including Search
  Save Evidence, typed Retrieval target, catalog return focus, and existing
  Library saved variant/snapshot behavior.

### V5-07 rendered validation and handoff

The V5-06 inspected 1440×900 and 1920×1080 renders remain the visual baseline:
the Research answer, citation-ordered Sources, and shared Document surface
stay simultaneously readable. V5-07 browser validation additionally verifies
the catalog, Search, Retrieval, and Library route handoffs within that shared
composition, with no document-level overflow or duplicate reader surface.

Unrelated dirty work was preserved: `.audit-runtime/`, `harness_stacks.txt`,
and ignored `data/` were untouched. No backend, retrieval, generation, model,
prompt, index, corpus, Qdrant, reader transport, provenance, persistence,
acquisition, or PDF behavior changed.

ROLLBACK POINT: remove `RouteDocumentContext`, typed route-target additions,
route handoff callbacks, stable return-focus IDs, scoped route CSS, and the
V5-07 fixture/tests; restore the previous route-local document/evidence entry
points while retaining V5-00 through V5-06 and all domain owners.

V5-07 exact next task: `V5-08` — complete visual, accessibility, browser,
performance, and regression closure with measured receipts.

## V5-08 closure — visual, accessibility, browser, performance, and regression

Status: `V5-08 COMPLETE`
Checkpoint date: 2026-09-13

### Closure contract

- V5-00 through V5-07 are complete in order. V5-08 closes the rendered
  workbench without changing query/SSE, retrieval, generation, model, prompt,
  index, corpus, Qdrant, acquisition, reader transport, provenance, or PDF
  behavior.
- Wide visual truth is the shared four-pane workbench: at 1440×900 the
  measured tracks are compact navigation 56px, Research 624px, Sources
  304px, two 8px splitters, and Document 440px; at 1920×1080 navigation is
  216px and Research is 944px with the same contextual tracks.
- 1366×768 and 1280×800 use the accessible context dock; 1024×768 and the
  explicit 1366×520 short-height case use the contextual surface; 768px and
  390px use drawer/single-surface behavior. 320px and 640px smoke coverage
  keep the workspace usable without page-level horizontal overflow.
- The 1440/1920 receipts show simultaneous Research, Sources, and Document
  surfaces, selected AAPL evidence, a structured reader canvas, and the exact
  amber/yellow evidence mark from the hermetic range fixture. The reader grid
  is a non-shrinking content track so the 1440×900 canvas and PDF limitation
  cannot overlap.
- The document pane supports only Structured and Normalized text. PDF remains
  explicitly unavailable/deferred; no PDF page or coordinate semantics are
  fabricated.

### Validation receipt

- Backend: `.venv\Scripts\python.exe -m pytest -q` — PASS, `770 passed`,
  `182 warnings`. No backend source or contract changed in V5.
- Frontend: `bun run test -- --reporter=dot` — PASS, `60 files / 292 tests`;
  `bun run lint` — PASS (`tsc --noEmit`); `bun run build` — PASS, `2,009`
  modules transformed.
- V5 acceptance slice (`v5-00`, `v5-02` through `v5-07`) — PASS, `15/15`
  Chromium and `15/15` Firefox, one worker, zero retries. The V5-06
  responsive slice itself is `3/3` in each engine, including 1366×520.
- Full app suite `e2e/app.spec.ts` — PASS, `38/38` Chromium and `38/38`
  Firefox. Full regression `e2e/regression.spec.ts` — PASS, `31/31`
  Chromium and `31/31` Firefox. These runs cover route persistence, citation
  handoff, theme/locale transitions, 1920/1440/1366/1280/1272/1024/768/640/
  390/320 widths, dialogs, contrast, reduced motion, and no-overflow checks.
- Synthetic performance `e2e/workspace-performance.spec.ts` — PASS, `2/2`
  executed and `2` provider-dependent checks skipped in each engine. The
  latest Chromium receipt measured warm composer p95 `14.00ms`, warm view
  switch p95 `42.90ms`, final Markdown layout p95 `175.70ms`, and source
  switching/reader p50 `166.10ms`, p95 `204.30ms` (`n=31`, no fixed budget).
  Firefox measured warm composer p95 `27.00ms`, warm view switch p95 `89.00ms`,
  final Markdown layout p95 `314.00ms`, and source switching/reader p50
  `143.00ms`, p95 `164.00ms`. The fixed warm-control budgets remain below
  100ms for composer and 200ms for view switch.
- The production regression performance checks stayed below their fixed
  budgets: Chromium Library search p95 `62.67ms` and 200-message composer
  p95 `43.50ms`; Firefox `68.21ms` and `40.00ms` respectively, against
  200ms/100ms budgets.
- Accessibility checks passed: overview Axe serious/critical scan has no
  violations; regression color-contrast scan passed; keyboard tab/splitter/
  dialog focus and return paths passed; EN/VI and reduced-motion journeys
  passed. Native browser chrome zoom remains the documented manual gate.
- `git diff --check` is expected to report only normal repository LF/CRLF
  normalization warnings. Final process hygiene requires no project listener
  on ports `3000`, `4173`, `4175`, `5173`, `8000`, `8765`, or `8766` after
  preview/browser cleanup.

### V5-08 boundary and handoff

The `rag-ui-ux` evidence-first review was applied to the attached workbench
reference: simultaneous navigation/research/source/document hierarchy,
selected-source continuity, readable document canvas, exact highlight truth,
bounded lower context, and responsive fallback states were checked in the
rendered browser rather than inferred from build success. The only product
fixes needed for closure were frontend presentation/test seams: the defined
warning token now drives exact reader marks, the reader grid cannot collapse
under short wide heights, and the synthetic probe accepts the documented
unavailable reader state while traversing the real Sources → Document tabs.

Unrelated dirty work was preserved: `.audit-runtime/`, `harness_stacks.txt`,
and ignored `data/` remain untouched; no commit, deploy, benchmark promotion,
or corpus/index regeneration was performed. No files were removed.

ROLLBACK POINT: revert only the V5-08 frontend CSS/test probe and closure-doc
updates, retaining the V5-00 through V5-07 workbench implementation and all
domain owners. The post-V5 next task is `PDF-01`: investigate a real,
provenance-bound PDF representation only if its backend contract, corpus
availability, and exact location semantics are separately approved.
