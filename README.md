# Enterprise Document QA

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-DC244C?style=for-the-badge)
![RAG](https://img.shields.io/badge/RAG-Hybrid_Retrieval-7C3AED?style=for-the-badge)
![Groq](https://img.shields.io/badge/Groq-LLM_Generation-F55036?style=for-the-badge)
[![Backend CI](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/workflows/backend.yml/badge.svg)](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/workflows/backend.yml)
[![Frontend CI](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/workflows/frontend.yml/badge.svg)](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/workflows/frontend.yml)

Enterprise Document QA is a production-style Retrieval-Augmented Generation application for answering grounded questions over SEC 10-K filings.
The system ingests a 50-company filing corpus, extracts key sections and financial tables, builds a hybrid search index, and serves cited financial answers through a Vite/React research workspace backed by FastAPI streaming, semantic caching, multi-turn memory, and query decomposition.

## Overview

- Problem type: enterprise document question answering over financial filings.
- Corpus: latest SEC 10-K filings for 50 configured tickers; all 50 currently have searchable embedded chunks.
- Serving style: FastAPI REST API with non-streaming and Server-Sent Events streaming responses.
- Retrieval stack: BM25 keyword search, Qdrant semantic search, Reciprocal Rank Fusion, and cross-encoder re-ranking.
- Generation stack: strict source-grounded LLM prompting with citations and insufficient-context fallback.
- Conversation support: session-based memory plus query rewriting for follow-up questions.
- Complex-query support: LLM query decomposition for comparative and enumeration-style questions.
- Evaluation: LLM-as-judge scoring for faithfulness, answer relevancy, and context precision.

## Documentation

| Document | Purpose |
|---|---|
| [`README.md`](README.md) | Public overview, setup, API contract, benchmark, and deployment instructions |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Stable component boundaries, data and request flows, state ownership, and extension paths |
| [`PROJECT_STATE.md`](PROJECT_STATE.md) | Living engineering journal, measured decisions, rejected experiments, and current milestone state |
| [`TODO.md`](TODO.md) | Short current action queue for always-on deployment, diagnostics, and evidence-gated backlog work |
| [`AGENTS.md`](AGENTS.md) | Stable repository rules and operational traps for coding agents |
| [`frontend/README.md`](frontend/README.md) | Frontend-specific local development, Vercel setup, and API usage |

## Key Features

| Area | Capability |
|---|---|
| Filing ingestion | SEC EDGAR client with CIK lookup, rate limiting, and filing download |
| Section extraction | Robust extraction for `business`, `risk_factors`, `mdna`, and `financial_statements` |
| Chunking | Token-aware recursive chunking with larger chunks for financial statements |
| Financial tables | Table extraction plus structured lookup for total assets, liabilities, revenue, equity, and auditor signatures |
| Embeddings | Local embeddings via `nomic-ai/nomic-embed-text-v1.5` |
| Vector search | Persistent local Qdrant collection with deterministic point IDs |
| Hybrid retrieval | BM25 + dense retrieval + RRF + cross-encoder re-ranking |
| RAG generation | Grounded answer generation with source citations and fallback behavior |
| API | FastAPI service with Swagger UI and SSE streaming |
| Cache | Filter-aware semantic response cache for repeated stateless queries |
| Memory | Multi-turn conversation memory and LLM-powered query rewriting |
| Decomposition | Comparative and enumeration queries decomposed into focused sub-queries |
| Evaluation | Fixed benchmark with faithfulness, relevancy, and context precision metrics |
| Research workspace | Vite/React interface with searchable company and section controls, streaming answers, evidence inspection, and session history |
| Conversation UX | Separate Overview and Conversation views, bounded answer cards, interpreted-query metadata, and a resizable desktop control sidebar |

## Architecture

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for component boundaries, request flows,
state ownership, reliability controls, deployment constraints, and extension
paths.

```text
SEC 10-K Filing
  -> HTML-to-Text Conversion
  -> Section Extraction
  -> Token-Aware Chunking
  -> Local Embeddings
  -> Qdrant Vector Index + BM25 Index
  -> Query Rewrite for Follow-ups
  -> Query Decomposition for Complex Questions
  -> Hybrid Retrieval + Reciprocal Rank Fusion
  -> Cross-Encoder Re-ranking
  -> Semantic Cache / Conversation Memory
  -> Grounded LLM Answer Generation
  -> FastAPI REST API / SSE Streaming
```

## Supported Corpus

The configured corpus targets 50 latest 10-K filings:

```text
AAPL, MSFT, AMZN, GOOGL, META, NVDA, TSLA,
JPM, BAC, GS, MS, BRK-B,
JNJ, UNH, PFE,
WMT, HD, MCD,
XOM, CVX,
AMD, INTC, QCOM, AVGO, TXN,
CRM, ORCL, NOW, IBM,
V, MA, AXP,
LLY, MRK, ABBV, TMO,
PG, KO, PEP, COST, NKE,
CAT, GE, BA, LMT, HON, UPS, RTX,
VZ, T
```

Current searchable corpus:

- All 50 configured tickers have embedded chunks in local Qdrant.
- Annual-report layout recovery now covers `MS`, `MCD`, `INTC`, `COST`, `GE`, and `HON`.
- Local Qdrant indexes `9,703` chunks.
- `financial_table` chunks are available for 39 searchable tickers.

The `/supported-tickers` endpoint returns the live searchable ticker list from embedded chunks, not the full configured list.

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
| `GET` | `/health/live` | Process liveness |
| `GET` | `/health/ready` | Pipeline readiness; returns `503` until ready |
| `GET` | `/health` | Legacy frontend-compatible readiness payload |
| `POST` | `/query` | Non-streaming RAG answer |
| `POST` | `/query/stream` | SSE streaming RAG answer |
| `POST` | `/query/decomposed` | Comparative or complex RAG answer |
| `GET` | `/supported-tickers` | Supported tickers and sections |
| `GET` | `/cache/stats` | Semantic cache metrics |
| `POST` | `/cache/clear` | Clear semantic cache when explicitly enabled |
| `POST` | `/cache/test` | Rate-limited query embedding comparison |
| `GET` | `/session/{session_id}/history` | Inspect conversation history |
| `DELETE` | `/session/{session_id}` | Clear one conversation session |

The two non-streaming query endpoints enforce a 60-second request timeout and return HTTP `504` when exceeded. Timed-out synchronous workers are abandoned so they cannot hold the response open, but Python cannot safely kill a thread already running; that worker may finish in the background and its result is discarded.

The three LLM query routes share per-IP limits of `10/minute` and `100/day`; decomposed queries also have a `5/minute` limit because each request can make multiple provider calls. `/cache/test` is limited to `10/minute`, and `/cache/clear` returns `403` unless `ENABLE_CACHE_CLEAR=true`. Limits use in-memory storage, matching the required single-worker local-Qdrant runtime. A multi-instance deployment must use shared rate-limit storage such as Redis.

Rate-limit identity uses the ASGI client address by default. When deploying behind a reverse proxy such as ngrok or a Docker gateway, set `TRUSTED_PROXY_CIDRS` to that proxy's comma-separated CIDR ranges (for example `203.0.113.0/24,10.0.0.0/8`). Only requests whose socket peer falls inside those ranges have `X-Forwarded-For` honored, and the header is then walked right-to-left past trusted hops to the first non-trusted client address. A malformed header, an untrusted peer, or an empty configuration all fall back to the socket peer, so direct clients cannot choose their rate-limit bucket by forging headers.

Session history returns the full stored assistant answer for each of the five retained turns, so reloading the frontend does not truncate earlier responses. LLM rewrite context already used the full stored messages independently of this API representation.

Example request:

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What was Apple total revenue in 2024?",
    "ticker": "AAPL",
    "section": "financial_table",
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

This design improved context precision and fixed a no-filter AWS query that previously returned Microsoft cloud context above Amazon evidence. High-confidence financial table lookups use structured row matching before final formatting, which promotes exact table evidence above semantically similar but wrong chunks.

## Generation Design

The generator uses a strict financial analyst prompt:

- Use only retrieved SEC filing context.
- Cite factual claims with `[Source N]`.
- Do not use general knowledge.
- Do not infer beyond the provided context.
- Quote numbers exactly as they appear in the retrieved context.
- Return an explicit insufficient-context fallback when evidence is missing.

LLM provider:

| Provider | Status |
|---|---|
| Groq | Only LLM provider; serves `openai/gpt-oss-120b` |

## Evaluation Results

Latest priority-1 and priority-2 LLM-as-judge run, using Groq `llama-3.3-70b-versatile` as judge:

| Metric | Score |
|---|---:|
| Faithfulness | `0.8533` |
| Answer relevancy | `0.9300` |
| Context precision | `0.4670` |
| Overall judge average | `0.7501` |
| Citation correctness | `1.0000` |
| Recall proxy | `1.0000` |
| Fallback accuracy | `1.0000` |

Coverage:

- `30/30` priority <= 2 cases completed with no skipped records.
- Covered categories: fact lookup `8/8`, summary `6/6`, enumeration `4/4`, comparative `6/6`, multi-hop `3/3`, out-of-corpus `3/3`.

Interpretation:

- Achieved `0.85` faithfulness, `0.93` answer relevancy, and `1.00` recall proxy across 30 cases spanning 6 query categories.
- Overall context precision remains the primary optimization target: correct answers are reliably retrieved, but retrieval still includes extra non-essential chunks.
- Balance-sheet `total X` questions use a lightweight structured lookup over financial-table row labels before semantic re-ranking. This fixes known total-assets retrieval failures without regenerating table chunks; Microsoft total-assets year-over-year now answers with `619,003`, `512,163`, and the computed increase `106,840`.
- Multi-hop improved most significantly after structured lookup: category faithfulness moved from `0.50` to `0.83`, with Microsoft total-assets year-over-year now scoring `1.00/1.00/0.50` instead of the previous `0.00/0.20/0.00`.
- The fresh checkpoint-resumed run confirms the Microsoft auditor retrieval fix: it answers `Deloitte & Touche LLP` with citation correctness and recall proxy both at `1.00`. The judge still scored that case's faithfulness and context precision at `0.00` while claiming the auditor evidence was absent, so the aggregate keeps the measured score unchanged and treats this case as a judge/context-window outlier rather than manually correcting it.
- Extended validation: 6 additional `priority=3` cases for `V`, `MA`, `LLY`, `KO`, and `RTX` were judged separately after the official N=30 run. They confirm structured lookup generalizes to new tickers: `V`, `MA`, and `LLY` total-assets cases all scored `1.00` faithfulness, and the RTX total-net-sales trend case also scored `1.00` faithfulness. One outlier, Coca-Cola competition risk factors, scored `0.50/0.60/0.20` despite recall `1.00` because retrieved context discussed competition only indirectly and included extra risk-factor context. The checkpoint-merged N=36 aggregate is not used as the official benchmark because it reused stale N=30 records, including the pre-fix MSFT auditor recall record.
- Latency from the 30-case judge run is not used as a performance benchmark because Groq returned repeated `429 Too Many Requests` responses and SDK backoff delays during generation/judging.
- A smaller `llama-3.1-8b-instant` judge was rejected after producing false negatives on exact numbers that were present in context.

## Performance Notes

Retrieval latency optimization:

- Optimized retrieval latency by about `52%` (`0.86s -> 0.41s` per query) through evidence-based tuning of `candidate_pool` (`20 -> 10`) and cross-encoder `batch_size` (`32 -> 4`).
- Validated with deterministic recall sweeps and LLM-judge evaluation: the broader 30-case priority <= 2 run reached recall proxy `1.0000` in every measurable category.
- Qdrant local is the default Docker/runtime target: Qdrant Cloud added about `0.30s` per retrieve call in measured network latency (`0.737s` cloud vs `0.444s` local at `candidate_pool=10`).
- On the Legion RTX 5060 environment, installing the CUDA 12.8 PyTorch build changed embedding from CPU to GPU (`cuda:0`) and measured throughput improved from about `2.7` to `23.3` chunks/sec on a 100-chunk sample.

Corpus scale:

- The configured corpus targets `50` tickers, and all `50` have searchable embedded chunks in local Qdrant.
- Local Qdrant indexes `9,703` chunks after annual-report recovery and table restoration.
- The local collection now has a trusted schema-v2 build manifest tied to the
  immutable generation `nomic-e9b6763-annual-report-rebuild-20260818-attempt-05`,
  Nomic revision `e9b6763023c676ca8431644204f50c2b100d9aab`, and canonical
  corpus fingerprint `sha256:dc44c9266856b044e8e928a0681f6f05a5e4889a3217c8eae3cdd0b080d391e2`.
  Local runtime and Docker Compose pin the same model revision through
  `EMBEDDING_MODEL_REVISION` so query embeddings cannot silently drift.
  This trust status applies only to local Qdrant; Cloud remains untrusted until
  full ID, payload, and vector-snapshot verification is completed.
- `financial_table` chunks are available for `39` searchable tickers.
- Latest extraction quality is `41` filings with all four target sections and `9` degraded but searchable filings; no configured ticker is currently unusable.

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
GROQ_API_KEY2=optional_second_serving_key
GROQ_API_KEY_FALL_BACK=optional_first_evaluation_generation_key
GROQ_API_KEY_FALL_BACK2=optional_second_evaluation_generation_key
QDRANT_MODE=local
QDRANT_LOCAL_PATH=data/processed/qdrant
QDRANT_INDEX_MANIFEST_PATH=data/processed/qdrant_index_manifest.json
QDRANT_CLOUD_URL=
QDRANT_CLOUD_API_KEY=
EMBEDDING_MODEL_ID=nomic-ai/nomic-embed-text-v1.5
EMBEDDING_MODEL_REVISION=<exact-hugging-face-commit>
EMBEDDING_GENERATIONS_DIR=data/embedding_generations
EMBEDDING_GENERATION_PATH=data/embedding_generations/<generation-id>
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
LLM_RATE_LIMIT_BURST=10/minute
LLM_RATE_LIMIT_DAILY=100/day
DECOMPOSED_RATE_LIMIT=5/minute
CACHE_TEST_RATE_LIMIT=10/minute
ENABLE_CACHE_CLEAR=false
TRUSTED_PROXY_CIDRS=
```

`ALLOWED_ORIGINS` is a comma-separated allowlist. Add the final Vercel domain before public deployment; do not use `*`. `TRUSTED_PROXY_CIDRS` is empty by default; set it to the proxy CIDR ranges only when the API runs behind ngrok or another reverse proxy, as described in the rate-limit section above.

Build local artifacts in order:

```powershell
.venv\Scripts\python.exe -m scripts.download_filings
.venv\Scripts\python.exe -m scripts.chunk_filings
.venv\Scripts\python.exe -m scripts.add_table_chunks
.venv\Scripts\python.exe -m scripts.embed_chunks --generation-id <generation-id>
.venv\Scripts\python.exe -m scripts.index_chunks
```

`EMBEDDING_MODEL_REVISION` is required for trusted embedding and index rebuilds.
`scripts.embed_chunks` creates a new immutable directory under
`EMBEDDING_GENERATIONS_DIR`; the generation ID must be safe and unused. It writes
each file atomically and publishes its completion manifest only after reloading
and validating every output from disk. Failed or incomplete generations are
retained for audit and are never resumed or selected automatically.
Use `--reuse-from <completed-generation>` to reuse vectors only when the pinned
model metadata, file hash, vector shape, and canonical payload match exactly.

Set `EMBEDDING_GENERATION_PATH` to the completed generation before running
`scripts.index_chunks`. Indexing has no fallback to canonical embedded JSONL: it
recomputes file, corpus, and vector fingerprints, verifies the active canonical
corpus identity, and rejects invalid generations before opening Qdrant. The index
manifest schema binds the validated generation fingerprint and takes model
provenance directly from its manifest. It is published only after the final
Qdrant point count is verified. If collection mutation fails, the old index
manifest remains absent instead of making a stale trust claim.

Run a smoke test:

```powershell
.venv\Scripts\python.exe -m scripts.diagnostics.rag_smoke_test
```

Run evaluation:

```powershell
.venv\Scripts\python.exe -m scripts.run_evaluation
```

## Continuous Integration

GitHub Actions runs separate path-filtered quality gates for the backend and
frontend. The backend job uses Python 3.12 with CPU-only PyTorch, runs the full
quota-free test suite, and compiles `src`, `scripts`, and `configs`. Hugging Face
offline flags prevent accidental model downloads. The frontend job uses the
project-pinned Bun `1.3.14`, installs from `bun.lock`, type-checks, runs Vitest,
and builds the production bundle.

Run the same checks locally:

```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
.venv\Scripts\python.exe -m compileall src scripts configs
```

```bash
cd frontend
bun install --frozen-lockfile
bun run lint
bun run test
bun run build
```

Use `bun run test`, not `bun test`: the latter invokes Bun's native test runner
instead of the repository's configured Vitest/jsdom environment.

## Running With Docker

Prerequisites: Docker Desktop installed and running, plus corpus artifacts already built locally under `data/processed/`.

1. Copy `.env.example` to `.env` and fill in `GROQ_API_KEY`. `GROQ_API_KEY2` is an optional serving key. `GROQ_API_KEY_FALL_BACK` and `GROQ_API_KEY_FALL_BACK2` form the optional evaluation-generation pool; evaluation falls back to the primary pair when both are blank. Each pool rotates keys round-robin and cools down a key after a Groq `429` before retrying another key.

2. Build and run the backend:

```bash
docker compose build
docker compose up
```

3. Verify the API is ready:

```bash
curl http://localhost:8000/health/ready
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

In cloud mode, the API scrolls chunk payloads from Qdrant at startup to rebuild
the in-memory BM25 index and structured-lookup inputs. A hosted container does
not need the git-ignored `data/processed/` directory when the cloud collection
contains complete payloads.

## Zero-Cost Public Demo

The frontend can remain online on Vercel while the backend runs locally through
the reserved ngrok endpoint. Visitors need only open the Vercel site; the owner
must start Docker and ngrok before a demo session.

Demo frontend: `https://frontend-one-gamma-f9jf11u8ec.vercel.app`

The workspace supports full legal company names, professional section labels,
streamed conversation cards, collapsible filing evidence, Overview/Conversation
navigation without deleting history, viewport-safe help tooltips, and a desktop
sidebar that can be resized from `280` to `480` pixels.

```powershell
.\scripts\start_demo.ps1
```

Stop all local demo services afterward:

```powershell
.\scripts\stop_demo.ps1
```

Configure Vercel with:

```text
VITE_API_BASE_URL=https://blog-making-bloated.ngrok-free.dev
```

Add the exact Vercel production origin to `ALLOWED_ORIGINS` in `.env`. The demo
frontend remains reachable when the local backend is offline, but queries
require the owner's machine, Docker Desktop, and ngrok tunnel to be running.

## Repository Structure

```text
configs/              Environment-backed project settings
frontend/             Independently deployed Vite/React/TypeScript client
scripts/              Data pipeline, indexing, smoke test, and evaluation entry points
src/api/              FastAPI application
src/evaluation/       LLM-as-judge evaluation framework
src/generation/       RAG generation, streaming, and decomposition foundation
src/ingestion/        SEC download, section extraction, and chunking
src/memory/           Conversation memory and query rewriting
src/retrieval/        Embeddings, vector store, hybrid retrieval, and semantic cache
tests/                Unit tests
ARCHITECTURE.md        Stable system design and component boundaries
PROJECT_STATE.md      Detailed engineering handoff and milestone notes
AGENTS.md             Stable operating guide for AI coding agents
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
| Query decomposition | Integrated and validated for comparative and enumeration queries |
| Docker deployment | Complete; CPU-only image supports local Qdrant or stateless Qdrant Cloud startup |
| Vite frontend | Deployed on Vercel with Overview/Conversation navigation, evidence inspection, and resizable desktop controls; verified against the local Docker backend through the reserved ngrok URL |

## Known Limitations

- The corpus targets `50` companies and all `50` are searchable; extraction remediation recovered the `6` filings that previously failed section extraction, leaving `41` filings with all four target sections and `9` degraded but searchable.
- Extraction quality remains uneven across large-company filing layouts: some annual-report cross-reference and non-standard Item 7/8 formats expose fewer than the four target sections.
- Financial statements can become verticalized after HTML-to-text conversion; table extraction and structured lookup reduce this issue for common total-line financial questions.
- Hybrid retrieval improves source quality but adds CPU latency due to cross-encoder re-ranking.
- Semantic cache and conversation memory are currently in-memory and are lost on process restart.
- Multi-turn query rewriting adds one LLM call for follow-up questions.
- The API has no authentication. CORS allowlisting, per-IP rate limits, input validation, and generic error messages mitigate abuse but are not access control; any client that knows the URL can call the public routes (see `ARCHITECTURE.md`).
- Groq free tier can return `429 Too Many Requests`; SDK retries can recover but increase latency.
- Docker runs CPU-only for portability. Local development on the Legion RTX 5060 can use CUDA for faster embedding generation.

## Roadmap

1. Add production logging, quota monitoring, and error alerts before selecting a paid always-on backend.
2. Improve annual-report/cross-reference extraction layouts to close the remaining section-completeness gaps.
3. Revisit permanent hosting only when always-on public availability is required.

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
