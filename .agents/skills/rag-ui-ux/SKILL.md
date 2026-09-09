---
name: rag-ui-ux
description: >
  Product-aware UI/UX and frontend quality workflow for the Enterprise Document
  QA SEC research workspace. Use for React, TypeScript, Tailwind, layout,
  theme, navigation, Chat, citation, source reader, Documents, Search,
  Library, tools, responsive behavior, accessibility, performance, visual
  review, or UI recovery work.
---

# SEC Research Workspace UI/UX

This skill coordinates four complementary layers: product cognition from the
Codex UI/UX skill, deliberate visual direction from Anthropic frontend-design,
implementation discipline from the Codex frontend skill, and final UX/a11y
auditing from UI/UX Pro Max. They are references, not competing designers.
Repository instructions and this product contract always have priority.

## Before any frontend change

Read `AGENTS.md`, `PROJECT_STATE.md`, `README.md`,
`docs/frontend/DESIGN.md`, and `docs/frontend/FRONTEND_CONTRACT.md`.
For a broad change, read the relevant files in `references/`:

- `design-system.md` for tokens, hierarchy, component boundaries, and copy.
- `state-matrix.md` for loading, empty, error, stale, long-content, and
  read-only behavior.
- `visual-qa.md` for browser inspection, screenshots, geometry, accessibility,
  and performance evidence.

Complete this short thinking gate before editing:

```text
Project: SEC filing research and grounded QA workspace.
Surface type: research workbench, document reader, or developer tool.
Primary user task: ask or search, understand the result, verify evidence, and
save or continue the work.
First decision: choose the question/scope or the source to inspect.
Success: readable result, correct source selection, recoverable state.
Recovery: retry, change scope, open an older saved conversation, or inspect
technical details.
Mobile primary action: ask/search first; sources and tools become a drawer.
```

If the current code or screenshot contradicts this model, diagnose the
contradiction before styling.

## Product rules

- Preserve query/SSE contracts, grounded-answer behavior, Library schema and
  saved user content unless the task explicitly changes them.
- Treat the primary journey as `question -> answer -> citation -> source ->
  reader -> save/continue`.
- Keep user-facing copy concise and action-oriented. Put IDs, paths, raw JSON,
  model details, scores, and implementation explanations in details or Tools.
- Keep Chat, Documents, Search, and Library primary. Keep Retrieval Lab,
  Evaluation, Analytics, System, and Architecture behind Tools.
- Prefer one coherent surface over a wall of equal cards. Use progressive
  disclosure for filters, diagnostics, and advanced retrieval settings.
- Use the existing Vite/React/TypeScript/Tailwind/Lucide architecture. Do not
  add a visual component library or runtime diagram renderer just for polish.
- Use semantic tokens for surface, text, border, focus, and state. Do not put
  raw colors in components or map one alias to incompatible roles.
- Light/Dark must be designed together. Normal text must meet 4.5:1 contrast;
  state is communicated with text/icon as well as color.
- No hidden horizontal navigation, accidental page overflow, clipped labels,
  hover-only actions, or fixed bars covering content. Preserve browser zoom.
- Motion is short, interruptible, and meaningful. Honor reduced motion. Do not
  use glow, gradients, or animation to compensate for weak hierarchy.
- Tables browse and select. Details and editing belong in a drawer, panel, or
  focused flow.

## Working sequence

1. Inspect the current implementation and recent evidence.
2. Record the product cognition gate, information hierarchy, component tree,
   state matrix, responsive behavior, and five self-review risks.
3. Implement the smallest coherent slice with existing components and typed
   props. Keep unrelated worktree changes intact.
4. Run the production frontend build and open the real rendered app.
5. Inspect Light/Dark, EN/VI, target widths, long labels, empty/error states,
   keyboard paths, and the primary user journey.
6. Critique the rendered result, fix observed problems, and inspect again.
7. Run relevant unit, typecheck, build, browser, accessibility, and
   integration checks. Report the exact evidence and remaining risks.
8. Update the design contract only after a rule has been validated by the
   implementation.

## RAG-specific boundaries

- A citation is tied to its message/variant and stable source identity; never
  open the newest answer's source for an older citation.
- Retrieval score is a retrieval score, not an accuracy probability or model
  confidence. Never invent evidence-strength labels.
- Keep citation numbering stable while filtering. Missing source data is
  shown as unavailable; it is never silently replaced with another source.
- `/retrieval/inspect` is provider-free and may power Search or Tools. Do not
  call generation on every keystroke.
- Archify diagrams describe verified source topology. Do not add OCR, queue,
  Redis, workers, upload, or other infrastructure unless the repository proves
  it exists. Keep Archify HTML outside the Chat bundle and load it lazily.
- Any real Groq request in this project must use `GROQ_KEY_POLICY=key5_only`
  and `GROQ_API_KEY5`; fail closed rather than falling back to another key.

## Definition of done

The UI change is not complete when it merely compiles. It is complete only
when the user journey works, all relevant states have a recovery path, labels
remain readable at required widths and languages, keyboard/focus behavior is
usable, the real rendered result has been inspected, and the reported tests
cover the changed behavior.
