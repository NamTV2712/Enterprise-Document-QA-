# Research Workspace UX Recovery — execution plan

Status: PLANNED, not implemented or visually accepted.
Date: 2026-09-07.
Baseline inspected: `95e6118`, branch `codex/bilingual-research-workspace`, with an existing uncommitted change to `frontend/src/index.css`.

## Objective

Deliver a readable, responsive and fast SEC research workspace inspired by the supplied dark and light reference images. Prioritize question -> answer -> citation -> source excerpt. Simplify navigation and remove redundant presentation. Preserve reliable conversation storage and the existing grounded-answer contracts.

This is a new UX acceptance round. Historical M0-M11 implementation/test receipts are evidence of prior checks, not acceptance of the current rendered interface. Do not repeat historical provider campaigns merely to make this round look complete.

## Evidence and diagnosis

This planning audit read the supplied prompt, inspected the four supplied images, reviewed current source, recent commits, the latest project-state entries, TODO entries and the previous improvement report. No browser profiling or new test run was performed for this plan. Performance causes below require measurement.

| Finding | Evidence | Consequence / next investigation |
|---|---|---|
| Header overload | `WorkspaceHeader.tsx`: duplicated product branding, seven desktop destinations, status, command, theme, language, help and reset controls | Move global navigation out of the header; preserve access without hidden horizontal scrolling |
| Navigation is deliberately clipped | `styles/components.css`: first header child has `overflow:hidden`; nav uses horizontal scrolling with hidden scrollbar | Existing containment prevents overlap but does not provide discoverable navigation |
| Current CSS differs materially from tested source | Working-tree `index.css` has 1,067 added lines before the four stylesheet imports, including duplicate theme declarations, hardcoded colors, glow/blur and animation rules | Capture the diff; inspect actual Vite output and computed styles before consolidating. Do not assume the imports or cascade behave as intended |
| Theme aliases conflate roles | `tokens.css` maps shade utilities to role tokens, including slate-900 to surface and slate-300 to border | Audit rendered text/background pairs; token-pair arithmetic alone cannot prove component contrast |
| Failed load is shown as empty search | `DocumentExplorerPanel.tsx` renders error and, independently, an empty list and pagination | Introduce explicit mutually exclusive states and actionable retry |
| Document search can become too narrow | Filter grid reserves fixed 180px and 220px columns while the sidebar takes workspace width | Size the filter bar by available container space, not only window breakpoints |
| Research controls persist on unrelated pages | App mounts Sidebar independently of active document/tool view | Separate global navigation from query-specific controls |
| Evidence selection has separate ownership | App supplies latest sources to `EvidenceWorkspaceRail`; the rail owns a local numeric selection, while messages retain source panels | Bind evidence selection to answer/message and stable source identity; avoid duplicate expanded sources |
| Existing performance receipt is narrow | `regression.spec.ts` measures warmed Library filtering of 100 x 100 messages | Profile startup, long assistant messages, streaming, persistence, theme and resizing separately |
| Some visual checks have limited coverage | General axe scan disables contrast; a separate conversation contrast test exists; screenshot coverage emphasizes overview/conversation/Library | Add Document Explorer, offline and long-label coverage; review actual images as well as assertions |
| Provider isolation already exists | `src/generation/provider_policy.py` supports strict `key5_only` | Reuse it across server, diagnostics and test runners; do not build another key pool |

The screenshots confirm visible clipping, unreadable dark labels and contradictory offline/empty feedback. They do not establish whether the network failure is backend downtime, URL configuration, CORS or tunnel failure, or whether lag comes from rendering, storage or network latency.

## Product decisions

### Keep, move and remove

| Surface | Decision |
|---|---|
| Chat | Primary destination, including the initial empty state and a few useful sample questions |
| Documents | Primary destination with compact search/filter/list and selected excerpt detail |
| Library | Primary destination; preserve search, bookmarks, notes, export/import, read-only and multi-tab behavior |
| Retrieval Lab, Evaluation, Analytics, System | Keep existing capability under a collapsed Tools group; lazy-load; remove from the main header |
| Overview | Fold useful introductory content into empty Chat; retain old navigation compatibility where necessary |
| Company, section, retrieval options | Context controls attached to Chat composer; advanced settings in a popover/drawer |
| Brand and New Chat | One brand location; one clearly discoverable primary New Chat action per layout |
| Theme, locale, help | Compact accessible header menu; keep preferences and shortcuts |
| Sources | One active source surface for the selected answer; inline citation buttons remain in answers |
| Metrics and pipeline | Compact optional details; show only actual available timings and states |
| Decorative cards, repeated headings/badges, persistent system metrics | Remove redundant presentation after checking usage; retain meaningful functionality elsewhere |
| Account avatar, plans/storage quota, Users/API Keys/Models menu, upload/Web controls from references | Do not add unless backed by an existing authorized capability; these are illustrative reference elements |
| Full PDF page viewer | Defer. Current data supports excerpts and safe source URLs, not verified PDF pages/bounding boxes |

