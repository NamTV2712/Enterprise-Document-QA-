---
name: rag-retrieval-quality
description: >
  Diagnose missing or irrelevant SEC evidence across BM25, dense, lexical,
  fusion, candidate-pool, structured-lookup, or reranker stages. Use when the
  expected passage is lost or ranking semantics need evidence-backed analysis.
  Do not use for metric reporting, general latency, UI layout, or source-lineage
  resolution.
---

# Retrieval quality

## Workflow

DIAGNOSE BEFORE TUNING:

query and submitted scope -> corpus/chunk freshness -> lexical/BM25 candidates
-> dense candidates -> fusion -> reranker -> production-selected evidence ->
failing stage -> smallest justified intervention -> comparable evaluation.

Inspect current implementation and distinguish `/retrieval/inspect` candidates
from the evidence actually supplied to generation. Preserve production RRF,
structured lookup, filters, ticker/section scope, and top-K semantics.

## Hard invariants

- Scores are ranking signals, not confidence or correctness.
- Negative cross-encoder scores may be valid.
- Candidate pool, inspected selection, and generation evidence are different.
- A keyword recall proxy is not labelled Recall@K without chunk-ID ground truth.
- Do not tune multiple stages without attribution and an evaluation plan.
- Qdrant exact-vs-ANN behavior diagnoses search/index behavior, not semantic
  relevance by itself.

## Do not use / rejection

Do not use for a citation opening another filing, unsupported metric claims,
general performance work, or Qdrant deployment documentation. Reject changes
that silently replace the repository’s fusion or promotion semantics, equate
reranker values with confidence, or optimize quality by score alone.

## Handoff and done

Hand off metric meaning and run comparison to `rag-evaluation`, identity and
representation mismatch to `rag-document-provenance`, resource cost to
`rag-performance`, and cross-layer contract changes to `rag-core`. Done means a
reproduced query, stage evidence, one attributable intervention or a justified
no-change result, and comparable quality evidence.
