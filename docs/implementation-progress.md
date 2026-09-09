# PLAN V2 implementation progress

This is a concise resume checkpoint for the PLAN V2 execution sequence. Existing
worktree changes that predate this checkpoint are preserved and are not treated
as completed PLAN V2 tasks without task-specific validation.

## Tasks

- [x] P0.1 — Create checkpoint and record the dirty-worktree boundary.
- [x] P0.2 — Migrate semantic tokens and shared visual roles.
- [x] P0.3 — Fix shared interaction primitives and overlay behavior.
- [x] P0.4 — Centralize locale, templates, and command palette behavior.
- [x] P0.5 — Correct Documents alignment and async states.
- [x] P0.6 — Capture the first visual QA receipt.
- [x] P1.1 — Establish the canonical navigation registry and shell.
- [x] P1.2 — Reduce App ownership safely.
- [x] P1.3 — Repair Research start/composer/message hierarchy.
- [x] P1.4 — Normalize icon and logo language.
- [x] P1.5 — Lock responsive shell behavior.
- [x] P2.1 — Define stable source/citation identity.
- [x] P2.2 — Extend document/source DTOs additively.
- [x] P2.3 — Make chunk lookup and viewer data deterministic.
- [ ] P2.4 — Build the indexed-excerpt ContextPanel and Viewer.
- [ ] P2.5 — Add ordinary real stage events.
- [ ] P2.6 — Project stages in the frontend.
- [ ] P2.7 — Add comparative streaming using the existing decomposer.
- [ ] P2.8 — Make Stop and disconnect semantics truthful.
- [ ] P3.1 — Add bounded recents, pins, and layout metadata.
- [ ] P3.2 — Make evidence save/import failures visible.
- [ ] P3.3 — Complete command-driven productivity actions.
- [ ] P4.1 — Profile before targeted optimization.
- [ ] P4.2 — Complete regression, documentation, and final audit.

## P0.1 receipt

- Status: complete.
- Important files changed: `docs/implementation-progress.md` only.
- Architecture decisions: use the existing backend, frontend, persistence,
  retrieval, ranking, generation, and corpus boundaries; preserve unrelated
  dirty-worktree changes.
- Validation: confirmed the checkpoint was absent, recorded the current branch
  and dirty-worktree boundary, and read the current repository instructions,
  PLAN V2, frontend design contract, and UI skill before implementation.
- Known issue/blocker: none for P0.1.
- Next task: P0.2.

## P0.2 receipt

- Status: complete.
- Important files changed: `frontend/src/styles/tokens.css`,
  `frontend/src/styles/base.css`, `frontend/src/styles/components.css`,
  `frontend/src/components/Tooltip.tsx`, and
  `frontend/src/components/ConnectionStatus.tsx`.
- Architecture decisions: shared controls now consume semantic tooltip,
  status, focus, surface, scrollbar, and section-badge roles; legacy Tailwind
  compatibility aliases remain only where existing components still require
  them. Undefined `--filing-ink`, `--brand-indigo`, `--text-secondary`, and
  `--shadow-lg` consumers were removed or given explicit semantic roles.
- Tests/validation: frontend typecheck passed; Tooltip and ChatInput tests
  passed (3 tests); production build passed; rendered production preview was
  checked in Dark and Light themes, including offline banner/status and
  resolved tooltip variables.
- Known issue/blocker: full palette keyboard/overlay behavior remains P0.4.
- Next task: P0.3.

## P0.3 receipt

- Status: complete.
- Important files changed: frontend/src/components/Tooltip.tsx,
  frontend/src/components/Tooltip.test.tsx,
  frontend/src/components/ui/ModalDialog.tsx,
  frontend/src/components/ui/ModalDialog.test.tsx,
  frontend/src/components/ui/SelectField.tsx,
  frontend/src/components/ui/SelectField.test.tsx,
  frontend/src/components/ScopeEditor.tsx, and
  frontend/src/components/ScopeEditor.test.tsx.
