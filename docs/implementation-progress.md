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

## FINAL PLAN V2 ADDENDUM reconciliation — 2026-09-10

- Status: `[-]` — checkpoint reconciliation complete; Addendum implementation has not started.
- Starting code binding: current worktree after the existing P0–P4 implementation; `git status --short` and `git diff --stat` were inspected before this entry.
- Important files changed: `docs/frontend/PLAN_V2_ADDENDUM_FINAL.md` and this checkpoint only.
- Reconciliation: the checklist still marks P2.4–P4.2 pending while later receipts describe implementations. Treat P2.4–P4.1 as implementation-present but validation-backed only where the receipt covers the relevant behavior. Treat P4.2 as unresolved because recurring full Chromium persistence/pending-request failures were not proven runner-only. P3.1 proves ContextPanel width persistence; pins remain deferred.
- Validation performed: `frontend/bun run lint` passed; focused workspace/template/palette/evidence suites passed (5 files, 16 tests). No full browser suite was rerun in this reconciliation.
- Known issue/blocker: V2-A06.1 must investigate the recurring Chromium gate before final closure; isolated reruns must not be used as proof of completion.
- Next task: V2-A06.1 after the documentation checkpoint is preserved; implementation sequence remains V2-A01.2 → V2-A02.1 → V2-A02.2 → V2-A03.1 → V2-A03.2 → V2-A04.1 → V2-A04.2 → V2-A05.1 → V2-A05.2 → V2-A05.3 → V2-A06.2.

## V2-A01.2 receipt — 2026-09-10

- Task ID / status: `V2-A01.2` / `[x]` for semantic metadata and icon parity.
- Starting code binding: repository after the A01.1 reconciliation and `V2-A06.1` diagnostic run.
- Files changed: `frontend/src/lib/semanticIcons.ts`, `frontend/src/lib/semanticIcons.test.ts`, `frontend/src/lib/workspace.ts`, `frontend/src/lib/commandRegistry.ts`, `frontend/src/lib/researchTemplates.ts`, `frontend/src/components/Sidebar.tsx`, `frontend/src/components/CommandPalette.tsx`, `frontend/src/lib/i18n.tsx`.
- Implementation summary: added one semantic Lucide registry for navigation, panels, actions and templates; route metadata now carries a shared description key and accent family; sidebar and palette consume the same route icon keys; Evaluation/Analytics, Research/Library and System/Documents are no longer duplicated or drifted.
- Contracts preserved: route IDs/order, template IDs, locale behavior, current-conversation guard, existing palette callbacks and installed dependency set.
- Commands run and exact results: `frontend/bun run lint` passed; `frontend/bun run test src/lib/workspace.test.ts src/lib/researchTemplates.test.ts src/components/CommandPalette.test.tsx` passed (3 files, 7 tests); central registry tests added and included in the next focused gate.
- Rendered/browser checks performed: not yet performed for this task; full Light/Dark and EN/VI rendered parity remains A02/A06.
- Artifact paths: none.
- Unresolved issue: A06.1 Chromium persistence gate remains `[-]`; no icon export fallback was needed because the planned Lucide exports are installed.
- Rollback slice: semantic registry plus route metadata/consumer imports and localized route descriptions.
- Next task: V2-A02.1.

## V2-A06.1 receipt — 2026-09-10

- Task ID / status: `V2-A06.1` / `[-]`.
- Starting code binding: `c3ccc51` plus the Addendum checkpoint above.
- Files changed: none; only browser artifacts were produced.
- Implementation summary: Chromium full suite was run twice with one worker and retries disabled. Both runs reproduced the same two failures: reload persistence at `e2e/app.spec.ts:286` and pending-delete action availability at `e2e/regression.spec.ts:157`; each run was `56 passed, 2 failed`. Isolated reruns of each test pass, so the failure is an order/shared-persistence timing problem that still requires an evidenced fix.
- Contracts preserved: no source, persistence, test or product code was changed.
- Commands run and exact results: `bunx playwright test --project=chromium --workers=1 --retries=0` twice: `56 passed, 2 failed` each; isolated reload and deletion commands each: `1 passed`.
- Rendered/browser checks performed: inspected failure screenshots; both show an empty Conversation Library immediately before the missing answer/delete control. Traces are in `frontend/test-results/e2e/`.
- Artifact paths: `frontend/test-results/e2e/app-conversation-survives--1d5a9-ge-reload-through-IndexedDB-chromium/`; `frontend/test-results/e2e/regression-deleting-the-ac-58b48--isolates-the-late-response-chromium/`.
- Unresolved issue: the suite-order/shared IndexedDB or writer/persistence timing interaction is not yet isolated; isolated pass is not sufficient evidence.
- Rollback slice: none.
- Next task: V2-A01.2; A06.1 may resume before A06.2 when the persistence owner can be changed safely.

## V2-A02.1 receipt — 2026-09-10

- Task ID / status: `V2-A02.1` / `[x]` for the shared interaction and feature-accent token slice.
- Starting code binding: worktree after `V2-A01.2`; A06.1 remains `[-]` under the plan's safe-independent-work exception.
- Files changed: `frontend/src/styles/tokens.css`, `frontend/src/styles/components.css`,
  `frontend/src/components/Sidebar.tsx`, `frontend/src/components/CommandPalette.tsx`,
  and `frontend/src/lib/commandRegistry.ts`.
- Implementation summary: added light/dark feature foreground and soft/hover/selected/pressed
  token families; applied stable sidebar and palette hover/current/keyboard-focus/pressed/
  disabled states with inset markers and feature-tinted icon emphasis. Transitions are limited
  to state properties, with reduced-motion fallback and no permanent glow or `transition: all`.
- Contracts preserved: no route/order changes, no backend/provider changes, existing callbacks,
  locale behavior, and the installed Lucide/Tailwind dependency set remain unchanged.
- Commands run and exact results: `frontend/bun run lint` passed; focused semantic/workspace/
  template/palette/modal tests passed (5 files, 11 tests); `frontend/bun run build` passed.
- Rendered/browser checks performed: not yet performed for this task; required Light/Dark,
  keyboard, responsive and forced-colors inspection remains in A06.2.
- Artifact paths: none.
- Unresolved issue or “none”: A06.1 Chromium persistence/pending-delete full-suite gate remains `[-]`.
- Rollback slice: token additions and the appended interaction rules in `tokens.css`/`components.css`
  plus their sidebar/palette data attributes.
- Next task: `V2-A02.2`.

## V2-A02.2 receipt — 2026-09-10

- Task ID / status: `V2-A02.2` / `[x]` for palette active-row and keyboard semantics.
- Starting code binding: worktree after `V2-A02.1`.
- Files changed: `frontend/src/components/CommandPalette.tsx` and
  `frontend/src/components/CommandPalette.test.tsx`.
- Implementation summary: the palette input is now the accessible combobox owner with a
  stable active descendant, localized label/description/keyword filtering, option rows that
  retain input focus for pointer activation, and existing Arrow/Home/End/Enter/Escape behavior.
  Active-row styling uses the shared feature state rules while current-route indication remains
  separate from keyboard activity.
- Contracts preserved: ModalDialog focus restoration, global shortcuts, command callback identity,
  template selection behavior, and navigation registry order.
- Commands run and exact results: `frontend/bun run lint` passed; focused semantic/icon/workspace/
  template/palette/modal tests passed (5 files, 11 tests); `frontend/bun run build` passed.
- Rendered/browser checks performed: not yet performed for this task; full palette pointer,
  keyboard, Light/Dark and EN/VI checks remain in A06.2.
- Artifact paths: none.
- Unresolved issue or “none”: A06.1 Chromium persistence/pending-delete full-suite gate remains `[-]`.
- Rollback slice: combobox/listbox attributes, option focus handling, and the matching palette tests.
- Next task: `V2-A03.1`.

## V2-A03.1 receipt — 2026-09-10

- Task ID / status: `V2-A03.1` / `[x]`.
- Starting code binding: worktree after the A02 icon/state/palette slices; A06.1 remains `[-]`.
- Files changed: `frontend/src/hooks/useNavigationLayout.ts` and
  `frontend/src/hooks/useNavigationLayout.test.ts`.
- Implementation summary: added the isolated `sec_qa_navigation_layout_v1` preference owner.
  It accepts only raw `expanded`/`compact`, defaults safely to expanded, ignores malformed
  values, updates from valid cross-tab storage events without echoing them, and retains the
  in-memory choice when storage is blocked or quota-limited. It is intentionally absent from
  conversation backup data.
- Contracts preserved: existing theme, scope, conversation, evidence and backup keys are not
  touched; breakpoints are not represented in the preference and cannot overwrite it.
- Commands run and exact results: `frontend/bun run lint` passed; focused navigation, semantic
  icon, palette and modal tests passed (4 files, 10 tests); `frontend/bun run test src/App.test.tsx
  src/hooks/useNavigationLayout.test.ts` passed (2 files, 19 tests); `frontend/bun run build` passed.
- Rendered/browser checks performed: valid compact/expanded behavior was visually inspected in
  the running local UI; storage-event, malformed and quota paths are covered by the hook tests.
  Full breakpoint and keyboard inspection remains A03.2/A06.2.
- Artifact paths: none.
- Unresolved issue or “none”: A06.1 Chromium persistence/pending-delete full-suite gate remains `[-]`.
- Rollback slice: the new hook and its focused tests only.
- Next task: `V2-A03.2`.

## V2-A03.2 receipt — 2026-09-10

- Task ID / status: `V2-A03.2` / `[-]` pending the complete responsive/browser matrix.
- Starting code binding: worktree after `V2-A03.1`.
- Files changed: `frontend/src/App.tsx`, `frontend/src/components/Sidebar.tsx`,
  `frontend/src/components/SidebarFooter.tsx`, `frontend/src/components/WorkspaceHeader.tsx`,
  `frontend/src/App.test.tsx`, `frontend/src/lib/i18n.tsx`, and
  `frontend/src/styles/components.css`.
- Implementation summary: wired the preference into the shell; desktop widths at or above
  1280px now expose an expanded 216px sidebar or a 56px icon rail with a header toggle. Narrower
  widths use a temporary 280px drawer (capped at viewport minus 32px on phones) with one shared
  route tree. Compact rail labels are replaced by accessible names/tooltips, active markers are
  inset, and the existing `ModalDialog` supplies Escape, backdrop close, focus trapping, inert
  background and focus return for the drawer.
- Contracts preserved: route order/IDs and callbacks, Library count, conversation reset behavior,
  existing desktop content flow, and no manual resize splitter were changed. Test-only viewport
  assumptions were updated to open the drawer before asserting drawer-owned navigation.
- Commands run and exact results: `frontend/bun run lint` passed; `frontend/bun run test
  src/App.test.tsx src/hooks/useNavigationLayout.test.ts` passed (2 files, 19 tests); `frontend/bun
  run build` passed.
- Rendered/browser checks performed: at the running local desktop viewport, compact rail and
  restoration to expanded were visually inspected; the rail showed semantic icons only, active
  marker and accessible toggle. Mobile/tablet drawer, keyboard-only and all zoom checks remain
  for A06.2.
- Artifact paths: none.
- Unresolved issue or “none”: A06.1 remains `[-]`; A03.2 is partial until the required widths,
  drawer focus and responsive production-build checks are recorded.
- Rollback slice: Sidebar/SidebarFooter/WorkspaceHeader layout integration plus the appended
  navigation CSS; the preference hook can remain independently verified.
- Next task: `V2-A04.1` may proceed under the plan's safe-independent-work exception; return to
  A03.2 during the browser matrix before A06.2.

## V2-A04.1 receipt — 2026-09-10

- Task ID / status: `V2-A04.1` / `[x]` for overview ordering, truthful corpus state and controlled scope plumbing.
- Starting code binding: worktree after A03.2; A03.2 remains `[-]` only for its pending responsive matrix.
- Files changed: `frontend/src/components/OverviewPanel.tsx`, `frontend/src/components/ScopeEditor.tsx`,
  `frontend/src/components/ScopeEditor.test.tsx`, `frontend/src/components/ChatInput.tsx`,
  `frontend/src/App.tsx`, and `frontend/src/styles/components.css`.
- Implementation summary: reordered the start view into concise heading, service-reported corpus
  summary or explicit unavailable state, current scope, connection state, four usable templates,
  real local recents and collapsed guidance. Removed duplicated company-count claims from the hero;
  Overview no longer falls back to configured ticker length or exposes fake freshness/coverage.
  Template cards use their semantic icons. ScopeEditor now supports an optional controlled owner,
  while its existing uncontrolled callers remain unchanged.
- Contracts preserved: existing health fields and corpus semantics, template IDs/callbacks, draft
  scope ownership, offline drafting, composer behavior, and existing overview/guide copy remain
  compatible; no API endpoint or persistence schema changed.
- Commands run and exact results: `frontend/bun run lint` passed; `frontend/bun run test src/App.test.tsx
  src/components/ChatInput.test.tsx src/components/ScopeEditor.test.tsx src/lib/researchTemplates.test.tsx`
  passed (4 files, 22 tests); `frontend/bun run build` passed.
- Rendered/browser checks performed: local UI accessibility tree verified the order and offline
  corpus-unavailable wording; no configured-ticker count or FastAPI placeholder was present. Full
  Light/Dark, EN/VI, real metadata and viewport matrix remains A06.2.
- Artifact paths: none.
- Unresolved issue or “none”: A06.1 Chromium persistence/pending-delete full-suite gate remains `[-]`;
  A03.2 responsive drawer evidence remains pending.
- Rollback slice: OverviewPanel/ScopeEditor/ChatInput ordering and controlled-open additions plus
  their overview CSS/test changes.
- Next task: `V2-A04.2`.

## V2-A04.2 receipt — 2026-09-10

- Task ID / status: `V2-A04.2` / `[x]` for source, pipeline and capability explanations.
- Starting code binding: worktree after A04.1; A03.2 responsive matrix and A06.1 Chromium gate remain open.
- Files changed: `frontend/src/components/ContextPanel.tsx`, `frontend/src/components/PipelineExecution.tsx`,
  `frontend/src/components/OverviewPanel.tsx`, and `frontend/src/styles/components.css`.
- Implementation summary: source context now states that the list contains excerpts retained after
  retrieval/reranking and that rank/retrieval/reranker scores are ordering signals, not confidence.
  Indexed-reader metadata continues to distinguish stored excerpts from indexed details and now uses
  the semantic reader icon. Pipeline disclosure now exposes “How this answer was built” while keeping
  actual reported stages/durations only. Overview capability cards use the shared reader/execution/
  sources icon metadata and feature accent tokens.
- Contracts preserved: citation/source/viewer identity, indexed chunk loading/cache/error behavior,
  pipeline event/trace semantics, missing metadata handling, and existing HelpDialog evidence wording.
  No endpoint, polling, fake stage, score, coverage or metric was introduced.
- Commands run and exact results: `frontend/bun run lint` passed; focused ChatMessage/App suites passed
  (2 files, 25 tests); `frontend/bun run build` passed.
- Rendered/browser checks performed: local overview accessibility tree shows truthful corpus/offline
  state and semantic template flow; compact rail was previously inspected. Source/pipeline rendered
  states, both themes and locale matrix remain A06.2.
- Artifact paths: none.
- Unresolved issue or “none”: A06.1 Chromium persistence/pending-delete full-suite gate remains `[-]`;
  A03.2 responsive drawer evidence remains pending.
- Rollback slice: ContextPanel/PipelineExecution explanation copy and Overview feature-icon metadata/CSS.
- Next task: `V2-A05.1`.

## V2-A05.1 receipt — 2026-09-10

- Task ID / status: `V2-A05.1` / `[x]` for the bounded template schema and send boundary.
- Starting code binding: worktree after A04.2; A03.2 and A06.1 remain open only at their documented browser gates.
- Files changed: `frontend/src/lib/researchTemplates.ts`, `frontend/src/lib/researchTemplates.test.ts`, and
  `frontend/src/App.tsx`.
- Implementation summary: added one schema per template with required/optional parameters, searchable-ticker
  validation, year/metric/claim limits, distinct comparison-company validation, deterministic localized rendering,
  and a reserved-placeholder detector. The send boundary accepts ordinary bracketed user text but rejects only
  unresolved template tokens or questions outside 5–500 characters.
- Contracts preserved: stable template IDs/scope presets, EN/VI copy selection, arbitrary free-form questions,
  existing request snapshots, retrieval behavior and no auto-send semantics.
- Commands run and exact results: `frontend/bun run lint` passed; `frontend/bunx vitest run
  src/lib/researchTemplates.test.ts` passed (1 file, 6 tests); `frontend/bun run build` passed.
- Rendered/browser checks performed: not applicable for the pure schema slice; guided UI validation is A05.2/A06.2.
- Artifact paths: none.
- Unresolved issue or “none”: A06.1 full Chromium persistence/pending-delete failures and A03.2 responsive matrix remain open.
- Rollback slice: research template schema/render/validation additions and the single App send-boundary guard.
- Next task: `V2-A05.2`.

## V2-A05.2 receipt — 2026-09-10

- Task ID / status: `V2-A05.2` / `[x]` for guided template completion.
- Starting code binding: worktree after A05.1.
- Files changed: `frontend/src/components/TemplateQuestionDialog.tsx`,
  `frontend/src/components/TemplateQuestionDialog.test.tsx`, and `frontend/src/App.tsx`.
- Implementation summary: added one schema-driven dialog using the existing ModalDialog and SelectField primitives.
  Required fields are validated before Apply; Apply only places a rendered question in the existing composer and
  applies the template scope. Selecting a template never sends, changes locale, or mutates the draft; Cancel,
  Escape and backdrop close leave the previous draft untouched. Missing searchable ticker data disables the
  company selector honestly instead of accepting an unsearchable company.
- Contracts preserved: current draft/scope ownership, controlled ScopeEditor, template IDs, locale provider,
  focus restoration and existing composer send/stop behavior. No generic form framework or persistence schema added.
- Commands run and exact results: `frontend/bun run lint` passed; focused template/App/Scope tests passed (4 files,
  26 tests); `frontend/bun run build` passed.
- Rendered/browser checks performed: dialog mechanics and validation are covered by component tests; production
  rendered Apply/Cancel and EN/VI visual checks remain in A06.2.
- Artifact paths: none.
- Unresolved issue or “none”: A06.1 full Chromium persistence/pending-delete failures and A03.2 responsive matrix remain open.
- Rollback slice: TemplateQuestionDialog plus App template-opening/apply wiring; A05.1 schema can remain independently verified.
- Next task: `V2-A05.3`.

## V2-A05.3 receipt — 2026-09-10

- Task ID / status: `V2-A05.3` / `[x]` for real contextual command callbacks.
- Starting code binding: worktree after A05.2.
- Files changed: `frontend/src/lib/commandRegistry.ts`, `frontend/src/lib/i18n.tsx`,
  `frontend/src/components/CommandPalette.tsx`, `frontend/src/components/CommandPalette.test.tsx`,
  `frontend/src/App.tsx`, and `frontend/src/styles/components.css`.
- Implementation summary: added runtime-bound contextual command metadata and App-owned callbacks for copying the
  latest grounded answer, inspecting current sources, saving the selected source through the existing evidence
  store, and opening the existing scope editor. Navigation, Library, Search, help and new-conversation commands
  remain registry-backed. The palette owns no mutation logic; unavailable contextual commands are hidden and
  storage/clipboard errors surface through an honest status notice.
- Contracts preserved: existing navigation registry/order, source identity and evidence collection semantics,
  conversation state, current callbacks, locale behavior and no new endpoint or persistence schema.
- Commands run and exact results: `frontend/bun run lint` passed; focused palette/template/research/App tests passed
  (4 files, 29 tests); `frontend/bun run build` passed.
- Rendered/browser checks performed: contextual command rendering is covered by the palette test; full keyboard,
  pointer, theme and source-state browser validation remains A06.2.
- Artifact paths: none.
- Unresolved issue or “none”: A06.1 full Chromium persistence/pending-delete failures and A03.2 responsive matrix remain open.
- Rollback slice: ContextualCommandDefinition metadata, localized labels, App callbacks and evidence accent selector.
- Next task: resume `V2-A06.1` persistence investigation; then `V2-A03.2` browser matrix before A06.2.

## V2-A06.1 continuation receipt — 2026-09-10

- Task ID / status: `V2-A06.1` / `[x]` after the persistence hard gate was reproduced, fixed, and rerun twice.
- Starting code binding: worktree after A05.3 and the earlier A06.1 `[-]` receipt.
- Files changed: `frontend/src/hooks/useConversationLibrary.ts`.
- Implementation summary: the recurring reload and pending-delete failures were traced to the 150 ms
  completion-save delay being canceled by the next render/query. Completed exchanges now persist immediately
  with the existing conversation snapshot and operation identity, while draft persistence remains debounced.
  No arbitrary wait, retry, test skip, schema change, or storage replacement was added.
- Contracts preserved: active-operation identity checks, switch/delete/cancellation behavior, local and
  IndexedDB storage fallback, draft debounce, conversation schema, and Library semantics.
- Commands run and exact results: `frontend/bun run lint` passed; focused hook/App suites passed (2 files,
  23 tests); isolated reload persistence passed (1 test); isolated pending-delete passed (1 test); full
  Chromium ran with one worker and zero retries twice, each run `58 passed`.
- Rendered/browser checks performed: the full Chromium gate covered Light/Dark visual smoke, 390/768/1440
  layout checks, reduced motion, 320/640 reflow, reload persistence, pending delete, Library search, and
  performance checks.
- Artifact paths: none.
- Unresolved issue or “none”: none for A06.1. A03.2 responsive/zoom evidence and A06.2 final matrix remain.
- Rollback slice: only the completion-persistence timing/cleanup slice in `useConversationLibrary.ts`.
- Next task: `V2-A03.2` responsive browser validation, then `V2-A06.2` final gate.

## V2-A03.2 continuation receipt — 2026-09-10

- Task ID / status: `V2-A03.2` / `[x]` after the responsive shell and rendered navigation checks.
- Starting code binding: worktree after A03.1; the earlier A03.2 `[-]` receipt remains as history.
- Files changed: `frontend/src/components/Sidebar.tsx`, `frontend/src/components/SidebarFooter.tsx`,
  `frontend/src/components/WorkspaceHeader.tsx`, `frontend/src/App.tsx`, `frontend/src/lib/i18n.tsx`,
  `frontend/src/styles/components.css`, `frontend/src/App.test.tsx`, and the width assertion in
  `frontend/e2e/regression.spec.ts`.
- Implementation summary: one registry-derived route tree now supports expanded desktop navigation,
  a 56px compact rail at desktop widths, and a modal drawer below 1280px. Drawer focus trap, Escape,
  backdrop close, close-on-navigation, inert background, and focus return use the existing ModalDialog
  primitive. Desktop layout preference stays expanded/compact and is not overwritten by breakpoint changes.
- Contracts preserved: route order/IDs, Current conversation behavior, New conversation behavior,
  keyboard targets, locale/theme controls, no free-form resizer, and no duplicate navigation source.
- Commands run and exact results: `frontend/bun run lint` passed; focused navigation hook/App suites passed;
  `bunx playwright test e2e/regression.spec.ts --grep "research shell stays" --workers=1 --retries=0`
  passed in both Chromium and Firefox (2 tests); the full Chromium/Firefox suites also passed as recorded
  in A06.1/A06.2.
- Rendered/browser checks performed: local rendered UI showed expanded navigation, compact 56px rail with
  distinct icons and active marker, restored expanded preference, and desktop header toggle. Accessibility
  checks exposed `Use compact navigation`/`Expand navigation`, labelled routes, and the drawer tests cover
  mobile open/close/focus semantics. Geometry assertion now includes 1920/1440/1366/1280/1024/768/390/320.
- Artifact paths: none.
- Unresolved issue or “none”: exact browser-UI zoom levels are recorded under A06.2 because headless
  Playwright does not control browser chrome zoom reliably; CSS-viewport equivalents remain covered.
- Rollback slice: Sidebar/WorkspaceHeader responsive layout and its test/checkpoint changes only.
- Next task: `V2-A06.2` final validation gate.

## V2-A06.2 final gate receipt — 2026-09-10

- Task ID / status: `V2-A06.2` / `[x]` for the final implementation and regression gate; the only
  environment limitation is separately recorded below and does not change application behavior.
- Starting code binding: worktree after A01.2, A02.1, A02.2, A03.1, A03.2, A04.1, A04.2, A05.1,
  A05.2, A05.3, and the completed A06.1 persistence fix.
- Files changed: final implementation set in the preceding receipts plus
  `frontend/e2e/regression.spec.ts` for the explicit 1366px viewport assertion and this checkpoint receipt.
- Implementation summary: all Addendum slices are complete: semantic icon parity, interaction/color
  states, expanded/compact/drawer navigation, truthful overview data, guided templates with send guards,
  contextual real commands, immediate completed-exchange persistence, and existing-product regression safety.
  No backend endpoint, schema, provider, Docker, retrieval, ranking, generation, or fake-data behavior changed.
- Contracts preserved: citation/source/indexed-reader identity, conversations/variants/notes/bookmarks,
  evidence collections, Library/Search/Documents, backup/import, multi-tab coordination, Stop/cancellation,
  late-event isolation, prompts, and Qdrant semantics.
- Commands run and exact results: `frontend/bun run lint` passed; `frontend/bun run test` passed (40 files,
  176 tests); `frontend/bun run build` passed; Chromium full suite with one worker and zero retries passed
  twice (`58 passed` each); Firefox full suite with one worker and zero retries passed (`58 passed`);
  the post-matrix 1366px focused geometry check passed in both browsers (`2 passed`); `.venv\\Scripts\\python.exe
  -m pytest -q` passed (`737 passed, 121 warnings`); `git diff --check` passed.
- Rendered/browser checks performed: CUA rendered Light/Dark-capable shell was inspected in the local
  preview, including expanded/compact navigation, active marker, truthful offline/corpus state, guided
  template dialog, Escape close, and focus return. Automated matrix covers Light/Dark, EN/VI, reduced motion,
  1920/1440/1366/1280/1024/768/390/320, 640px reflow, accessibility/contrast, source-reader continuity,
  stop/late events, notes/bookmarks, backup/import, multi-tab, Library/Search/Documents, and performance.
