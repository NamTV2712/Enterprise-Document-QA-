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