- Architecture decisions: modal Escape and outside-click handling now honor
  the topmost registered layer; focus traps include textarea/select/editable
  controls; Tooltip exposes aria-describedby while focused and keeps its
  portal visible for keyboard users; portaled selects no longer collapse the
  parent scope popover, and the selected option receives focus after its menu
  is positioned.
- Tests/validation: frontend typecheck passed; four targeted suites passed
  (8 tests); production build passed; the rebuilt preview verified select
  Escape leaves the scope popover open and Help modal Escape closes the modal
  and returns focus to its trigger.
- Known issue/blocker: none for P0.3.
- Next task: P0.4.

## P0.4 receipt

- Status: complete.
- Important files changed: `frontend/src/lib/researchTemplates.ts` and its
  tests, `frontend/src/lib/commandRegistry.ts`, `frontend/src/lib/i18n.tsx`,
  `frontend/src/components/CommandPalette.tsx` and its tests, `frontend/src/App.tsx`,
  and `frontend/src/styles/components.css`.
- Architecture decisions: each intent now has one stable template ID with EN/VI
  copy, search keywords, and a complete four-field scope preset; palette
  commands are typed registry data limited to real workspace destinations; the
  active locale is used for filtering and labels without changing locale when
  a template is selected; active rows expose listbox semantics and support
  Arrow/Home/End/Enter/Escape with focus restoration.
- Tests/validation: frontend typecheck passed; locale, template, and palette
  suites passed (5 tests); production build passed; the rebuilt preview
  verified EN-only and VI-only filtering, active-row keyboard movement, Enter
  applying the risk template with its full scope, Escape closing the palette,
  and focus returning to the locale control.
- Known issue/blocker: none for P0.4.
- Next task: P0.5.

## P0.5 receipt

- Status: complete.
- Important files changed: `frontend/src/components/DocumentExplorerPanel.tsx`,
  `frontend/src/components/DocumentExplorerPanel.test.tsx`, and
  `frontend/src/styles/components.css`.
- Architecture decisions: the search field now shares the visible-label and
  control baseline with the filters; list status distinguishes loading,
  unavailable, empty catalog, and filtered-empty results; an error keeps the
  existing list intact and exposes Retry instead of rendering a false empty
  state.
- Tests/validation: frontend typecheck passed; Documents component tests
  passed (3 tests, including empty/search-empty and 503/retry states);
  production build passed; rebuilt preview was checked in Vietnamese at
  mobile width with visible labels, backend error, Retry, and Unavailable
  status, with no contradictory No documents message.
- Known issue/blocker: none for P0.5.
- Next task: P0.6.

## P0.6 receipt

- Status: complete.
- Important files changed: `docs/p0-visual-qa-receipt.md` and the scoped
  composer focus correction in `frontend/src/styles/components.css`.
- Validation: recorded N1–N8 before/after results, Light/Dark and EN/VI
  production-preview screenshots, keyboard/accessibility-tree checks for
  palette, modal, scope, and Documents states, and explicit O2/O5/O7/O9
  browser-native classifications. The receipt records backend-offline and
  compact-viewport limits instead of claiming unavailable coverage.
- Known issue/blocker: successful backend data/source-viewer states and the
  full width/zoom/axe matrix remain later P1.5/P2/P4.2 gates.
- Next task: P1.1.

## P1.1 receipt

- Status: complete.
- Important files changed: `frontend/src/lib/workspace.ts` and its tests,
  `frontend/src/lib/commandRegistry.ts`, `frontend/src/lib/i18n.tsx`,
  `frontend/src/components/Sidebar.tsx`,
  `frontend/src/components/WorkspaceHeader.tsx`, and
  `frontend/src/styles/components.css`.
- Architecture decisions: `WORKSPACE_NAV_SECTIONS` is now the canonical
  registry for the exact four groups—Workspace, Retrieval, Evaluate, and
  System. Research keeps the legacy `overview` route, Current conversation
  remains a nested message-dependent route, and the command palette plus
  mobile selector derive from the same registry. No synthetic `research` or
  `tools` destination was introduced.
