# FINAL EXECUTION PLAN — PLAN V2 ADDENDUM

This is the authoritative implementation checkpoint for the UI/UX polish and product-discoverability cycle. It extends existing P0–P4 work and must not restart or rewrite stable retrieval, ranking, generation, citation, source-reader, persistence, or Qdrant behavior.

## Locked boundaries

- Keep React, TypeScript, Tailwind, installed Lucide, existing registries, tokens, primitives and state owners.
- No new framework, state library, query library, endpoint, conversation-schema migration, Docker/provider/deployment work, corpus rewrite, fake data/metrics/coverage/stages, full filing/PDF viewer, or navigation drag-resize.
- Preserve conversations, variants, citations/source identity, indexed-excerpt viewer, notes, bookmarks, collections, Library, Search, Documents, backup/import, multi-tab protection, streaming and cancellation.
- Navigation modes: expanded 216px, compact rail 56px, responsive drawer 280px. The existing ContextPanel splitter remains separate.

## Current evidence/status

- Existing P2.4–P2.8, P3.1–P4.2 implementations and receipts exist, but the old checklist/receipts disagree. Retain history and reconcile it; do not treat receipt-only browser claims as fresh proof.
- P3.2 focused persistence/evidence behavior is verified. P3.1 proves ContextPanel width persistence, not pins; pins remain deferred.
- P4.2 Chromium full-suite persistence/pending-request failures remain `[!]` until two complete retry-free one-worker runs prove resolution. Isolated reruns are insufficient.
- Start with `V2-A01.1`, then execute exactly: `A06.1 → A01.2 → A02.1 → A02.2 → A03.1 → A03.2 → A04.1 → A04.2 → A05.1 → A05.2 → A05.3 → A06.2`.

## Task contracts

### V2-A01.1 — Reconcile checkpoint and protect the starting worktree

Record branch/HEAD, dirty boundary and current status in `docs/implementation-progress.md`; append reconciliation of checklist versus receipts; mark old Chromium conclusion unresolved; keep pins deferred. Documentation only. Validate `git status --short`, `git diff --stat`, and the focused existing evidence. Receipt must include starting binding, files, summary, commands/results, browser evidence, unresolved issue, rollback slice and next task.

### V2-A06.1 — Resolve the pre-existing Chromium persistence gate

Inspect `frontend/e2e/regression.spec.ts`, `fixtures.ts`, `playwright.config.ts`, `frontend/src/hooks/useConversationLibrary.ts`, `frontend/src/lib/conversationStore.ts` and traces. Run Chromium full suite one worker/retries 0, trace reload/fallback, pending deletion and writer handoff. Fix only an evidenced race; do not add sleeps, skip assertions or declare runner-only. Pass two complete runs before `[x]`; otherwise `[!]`. Do not touch schemas.

### V2-A01.2 — Centralize semantic icons and feature descriptions

Create `frontend/src/lib/semanticIcons.ts` as the only semantic-key-to-Lucid mapping. Extend `frontend/src/lib/workspace.ts` metadata with description keys/accent family; make `commandRegistry.ts`, `Sidebar.tsx`, `CommandPalette.tsx`, template cards and tool introductions consume it. Use distinct Research/Library and Evaluation/Analytics icons and consistent System/Documents icons. Verify installed exports and use only the fixed fallback mapping documented in the final plan; never add a dependency. Add registry parity tests.

### V2-A02.1 — Implement shared color and interaction states

Extend `frontend/src/styles/tokens.css` and `components.css` with domain foreground/soft/hover/selected/pressed/border tokens for research, documents, retrieval, evidence, evaluation, analytics and system. Implement distinct default/hover/current/keyboard-active/focus-visible/pressed/disabled states; markers and outlines must not shift layout. Halo is limited to interactive icon containers; no permanent glow, `transition: all`, decorative pulse or color-only state. Honor hover capability, forced colors and `prefers-reduced-motion`.

### V2-A02.2 — Correct palette active-row and keyboard behavior

Use one accessible combobox/listbox model in `CommandPalette.tsx`: stable active descendant, input-owned focus, Arrow/Home/End/Enter/Escape, scroll active option into view, localized label/description/keyword filtering, pointer/keyboard parity and separate current-route indication. Preserve shortcut and ModalDialog focus restoration.

### V2-A03.1 — Add isolated navigation preference persistence

Create `frontend/src/hooks/useNavigationLayout.ts`. Store only raw `expanded` or `compact` at `sec_qa_navigation_layout_v1`; default expanded; ignore malformed values; do not delete old data; keep in-memory behavior on storage/quota failure; apply valid `storage` events without echo; breakpoint overrides never overwrite preference; do not include this key in backups.

