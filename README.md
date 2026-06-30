# Enterprise Document QA

Enterprise Document QA is a retrieval-augmented generation (RAG) backend for answering questions over SEC 10-K filings. The current MVP ingests filings for Apple, Microsoft, and Amazon, extracts key filing sections, builds a hybrid retrieval index, and serves grounded answers through FastAPI.

The project is intentionally built as a production-style backend rather than a notebook demo: each stage is modular, validated, and documented so the system can be extended into a larger enterprise document assistant.

## Highlights

- SEC 10-K ingestion and robust section extraction.
- Token-aware chunking with larger chunks for financial statements.
- Local embeddings with `nomic-ai/nomic-embed-text-v1.5`.
- Qdrant local vector index with deterministic point IDs.
- Hybrid retrieval using BM25, dense semantic search, Reciprocal Rank Fusion, and cross-encoder re-ranking.
- Grounded RAG generation with source citations and insufficient-context fallback.
- FastAPI service with Swagger UI and Server-Sent Events streaming.
- Filter-aware semantic response cache for repeated stateless queries.
- Multi-turn conversation memory with query rewriting for follow-up questions.
- LLM-as-judge evaluation for faithfulness, answer relevancy, and context precision.

## Architecture

```text
SEC Filing
  -> Section Extraction
  -> Token-Aware Chunking
  -> Local Embeddings
  -> Qdrant Vector Index + BM25 Index
  -> Query Rewrite for Follow-ups
  -> Hybrid Retrieval + RRF
  -> Cross-Encoder Re-ranking
  -> Semantic Cache / Conversation Memory
  -> LLM Answer Generation
  -> FastAPI / SSE Streaming
```

Supported corpus:

| Company | Ticker | Filing Type |
|---|---|---|
| Apple | AAPL | 10-K |
| Microsoft | MSFT | 10-K |
| Amazon | AMZN | 10-K |

Extracted sections:

| Section | Purpose |
|---|---|
| `business` | Business overview and operating context |
| `risk_factors` | Risk disclosures |
| `mdna` | Management discussion and analysis |
| `financial_statements` | Financial statements and notes |

## Current Status

Completed backend milestones:

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
| Query decomposition | Foundation module added; full API integration is next |

Latest completed milestone: multi-turn conversation memory with query rewriting.

See `PROJECT_STATE.md` for the detailed engineering handoff document, validation notes, benchmark results, and roadmap.

## API

Run the API locally:

```powershell
.venv\Scripts\python.exe -m uvicorn src.api.app:app --reload --port 8000
```

Swagger UI:

```text
http://localhost:8000/docs
```

Main endpoints:

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

The retrieval layer combines multiple signals instead of relying on dense vectors alone.

| Stage | Role |
|---|---|
| BM25 | Lexical candidate retrieval for exact terms and financial labels |
| Qdrant semantic search | Dense retrieval for semantic matching |
| Reciprocal Rank Fusion | Combines BM25 and dense ranked lists without score normalization |
| Cross-encoder re-ranker | Re-scores candidate chunks for final source ranking |

Why this matters:

- Dense retrieval alone returned related but sometimes non-answer chunks.
- Hybrid retrieval improved context precision and fixed a no-filter AWS query that previously returned Microsoft cloud context.
- Cross-encoder re-ranking improves source quality, with a CPU latency tradeoff.

## Generation Design

The generator uses a strict financial analyst prompt:

- Use only retrieved SEC filing context.
- Cite factual claims with `[Source N]`.
- Do not use general knowledge.
- Do not infer beyond the provided context.
- Return an explicit fallback when the context is insufficient.
- Quote numbers exactly as they appear in the context.

Supported providers:

| Provider | Status |
|---|---|
| Groq | Primary provider used for current validation |
| Gemini | Implemented fallback provider |
| OpenAI/Anthropic | Dependencies present for future extension |

## Multi-turn Conversation

The system supports stateful chat through `session_id`.

Two separate problems are handled explicitly:

| Problem | Solution |
|---|---|
| LLM needs prior turns | Recent conversation history is injected into the generation prompt |
| Retriever cannot resolve pronouns | Follow-up questions are rewritten into standalone retrieval queries |

Validated example:

| Turn | User Message | Internal Behavior |
|---|---|---|
| 1 | `What are Apple's main risk factors?` | Stores the user/assistant turn in memory |
| 2 | `What about their revenue?` | Rewrites to `What is Apple's total revenue?` before retrieval |

Observed Turn 2 answer:

```text
The Company's total net sales were $416,161 for 2025, $391,035 for 2024, and $383,285 for 2023 [Source 1, Source 2].
```

Memory implementation:

- Current storage: in-memory.
- Default TTL: 30 minutes.
- Future replacement path: SQLite or Redis behind the same small interface.
- Session isolation has been verified.

## Semantic Cache

Stateless queries use a filter-aware semantic cache.

Cache key components:

