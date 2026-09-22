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

## Documents catalog acceptance

The Documents page reads the catalog API as its only source of counts and
filter values. `/documents/stats` owns the metric cards and the filing-date
range, and `/documents/facets` owns the filter option labels, whose counts
follow the documented `all_filters_except_own_dimension` basis. No total,
facet count, or availability state is computed from the loaded page of rows.

A filter control exists only for a dimension the catalog reports as recorded,
so a dimension with no values is omitted rather than rendered as an empty
select. The form type is one of those dimensions: stored artifacts record none,
so the page never names a form type and never offers a form-type filter or
column, reporting `Unknown` with the API's reason wherever a form type would
have appeared. Unavailable statistics degrade to labeled unavailable values and
never to a fabricated zero.

Browsing the catalog is read-only. Search, filter, sort, page-size, paging, row
selection, detail tabs, and reader handoffs issue only reads; a document action
with no submitted question keeps its own grammatical context and never uses
answer-scoped wording. Selection carries exact document identity into the
reader handoff, and the deep link and return focus are unchanged.

## Discovery Search acceptance

Search is a snapshot view over API-004. One submitted search creates exactly one
`POST /search` snapshot; paging and the page-size control read that snapshot
through `GET /search/{search_id}` and never re-run the search. Opening a result,
saving evidence, and every visual-only change issue no further search. A newly
committed query, filter scope, or grouping is a new snapshot, and the page
always renders the snapshot's own submitted query and scope, so unsubmitted
typing can never relabel the results on screen. Snapshots stay runtime-only: a
reload returns to the initial state instead of silently re-running the query.

Counts are bounded discovery counts. When the API reports `limited_by_ceiling`
the page says discovery ranked the first N candidates and never presents that
total as a corpus total. Scores are raw BM25 ranking signals labelled as such:
never confidence, accuracy, probability, or a percentage. Highlights are the
API's character ranges rendered as React nodes; returned text is never
interpreted as HTML. An expired snapshot (410) is distinct from an unknown one
(404) and from a legitimate no-match, and each states what happened and what to
do next.

Filter and mode controls exist only for axes the API supports. The form type has
no dimension in this corpus, so no form-type filter or facet is offered; there
is no sort selector because the ranking engine owns the order; and recent
searches are the browser-local list the app already owns, labelled as such.

## Retrieval inspection acceptance

Retrieval (and the Reranker view over the same trace) renders only what API-005
reported. The score families — BM25, dense similarity, RRF, and the
cross-encoder logit — keep their own scales, carry the API's own definitions,
and are never presented as a confidence, accuracy, probability, or percentage. A
missing score or duration is named as not reported, never rendered as zero, and
a negative logit stays negative. Stage status is preserved exactly: a skipped or
`not_executed` stage says so with the API's reason and is never made to look
run, and the production-only stages stay labelled as not executed so an
inspection trace is not read as production output. `dropped_reason` is shown
only when the API supplied one, and a bounded eligible-document list is never
described as complete.

One submitted configuration is one `POST /retrieval/inspect`; selecting a
candidate, changing the view order or page size, paging, opening disclosures,
and opening a document run nothing further. An unchanged configuration cannot be
submitted twice while a run is open, while an edited one may be committed
immediately, in which case the earlier request is aborted and its late response
is ignored. The Reranker view compares the fusion and cross-encoder orders of
one same-pool trace and never reranks a second time.

