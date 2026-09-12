---
name: rag-evaluation
description: >
  Design, run, compare, or interpret SEC RAG quality evaluations, datasets,
  judges, deterministic metrics, slices, checkpoints, and promotion claims.
  Do not use for ordinary UI tests, isolated ranking implementation, or
  performance-only profiling.
---

# RAG evaluation

## Workflow

Define the claim -> inspect labels and metric implementation -> bind dataset,
config, evidence renderer, model/provider, and judge -> run permitted checks ->
inspect slices and worst failures -> verify comparability and denominators ->
report limitations -> promote only a complete eligible run.

## Hard invariants

- Retrieval relevance, answer relevance, faithfulness, citation support,
  correctness, system regression, and latency/cost are separate dimensions.
- `citation_correctness` that only checks in-range source numbers is not claim
  support. A keyword recall proxy is not Recall@K without labelled chunk IDs.
- LLM-as-judge is not the sole source of truth.
- Generation, deterministic metrics, and judging receive the same rendered
  evidence.
- Generation checkpoints are single-binding append-only artifacts; a changed
  binding requires a fresh path.
- Quota-skipped, incomplete, mixed-binding, or exploratory runs are not the
  official benchmark.

## Do not use / rejection

Do not invent precision, recall, MRR, NDCG, correctness, or citation-support
claims without supporting data. Reject a result with missing denominators,
unreported skipped records, changed renderer evidence, or incomparable model,
dataset, and prompt bindings.

## Handoff and done

Hand ranking failures to `rag-retrieval-quality`, evidence support to
`rag-document-provenance`, contract changes to `rag-core`, and resource-only
comparisons to `rag-performance`. Done means provenance, complete denominators,
correct metric names, slice/worst-case analysis, and explicit official or
exploratory status.