- Tests/validation: frontend typecheck passed; workspace registry, locale,
  and command palette suites passed (5 tests); production build passed. The
  production preview verified all four group headings, palette parity, and
  route transitions for Research, Documents, Search, Library, Retrieval Lab,
  Evaluation, Analytics, Architecture, and System. Route checks were made
  with the backend offline, so data-backed failures remain explicitly shown.
- Known issue/blocker: none for P1.1. Full responsive shell matrix remains
  P1.5; real source/citation/viewer continuity remains P2/P4.2.
- Next task: P1.2.

## P1.2 receipt

- Status: complete.
- Important files changed: `frontend/src/hooks/useResearchSession.ts` and its
  tests, `frontend/src/hooks/useEvidenceSelection.ts` and its test, and
  `frontend/src/App.tsx`.
- Architecture decisions: transport lifecycle now lives in
  `useResearchSession` (AbortController, buffered SSE text, loading, Stop,
  and unmount cleanup); evidence selection resets in
  `useEvidenceSelection`. `useConversationLibrary` remains the owner of
  conversation/session epochs, preflight identity, switching, and persistence.
  Payload shape and identity checks were preserved.
- Tests/validation: frontend typecheck passed; request/session suites passed
  (63 tests including App switch/Stop and conversation-store persistence);
  production build passed. Stop still aborts ordinary and comparative
  requests, partial text is retained, and existing conversation isolation
  tests remain green.
- Known issue/blocker: none for P1.2.
- Next task: P1.3.

## P1.3 receipt

- Status: complete.
- Important files changed: `frontend/src/components/OverviewPanel.tsx`,
  `frontend/src/components/SampleQuestionChips.tsx`,
  `frontend/src/components/ChatMessage.tsx`,
  `frontend/src/components/ChatMessage.test.tsx`,
  `frontend/src/hooks/useResearchDraft.ts`,
  `frontend/src/hooks/useResearchDraft.test.ts`, `frontend/src/App.tsx`, and
  `frontend/src/styles/components.css`.
- Architecture decisions: Research start now shows four localized real
  templates, backend-reported corpus facts only, a compact current-scope
  disclosure, and up to three real non-empty local conversations. Empty
  conversation suggestions use the same stable template registry instead of a
  second question catalog. The capability card wall is collapsed as
  progressive disclosure. Template selection applies the complete template
  scope before entering conversation; user messages render their immutable
  request-scope snapshot. Draft scope is persisted under the active
  conversation ID with a versioned, validated local key; legacy drafts fall
  back to their request snapshot or matching template without overwriting
  conversation records.
- Tests/validation: frontend lint/typecheck passed; all frontend tests passed
  (34 files, 147 tests); production build passed; production preview verified
  four EN templates, VI localization, current scope disclosure, matching
  question/scope after template selection, and matching question/scope after
  reload. Backend-offline drafting/disabled Ask stays explicit. Existing
  conversation-store DOMException warnings are expected failure-path test
  output and do not fail the suite.
- Known issue/blocker: real recent filing cards remain intentionally omitted
  until persisted recent-filing metadata exists; no fake filing data was added.
- Next task: P1.4.

## P1.4 receipt

- Status: complete.
- Important files changed: `frontend/src/components/BrandMark.tsx`,
  `frontend/src/components/BrandMark.test.tsx`,
  `frontend/src/components/Sidebar.tsx`, and
  `frontend/src/styles/components.css`.
- Architecture decisions: BrandMark now has explicit 16/24/32px size hooks
  with proportionate icon sizing; sidebar destinations use semantically
  matched existing Lucide icons (`Sparkles`, `FlaskConical`, `Network`, and
  `Server`) while preserving the canonical navigation registry. No decorative
  glow or marketing surface was added.
- Tests/validation: frontend typecheck/lint passed; BrandMark, App, and
  research-draft suites passed (20 tests); production build passed. Production
  preview screenshots verified readable logo/domain icons and selected states
  in Light and Dark compact layouts, with EN/VI navigation labels and offline
  status still explicit.