- Environment limitation: the repository’s Playwright test documents that browser chrome zoom is not
  controllable consistently in headless Chromium/Firefox. The in-app browser accepted reset/plus key events
  without exposing a reliable zoom state, so exact 125/150/200 browser-chrome zoom is not claimed as a
  reproducible automated result. CSS viewport equivalents and the 100% baseline passed; no code change was
  made to fake browser zoom or alter product layout solely for the harness.
- Artifact paths: no generated artifacts are part of the implementation; pre-existing `harness_stacks.txt`
  remains untouched.
- Unresolved issue or “none”: no implementation or regression failure. The browser-chrome zoom limitation
  is an environment validation note, not a product defect.
- Rollback slice: the Addendum implementation set as a whole, with A06.1 persistence timing independently
  revertible; no unrelated dirty-worktree file was reverted.
- Next task: none. The Addendum execution sequence is complete.

## FINAL MASTER EXECUTION PLAN reconciliation — 2026-09-10

- Task ID / status: `V2-B01.1` / `[x]`; this entry supersedes the historical Addendum
  "Next task: none" statement for execution purposes while preserving that receipt as history.
- Starting code binding: HEAD `c3ccc51`; existing dirty implementation and untracked files were
  inspected and preserved. No application source was changed for this task.
- Files changed: `docs/frontend/FINAL_MASTER_EXECUTION_PLAN.md` (created) and this checkpoint.
- Implementation summary: saved the attached FINAL MASTER EXECUTION PLAN as the repository
  authority and established the dependency-safe remaining-work order:
  `B01.1 → B02.4 → B02.1 → B01.2 → B01.3 → B01.7 → B01.4 → B01.5 → B01.6 →
  B02.2 → B02.5 → B03.1 → B03.2 → B03.3 → B03.4 → B04.1 → B04.2 → B05.1 →
  B02.3 → B06.1`.
- Remaining-work ledger: `B01.1` is `[x]`; every later B task is `[ ]` pending until its
  task-specific implementation and gate are evidenced. Historical P0–P4 and V2-A receipts are
  not restarted, but their unresolved validation limitations remain applicable where the master
  plan calls them out.
- Contracts preserved: no backend, retrieval, ranking, generation, persistence, frontend runtime,
  data, or test behavior was modified.
- Commands run and exact results: `git status --short --branch`, `git diff --stat`, `git diff -- .
  ':(exclude)data'`, and `rg -n "V2-B" docs` were inspected; the master plan file was created
  from the attached 1,452-line source. Documentation validation is pending the fast gate below.
- Integration level: `NONE` (documentation task).
- Browser/backend/process validation: not applicable; no process was started.
- Unresolved issue or “none”: none for B01.1. The existing dirty worktree and pre-existing
  `harness_stacks.txt` remain intentionally untouched.
- Rollback slice: the new master-plan file and this reconciliation entry only.
- Next task: `V2-B02.4` — make integration tooling safe and sufficient.

## V2-B02.4 receipt — 2026-09-10

- Task ID / status: `V2-B02.4` / `[x]`.
- Starting code binding: HEAD `c3ccc51` with the pre-existing Addendum implementation and
  untracked files preserved; ports 4173, 4175, 8765 and 8766 were free before the task.
- Files changed: `tests/integration/harness_server.py`,
  `tests/integration/test_http_sse_integration.py`,
  `frontend/playwright.integration.config.ts`, `frontend/playwright.local.config.ts`,
  `frontend/e2e/integration.spec.ts`, `frontend/e2e/workspace.local.spec.ts`,
  `frontend/package.json`, `.gitignore`, and this checkpoint.
- Implementation summary: normal harness streams now emit deterministic reported stage events;
  source payloads retain document/chunk identity; the harness exposes four indexed document
  chunks for catalog/detail/neighbor verification; stack traces and Qdrant paths use isolated
  task-owned temp directories without overwriting `harness_stacks.txt`; occupied harness ports
  fail closed; integration and local previews refuse server reuse and build into separate
  `dist-integration`/`dist-local` outputs. Added a provider-free local workspace spec covering
  rendered stages, source reader identity, neighboring excerpts, and readiness transitions.
- Contracts preserved: production API routes, retrieval/ranking/generation semantics, corpus data,
  and frontend production behavior were not changed; all fixtures remain test-only. The existing
  fragmentation, cancellation, session, error, and comparative integration coverage remains.
- Commands run and exact results: `py_compile` passed; `frontend bun run lint` passed;
  `.venv\Scripts\python.exe -m pytest -q tests\integration\test_http_sse_integration.py`
  passed (`14 passed`); `frontend bun run test:e2e-local` passed (`4 passed`, Chromium/Firefox);
  `frontend bun run test:e2e-integration` passed (`14 passed`, Chromium/Firefox); `git diff --check`
  passed. Generated preview outputs are ignored by `frontend/dist-*/` and are not implementation
  artifacts for commit.
- Integration level: `HERMITIC` — real FastAPI harness, HTTP/SSE transport, fragmented proxy,
  deterministic stages, document catalog/chunk detail, and isolated production previews.
- Browser states inspected: normal stream, execution-stage disclosure, retrieved-sources opening,
  citation-to-reader selection, source metadata/chunk identity, neighboring indexed excerpt,
  readiness 503/restore, fragmented SSE, interrupted stream, reload/session memory, comparative
  stream, and backend-error sanitization in Chromium and Firefox.
- Backend/process ownership: only task-started harness/preview processes ran; all were stopped by
  Playwright and ports 4173/4175/8765/8766 were free at closeout. No real backend, Qdrant store,
  provider, ingestion, reindex, or deployment process was started.
- Performance validation: not applicable; no optimization was performed.
- Unresolved issue or “none”: none for B02.4. A first browser attempt exposed only task-owned
  assertion/fixture mismatches; after correction all required gates passed.
- Rollback slice: harness fixtures/temp isolation, Playwright configs/specs, package scripts and
  generated-output ignore rule; no production endpoint or runtime source rollback is needed.
- Next task: `V2-B02.1` — capture baseline and real-runtime feasibility.

## V2-B02.1 receipt — 2026-09-10

- Task ID / status: `V2-B02.1` / `[x]` for baseline and local provider-free feasibility.
- Starting code binding: worktree after `V2-B02.4`; no production runtime source was changed.
- Files changed: `frontend/e2e/workspace-performance.spec.ts`, the conditional real-backend
  mode in `frontend/playwright.local.config.ts`, and this checkpoint.
- Implementation summary: added measured frontend workloads for warm input, warm view switching,
  palette cycles, source switching/reader paths, and final Markdown layout reads. Added explicit
  labels for workloads intentionally not inferred from provider-free fixtures: the 60-second
  stream with simultaneous typing, empty-overview scope mount, and client network/provider timing.
  The local config now has an explicit `PLAYWRIGHT_REAL_BACKEND=1` mode that starts no backend,
  targets the separately verified API on 8000, and keeps the 4175/dist-local preview isolated.
- Environment preflight: `GROQ_API_KEY5` present; Qdrant mode `local`; local store and model
  cache available; embedding model configured; `http://localhost:4175` was temporarily appended
  to the configured origins for the task process only.
- Commands run and exact results: `.venv\Scripts\python.exe -m uvicorn ... --workers 1` reached
  `/health/live` 200 and `/health/ready` 200 after cached startup; direct provider-free checks
  returned 200 for health, system, documents, document chunks, chunk detail and retrieval inspect.
  `bunx playwright test e2e/workspace-performance.spec.ts --workers=1 --retries=0` passed
  (`4 passed`, 2 intentionally skipped) across Chromium/Firefox. `PLAYWRIGHT_REAL_BACKEND=1
  bunx playwright test -c playwright.local.config.ts --workers=1 --retries=0` passed the local
  backend cases in both browsers (`2 passed`, 4 synthetic cases skipped). `bun run lint` and
  `git diff --check` passed.
- Integration level: `LOCAL BACKEND`, preceded by `HERMITIC`.
- Measured baseline: synthetic Chromium/Firefox p95 respectively — warm input `16.4/46.0 ms`
  (budget 100 ms), warm view switch `115.1/142.0 ms` (budget 200 ms), palette cycle `66.7/81.0 ms`;
  source reader `61.6/60.0 ms`; final Markdown layout read `215.0/314.0 ms` with no fixed budget.
  Local provider-free endpoint timings were approximately `health/live 9.6/10.3 ms`,
  `health/ready 2.9/3.6 ms`, `system/info 3.3/3.9 ms`, `documents 3.2/2.8 ms`,
  chunk listing `2.9/3.4 ms`, chunk detail `2.8/2.7 ms`, and retrieval inspect `251/261 ms`
  for Chromium/Firefox; these are endpoint timings, not generation or provider latency.
- Runtime/browser states inspected: real local production preview at 4175 against backend 8000;
  readiness/system metadata; returned document catalog and exact chunk identity; indexed retrieval
  inspect; synthetic warm input/view/palette, source reader cold/warm, Markdown, reduced external
  traffic, Chromium and Firefox. Existing lifecycle regression tests remain the evidence for
  obsolete-response rejection; it was not remeasured in this baseline task.
- Backend/process ownership: task-started uvicorn PID 17424, one worker, was stopped after the
  gate; ports 3000/4173/4175/8000/8765/8766 were free at closeout. No generation request,
  ingestion, reindex, migration, cache clear or deployment action was performed.
- Unresolved issue or “none”: no blocker. Explicitly unverified workloads are recorded above;
  no optimization was justified by this baseline, so no product performance code changed.
- Rollback slice: performance instrumentation and local-config mode only.
- Next task: `V2-B01.2` — reflow desktop navigation.

## V2-B01.2 receipt — 2026-09-10

- Task ID / status: `V2-B01.2` / `[x]` after the 1024px navigation reflow and
  hard geometry gate.
- Starting code binding: worktree after `V2-B02.1`; the existing Addendum
  implementation and all unrelated dirty files were preserved.
- Files changed: `frontend/src/App.tsx`, `frontend/src/components/Sidebar.tsx`,
  `frontend/src/styles/components.css`, `frontend/e2e/regression.spec.ts`,
  and this checkpoint.
- Implementation summary: App now owns the effective navigation mode through a
  single `min-width: 1024px` media query. The Sidebar receives that mode and is
  an inline flex sibling at and above 1024px, while narrower viewports use the
  existing ModalDialog drawer. The expanded/compact preference key and values
  remain unchanged; crossing into desktop closes an open drawer without
  rewriting the preference. CSS uses the same 1024px boundary, keeps the 216px
  expanded rail and 56px compact rail, and preserves the below-1024 drawer.
- Contracts preserved: workspace route registry, active markers, App-owned
  conversation/evidence state, drawer focus return, existing navigation
  preference storage, API/SSE behavior, and no desktop backdrop/fixed sidebar.
- Commands run and exact results: `frontend/bun run lint` passed; `frontend/bun
  run test` passed (`40` files, `176` tests); `frontend/bun run build` passed;
  `bunx playwright test e2e/regression.spec.ts --grep "navigation reflows at the
  1024px|research shell stays" --workers=1 --retries=0` passed (`4` tests,
  Chromium/Firefox); the conversation-loaded guided portfolio plus navigation
  check passed (`4` tests, Chromium/Firefox); `git diff --check` passed.
- Integration level: `HERMITIC` — provider-free production preview and browser
  fixtures only; no backend, provider, corpus, Qdrant, or deployment process was
  started.
- Browser validation: exact widths `1024`, `1272`, `1280`, and `1440` stayed
  inline with 216px geometry and no main/composer intersection; `1023px`
  opened the drawer. The matrix covered Light/Dark and EN/VI, compact preference
  persistence, active route semantics, focus return, and viewport scroll bounds.
  The rendered production preview was visually inspected at 1440px expanded,
  1440px compact, and 1023px drawer states; the loaded conversation route also
  passed in both Chromium and Firefox.
- Performance validation: no optimization was performed; the existing 160ms
  navigation transition remains unchanged.
- Accessibility validation: compact routes retain accessible names/tooltips;
  drawer close and focus return passed; the existing 44px navigation targets and
  visible focus styles remain in force.
- Unresolved issue or “none”: none for B01.2.
- Rollback slice: App effective-mode state/prop, Sidebar mode consumption, the
  navigation media-query boundary, and its regression coverage only.
- Next task: `V2-B01.3` — correct navigation foreground states.

## V2-B01.3 receipt — 2026-09-10

- Task ID / status: `V2-B01.3` / `[x]` after semantic foreground, state, and
  contrast checks.
- Starting code binding: worktree after `V2-B01.2`; no unrelated dirty files
  were reverted or reformatted.
- Files changed: `frontend/src/components/WorkspaceHeader.tsx`,
  `frontend/src/components/ChatMessage.tsx`,
  `frontend/src/components/SubQueriesPanel.tsx`,
  `frontend/src/styles/components.css`, `frontend/e2e/regression.spec.ts`,
  and this checkpoint.
- Implementation summary: replaced confirmed `dark:text-slate-300` foreground
  misuse, which resolved to the compatibility border token, with explicit
  `--text-primary`/`--text-muted` roles in the header, assistant state, query
  interpretation, and sub-query surfaces. Header navigation controls now use
  semantic surface/border/text roles for hover, pressed, focus-visible, open,
  and selected states; the layout toggle exposes `aria-pressed`; header action
  targets are at least 44px. No global slate alias or theme preference was
  changed.
- Contracts preserved: theme preference and system resolution, locale controls,
  navigation routes/active markers, ChatMessage citation and feedback actions,
  SubQueriesPanel disclosure behavior, and all API/SSE/data contracts.
- Commands run and exact results: `frontend/bun run lint` passed; focused App
  and ChatMessage tests passed (`2` files, `25` tests); `frontend/bun run build`
  passed; the focused Chromium/Firefox navigation plus conversation-loaded
  browser gate passed (`4` tests); `git diff --check` passed.
- Integration level: `NONE` — frontend-only semantic styling and browser
  fixture validation; no backend/provider/process was required.
- Browser/accessibility validation: the rendered production preview was
  inspected in Dark and Light at 1440px and in Vietnamese; automated coverage
  also exercised EN/VI and both themes. Computed foreground colors differed
  from border colors, header/navigation controls measured at least 44px, and
  active/open/focus states remained recognizable without hover.
- Performance validation: only color, surface, border, and transform
  transitions changed; no fetch, rendering, or persistence path changed.
- Unresolved issue or “none”: none for B01.3.
- Rollback slice: semantic header/control classes, the two confirmed
  ChatMessage/SubQueriesPanel foreground corrections, and their regression
  assertions only.
- Next task: `V2-B01.7` — make narrow-header controls explicit.

## V2-B01.7 receipt — 2026-09-10

- Task ID / status: `V2-B01.7` / `[x]` after the narrow-header hard gate.
- Starting code binding: worktree after `V2-B01.3`; the existing header/theme
  preferences and unrelated dirty work were preserved.
- Files changed: `frontend/src/components/WorkspaceHeader.tsx`,
  `frontend/src/components/ConnectionStatus.tsx`, `frontend/src/styles/components.css`,
  `frontend/src/App.test.tsx`,
  `frontend/e2e/regression.spec.ts`, and this checkpoint.
- Implementation summary: below 768px the header now exposes exactly the four
  direct controls required by the layout contract: navigation, compact status,
  command palette, and More workspace controls. The view picker is delegated to
  the navigation drawer at phone widths. Theme, locale, help, and reset are in
  one existing ModalDialog with a real initial-focus target, 44px actions, and
  semantic selected/pressed states. Help closes More before opening on the next
  animation frame; there are no hidden focusable duplicate secondary controls.
  At 768px and above the direct header controls remain available.
- Contracts preserved: command shortcut/callback, theme preference and system
  mode, locale persistence, reset confirmation, navigation drawer semantics,
  help content, API/SSE behavior, and no new fetch or menu framework.
- Commands run and exact results: `frontend/bun run lint` passed; `frontend/bun
  run test` passed (`40` files, `177` tests); `frontend/bun run build` passed;
  `bunx playwright test e2e/regression.spec.ts --grep "narrow header exposes|320px
  smoke|narrow-viewport reflow" --workers=1 --retries=0` passed (`6` tests,
  Chromium/Firefox); `git diff --check` passed.
- Integration level: `NONE` — frontend-only production preview and hermetic
  browser fixtures; no backend/provider/process was required.
- Browser/accessibility validation: 320px, 390px, and 768px were checked in
  both Chromium and Firefox, with EN and VI. The gate verified no horizontal
  overflow, compact connection status, command reachability, More dialog focus
  trap/return, More-to-Help sequencing, direct-control visibility, and 44px
  targets. The production preview was visually inspected at 320px in Vietnamese
  and showed the four-control header plus an in-bounds More dialog.
- Performance validation: no added fetch or data work; only header state,
  presentation, and existing modal mechanics are used.
- Unresolved issue or “none”: none for B01.7.
- Rollback slice: narrow header control grouping, More dialog presentation/state,
  compact status styling, and related App/browser coverage only.
- Next task: `V2-B01.4` — unify evidence modes and lifecycle.

## V2-B01.4 receipt — 2026-09-10

- Task ID / status: `V2-B01.4` / `[x]` after the evidence lifecycle and
  responsive-mode hard gate.
- Starting code binding: worktree after `V2-B01.7`; unrelated dirty changes
  and the existing indexed-excerpt/cache contracts were preserved.
- Files changed: `frontend/src/App.tsx`,
  `frontend/src/components/ContextPanel.tsx`,
  `frontend/src/components/EvidenceWorkspaceRail.test.tsx`,
  `frontend/src/styles/components.css`, `frontend/e2e/regression.spec.ts`,
  and this checkpoint.
- Implementation summary: App now owns evidence selection/open state and
  measures the remaining post-navigation workspace once with ResizeObserver.
  Inline evidence is gated by the specified `W >= 888` formula with the
  preferred rail width clamped to the available `W - 496` space; narrower
  states use one explicit right-aligned evidence drawer. The same
  ContextPanel instance remains mounted while closed or while switching
  inline/drawer presentation, and reader search, page, and text-scale state
  is lifted only far enough to survive the drawer portal remount. Closing
  retains the exact message/variant/citation/chunk identity and resolves the
  current citation button for focus return.
- Lifecycle safeguards: neighbor detail requests now use an AbortSignal plus
  a request identity guard on replacement and unmount; nearby-list requests
  invalidate their identity on cleanup; resize listeners clean up on
  pointerup, pointercancel, and component unmount. Missing or removed sources
  remain explicit unavailable/empty states without fallback substitution.
- Commands run and exact results: `frontend/bun run lint` passed;
  `frontend/bun run test` passed (`40` files, `179` tests);
  `frontend/bun run build` passed; targeted Chromium/Firefox browser coverage
  passed (`4` tests for exact citation/drawer/inline behavior plus the
  existing citation/contrast/reduced-motion checks); `git diff --check` passed.
- Integration level: `NONE` — this was a frontend lifecycle/presentation
  slice; no backend or provider process was needed. The existing hermetic
  browser fixtures supplied the H evidence identity path.
- Browser/accessibility validation: the rendered production preview was
  inspected at a narrow viewport, and the browser gate exercised 1440px
  expanded inline, 1024px expanded drawer, 1024px compact inline, and the
  390px drawer path in Chromium and Firefox. Drawer focus traps and return,
  explicit Close, exact source reopening, separator bounds, and no stale
  neighbor content were verified. A pre-existing contrast gate surfaced the
  `Question scope` label at 4.47:1; its semantic role was corrected to the
  existing passing muted token and the gate then passed in both browsers.
- Performance validation: source switching and neighbor lookup retain the
  existing cache API; the new cancellation paths avoid stale state commits
  without changing cache architecture or network payloads.
- Unresolved issue or “none”: none for B01.4.
- Rollback slice: App evidence open/measurement/focus state, ContextPanel
  presentation and cancellation guards, evidence drawer/inline CSS, and the
  focused lifecycle/browser assertions only.
- Next task: `V2-B01.5` — attach the composer to conversation geometry.

## V2-B01.5 receipt — 2026-09-10

- Task ID / status: `V2-B01.5` / `[x]` after the conversation geometry and
  scroll-behavior hard gate.
- Starting code binding: worktree after `V2-B01.4`; existing draft ownership,
  send behavior, conversation scroll refs, and unrelated dirty changes were
  preserved.
- Files changed: `frontend/src/App.tsx`, `frontend/src/styles/components.css`,
  `frontend/e2e/regression.spec.ts`, and this checkpoint.
- Implementation summary: the conversation view now has one bounded message
  scroller and one composer in the primary column, while the same existing
  ChatInput JSX/state remains the single draft owner. Overview and tool views
  retain their existing outer composer placement. The workspace main ref now
  measures the post-navigation width independently from the conversation
  scroller; evidence rail/drawer geometry remains attached to the primary
  column. Near-bottom follow, reading older answers, scroll-to-latest, and
  per-token rendering semantics were retained without changing send or API
  contracts.
- Contracts preserved: draft persistence and controlled input behavior,
  request snapshots, send/stop/cancel flows, conversation switching,
  citation/evidence selection, navigation layout preference, and all backend
  and SSE contracts.
- Commands run and exact results: `frontend/bun run lint` passed; the full
  unit suite passed (`40` files, `179` tests; one earlier parallel timing
  flake passed on immediate isolated and full reruns); `frontend/bun run build`
  passed; the full Chromium/Firefox regression suite passed (`58` tests,
  workers=1, retries=0); the repeated drawer focus gate passed (`10` tests,
  5 repetitions across both browsers); `git diff --check` passed.
- Integration level: `NONE` — frontend-only geometry and scroll behavior with
  hermetic API fixtures; no backend/provider process was required.
- Browser/accessibility validation: the browser gate verified the primary,
  message-scroller, composer, and latest-answer rectangles at 1440px and
  1024px, multiline draft preservation through the width transition, exact
  citation focus return, both themes/locales, reduced-motion visibility, and
  no horizontal overflow through the existing narrow viewport suite. The
  production preview was also inspected at a narrow offline Vietnamese
  viewport; the composer remained visible and in bounds.
- Performance validation: full regression p95 samples remained within the
  existing gates: Library search `69.91ms` against `<200ms`, and the
  200-message composer input `29.00ms` against `<100ms`.
- Unresolved issue or “none”: none for B01.5. The initial focus timing race
  was resolved by moving citation restoration into the post-close React effect
  and retrying until the modal `inert` cleanup and citation node recreation
  settle.
- Rollback slice: conversation-only composer/scroller structure, workspace
  and primary-column geometry rules, citation focus restoration, and the new
  bounded-geometry regression assertion only.
- Next task: `V2-B01.6` — complete the automated layout matrix and interaction
  harness.

## V2-B01.6 receipt — 2026-09-10

- Task ID / status: `V2-B01.6` / `[x]` after the combined A–G layout matrix,
  modal lifecycle, and focus/hit-testing gate.
- Starting code binding: worktree after `V2-B01.5`; the existing width
  breakpoints, navigation preference key, source identity path, and unrelated
  dirty work were preserved.
- Files changed: `frontend/e2e/workspace-layout.spec.ts`,
  `frontend/src/styles/components.css`, `frontend/src/App.tsx`,
  `frontend/src/components/ChatMessage.tsx`, and this checkpoint.
- Implementation summary: added one hermetic A–G matrix covering expanded and
  compact desktop navigation, inline evidence, 1024px remaining-width drawer,
  mobile navigation drawer, and mobile evidence drawer. Assertions cover exact
  rectangle containment/intersections, center hit tests, stored navigation
  preference, keyboard close, `inert`/portal cleanup, focus return, and the
  drawer-to-inline plus drawer-to-desktop breakpoint transitions across Light /
  Dark and EN / VI. The first matrix run found a real B01.5 edge: the grid
  primary column used intrinsic height while inline evidence was open. The
  bounded grid row/primary stretch rule fixes that without changing data or
  send behavior. Source-inspector focus now owns citation focus when present,
  and pending focus restoration is canceled when a new navigation interaction
  starts.
- Contracts preserved: API/SSE fixture shape, evidence/source/chunk identity,
  composer ownership, navigation layout persistence, modal semantics, and
  existing breakpoint widths.
- Commands run and exact results: `frontend/bun run lint` passed; focused App
  and ChatMessage tests passed (`2` files, `26` tests); the full unit suite
  passed (`40` files, `179` tests); `frontend/bun run build` passed; the new
  layout spec passed with Chromium and Firefox (`2` tests, workers=1,
  retries=0); the full Chromium/Firefox regression suite passed (`58` tests,
  workers=1, retries=0); `git diff --check` passed.
- Integration level: `HERMITIC` — API fixtures and browser storage only; no
  backend/provider process was required, and every non-preview network request
  remained blocked by the fixture harness.
- Browser/accessibility validation: A–G ran in both browsers for Light/Dark and
  EN/VI. The production preview was also inspected in the Codex browser at a
  narrow Vietnamese offline state; the onboarding, header, and composer stayed
  in bounds with no visible clipping. No matrix retries or uninspected
  screenshots were used.
- Performance validation: the unchanged full regression budgets remained green:
  Library search p95 `64.44ms` against `<200ms`, and 200-message composer
  input p95 `29.00ms` against `<100ms`.
- Unresolved issue or “none”: none for B01.6.
- Rollback slice: `workspace-layout.spec.ts` plus the bounded inline-evidence
  grid stretch and citation-focus lifecycle corrections only.
- Next task: `V2-B02.2` — reject obsolete Search responses.

## V2-B02.2 receipt — 2026-09-10

- Task ID / status: `V2-B02.2` / `[x]` after the obsolete-response, scope-change,
  unmount, and duplicate-submit gate.
- Starting code binding: worktree after `V2-B01.6`; the existing retrieval
  payload, submit-only behavior, and unrelated dirty work were preserved.
- Files changed: `frontend/src/components/SearchWorkspace.tsx`,
  `frontend/src/components/SearchWorkspace.test.tsx`, and this checkpoint.
- Implementation summary: Search now owns a monotonically increasing request
  sequence plus an `AbortController`, captures the submitted ticker/section
  scope, and guards success, error, and finally mutations against both request
  identity and current scope. Scope changes abort and invalidate the active
  request and clear mismatched results; unmount performs the same cleanup.
  Same-scope refreshes retain the labeled prior results with an explicit
  loading status, while a changed scope does not show stale results. The
  disabled loading control preserves submit-only retrieval and rejects a
  second click.
