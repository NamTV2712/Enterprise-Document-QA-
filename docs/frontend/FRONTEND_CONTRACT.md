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