Hiding or relocating a feature must not delete saved notes, bookmarks, variants, exports or schema compatibility. Make a feature-to-destination inventory before removing UI entry points.

### Target layout

- Global header: approximately 52-56 CSS px; current context/title on the left; compact search/commands and connection/settings on the right. No seven-item horizontal navigation.
- Desktop sidebar: approximately 208-224px; icon + label navigation, recent conversations and New Chat. Optional collapsed rail around 56px. Clamp and version saved widths so old wide preferences cannot break the new shell.
- Large desktop: navigation | answer | sources | excerpt reader, only when all minimum widths fit. Suggested minimums: answer 480px, sources 240px, reader 300px. Include gutters and sidebar when deciding fit.
- Medium desktop: navigation | answer | combined sources/reader inspector with tabs. Never squeeze the answer simply to reproduce the four-column reference.
- Tablet: collapsed navigation, primary content, inspector drawer. Mobile: one main surface with source/reader sheet, focus return and usable on-screen-keyboard layout.
- Documents and Library use their own content layouts. Do not reserve an empty evidence rail outside Chat.
- Composer belongs to the Chat column; source panes do not force an excessively wide input. Preserve draft while changing views.
- Source titles can use a two-line clamp plus accessible full-title disclosure. Navigation labels and primary actions must remain readable; hidden overflow is not the acceptance solution.
- Use container width for internal filter layouts. Document search gets useful width first; filters wrap or move into a filter popover when necessary.

### Design system

Use existing semantic token architecture; consolidate rather than layer a third palette. Reference starting colors are light canvas #F6F8FB, white surface, text #172033, secondary #526174, blue #2563EB; dark canvas #08111E, surface #0D1828, raised #111F32, text #EDF3FB, secondary #A8B6C9, blue #3B82F6. Validate actual pairings before adopting values.

Use one sans-serif UI family, 14px normal interface text, 15-16px answer text, 12-13px readable metadata, 20-24px page headings. Use 4/8/12/16/24 spacing, mostly 6-10px radii, subtle borders and restrained elevation. Desktop controls generally 32-36px; touch targets approximately 44px. Avoid perpetual decorative animations, glowing borders, large blurred surfaces and oversized nested cards.

Separate text, surface, border and icon roles, including success/warning/error/disabled states. Do not globally redefine a shade used both for text and backgrounds as one semantic role. Query blue, embedding teal, retrieval cyan, reranking violet and generation green are optional small technical accents, not full-panel fills. Do not copy unreadably small metadata from the reference.

## Ordered phases and completion gates

### P0 — Reproduce, inventory and preserve baseline

1. Read AGENTS, current PROJECT_STATE and README; inspect status/diff and existing processes before starting servers.
2. Preserve the current uncommitted CSS diff in a recovery artifact outside tracked product source. Record its hash and provenance; never silently discard it. Compare committed and current styling using an isolated checkout if needed.
3. Capture app version/commit, dirty diff hash, built asset hashes, CSS viewport, device scale, browser zoom, theme, locale and backend mode for each baseline screenshot.
4. Reproduce supplied Document Explorer screens, then empty Chat, populated Chat, Library and Tools. Check both fresh preferences and existing persisted widths/themes.
5. Diagnose API offline via configured public base URL, health/readiness response, browser network/CORS and tunnel status. Do not print secret files. Separate HTTP availability from pipeline readiness.
6. Create `docs/design/UX_RECOVERY_AUDIT.md`: stable issue IDs, severity, reproduction, observed/expected behavior, source ownership, evidence and phase assignment. Cross-reference prior M4-M8 claims against observed behavior.