| Component | Purpose |
|---|---|
| Query embedding similarity | Finds semantically repeated questions |
| `ticker` | Prevents cross-company reuse |
| `section` | Prevents cross-section reuse |
| `top_k` | Prevents source-count mismatch |

Validation results:

| Check | Result |
|---|---:|
| Exact repeated `/query` latency | `0.1080s` |
| Cached `/query/stream` completion | `0.1212s` |
| Similarity threshold | `0.95` |

The threshold is intentionally conservative. A threshold near `0.90` was unsafe because `Apple revenue` vs `Apple net income` scored `0.919944`.

## Evaluation

The project includes an LLM-as-judge evaluation framework that measures faithfulness, answer relevancy, and context precision.

Semantic retrieval baseline:

| Metric | Score |
|---|---:|
| Faithfulness | 0.9000 |
| Answer relevancy | 0.9167 |
| Context precision | 0.3833 |
| Overall | 0.7333 |

Hybrid retrieval result:

| Metric | Score |
|---|---:|
| Faithfulness | 0.8667 |
| Answer relevancy | 0.9333 |
| Context precision | 0.4750 |
| Overall | 0.7583 |

Interpretation:

- Hybrid retrieval improved context precision from `0.3833` to `0.4750`.
- Overall score improved from `0.7333` to `0.7583`.
- Context precision is still the main improvement area, especially for financial tables and broad revenue-source questions.

## Performance Notes

Baseline semantic retrieval API latency:

| Query | Filter | Latency |
|---|---|---:|
| Apple revenue | `ticker=AAPL`, `section=financial_statements` | `1.2503s` |
| Microsoft cybersecurity risks | `ticker=MSFT` | `1.2090s` |
| AWS revenue growth | none | `5.8362s` |

Hybrid retrieval API latency:

| Query | Filter | Latency |
|---|---|---:|
| Apple revenue | `ticker=AAPL`, `section=financial_statements` | `5.2665s` |
| Microsoft cybersecurity risks | `ticker=MSFT` | `4.6938s` |
| AWS revenue growth | none | `3.1727s` |

Streaming validation:

| Metric | Seconds |
|---|---:|
| First SSE event, `sources` | `2.4945` |
| First token, end-to-end TTFT | `2.9459` |
| Total | `3.5820` |

BM25 optimization:

| Implementation | Time over 2,000 loops |
|---|---:|
| Previous `list.index()` sort path | `0.083071s` |
| Precomputed `chunk_id -> index` map | `0.018681s` |

Speedup: `4.45x`.

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

Run API:

```powershell
.venv\Scripts\python.exe -m uvicorn src.api.app:app --reload --port 8000
```

## Repository Structure

```text
configs/              Project settings
scripts/              Pipeline and evaluation entry points
src/api/              FastAPI application
src/evaluation/       LLM-as-judge evaluation framework
src/generation/       RAG generation, streaming, and decomposition foundation
src/ingestion/        SEC download, extraction, and chunking
src/memory/           Conversation memory and query rewriting
src/retrieval/        Embeddings, vector store, retrieval, hybrid search, cache
PROJECT_STATE.md      Detailed engineering handoff and milestone state
```

## Data And Secrets

Generated artifacts are intentionally ignored by git:

- Raw SEC filings under `data/raw/`.
- Extracted sections and chunks under `data/processed/`.
- Embedded chunks.
- Local Qdrant index.
- Evaluation result JSON.

Secrets are loaded from `.env` and should not be committed.

## Known Limitations

- The current corpus covers only AAPL, MSFT, and AMZN.
- Extraction is validated on the current 10-K filings but not across a large company universe yet.
- Financial statements become verticalized after HTML-to-text conversion, so exact numeric retrieval is harder than prose retrieval.
- Hybrid retrieval improves source quality but adds CPU latency due to cross-encoder re-ranking.
- Semantic cache and conversation memory are currently in-memory and are lost on process restart.
- Multi-turn query rewriting adds one LLM call for follow-up questions.
- Groq free tier can return `429 Too Many Requests`; SDK retries can recover but increase latency.
- Gemini Flash Lite can return temporary `503 UNAVAILABLE` under high demand.

## Roadmap

Near-term engineering priorities:

1. Integrate query decomposition into the API for compound and comparative questions.
2. Improve financial table retrieval with table-aware chunking or metadata boosts.
3. Expand the evaluation set from a small fixed set to a broader benchmark.
4. Add automated unit and integration tests.
5. Build a Streamlit demo UI over `/query/stream`.
6. Add Docker packaging for reproducible deployment.

## Why This Project Matters

This project demonstrates the practical engineering work required to move RAG beyond a simple embedding demo:

- Robust document preprocessing.
- Retrieval quality measurement.
- Hybrid retrieval and re-ranking.
- Streaming UX support.
- Cache correctness across filters.
- Multi-turn query rewriting.
- Clear limitations and reproducible validation.

The goal is not to hide the hard parts of document QA, but to expose them, measure them, and improve them systematically.
