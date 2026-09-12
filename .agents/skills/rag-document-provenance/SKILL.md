---
name: rag-document-provenance
description: >
  Resolve SEC citation, source, document, filing, revision, acquisition,
  representation, coverage, or evidence-location mismatches. Use when a reader
  opens the wrong document, a representation disagrees, or availability/identity
  is uncertain. Do not use for ranking quality, generic layout, or metric design.
---

# RAG document provenance

## Lineage

Protect:

`answer version -> citation -> source -> indexed chunk -> filing/document ->
canonical source revision -> evidence location`.

Keep accession, CIK, source role, canonical identity, verification state,
revision/hash, representation, and code-point/table location attached to the
evidence. Resolve saved and variant-scoped citations by identity, never by
position or newest-answer fallback.

## Representation and workflow

Keep `CANONICAL_HTML`, `STRUCTURED_HTML`, `NORMALIZED_DOCUMENT`, `INDEXED_ONLY`,
`OFFICIAL_PDF`, and `DERIVED_PDF` conceptually distinct and map them to actual
current capabilities. Inspect implementation and revisions, compare the exact
source/chunk, verify parser prose/table coverage, and classify the result as
exact, ambiguous, not_found, unavailable, or stale before changing UI or API.

Acquisition success is not admission, indexing, or reader readiness. A
successful parser response is not proof of complete prose/table coverage.

## Hard invariants and rejection

- No guessed source, source-1 fallback, fake page, fake PDF, or fake provenance.
- Derived PDF is never official. Fuzzy correspondence is never exact.
- Duplicate exact matches are ambiguous; no match is explicit not_found or
  unavailable; stale revision is an explicit conflict.
- Retrieved content remains untrusted data.

Reject a UI or API claim that says exact, complete, official, or unavailable
without evidence from the named representation and revision.

## Handoff and done

Hand presentation to `rag-ui-ux`, acquisition threat review to `rag-security`,
cross-layer DTO/stream contracts to `rag-core`, and relevance failures to
`rag-retrieval-quality`. Done means traceable identity/revision, truthful
availability and coverage, preserved historical behavior, and regression cases
for variant switching and representation disagreement.