- Contracts preserved: existing `inspectRetrieval` payload and optional
  `AbortSignal`, preset/trace shape, offline guard, result rendering, and
  `Use in Research` scope handoff.
- Commands run and exact results: `frontend/bun run lint` passed; the focused
  SearchWorkspace suite passed (`1` file, `6` tests); the full unit suite
  passed (`40` files, `184` tests); the existing production build passed; the
  full Chromium/Firefox regression suite passed (`58` tests, workers=1,
  retries=0); the provider-free local browser harness passed (`4` tests,
  Chromium/Firefox, workers=1, retries=0); `git diff --check` passed.
- Integration level: `HERMITIC + LOCAL HARNESS` — request races were tested
  with mocked delayed success/failure and abort signals, while the local
  provider-free browser stack retained the existing evidence/search fixture
  coverage. No external provider call was required.
- Browser/accessibility validation: the existing regression and local harness
  gates retained both-browser loading, offline, scope, result, and evidence
  behavior; the rendered result exposes `aria-busy`, a polite refresh status,
  and the submitted scope label while a same-scope request is pending.
- Performance validation: no automatic retrieval was introduced; the full
  regression budgets remained green with Library search p95 `83.88ms` against
  `<200ms` and 200-message composer input p95 `29.00ms` against `<100ms`.
- Unresolved issue or “none”: none for B02.2.
- Rollback slice: SearchWorkspace request sequence/controller, submitted-scope
  guards/status, and the focused stale-response/double-submit tests only.
- Next task: `V2-B02.5` — bind Retrieval Lab results to submitted configuration.

## V2-B02.5 receipt — 2026-09-10

- Task ID / status: `V2-B02.5` / `[x]` for the implementation and hermetic
  acceptance gates; assigned `LOCAL BACKEND` gate remains `[!]` because the
  verified API was unavailable.
- Starting code binding: worktree after `V2-B02.2`; the existing retrieval
  presets, comparison controls, export affordances, and unrelated dirty work
  were preserved.
- Files changed: `frontend/src/components/RetrievalLabPanel.tsx`,
  `frontend/src/components/RetrievalLabPanel.test.tsx`,
  `frontend/e2e/regression.spec.ts`, and this checkpoint.
- Implementation summary: Retrieval Lab now captures the exact submitted
  question, filters, top K, candidate pool, primary preset, and comparison
  preset. Any query/filter/ranking/preset/comparison edit aborts and
  invalidates the active request, clears mismatched primary/comparison traces,
  and announces that a new run is required. Primary and delayed comparison
  responses require both the request ID and configuration key to match before
  mutating state; route exit aborts the request as well. Completed trace output
  displays its submitted query/configuration, and JSON/CSV export is derived
  from the trace fields rather than live controls. Controls remain edit-only;
  no automatic inspect was introduced.
- Contracts preserved: existing `inspectRetrieval` payload and optional
  `AbortSignal`, trace/comparison shape, preset selection, backend/offline
  guard, Research handoff, and download filenames.
- Commands run and exact results: `frontend/bun run lint` passed; the focused
  RetrievalLabPanel suite passed (`1` file, `8` tests); the full unit suite
  passed (`40` files, `188` tests); `frontend/bun run build` passed; the new
  loading-edit/export browser test passed in Chromium and Firefox (`2` tests,
  workers=1, retries=0); the full Chromium/Firefox regression suite passed
  (`60` tests, workers=1, retries=0); the provider-free local harness passed
  (`4` tests, Chromium/Firefox, workers=1, retries=0); `git diff --check`
  passed.
- Integration level: `HERMITIC + LOCAL HARNESS`; the H comparison race,
  route-exit, export, and delayed-response checks are covered by focused unit
  tests, and the browser gate exercises the provider-free fixture path. The
  assigned real local-backend probe was attempted with
  `PLAYWRIGHT_REAL_BACKEND=1` but both browser projects failed at
  `GET http://127.0.0.1:8000/health/live` with `ECONNREFUSED`; no retrieval or
  provider call was made.
- Browser/accessibility validation: the production preview was inspected at a
  narrow viewport in offline state; the Lab header, status chip, question
  field, and run control remained in bounds without visible clipping. The
  browser gate verified edit-during-loading invalidation, stale-trace removal,
  accessible configuration-change status, and completed JSON download in both
  browsers.
- Performance validation: the full regression budgets remained green with
  Library search p95 `85.06ms` against `<200ms` and 200-message composer input
  p95 `31.00ms` against `<100ms`; controls still do not trigger inspection on
  change.
- Unresolved issue or blocker: `[!]` real local-backend readiness/retrieval
  gate is blocked by `ECONNREFUSED 127.0.0.1:8000`; retry only when the
  separately verified local API is available. No implementation or hermetic
  test blocker remains.
- Rollback slice: RetrievalLab request/snapshot invalidation, submitted
  configuration/status rendering, trace-anchored export serialization, and
  the focused unit/browser assertions only.
- Next task: `V2-B03.1` — refine research message hierarchy.

## V2-B03.1 receipt — 2026-09-10

- Task ID / status: `V2-B03.1` / `[x]` after the answer-hierarchy,
  single-inspector, responsive-action, and persistence/deep-link gates.
- Starting code binding: worktree after `V2-B02.5`; the existing answer
  variants, citation identity, pipeline trace, feedback/note/bookmark actions,
  fallback source panel, and unrelated dirty work were preserved.
- Files changed: `frontend/src/components/ChatMessage.tsx`,
  `frontend/src/styles/components.css`, `frontend/src/components/ChatMessage.test.tsx`,
  `frontend/src/App.tsx`, `frontend/e2e/app.spec.ts`,
  `frontend/e2e/integration.spec.ts`, `frontend/e2e/regression.spec.ts`,
  `frontend/e2e/workspace-performance.spec.ts`, and this checkpoint.
- Implementation summary: assistant messages now present identity/state first,
  the answer and citations before secondary controls, and real source-count,
  variant, and elapsed metadata before the action row. Copy and Sources are
  primary actions; bookmark, feedback, saved variants, notes, feedback reasons,
  interpreted query, pipeline stages, and sub-queries are secondary disclosure
  or execution detail. When the app-level inspector callback is available,
  the message no longer renders a duplicate source tree; standalone rendering
  retains the legacy source-panel fallback. The shared inspector now preserves
  citation hash anchors and restores a valid source selection after reload.
- Contracts preserved: original and variant citation identity, source fallback
  behavior for legacy metadata, stopped/error rendering, copy/bookmark/feedback/
  note/save-variant callbacks, streaming state, pipeline stages, Markdown
  export, and backend/API/SSE shapes.
- Commands run and exact results: `frontend/bun run lint` passed; focused
  ChatMessage and evidence-selection tests passed (`2` files, `11` tests); the
  full unit suite passed (`40` files, `189` tests); `frontend/bun run build`
  passed; the full application E2E suite passed (`66` tests, Chromium/Firefox,
  workers=1, retries=0); the full regression suite passed (`60` tests,
  Chromium/Firefox, workers=1, retries=0); the integration HTTP/SSE harness
  passed (`14` tests); the provider-free local harness passed (`4` tests,
  Chromium/Firefox); `git diff --check` passed.
- Integration level: `HERMITIC + INTEGRATION HARNESS + LOCAL HARNESS`; the
  real local-backend gate remains the previously recorded `[!]` from B02.5
  (`ECONNREFUSED` at `127.0.0.1:8000/health/live`). No provider call was made
  by the hermetic or harness tests.
- Browser/accessibility validation: both browsers verified the primary Sources
  action opening the shared inspector, source search/copy, citation deep links
  through reload, stopped/error/read-only states, bookmark flow, responsive
  light/dark screenshots at 390/768/1440px, and no duplicate source tree. The
  responsive theme helper uses the actual narrow More-controls dialog. Unit
  coverage retains original/variant identity and the standalone fallback path.
- Performance validation: full regression budgets remained green: Library
  search p95 `36.57ms` Chromium / `81.01ms` Firefox against `<200ms`, and
  200-message composer input p95 `23.10ms` / `31.00ms` against `<100ms`.
- Unresolved issue or blocker: `[!]` real local-backend readiness/retrieval
  gate remains blocked by the previously verified unavailable API; no
  implementation, unit, browser, or harness blocker remains.
- Rollback slice: ChatMessage answer/action hierarchy and disclosure styles,
  app-level shared-inspector/hash synchronization, source-action E2E locator
  updates, and focused hierarchy assertions only.
- Next task: `V2-B03.2` — normalize research response blocks.

## V2-B03.2 receipt — 2026-09-10

- Task ID / status: `V2-B03.2` / `[x]` after the editable-draft, stream
  persistence, reload, and no-concurrent-send gates.
- Starting code binding: worktree after `V2-B03.1`; the existing streaming
  response lifecycle, Stop behavior, message sanitation, library ownership,
  and unrelated dirty work were preserved.
- Files changed: `frontend/src/components/ChatInput.tsx`,
  `frontend/src/components/ChatInput.test.tsx`, `frontend/src/App.tsx`,
  `frontend/src/App.test.tsx`, `frontend/src/hooks/useConversationLibrary.ts`,
  `frontend/src/hooks/useConversationLibrary.test.tsx`,
  `frontend/e2e/fixtures.ts`, `frontend/e2e/app.spec.ts`, and this checkpoint.
- Implementation summary: the textarea remains editable while a request is
  streaming, while send and preflight are disabled so Enter cannot queue or
  submit a concurrent question. The accepted question clears only the draft
  that was actually submitted, so text entered during preflight or streaming
  remains available. Failed preflight leaves the draft intact. Debounced and
  visibility-flush persistence now stores the next draft during streaming but
  excludes incomplete assistant messages; cross-tab repository updates cannot
  replace newer local draft input while an answer is active. Stop and normal
  completion retain their existing message semantics, and reload recovery is
  covered by the delayed-stream browser gate.
- Contracts preserved: IME composition handling, submit-only send behavior,
  existing draft sanitation and storage keys, streaming/Stop/error rendering,
  conversation switching, offline/read-only draft recovery, API/SSE fixture
  shapes, and no queued-send behavior.
- Commands run and exact results: `frontend/bun run lint` passed; the focused
  ChatInput/library/App suite passed (`3` files, `28` tests); the full unit
  suite passed (`40` files, `191` tests); `frontend/bun run build` passed; the
  full Chromium/Firefox application suite passed (`68` tests, workers=1,
  retries=0); the full regression suite passed (`60` tests, workers=1,
  retries=0); the integration HTTP/SSE harness passed (`14` tests); the
  provider-free local harness passed (`4` tests, Chromium/Firefox); and
  `git diff --check` passed. The unit run emitted only the existing expected
  jsdom storage warnings from storage tests.
- Integration level: `HERMITIC + INTEGRATION HARNESS + LOCAL HARNESS`; the
  delayed fixture stream exercised drafting during an active response, while
  the HTTP/SSE and provider-free stacks retained their real transport and
  local-provider coverage. The real local-backend gate remains the previously
  recorded `[!]` from `V2-B02.5` (`ECONNREFUSED` at
  `127.0.0.1:8000/health/live`), and no provider call was made by these gates.
- Browser/accessibility validation: both browsers verified that the next draft
  stays editable during a delayed stream, Enter does not submit it, the Stop
  control remains available, completion preserves the draft, and reload
  restores it from the library. Existing IME, switch, partial-answer, 500
  character, offline/read-only, and responsive application coverage remained
  green. The production preview was inspected in the Codex browser at
  retrieval and offline research states; the question field/composer, status
  chip, onboarding/error state, and controls remained within the viewport with
  no visible clipping.
- Performance validation: full regression budgets remained green with
  Library search p95 `36.34ms` Chromium / `83.95ms` Firefox against `<200ms`,
  and 200-message composer input p95 `27.40ms` / `32.00ms` against `<100ms`.
- Unresolved issue or blocker: `[!]` real local-backend readiness/retrieval
  gate remains blocked by the previously verified unavailable API; retry only
  when the separately verified local API is available. No implementation,
  unit, browser, integration, or local-harness blocker remains.
- Rollback slice: ChatInput acceptance/disable logic, App draft-clear timing,
  streaming-safe library persistence/subscription guard, delayed-stream
  fixture, and focused draft recovery assertions only.
- Next task: `V2-B03.3` — test and harden research response rendering.

## V2-B03.3 receipt — 2026-09-10

- Task ID / status: `V2-B03.3` / `[x]` after the conflict-safe Apply,
  parameter-derived scope, locale, cancellation, focus, and no-auto-send
  gates.
- Starting code binding: worktree after `V2-B03.2`; the existing template
  schemas, localized copy, validation limits, draft ownership, scope owner,
  and unrelated dirty work were preserved.
- Files changed: `frontend/src/App.tsx`, `frontend/src/App.test.tsx`,
  `frontend/src/components/TemplateQuestionDialog.tsx`,
  `frontend/src/components/TemplateQuestionDialog.test.tsx`,
  `frontend/src/components/ui/SelectField.tsx`,
  `frontend/src/lib/researchTemplates.ts`,
  `frontend/src/lib/researchTemplates.test.ts`, `frontend/e2e/app.spec.ts`,
  and this checkpoint.
- Implementation summary: opening a template now captures the active
  conversation, draft, scope, locale, and template identity. Apply returns a
  typed payload with the normalized question, validated values, and a derived
  scope. App verifies that snapshot before applying; stale conversation/draft/
  scope/locale or template identity preserves the current state, closes the
  stale dialog, and reports “Research context changed; reopen this template.”
  Valid Apply updates the draft and scope together, closes, focuses the
  composer, and never sends. Single-company templates apply their selected
  ticker; dependency comparison remains all-company with both companies in
  the question and its comparative preset intact. Localized `[Công ty]` and
  `[năm]` tokens are normalized before rendering. Template select errors now
  expose `aria-invalid` and `aria-describedby`.
- Contracts preserved: EN/VI copy, cancellation/Escape/backdrop semantics,
  5–500 question bounds, reserved placeholder validation, existing template
  section/topK presets, no schema/API migration, draft persistence, and
  submit-only query behavior.
- Commands run and exact results: `frontend/bun run lint` passed; the focused
  dialog/template/App suite passed (`3` files, `30` tests); the full unit suite
  passed (`40` files, `195` tests); `frontend/bun run build` passed; the full
  Chromium/Firefox application suite passed (`74` tests, workers=1,
  retries=0); the full regression suite passed (`60` tests, workers=1,
  retries=0); the integration HTTP/SSE harness passed (`14` tests); the
  provider-free local harness passed (`4` tests, Chromium/Firefox); and
  `git diff --check` passed. The unit run emitted only the existing expected
  jsdom storage warnings from storage tests.
- Integration level: `HERMITIC + INTEGRATION HARNESS + LOCAL HARNESS`; the
  H browser gate proved selecting parameters and Apply cause no request, then
  the later send uses the applied AAPL/financial-table scope. The real
  local-backend gate remains the previously recorded `[!]` from `V2-B02.5`
  (`ECONNREFUSED` at `127.0.0.1:8000/health/live`), and no provider call was
  made by these gates.
- Browser/accessibility validation: both browsers verified valid EN Apply,
  valid VI Apply, Cancel preserving the draft, stale-draft conflict rejection,
  no auto-send, later scoped submission, initial dialog focus, return focus to
  the composer, and field-associated validation errors. The full responsive,
  reduced-motion, visual, and accessibility application matrix remained green.
  The final production preview was inspected in the Codex browser at the
  offline overview and template-dialog states; controls and dialog remained
  within the viewport without visible clipping.
- Performance validation: full regression budgets remained green with
  Library search p95 `39.12ms` Chromium / `85.91ms` Firefox against `<200ms`,
  and 200-message composer input p95 `29.30ms` / `31.00ms` against `<100ms`.
- Unresolved issue or blocker: `[!]` real local-backend readiness/retrieval
  gate remains blocked by the previously verified unavailable API; retry only
  when the separately verified local API is available. No implementation,
  unit, browser, integration, or local-harness blocker remains.
- Rollback slice: template opening snapshot and Apply payload/guard,
  parameter-derived scope/token normalization, select-field error metadata,
  and the focused App/dialog/browser assertions only.
- Next task: `V2-B03.4` — bind commands to displayed answer identity.

## V2-B03.4 receipt — 2026-09-10

- Task ID / status: `V2-B03.4` / `[x]` after the displayed-answer identity,
  live-resolution, race, source-reader, accessibility, and performance gates.
- Starting code binding: worktree after `V2-B03.3`; existing variant storage,
  evidence selection, command palette keyboard model, `saveEvidence` behavior,
  and unrelated dirty work were preserved.
- Files changed: `frontend/src/App.tsx`, `frontend/src/App.test.tsx`,
  `frontend/src/components/ChatMessage.tsx`,
  `frontend/src/components/ChatMessage.test.tsx`, `frontend/src/types.ts`,
  `frontend/src/lib/i18n.tsx`, `frontend/e2e/app.spec.ts`,
  `frontend/e2e/fixtures.ts`, and this checkpoint.
- Implementation summary: App now owns an ID-only transient
  `{conversationId, messageId, variantId}` display context. ChatMessage
  publishes it when the answer article itself receives focus, when answer
  text/actions are clicked, and when Original/Variant selection changes; it
  does not publish context for each streaming token. Command actions resolve
  the current message/variant/source records from refs at invocation time.
  Copy uses the exact resolved displayed text; Inspect Sources and Save Source
  use the exact selected evidence identity. Deleted or changed variants,
  stale sources, and conversation switches fail closed with a contextual
  notice rather than substituting the newest answer. The palette remains a
  delegate-only command surface, and existing `saveEvidence` semantics remain
  intact. Focus handling avoids rerendering nested citation controls before
  their click events dispatch.
- Contracts preserved: variant persistence and ownership, evidence-selection
  identity, citation deep links, keyboard palette navigation, source reader
  routing, pointer and keyboard interaction, streaming rendering, and no
  global state framework.
- Commands run and exact results: `frontend/bun run lint` passed; full unit
  suite passed (`40` files, `198` tests); `frontend/bun run build` passed;
  full Chromium/Firefox application suite passed (`76` tests, workers=1,
  retries=0); full regression suite passed (`60` tests, workers=1,
  retries=0); integration HTTP/SSE harness passed (`14` tests); provider-free
  local harness passed (`4` tests, Chromium/Firefox); and `git diff --check`
  passed. Unit output contained only the existing expected jsdom storage
  warnings from storage-failure tests.
- Integration level: `HERMITIC + INTEGRATION HARNESS + LOCAL HARNESS`; the
  identity browser fixture used distinct older/newer answers and sources,
  while the real local-backend gate remains the previously recorded `[!]`
  from `V2-B02.5` (`ECONNREFUSED` at `127.0.0.1:8000/health/live`). No
  provider call was made by these gates.
- Browser/accessibility validation: Chromium and Firefox verified that an
  older answer with a saved variant remains the target for palette Copy and
  Inspect Sources, selected evidence opens the matching reader content, stale
  variants fail closed, nested citation clicks preserve deep links, and the
  answer focus model is not pointer-only. The final production preview was
  inspected in the Codex browser at the offline overview; the navigation,
  command control, status banner, onboarding cards, composer, and scope bar
  remained within the viewport without visible clipping.
- Performance validation: full regression budgets remained green with
  Library search p95 `38.15ms` Chromium / `109.61ms` Firefox against `<200ms`,
  and 200-message composer input p95 `30.20ms` / `48.00ms` against `<100ms`.
- Unresolved issue or blocker: `[!]` real local-backend readiness/retrieval
  remains blocked by the previously verified unavailable API; retry only when
  the separately verified local API is available. No implementation, unit,
  browser, integration, or local-harness blocker remains.
- Rollback slice: displayed-answer context callback/types, App ID-based
  command resolvers and live refs, ChatMessage focus/click/variant plumbing,
  palette copy wording, and the focused resolver/browser assertions only.
- Next task: `V2-B04.1` — verify honest execution presentation.

## V2-B04.1 receipt — 2026-09-10

- Task ID / status: `V2-B04.1` / `[x]` after the honest execution
  presentation, timing provenance, accessibility, browser, performance, and
  provider-free validation gates.
- Starting code binding: worktree after `V2-B03.4`; existing request-local
  stage events, legacy trace data, ordering/cancellation behavior, and
  unrelated dirty work were preserved.
- Files changed: `frontend/src/components/PipelineExecution.tsx`,
  `frontend/src/components/PipelineExecution.test.tsx`,
  `frontend/src/components/ChatMessage.test.tsx`,
  `frontend/e2e/regression.spec.ts`, `frontend/e2e/app.spec.ts`, and this
  checkpoint.
- Implementation summary: execution stages now expose reported counters with
  labels, distinguish server measurements from the local 250 ms running-view
  timer, show server final duration for trace summaries, render skipped,
  cancelled, cache, and trace-only states without invented progress, indent
  only valid same-request parent relationships, and label unknown stages
  neutrally. Stage changes are announced through a dedicated polite live
  region without announcing every timer tick; the visible stage list remains
  independently inspectable.
- Contracts preserved: existing event ordering, request-local cancellation,
  legacy trace fallback, cache/skipped/cancelled semantics, compact panel
  presentation, and no backend instrumentation or fabricated stages/timing.
- Commands run and exact results: `frontend/bun run lint` passed; full Vitest
  passed (`41` files, `202` tests); `frontend/bun run build` passed; full
  Chromium/Firefox application coverage passed (`76` tests, workers=1,
  retries=0); full regression coverage passed (`60` tests, workers=1,
  retries=0); HTTP/SSE integration harness passed (`14` tests); provider-free
  local harness passed (`4` tests); and `git diff --check` passed. The existing
  jsdom storage-fault warnings remained expected test output.
- Integration level: `HERMITIC + INTEGRATION HARNESS + LOCAL HARNESS`; the
  real local-backend gate remains the previously recorded `[!]`
  (`ECONNREFUSED` at `127.0.0.1:8000/health/live`). No provider call was made
  by these gates.
- Browser/accessibility validation: Chromium and Firefox covered stage-event
  rendering, preserved drafts, citations, stopped streams, responsive/reduced
  motion layouts, and the focused displayed-answer identity flow. The final
  production preview was inspected in the Codex browser at the offline
  overview; navigation, connection state, onboarding, composer, scope bar,
  and cards remained within the viewport without visible clipping.
- Performance validation: regression budgets remained green with Library
  search p95 `42.59ms` Chromium / `76.22ms` Firefox against `<200ms`, and
  200-message composer input p95 `35.20ms` / `36.00ms` against `<100ms`.
  Running-stage timing uses only the local 250 ms refresh interval; reported
  elapsed values remain server-labelled.
- Unresolved issue or blocker: `[!]` real local-backend readiness/retrieval
  remains blocked by the previously verified unavailable API; retry only when
  the separately verified local API is available. No implementation, unit,
  browser, integration, or local-harness blocker remains.
- Rollback slice: execution-stage presentation/counter/timing/accessibility
  changes, the focused component tests, and the scoped browser selector/test
  updates only.
- Next task: `V2-B04.2` — finish concise discoverability and metadata parity.

## V2-B04.2 receipt — 2026-09-10

- Task ID / status: `V2-B04.2` / `[x]` after the metadata, copy, registry
  parity, responsive, accessibility, and provider-free validation gates.
- Starting code binding: worktree after `V2-B04.1`; existing workspace routes,
  health/scope owners, templates, guides, and tool behavior were preserved.
- Files changed: `frontend/src/App.tsx`,
  `frontend/src/components/ConnectionStatus.tsx`, `OverviewPanel.tsx`,
  `ContextPanel.tsx`, `SearchWorkspace.tsx`, `DocumentExplorerPanel.tsx`,
  `RetrievalLabPanel.tsx`, `ArchitecturePanel.tsx`, `EvaluationPanel.tsx`,
  `AnalyticsPanel.tsx`, `SystemInfoPanel.tsx`,
  `frontend/src/lib/workspace.ts`, focused registry/App/browser assertions,
  and this checkpoint.
- Implementation summary: the overview keeps the truthful sequence heading →
  service-reported corpus metadata → current scope → readiness/offline state
  → four templates → three local recents → collapsed guidance. Configured
  ticker lists no longer appear as searchable-corpus counts. Readiness copy
  no longer promises an estimated wait; connection metadata distinguishes
  searchable companies from index readiness. Source-panel copy now states that
  counts are answer-local retrieved sources and rank scores are ordering
  signals, not confidence. Tool headers and the Library intro consume the
  existing workspace registry for icons/descriptions through
  `getWorkspaceNavItem` and the semantic icon map.
- Contracts preserved: no additional requests or polling, no new state owner,
  existing routes/guides/templates/source reader behavior, EN/VI handling,
  and provider-free tool semantics.
- Commands run and exact results: `frontend/bun run lint` passed; full Vitest
  passed (`41` files, `203` tests); `frontend/bun run build` passed; full
  Chromium/Firefox application coverage passed (`76` tests, workers=1,
  retries=0); HTTP/SSE integration harness passed (`14` tests); provider-free
  local harness passed (`4` tests); and `git diff --check` passed. Existing
  jsdom storage-fault warnings remained expected test output.
- Browser/accessibility validation: the application matrix covered both
  themes at 1440/768/390 widths plus 320px and reduced-motion smokes; the
  existing locale/reflow scenarios passed in Chromium and Firefox. The full
  regression run passed `59/60` in each final attempt because one Chromium
  evidence-drawer scenario timed out while an overlay intercepted the layout
  toggle; the exact scenario passed in a focused Chromium/Firefox rerun before
  the reverted wait experiment. This is retained as a runner-only timing
  caveat, not an implementation failure. The final production preview was
  inspected in the Codex browser at the offline overview; the explicit offline
  readiness copy, reported-metadata notice, scope bar, templates, composer,
  and narrow layout remained legible without visible clipping.
- Performance validation: the regression performance probes remained below
  budget in the final run: Library search p95 `49.81ms` Chromium / `90.87ms`
  Firefox against `<200ms`, and 200-message composer input p95 `28.50ms` /
  `35.00ms` against `<100ms`. No additional request was introduced.
- Integration level: `HERMITIC + INTEGRATION HARNESS + LOCAL HARNESS`; the
  real local-backend metadata gate remains the previously recorded `[!]`
  (`ECONNREFUSED` at `127.0.0.1:8000/health/live`). No provider call was made
  by these gates.
