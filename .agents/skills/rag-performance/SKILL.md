---
name: rag-performance
description: >
  Diagnose reproducible SEC RAG latency, memory, streaming, cache, parsing,
  search, or first-useful-reader-content regressions with stage attribution.
  Do not use for unmeasured optimization, relevance-only tuning, or ordinary UI
  styling.
---

# RAG performance

## Workflow

Baseline -> reproduce -> attribute stage/resource -> profile -> smallest change
-> same workload -> remeasure -> retain or revert. Record browser/device,
backend mode, corpus/data volume, cold/warm state, throttling, sample count,
and provider/network boundaries.

Measure retrieval, BM25/dense/fusion/reranker when instrumented, generation and
SSE, parsing/search, reader first useful content, cache retention, persistence,
large filings, and frontend responsiveness related to RAG. State when a stage
is not instrumented; never infer it from total time.

## Hard invariants

- Quality benchmarking and performance benchmarking remain separate.
- Do not trade retrieval quality for speed without comparable quality evidence.
- Client abort, a TTL, or a declared timeout does not prove worker cancellation,
  bounded memory, or enforced deadlines.
- Reuse UI budgets in `rag-ui-ux/references/visual-qa.md`; do not duplicate or
  lower them.

## Do not use / handoff / done

Do not use for expected-passage failures, benchmark metric meaning, or identity
mismatches. Hand ranking to `rag-retrieval-quality`, claims to
`rag-evaluation`, provenance to `rag-document-provenance`, and cross-layer
contracts to `rag-core`. Done means comparable measurements, attribution,
quality-preservation evidence where needed, and trace-backed limitations.