Gate: every reported symptom is reproduced or explicitly recorded as unverified with the missing condition. Record a clean baseline and dirty baseline separately. No performance cause is asserted without a trace.

### P1 — Establish reusable design and QA guidance

1. Use the available skill-creator workflow to author a concise repo skill at `.agents/skills/rag-ui-ux/SKILL.md`.
2. Add focused references: `design-system.md`, `ui-patterns.md`, `visual-qa.md`; add `docs/design/design.md` as the single product design decision record.
3. Copy the supplied dark/light target images to durable repo skill assets; retain current screenshots as baseline evidence. Do not depend on Temp attachment paths for future execution.
4. Skill workflow: inspect -> implement one coherent slice -> run built app -> inspect rendered result -> critique -> fix -> inspect again -> acceptance receipt. Read relevant references before edits.
5. Add only a short recurring frontend rule to AGENTS. Keep milestone details in project state/design docs.
6. Write a feature destination map, responsive width budget and user journeys. Avoid adding a component framework or plugin merely for this refactor.

Gate: guidance has concrete observable checks and matches this repository's actual excerpt, storage and provider capabilities. No unspecified external plugin dependency.

### P2 — Repair CSS ownership and establish primitives

1. Determine exactly how current import order is compiled. Consolidate into tokens/components/base/motion; entry stylesheet only orchestrates imports.
2. Reconcile useful parts of the existing CSS diff with the design target. Keep recoverable evidence of the original diff and document what was superseded.
3. Replace conflicting shade aliases and hardcoded overrides with role-based styles in affected components. Search call sites before changing aliases; migrate incrementally.
4. Standardize Button, IconButton, Input, Select, StatusBadge, Tabs, Popover/Dialog and empty/error/loading presentation, reusing existing primitives where adequate.
5. Fix theme menu keyboard navigation to advance from the focused item, not repeatedly from the selected preference. Verify Escape/focus return.

Gate: one authoritative palette; no unexpected unresolved tokens; readable actual labels/buttons/statuses in both themes; reduced motion honored; no CSS import warnings. Visually inspect primitives in the real shell.

### P3 — Replace overloaded shell and navigation

1. Implement primary sidebar destinations and collapsed Tools group. Fold Overview into empty Chat.
2. Remove duplicate branding and navigation from header; keep status and settings compact and reachable.
3. Move query controls out of global sidebar into Chat context controls. Keep drafts, selected filters and existing Library operations intact.
4. Implement container-aware layout and panel state persistence with versioning/clamping. Add Reset layout inside settings, separate from New Chat.
5. Define scroll ownership so content panes scroll without nested traps or fixed elements covering text. Check viewport height and mobile keyboard behavior.

Gate: all destinations reachable without hidden horizontal navigation; no truncated primary labels at required viewport/locale combinations; keyboard and touch navigation work; changing layout does not mutate conversations.

### P4 — Connection and document-state recovery

1. Normalize UI errors into unavailable/timeout/server/rate-limit/unauthorized where observable. Browser fetch errors cannot reliably distinguish CORS from downtime; put diagnostics in technical details.
2. Share connection state across the header and views. Use checking, loading pipeline, ready, unreachable and retrying consistently; remove unrelated green health cues.
3. Model Documents as loading, success, empty corpus, no matches, error and stale cached results. Do not show no-matches or pagination for an initial failed fetch.
4. Provide Retry and recovery help. Retry refreshes actual requests, not just dismisses the banner. Separate list errors from selected-document excerpt errors.
5. Preserve existing abort/stale guards and debounce. Bound caches by count/TTL and invalidate when backend/corpus identity changes; preserve usable stale data with an explicit label.
6. Fix narrow search input, long metadata wrapping, document selection resets and chunk pagination. Use server totals if present; otherwise do not imply known total pages.
7. Replace filesystem/internal implementation copy with task-oriented EN/VI text.

Gate: reproduce and resolve screenshot failure states; test offline -> ready without reload, ready -> offline, timeout, empty, no-match, slow response, rapid filter changes and retry. Saved Library remains usable offline.

### P5 — Chat, citations and inspector