- Unresolved issue or blocker: `[!]` real local-backend readiness/retrieval
  remains unavailable and the full regression runner retains the pre-existing
  Chromium drawer-timing flake described above. No implementation, unit,
  application, integration, local-harness, or production-preview blocker
  remains.
- Rollback slice: overview/readiness/count copy, registry lookup and tool
  intro consumers, source-count/ranking explanation, and the focused tests
  only.
- Next task: `V2-B05.1` — refine compact brand.

## V2-B05.1 receipt — 2026-09-10

- Task ID / status: `V2-B05.1` / `[x]` after the compact-mark geometry,
  accessibility, forced-colors, static-SVG, and visual-preview gates.
- Starting code binding: worktree after `V2-B04.2`; existing BrandMark
  callers, lockup text, navigation behavior, and unrelated dirty work were
  preserved.
- Files changed: `frontend/src/components/BrandMark.tsx`,
  `frontend/src/components/BrandMark.test.tsx`,
  `frontend/src/styles/components.css`, and this checkpoint.
- Implementation summary: replaced the filing checkmark with an original
  folded-filing-page plus single search/evidence connection silhouette;
  removed the inert glow layer; kept the decorative `aria-hidden` lockup;
  retained `currentColor` SVG strokes; added explicit 16/24/32/48px semantic
  hooks (`xs`/`sm`/`md`/`lg`); and added a forced-colors monochrome fallback.
  Existing product names and all existing callers remain unchanged.
- Contracts preserved: no icon-system or product rename, no data/API change,
  static SVG with no filter/animation node, no permanent glow, and compact
  rail/header geometry.
- Commands run and exact results: focused BrandMark Vitest passed (`2` tests);
  `frontend/bun run lint` passed; `frontend/bun run build` passed; full
  Vitest passed with `--retry=2` (`41` files, `204` tests); and
  `git diff --check` passed. The retry-free full Vitest invocation reported
  one timing-sensitive failure in the unrelated App session-history test
  (`203/204`); that test passed in isolation and no BrandMark test failed.
- Browser/accessibility validation: the rebuilt production preview was
  inspected at `1440×900` in light and dark themes. The live 24px header mark
  and 32px sidebar mark were legible, the lockup remained intact, and no
  visible clipping or contrast regression appeared. The component test covers
  the 16/24/32/48px hooks, decorative SVG hiding, currentColor strokes, and
  absence of filter/animation/glow nodes. The forced-colors CSS path removes
  decorative shadow and uses Canvas/CanvasText roles.
- Integration level: `NONE` by contract; no backend/provider call was made.
- Unresolved issue or blocker: `[!]` the existing retry-free App
  session-history unit test remains timing-sensitive under the full Vitest
  runner; isolated and retry-enabled validation pass. This is unrelated to
  the BrandMark slice. The previously recorded local FastAPI readiness gate
  remains unavailable at `127.0.0.1:8000/health/live`.
- Rollback slice: BrandMark geometry/markup, BrandMark focused assertions,
  and the compact-mark CSS/forced-colors rules only.
- Next task: `V2-B02.3` — retain only measured optimization.

## V2-B02.3 receipt — 2026-09-10

- Task ID / status: `V2-B02.3` / `[x] NO CODE CHANGE REQUIRED` after the
  three-run performance and regression-preservation gate.
- Starting code binding: worktree after `V2-B05.1`; no frontend/backend source
  file was changed for this task.
- Measurement method: identical provider-free
  `e2e/workspace-performance.spec.ts` workload, one worker, zero retries,
  executed three times against a freshly built production preview each run.
  Each run passed `4` tests and skipped the two real-backend cases because
  `127.0.0.1:8000` is unavailable.
- Comparable results: Chromium warm composer p95 was `15.00`, `13.70`, and
  `15.90ms`; Firefox was `25.00`, `39.00`, and `46.00ms` against `≤100ms`.
  Chromium warm view-switch p95 was `139.40`, `117.40`, and `130.20ms`;
  Firefox was `154.00`, `139.00`, and `153.00ms` against `≤200ms`. Unbudgeted
  source/reader and final-Markdown probes were retained as observations only;
  no threshold or measured hotspot justified a patch.
- Decision: retain the existing message-row ownership, resize/motion behavior,
  80ms streaming batching, and component architecture. No broad memoization,
  virtualization, batching, framework, or state refactor was introduced.
- Commands run and exact results: three identical performance runs each
  passed (`4 passed, 2 skipped`); existing output reported the documented
  unverified 60-second stream and local-backend measurements; and
  `git diff --check` passed.
- Integration level: `HERMITIC`; no affected runtime-facing source changed,
  so no additional local gate was required.
- Unresolved issue or blocker: `[!]` the real local-backend performance cases
  remain unavailable at `127.0.0.1:8000`; the provider-free budgets and all
  measured frontend paths passed. No implementation blocker remains.
- Rollback slice: none; this is a no-code-change receipt.
- Next task: `V2-B06.1` — close integrated product gates.

## V2-B06.1 receipt — 2026-09-10

- Task ID / status: `V2-B06.1` / `[!] PARTIAL — implementation and all
  available gates are green; native browser-zoom inspection remains
  unavailable in the connected browser surface.`
- Starting code binding: worktree after `V2-B02.3`; unrelated dirty work and
  the immutable `data/` boundary were preserved.
- Files changed for final closure: `frontend/src/App.tsx` clears the evidence
  deep-link hash when the inspector closes, preventing a responsive remount
  from reopening a closed modal; `frontend/playwright.config.ts` excludes the
  dedicated local-backend specs from the regular hermetic browser gate; and
  `frontend/e2e/workspace-layout.spec.ts` waits through modal transition
  hit-test cleanup while retaining the A–G geometry/focus assertions.
- Static/unit/build gates: `frontend/bun run lint` passed; one-worker Vitest
  passed `41` files / `204` tests; and `frontend/bun run build` passed with
  `1892` modules transformed.
- Browser gates: the regular config ran `72` tests. Chromium passed `71` with
  the single real-backend performance case skipped, repeated twice;
  Firefox passed `71` with the same single skip. The A–G layout, modal
  cleanup, focus, hit-testing, theme/locale, reduced-motion, reader,
  Library/Search/Documents, backup/import, multi-tab, and performance paths
  remained green. Provider-free HTTP/SSE integration passed `14/14`; the
  local harness passed `4/4` in Chromium and Firefox.
- Backend gate: `.venv\\Scripts\\python.exe -m pytest -q` passed `738` tests
  with `121` existing parser/deprecation warnings. `git diff --check` passed.
- Performance evidence: final regular browser probes remained below budget;
  Library search p95 was `42.43ms` Chromium / `89.88ms` Firefox against
  `<200ms`, and 200-message composer input p95 was `30.10ms` / `34.00ms`
  against `<100ms`.
- Product inspection: the production preview was inspected at the offline
  overview in the connected browser. The navigation, offline/readiness
  messaging, composer, scope bar, cards, theme, locale, and narrow layout
  were legible without visible clipping. The required native browser zoom
  checkpoints at `100%`, `125%`, `150%`, and `200%` could not be driven or
  observed through this browser surface, so no native-zoom claim is made.
- Remaining blockers: `[!]` the real local FastAPI readiness/retrieval gate
  remains unavailable at `127.0.0.1:8000/health/live`, while the provider-free
  local harness is green; `[!]` native browser-zoom verification is an
  environment/tooling limitation. No implementation, unit, build, regular
  browser, integration, local-harness, or backend regression blocker remains.
- Rollback slice: the evidence-anchor close behavior, regular Playwright test
  boundary, and transition-stability assertion only.
- Definition-of-Done result: partial delivery is documented because the plan
  explicitly requires leaving `[!]` when native zoom cannot be verified.

## V2-B06.1 continuation receipt — 2026-09-10

- The previously unavailable real backend was started from the existing local
  artifacts and verified before rerunning the remaining live-local checks.
  `GET /health/live`, `/health/ready`, and `/health` returned `200`; readiness
  reported `pipeline_ready=true`, `50` searchable companies, and `10053`
  indexed chunks.
- The real-backend performance/feasibility test passed in both Chromium and
  Firefox with `PLAYWRIGHT_REAL_BACKEND=1`: `2 passed, 4 skipped` total because
  the two synthetic-only tests are intentionally skipped in real-backend mode.
  Retrieval inspection was provider-free and issued no generation request;
  measured retrieval-inspect timings were `244.25ms` Chromium and `256.95ms`
  Firefox in the final two-engine run.
- The real local API blocker is therefore cleared for this gate and the API
  process was stopped cleanly afterward. No source, corpus, index, provider,
  deployment, or secret state changed.
- Remaining Definition-of-Done blocker: `[!]` native browser-chrome zoom at
  `100%`, `125%`, `150%`, and `200%` still cannot be driven or observed in the
  connected browser surface. CSS-viewport equivalents remain green; no
  native-zoom claim is made.

## V2-B06.1 zoom-surface audit — 2026-09-10

- Rechecked the connected-computer inventory: only the Codex in-app browser is
  exposed; named Chrome and Edge surfaces are unavailable. The in-app browser
  exposes the rendered page but no browser-chrome zoom control or measurable
  native zoom setting.
- A scoped temporary-profile headed-Chrome/CDP probe was attempted. The
  environment policy rejected launching the native Chrome process, so no
  browser-chrome zoom value could be established. The temporary probe
  directory was removed and no user browser profile was touched.
- Result remains `[!]` by the master plan's explicit rule: CSS viewport
  equivalents are verified, but native zoom at `100%`, `125%`, `150%`, and
  `200%` still requires a user-visible Chrome/Edge surface or manual evidence.

## V2-B06.1 final closure review — 2026-09-10

- Project status: `IMPLEMENTATION COMPLETE` / `VALIDATION COMPLETE EXCEPT ONE
  EXTERNAL MANUAL-VERIFICATION GATE`.
- Completed implementation tasks: `V2-B01.1`, `V2-B02.4`, `V2-B02.1`,
  `V2-B01.2`, `V2-B01.3`, `V2-B01.7`, `V2-B01.4`, `V2-B01.5`, `V2-B01.6`,
  `V2-B02.2`, `V2-B02.5`, `V2-B03.1`, `V2-B03.2`, `V2-B03.3`, `V2-B03.4`,
  `V2-B04.1`, `V2-B04.2`, `V2-B05.1`, `V2-B02.3`, and the available B06.1
  closure gates.
- Completion evidence: lint, production build, one-worker Vitest `204/204`,
  backend pytest `738 passed`, regular Chromium `71 passed + 1 intentional
  real-backend skip` on two runs, Firefox `71 passed + 1 intentional skip`,
  HTTP/SSE integration `14/14`, local harness `4/4`, and real-local backend
  feasibility in both engines all passed. The recorded matrix covers layout,
  accessibility, source identity, persistence, streaming/cancellation,
  integration, and measured performance; no defect is hidden by the zoom
  limitation.
- Sole active `[!]` item — native browser zoom: the requirement remains
  unchanged. Only the Codex in-app browser was available, which has no
  browser-chrome zoom state/control; named Chrome/Edge were unavailable; and
  the environment policy rejected the temporary headed-Chrome/CDP probe.
  This is an external environment/policy limitation, not a product defect.
- Manual verification procedure: on a user-visible Chrome or Edge instance,
  build and preview the frontend (`cd frontend`, `bun run build`, then
  `bunx vite preview --host 127.0.0.1 --port 4173 --strictPort`), open
  `http://127.0.0.1:4173/`, and use the browser menu to set exactly `100%`,
  `125%`, `150%`, and `200%`. At each value, record the browser-reported zoom
  and `window.innerWidth × window.innerHeight` from DevTools, capture the
  rendered overview and conversation/evidence surface, and verify no
  horizontal overflow, overlay, clipped control, focus loss, or inaccessible
  header/composer/navigation control. Attach the four records to this receipt.
- No production-code workaround is warranted or permitted: altering layout,
  CSS zoom, browser-specific code, or the test suite to simulate native zoom
  would weaken the original requirement rather than verify it. No production
  code remains unfinished.

## V3-C00.1 — identity-safe execution baseline — 2026-09-11

- Status: `[x] complete`.
- Changed files: `frontend/e2e/fixtures.ts` and
  `frontend/e2e/workspace.local.spec.ts`.
- The local browser fixture now resolves `/chunks/{chunk_id}` by exact identity
  and returns `404` for an unknown chunk; it no longer substitutes the first
  sample source. Added a browser HTTP gate for the unknown-identity case.
- Validation: Chromium local harness `3 passed`; the new exact-identity gate,
  readiness gate, and existing indexed-reader identity scenario all passed.
- Integration level: `HERMITIC` / isolated local harness. No provider, corpus,
  index, backend production process, or user storage was touched.
- Browser state inspected: production preview through the local harness,
  exact indexed reader, readiness-down/up, and unknown chunk identity.
- Accessibility/performance: existing C00 browser assertions preserved; no
  performance change in this fixture-only task.
- Owned processes: Playwright-created harness/preview processes exited cleanly.
- Remaining issue: none for C00.1. Native zoom is outside this task's
  scope; its current external-manual-gate status is recorded in the final
  closure review below and is not changed by C00.1.
- Next task: `V3-C01.1`.

## V3 final closure review — 2026-09-11

- Project status: `IMPLEMENTATION COMPLETE` / `VALIDATION COMPLETE EXCEPT ONE
  EXTERNAL MANUAL-VERIFICATION GATE`.
- Completed implementation tasks, in the required order: `V3-C00.1`,
  `V3-C01.1`, `V3-C02.1`, `V3-C04.1`, `V3-C03.1`, `V3-C06.1`, `V3-C07.1`,
  `V3-C08.1`, `V3-C05.1a`, `V3-C05.1b`, `V3-C05.2`, and `V3-C09.1`.
  `V3-C08.2` was not executed, per the objective file.
- Implementation receipts: exact chunk identity and 404 behavior are covered
  by the local harness; composite-field focus is opt-in and forced-colors
  safe; retrieval inspection serializes the full RRF candidate union with
  truthful stage scores, ranks, and counts; the shared reader preserves
  immutable citation identity; financial-table presentation is strict and
  arithmetic-free; Search, Documents, and Retrieval Lab use the same indexed
  reader; Retrieval Lab preserves submitted configuration and exact JSON/CSV
  exports; evidence collections use single-write, lease-checked persistence
  with no eviction and snapshot-first reads; and the original viewer is
  bounded, normalized, revision-bound, source-identity-safe, and conservative
  about exact/ambiguous/unavailable correspondence.
- Backend validation: `.venv\Scripts\python.exe -m pytest -q` passed `752`
  tests with `136` existing parser/deprecation warnings. Compile validation
  passed. The real local FastAPI service was started with one worker;
  `/health/live`, `/health/ready`, `/system/info`, documents, chunks, chunk
  detail, original manifest/content/location, and provider-free retrieval
  inspection all returned the expected contract. Live-backend Playwright
  feasibility passed in Chromium and Firefox (`2 passed`, `4 intentional
  synthetic-test skips`), with no generation request issued.
- Frontend validation: `bun run lint` passed; `bun run test` passed `42` test
  files / `211` tests; `bun run build` passed with `1986` modules transformed.
  The hermetic browser matrix covered `146` scenarios across Chromium and
  Firefox, including accessibility, layout, source identity, persistence,
  streaming/cancellation, Library/Search/Documents, reader, Retrieval Lab,
  exports, and measured performance. The benchmark cases affected by host
  worker contention were re-run deterministically with one worker and passed;
  the bookmark case passed three consecutive Firefox repetitions, and the
  isolated performance set passed `6/6` with p95 budgets green. HTTP/SSE
  integration passed `14/14`; the identity/readiness local harness passed
  `6/6`; and `git diff --check` passed.
- Final running services: FastAPI is available at `http://127.0.0.1:8000`
  (one worker, pipeline ready, 50 searchable companies, 10053 indexed
  chunks), and the Vite frontend is available at `http://localhost:3000/`.
  These task-owned sessions were intentionally left running for the user.
- Closure review conclusion: no code, layout, accessibility, backend,
  integration, persistence, source-identity, streaming, cancellation, or
  performance defect is hidden behind the remaining blocker. No production
  code remains unfinished.

- `[!]` Sole remaining item — native browser-zoom verification. Reason: the
  required browser-chrome zoom values (`100%`, `125%`, `150%`, `200%`) cannot
  be established from the connected Codex in-app browser. Attempted method:
  Playwright CSS-viewport equivalents, connected in-app browser inspection,
  and a scoped temporary-profile headed-Chrome/CDP probe. The in-app browser
  exposes no native browser-chrome zoom control/value, and environment policy
  rejected launching the native Chrome probe. This is an external
  environment/policy limitation, not an implementation defect.
- Manual verification for a human: in a visible Chrome or Edge window, run
  `cd frontend`, `bun run build`, then
  `bunx vite preview --host 127.0.0.1 --port 4173 --strictPort`; open
  `http://127.0.0.1:4173/`. Use the browser menu to set exactly `100%`,
  `125%`, `150%`, and `200%`, one value at a time. At each value inspect the
  overview, conversation/composer, evidence inspector/source reader,
  Documents, Search, Retrieval Lab, and Library; verify no horizontal
  overflow, clipping, overlap, hidden control, lost keyboard focus, or
  inaccessible header/navigation/composer action. Record the browser-reported
  zoom and the DevTools `window.innerWidth × window.innerHeight`, and attach
  screenshots/notes for all four values. Return the browser to `100%` when
  finished.
- The original native-zoom validation requirement is preserved. No
  production-code workaround is warranted: CSS zoom, browser-specific code,
  or a simulated test would weaken the requirement instead of verifying it.

## V4-D00.1 — reconcile execution checkpoint — 2026-09-11

- Status: `[x] complete`.
- The authoritative V4 objective and referenced final plan were read before
  execution. The frozen task order remains
  `V4-D00.1 → V4-D01.1 → V4-D02.1 → V4-D03.1 → V4-D04.1 → V4-D05.1 →
  V4-D05.2 → V4-D06.1 → V4-D07.1 → V4-D08.1 → V4-D09.1 → V4-D10.1 →
  V4-D11.1 → V4-D12.1 → V4-D13.1`.
- Current implementation truth remains the dirty worktree recorded above:
  26 tracked files modified, 14 untracked entries, and the same 1,356-line
  insertion / 112-line deletion diff statistic. No unrelated change was
  reverted or absorbed.
- Existing V2/V3 closure receipts are historical evidence only. V4 starts
  from the plan's verified contradiction: the Evidence Inspector overlap was
  reproduced at `1366×768` without native browser zoom, so it is an
  implementation defect owned by D01.1, not a zoom limitation.
- The previously audited service ownership was rechecked. No listener was
  present on ports `3000`, `4173`, or `8000`; no process was reused or stopped.
- No production code, corpus, index, provider configuration, or user data was
  changed by D00.1.
- Validation: checkpoint/document reconciliation only; no new test was needed.
- Remaining issue: none for D00.1. Native browser zoom is optional post-V4 QA
  under the objective correction and is not a V4 implementation blocker.
- Next task: `V4-D01.1`.

## V4-D01.1 — reader layout and selection-session checkpoint — 2026-09-11

- Status: `[x] complete`.
- Fixed the demonstrated `1366×768` Evidence Inspector failure without
  changing retrieval, corpus, index, provider, or persistence contracts.
  The inspector now owns an opaque bounded grid shell; the source list owns
  its scroll region, the reader owns its scroll region, and the excerpt body
  no longer creates a competing nested vertical scrollbar.
- Added `frontend/src/hooks/useReaderSession.ts` and its focused tests. The
  app-mounted session controller increments a generation, aborts the prior
  selection, preserves exact document/source identity, and rejects stale
  detail, nearby, manifest, location, and find responses. Invalid source
  indexes no longer fall back silently to the first source.
- Updated `App.tsx`, `ContextPanel.tsx`, `OriginalDocumentReader.tsx`, and
  the V4 layout rules in `frontend/src/styles/components.css`; added
  `frontend/e2e/document-workspace.spec.ts` for desktop geometry, bounded
  short-tablet drawer behavior, and the existing Open SEC identity contract.
- Frontend validation: `bun run lint` passed; focused Vitest passed `13/13`
  across the session, reader, and evidence-rail suites; production build
  passed with `1987` modules transformed; Playwright passed `4/4` in
  Chromium and Firefox. The first geometry assertion was corrected because
  a scrollable child is expected to make the shell's `scrollHeight` exceed
  its client height; the final assertion verifies shell `overflow:hidden`
  plus non-overlapping region boundaries and explicit child scroll owners.
- Backend validation: original-location/viewer/content-presentation tests
  passed `13/13` (`15` existing BeautifulSoup deprecation warnings). Runtime
  checks at `1366×768`, `768×480`, and `390×844` showed separate source and
  reader regions, no overlap, no horizontal overflow, and a bounded drawer.
- Accessibility evidence: existing semantic dialog/close, source-button,
  Open SEC link, and keyboard/focus contracts remain green; no new axe or
  keyboard defect was introduced. Performance evidence: selection requests
  are abortable and generation-bound; the full twenty-cycle stress gate is
  retained for the final V4 matrix rather than being relabeled as complete
  from a single manual pass.
- No known D01 implementation defect remains. Next task:
  `V4-D02.1`.

## V4-D02.1 — saved answer versions and field-safe mutations — 2026-09-11

- Status: `[x] complete`.
- Renamed the user action to `Save answer version`. `ChatMessage` now sends
  the displayed `{ messageId, variantId }` identity rather than an implicit
  original-message callback. The hook resolves that identity against the
  current conversation, snapshots the displayed text/sources/request
  provenance, awaits persistence, and exposes `saving`, `saved`,
  `already_saved`, `failed`, and `volatile` outcomes with live recovery
  actions. Successful and already-saved states offer `View in Library`;
  volatile/failed states never claim durable saving and offer retry.
- Added repository `mutateConversationRecord`, which performs latest-record
  field mutations inside the existing serialized writer queue. Autosave now
  preserves newer tags, notes, and variants; bookmarks, notes, renames, and
  Library metadata no longer enqueue stale whole-record replacements.
  Existing storage engine, schema, writer authority, tombstones, mirrors,
  quotas, and deletion semantics remain unchanged.
- Version identity excludes timestamps and includes the origin message,
  answer text, ordered sources, request provenance, answer language, and
  answer status. Stable object-key canonicalization prevents equivalent
  snapshots from proliferating. Saving a selected existing version is
  explicitly `already_saved`; no new answer is generated and the origin
  message is never mutated.
- Changed files: `frontend/src/App.tsx`,
  `frontend/src/components/ChatMessage.tsx`,
  `frontend/src/hooks/useConversationLibrary.ts`,
  `frontend/src/lib/conversationStore.ts`, `frontend/src/types.ts`, and
  `frontend/src/styles/components.css`. Added focused repository/hook tests
  and `frontend/e2e/saved-answer-version.spec.ts`.
- Validation: lint/typecheck passed; full Vitest passed with one worker,
  `43` files / `215` tests; the default parallel run exposed one known
  host-shared-storage timing failure in an existing App cancellation test,
  which passed in isolation and in the deterministic one-worker rerun;
  this is test-environment contention, not a product failure. Production
  build passed with `1987` modules transformed. Hermetic Playwright passed
  `6/6` across Chromium and Firefox for D01 geometry plus D02 save →
  duplicate-save deduplication → Library → exact Version 1 reopen.
- Backend: N/A by contract; existing backend remained unchanged and the
  task-owned FastAPI service stayed ready at `127.0.0.1:8000`. Security and
  persistence checks confirmed writer authority/tombstones remain enforced;
  volatile/read-only and quota behaviors retain their existing repository
  coverage. No known D02 implementation defect remains.
- Next task: `V4-D03.1`.

## V4-D03.1 — canonical document/source identity and local reader contract — 2026-09-11

- Status: `[x] complete`.
- Added the typed V4 reader contract in `src/api/document_reader_models.py`
  and the local-only resolver in `src/api/document_sources.py`. `GET
  /documents/{document_id}/reader` now returns a revision-bound
  `ReaderManifest` with verified filing identity, stable source identities,
  canonical SEC index URL when local metadata agrees, and explicit
  normalized-text/structured/PDF availability states. Existing `/original`
  routes and previously issued source IDs remain unchanged.
- Identity resolution is catalog → validated processed metadata → contained
  local source. It requires the exact `ticker:accession` document identity and
  an integer CIK in the matching processed metadata; it never infers a CIK
  prefix, accession, or filesystem path. Unknown/mismatched identities remain
  explicit `unverified`/`404` states while indexed retrieval remains intact.
  Companion sources receive stable local IDs but no fabricated canonical URL.
- Corrected the existing normalized-text cache accounting to subtract UTF-8
  encoded bytes on replacement/eviction. No corpus, chunk, embedding,
  retrieval, or remote acquisition path was changed. PDF feasibility remains
  explicitly unavailable for the current local corpus (50 primary HTML
  filings plus one HTML companion and no PDF); acquisition is deferred to
  D04.1.
- Frontend `types.ts` and `lib/api.ts` now expose the same typed reader
  manifest for the upcoming workspace; no UI behavior was widened in this
  identity-only task.
- Validation: focused backend/API/identity/cache tests passed `17/17` in the
  D03 selection and the expanded reader set passed `22` selected tests; the
  frontend lint and TypeScript checks passed; production Vite build passed
  with `1987` modules transformed. Runtime against the owned local backend
  returned AAPL `verified/available` with normalized text, IBM with primary
  plus companion sources, and `404` for an unknown identity. No external
  network was used.
- Security/performance: containment and metadata consistency checks remain
  enforced; the reader manifest is per-document and does not parse the
  corpus-wide source set. No known D03 implementation defect remains.
- Next task: `V4-D04.1` — secure bounded official/derived document acquisition.

## V4-D04.1 — bounded SEC reader experiment — 2026-09-11

- Status: historical experiment; retired by V4-R03.1.
- The earlier bounded transport was removed because a successful response did
  not admit a usable reader representation. The supported contract remains
  local-only and keeps the manifest, normalized/structured viewers, and
  canonical SEC links. No remote-body cache, queue, or ingestion side effect
  replaces the retired path.
- Historical transport receipts remain useful as provenance for the decision,
  but are not current capability or setup requirements. Next task in the
  original sequence: `V4-D05.1` — structured API and first complete reader
  slice.