### V2-A03.2 — Render expanded, compact and drawer navigation

Update `Sidebar.tsx`, `SidebarFooter.tsx`, `WorkspaceHeader.tsx`, `App.tsx` and sidebar CSS. Use one route tree. At ≥1280px honor expanded/compact; 1024–1279px effective compact with temporary drawer; 768–1023px drawer 280px; below 768px `min(280px, viewport-32px)`. Expanded labels remain readable in EN/VI and zoom; rail targets are ≥44px with tooltips and active marker; drawer reuses `ModalDialog`, traps focus, closes on Escape/backdrop/navigation, inert background and returns focus.

### V2-A04.1 — Compact overview and truthful corpus/scope state

Update `OverviewPanel.tsx`, `ChatInput.tsx`, `ScopeEditor.tsx`, App health wiring and i18n. Order: concise heading, real corpus summary or unavailable, current scope, offline/unknown, up to four templates, up to three real recents, collapsed guide, composer sibling. No configured-ticker fallback, fake freshness/coverage, duplicate scope editor or technical FastAPI copy. Add controlled scope-open plumbing without changing existing callers.

### V2-A04.2 — Explain sources, pipeline and tool capabilities

Use existing `ContextPanel.tsx`, `PipelineExecution.tsx`, `HelpDialog.tsx`, tool panels and registry descriptions. Explain indexed excerpts, source counts within retrieved sources, ranking score versus confidence, and “How this answer was built”. Missing metadata/stages stay unavailable; do not add endpoint or polling.

### V2-A05.1 — Define template parameters and block unresolved submissions

Extend `researchTemplates.ts` with deterministic parameter schemas/renderers. Required parameters: revenue company/year; growth company/metric/year1/year2; dependency companyA/companyB/metric with optional year; risk company; source audit company/claim with optional year; summary company/year. Validate searchable ticker, year 1900–current, metric 1–80, claim 1–240, distinct comparison companies, 5–500 final length and reserved placeholder tokens. Add one send-boundary guard preserving drafts and allowing arbitrary non-template bracketed text.

### V2-A05.2 — Add guided template customization

Create `frontend/src/components/TemplateQuestionDialog.tsx` using `ModalDialog`, `SelectField` and native labelled inputs. Selecting never sends, changes locale or immediately changes draft/scope. Snapshot conversation/draft/scope; Cancel/Escape/backdrop leaves them untouched; Apply atomically updates existing owners only after conflict validation and focuses composer. No generic form framework or persistence.

### V2-A05.3 — Connect identity-safe contextual commands

Extend the existing registry/palette with real callback commands: copy current answer, inspect current sources, save selected source, open scope, plus existing new conversation/Library/Search. Callback registration must carry and revalidate conversation/message/variant/source identity. Palette dispatches callbacks only; it must not own clipboard, evidence persistence or source resolution. Hide unavailable commands and surface errors after close.

### V2-A06.2 — Run final matrix and close the Addendum

Run the complete validation matrix on one unchanged binding; fix failures in the owning task only. Required gates: frontend lint/tests/build; Chromium one-worker full suite twice; Firefox; integration; backend pytest; diff check. Inspect Light/Dark, EN/VI, widths 1920/1440/1366/1280/1024/768/390/320, real browser zoom 100/125/150/200, all interaction states, online/offline/unknown/stale/loading/error, keyboard/drawer/palette focus, reduced motion, contrast, citation-reader, stop/late events, notes/bookmarks/backup/import/multi-tab/Library/Search/Documents, and performance budgets. Mark `[x]` only when every acceptance gate passes.

## Receipt and resume protocol

After every task update `docs/implementation-progress.md` with:

```text
Task ID / status:
Starting code binding:
Files changed:
Implementation summary:
Contracts preserved:
Commands run and exact results:
Rendered/browser checks performed:
Artifact paths:
Unresolved issue or “none”:
Rollback slice:
Next task:
```

Use `[x]` only for implementation plus required validation, `[-]` for partial, `[ ]` pending and `[!]` blocked. Future sessions use this file, this plan, current repository and `git status/diff`; no Plan V1 reread is required. If reality crosses a locked boundary, document the mismatch and stop that task for direction. Never reset/checkout/delete the dirty worktree.

## Definition of done

All subtasks are `[x]`; old checkpoint contradictions are reconciled; the Chromium gate has two complete retry-free passes; icon/state/theme/sidebar/overview/template/context-command contracts pass; all required browser/accessibility/performance/regression evidence is recorded; no deferred feature or locked backend/data boundary was added.