1. Make answers the visual focus; use compact metadata and subordinate Copy/Bookmark/Notes/Feedback actions. Put infrequent actions in an accessible menu.
2. Keep company/section summary near composer with expandable advanced retrieval settings; explain disabled sending inline while preserving drafts.
3. Own evidence selection in a shared model keyed by message ID + stable source ID. Citation click selects the correct answer, source and excerpt, including earlier messages and repeated source numbers.
4. Render a single expanded source/reader surface per layout. Preserve source numbering across filtering/sorting and reloads. Explain score as retrieval score, not probability/confidence.
5. Open the selected excerpt, highlight matching text only where real offsets/text support it, and expose safe SEC links. Identify previews/truncated text honestly; do not invent PDF page numbers.
6. Keep selection and scroll stable during streaming and filtering; reset stale selection when its answer changes. Keyboard activation opens the inspector and returns focus on close.
7. Show real total latency/stages only when provided; detailed traces remain expandable. Do not manufacture a five-stage timing diagram from incomplete metadata.

Gate: a reader can ask, read, open citation, inspect the matching excerpt, copy/save evidence and return to the answer without losing context. Verify older messages, long answers, streaming interruption, stop and retry.

### P6 — Library, tools and utility cleanup

1. Keep searchable conversations, bookmarks, notes and backup/restore prominent in Library; move diagnostic identifiers into details.
2. Preserve schema v4 compatibility, tombstones, storage limits, write locks, expired sessions and multi-tab handoff.
3. Keep Tools functional but secondary and lazy-loaded. Standardize their headers, tables, empty/error states and long-label behavior.
4. Remove only presentation redundancy identified in the feature map. Retain access to answer variants and collections if existing users have saved data.
5. Reconcile keyboard shortcuts and Help; ensure EN/VI uses consistent task vocabulary and no essential untranslated strings.

Gate: every retained feature has a destination and verified path; backup round-trip and existing Library reliability tests pass. No saved user content is removed as UI cleanup.

### P7 — Measure and fix interaction latency

1. Profile a production build, not only development mode. Record hardware/browser, dataset, warm/cold state, throttling and backend mode.
2. Capture browser performance traces and React profiling for typing during streaming, opening a long chat, theme/view changes, source selection, resizing, Library search and persistence. Attribute long tasks before edits.
3. Inspect whole-App updates per stream batch, repeated Markdown parsing, unstable callbacks, repeated source panels, synchronous serialization, full-list rendering, continuous blur/animation and repeated API traffic.
4. Apply measured fixes: stable completed-message props, isolated stream state, bounded batch updates, cached derived data, incremental persistence. Add virtualization only where traces justify it; preserve browser find, focus and citation navigation.
5. Maintain scroll anchoring: stop automatic bottom scrolling when the user reads history; preserve position across inspector opening and updates.
6. Separate UI response, API retrieval, first-token and generation times. Do not label provider/network latency a rendering improvement.

Proposed local budgets (acceptance targets, not existing results):

| Scenario | Target and method |
|---|---|
| Typing/selection/theme/command | p95 input-to-next-paint <=100ms on recorded unthrottled reference device, >=30 measured actions after warmup |
| Library search | p95 <=200ms with existing 100 x 100 dataset, plus interaction trace rather than runner wall time alone |
| Warm view switch | p95 <=200ms excluding required network fetch; loading feedback within 100ms |
| Long chat | At least 200 messages with realistic Markdown/sources, total content within existing storage limit; no lost focus/scroll and no recurring app-attributable >50ms long tasks during steady interaction |
| Streaming | Sustained fixture for 60s while typing, scrolling and selecting sources; no dropped final text, input starvation or continually growing queued work |
| Memory/cache | No monotonic retained growth across 20 repeated open/close/filter cycles after settling; bounded caches and listener cleanup |

Report cold startup and 4x CPU stress results separately. If a target fails, record the trace and fix or report the unresolved gate; do not silently relax thresholds. Fix shared backend metadata/timeout issues only when traced; preserve retrieval defaults and Qdrant single-worker constraints.

### P8 — Visual, accessibility and integration acceptance