## V4-D05.1 — structured API and first complete reader slice — 2026-09-11

- Status: `[x] complete`.
- Added bounded, application-owned structured blocks for headings, paragraphs,
  lists, tables, separators, and explicit unsupported-content notices. The
  parser removes executable/remote markup, preserves source text values and
  table order, computes a representation revision, and rejects excessive
  bytes, nodes, depth, code points, table cells, and response size.
- Added revision-bound outline/content/search/export endpoints and an LRU
  parsed-representation cache with serialized-byte accounting. The service
  revalidates source-set and document revisions before cache use, so stale
  requests cannot read an old representation. No persistence, ingestion,
  Qdrant, chunk text, or retrieval behavior changed.
- Replaced the normalized-dump reader path with `StructuredDocumentReader`:
  semantic React rendering, outline navigation, explicit find, source picker,
  text scale, wide mode, safe export, Open SEC, and truthful PDF-unavailable
  messaging. Structured content stays application-rendered; raw HTML is never
  inserted into the DOM.
- E2E uncovered and fixed two real lifecycle/layout defects before acceptance:
  shared reader-session changes caused repeated manifest requests, and the
  embedded rail used viewport rather than container width for reader columns.
  Stable session callbacks, memoized request parameters, and container-aware
  responsive CSS now keep one mounted content window and prevent horizontal
  content loss. Duplicate structured paragraphs are retained for later
  ambiguity detection.
- Validation: backend structured/parser/source/API selection passed `25/25`
  including parser limits, XSS-safe output, revision conflicts, semantic
  table correspondence fixtures, and the location route; frontend structured
  reader component test passed `1/1`; production Vite build passed with
  `1988` modules; hermetic Playwright passed the structured-reader flow on
  Chromium and Firefox (`2/2`) plus the existing D01 workspace checks.
- Runtime after backend restart: local AAPL and IBM reader manifests are
  identity-verified with normalized sources and structured representation
  available; IBM exposes its companion source. A guessed JPM identity returns
  `404`, so no unsupported runtime claim is made. PDF remains explicitly
  unavailable because the corpus contains no PDF.
- No known D05.1 implementation defect remains. Next task: `V4-D05.2` —
  verified evidence mapping and navigation.

## V4-D05.2 — verified evidence mapping and navigation — 2026-09-11

- Status: `[x] complete`.
- Added conservative structured correspondence from exact chunk ID and
  SHA-256 text hash through the complete declared source set and the
  revision-bound structured representation. Results are explicitly typed as
  `exact`, `ambiguous`, `not_found`, `unavailable`, or `stale`; numeric-only
  financial values never establish correspondence. Exact results carry the
  source/document/representation revisions and Unicode code-point ranges;
  unprovable corpus cases remain visibly unhighlighted.
- Added the additive `/chunks/{chunk_id}/reader-location` route and guarded
  reader navigation/highlighting. Amber evidence marks and outlined tables are
  distinct from literal-search results, source selection remains session-bound,
  and a late location response cannot steal a user's manual navigation.
- Validation: backend structured/location/source/API selection passed `25/25`;
  focused component coverage passed `1/1`; TypeScript passed; structured-reader
  Playwright passed Chromium and Firefox `2/2`. Runtime verified AAPL/IBM
  manifests after backend restart and exercised a real AAPL location request;
  the current corpus returned an explicit `not_found` for that chunk because
  the application-owned HTML blocks do not contain the full caption/header/
  unit/row correspondence. No false exact highlight was produced. No
  persistence, ingestion, Qdrant, retrieval, generation, or PDF behavior was
  changed.
- No known D05.2 implementation defect remains. Next task: `V4-D06.1` — full
  adaptive document workspace.

## V4-D06.1 — full adaptive document workspace — 2026-09-11

- Status: `[x] complete`.
- Added `frontend/src/components/DocumentWorkspace.tsx` as the shared
  workspace composition for the repaired inspector and structured reader.
  It keeps one reader-session owner while exposing explicit Document, Indexed
  excerpt, and Metadata views, preserves the citation snapshot as a separate
  view, and keeps source/document identity visible.
- Added container-aware layout states for three-column, two-column, and
  single-surface reading. The narrow mode switches architecture instead of
  crushing the document; the embedded reader has one vertical scroll owner,
  tables retain labelled horizontal scrolling, and all tabs/actions remain
  keyboard reachable. The existing inspector remains a compatibility wrapper.
- Validation: TypeScript passed; focused reader/rail/workspace component tests
  passed `11/11`; Playwright passed workspace geometry, bounded short-tablet
  drawer, and structured-reader flows on Chromium and Firefox `6/6`. The
  Playwright webserver production build passed with `1988` modules transformed.
  No reader API, persistence, retrieval, source identity, or PDF contract was
  changed.
- No known D06.1 implementation defect remains. Next task: `V4-D07.1` — saved
  evidence, notes, Library, and import safety.

## V4-D07.1 — saved evidence, notes, Library, and import safety — 2026-09-11

- Status: `[x] complete`.
- Saved evidence remains an independent immutable excerpt snapshot with chunk,
  ticker, section, filing date, conversation/message lineage, and now a
  bounded plain-text evidence note (maximum 10,000 characters). Notes are
  field-scoped mutations; deleting or changing a conversation cannot rewrite
  the saved excerpt.
- Library backup import now validates and remaps collection/item IDs before
  mutation, preflights writer authority and collection capacity before
  conversation writes, preserves malformed bytes, and reports evidence
  collection failures separately when a later storage write rejects. Existing
  writer locks, tombstones, quotas, storage fallback, and export recovery are
  unchanged.
- Validation: TypeScript passed; focused evidence/library/workspace tests
  passed `13/13`, including note persistence, lineage round-trip, malformed
  storage preservation, bounded import preflight, and saved-evidence reopen.
  No backend/API or corpus changes were made.
- No known D07.1 implementation defect remains. Next task: `V4-D08.1` —
  Documents/Search research integration.

## V4-D08.1 — Documents/Search research integration — 2026-09-11

- Status: `[x] complete`.
- Documents and Search now open the shared full document workspace with a
  stable selected filing identity. The integration preserves the selected
  document, source, chunk, citation, and reader revisions across the route
  boundary; it does not create a second reader state owner or expose local
  filesystem paths.
- Validation: focused Documents/Search/workspace coverage passed `11/11` and
  frontend lint/typecheck passed. Existing reader, source identity, and
  indexed-excerpt contracts remained green. No backend, retrieval, ingestion,
  persistence, or PDF behavior changed.
- No known D08.1 implementation defect remains. Next task: `V4-D09.1` —
  related research and answer workflow.

## V4-D09.1 — related research and answer workflow — 2026-09-11

- Status: `[x] complete`.
- Related research suggestions are derived only from available indexed
  sections and preserve the active analyst scope. Selecting a suggestion
  places a non-empty draft in the composer without auto-submitting a new
  request, so the user retains control of query, company, section, and send.
- Validation: focused related-research/Chat coverage passed `14/14` and
  frontend lint/typecheck passed. No unsupported Web, Deep Research, source,
  provider, streaming, cancellation, or persistence capability was added.
- No known D09.1 implementation defect remains. Next task: `V4-D10.1` —
  Retrieval Lab analyst workflow.

## V4-D10.1 — Retrieval Lab analyst workflow — 2026-09-11

- Status: `[x] complete`.
- Retrieval Lab now separates the normal analyst path from advanced
  diagnostics, explains preset/Top K/candidate-pool semantics, shows stage
  scores and ranks, preserves submitted configuration, and provides exact
  JSON/CSV export plus source actions. Comparison diagnostics remain truthful
  and provider-free; the shared immutable source identity is preserved.
- Validation: focused Retrieval Lab and save-evidence coverage passed `10/10`
  and frontend lint/typecheck passed. The final browser matrix also covered
  retrieval controls, exports, source actions, and persistence. No retrieval
  ranking or backend contract was redesigned.
- No known D10.1 implementation defect remains. Next task: `V4-D11.1` —
  actionable system and provenance surface.

## V4-D11.1 — actionable system and provenance surface — 2026-09-11

- Status: `[x] complete`.
- System and provenance now expose safe actionable refresh, reader
  availability, provenance, and next-action states. Refresh is asynchronous,
  clipboard actions are guarded, and the UI does not surface secrets or local
  filesystem paths.
- Validation: focused SystemInfoPanel coverage passed `2/2` and frontend
  lint/typecheck passed. Runtime `/system/info` returned the expected
  provider-free corpus/model contract. No backend security or provenance
  contract was weakened.
- No known D11.1 implementation defect remains. Next task: `V4-D12.1` —
  evaluation workflow guidance.

## V4-D12.1 — evaluation workflow guidance — 2026-09-11

- Status: `[x] complete`.
- Added `docs/EVALUATION_REVIEW_GUIDE.md` and made the Evaluation panel an
  actionable workflow: live/recorded source choice, status filtering, reload,
  clear empty-state guidance, and distinct OK/error/missing report states.
  Recorded mode remains provider-free and no fake report, metric, confidence,
  or provider result is synthesized.
- Validation: focused Evaluation coverage passed `2/2` and frontend
  lint/typecheck passed. The guide is linked from the public README. No
  evaluation data or benchmark semantics were changed.
- No known D12.1 implementation defect remains. Next task: `V4-D13.1` —
  final closure and performance verification.

## V4-D13.1 — final closure and performance verification — 2026-09-11

- Status: `[x] complete` for implementation and every
  non-environment-dependent validation gate.
- Final frontend receipts are green: `bun run lint`; full Vitest
  `47 files / 228 tests`; production Vite build with `1991` modules
  transformed; hermetic Playwright `152 passed, 2 skipped` across Chromium
  and Firefox with the two intentional real-backend-only skips. The final
  performance matrix stayed within the frozen budgets: Chromium warm composer
  p95 `17.6 ms`, warm view switch p95 `57.1 ms`; Firefox warm composer p95
  `44 ms`, warm view switch p95 `160 ms`; the remaining measured input/search,
  reader/source-switch, Library, and 200-message composer budgets were also
  green.
- Final backend/integration receipts are green: full pytest `771 passed` with
  `172` existing parser/deprecation warnings; SEC live smoke passed with
  AAPL CIK `320193`, latest 10-K accession
  `0000320193-25-000079`, and the expected canonical primary URL; local
  identity/readiness harness `6/6`; real-backend feasibility `2 passed` and
  `4` intentional synthetic skips. Runtime HTTP checks returned frontend
  `200`, live/ready/health `200/ok`, `50` searchable tickers, `50` catalog
  filings, AAPL `91` chunks, verified/available reader identity, structured
  representation available, PDF representation unavailable, `3` reader
  search matches, `22` retrieval candidates, and `5` selected results. The
  AAPL reader's empty outline is an explicit no-heading limitation; its
  bounded content response returned structured blocks, so no reader defect is
  hidden by that state.
- The official/derived PDF decision remains explicit: the local corpus has
  `50` primary HTML filings plus `1` HTML companion and currently no PDF.
  D04.1 safely supports bounded official SEC HTML acquisition only; no fake
  PDF, page count, viewer, confidence, or unsupported document capability is
  claimed. A future PDF source requires a separately verified official or
  derived artifact and a new contract decision.
- Closure review confirms there is no hidden code, layout, accessibility,
  backend, integration, persistence, source-identity, streaming,
  cancellation, or performance defect. All implementation tasks
  `V4-D00.1`, `V4-D01.1`, `V4-D02.1`, `V4-D03.1`, `V4-D04.1`, `V4-D05.1`,
  `V4-D05.2`, `V4-D06.1`, `V4-D07.1`, `V4-D08.1`, `V4-D09.1`, `V4-D10.1`,
  `V4-D11.1`, `V4-D12.1`, and `V4-D13.1` are complete. No production code
  remains unfinished.
- Final running services remain owned and healthy: frontend
  `http://127.0.0.1:3000/` and one-worker backend
  `http://127.0.0.1:8000`.

### Final status

`IMPLEMENTATION COMPLETE`

## V4-P00.1 — truth-contract fixture and baseline gate — 2026-09-12

- Status: `[x] complete`.
- Added `tests/fixtures/reader_table_source_layout.html`, a bounded AAPL-like
  source fixture with blank physical spacer cells, multi-column year spans,
  split currency/value cells, row spans, parenthetical values, and a long
  issuer label. The fixture is source evidence only; the local SEC corpus was
  not changed.
- Added focused backend assertions that freeze the fixture facts and record the
  current first-row-as-columns behavior as an expected baseline failure for the
  next table-contract task. No production behavior was changed in this task.
- Native command: `.\.venv\Scripts\python.exe -m pytest tests/test_structured_document.py`.
- Result: `6 passed` (12 existing BeautifulSoup deprecation warnings); expected
  baseline remains green because the failure is represented as a documented
  assertion, not an intentionally failing test.
- Runtime/browser: not applicable; no service started or stopped. Existing
  dirty files and process ownership were preserved.
- Rollback: remove only the new fixture/test section and this receipt.
- Next task: `V4-P01.1` — versioned table presentation contract.

`VALIDATION COMPLETE EXCEPT ONE EXTERNAL MANUAL-VERIFICATION GATE`

- `[!]` Sole remaining item: native browser-zoom verification. Reason: the
  required browser-chrome zoom values `100%`, `125%`, `150%`, and `200%` cannot
  be established from the connected Codex in-app browser. Attempted method:
  CSS-viewport Playwright coverage, connected in-app browser inspection, and a
  scoped temporary-profile headed-Chrome/CDP probe. The in-app browser exposes
  no native browser-chrome zoom control/value, and environment policy rejected
  launching the native Chrome probe. This is an external environment/policy
  limitation, not an implementation defect.
- Manual verification for a human: in a visible Chrome or Edge window, from
  the repository run `cd frontend`, `bun run build`, then
  `bunx vite preview --host 127.0.0.1 --port 4173 --strictPort`; open
  `http://127.0.0.1:4173/`. Set the browser menu zoom to exactly `100%`,
  `125%`, `150%`, and `200%`, one value at a time. At each value inspect
  Overview, Conversation/composer, Evidence Inspector/source reader,
  Documents, Search, Retrieval Lab, and Library. Verify no horizontal
  overflow, clipping, overlap, hidden control, lost keyboard focus, or
  inaccessible header/navigation/composer action. Record browser-reported
  zoom and DevTools `window.innerWidth × window.innerHeight`, and capture
  screenshots/notes for all four checkpoints. Restore `100%` afterward.
- The original native-zoom validation requirement is preserved and is not
  weakened or deleted. No production-code workaround is warranted: CSS zoom,
  browser-specific behavior, or a simulated zoom test would change the
  requirement instead of verifying it.

## Skill governance reconciliation — 2026-09-12

The frozen PASS-1 architecture was applied as project-local skill and reference
documentation only. `rag-ui-ux` remains the frontend/product authority and the
new RAG specialists have precise routing boundaries. No production application,
backend, corpus, index, deployment, or dependency files were changed.

The historical findings above are retained as dated evidence, but the
follow-on V4 remediation sequence below is the current implementation state.
The catalog/search actions now open a direct document workspace, the workspace
owns identity chrome, structured coverage is explicit and conservative, and
the unsupported remote acquisition surface is retired. The only remaining
validation item is the external native browser-zoom gate recorded above.

## V4 remediation and improvement closure — 2026-09-12

- `V4-R00.1` established the expected-failure baseline without changing
  production behavior.
- `V4-R01.1` made catalog/search navigation discriminated and direct, while
  preserving answer-scoped evidence inspection and return focus.
- `V4-R02.1` added representation-scoped `coverage_status` and reasons,
  conservative structured coverage detection, and normalized-search fallback
  copy for incomplete views.
- `V4-R03.1` retired the non-admitting remote reader resolver and its client,
  DTOs, settings, tests, and setup documentation. The supported reader remains
  bounded and local-only.
- `V4-R04.1` removed duplicate embedded identity chrome while retaining the
  toolbar, outline, content canvas, accessibility labels, and normalized
  fallback within one workspace shell.
- `V4-R05.1` closure receipts: full frontend Vitest `47 files / 231 tests`,
  frontend TypeScript lint, production Vite build (`1,992` modules), full
  backend pytest (`766 passed`, `178` existing warnings), and isolated local
  Playwright (`6 passed` across Chromium and Firefox). No corpus, index,
  retrieval, embedding, Qdrant, acquisition, persistence, or evaluation data
  was regenerated or changed by this sequence; existing user-owned services
  and dirty files were preserved.

## V4-P01.1 — versioned table presentation contract — 2026-09-12

- Status: `[x] complete`.
- `StructuredBlock` now carries an additive, versioned table contract with
  explicit `semantic`, `source_layout`, and `unsupported` modes, adapter and
  reason metadata, verified header rows, bounded spans, deterministic cell
  identity, source row/column lineage, and raw preservation. Ambiguous SEC
  layout is not promoted to a semantic financial table.
- Files: `src/api/structured_document.py`, `frontend/src/types.ts`, and the
  focused structured-document tests/fixture already recorded by `V4-P00.1`.
  No corpus, index, embedding, Qdrant, retrieval, or API acquisition path was
  changed.
- Validation: backend full pytest `770 passed` with `182` existing warnings;
  frontend full Vitest `48 files / 235 tests`, TypeScript lint, and production
  build all passed. The contract is covered by the source-layout fixture and
  semantic/raw/unsupported assertions.
- Runtime/browser: no new service was required for the contract gate. Existing
  dirty files and process ownership were preserved. Rollback is limited to
  this contract slice and its tests. Next task: `V4-P01.2`.

## V4-P01.2 — reader table renderer and fallback — 2026-09-12

- Status: `[x] complete`.
- The reader discloses table mode, renders verified headers only, keeps source
  layout as source layout (without a fabricated `<thead>`), preserves raw and
  unsupported fallbacks, adds bounded local table scrolling, numeric alignment,
  focusable reading regions, and normalized-text recovery for incomplete views.
  CSS does not attempt to repair parser semantics.
- Files: `frontend/src/components/StructuredDocumentReader.tsx`,
  `frontend/src/styles/document-reader.css`, `frontend/src/types.ts`, and
  focused reader tests. No backend retrieval or source data was regenerated.
- Validation: structured-reader browser coverage passed in Chromium and
  Firefox; the final serial E2E run passed `152/152` executed tests, and the
  local synthetic reader suite passed `6/6`. Wide tables retained local
  overflow with no global page overflow in the checked desktop and narrow
  viewport paths. Rollback is the reader renderer/style/test slice only.
  Next task: `V4-P02.1`.

## V4-P02.1 — unified company presentation — 2026-09-12

- Status: `[x] complete`.
- `displayMetadata` is a versioned presentation formatter with explicit
  unknown-ticker fallback. Documents, Search, Research, Retrieval Lab, reader,
  source, and workspace identity surfaces use the same full company label while
  retaining an accessible ticker. This is presentation metadata, not a claim
  of canonical legal-entity provenance.
- Files: `frontend/src/lib/displayMetadata.ts`, its tests, and the affected
  workspace/source components. No `/supported-tickers` or filing identity DTO
  was broadened.
- Validation: display metadata tests are included in the `48 files / 235
  tests` Vitest receipt; lint/build and the full Chromium/Firefox E2E matrix
  passed. Documents/Search exact-label handoffs were verified. Rollback is the
  formatter and presentation consumers only. Next task: `V4-P03.1`.

## V4-P03.1 — typed answer-action state contract — 2026-09-12

- Status: `[x] complete`.
- Bookmark, answer-version save, Helpful/Not helpful/Other, and note actions
  use keyed, stale-attempt-safe states (`idle`, `pending`, `persisted`,
  `already_exists`, `volatile`, `failed`, `retryable`, `cancelled`). `Other`
  requires text and supports submit/cancel; local-only outcomes are named
  honestly and never presented as server success. Context changes suppress late
  results and preserve unrelated conversation data.
- Files: `frontend/src/hooks/useAnswerActions.ts`,
  `frontend/src/hooks/useConversationLibrary.ts`, `frontend/src/lib/conversationStore.ts`,
  `frontend/src/lib/conversationExport.ts`, `frontend/src/types.ts`,
  `frontend/src/components/ChatMessage.tsx`, and focused tests. There are no
  backend mutation endpoints to silently imply.
- Validation: full Vitest `235/235`; saved-answer, bookmark, feedback, storage
  failure, context-switch, and multi-tab journeys passed in the serial
  Chromium/Firefox E2E closure. Rollback is the action hook/store/UI/test
  slice. Next task: `V4-P03.2`.

## V4-P03.2 — local evidence snapshot provenance — 2026-09-12

- Status: `[x] complete`.
- Evidence collections use schema `v2` with explicit application/schema
  version, capture time, document/source/accession/date, representation,
  coverage, location, revision, URL, and hash fields. Read-only migration from
  v1 preserves malformed bytes; stale or local-only snapshots are labelled as
  such and cannot masquerade as current corpus truth.
- Files: `frontend/src/lib/evidenceCollections.ts`, tests,
  `frontend/src/components/EvidenceCollectionsPanel.tsx`, and provenance
  plumbing in App/Context/Sources panels. Persistence remains same-origin local
  storage; no sync or backend mutation was introduced.
- Validation: evidence collection tests, save-evidence journeys, full Vitest,
  lint/build, and the full serial browser matrix passed. Rollback is limited to
  the v2 schema/migration and its consumers. Next task: `V4-P04.1`.

## V4-P04.1 — Evidence Review layout controller — 2026-09-12

- Status: `[x] complete`.
- Evidence is inline only when remaining width is safe; otherwise it opens as a
  bounded, short-desktop-aware drawer/dialog. Explicit citation/source actions
  open and focus the inspector, while generic composition remains answer-first;
  close returns focus and identity. The controller uses width and height
  observations with thresholds `1120/760/640` and preserves one primary scroll
  owner.
- Files: `frontend/src/App.tsx`, `frontend/src/components/ContextPanel.tsx`,
  `frontend/src/components/SourcesPanel.tsx`, and related tests/styles. No
  retrieval or evidence identity semantics changed.
- Validation: the focused evidence-inspector suite passed `2/2` in Chromium and
  Firefox; the final serial E2E run passed all layout/modal/focus journeys. No
  global horizontal overflow was observed. Rollback is the controller and
  layout slice. Next task: `V4-P04.2`.

## V4-P04.2 — typography and density tokens — 2026-09-12

- Status: `[x] complete`.
- Added semantic body/meta/diagnostic/action/readable-line tokens and minimum
  readable floors. Diagnostics stay visually subordinate without shrinking
  analyst text; table cells retain practical minimums and tabular numeric
  alignment. EN/VI and light/dark token paths remain shared.
- Files: `frontend/src/styles/tokens.css`, `components.css`,
  `document-reader.css`, and affected component tests. No native browser zoom
  behavior was simulated or changed.
- Validation: full Vitest, lint/build, accessibility/contrast checks, and the
  Chromium/Firefox visual/reflow matrix passed. The historical native Chrome
  zoom gate remains external because the connected browser cannot report
  chrome-level zoom. Rollback is token/component styling only. Next task:
  `V4-P05.1`.

## V4-P05.1 — document workspace composition — 2026-09-12

- Status: `[x] complete`.
- The direct document workspace owns identity, back/tabs, and reading
  composition. The embedded reader contributes tools, availability, outline,
  and content only; the normalized fallback stays in the same shell. Wide,
  two-column, and single-surface layouts are explicit, with bounded drawers at
  short desktop/tablet widths.
- Files: `frontend/src/components/DocumentWorkspace.tsx`,
  `StructuredDocumentReader.tsx`, `OriginalDocumentReader.tsx`, reader/workspace
  styles, and tests. No source identity or reader async owner was duplicated.
- Validation: document-workspace, structured-reader, and full serial E2E suites
  passed in Chromium and Firefox, including 1024/1280/1440 desktop and narrow
  reflow paths. Rollback is the workspace composition slice. Next task:
  `V4-P05.2`.

## V4-P05.2 — Search/Documents/Research handoffs — 2026-09-12

- Status: `[x] complete`.
- Catalog/search opens a direct indexed document workspace; answer citations
  retain answer-scoped evidence semantics. Handoffs preserve issuer/ticker,
  accession/date, section, chunk/source identity, representation, coverage,
  and return target, with honest unavailable/reselect behavior for stale or
  missing state. Direct document surfaces avoid “retrieved sources” wording.
- Files: `DocumentExplorerPanel.tsx`, `SearchWorkspace.tsx`, `DocumentWorkspace.tsx`,
  App/types/API display plumbing, and E2E regressions. No nearby-source
  substitution or remote acquisition was introduced.
- Validation: Documents/Search exact-chunk handoff, deep-link, return-focus,
  fallback, and full browser closure tests passed in both engines. Rollback is
  navigation state and test coverage only. Next task: `V4-P06.1`.

## V4-P06.1 — Retrieval Lab analyst workflow — 2026-09-12

- Status: `[x] complete`.
- Analyst mode exposes full company/filing/section/date identity, submitted
  scope/configuration, honest result order, source actions, and Save evidence.
  Advanced mode contains stage scores, candidate counts, and export diagnostics;
  scores are not confidence claims and no ranking algorithm was changed.
- Files: `frontend/src/components/RetrievalLabPanel.tsx`, styles, types, and
  focused/e2e tests. Retrieval, BM25/dense/fusion/reranker, presets, and API
  contracts remain frozen.
- Validation: Retrieval Lab regression, export/source/save-evidence journeys,
  full Vitest/lint/build, and the full Chromium/Firefox serial matrix passed.
  Rollback is the panel disclosure/presentation slice. `V4-P07.1` Library
  continuity is intentionally deferred; next task: `V4-P08.1`.

## V4-P08.1 — measured reader performance gate — 2026-09-12

- Status: `[x] complete` for the measured, repository-verifiable gate.
- A one-worker local backend was started only for this gate with explicit CORS
  for `http://localhost:4175`; readiness and system contracts returned `200`.
  The real-browser harness measured AAPL, GOOGL, and AMZN cold/warm open paths
  in Chromium and Firefox, from manifest/outline/content request timings to the
  first readable structured block. It also recorded table/row/cell counts,
  local table overflow, viewport/global overflow, DOM count, and a bounded
  forced-layout proxy. Memory measurement was unavailable in this provider.