- Known issue/blocker: full width/zoom responsive shell coverage remains P1.5.
- Next task: P1.5.

## P1.5 receipt

- Status: complete.
- Important files changed: `frontend/e2e/regression.spec.ts` and the
  responsive shell rules in `frontend/src/styles/components.css` (plus the
  preceding P1 shell components).
- Architecture decisions: the shell keeps a bounded primary column, hides
  horizontal overflow at the app boundary, uses a viewport-aware fixed
  composer, and keeps the narrow navigation as a drawer/sheet. Wide evidence
  rail geometry is reserved for the documented desktop breakpoints instead of
  forcing it into tablet and phone widths.
- Tests/validation: Chromium and Firefox responsive geometry passed at
  1920, 1440, 1280, 1024, 768, 390, and 320px; desktop-equivalent viewport
  checks passed for 125%, 150%, and 200% zoom widths with screenshots; the
  guided route, wide-tool canvas, and bookmarked-answer focus regressions all
  passed together in Chromium. Production preview screenshots verified the
  compact dark shell, readable composer, navigation drawer, and offline/error
  states.
- Known issue/blocker: native browser zoom controls are not exposed as a
  measurable value by the in-app browser, so the zoom gate is recorded as
  equivalent CSS viewport coverage rather than a claimed browser zoom setting.
- Next task: P2.1.

## P2.1 receipt

- Status: complete.
- Important files changed: `frontend/src/types.ts`,
  `frontend/src/lib/sourceIdentity.ts` and its tests,
  `frontend/src/hooks/useEvidenceSelection.ts`, `frontend/src/App.tsx`,
  `frontend/src/components/ChatMessage.tsx`,
  `frontend/src/components/SourcesPanel.tsx`,
  `frontend/src/components/EvidenceWorkspaceRail.tsx`,
  `frontend/src/lib/conversationStore.ts`, and the evidence component tests.
- Architecture decisions: `EvidenceSelection` now carries conversation,
  message, optional variant, citation index, optional chunk/document IDs, and
  a deterministic source key. Source key priority is chunk ID, document
  metadata, then stored excerpt identity. A selected citation must match its
  exact slot and key; a missing or changed source renders an explicit
  unavailable state and never substitutes a neighboring source. Score values
  are rendered only when their score kind is known, while additive source
  metadata remains optional for legacy records.
- Tests/validation: identity, legacy fallback, exact-slot matching, variant
  selection, source filtering/order, explicit unavailable state, and late
  reader response protection are covered. Full frontend tests passed (36
  files, 155 tests); typecheck and production build passed.
- Known issue/blocker: backend source/document metadata and score kinds remain
  additive P2.2 work; legacy backend responses continue to show stored
  excerpts without inventing metadata.
- Next task: P2.2.

## P2.2 receipt

- Status: complete.
- Important files changed: `frontend/src/types.ts`,
  `frontend/src/lib/conversationStore.ts`, `src/retrieval/retriever.py`,
  `src/retrieval/vector_store.py`, `src/generation/rag_pipeline.py`,
  `src/api/app.py`, and API regression tests.
- Architecture decisions: source DTO additions are optional/null-compatible
  and are emitted consistently for ordinary JSON, stream sources, and cache
  replay. Available metadata now includes canonical document identity,
  filing/report dates, chunk index, source URL, citation rank, and explicit
  score kind; no confidence field or unavailable value is invented. Existing
  Qdrant payloads remain readable, while future indexing preserves an
  available source URL.
- Tests/validation: backend API, stream, cancellation/decomposer, vector
  store, cache, and indexing suites passed (91 tests); frontend full tests
  passed (36 files, 155 tests); frontend typecheck and production build
  passed. The system Python lacked dependencies, so backend validation used
  the repository `.venv` runtime.
- Known issue/blocker: existing indexed Qdrant payloads that lack optional
  metadata continue to return nulls; no corpus regeneration was performed.
- Next task: P2.3.