1. Automate geometry checks for primary controls, overlap, clipping, document-level horizontal overflow, composer coverage and visible focus. Do not accept merely nonzero bounding boxes or DOM presence.
2. Cover CSS widths 390, 768, 1024, 1280, 1440, 1920 and the screenshot-equivalent effective width; include a short 1366x768 laptop window. Core views: empty/populated Chat, Documents, Library. Test Light/Dark x EN/VI; pairwise additional tool/error states to avoid pointless matrix explosion.
3. Inspect real browser zoom at 125%, 150% and 200% separately from CSS viewport simulation and device scale. Record exact mechanism; do not label viewport resizing as browser zoom.
4. Review screenshots after rendering at least the reference-sized light/dark Chat and Documents, narrow layout, offline state and long Vietnamese labels. Iterate on hierarchy/spacing/readability, not only assertions.
5. Run rendered contrast/accessibility scans on Documents, navigation, menus, offline/error states and Chat; normal text >=4.5:1, large text and required non-text controls >=3:1. Visually check alpha/background combinations and disabled-state readability.
6. Run relevant unit tests and build/typecheck, then full frontend and browser gates once the source is stable. Run HTTP/SSE integration for contract paths; run backend tests if backend changed.
7. Validate fresh storage and realistic existing storage; test reload, corrupted backup rejection, read-only sessions and multi-tab ownership. No browser reset may destroy the user's real saved conversations.

Gate: zero unresolved blocking/high-severity UX defects, all required views/states accepted, and evidence bound to the final source/diff/assets. A screenshot saved without visual review is not visual acceptance.

### P9 — KEY5-only live smoke

1. Reuse `GROQ_KEY_POLICY=key5_only` for every Groq-backed server, subprocess, diagnostic and judge call. Verify safe key-slot metadata, never the key value. Fail closed if KEY5 is unavailable; no fallback to other keys.
2. Perform one readiness check and a small real EN/VI smoke set after offline UI gates: single-company question, comparison, and insufficient-evidence case; inspect streamed result and citation interaction in the browser.
3. Record each actual provider attempt, model, role, timing and outcome in a new ledger. Reuse old campaign receipts only as historical evidence. Pure UI work does not require a full N=30 or repeated judge campaigns.
4. Honor Retry-After for transient throttling with bounded retries and cancellation. Terminal quota/auth errors leave live acceptance incomplete; continue independent UI work and report the exact blocker. Large quota is not proof that every model/window is available.
5. Do not invent a total 120/2000-attempt cap as a user quota. Keep bounded scenario/retry limits to avoid runaway calls, and document them as test protocol limits.

Gate: required real scenarios work with KEY5 provenance, or live acceptance is explicitly BLOCKED/INCOMPLETE. Mocked success never substitutes for real API readiness.

### P10 — Final handoff

1. Create `docs/UX_RECOVERY_REPORT.md` with P0-P10 status, issue closure, before/after screenshots, final source/diff/assets, benchmark methodology/results, test receipts and remaining limitations.
2. Update README/frontend README for the new navigation, local startup, backend connectivity and shortcuts. Add a new project-state entry rather than rewriting historical receipts.
3. Leave a verified local preview with its exact URL and startup command; identify whether it uses real backend or explicit fixtures.
4. Do not call the production URL updated merely because local work is complete. Merge/deployment are separate from this UX Goal unless the user later includes them.

Final gate: all mandatory phases accepted, visual evidence reviewed, local preview verified and real provider outcome honestly recorded. If an external blocker prevents a phase, report partial completion and the exact unresolved gate rather than marking the whole Goal complete.

## Goal prompt to paste

Execute `docs/UX_RECOVERY_GOAL_PLAN.md` from P0 through P10 in the current Enterprise_Document_QA repository. Begin by re-reading the plan and repository instructions and verifying the current worktree; preserve the pre-existing CSS change and user data. Create and use the repo rag-ui-ux skill in P1, then implement the responsive sidebar/header, semantic themes, explicit connection/document states, synchronized citation inspector, utility simplification and measured performance fixes. Treat the supplied reference images as the visual direction, with only real existing capabilities. For each phase record issue IDs, changes and concrete acceptance evidence. Run the production frontend, visually inspect actual rendered Light/Dark and EN/VI states, critique and iterate; builds and historical passing test counts are not visual acceptance. Use only GROQ_API_KEY5 with GROQ_KEY_POLICY=key5_only for any Groq request, including server subprocesses and judges, without printing secrets or falling back to other keys. Keep canonical corpus/index, official benchmark and saved conversations intact. Do not launch repeated provider campaigns for UI-only changes. Continue independent work through provider/network interruptions and report any unresolved live gate accurately. Finish with the final report, before/after evidence, measured performance, verified local preview URL and P0-P10 status. Do not claim Goal completion until mandatory acceptance gates pass. Production merge/deployment is outside this Goal.