- Observed cold/warm first-readable milliseconds were: Chromium AAPL
  `1311.88/964.66`, GOOGL `2546.34/1263.31`, AMZN `2297.87/1280.68`;
  Firefox AAPL `1065.67/1032.08`, GOOGL `1413.35/1897.96`, AMZN
  `1447.46/1382.40`. AAPL/GOOGL/AMZN max local table scroll widths were about
  `3144/4523/4043 px` against a `670 px` client region; no page overflow or
  duplicate open transition was observed in the measured paths. These are
  characterization samples, not universal performance promises.
- Test-only harness changes are confined to
  `frontend/e2e/workspace-performance.spec.ts`; the stale local source-card
  locator was corrected in `workspace.local.spec.ts`. No production UI/API
  code changed during resumption. Rollback is the harness/test receipt only.
  Next task: `V4-P09.1`.

## V4-P09.1 — integrated regression closure — 2026-09-12

- Status: `[x] complete` for every repository- and harness-verifiable gate;
  the external native browser-chrome zoom check remains explicitly manual.
- Closure commands and results: frontend full Vitest `48 files / 235 tests`;
  `bun run lint` passed; production Vite build transformed `1,993` modules;
  serial default Playwright passed `152` tests with `4` intentional skips;
  local synthetic Playwright passed `6/6` across Chromium and Firefox. The
  skipped tests are the two real-backend readiness/P08 cases in each engine,
  not failures. Backend full pytest was already green at `770 passed` with
  `182` existing warnings after the P01–P06 source-contract work.
- Browser acceptance covered table/source-layout fallback, direct
  Documents/Search reader handoffs, full company labels, evidence inline vs
  drawer behavior, action-state persistence/failure/retry, Retrieval Lab
  analyst/advanced disclosure, EN/VI and light/dark reflow, keyboard/focus,
  reduced motion, contrast, local overflow, and 100%-CSS-viewport desktop and
  narrow paths. The P08 real-browser sample covered AAPL, GOOGL, and AMZN in
  Chromium and Firefox with no global page overflow or duplicate open
  transition observed.
- Preservation gates: retrieval algorithms and presets, embeddings/models,
  prompts, chunking/Qdrant/index data, corpus/acquisition, streaming/cancel,
  reader async ownership, normalized fallback, source identity, user-data
  import/export, multi-tab behavior, EN/VI, themes, and the closed native-zoom
  gate remain unchanged in intent. No corpus/index/evaluation artifact was
  regenerated. `git diff --check` returned no whitespace errors (only normal
  LF→CRLF warnings), and the dirty worktree was retained without reset.
- Runtime ownership: the audit-owned one-worker backend (parent `19160`,
  worker/listener `2488`, `127.0.0.1:8000`) returned health/ready `200`,
  `50` searchable tickers, `10,053` indexed chunks, and the expected
  provider-free system contract. It was stopped deliberately after closure;
  no project listener remains on `3000`, `4173`, `5173`, or `8000`. No
  unrelated process was killed or restarted.
- Remaining manual gate: a human must verify native Chrome/Edge menu zoom at
  exactly `100%`, `125%`, `150%`, and `200%` on Overview, Conversation,
  Evidence Inspector/source reader, Documents, Search, Retrieval Lab, and
  Library. This cannot be established by the connected browser and is not
  substituted with CSS viewport scaling. Rollback is the entire P-slice via
  its implementation checkpoints; no production/source changes were made
  during this resumption beyond already-present P-task work.

### P-sequence final status

`V4-P00.1 → P01.1 → P01.2 → P02.1 → P03.1 → P03.2 → P04.1 → P04.2 →
P05.1 → P05.2 → P06.1 → P08.1 → P09.1 COMPLETE`; `V4-P07.1` is explicitly
deferred and was not implemented.

## V4-P07.1 — Library continuity — 2026-09-12

### P07-A — reconciliation and frozen contracts

- Status: `[x] complete`.
- Reconciled the existing Library view, `useConversationLibrary`, conversation
  schema v4/IndexedDB-localStorage ownership, answer variants, bookmarks,
  notes, import/export, Web Locks/BroadcastChannel, EvidenceSnapshot v2, and
  the shared company formatter. The Library remains a derived organization and
  continuation surface; no second persistence index was introduced.
- Existing P/V4 contracts were frozen: direct document/search workspaces,
  reader coverage/representation semantics, answer actions, evidence
  provenance, streaming/cancellation, themes, EN/VI, and local-only reader
  behavior were not reopened.

### P07-B — Library information architecture

- Status: `[x] complete`.
- `ConversationLibrary` now presents bounded `Recent Research`, the complete
  conversation history, immutable `Saved Answer Versions`, and `Evidence
  Collections` sections over the current stores. Recent work is capped at
  eight records and sorted by stored activity; the canonical history list
  remains unbounded by this continuity view, while saved variants are capped
  at 100 derived rows and retain exact origin message/variant IDs. No duplicate
  artifact records are created.
- Company and scope labels use `formatCompanyLabel` and stored request/source
  metadata only. Missing identity is omitted rather than guessed. Recent cards
  expose an explicit answer state only when the message/variant metadata stores
  one; otherwise no state is invented.

### P07-C — exact continuation and snapshot/current semantics

- Status: `[x] complete`.
- `Open saved answer` selects the exact conversation/message/variant and never
  falls back to the latest answer. `Continue (fill draft)` restores stored
  scope and draft/question without submitting a query. `Open evidence` keeps
  the captured text as a historical snapshot; `Open current source` performs a
  fresh exact chunk/document/hash check through the existing API and refuses
  fuzzy or nearby substitution, returning explicit current/stale/missing/
  unavailable states.
- Reader identity facts already present in `stored_snapshot` are copied into
  the existing EvidenceSnapshot v2 fields; missing representation metadata is
  left absent rather than inferred. No backend route, reader owner, or corpus
  representation was added.

### P07-D — filters, storage/error states, disclosure, and responsive UX

- Status: `[x] complete`.
- Local search and bookmark filtering cover the derived Library sections;
  empty, filtered-empty, read-only, volatile, malformed-storage, and current
  source limitation states are explicit in EN/VI. Evidence collection IDs,
  revisions, hashes, locations, lineage, capture time, and other implementation
  metadata are behind a `Provenance details` disclosure. A storage warning
  cannot be rendered as a durable “Saved on this device” state. Destructive
  conversation deletion and backup import preview/confirmation remain under
  the existing controls.
- Semantic headings, labelled controls, live status/error regions, native
  disclosure elements, and the existing keyboard/focus contracts are retained.
  CSS viewport checks at 390, 768, 1024, 1280, 1366, 1440, 1920, plus a short
  1366×520 desktop, showed no horizontal page overflow; text was not reduced to
  solve density.

### P07-E — integration/regression closure

- Status: `[x] complete`.
- Focused Library/evidence tests passed `24/24`; the full frontend Vitest suite
  passed `48 files / 245 tests`; `bun run lint` passed; and the production Vite
  build passed with `1,993` transformed modules using
  `VITE_API_BASE_URL=http://127.0.0.1:8000`.
- The saved-answer journey was verified in Chromium and Firefox against the
  built preview (`2 passed`): Research → Save answer version → Library → exact
  variant reopen. The complete default preview matrix then passed `152` tests
  with `4` intentional skips across Chromium and Firefox; the skips are the
  two real-backend readiness/P08 cases per engine. This rerun also verified
  bookmarked-answer focus, pending-update retention, malformed tombstones,
  and 100-record Library search (`p95` 54.93 ms Chromium / 106.88 ms Firefox,
  below the 200 ms budget). Connected-browser AX inspection verified the
  Library section headings, local-only/read-only disclosures, bounded empty
  states, and the healthy backend badge. Backend health remained `200` with
  `pipeline_ready` true, `50` searchable companies, and `10,053` indexed
  chunks; the existing backend contract suite remains the prior `770 passed`
  receipt because no backend file changed for P07.1.
- Current services were preserved, not restarted or killed: backend parent
  `19104`/listener `16700` on `127.0.0.1:8000`, frontend parent `19292`/listener
  `18944` on `127.0.0.1:4173`. The dirty worktree and ignored `data/` remain
  untouched outside the requested Library slice.
- Remaining limitation: native browser-chrome zoom at exact 100/125/150/200%
  is the previously closed manual gate and cannot be established by the
  connected browser; CSS viewport checks were not substituted for it.

Exact next step: none for V4-P07.1; proceed only with a separately scoped
product goal.

## V5-00 Research workbench baseline — 2026-09-13

- TASK ID: `V5-00`.
- STATUS: `[x] COMPLETE`.
- INTENT: freeze the current SEC research/evidence composition, record the
  V5 workbench contract, and establish a deterministic checkpoint before any
  runtime migration.
- FILES CHANGED: `frontend/e2e/v5-00-baseline.spec.ts`,
  `docs/frontend/V5_WORKBENCH_CONTRACT.md`,
  `docs/implementation-progress.md`, and `PROJECT_STATE.md`.
- FILES CREATED: the test-only baseline capture and
  `docs/frontend/V5_WORKBENCH_CONTRACT.md`; no files removed.
- RUNTIME BOUNDARY: no production UI runtime, backend route/DTO, retrieval,
  generation, model, prompt, corpus, index, Qdrant, persistence schema, or
  PDF behavior changed. The baseline spec only captures existing behavior,
  geometry, and screenshots.
- ARCHITECTURE EFFECT: none. The current App → primary research conversation
  → EvidenceWorkspaceRail/ContextPanel composition remains unchanged. The
  contract records the intended future `Research`, `Sources`, and `Document`
  pane boundaries without introducing them.
- STATE EFFECT: none. Existing `useResearchDraft`, `useResearchSession`,
  `useEvidenceSelection`, `useReaderSession`, Library stores, cancellation,
  stale-response, and read-only/volatile state owners remain authoritative.
- ASYNC EFFECT: none. No new request owner, fetch, stream, cancellation path,
  or duplicate source/document load was added.
- API EFFECT: none. Backend DTOs, SSE events, local indexed-reader behavior,
  and direct catalog/search/document routes are unchanged.
- PERSISTENCE EFFECT: none. IndexedDB/localStorage fallback, Web Locks,
  BroadcastChannel, Library continuity, and existing evidence snapshot data
  remain unchanged. P07 Library continuity is preserved as complete.
- PROVENANCE EFFECT: none. The contract freezes the existing exact
  company/source/document/revision/hash/chunk/location/representation
  identity requirement; it does not create new identity fields.
- RESPONSIVE EFFECT: none. Existing viewport behavior was measured only. The
  later target contract records context-dock, contextual-surface, drawer, and
  single-surface modes; no breakpoint or resizer changed here.
- ACCESSIBILITY EFFECT: none. Existing semantic/focus/contrast behavior was
  exercised; no runtime ARIA, keyboard, or hit-target implementation changed.
- PERFORMANCE EFFECT: none. The baseline records existing serial browser
  timings and the token contrast audit; no optimization or instrumentation
  path was added.

### V5-00 commands and results

- `cd frontend; bun run test` — PASS, 48 files / 245 tests.
- `cd frontend; bun run lint` — PASS, `tsc --noEmit`.
- `cd frontend; bun run build` — PASS, Vite transformed 1,993 modules.
- `python -m compileall src scripts configs` in the repository virtual
  environment — PASS.
- `python -m pytest tests/ -v` in the repository virtual environment — PASS,
  770 passed with 182 existing warnings.
- `bunx playwright test e2e/workspace-layout.spec.ts
  e2e/regression.spec.ts e2e/structured-document-reader.spec.ts
  --workers=1 --retries=0` — PASS, 66/66 across Chromium and Firefox.
- `bun run test:e2e-local` — PASS, 6/6.
- `bunx playwright test e2e/v5-00-baseline.spec.ts --workers=1
  --retries=0` — PASS, 4/4 across Chromium and Firefox.
- `bun e2e/token-contrast.mjs` — PASS, all reported light/dark token pairs
  meet their WCAG thresholds.
- `bunx playwright test --workers=1 --retries=0` — 155 passed, one existing
  Firefox timing/modal failure in the workspace-layout A–G setup, and four
  intentional skips. The focused 66-test gate above is the clean checkpoint
  gate.
- `bun run test:e2e` — 136 passed, 16 parallel timing/shared-state failures,
  and four skips; recorded as an unstable operational baseline, not a green
  gate.
- `bun run test:e2e-integration` — 12 passed and two failures in both engines
  at the cited-answer assertion because the harness response did not expose
  the expected `Open source 1` citation button. The existing harness/test
  mismatch is outside V5-00 and was not changed.

### V5-00 runtime, visual, and ownership receipt

- Runtime validation: production Vite build and the focused browser gate
  passed; the baseline capture verified answer/source/excerpt visibility and
  page `scrollWidth <= viewport width` at 1440×900 and 1920×1080.
- Visual validation: Chromium and Firefox captures record the current light
  default composition at both wide viewports. The user-supplied
  `09-product-reference.png` was used as a visual target reference only; it
  does not change the representation contract.
- Current geometry: 216px navigation; primary x=232, width 816 at 1440×900
  and width 1296 at 1920×1080; current evidence rail x=1064/1544, width
  360px; two source cards; reader stacked below sources; no separate
  persistent Document pane.
- Known limitations: V5 four-pane implementation has not started; real
  integration retains the two citation-button failures; provider/network,
  long-stream, and memory timings are not claimed; the historical native
  browser-chrome zoom gate at 100/125/150/200% remains an external manual
  gate.
- Process ownership: Playwright/Vite/harness processes were task-owned and
  self-cleaned. No project listener remained on 3000, 4173, 4175, 5173,
  8000, 8765, or 8766. Existing Codex/browser infrastructure was not killed.
- Unrelated dirty state: pre-existing untracked `.audit-runtime/` and
  `harness_stacks.txt` were preserved untouched, as was ignored `data/`.
- ROLLBACK POINT: remove only the V5-00 contract/receipt and the test-only
  baseline spec if the checkpoint is intentionally rolled back; do not revert
  unrelated user work or generated/ignored data.
- EXACT NEXT TASK: `V5-01`, typed workbench primitives and
  resizer/preference contracts, with no shell migration outside that scope.

## V5-01 Workbench state, preferences, and typed targets — 2026-09-13

- TASK ID: `V5-01`.
- STATUS: `[x] COMPLETE`.
- PROBLEM/DECISION: the current App-level booleans and legacy rail width did
  not model the planned four-pane presentation, actual geometry modes, exact
  variant-aware return links, or a representation-neutral reader binding.
  V5-01 adds those typed seams without mounting them in the visible App shell.
- FILES CREATED: `frontend/src/lib/workbench.ts`,
  `frontend/src/lib/evidenceDeepLink.ts`,
  `frontend/src/lib/readerLocationView.ts`,
  `frontend/src/hooks/useWorkbenchController.ts`,
  `frontend/src/hooks/useWorkbenchPreferences.ts`, plus focused tests in
  `frontend/src/lib/workbench.test.ts`,
  `frontend/src/lib/evidenceDeepLink.test.ts`,
  `frontend/src/lib/readerLocationView.test.ts`,
  `frontend/src/hooks/useWorkbenchPreferences.test.tsx`, and
  `frontend/src/hooks/useWorkbenchController.test.tsx`.
- FILES CHANGED: the files above and the V5 contract/implementation receipts;
  no files removed.
- ARCHITECTURE EFFECT: adds an isolated presentation contract for
  `WorkbenchLayoutMode`, `ActiveRepresentation`, source/document panes,
  document context tabs, source filters, and the existing
  `WorkspaceTarget` identity type. The App and legacy rail remain unchanged;
  V5-02 is the first shell consumer.
- STATE EFFECT: `useWorkbenchController` owns transient presentation and
  coordination only: mode, target handoff, active contextual pane,
  representation, source filter, document lower tab, find text, focus-return
  ID, and selected-source binding status. It does not become a second owner
  for conversations, query lifecycle, evidence persistence, document content,
  reader network state, or source identity.
- ASYNC EFFECT: none in transport. The controller has no fetch or stream
  path. Its generation-guarded evidence binding reducer ignores late
  Structured/Normalized location outcomes after a newer target or generation;
  `useReaderSession` remains the cancellation/abort owner.
- API EFFECT: none. Existing `EvidenceLocation`, `OriginalLocation`, reader
  responses, `WorkspaceTarget`, and backend DTOs are consumed as types only;
  no endpoint, query, SSE event, or request payload changed.
- PERSISTENCE EFFECT: adds only the layout-only V1 preference envelope
  `sec_qa_workbench_panes_v1`. It stores Sources/Document widths and collapse
  flags only. No source content, selection, document content, document find
  query, or fullscreen state is persisted. The old
  `sec_qa_context_rail_width_v1` value is clamped into Sources width on a
  missing V5 key, the new key is written, and the old key is left untouched.
- PROVENANCE EFFECT: no new identity is invented. `readerLocationView.ts`
  preserves the raw Structured/Normalized response, keeps missing source
  document/revision facts null, and exposes exact/ambiguous/not-found/
  unavailable/stale/error states without fuzzy fallback.
- RESPONSIVE EFFECT: no visible breakpoint change. `deriveWorkbenchLayoutMode`
  uses measured container width/height, measured navigation width, current
  pane widths, and separators. It covers four-pane, context-dock,
  contextual-surface, drawer, and single-surface modes plus short-height
  downgrade thresholds for the future shell.
- ACCESSIBILITY EFFECT: no visible runtime change. The typed contract leaves
  the future splitter and focus-restoration seam explicit; keyboard/focus
  behavior is not claimed as a rendered V5-01 feature.
- PERFORMANCE EFFECT: no runtime fetch/render path or dependency added.
  Preference updates are explicit commits; no pointer-event loop or global
  state library was introduced.
- SECURITY/PDF EFFECT: no browser-exposed secret, unsafe content path, raw
  HTML path, PDF state, PDF control, or PDF endpoint was introduced.

### V5-01 acceptance coverage

- `WorkbenchLayoutMode` derives from actual geometry: tests cover 1440×900
  and 1920×1080 four-pane, 1366/1280 context-dock, 1024 contextual surface,
  768 drawer, 390 single surface, and short-height downgrades.
- Pane width tests cover Sources `280–360`, Document `400–560`, integer
  clamping, remaining Research width, malformed payload fallback, future
  schema fallback, and non-destructive old-width migration.
- Preference hook tests cover V1 envelope writes, reset, storage failures,
  valid cross-tab updates, malformed/future cross-tab payloads, and clear-to-
  default behavior.
- Deep-link tests cover legacy hashes, exact variant/conversation/source-key
  round trips, short aliases from early links, selection conversion, and
  malformed/invalid inputs.
- Reader location tests cover raw-response preservation, Structured and
  Normalized offset adaptation, exact/ambiguous status, missing identity, and
  stale/unavailable generation guards.
- Controller tests cover presentation-only state transitions, target
  reference preservation, representation reset, explicit focus restoration,
  and late binding rejection.

### V5-01 commands and results

- `bunx vitest run src/lib/workbench.test.ts src/lib/evidenceDeepLink.test.ts
  src/lib/readerLocationView.test.ts
  src/hooks/useWorkbenchPreferences.test.tsx
  src/hooks/useWorkbenchController.test.tsx` — PASS, 18/18.
- `bun run test` — PASS, 53 files / 263 tests.
- `bun run lint` — PASS, `tsc --noEmit`.
- `bun run build` — PASS, Vite transformed 1,993 modules.
- `bunx playwright test e2e/v5-00-baseline.spec.ts --workers=1
  --retries=0` — PASS, 4/4 across Chromium and Firefox; the measured
  V5-00 visual baseline remains unchanged at 1440×900 and 1920×1080.
- `git diff --check` — PASS; only normal Git LF/CRLF normalization warnings
  were reported for the existing journal files.

### V5-01 checkpoint ownership and rollback

- Visual/runtime result: no visible redesign was claimed or introduced;
  current screenshots and legacy rail geometry remain the V5-00 baseline.
- Known limitations: the new seams are not yet consumed by App; V5-02 must
  mount them incrementally. Full browser parallel/serial integration
  limitations from V5-00 remain unchanged and are not reclassified as V5-01
  failures.
- Unrelated dirty state: pre-existing untracked `.audit-runtime/` and
  `harness_stacks.txt` remain untouched; ignored `data/` remains untouched.
- Process ownership: no service was started or stopped for V5-01; the final
  V5-00 baseline browser run self-cleaned and no project listener remained on
  3000, 4173, 4175, 5173, 8000, 8765, or 8766.
- ROLLBACK POINT: remove the five new implementation modules and their five
  focused test files, leaving existing App/rail code and all prior V5-00
  receipts intact. No data migration is required; the old rail key remains
  readable because migration is non-destructive.
- EXACT NEXT TASK: `V5-02`, workbench shell, top bar, navigation, and scoped
  CSS foundation. Do not begin Sources/Document replacement before V5-02 is
  accepted.

## V5-02 — Workbench shell, top bar, navigation, and CSS foundation

- TASK ID: `V5-02`
- STATUS: `[x] COMPLETE`
- PROBLEM: The previous App composition mixed the global frame with the
  route-local canvas and exposed only the legacy rail presentation. It also
  retained a 64px toolbar instead of the V5 56px global bar.
- DECISION: Add `ApplicationWorkspace`, `ResearchWorkbench`, and
  `WorkbenchLayout` as a rollback-safe shell boundary. Mount the
  presentation controller/preferences there, measure the actual rendered
  shell/navigation geometry, expose future pane CSS variables, and pass the
  existing route main/reader/rail through unchanged until V5-03/V5-04.
- FILES CREATED: `frontend/src/components/workbench/ApplicationWorkspace.tsx`,
  `ResearchWorkbench.tsx`, `WorkbenchLayout.tsx`, their two focused
  component tests, `frontend/src/styles/workbench.css`, and
  `frontend/e2e/v5-02-shell.spec.ts`.
- FILES CHANGED: `frontend/src/App.tsx`, `Sidebar.tsx`,
  `WorkspaceHeader.tsx`, `index.css`, `lib/i18n.tsx`, and `lib/workspace.ts`.
- FILES REMOVED: none.
- ARCHITECTURE CHANGE: App now composes navigation/header/route main/footer
  through the workbench shell. `WorkbenchLayout` provides a measured,
  mode-labelled host; `ResearchWorkbench` provides the semantic route-local
  research region. The legacy `EvidenceWorkspaceRail` remains intentionally
  available as the V5-02 rollback surface.
- STATE OWNERSHIP: `useWorkbenchController` and
  `useWorkbenchPreferences` mount at the shell boundary and own only
  presentation/coordination and layout-only preferences. Existing
  `useResearchSession`, `useEvidenceSelection`, `useReaderSession`,
  Library, storage, and App lifecycle owners remain unchanged.
- ASYNC OWNERSHIP: no new async path; no duplicated source/document fetch,
  stream, cancellation, or reader generation owner.
- API/DTO EFFECT: none.
- PERSISTENCE EFFECT: no new persisted content. V5-01's clamped pane
  preference envelope is consumed; source/reader/find/fullscreen state is not
  persisted.
- PROVENANCE EFFECT: none. Existing evidence and reader identity pass through.
- RESPONSIVE EFFECT: mode labels derive from measured shell width/height and
  measured nav width. Expanded desktop resolves to `context-dock` at
  1440×900 and `four-pane` at 1920×1080; later pane work will make those
  modes visibly distinct.
- ACCESSIBILITY EFFECT: header, navigation, and research landmarks now carry
  stable data regions and translated EN/VI labels; existing keyboard controls,
  dialog focus management, and target hit areas remain in use.
- PERFORMANCE EFFECT: scoped ResizeObserver measurement and one committed
  mode update; no dependency or network path added.
- SECURITY/PDF EFFECT: no secrets, unsafe content, backend route, PDF state,
  PDF control, or PDF implementation added.
- TEST COMMANDS AND RESULTS:
  - `bunx vitest run src/components/workbench/ApplicationWorkspace.test.tsx
    src/components/workbench/WorkbenchLayout.test.tsx src/lib/workspace.test.ts
    src/lib/i18n.test.tsx src/App.test.tsx` — PASS, `5 files / 27 tests`.
  - `bun run test` — PASS, `55 files / 265 tests`.
  - `bun run lint` — PASS, `tsc --noEmit`.
  - `bun run build` — PASS, `2,000` Vite modules transformed.
  - `bunx playwright test e2e/v5-02-shell.spec.ts --workers=1
    --retries=0` — PASS, `4/4` across Chromium/Firefox.
  - `bunx playwright test e2e/workspace-layout.spec.ts
    e2e/regression.spec.ts e2e/structured-document-reader.spec.ts
    e2e/v5-02-shell.spec.ts --workers=1 --retries=0` — PASS, `70/70`
    across Chromium/Firefox.
  - `git diff --check` — PASS, with only normal line-ending warnings.
- RUNTIME/BROWSER VALIDATION: production preview was rebuilt and the shell
  gate verified route content, measured geometry, compact/expanded nav,
  mode signals, 56px bar, focus, theme/locale, and no horizontal overflow.
  The retained reader, route, responsive, Library, and performance gate also
  passed.
- VISUAL VALIDATION: final Chromium captures at 1440×900 and 1920×1080 were
  inspected. The navigation, top bar, overview/research canvas, and composer
  stay visible and within the viewport. These captures validate the shell
  foundation only; they do not claim the final Sources/Document panes.
- KNOWN LIMITATIONS: the vertical `EvidenceWorkspaceRail` is still the
  source/reader presentation. SourcesPane, DocumentPane, exact synchronization,
  resizers, collapse, and final route integrations are not part of V5-02.
- UNRELATED DIRTY WORK PRESERVED: `.audit-runtime/` and
  `harness_stacks.txt` were untouched; ignored `data/` was untouched.
- OWNED PROCESSES: only task-owned Playwright/Vite preview processes were
  started; they self-cleaned. Final listener check was empty for project
  ports `3000`, `4173`, `4175`, `5173`, `8000`, `8765`, `8766`.
- ROLLBACK POINT: remove the V5-02 shell components/tests/style import and
  restore App's prior root composition and 64px header. V5-00/V5-01 files,
  backend, data, and persistence remain intact.
- EXACT NEXT TASK: `V5-03` — first-class Sources pane. Preserve the rail
  until the replacement reference sweep and browser coverage are complete.

## V5-03 — First-class Sources pane

