---
name: rag-ui-ux
description: >
  Improve or verify the Enterprise Document QA SEC research workspace frontend:
  user journeys, state ownership, evidence presentation, responsive layout,
  accessibility, and rendered browser quality. Use for React, TypeScript,
  Tailwind, Chat, Documents, Search, Library, citation, source-reader, or UI
  recovery work. Do not use for retrieval tuning, evaluation methodology,
  provenance resolution, or backend-only changes.
---

# SEC research workspace UI/UX

This is the project-specific product authority for the React/Vite workspace. It
preserves the SEC research workflow, grounded-answer behavior, citation identity,
Library data, and current component architecture. Supporting capabilities are
conditional: use `product-design:audit` for screenshot critique, the available
browser/computer-use capability for interaction evidence, `archify` for verified
architecture artifacts, and the RAG specialists for their owned boundaries.

## Use this workflow

1. Read `AGENTS.md`, `PROJECT_STATE.md`, `README.md`,
   `docs/frontend/DESIGN.md`, and `docs/frontend/FRONTEND_CONTRACT.md`.
2. Load the relevant references: `design-system.md`, `state-matrix.md`,
   `visual-qa.md`, `frontend-architecture.md`, and `document-workspace.md`.
3. Complete the task-semantics gate before styling: record the entry point,
   user intent, submitted scope or selected source, available evidence, primary
   action, resulting surface, success, and recovery. Labels and transitions
   must describe the operation actually being performed. A catalog action must
   not imply an answer or retrieved sources.
4. Record the information hierarchy, component tree, state matrix, responsive
   behavior, and five self-review risks. Identify the state owner, request
   owner, persistence boundary, identity key, notification lifetime, and scroll
   owner before editing affected UI.
5. Implement the smallest coherent typed change using existing Vite/React/
   TypeScript/Tailwind/Lucide patterns. Do not add a component library or
   runtime diagram renderer for polish.
6. Build the production frontend and inspect the real rendered affected
   journey. Check light/dark, EN/VI, target widths, long labels, empty/error/
   stale states, keyboard/focus paths, and first useful content.
7. Critique the screenshot and DOM state, then run relevant type, unit,
   browser, accessibility, and integration checks. Report coverage and limits.

## Product and RAG rules

- Preserve query/SSE contracts, grounded answers, Library schema, and saved
  user content unless a separately authorized product change says otherwise.
- The primary journey is `question -> answer -> citation -> source -> reader ->
  save/continue`; Documents and direct source browsing have their own task
  semantics and must not be forced through that journey.
- Keep Chat, Documents, Search, and Library primary. Put Retrieval Lab,
  Evaluation, Analytics, System, and Architecture behind Tools.
- Human labels and actions lead; IDs, paths, raw JSON, model details, scores,
  and implementation status are secondary details.
- Use semantic tokens for surface, text, border, focus, and state. Design light
  and dark together; normal text meets 4.5:1 and state is not color-only.
- Motion is short, interruptible, meaningful, and reduced-motion aware. Do not
  use glow, gradients, or animation to compensate for weak hierarchy.
- Tables browse and select; details and editing belong in a drawer, panel, or
  focused flow.
- A citation is tied to its originating message/answer variant and stable source
  identity. Never resolve an older citation through the newest answer.
- Retrieval scores are ranking signals, not confidence or correctness. Do not
  invent evidence-strength labels or silently replace missing source data.
- `/retrieval/inspect` is provider-free and must not trigger generation on every
  keystroke. Archify must describe verified topology and load outside Chat.
- Any real Groq request must use `GROQ_KEY_POLICY=key5_only` and
  `GROQ_API_KEY5`; fail closed rather than falling back to another key.

## Gates and rejection criteria

- Draft scope, submitted scope, answer version, selected source, and reader
  target remain distinct. Cancelled, stale, or cross-conversation responses
  cannot update the current surface.
- Notifications have an owning operation and explicit clearing condition; a
  transient toast must not become a cross-context error banner.
- Every surface has default, focus, selected, disabled, loading, error, stale,
  and read-only states where applicable, with a recovery path.
- Scroll ownership is explicit for app, inspector, workspace, document body,
  results, tables, code, and overlays. No clipped primary copy, hidden primary
  action, fixed bar covering content, or hover-only action is acceptable.
- The containing rail/panel must be evaluated, not only a child canvas. Native
  browser zoom is a separate check from viewport resizing.
- Do not label a source "retrieved," a document "complete," a match "exact,"
  or a representation "official" beyond the current task and verified data.
  Hand identity, revision, coverage, or acquisition questions to
  `rag-document-provenance`.
- A build, snapshot, nonzero bounding box, or test count alone never proves a
  successful product journey.

## Handoffs

- Missing or irrelevant evidence, ranking, fusion, or reranker behavior:
  `rag-retrieval-quality`.
- Cross-layer request, SSE, context, or state contract: `rag-core`.
- Source/document/citation identity, revision, acquisition, or representation:
  `rag-document-provenance`.
- Threat, injection, unsafe acquisition, HTML, path, or leakage concern:
  `rag-security`.
- Reproducible latency, memory, streaming, cache, or first-useful-content
  regression: `rag-performance`.
- Quality claims, benchmark comparisons, judge or metric meaning:
  `rag-evaluation`.
- Screenshot-first critique: `product-design:audit`; interaction evidence:
  browser/computer-use; verified system diagram: `archify`.

## Definition of done

The changed journey is semantically correct, readable, keyboard-usable,
responsive, recoverable, and source-honest in the rendered product. The real
affected state was inspected, relevant tests cover observable behavior, and
remaining limitations, including known current defects, are reported.