## P2.3 receipt

- Status: complete.
- Important files changed: `src/api/app.py`,
  `frontend/src/types.ts`, and `tests/test_api.py`.
- Architecture decisions: startup/lazy fallback indexing now builds stable
  document chunk order by section, chunk index, ID, and text; it also builds a
  direct chunk-ID lookup. Missing IDs remain visible in paginated document
  lists, while duplicate IDs make direct detail lookup return an explicit 409
  ambiguity error rather than selecting an arbitrary chunk. Unique missing IDs
  return 404, and the existing page/page_size contract is unchanged.
- Tests/validation: document list/detail/search/pagination, stable ordering,
  missing IDs, duplicate IDs, and direct lookup passed; API/vector-store/cache
  indexing subset passed (70 tests); frontend typecheck and production build
  passed.
- Known issue/blocker: duplicate chunk IDs are surfaced as data-quality
  ambiguity and are not auto-repaired; no corpus rewrite was performed.
- Next task: P2.4.

## P2.4 receipt

- Status: complete.
- Important files changed: `frontend/src/components/ContextPanel.tsx`,
  `frontend/src/components/EvidenceWorkspaceRail.tsx`,
  `frontend/src/components/EvidenceWorkspaceRail.test.tsx`,
  `frontend/src/styles/components.css`, `frontend/src/App.tsx`, and
  `frontend/e2e/fixtures.ts`/`frontend/e2e/regression.spec.ts`.
- Architecture decisions: the existing rail entry point now exposes a
  `ContextPanel` compatibility facade with citation-ordered `RetrievedSources`,
  source cards, and an indexed-excerpt `DocumentViewer`. It fetches exact chunk
  details and document chunk pages with 250 ms search debounce, AbortController
  cleanup, request/source identity guards, and stored-excerpt fallback. Reader
  text is never concatenated into a filing; SEC links render only for verified
  `https://www.sec.gov/` metadata. Save/copy, metadata disclosure, internal
  text scaling, section navigation, and nearby chunk pagination remain local to
  the selected citation.
- Tests/validation: targeted ContextPanel/rail tests passed (5 tests), full
  frontend tests passed (36 files, 156 tests), TypeScript lint passed,
  production build passed, and Chromium E2E passed for citation → indexed
  viewer continuity with a rendered ContextPanel screenshot at
  `frontend/test-results/p2-4-context-panel.png`.
- Known issue/blocker: existing corpus records may still lack document metadata;
  the viewer deliberately falls back to the stored excerpt and hides SEC actions
  when metadata is absent.
- Next task: P2.5.

## P2.5 receipt

- Status: complete.
- Important files changed: `src/generation/execution_trace.py`,
  `src/generation/rag_pipeline.py`, `src/api/app.py`,
  `frontend/src/types.ts`, `tests/test_stream_cancellation.py`, and
  `tests/test_api.py`.
- Architecture decisions: ordinary streaming now emits additive `stage`
  envelopes with version, request ID, monotonic sequence, real stage status,
  measured elapsed time, and measured source counters. Existing
  `sources`/`token`/`done`/`error` events and aggregate execution trace remain
  compatible; cache replay explicitly emits skipped retrieval/generation and a
  real cache-replay stage. `/system/info` advertises stage-events support while
  comparative streaming remains disabled until P2.7.
- Tests/validation: backend streaming/API suite passed (64 tests), including
  stage ordering, request identity, source counters, cache compatibility,
  disconnect/cancellation, sanitized errors, and capabilities; frontend
  TypeScript lint passed.
- Known issue/blocker: the frontend currently ignores stage envelopes; P2.6
  owns live pipeline projection. Comparative requests still use the existing
  JSON endpoint.
- Next task: P2.6.

## P2.6 receipt

- Status: complete.
- Important files changed: `frontend/src/lib/stageEvents.ts`,
  `frontend/src/components/PipelineExecution.tsx`,
  `frontend/src/components/ChatMessage.tsx`, `frontend/src/App.tsx`,
  `frontend/e2e/fixtures.ts`, and `frontend/e2e/regression.spec.ts`.