- TASK ID: `V5-03`
- STATUS: [x] COMPLETE
- PROBLEM: The answer and inspector used separate legacy source-list renderers,
  so source states, answer filters, selection focus, and saved evidence affordances
  were not governed by one first-class source surface.
- DECISION: Introduce `SourcesPane` and `SourceCard`. Use the pane for the
  production evidence inspector and the answer fallback disclosure, with the
  workbench context supplying presentation/filter coordination. Keep
  `ContextPanel`/`DocumentViewer` as the existing reader/async owner until
  V5-04.
- FILES CREATED: `frontend/src/components/workbench/WorkbenchContext.tsx`,
  `SourceCard.tsx`, `SourcesPane.tsx`,
  `SourcesPane.test.tsx`, `frontend/src/lib/sourcePresentation.ts`, and
  `frontend/e2e/v5-03-sources.spec.ts`.
- FILES CHANGED: `frontend/src/components/workbench/ApplicationWorkspace.tsx`,
  `frontend/src/components/ChatMessage.tsx`,
  `frontend/src/components/ContextPanel.tsx`,
  `frontend/src/components/EvidenceWorkspaceRail.tsx`, and
  `frontend/src/styles/workbench.css`. No file was deleted.
- ARCHITECTURE CHANGE: `SourcesPane` owns source-list rendering, literal text
  filtering, citation-order presentation, answer-only All/Cited/Saved policy,
  section chips, collapse, list keyboard navigation, and exact focus return.
  `SourceCard` is the shared card implementation for filing identity,
  section, excerpt, representation/state facts, Save Evidence, Open document,
  and advanced ranking disclosure. The removed `ContextPanel` duplicate
  source functions no longer form a second runtime tree.
- STATE OWNERSHIP: the V5 controller owns category-filter coordination and the
  preference context owns layout-only collapse state. `App` and
  `useEvidenceSelection` remain authoritative for exact selected
  source identity. Existing evidence collection storage remains the save
  writer and source provenance owner.
- ASYNC OWNERSHIP: unchanged. The pane does not fetch source/document content.
  `DocumentViewer` retains detail and nearby-chunk requests, abort/retry,
  and reader-generation guards.
- API/DTO EFFECT: none. No backend/retrieval/model/prompt/index/corpus/Qdrant,
  endpoint, DTO, query, SSE, PDF, or request behavior changed.
- PERSISTENCE EFFECT: Save Evidence calls the existing writer and provenance
  helper. Saved state is derived from exact source identity/content and stored
  snapshot metadata; the pane adds no schema or writer.
- PROVENANCE EFFECT: citation order and source/chunk identity remain exact.
  Saved, stale, and unavailable states are explicit. Selection is not fuzzy,
  and no document/PDF location is invented.
- RESPONSIVE EFFECT: answer sources may expose All/Cited/Saved; catalog/search/
  retrieval origins do not expose answer-only filters. The shared pane renders
  in the existing inline and drawer surfaces without changing mode thresholds.
- ACCESSIBILITY EFFECT: stable source labels, `aria-pressed` selection,
  state descriptions, list semantics, 44px-class actions, keyboard
  ArrowUp/ArrowDown/ArrowLeft/ArrowRight/Home/End/Enter behavior, and
  exact deep-link focus are covered.
- PERFORMANCE EFFECT: visible-index computation and saved-state refresh are
  local/event-driven; no new network or global lifecycle owner was added.
- SECURITY/PDF EFFECT: no new URL acquisition, unsafe HTML, secret, PDF control,
  PDF artifact, or external source path was introduced.
- PRODUCTION REFERENCE SWEEP: no production component imports
  `SourcesPanel.tsx`; its direct compatibility tests remain. No
  destructive legacy migration was performed.
- TEST COMMANDS AND RESULTS:
  - `bun run test` — PASS, `56 files / 271 tests`.
  - `bun run lint` — PASS, `tsc --noEmit`.
  - `bun run build` — PASS, `2,003` Vite modules transformed.
  - `bunx playwright test e2e/v5-03-sources.spec.ts --workers=1
    --retries=0` — PASS, `2/2` across Chromium/Firefox.
  - V5-00/V5-02/V5-03 serial slice — PASS, `10/10` across Chromium/
    Firefox.
  - Full serial browser gate `bunx playwright test --workers=1 --retries=0`
    discovered `166` tests: `160 passed, 4 skipped, 2 Firefox-only
    timing failures`. The two pre-existing V4 reader failures passed in an
    isolated Firefox rerun (`3/3`); no reader fix was made.
  - `git diff --check` — PASS, with normal LF/CRLF warnings only.
- RUNTIME/BROWSER VALIDATION: the V5-03 acceptance flow verified source
  identity, saved-state transition, All/Cited/Saved filtering, keyboard
  selection, and one-source reader handoff in both engines. The full browser
  gate retained route, reader, responsive, focus, Library, and performance
  coverage.
- VISUAL VALIDATION: `frontend/e2e/screenshots/v5-03-sources-1440x900.png`
  was inspected from the rebuilt Chromium preview. The pane remains inside the
  viewport without horizontal overflow and visibly exposes the source stack,
  filters, search, selection, save action, and reader.
- KNOWN LIMITATIONS: the source pane still sits in the existing vertical
  `EvidenceWorkspaceRail`; independent Sources/Document pane geometry and
  route-specific catalog/search integrations remain future V5-04/V5-05 work.
  `SourcesPanel.tsx` is retained for compatibility-only references and is
  not a production import. Backend/data/PDF behavior was not rerun because
  none of those paths changed; the previous backend baseline remains current.
- UNRELATED DIRTY WORK PRESERVED: `.audit-runtime/`,
  `harness_stacks.txt`, and ignored `data/` were untouched.
- ROLLBACK POINT: remove the V5-03 SourcesPane/SourceCard/context integration,
  shared display helper, styles, tests, and browser receipt, then restore the
  previous answer fallback and ContextPanel source-list call. Leave V5-00/
  V5-01/V5-02, backend, data, and persistence intact.
- EXACT NEXT TASK: `V5-04` — first-class Document pane, retaining the existing
  reader/provenance lifecycle while SourcesPane remains the sole source-list
  owner.

## V5-04 — Shared Document pane and reader adaptation

- TASK ID: `V5-04`
- STATUS: [x] COMPLETE
- PROBLEM: The existing readers were valuable but appeared as a standalone
  route shell or a nested inspector surface, without a shared workbench
  identity header, genuine representation switcher, lower evidence context,
  or coordinated find state.
- DECISION: Add `DocumentPane` and `DocumentContextTabs` as
  a presentation adapter around `DocumentWorkspace`. Use the
  existing Structured and Normalized text readers unchanged as the content
  owners; keep the compatibility workspace mode and legacy tabs for direct
  consumers.
- FILES CREATED: `frontend/src/components/workbench/DocumentPane.tsx`,
  `DocumentContextTabs.tsx`, focused unit tests, and
  `frontend/e2e/v5-04-document.spec.ts`.
- FILES CHANGED: `DocumentWorkspace.tsx`,
  `StructuredDocumentReader.tsx`,
  `OriginalDocumentReader.tsx`, `ContextPanel.tsx`,
  `App.tsx`, `document-reader.css`, and test-only
  original-reader fixture routes.
- ARCHITECTURE CHANGE: production answer/catalog/search document entry points
  now use `DocumentPane`. It supplies one identity-bearing shell,
  Structured/Normalized text controls, one embedded reader canvas, local
  Evidence/Metadata/conditional Notes tabs, and a bounded expand/restore
  surface. Indexed excerpt is evidence context, not a representation.
- STATE OWNERSHIP: the existing workbench controller coordinates
  representation, context tab, find query, and active pane when available;
  direct consumers use transient local fallback state. App route identity,
  reader session/generation, source provenance, evidence selection, and Save
  Evidence persistence remain in their existing owners.
- ASYNC OWNERSHIP: unchanged. No new fetch, stream, cancellation owner, or
  request lifecycle was introduced. Reader manifest/content/search/location,
  coverage, table semantics, and exact location behavior remain intact.
- API/DTO EFFECT: none in production. Retrieval, generation, model, prompt,
  index, corpus, Qdrant, backend/API/DTO/query/SSE, and PDF behavior were not
  changed. The e2e fixture only adds responses for the existing normalized
  reader contract.
- PERSISTENCE/PROVENANCE EFFECT: no new storage or notes model. Find,
  representation, context-tab, and expansion state are transient. Existing
  source identity, revision binding, exactness/fallback semantics, SEC link,
  and evidence save/provenance behavior remain authoritative.
- RESPONSIVE/ACCESSIBILITY EFFECT: the reader and lower context surface share
  one bounded scroll composition; container-aware header wrapping keeps
  narrow inspector controls usable. Representation buttons expose pressed
  state, context tabs have tablist semantics and roving keyboard focus, and
  normalized embedded reader states have an explicit accessible label.
- SECURITY/PDF EFFECT: no unsafe HTML, new external source path, secret, PDF
  control, PDF artifact, or fake page semantics were introduced.
- TEST COMMANDS AND RESULTS:
  - `bun run test` — PASS, `58 files / 277 tests`.
  - `bun run lint` — PASS, `tsc --noEmit`.
  - `bun run build` — PASS, `2,005` Vite modules.
  - V5-04 Chromium/Firefox acceptance — PASS, `2/2`.
  - V5-00/V5-02/V5-03/V5-04 serial slice — PASS, `12/12`.
  - Existing document-workspace/structured-reader compatibility slice —
    PASS, `6/6` across Chromium/Firefox.
  - `git diff --check` — PASS, normal line-ending warnings only.
- RUNTIME/VISUAL VALIDATION: the rebuilt Chromium preview at 1440×900 was
  inspected in `frontend/e2e/screenshots/v5-04-document-1440x900.png`.
  The shared document identity, reader representation switcher, context
  tabs, find handoff, and restore control are visible and remain within the
  viewport. The existing inspector remains a vertical source/reader
  composition pending the geometry task.
- KNOWN LIMITATIONS: independent Sources/Document pane geometry, resizers,
  collapse behavior, and exact cross-pane synchronization remain V5-05/V5-06.
  The compatibility `DocumentWorkspace` module remains present.
  Backend/data/PDF behavior was not rerun because no production path changed.
- UNRELATED DIRTY WORK PRESERVED: `.audit-runtime/`,
  `harness_stacks.txt`, and ignored `data/` were untouched.
- ROLLBACK POINT: remove the V5-04 DocumentPane/context-tab adapter,
  reader prop seam, styles/tests/fixture routes, and App/ContextPanel
  substitutions; restore their prior DocumentWorkspace imports without
  touching V5-00 through V5-03 or backend/data/persistence behavior.
 - EXACT NEXT TASK: `V5-05` — responsive Sources + Document geometry
  and explicit cross-pane source/document synchronization.

## V5-05 — Exact source synchronization and deep links

- TASK ID: `V5-05`
- STATUS: [x] COMPLETE
- PROBLEM: the selected source, reader location, and route target could drift
  when a source lacked a local hash, when a location response was stale or
  ambiguous, when representations changed, or when an old/new deep link was
  reopened.
- DECISION: keep `App` authoritative for route identity, keep the readers as
  request/cancellation owners, and add a typed evidence-location seam that
  verifies chunk/hash/document/source-set/source-revision identity before
  highlighting. Resolve only live missing-hash details through the existing
  cache; treat hashless historical snapshots as unavailable.
- FILES CREATED: `frontend/src/hooks/useReaderEvidenceSource.ts` and its
  focused test, `frontend/src/lib/api.test.ts`, and
  `frontend/e2e/v5-05-sync.spec.ts`.
- FILES CHANGED: `frontend/src/App.tsx`, `ContextPanel.tsx`, `SourcesPane.tsx`,
  `DocumentWorkspace.tsx`, `StructuredDocumentReader.tsx`,
  `OriginalDocumentReader.tsx`, their tests, `readerLocationView.ts` and its
  tests, `useWorkbenchController.ts`, and hermetic normalized-reader
  fixtures. No file was deleted.
- STATE/ASYNC OWNERSHIP: exact canonical deep links select the requested
  conversation/message/variant/citation/source key; missing targets are
  unavailable or closed rather than falling forward. Readers emit
  resolving/resolved/stale/unavailable/error events with generation and
  request guards. Late responses after rapid source switching are ignored.
- LOCATION TRUTH: exact responses require matching chunk ID/hash, document ID,
  source-set revision, verified source document, document revision, and a
  representation range. Ambiguous, stale, not-found, unavailable, and
  transport-error results remain visible with concise reason text and never
  produce a yellow mark. Normalized exact locations use the existing nested
  source/document identity contract.
- API/DTO EFFECT: none. Existing structured reader-location,
  normalized original-location, and cached chunk-detail client paths are
  reused and covered by URL/error tests. No backend, endpoint, DTO, query,
  SSE, retrieval, generation, model, prompt, index, corpus, Qdrant, or PDF
  behavior changed.
- PERSISTENCE/PROVENANCE EFFECT: none. Existing evidence collection and
  snapshot writers remain unchanged. A saved snapshot without a verifiable
  hash is explicitly unavailable and is not silently replaced with current
  content.
- RESPONSIVE/A11Y EFFECT: no pane geometry was changed; source actions open
  the existing shared document surface, reader status remains live and
  accessible, exact structured ranges retain block focus, and current shell
  EN/VI/dark/keyboard/width coverage remains authoritative.
- PERFORMANCE/SECURITY EFFECT: resolution uses the existing cache and
  generation/abort mechanisms, with no new global listener or acquisition
  path. No unsafe HTML, secret, new external URL, approximate highlight,
  fabricated page, or PDF control was introduced.
- TEST COMMANDS AND RESULTS:
  - `bun run test -- --reporter=dot` — PASS, `60 files / 288 tests`.
  - `bun run lint` — PASS, `tsc --noEmit`.
  - `bun run build` — PASS, `2,007` Vite modules transformed.
  - V5-00/V5-02/V5-03/V5-04/V5-05 Chromium/Firefox serial slice — PASS,
    `16/16`.
  - Existing Documents/Search exact-chunk compatibility regression — PASS,
    `2/2` across Chromium/Firefox.
  - `git diff --check` — PASS, normal LF/CRLF warnings only; final project
    listener check empty on ports `3000`, `4173`, `4175`, `5173`, `8000`,
    `8765`, and `8766`.
- RUNTIME/VISUAL VALIDATION: `frontend/e2e/screenshots/v5-05-sync-1440x900.png`
  was captured from the rebuilt Chromium preview and inspected. The answer,
  sources, selected evidence, document identity, representation controls, and
  verified reader context stayed legible and inside the viewport. The V5-05
  browser flow also verified exact structured/normalized marks and reload
  without source fall-forward.
- KNOWN LIMITATIONS: the answer inspector still uses the existing vertical
  evidence rail; independent Sources/Document geometry, resizers, collapse
  policy, and pane-level visual acceptance remain V5-06. Compatibility
  `DocumentWorkspace` remains present for direct consumers. Backend/data/PDF
  behavior was not rerun because no production path in those areas changed.
- UNRELATED DIRTY WORK PRESERVED: `.audit-runtime/`,
  `harness_stacks.txt`, and ignored `data/` were untouched. Task-owned
  browser/preview processes self-cleaned.
- ROLLBACK POINT: remove the V5-05 location validation/event seam, cached
  source resolver, canonical target resolution, and focused tests/fixtures;
  restore the prior source-open/deep-link handoff while leaving V5-00 through
  V5-04 and backend/data/persistence behavior intact.
- EXACT NEXT TASK: `V5-06` — responsive Sources + Document geometry,
  resizers, collapse policy, and visual acceptance.

## V5-06 — Responsive workstation geometry and pane controls

- TASK ID: `V5-06`
- STATUS: [x] COMPLETE
- DECISION: the measured `WorkbenchLayout` now composes Research with sibling
  Sources and Document surfaces. Four-pane, context-dock, contextual-surface,
  drawer, and single-surface modes are selected from actual shell geometry,
  navigation width, pane widths, separators, and height. No readable text is
  reduced to force a mode.
- FILES CREATED: `frontend/src/components/workbench/PaneResizer.tsx` and
  `frontend/e2e/v5-06-layout.spec.ts`.
- FILES CHANGED: `ApplicationWorkspace.tsx`, `WorkbenchLayout.tsx`,
  `ContextPanel.tsx`, `DocumentWorkspace.tsx`, `App.tsx`,
  `useNavigationLayout.ts`, layout styles, `README.md`, `DESIGN.md`, and
  hermetic non-Apple reader fixtures. No production backend/reader endpoint
  or data file changed.
- GEOMETRY: 1440×900 is compact-nav 56px + Research 624px + Sources 304px +
  8px splitter + Document 440px + 8px splitter; 1920×1080 is expanded-nav
  216px + Research 944px with the same contextual tracks. 1366×768 and
  1280×800 use a 440px Sources/Document dock; 1024 is contextual-surface;
  below 1024 uses modal drawer/single-surface behavior.
- INTERACTION: pointer motion is CSS-variable-only in rAF until pointer-up;
  cancel restores the start width. Arrow/Home/End/Enter/Space, double-click
  Reset, Wider/Narrower, and width clamping are available without drag-only
  access. Source/document collapse retains the last width and exposes a
  keyboard-accessible restore target. Document reader height is at least 300px;
  lower context is bounded to `min(17rem, 32%)` and collapses first on short
  tracks.
- STATE/ASYNC/PROVENANCE: layout preferences remain the only persisted V5
  state. Source identity, reader transport, exact location, evidence saves,
  query lifecycle, and all backend boundaries remain in their prior owners.
- TEST COMMANDS AND RESULTS:
  - `bun run test -- --reporter=dot` — PASS, `60 files / 289 tests`.
  - `bun run lint` — PASS; `bun run build` — PASS, `2,008` Vite modules.
  - V5-02 shell Chromium — PASS, `2/2`; V5-05 sync Chromium — PASS, `2/2`.
  - V5-06 layout Chromium — PASS, `3/3`; Firefox — PASS, `3/3`.
  - `git diff --check` remains limited to normal line-ending warnings.
- VISUAL VALIDATION: inspected the rebuilt Chromium renders at
  `frontend/e2e/screenshots/v5-06-four-pane-1440x900.png` and
  `frontend/e2e/screenshots/v5-06-four-pane-1920x1080.png`; Research,
  Sources, and Document remain simultaneously legible and inside the viewport.
- PRESERVED/UNRELATED: `.audit-runtime/`, `harness_stacks.txt`, ignored
  `data/`, and existing persistence/library behavior were preserved. No
  retrieval, generation, model, prompt, index, corpus, Qdrant, PDF, or
  acquisition behavior changed.
- ROLLBACK POINT: remove `PaneResizer`, sibling composition, responsive CSS,
  navigation default, document collapse affordance, and V5-06 tests/fixtures;
  restore the prior rail presentation without touching V5-00 through V5-05 or
  backend/data/reader ownership.
- EXACT NEXT TASK: `V5-07` — Documents, Search, Retrieval Lab, and Library
  handoffs through the shared workbench boundary.

## V5-07 execution checkpoint — 2026-09-13

V5-07 is complete. Documents, Search, Retrieval Lab, and Library now hand off
through the shared workbench presentation boundary while their existing route,
fetch, retrieval, cache, reader, and persistence owners remain in place.
Documents keeps its catalog mounted while a filing is open; Search result
cards expose analyst identity, filing date, indexed inspection, Document
workspace, and the existing Save Evidence action; Retrieval Lab emits a typed
document target without changing Analyst/Advanced diagnostics or score
semantics. Library reuses the completed P07 saved variant/evidence behavior,
including exact source identity and truthful historical snapshot/current-source
distinction.

`RouteDocumentContext` selects the shared contextual slot at four-pane and
context-dock widths and the existing modal lifecycle at narrower widths.
Stable route and Library opener IDs restore the exact invoker after Back or
close. The Search indexed action remains an evidence inspector action, while
the explicit Document action opens the typed shared Document target; this
preserves the existing exact-chunk regression semantics.

Validation receipts:

- Full frontend Vitest passed `60 files / 291 tests`.
- TypeScript lint passed; production Vite build passed with
  `2,009` transformed modules.
- V5-07 handoff acceptance passed `4/4` in Chromium and `4/4` in Firefox.
- Existing affected browser compatibility checks passed: the exact-chunk
  Documents/Search regression `1/1` and V5-04 document acceptance `1/1` in
  Chromium.
- Focused route unit coverage passed `4 files / 35 tests`.

No backend/API/DTO, query/SSE, retrieval, generation, model, prompt, corpus,
index, Qdrant, reader transport, provenance, persistence schema, acquisition,
or PDF behavior changed. The only e2e fixture adjustment adds identity fields
for the existing normalized-reader response. `.audit-runtime/`,
`harness_stacks.txt`, and ignored `data/` remain untouched; task-owned
preview/browser processes self-cleaned.

Rollback is limited to the route target adapter, handoff callbacks, stable
focus IDs, scoped CSS, and V5-07 tests/fixture updates. No data migration or
backend/domain rollback is required. Exact next task: `V5-08` — complete
visual, accessibility, browser, performance, and regression closure.

## V5-08 — Final workbench closure

- TASK ID: `V5-08`
- STATUS: [x] COMPLETE
- DECISION: close the V5 research workbench at the rendered browser boundary.
  The shared four-pane composition, measured responsive downgrades, exact
  reader highlight, accessible focus paths, and existing route handoffs are
  now validated as one system. No domain or reader transport was redesigned.
- FINAL ARCHITECTURE: `App.tsx` owns route/document identity;
  `ApplicationWorkspace`/`WorkbenchLayout` own shell composition and measured
  mode; `useWorkbenchController` mirrors presentation state;
  `useWorkbenchPreferences` persists only pane widths/collapse; `SourcesPane`
  owns source-list filtering/focus; `DocumentPane` adapts existing Structured
  and Normalized readers; `RouteDocumentContext` carries typed route targets.
- RESPONSIVE RECEIPT: 1440×900 = 56px navigation + Research 624px + Sources
  304px + 8px splitter + Document 440px + 8px splitter; 1920×1080 = 216px
  navigation + Research 944px with the same contextual tracks. 1366×768 and
  1280×800 use context dock; 1024×768 and 1366×520 use contextual surface;
  768/390 use drawer/single surface; 640/320 smoke paths stay usable.
- VISUAL RECEIPT: rebuilt Chromium renders at
  `frontend/e2e/screenshots/v5-06-four-pane-1440x900.png` and
  `frontend/e2e/screenshots/v5-06-four-pane-1920x1080.png` were inspected.
  Both show simultaneous Research/Sources/Document surfaces, selected AAPL
  evidence, readable document content, the exact amber/yellow structured mark,
  and no overlap or page-level horizontal overflow. The reader grid now uses a
  non-shrinking content track at the 1440×900 short wide height.
- TEST COMMANDS AND RESULTS:
  - `.venv\Scripts\python.exe -m pytest -q` — PASS, `770 passed`,
    `182 warnings`.
  - `bun run test -- --reporter=dot` — PASS, `60 files / 292 tests`.
  - `bun run lint` — PASS, `tsc --noEmit`.
  - `bun run build` — PASS, `2,009` Vite modules transformed.
  - V5-00/V5-02/V5-03/V5-04/V5-05/V5-06/V5-07 serial slice — PASS,
    `15/15` Chromium and `15/15` Firefox.
  - Full `app.spec.ts` — PASS, `38/38` Chromium and `38/38` Firefox.
  - Full `regression.spec.ts` — PASS, `31/31` Chromium and `31/31` Firefox.
  - Synthetic `workspace-performance.spec.ts` — PASS, `2/2` executed in
    each engine and `2` provider-dependent checks skipped. Chromium latest
    p95s: warm composer `14.00ms`, warm view `42.90ms`, Markdown layout
    `175.70ms`; source switching p50/p95 `166.10/204.30ms`. Firefox:
    `27.00ms`, `89.00ms`, `314.00ms`; source switching `143.00/164.00ms`.
  - Production regression p95s: Chromium Library search/composer
    `62.67/43.50ms`; Firefox `68.21/40.00ms`, below 200/100ms budgets.
- ACCESSIBILITY: overview Axe serious/critical scan, regression contrast scan,
  keyboard tabs/splitters/dialogs, focus restoration, EN/VI, and reduced-motion
  browser journeys passed. Native browser zoom remains a manual external gate.
- BOUNDARY/PRESERVATION: no backend/API/DTO, query/SSE, retrieval, generation,
  model, prompt, index, corpus, Qdrant, acquisition, provenance, persistence,
  or PDF behavior changed. `.audit-runtime/`, `harness_stacks.txt`, ignored
  `data/`, and unrelated dirty work were preserved. No file was removed, no
  commit/deploy/benchmark promotion occurred, and task-owned listeners were
  cleaned up.
- KNOWN LIMITATIONS: PDF is still deferred and no tracked PDF corpus or
  provenance-bound PDF location contract exists; native browser zoom remains
  manual. Historical checkpoint text may mention the former rail, but the
  current design/contract now identifies the shared workbench as authoritative.
- ROLLBACK POINT: V5-08-only reader/workbench CSS, performance-probe,
  responsive-fixture, and documentation changes. POST-V5 NEXT TASK: `PDF-01`,
  only after a separate real PDF representation and exact-location contract
  is approved.

## PDF-00 — Current repository / test / process reconciliation

- TASK ID: `PDF-00`
- STATUS: [x] COMPLETE
- FILES CHANGED: `docs/implementation-progress.md` only for this checkpoint.
- FILES CREATED: none by PDF-00. The dirty worktree already contained
  untracked `src/api/pdf_representation.py`, `src/api/pdf_generator.py`, and
  `tests/test_pdf_pipeline.py`; these are preserved as existing user-owned
  work and are not treated as a clean baseline.
- CURRENT IMPLEMENTATION TRUTH: document identity and source-set/document
  revisions are owned by `OriginalViewer` and its revision-bound snapshots;
  Structured and Normalized readers already validate document/source/chunk/hash
  identity before highlighting. The backend reader manifest has a provisional
  `pdf` entry and PDF status/generate/content routes, while the frontend
  `ActiveRepresentation` and live reader UI still support only Structured and
  Normalized. The legacy `WorkstationDocumentViewer` is fabricated presentation
  data (fixed page count, page number, and text) and is not a valid PDF path; it
  must not be reused as evidence or page truth.
