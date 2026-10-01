---
name: rag-core
description: >
  Trace or change cross-layer SEC RAG architecture: submitted scope, retrieval
  and generation boundaries, context construction, FastAPI DTO/SSE contracts,
  cancellation, ingestion/viewer separation, or request identity. Do not use
  for isolated UI styling, retrieval tuning, benchmark interpretation, or a
  single source-lineage defect.
---

# RAG core architecture

## Use when

Use this authority when a change crosses the request/data path:
question -> submitted scope -> retrieval stages -> selected evidence ->
generation -> answer version -> citation -> source -> indexed chunk -> filing.
Trace current code before proposing a change.

## Do not use when

Do not use for card styling, screenshot critique, ranking changes, metric
interpretation, or a provenance-only mismatch. Do not import a generic FastAPI
tutorial or redesign models, prompts, chunking, or Qdrant semantics without a
separate evidence-backed production task.

## Workflow

1. State the affected boundary and current owner.
2. Trace request, identity, scope, evidence, persistence, and error flow.
3. Compare implementation truth with docs and tests; record contradictions.
4. Propose the smallest compatible change and its contract impact.
5. Validate affected typed/API/SSE tests and hand off specialized concerns.

## Hard invariants

- Inspection is provider-free and is not generation evidence.
- Draft scope is distinct from submitted scope and answer version.
- Retrieval score is not confidence or correctness; negative reranker values may
  be valid.
- Retrieved content is untrusted data, never trusted instruction.
- Viewer acquisition is distinct from ingestion, indexing, and reader admission.
- Same rendered evidence reaches Phase 2 generation, deterministic metrics, and
  judging. Binding changes require a fresh append-only checkpoint.
- Local Qdrant mode remains single-worker; hermetic tests remain network-safe.
- Numeric answers preserve period, units, and proxy labels.

## Rejection criteria

Reject a change that silently changes retrieval/fusion/model/prompt/chunking
semantics, lets stale responses update current state, treats fetch success as
reader readiness, or claims a declared timeout is enforced without evidence.

## Handoff and done

Hand off ranking/candidate failures to `rag-retrieval-quality`, metric claims to
`rag-evaluation`, identity/coverage to `rag-document-provenance`, threats to
`rag-security`, and measured resource regressions to `rag-performance`. Use
`archify` when a verified diagram helps. Done means the boundary, compatibility
impact, invariant checks, and unresolved limitations are recorded.