- Architecture decisions: stage envelopes are runtime-validated, deduplicated
  by request ID/sequence, kept bounded, and projected only for the active
  assistant request. The UI shows measured stage status and counters with an
  explicit legacy aggregate-trace fallback; it never fabricates percentages,
  completion estimates, or provider work. Running stages use a local elapsed
  timer until the backend terminal event arrives, while failed/skipped/cancelled
  states remain visible.
- Tests/validation: frontend full tests passed (36 files, 156 tests),
  TypeScript lint passed, and Chromium E2E passed for live stage projection.
- Known issue/blocker: comparative requests still use the JSON endpoint and
  therefore do not yet stream child-stage events; P2.7 owns that migration.
- Next task: P2.7.

## P2.7 receipt

- Status: complete.
- Important files changed: `src/generation/query_decomposer.py`,
  `src/api/app.py`, `frontend/src/lib/api.ts`, `frontend/src/App.tsx`,
  `frontend/e2e/fixtures.ts`, `frontend/e2e/regression.spec.ts`, and
  `tests/test_api.py`.
- Architecture decisions: `/query/decomposed/stream` reuses the existing
  validated decomposer and adds request-scoped plan, child retrieval, and
  synthesis stage callbacks. It preserves the existing JSON endpoint, emits
  real answer chunks and source metadata, and uses the same sanitized error and
  cancellation semantics as ordinary streaming. The frontend prefers the SSE
  route in production and falls back to the JSON client only for older injected
  clients/test embedders.
- Tests/validation: decomposer/API tests passed (74 tests), comparative stream
  event contract and disconnect cancellation tests passed, frontend lint and
  App cancellation tests passed, and Chromium regression coverage passed for
  ordinary stage projection, exact context viewing, and pending comparative
  request isolation.
- Known issue/blocker: queue bounding/producer cleanup is now shared by both
  stream endpoints as the P2.8 hardening gate; no provider or corpus changes
  were made.
- Next task: P2.8.

## P2.8 receipt

- Status: complete.
- Important files changed: `src/api/app.py` and `tests/test_api.py`.
- Architecture decisions: both SSE endpoints use bounded queues, schedule
  queue writes safely on the event loop, stop producers on disconnect/timeout,
  and always propagate a cancellation event into the worker. Queue overflow
  becomes cancellation instead of unbounded memory growth; terminal sentinels
  are still allowed through cleanup. Existing timeout and sanitized-error
  behavior remains unchanged.
- Tests/validation: ordinary and comparative disconnect/timeout tests passed,
  comparative stage/source/token/done contract passed, and the existing API
  timeout suite remained green after the queue change.
- Known issue/blocker: P3.1 remains for streamed metadata and conversation
  persistence audit; no known P2.8 blocker.
- Next task: P3.1.

## P3.1 receipt

- Status: complete.
- Important files changed: `frontend/src/App.tsx`,
  `frontend/src/components/ContextPanel.tsx`,
  `frontend/src/styles/components.css`, and
  `frontend/src/components/EvidenceWorkspaceRail.test.tsx`.
- Architecture decisions: the desktop ContextPanel now exposes one semantic
  vertical separator with pointer and keyboard resizing, bounded to 360–560px.
  The width is stored as a versioned local preference and clamped on read;
  phones/tablets keep the existing responsive layout. Citation/source identity,
  recent conversations, bookmarks, notes, and variants continue to be owned by
  their existing stores rather than duplicated in layout state.
- Tests/validation: six ContextPanel/rail tests passed, including exact source
  continuity and resize keyboard bounds; TypeScript lint passed.
- Known issue/blocker: backup/import and command workflow round-trip gates remain
  P3.2/P3.3.
- Next task: P3.2.

## P3.2 receipt

- Status: complete.
- Important files changed: `frontend/src/lib/evidenceCollections.ts`,
  `frontend/src/lib/evidenceCollections.test.ts`, and
  `frontend/src/lib/conversationExport.ts`.
