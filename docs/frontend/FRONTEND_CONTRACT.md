# Frontend Contract

## Non-negotiable behavior

- Preserve existing Vite/React/TypeScript/Tailwind/Lucide conventions.
- Preserve query/SSE, grounded citations, conversation storage, backup/restore,
  bookmarks, notes, variants, collections, read-only sessions, and multi-tab
  safeguards.
- Keep API keys and secrets out of browser-exposed variables, artifacts, logs,
  screenshots, diagram files, and UI.
- All async surfaces expose loading, empty, error, recovery, and long-content
  behavior where applicable.
- Primary user copy is concise and human. Technical details belong in Tools,
  details, tooltips, or diagnostics.
- No accidental document overflow, hidden primary labels, clipped content,
  fixed overlay coverage, or disabled browser zoom.
- Destructive actions require confirmation or undo.
- Normal text contrast is at least 4.5:1 in both themes. Status never relies
  on color alone.
- `GROQ_KEY_POLICY=key5_only` and `GROQ_API_KEY5` are mandatory for any real
  Groq request; no fallback key is allowed.
- `data/` and canonical corpus/index are immutable in frontend work.

## Product vocabulary

Use: question, answer, source, citation, filing, section, excerpt, saved
conversation, note, bookmark, search, retry, reader, retrieval score.

Keep secondary or translate: chunk ID, candidate pool, BM25, dense vector,
reranker, raw JSON, session ID, endpoint, provenance hash, provider error code.

Never label retrieval score as accuracy, confidence, or probability.

## State copy contract

An error states what failed and gives a next action. A no-result state is only
shown after a successful search. Offline/local storage warnings explain what is
still available. Unknown or stale data is labelled instead of silently replaced.

## Architecture boundary

Architecture diagrams are generated from verified source evidence and loaded
only in Tools → Architecture. They do not run the query path, expose local
paths, or add runtime dependencies to Chat.

## Evidence and reader acceptance

Reader labels, transitions, availability, and completeness are representation-
and revision-bound. A Documents action with no submitted question must not use
answer-scoped “this answer” or “retrieved sources” language. A successful fetch
does not by itself prove reader admission, structured coverage, or search
readiness. Structured no-match copy must stay scoped to the structured view
when coverage is partial or unknown and must offer normalized local search. The
direct document workspace owns identity/header chrome; embedded readers own
reading controls and content without repeating that identity. The historical
native browser-zoom gate remains an external manual check because the
connected browser cannot report native chrome zoom values.

## Library continuity acceptance

Library is a derived view over the existing conversation and evidence stores;
it does not create a second persistence index. Its order is Recent Research,
Saved Answer Versions, and Evidence Collections. Saved answer actions carry
exact conversation/message/variant identity, while evidence actions distinguish
the historical captured snapshot from a separately verified current corpus
source. Current-source handoffs require exact chunk/document/hash identity and
must not substitute a nearby source. Browser-local, read-only, volatile, and
storage-failure states are explicit, and raw IDs/revisions remain behind a
provenance disclosure. Recent items are bounded and continuation fills a draft
without submitting a query.

## V5 current workbench architecture and closure

V5-08 is the current frontend baseline. `App.tsx` is the route and identity
coordinator; `ApplicationWorkspace` and `WorkbenchLayout` compose the shared
shell; `useWorkbenchController` mirrors presentation state; and
`useWorkbenchPreferences` persists only pane widths and collapse booleans.
`SourcesPane` owns source-list filtering/focus, `DocumentPane` adapts the
existing reader lifecycle, and `RouteDocumentContext` handles typed route
handoffs. Existing API, reader, cancellation, provenance, evidence-save,
conversation, retrieval, and persistence owners remain authoritative.

The responsive source of truth is measured geometry: four panes from the
~1254px reference width upward (the document pane narrows toward its own
minimum before the layout changes mode), a context dock for wide-but-short
viewports, a contextual modal surface at 1024px or below the height floor, and
drawer/single-surface behavior below that boundary. Pointer resize is rAF/CSS-
variable driven until commit; keyboard, reset, collapse, restore, modal focus
return, and reduced-motion paths are covered. The pane limits are the
documented reference geometry (sources 300-400px, document 272-560px), and the
workbench derives the rendered tracks from the same effective widths it used to
choose the mode, so the rendered geometry always matches the decision.
The Document region supports Structured, Normalized text, and a
manifest-gated PDF representation. An exact reader mark requires matching
source/chunk/hash/document/revision identity; mismatches remain explicitly
stale, unavailable, or error and never fall forward to a nearby source.
Current corpus support is `DERIVED_PDF` only; `OFFICIAL_PDF` is schema/helper
support without admitted official bytes. PDF.js is loaded lazily after the
backend manifest admits the representation. The document pane deliberately
omits page-level navigation for representations that do not define pages,
rather than fabricating page numbers from the reference screenshot.

The visual and regression receipt is maintained in
`V5_WORKBENCH_CONTRACT.md`; historical rail references in earlier checkpoint
sections are historical only and are not the current composition.

## PDF representation extension

The post-V5 PDF surface is optional and representation-bound. `DocumentPane`
may expose a PDF tab only for a current backend manifest whose type is
`OFFICIAL_PDF` or `DERIVED_PDF`; missing, unsupported, failed, or stale status
must keep Structured/Normalized text usable. The browser uses PDF.js with the
document-only content route and never accepts a remote URL, filesystem path, or
HTML payload for rendering.

The PDF location contract is stricter than a visual search: exact source and
chunk identity, source/document revisions, content hash, artifact hash, and
sidecar mapping identity must validate before a highlight is painted. A
non-exact response is a visible fallback state, not a yellow approximation.
Generated pages are labeled as generated representation pages and are never
presented as official SEC pagination. The PDF metadata panel exposes the
representation type, page semantics, renderer, revisions, page count, and
advanced artifact identity.
