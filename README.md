# Enterprise Document QA

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-DC244C?style=for-the-badge)
![RAG](https://img.shields.io/badge/RAG-Hybrid_Retrieval-7C3AED?style=for-the-badge)
![Groq](https://img.shields.io/badge/Groq-LLM_Generation-F55036?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-MVP_Complete-16A34A?style=for-the-badge)

Enterprise Document QA is a production-style Retrieval-Augmented Generation backend for answering grounded questions over SEC 10-K filings.
The system ingests filings for Apple, Microsoft, and Amazon, extracts key sections, builds a hybrid search index, and serves cited financial answers through FastAPI with streaming, semantic caching, and multi-turn memory.

## Overview

- Problem type: enterprise document question answering over financial filings.
- Corpus: latest SEC 10-K filings for `AAPL`, `MSFT`, and `AMZN`.
- Serving style: FastAPI REST API with non-streaming and Server-Sent Events streaming responses.
- Retrieval stack: BM25 keyword search, Qdrant semantic search, Reciprocal Rank Fusion, and cross-encoder re-ranking.
- Generation stack: strict source-grounded LLM prompting with citations and insufficient-context fallback.
- Conversation support: session-based memory plus query rewriting for follow-up questions.
- Evaluation: LLM-as-judge scoring for faithfulness, answer relevancy, and context precision.

## Key Features

| Area | Capability |
|---|---|
| Filing ingestion | SEC EDGAR client with CIK lookup, rate limiting, and filing download |
| Section extraction | Robust extraction for `business`, `risk_factors`, `mdna`, and `financial_statements` |
| Chunking | Token-aware recursive chunking with larger chunks for financial statements |
| Embeddings | Local embeddings via `nomic-ai/nomic-embed-text-v1.5` |
| Vector search | Persistent local Qdrant collection with deterministic point IDs |
| Hybrid retrieval | BM25 + dense retrieval + RRF + cross-encoder re-ranking |
| RAG generation | Grounded answer generation with source citations and fallback behavior |
| API | FastAPI service with Swagger UI and SSE streaming |
| Cache | Filter-aware semantic response cache for repeated stateless queries |
| Memory | Multi-turn conversation memory and LLM-powered query rewriting |
| Evaluation | Fixed benchmark with faithfulness, relevancy, and context precision metrics |

## Architecture

```text
SEC 10-K Filing
  -> HTML-to-Text Conversion
  -> Section Extraction
  -> Token-Aware Chunking
  -> Local Embeddings
  -> Qdrant Vector Index + BM25 Index
  -> Query Rewrite for Follow-ups
  -> Hybrid Retrieval + Reciprocal Rank Fusion
  -> Cross-Encoder Re-ranking
  -> Semantic Cache / Conversation Memory
  -> Grounded LLM Answer Generation
  -> FastAPI REST API / SSE Streaming
```

## Supported Corpus

| Company | Ticker | Filing Type | Sections Indexed |
|---|---|---|---|
| Apple | `AAPL` | 10-K | Business, Risk Factors, MD&A, Financial Statements |
| Microsoft | `MSFT` | 10-K | Business, Risk Factors, MD&A, Financial Statements |
| Amazon | `AMZN` | 10-K | Business, Risk Factors, MD&A, Financial Statements |

## API Endpoints

Run the API locally:

```powershell
.venv\Scripts\python.exe -m uvicorn src.api.app:app --reload --port 8000
```

Swagger UI:

```text
http://localhost:8000/docs
```

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Service readiness and memory stats |
| `POST` | `/query` | Non-streaming RAG answer |
| `POST` | `/query/stream` | SSE streaming RAG answer |
| `GET` | `/supported-tickers` | Supported tickers and sections |
| `GET` | `/cache/stats` | Semantic cache metrics |
| `POST` | `/cache/clear` | Clear semantic cache |
| `POST` | `/cache/test` | Compare query embedding similarity |
| `GET` | `/session/{session_id}/history` | Inspect conversation history |
| `DELETE` | `/session/{session_id}` | Clear one conversation session |

Example request:

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What was Apple total revenue in 2024?",
    "ticker": "AAPL",
    "section": "financial_statements",
    "top_k": 5
  }'
```

Example multi-turn request:

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are Apple main risk factors?",
    "ticker": "AAPL",
    "section": "risk_factors",
    "session_id": "demo-session-001"
  }'

curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What about their revenue?",
    "session_id": "demo-session-001"
  }'
```

The second question is rewritten internally into a standalone retrieval query similar to:

```text
What is Apple's total revenue?
```

## Retrieval Design

The retriever combines lexical and semantic signals instead of relying on vector search alone.

| Stage | Role |
|---|---|
| BM25 | Finds exact financial terms, company names, and table labels |
| Qdrant semantic search | Finds conceptually relevant chunks using dense embeddings |
| Reciprocal Rank Fusion | Merges BM25 and semantic rankings without score normalization |
| Cross-encoder re-ranker | Re-scores fused candidates for final source ranking |

This design improved context precision and fixed a no-filter AWS query that previously returned Microsoft cloud context above Amazon evidence.

## Generation Design

The generator uses a strict financial analyst prompt:

- Use only retrieved SEC filing context.
- Cite factual claims with `[Source N]`.
- Do not use general knowledge.
- Do not infer beyond the provided context.
- Quote numbers exactly as they appear in the retrieved context.
- Return an explicit insufficient-context fallback when evidence is missing.

Supported providers:

| Provider | Status |
|---|---|
| Groq | Primary provider used for current validation |
| Gemini | Implemented fallback provider |
| OpenAI / Anthropic | Dependencies present for future extension |

## Evaluation Results

Latest priority-1 and priority-2 LLM-as-judge run, using Groq `llama-3.3-70b-versatile` as judge:

| Metric | Score |
|---|---:|
| Faithfulness | `0.8767` |
| Answer relevancy | `0.9100` |
| Context precision | `0.4453` |
| Overall judge average | `0.7440` |
| Citation correctness | `1.0000` |
| Recall proxy | `0.9583` |
| Fallback accuracy | `1.0000` |

Coverage:

- `30/30` priority <= 2 cases completed with no skipped records.
- Covered categories: fact lookup `8/8`, summary `6/6`, enumeration `4/4`, comparative `6/6`, multi-hop `3/3`, out-of-corpus `3/3`.

Interpretation:

- Achieved `0.88` faithfulness, `0.91` answer relevancy, and `0.96` recall proxy across 30 cases spanning 6 query categories.
- Overall context precision remains the primary optimization target: correct answers are reliably retrieved, but retrieval still includes extra non-essential chunks.
- Balance-sheet `total X` questions use a lightweight structured lookup over financial-table row labels before semantic re-ranking. This fixes known total-assets retrieval failures without regenerating table chunks; Microsoft total-assets year-over-year now answers with `619,003`, `512,163`, and the computed increase `106,840`.
- Multi-hop improved most significantly after structured lookup: category faithfulness moved from `0.50` to `0.83`, with Microsoft total-assets year-over-year now scoring `1.00/1.00/0.50` instead of the previous `0.00/0.20/0.00`.
- The 30-case run exposed a narrow fact-lookup recall miss on Microsoft's auditor question, lowering that run's fact-lookup recall proxy to `0.875`. This was subsequently fixed with auditor-signature lookup and targeted verification; the full 30-case table has not been rerun after that targeted fix.
- Extended validation: 6 additional `priority=3` cases for `V`, `MA`, `LLY`, `KO`, and `RTX` were judged separately after the official N=30 run. They confirm structured lookup generalizes to new tickers: `V`, `MA`, and `LLY` total-assets cases all scored `1.00` faithfulness, and the RTX total-net-sales trend case also scored `1.00` faithfulness. One outlier, Coca-Cola competition risk factors, scored `0.50/0.60/0.20` despite recall `1.00` because retrieved context discussed competition only indirectly and included extra risk-factor context. The checkpoint-merged N=36 aggregate is not used as the official benchmark because it reused stale N=30 records, including the pre-fix MSFT auditor recall record.
- Latency from the 30-case judge run is not used as a performance benchmark because Groq returned repeated `429 Too Many Requests` responses and SDK backoff delays during generation/judging.
- A smaller `llama-3.1-8b-instant` judge was rejected after producing false negatives on exact numbers that were present in context.

## Performance Notes

Retrieval latency optimization:

- Optimized retrieval latency by about `52%` (`0.86s -> 0.41s` per query) through evidence-based tuning of `candidate_pool` (`20 -> 10`) and cross-encoder `batch_size` (`32 -> 4`).
- Validated with deterministic recall sweeps and LLM-judge evaluation: priority-1 recall proxy reached `1.0000`; the broader 30-case priority <= 2 run is `0.9583`, with comparative, enumeration, multi-hop, and summary all at `1.0000`.
- Qdrant local is the default Docker/runtime target: Qdrant Cloud added about `0.30s` per retrieve call in measured network latency (`0.737s` cloud vs `0.444s` local at `candidate_pool=10`).
- On the Legion RTX 5060 environment, installing the CUDA 12.8 PyTorch build changed embedding from CPU to GPU (`cuda:0`) and measured throughput improved from about `2.7` to `23.3` chunks/sec on a 100-chunk sample.

Corpus scale:

- The configured corpus now targets `50` tickers; `44` currently have searchable embedded chunks in local Qdrant.
- Local Qdrant indexes `7,940` chunks after restoring and embedding `financial_table` chunks for the 50-company scale trial.
- `financial_table` chunks are available for `33` searchable tickers; the remaining searchable degraded tickers are limited to extracted text sections.
- Latest extraction quality: `35` clean, `9` degraded, `6` failed/unusable. The main remaining corpus-scale limitation is section extraction for filings that use annual-report cross-reference or non-standard Item 7/8 layouts.
- The unusable rate stayed stable at `12%` from the 25-company snapshot to the 50-company trial, while clean extraction improved from `56%` to `70%`.

| Scenario | Filter | Latency |
|---|---|---:|
| Apple revenue | `ticker=AAPL`, `section=financial_statements` | `5.2665s` |
| Microsoft cybersecurity risks | `ticker=MSFT` | `4.6938s` |
| AWS revenue growth | none | `3.1727s` |

Streaming validation:

| Metric | Seconds |
|---|---:|
| First SSE event, `sources` | `2.4945` |
| First token, end-to-end TTFT | `2.9459` |
| Total response time | `3.5820` |

Semantic cache validation:

| Check | Result |
|---|---:|
| Exact repeated `/query` latency | `0.1080s` |
| Cached `/query/stream` completion | `0.1212s` |
| Similarity threshold | `0.95` |

## Local Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create `.env`:

```text
GROQ_API_KEY=your_groq_key
GROQ_API_KEY_FALL_BACK=optional_second_groq_key_for_evaluation
GEMINI_API_KEY=optional_gemini_key
QDRANT_MODE=local
QDRANT_LOCAL_PATH=data/processed/qdrant
QDRANT_CLOUD_URL=
QDRANT_CLOUD_API_KEY=
```

Build local artifacts in order:

```powershell
.venv\Scripts\python.exe -m scripts.download_filings
.venv\Scripts\python.exe -m scripts.chunk_filings
.venv\Scripts\python.exe -m scripts.add_table_chunks
.venv\Scripts\python.exe -m scripts.embed_chunks
.venv\Scripts\python.exe -m scripts.index_chunks
```

Run a smoke test:

```powershell
.venv\Scripts\python.exe -m scripts.diagnostics.rag_smoke_test
```

Run evaluation:

```powershell
.venv\Scripts\python.exe -m scripts.run_evaluation
```

## Running With Docker

Prerequisites: Docker Desktop installed and running, plus corpus artifacts already built locally under `data/processed/`.

1. Copy `.env.example` to `.env` and fill in `GROQ_API_KEY`. `GEMINI_API_KEY` is optional for serving and only needed for Gemini-backed evaluation/judging flows.

2. Build and run the backend:

```bash
docker compose build
docker compose up
```

3. Verify the API is ready:

```bash
curl http://localhost:8000/health
```

The response should include `"pipeline_ready": true`.

Docker notes:

- The container uses CPU-only PyTorch for portability, so it runs on machines without an NVIDIA GPU. The verified Docker smoke test answered an Apple financial-table query in about `1.3s` end-to-end including the Groq API call.
- Qdrant runs in local persistent mode and is mounted from `./data/processed` into `/app/data/processed`. The image does not bundle corpus data; `data/processed/` must exist on the host before running Docker.
- The service uses one Uvicorn worker because Qdrant local mode uses a file lock and does not support multiple API worker processes reading the same local storage path. Use Qdrant server or Qdrant Cloud before enabling multi-worker deployment.

## Qdrant Cloud

Local Qdrant remains the default serving mode. To migrate the current local collection to Qdrant Cloud, create a Qdrant Cloud cluster and set:

```text
QDRANT_CLOUD_URL=https://your-cluster-id.cloud.qdrant.io:6333
QDRANT_CLOUD_API_KEY=your_api_key
```

Migrate the local `sec_filings` collection:

```powershell
.venv\Scripts\python.exe -m scripts.migrate_to_qdrant_cloud
```

Use `--recreate` only when you intentionally want to replace the cloud collection:

```powershell
.venv\Scripts\python.exe -m scripts.migrate_to_qdrant_cloud --recreate
```

Verify local and cloud retrieval agree on a smoke query:

```powershell
.venv\Scripts\python.exe -m scripts.verify_qdrant_cloud
```

After verification passes, switch serving to cloud:

```text
QDRANT_MODE=cloud
```

## Repository Structure

```text
configs/              Environment-backed project settings
scripts/              Data pipeline, indexing, smoke test, and evaluation entry points
src/api/              FastAPI application
src/evaluation/       LLM-as-judge evaluation framework
src/generation/       RAG generation, streaming, and decomposition foundation
src/ingestion/        SEC download, section extraction, and chunking
src/memory/           Conversation memory and query rewriting
src/retrieval/        Embeddings, vector store, hybrid retrieval, and semantic cache
tests/                Unit tests
PROJECT_STATE.md      Detailed engineering handoff and milestone notes
```

## Data And Secrets

Generated artifacts are intentionally ignored by git:

- Raw SEC filings under `data/raw/`.
- Extracted sections and chunks under `data/processed/`.
- Embedded chunks.
- Local Qdrant index.
- Evaluation result JSON.

Secrets are loaded from `.env` and should never be committed.

## Current Status

| Area | Status |
|---|---|
| SEC download and section extraction | Complete |
| Token-aware chunking | Complete |
| Local embedding pipeline | Complete |
| Qdrant vector indexing | Complete |
| Base semantic retrieval | Complete |
| RAG generation | Complete |
| Evaluation framework | Complete |
| FastAPI service | Complete |
| Hybrid search and re-ranking | Complete |
| SSE streaming | Complete |
| Semantic query cache | Complete |
| Multi-turn conversation memory | Complete |
| Query decomposition | Foundation module added; API integration pending |

## Known Limitations

- The current corpus targets `50` companies, but only `44` have searchable chunks because `6` filings failed section extraction under the current single-document Item-boundary extractor.
- Extraction quality remains uneven across large-company filing layouts: some annual-report cross-reference and non-standard Item 7/8 formats are degraded or unusable until the extractor is expanded.
- Financial statements become verticalized after HTML-to-text conversion, making exact numeric retrieval harder than prose retrieval.
- Hybrid retrieval improves source quality but adds CPU latency due to cross-encoder re-ranking.
- Semantic cache and conversation memory are currently in-memory and are lost on process restart.
- Multi-turn query rewriting adds one LLM call for follow-up questions.
- Groq free tier can return `429 Too Many Requests`; SDK retries can recover but increase latency.

## Roadmap

1. Integrate query decomposition into the API for compound and comparative questions.
2. Improve financial table retrieval with table-aware chunking or metadata boosts.
3. Expand the evaluation set into a broader benchmark.
4. Add automated unit and integration tests for extraction, retrieval, API, and memory.
5. Build a Streamlit demo UI over `/query/stream`.
6. Add Docker packaging for reproducible deployment.

## Why This Project Matters

This project demonstrates the engineering work required to move RAG beyond a simple embedding demo:

- Robust document preprocessing.
- Retrieval quality measurement.
- Hybrid retrieval and re-ranking.
- Streaming UX support.
- Cache correctness across filters.
- Multi-turn query rewriting.
- Clear limitations and reproducible validation.

The goal is not to hide the hard parts of enterprise document QA, but to expose them, measure them, and improve them systematically.