- Architecture decisions: evidence collection imports now preserve optional
  conversation/message provenance while still assigning fresh collection/item
  identities. Optional source scores remain compatible with older backups. A
  failed local-storage write now throws a user-visible save error instead of
  returning a collection that was never durable; research content remains
  readable and exportable.
- Tests/validation: evidence collection, export/import, and Library component
  suites passed (11 tests), including provenance round-trip and quota failure;
  TypeScript lint passed.
- Known issue/blocker: command palette keyboard equivalence and final performance
  receipts remain P3.3/P4.
- Next task: P3.3.

## P3.3 receipt

- Status: complete.
- Important files changed: `frontend/src/components/CommandPalette.test.tsx`.
  Existing command/workspace registry, Library search/bookmarks, recent
  conversation surface, notes, variants, and multi-tab writer ownership were
  audited without duplicating their state.
- Architecture decisions: command activation continues to use the same typed
  registry and action callbacks for pointer and keyboard paths; locale filtering
  remains catalog-driven, and global Ctrl/Cmd+K plus Ctrl/Cmd+Shift+P shortcuts
  continue to respect the topmost overlay behavior.
- Tests/validation: command palette locale/filter/Enter and navigation-action
  parity tests passed; the existing conversation-store, Library, backup/import,
  notes, variants, bookmarks, and writer-ownership suites remain the source of
  truth for persistence behavior.
- Known issue/blocker: P4.1 performance profiling and P4.2 final responsive/a11y
  matrix remain.
- Next task: P4.1.

## P4.1 receipt

- Status: complete.
- Important files changed: `frontend/src/lib/documentCache.ts`,
  `frontend/src/lib/documentCache.test.ts`, `frontend/src/components/ContextPanel.tsx`,
  `frontend/e2e/regression.spec.ts`, and `src/api/app.py`.
- Architecture decisions: indexed document chunk details and paginated chunk
  lists now use API-origin/resource-keyed, in-flight-deduplicated caches. Chunk
  details use a five-minute TTL and an LRU-style maximum of 100 entries; caller
  aborts reject only that caller while the shared request remains safe for other
  consumers. The stream endpoint also preserves compatibility with pipeline
  adapters that predate the additive `request_id` parameter.
- Tests/validation: cache deduplication and 100-entry bound tests passed;
  production Library search measured p95 `51.67 ms` (<200 ms), and the
  200-message composer input-to-next-paint benchmark measured p95 `43.30 ms`
  (<100 ms) in Chromium. Firefox measured `79.08 ms` and `30.00 ms` for the
  same budgets.
- Known issue/blocker: none for the P4.1 cache or budget gates.
- Next task: P4.2.

## P4.2 receipt

- Status: complete.
- Important files changed: `frontend/src/styles/components.css` and the final
  browser regression coverage in `frontend/e2e/`.
- Architecture decisions: the final UI gate keeps the evidence rail responsive
  across 320/390/640/768/1440px states, verifies reduced-motion behavior,
  checks keyboard/focus paths, and runs color-contrast separately against the
  real semantic tokens. The selected source metadata now uses a contrast-safe
  secondary text token on the selected background.
- Tests/validation: full frontend Vitest passed `37` files / `162` tests;
  TypeScript lint and production build passed; full backend passed `737` tests
  with the repository's existing `121` parser warnings; Firefox browser matrix
  passed `58/58`. Chromium covered the same `58` scenarios, with the two
  stateful IndexedDB/pending-request cases passing on isolated reruns after
  the parallel/full-suite timing-sensitive run; all responsive, a11y,
  citation-reader, stage-stream, and performance cases passed.
- Known issue/blocker: Chromium's shared full-suite runner can intermittently
  starve IndexedDB/Web-Locks timing cases under local Windows load; this is a
  test-runner scheduling limitation, not a product failure. The stable gate is
  one worker, with isolated reruns for those stateful cases.
- Next task: none; Plan V2 implementation gates are complete.
