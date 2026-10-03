# SEC Research Copilot — Application Copy

Public display name: **SEC Research Copilot** (original repository: Enterprise Document QA).

Copy grounded in the [case study](PORTFOLIO_CASE_STUDY.md) and
[frozen release evidence](IMPROVEMENT_FINAL_RECEIPT.md). Measurements below are
controlled local development results; they do not imply employment, customer
adoption or production SLA. Adjust first-person wording to your actual contribution.

## A. CV — three bullets

- Built a production-style SEC 10-K research system configured for 50 companies,
  using BM25, Qdrant, RRF and cross-encoder reranking for cited RAG answers.
- Designed bounded durable Agent runs with SQLite authority, safe cancellation
  and fixed workers; reduced idle-confirmed queue p95 from 502.753 to 9.340ms
  in a controlled local benchmark.
- Integrated React/FastAPI Research workflows; verified 844 frontend tests,
  542 browser passes and successful exact-release Backend/Frontend CI.

## B. LinkedIn / portfolio paragraph

I built SEC Research Copilot, a production-style research workspace for SEC
10-K filings configured for 50 companies. Quick Research combines BM25, Qdrant,
Reciprocal Rank Fusion and cross-encoder reranking to produce cited RAG answers.
Deep Research uses bounded durable Agent runs, with SQLite owning state, events
and results while the React frontend stores safe references. I focused on
cancellation, restart boundaries, memory-only credentials and content-free
observability. Controlled local benchmarks reduced read50 client p95 from
1967.995 to 982.813ms and idle-confirmed queue p95 from 502.753 to 9.340ms.
The frozen release passed backend, frontend, browser and HTTP/SSE validation,
including successful exact-release CI. The project remains single-process and
does not claim production SLA or real provider quota certification.

## C. GitHub repository description

SEC Research Copilot — hybrid RAG + durable Deep Research Agent for cited SEC 10-K analysis with FastAPI, Qdrant, React and Groq.

## Evidence for application and interview use

- Retrieval and authority: [architecture](../ARCHITECTURE.md),
  [closed tools](../src/agent/registry.py).
- Queue measurement: [WORKER-002 receipt](WORKER_002_FINAL_RECEIPT.md).
- Read measurement: [DB-SCALE receipt](DB_SCALE_001_FINAL_RECEIPT.md).
- Release counts/skips and provenance: [final receipt](IMPROVEMENT_FINAL_RECEIPT.md).
- Exact code release `cbaacc3765f8dbca2ff04247cb24fd773751a0f9`:
  [Backend CI](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/runs/37085104945),
  [Frontend CI](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/runs/37085104875).

Use “production-style,” not an absolute “production-ready.” Do not turn the
50-company configuration into a customer count, structural metrics into an
accuracy score, or local benchmark reductions into internet latency promises.
