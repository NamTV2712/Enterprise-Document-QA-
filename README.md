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

| Metric | Semantic Baseline | Hybrid Retrieval |
|---|---:|---:|
| Faithfulness | `0.9000` | `0.8667` |
| Answer relevancy | `0.9167` | `0.9333` |
| Context precision | `0.3833` | `0.4750` |
| Overall | `0.7333` | `0.7583` |

Interpretation:

- Hybrid retrieval improved context precision from `0.3833` to `0.4750`.
- Overall evaluation improved from `0.7333` to `0.7583`.
- The remaining bottleneck is retrieval precision over verticalized financial tables.

## Performance Notes

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
GEMINI_API_KEY=optional_gemini_key
QDRANT_MODE=local
QDRANT_CLOUD_URL=
QDRANT_CLOUD_API_KEY=
```

Build local artifacts in order:

```powershell
.venv\Scripts\python.exe -m scripts.download_filings
.venv\Scripts\python.exe -m scripts.chunk_filings
.venv\Scripts\python.exe -m scripts.embed_chunks
.venv\Scripts\python.exe -m scripts.index_chunks
```

Run a smoke test:

```powershell
.venv\Scripts\python.exe -m scripts.test_rag
```

Run evaluation:

```powershell
.venv\Scripts\python.exe -m scripts.run_evaluation
```

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

- The current corpus covers only `AAPL`, `MSFT`, and `AMZN`.
- Extraction is validated on the current 10-K filings but not across a large company universe yet.
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