- CURRENT PDF SCAFFOLD CONTRADICTIONS: the existing untracked backend scaffold
  uses ReportLab and a block-level mapping sidecar, has no mapping retrieval
  endpoint, and exposes PDF lifecycle strings that do not yet align with the
  typed reader/frontend status contracts. These are PDF-01 hardening items,
  not reasons to change retrieval, generation, indexing, or corpus semantics.
- CURRENT STORAGE: verified raw SEC sources remain under the existing
  `data/raw` boundary and processed reader/index artifacts under `data`; the
  configured backend PDF artifact root is `data/generated/pdf` and remains
  git-ignored. No data files were deleted, moved, regenerated, or committed.
- CURRENT TEST COMMANDS / RESULTS:
  - `.venv\\Scripts\\python.exe -m pytest -q tests/test_original_viewer.py tests/test_structured_document.py tests/test_structured_location.py tests/test_pdf_pipeline.py` — PASS, `29 passed`, `50 warnings`.
  - `bun run test -- --run src/components/workbench/DocumentPane.test.tsx src/components/StructuredDocumentReader.test.tsx src/components/OriginalDocumentReader.test.tsx src/components/DocumentWorkspace.test.tsx` from `frontend/` — PASS, `4 files / 16 tests`.
  - Existing V5-08 closure remains the broader repository baseline recorded
    above; no intentionally failing baseline test was introduced.
- CURRENT PROCESSES / PORTS: read-only inspection found no project-owned
  listener on ports `3000`, `4173`, `4175`, `5173`, `8000`, `8765`, or `8766`.
  Existing desktop Chrome/Edge/Codex processes were not killed or claimed as
  Goal-owned. No PDF/backend/frontend process was started by PDF-00.
- REPRESENTATION CONTRACT EFFECT: none; reconciliation only.
- API EFFECT: none; existing provisional PDF routes were inspected only.
- STORAGE EFFECT: none.
- PROVENANCE EFFECT: none.
- SECURITY EFFECT: confirmed the intended boundary must resolve only a
  verified project-owned `document_id`; arbitrary URL/path/HTML rendering is
  not an allowed design.
- FRONTEND EFFECT: none.
- MAPPING EFFECT: none; the missing mapping transport and representation
  switch integration are recorded for later phases.
- BROWSER VALIDATION: no browser session was started; the existing V5-08
  receipts remain the current workbench visual baseline.
- PERFORMANCE OBSERVATION: no PDF measurement was claimed at baseline.
- KNOWN LIMITATIONS: no real PDF.js viewer, official-PDF admission path,
  mapping API, PDF↔reader synchronization, or PDF-specific browser coverage
  exists yet; current source corpus truth still needs a live inventory check.
- UNRELATED WORK PRESERVED: all dirty V5/V5.1 frontend, backend, docs,
  audit-runtime, screenshots, harness, and ignored `data/` work was preserved.
- OWNED PROCESSES: none.
- EXACT NEXT TASK: `PDF-01` — harden the representation/provenance/artifact
  manifest and reader/API contracts before exposing PDF controls.

## PDF-01 — Representation, provenance, and artifact contracts

- TASK ID: `PDF-01`
- STATUS: [x] COMPLETE
- FILES CHANGED: `src/api/pdf_representation.py`, `src/api/pdf_generator.py`,
  `src/api/app.py`, `src/api/document_reader_models.py`,
  `src/api/document_sources.py`, `frontend/src/types.ts`,
  `frontend/src/lib/api.ts`, `tests/test_pdf_pipeline.py`, and this file.
- FILES CREATED: none in this phase; the pre-existing untracked PDF scaffold
  was extended in place and remains user-owned dirty work.
- REPRESENTATION CONTRACT EFFECT: manifests now distinguish `OFFICIAL_PDF`
  from `DERIVED_PDF`, carry explicit `official_pdf_pages` versus
  `generated_representation_pages` semantics, include representation identity,
  artifact status, renderer profile, mapping-manifest identity, page count,
  and source/artifact hashes. The internal official-admission constructor is
  explicit and does not relabel generated bytes as official. Current corpus
  inventory remains 50 `.html` + 1 `.htm` under `data/raw` and no PDF source.
- ARTIFACT IDENTITY: derived keys bind representation type, document ID,
  source document ID, source-set revision, document revision, source hash, and
  the frozen renderer profile. Browser-facing manifests carry no local path.
- API EFFECT: existing document-bound status/generate/content routes now return
  the v2 manifest shape and typed PDF availability metadata; the client API
  has document-bound manifest/generate/content/mapping contracts. No arbitrary
  URL, filesystem path, or HTML input is accepted or used for rendering.
- STORAGE EFFECT: artifact keys are path-safe; promotion validates artifact
  and mapping hashes, writes all files under a unique temporary directory,
  fsyncs them, and atomically promotes the directory while quarantining a
  mismatched current directory. Latest-revision markers are written with
  unique temporary names.
- PROVENANCE EFFECT: document/source/revision/hash identity remains the
  authority; PDF page coordinates are representation-specific metadata only.
- SECURITY EFFECT: route identity is resolved from the verified project-owned
  document catalog and admitted local source. The contract rejects traversal
  keys and unbound artifact/mapping bytes; arbitrary source acquisition is
  outside the PDF surface.
- FRONTEND EFFECT: browser types and API helpers understand truthful PDF
  status/manifest metadata, but no PDF tab or fake viewer control was exposed.
- MAPPING EFFECT: mapping sidecar IDs and artifact-hash binding are now part of
  the contract; retrieval and exact range resolution remain PDF-04 work.
- TEST COMMANDS / RESULTS:
  - `.venv\\Scripts\\python.exe -m pytest -q tests/test_pdf_pipeline.py tests/test_original_viewer.py tests/test_structured_document.py tests/test_structured_location.py` — PASS, `31 passed`, `50 warnings`.
  - `bun run lint` from `frontend/` — PASS, `tsc --noEmit`.
  - `git diff --check` — PASS apart from normal line-ending warnings.
- BROWSER VALIDATION: no PDF browser controls were exposed in PDF-01, so no
  new browser receipt was claimed.
- PERFORMANCE OBSERVATION: no PDF performance claim was made.
- KNOWN LIMITATIONS: generation still uses the existing controlled ReportLab
  renderer scaffold and needs bounded generation validation, mapping transport,
  and page/viewer integration. `ReaderAvailability` now admits lifecycle
  states, but the live frontend still intentionally renders Structured and
  Normalized only.
- UNRELATED WORK PRESERVED: all pre-existing V5/V5.1 changes, audit artifacts,
  screenshots, harness files, processes, and ignored `data/` were preserved.
- OWNED PROCESSES: none.
- EXACT NEXT TASK: `PDF-02` — secure DERIVED_PDF generation, real artifact
  validation, bounded concurrency/timeout, stale invalidation, and fixture
  coverage without changing retrieval or ingestion semantics.

## PDF-02 — Controlled DERIVED_PDF generation backend

- TASK ID: `PDF-02`
- STATUS: [x] COMPLETE
- FILES CHANGED: `configs/settings.py`, `src/api/pdf_generator.py`,
  `src/api/pdf_representation.py`, `src/api/app.py`,
  `tests/test_pdf_pipeline.py`, and this file.
- FILES CREATED: none in this phase; the existing PDF scaffold remains the
  source tree for the implementation.
- GENERATOR: the current backend has no Playwright/Python browser runtime and
  the repository's frontend is independently deployed, so the controlled
  renderer remains the fixed ReportLab text renderer already present in the
  scaffold. It consumes only the admitted normalized source snapshot, escapes
  active content, emits no remote scripts, preserves source text/table lines,
  and captures PDF-point rectangles during the same draw operation. This
  direct PDF-coordinate approach avoids an unverified browser viewport-to-PDF
  transform for the first implementation.
- ARTIFACT LIFECYCLE: source identity is revalidated after rendering and
  before promotion; generated bytes pass PDF header/EOF/page-tree/size checks,
  are hash-bound to the manifest and mapping, then publish via unique
  temporary-directory writes and atomic promotion. Failed or timed-out output
  is never published.
- CONCURRENCY / STATES: generation uses per-artifact single-flight locking,
  a bounded cross-artifact semaphore, and backend-managed `generating`,
  `failed`, and `stale` state receipts. A current artifact is reused on repeat
  requests; stale revision artifacts are not served. The configured bounds are
  two concurrent jobs, 60 seconds, 8,000,000 source code points, 20,000
  blocks, and 64 MiB output by default.
- API EFFECT: the document-only POST lifecycle now marks generation state,
  rechecks source identity, publishes the latest artifact marker only after
  atomic promotion, and returns retryable machine-coded failures. No browser
  URL/path/HTML input is read.
- STORAGE EFFECT: no generated artifact was written to the repository's
  ignored `data/` tree by validation; real-fixture generation used a temporary
  directory that was cleaned up.
- PROVENANCE EFFECT: generated page numbers remain pages of the generated
  representation; source/document/revision/hash identity remains canonical.
- SECURITY EFFECT: source changes during rendering, invalid artifact bytes,
  traversal keys, unbound hashes, oversize input/output, and render-over-time
  output are rejected before current-artifact publication.
- FRONTEND EFFECT: none beyond the PDF-01 typed contracts; PDF controls remain
  deferred until the real artifact transport/viewer exists.
- MAPPING EFFECT: every admitted source-line block receives zero or more
  page/rectangle entries; long documents yield multiple page rectangles, and
  source-layout table lines remain marked as table blocks without invented
  financial semantics.
- TEST COMMANDS / RESULTS:
  - `.venv\\Scripts\\python.exe -m pytest -q tests/test_pdf_pipeline.py` — PASS, `18 passed`, `1 warning`.
  - Real local fixture: AAPL `AAPL:0000320193-25-000079` — PASS, `72` generated pages, `170,516` bytes, `1,515/1,515` mapped blocks, `279.9 ms` in a temporary store.
- BROWSER VALIDATION: not applicable; the PDF.js viewer is the next phase.
- PERFORMANCE OBSERVATION: the measurement above is a local warm-process
  generation observation, not a production guarantee; browser first-render and
  memory behavior remain unmeasured.
- KNOWN LIMITATIONS: rectangle capture is currently block/line-granular, not
  character-granular; official-PDF inventory remains empty; no mapping endpoint
  or PDF.js viewer is wired yet.
- UNRELATED WORK PRESERVED: all V5/V5.1 dirty work, `data/`, audit artifacts,
  screenshots, and desktop processes were preserved.
- OWNED PROCESSES: none; temporary fixture storage was cleaned up.
- EXACT NEXT TASK: `PDF-03` — integrate a real project-owned PDF.js viewer
  into the existing DocumentPane without disturbing Structured/Normalized.

## PDF-03 — Real PDF.js viewer and document-bound transport

- TASK ID: `PDF-03`
- STATUS: [x] COMPLETE
- FILES CHANGED: `frontend/package.json`, `frontend/bun.lock`,
  `frontend/src/components/PdfDocumentViewer.tsx`,
  `frontend/src/styles/pdf-viewer.css`, `frontend/src/components/DocumentWorkspace.tsx`,
  `frontend/src/lib/api.ts`, `frontend/src/types.ts`,
  `frontend/src/lib/workbench.ts`, `frontend/src/hooks/useReaderSession.ts`,
  `frontend/e2e/fixtures.ts`, `frontend/e2e/pdf-viewer.spec.ts`, and this file.
- FILES CREATED: the real `PdfDocumentViewer`, its scoped stylesheet, and a
  hermetic browser fixture/spec using valid PDF bytes. No production data or
  external provider was used.
- FILES REMOVED: none in this phase.
- REPRESENTATION CONTRACT EFFECT: the PDF tab is selectable only for an
  admitted manifest status (`supported`, `generating`, `available`, `stale`, or
  `failed`). Official and generated page semantics are labeled separately;
  Structured and Normalized remain available fallbacks.
- API EFFECT: the frontend uses only document-bound GET/POST manifest routes
  and the document-bound PDF content route. No browser-supplied URL, path, or
  HTML is accepted.
- STORAGE EFFECT: `pdfjs-dist` and its worker are bundled in the independent
  frontend build; no PDF bytes are stored in the frontend repository.
- PROVENANCE EFFECT: the viewer displays the backend representation identity,
  source/revision-bound status, and generated-page truth; it does not infer SEC
  page numbers from a generated artifact.
- SECURITY EFFECT: PDF.js receives bytes only from the backend's checked
  document route. Download and fullscreen controls are bound to the current
  document, not to arbitrary href/path input.
- FRONTEND EFFECT: the existing DocumentPane now hosts a real canvas/text-layer
  viewer with page controls, fit/zoom, search, download, fullscreen, keyboard
  navigation, loading/error/retry states, and reduced-motion styling.
- MAPPING EFFECT: the viewer accepts highlight rectangles only as a typed prop;
  no approximate or locally guessed highlight is painted.
- TEST COMMANDS / RESULTS:
  - `bun run lint` — PASS, `tsc --noEmit`.
  - `bun run build` — PASS, 2,015 modules transformed; the expected PDF worker
    and large-application-chunk warnings remain non-fatal.
  - `bunx playwright test e2e/pdf-viewer.spec.ts --project=chromium --workers=1` — PASS, `1/1`.
  - `bunx playwright test e2e/pdf-viewer.spec.ts --project=firefox --workers=1` — PASS, `1/1`.
- BROWSER VALIDATION: both engines loaded real PDF.js bytes, rendered a canvas
  page, exposed the selectable text layer, exercised zoom and find, and kept
  the generated-page label visible.
- PERFORMANCE OBSERVATION: final focused runs measured first-page readiness at
  207 ms in Chromium and 344 ms in Firefox on the local fixture; search took
  63 ms and 54 ms respectively. Heap reporting was available in Chromium
  20,500,000 bytes and unavailable in Firefox.
- KNOWN LIMITATIONS: the backend renderer is the controlled ReportLab profile,
  not a Chromium print pipeline; the current corpus still has no admitted
  official PDF bytes. Exact evidence mapping is PDF-04 work.
- UNRELATED WORK PRESERVED: V5/V5.1 workbench behavior, retrieval/generation,
  ingestion, corpus/index/Qdrant data, and existing dirty audit artifacts were
  preserved. The test-only PDF fixture is synthetic and does not touch `data/`.
- OWNED PROCESSES: browser preview processes were task-owned and cleaned after
  the focused runs; no persistent project listener was retained.
- EXACT NEXT TASK: `PDF-04` — expose the hash-bound mapping sidecar and exact
  PDF evidence-location contract.

## PDF-04 — Exact PDF mapping sidecar and location API

- TASK ID: `PDF-04`
- STATUS: [x] COMPLETE
- FILES CHANGED: `src/api/pdf_representation.py`, `src/api/pdf_generator.py`,
  `src/api/app.py`, `tests/test_pdf_pipeline.py`,
  `frontend/src/types.ts`, `frontend/src/lib/api.ts`,
  `frontend/src/lib/readerLocationView.ts`, and this file.
- FILES CREATED: none beyond the PDF contract/generator files already recorded
  in PDF-01/PDF-02.
- FILES REMOVED: none.
- REPRESENTATION CONTRACT EFFECT: mapping manifests now bind
  `representation_id`, document/source identities, source content hash,
  source-set/document revisions, artifact key/hash, and mapping-manifest ID.
  Coordinates are PDF points with explicit generated-page semantics.
- API EFFECT: added document-bound `/pdf/mapping` and
  `/pdf/mapping/location` routes. Location resolution requires chunk ID/hash
  and source/document revisions; it returns exact, ambiguous, unavailable, or
  stale states instead of guessing.
- STORAGE EFFECT: mapping JSON is atomically promoted beside the PDF and is
  rejected when its identity or artifact hash differs. Status/content routes
  now detect missing or hash-corrupted bytes rather than reporting a false
  available artifact.
- PROVENANCE EFFECT: source text remains canonical. A PDF rectangle is usable
  only when the complete indexed chunk matches one source interval and aligns
  with complete mapped source blocks; page coordinates never replace source
  document/revision identity.
- SECURITY EFFECT: artifact keys remain path-safe; the API resolves chunks
  from the current document index and rejects traversal, mismatched hashes,
  stale revisions, missing sidecars, and corrupted bytes.
- FRONTEND EFFECT: typed PDF location responses can enter the same reader
  location validation seam as Structured and Normalized without changing their
  existing contracts.
- MAPPING EFFECT: wrapped paragraphs yield multiple rectangles; partial,
  repeated, and cross-boundary matches remain unhighlighted or ambiguous.
- TEST COMMANDS / RESULTS:
  - `.venv\Scripts\python.exe -m pytest -q tests/test_pdf_pipeline.py` — PASS, `21 passed`, `1 warning`.
  - `.venv\Scripts\python.exe -m pytest -q tests/test_pdf_pipeline.py tests/test_original_viewer.py tests/test_structured_document.py tests/test_structured_location.py tests/test_api.py` — PASS, `103 passed`, `54 warnings`.
  - `bun run test -- --run src/lib/api.test.ts src/components/workbench/DocumentPane.test.tsx` — PASS, `2 files / 7 tests`.
- BROWSER VALIDATION: the sidecar-backed exact overlay is exercised by the
  PDF-05 browser fixture after this API phase.
- PERFORMANCE OBSERVATION: exact location resolution is local and bounded by
  the indexed chunk lookup plus one whitespace-literal source match; no remote
  acquisition or retrieval rerun is introduced.
- KNOWN LIMITATIONS: mapping is block/line-granular rather than
  character-granular, and the current source inventory has no official-PDF
  pagination to compare against.
- UNRELATED WORK PRESERVED: retrieval/reranking/model/index/corpus/generation
  semantics and ignored `data/` artifacts were not changed or regenerated.
- OWNED PROCESSES: none after backend test completion.
- EXACT NEXT TASK: `PDF-05` — synchronize exact PDF evidence with the shared
  reader state, add truthful metadata/fallback UI, and remove the fabricated
  viewer path.

## PDF-05 — Evidence synchronization, metadata, and responsive truthfulness

- TASK ID: `PDF-05`
- STATUS: [x] COMPLETE
- FILES CHANGED: `frontend/src/components/DocumentWorkspace.tsx`,
  `frontend/src/components/ContextPanel.tsx`,
  `frontend/src/components/workbench/DocumentPane.tsx`,
  `frontend/src/lib/readerLocationView.ts`,
  `frontend/src/lib/readerLocationView.test.ts`,
  `frontend/src/components/workbench/DocumentPane.test.tsx`,
  `frontend/src/styles/document-reader.css`, `frontend/e2e/fixtures.ts`,
  `frontend/e2e/pdf-viewer.spec.ts`, and this file.
- FILES CREATED: no new production component; the shared existing DocumentPane
  remains the composition owner.
- FILES REMOVED: `frontend/src/components/workbench/WorkstationDocumentViewer.tsx`,
  the pre-existing fabricated fixed-page/Apple-data viewer. It had no remaining
  imports after ContextPanel was switched to the real DocumentPane.
- REPRESENTATION CONTRACT EFFECT: evidence stays selected across Structured,
  Normalized, and PDF representation changes. PDF metadata discloses derived
  versus official type, page semantics, status, source/revisions, renderer,
  page count, and advanced artifact identity.
- API EFFECT: DocumentWorkspace requests the exact bound PDF location only for
  the active current manifest/source identity and reports resolving, resolved,
  stale, unavailable, or error through the existing reader-session seam.
- STORAGE EFFECT: no new browser persistence or evidence schema; the selected
  source remains transient and the existing evidence store is untouched.
- PROVENANCE EFFECT: exact PDF rectangles are painted only after client-side
  identity validation of chunk/hash/document/source/revisions/artifact and
  non-empty rectangles. Stale/unavailable responses preserve the source and
  show the reason without painting an approximate mark.
- SECURITY EFFECT: SEC source links in metadata are displayed only when they
  pass the existing `https://www.sec.gov/` allowlist; arbitrary source URLs are
  not turned into viewer inputs.
- FRONTEND EFFECT: the four-pane/dock/drawer compositions share one real PDF
  path. Responsive remounts preserve the selected representation through the
  workbench controller instead of resetting to Structured.
- MAPPING EFFECT: verified amber overlays support multi-rectangle and
  multi-line locations; unavailable/ambiguous/stale mappings remain visible as
  truthful status banners and Structured/Normalized remain safe fallbacks.
- TEST COMMANDS / RESULTS:
  - `bun run test -- --run --reporter=dot` — PASS, `60 files / 295 tests`.
  - `bun run lint` — PASS, `tsc --noEmit`.
  - `bunx playwright test e2e/pdf-viewer.spec.ts --project=chromium --workers=1` — PASS, `1/1`.
  - `bunx playwright test e2e/pdf-viewer.spec.ts --project=firefox --workers=1` — PASS, `1/1`.
- BROWSER VALIDATION: screenshots were captured at 1440×900,
  1920×1080, and 720×900 in `frontend/.audit-runtime/`. Wide captures show
  the PDF canvas, exact amber overlay, generated-page label, find results, and
  selected evidence; the narrow capture keeps PDF selected and exposes a
  responsive toolbar without page-level overflow.
- PERFORMANCE OBSERVATION: local fixture first-page/search measurements remain
  207/63 ms in Chromium and 344/54 ms in Firefox; Chromium reported a
  20.5 MB heap sample, while Firefox did not expose heap telemetry.
- KNOWN LIMITATIONS: the renderer remains ReportLab rather than Chromium, the
  mapping is block/line-granular, and official PDF admission is not present in
  the current HTML-only corpus.
- UNRELATED WORK PRESERVED: conversation seed behavior, query/SSE, retrieval,
  generation, model, prompt, index, Qdrant, acquisition, persistence, and
  corpus artifacts remain outside this change.
- OWNED PROCESSES: focused browser previews were cleaned; no task-owned
  listener remains.
- EXACT NEXT TASK: `PDF-06` — perform final repository/browser/security/
  performance closure and record the complete handoff.

## PDF-06 — Final PDF representation closure

- TASK ID: `PDF-06`
- STATUS: [x] COMPLETE
- FILES CHANGED: `README.md`, `.env.example`, `PROJECT_STATE.md`,
  `docs/frontend/DESIGN.md`, `docs/frontend/FRONTEND_CONTRACT.md`,
  `docs/frontend/V5_WORKBENCH_CONTRACT.md`, and this file.
- FILES CREATED: no new runtime files; ignored visual audit screenshots remain
  under `frontend/.audit-runtime/` for local inspection.
- FILES REMOVED: none beyond the fabricated viewer removal recorded in PDF-05.
- REPRESENTATION CONTRACT EFFECT: public/project docs now describe the
  optional document-bound `OFFICIAL_PDF`/`DERIVED_PDF` surface, generated-page
  semantics, exact-only mapping, lifecycle statuses, and official-PDF absence
  in the current corpus.
- API EFFECT: environment documentation exposes optional PDF generation,
  artifact-root, timeout, and concurrency settings. No retrieval, generation,
  model, index, corpus, or streaming API was changed.
- STORAGE EFFECT: PDF artifacts remain git-ignored under `data/generated/pdf`;
  no repository `data/` artifact was deleted, regenerated, moved, or committed.
- PROVENANCE EFFECT: the final handoff records source/document/revision/hash
  identity as canonical and clearly labels ReportLab pages as generated
  representation pages rather than official SEC pagination.
- SECURITY EFFECT: final checks cover URL/path/HTML rejection, safe artifact
  keys, source revalidation, atomic promotion, hash-bound content/mapping,
  stale revisions, corrupt/missing artifact states, SEC-link allowlisting, and
  hermetic browser network blocking.
- FRONTEND EFFECT: the real PDF.js path is documented as optional and the
  Structured/Normalized fallback remains authoritative when PDF is unavailable.
- MAPPING EFFECT: final docs and tests preserve exact-only behavior; no fuzzy
  nearest-page or approximate highlight was introduced.
- TEST COMMANDS / RESULTS:
  - `.venv\Scripts\python.exe -m pytest -q` — PASS, `791 passed`, `188 warnings`.
  - `bun run test -- --run --reporter=dot` — PASS, `60 files / 295 tests`.
  - `bun run lint` — PASS, `tsc --noEmit`.
  - `bun run build` — PASS, 2,015 modules transformed.
  - PDF-focused Chromium and Firefox browser tests — PASS, `1/1` each.
  - The attempted combined legacy `app.spec.ts` + `regression.spec.ts` + PDF
    run exposed existing seeded-demo/template expectations before reaching the
    PDF case (overview expected the empty landing copy while the app seeded the
    sample conversation; template buttons were consequently absent). That run
    was stopped after the baseline failures; the isolated PDF test is the
    authoritative PDF browser gate and passed in both engines.
- BROWSER VALIDATION: PDF.js rendered valid bytes in Chromium and Firefox;
  page/zoom/find/download/fullscreen controls were mounted; exact evidence
  was labeled Verified; screenshots were visually inspected at the three
  required widths.
- PERFORMANCE OBSERVATION: first page/search were 207/63 ms in Chromium and
  344/54 ms in Firefox on the hermetic one-page fixture. Backend local fixture
  generation previously measured 72 pages, 170,516 bytes, 1,515/1,515 mapped
  blocks, and 279.9 ms in a temporary store; this is an observation, not a
  production SLA. Native browser-chrome zoom remains a manual gate.
- KNOWN LIMITATIONS: current corpus inventory is 50 `.html` + 1 `.htm` and no
  official PDF/XML/XSL source; ReportLab is the controlled renderer because
  the backend has no browser runtime, so derived pages are not official SEC
  pagination; mapping is block/line-granular; Firefox does not expose the
  optional heap metric; the legacy seeded-demo E2E slice remains outside this
  PDF closure and was not altered.
- UNRELATED WORK PRESERVED: all pre-existing V5/V5.1 dirty files, audit
  outputs, harness files, desktop processes, and ignored `data/` artifacts were
  preserved. No commit, deploy, benchmark promotion, retrieval redesign, or
  corpus/index rebuild was performed.
- OWNED PROCESSES: final listener audit is required to be empty for project
  ports `3000`, `4173`, `4175`, `5173`, `8000`, `8765`, and `8766`; browser
  preview processes from this task were cleaned.
- EXACT NEXT TASK: none for the approved PDF-00 through PDF-06 scope. A future
  evolution should separately decide whether to add trusted official-PDF
  admission or a backend Chromium renderer; neither is implied by this closure.
