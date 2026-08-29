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
- Annual-report layout recovery covers `MS`, `MCD`, `INTC`, `COST`, `GE`,
  and `HON`; the FY2026 recovery pass additionally restored
  `financial_statements` for `NOW`, `NVDA`, `ORCL`, and `PEP` plus `mdna`
  for `PFE`.
- Local Qdrant indexes `10,053` chunks from trusted generation
  `nomic-e9b6763-fy2026-ibm-companion-20260829`.
- Extraction quality is `46` filings with all four target sections and
  `4` degraded but searchable filings (`CVX`, `IBM`, `JPM`, `XOM`).
- `financial_table` chunks are available for all `50` searchable tickers; CVX,
  JPM, and XOM use verified same-document statement intervals, while IBM uses
  its uniquely linked, page-bounded Annual Report companion.

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
- For trends and comparisons, inspect all provided sources and quote every
  relevant period/value pair; do not answer with only a percentage when exact
  underlying values are available.
- Use only canonical `[Source N]` citations; line-number citation formats are
  invalid. Keep the fiscal period and sign attached to every numeric claim.
- Do not invent enumeration categories from general knowledge; include only
  categories supported by the filing excerpts.
- Return an explicit insufficient-context fallback when evidence is missing.

LLM provider:

| Provider | Status |
|---|---|
| Groq | Only LLM provider; serves `openai/gpt-oss-120b` |

## Evaluation Results

Historical completed benchmark: the two-phase pipeline (offline Phase 1
frozen retrieval artifact, then frozen-evidence generation and judging) over
all `30` priority <= 2 cases, using `openai/gpt-oss-120b` for both generation
and judging. All `30` generations and `30` judgments completed with no skips
or parse failures under the schema-v1 binding. A later renderer audit found
that this run's `selective_packed_v1` label applied packed context to judging
but generation still received full evidence. The table below remains a
reproducibility record, but it is not a current validation of packed generation
and must not be compared directly with corrected schema-v2 runs.
The active local index uses the IBM companion-recovery generation
`nomic-e9b6763-fy2026-ibm-companion-20260829` (corpus
`sha256:1d5b99ed…`, `10,053` points). The published Phase 2 scores remain bound
to the historical schema-v1 Phase 1 artifact `sha256:8283b628…`, which
completed all 30 priority <= 2 cases with 61 non-empty queries. A later
fact-specific audit correctly classifies its AWS comparative branch as the one
retrieval miss (`11/12 evidence_ok`). The separate priority-3 replay covers 22
recovery cases at keyword recall `1.0000`. The current-corpus Phase 2 run
completed officially with one binding and no skipped or failed records. The
judge was rerun after correcting a context
boundary bug that could split SEC chunks at internal blank lines; the judge
checkpoint now fingerprints this renderer. The three-case probe was run first
as a quota preflight and remains non-official self-judge evidence.

| Metric | Score |
|---|---:|
| Faithfulness | `0.9793` |
| Answer relevancy | `0.9733` |
| Context precision | `0.6197` |
| Overall judge average | `0.8574` |
| Citation correctness | `1.0000` |
| Recall proxy | `1.0000` |
| Fallback accuracy | `1.0000` |

Category table (faithfulness / relevancy / precision):

| Category | N | Scores |
|---|---:|---|
| fact_lookup | 8 | `1.0000 / 1.0000 / 0.7500` |
| summary | 6 | `0.9867 / 0.9917 / 0.8333` |
| enumeration | 4 | `1.0000 / 0.8500 / 0.5925` |
| comparative | 6 | `0.9933 / 0.9917 / 0.4533` |
| multi_hop | 3 | `1.0000 / 1.0000 / 0.8333` |
| out_of_corpus | 3 | `0.8333 / 0.9667 / 0.0000` |

Official historical binding: artifact `sha256:8283b628…`, Phase 2 binding
`sha256:680e0370…`, with `30/30` generation and `30/30` judgment records.
Deterministic checks remain citation correctness `1.0000` (`29` scored cases),
recall proxy `1.0000` (`24` scored cases), and fallback accuracy `1.0000`.
Token usage for the judge rerun was `65,435` judging prompt + `15,716`
judging completion tokens; generation resumed from the existing checkpoint.

An offline answer-integrity audit is available through
`python -m scripts.diagnostics.answer_integrity_audit`. It checks all 30
answers for canonical citations, source-range validity, legacy line citations,
and numeric claims absent from cited evidence. Its review flags are diagnostic
and are intentionally not substituted for semantic judge scores.

The current retrieval follow-up includes a shared deterministic query shaper
for direct and decomposed paths. In an offline counterfactual, the original
`Amazon AWS growth` query missed the AWS FY2024/FY2025 values, while the shaped
query retrieved the correct chunk at rank 1 with both `107,556` and `128,725`.
The Phase 1 executor now applies the same shaper and records both the original
effective query and actual retrieval query. Artifact schema v2 fingerprints the
shaper rules; Phase 2, the quota probe, and the answer sentinel refuse a Phase
1 artifact without the matching provenance. The `sha256:8283b628…` artifact
therefore remains a historical benchmark binding. The offline 61-subquery A/B
shaped only two AWS queries, introduced zero ticker leaks or required-term
regressions, and serialized byte-identically across repeated runs.
A field-aware lexical ladder now consumes only explicit shaper hints and merges
the first non-empty `exact_phrase -> full_terms -> partial_terms -> fuzzy` tier
into RRF. Filters are applied before matching; fuzzy requires a ticker and runs
only after all exact tiers miss. Its full 61-subquery A/B produced zero ticker
leaks, zero required-term regressions, and byte-identical reports across two
runs. The 59 unhinted queries remained byte-stable, while both AWS queries kept
the fact-bearing chunk at rank 1. Artifact provenance now binds both shaper and
ladder fingerprints.

The active offline Phase 1 artifact is now schema v2
`sha256:986991219560…` (file SHA-256 `15ff6eb08aaa…`). It was rebuilt twice
with byte-identical output over 30 cases and 61 non-empty queries. Ticker
leakage is zero, the AWS comparative branch stores the shaped retrieval query
and retrieves `mdna_0012` at rank 1 with both required values, and the
decomposed evidence audit passes `12/12`. Phase 2 runners pin this artifact,
but no provider-backed full N=30 Phase 2 result exists on it yet; the published
scores above remain bound to the historical artifact. The comparative-only A/B
below is deliberately non-official.

Comparative context packing v3 has passed a provider-free offline gate on this
active artifact. It keeps the first two unique chunks from every decomposition
branch and retains structured hits plus required-fact donors. The gate passed
`30/30` evidence coverage, `30/30` exact source boundaries, `24/24`
non-comparative byte stability, and `6/6` comparative branch coverage, while
reducing comparative rendered evidence from `20,939` to `10,211` tokens
(`51.23%`; pre-registered minimum `25%`). Two runs produced byte-identical
reports. The strategy is available only as the explicit experimental
`comparative_packed_v3` Phase 2 option; `selective_packed_v1` remains the
default until a separately authorized comparative-only provider A/B passes.
No published score changed in this offline milestone.

That comparative-only provider A/B has now completed as a non-official NO-GO.
An integrity audit first corrected the runner so generation, deterministic
metrics, and judging all consume the same rendered context; generation
checkpoints now fingerprint that renderer. Both arms then completed `6/6`
generation and `6/6` judging with no skips. V3 cut evidence tokens by `51.23%`
and improved context precision `0.5550 -> 0.7783` (`+0.2233`), while
faithfulness stayed within the pre-registered bound and overall judge average
rose `0.8461 -> 0.8928`. It was not admitted because answer relevancy fell
`0.9833 -> 0.9067` (`-0.0766`) and the AWS answer omitted the required
`107,556` and `128,725` values. The earlier packing results remain historical:
they passed packed evidence to the judge but not to generation, so they must not
be used as evidence that packed generation was validated. The Phase 2 default
therefore remains `selective_packed_v1`, pending a new corrected benchmark.

Comparative packing v4 is the provider-free follow-up to that NO-GO. It replaces
blind top-2 retention with branch top-1 plus only a missing query-intent or
explicit fact donor. On the same active artifact it passes `30/30` evidence and
source-boundary checks, keeps all `24` non-comparative contexts byte-identical,
and satisfies all six comparative branch contracts. It retains the previously
missed AMZN security-incidents and Microsoft high-level Cloud-growth chunks,
keeps both AWS values, and drops the off-topic Apple international-risk support
chunk. Comparative evidence is `6,737` tokens versus `20,939` full evidence
(`67.83%` reduction). V4 is offline-only and is not exposed as a Phase 2 arm;
the next provider gate is an AWS-only exact-number generation sentinel.

The AWS-only v4 sentinel has now passed. It completed `1/1` generation and
`1/1` judging with one provider call per phase and produced a grounded,
canonical-citation answer containing AWS `107,556` in 2024 and `128,725` in
2025. Faithfulness and Answer Relevancy were both `1.00`; Context Precision was
`0.67`; deterministic citation correctness, recall proxy, and fallback
correctness were all `1.00`. The run is non-official and stored under ignored
`data/eval_artifacts/aws_numeric_v4_summary.json` (file SHA-256
`792e9b94511319ada7ef98902398c9a0860dde39e6edf2ec41ce9585a9f3932f`).
It can be reproduced after a quota reset with
`python -m scripts.run_aws_numeric_sentinel --fresh`.
Generation checkpoint schema v3 now fingerprints the active system prompt in
addition to the user template and context renderer, so prompt changes cannot
reuse stale answers. The next step is a new pre-registered six-case v5 versus
full-evidence provider A/B; v5 remains experimental for Phase 2 until that
gate passes.

Comparative context packing v5 is the current provider-free improvement. It
uses an oracle-free selector shared with production `/query/decomposed`: each
company branch keeps its leader, structured hits, and only a filing-phrase or
missing-intent donor. If selection would drop a company branch or leave fewer
than two chunks, production safely keeps the full context. The Microsoft Cloud
trend query shaper supplies the filing-native phrase needed to retain the
aggregate `Microsoft Cloud revenue increased 23% to $168.9 billion` evidence.
The v5 gate passes `30/30` evidence coverage and source boundaries, `24/24`
non-comparative byte stability, `6/6` branch coverage/contracts/known findings,
and `6/6` production/evaluation adapter parity. Comparative evidence falls
from `20,455` to `6,704` tokens (`67.23%`). The ignored report is
`data/diagnostics/comparative_packing_v5.json` (file SHA-256
`63169abbd872a97e4912f714ac0399d27a17056e697822dc9060b30dd9accbd5`). No
provider call or official-score change occurred.

Historical context-packing A/B (the pre-registration and confirmatory run used
the prior frozen Phase 1 artifact, paired per-case,
pre-registered merge gates): packing only the `fact_lookup`, `multi_hop`,
and `summary` categories moved context precision from `0.2872` to
`0.3983` (`+0.1111 >= +0.08`), kept recall proxy at `1.0000`, stayed
within the faithfulness significance bar (`-0.0350 >= -0.05`), and cut
rendered evidence tokens by `20.19%` (`>= 20%`). The packed-all variant
was rejected: it raised context precision further (`+0.1295`) but broke
the faithfulness bar (`-0.0800`) with regressions concentrated in
enumeration, comparative-topical, and out-of-corpus cases.

Interpretation:

- Judge-model confound: this table uses `openai/gpt-oss-120b` as a
  self-judge. It is substantially stricter than the previous official
  table's Groq `llama-3.3-70b-versatile` judge (`Faithfulness 0.8533`,
  overall `0.7501`), so the two tables must NOT be compared directly.
  The deterministic checks are model-independent and stay perfect under
  both judges: citation correctness, recall proxy, and fallback accuracy.
- The comparative Apple-vs-Amazon revenue question now pins fiscal year
  2024 inside the question itself, resolving the earlier year-ambiguity
  blocker; that case cites both FY2024 totals (`391,035`, `637,959`).
- Production generation states the fiscal year used whenever a question
  does not specify one, using the latest fiscal year available in the
  retrieved context.
- Multi-hop context precision improved from `0.1750` (full evidence) to
  `0.6667` under packing because required-number donors keep exactly the
  fact-bearing chunks.
- Out-of-corpus context precision is `0.0` by design: chunks retrieved
  for out-of-corpus questions are intentionally irrelevant because the
  correct behavior is abstention.
- Latency from these runs is not used as a performance benchmark because
  Groq returned repeated `429 Too Many Requests` responses and SDK retry
  backoff during judging.
- Historical note: an earlier `llama-3.1-8b-instant` judge was rejected
  after producing false negatives on exact numbers present in context.

## Performance Notes

Retrieval latency optimization:

- Optimized retrieval latency by about `52%` (`0.86s -> 0.41s` per query) through evidence-based tuning of `candidate_pool` (`20 -> 10`) and cross-encoder `batch_size` (`32 -> 4`).
- Validated with deterministic recall sweeps and LLM-judge evaluation: the broader 30-case priority <= 2 run reached recall proxy `1.0000` in every measurable category.
- Qdrant local is the default Docker/runtime target: Qdrant Cloud added about `0.30s` per retrieve call in measured network latency (`0.737s` cloud vs `0.444s` local at `candidate_pool=10`).
- On the Legion RTX 5060 environment, installing the CUDA 12.8 PyTorch build changed embedding from CPU to GPU (`cuda:0`) and measured throughput improved from about `2.7` to `23.3` chunks/sec on a 100-chunk sample.

Corpus scale:

- The configured corpus targets `50` tickers, and all `50` have searchable embedded chunks in local Qdrant.
- Local Qdrant indexes `10,053` chunks from the trusted IBM companion recovery
  generation `nomic-e9b6763-fy2026-ibm-companion-20260829`.
- The local collection has a trusted schema-v2 build manifest tied to the
  pinned Nomic revision `e9b6763023c676ca8431644204f50c2b100d9aab` and
  corpus fingerprint `sha256:1d5b99ed962ab9dff88f268ea17da4efd5c7128900961a123bdfb5e49716c8f4`.
  Local runtime and Docker Compose pin the same model revision through
  `EMBEDDING_MODEL_REVISION` so query embeddings cannot silently drift.
  This trust status applies only to local Qdrant; Cloud remains untrusted until
  full ID, payload, and vector-snapshot verification is completed.
- `financial_table` chunks are available for all `50` searchable tickers.
- Latest extraction quality is `46` filings with all four target sections and `4` degraded but searchable filings (`CVX`, `IBM`, `JPM`, `XOM`); no configured ticker is currently unusable.

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
GROQ_API_KEY3=optional_third_failover_key
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

Run the two-phase evaluation (Phase 1 builds a deterministic offline
retrieval artifact; Phase 2 generates and judges against frozen evidence
with checkpointed, binding-verified resume):

```powershell
.venv\Scripts\python.exe -m scripts.run_evaluation_phase1 --priority 2 --output data/eval_artifacts/phase1_priority2.json --verify-determinism
.venv\Scripts\python.exe -m scripts.run_evaluation_phase2 --priority 2
```

The legacy single-phase runner remains available:

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

The backend suite is hermetic: a pytest socket guard fails any unmocked
external network call, and `live_network` tests are deselected by default.
Real SEC connectivity can be checked separately with the opt-in smoke
`python -m scripts.diagnostics.sec_live_smoke`.

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

1. Copy `.env.example` to `.env` and fill in `GROQ_API_KEY`. `GROQ_API_KEY2` and `GROQ_API_KEY3` are optional serving failover keys. `GROQ_API_KEY_FALL_BACK` and `GROQ_API_KEY_FALL_BACK2` form the optional evaluation-generation pool; evaluation falls back to the primary pair and then `GROQ_API_KEY3` when the dedicated pair is blank. Each pool rotates keys round-robin and cools down a key after a Groq `429` before retrying another key.

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

- The corpus targets `50` companies and all `50` are searchable; extraction remediation plus the FY2026 recovery pass restored `10` previously incomplete filings, leaving `46` filings with all four target sections and `4` degraded but searchable (`CVX`, `IBM`, `JPM`, `XOM`).
- Extraction quality remains uneven across large-company filing layouts: some annual-report cross-reference and non-standard Item 7/8 formats expose fewer than the four target sections.
- Financial statements can become verticalized after HTML-to-text conversion; table extraction and structured lookup reduce this issue for common total-line financial questions.
- Hybrid retrieval improves source quality but adds CPU latency due to cross-encoder re-ranking.
- Semantic cache and conversation memory are currently in-memory and are lost on process restart.
- Multi-turn query rewriting adds one LLM call for follow-up questions.
- The API has no authentication. CORS allowlisting, per-IP rate limits, input validation, and generic error messages mitigate abuse but are not access control; any client that knows the URL can call the public routes (see `ARCHITECTURE.md`).
- Groq free tier can return `429 Too Many Requests`; SDK retries can recover but increase latency.
- Docker runs CPU-only for portability. Local development on the Legion RTX 5060 can use CUDA for faster embedding generation.

## Roadmap

1. Improve comparative and enumeration grounding using deterministic evidence-shape
   diagnostics and per-case answer/citation review; require a pre-registered gate
   before changing retrieval, reranking, or context packing.
2. Add production logging, quota monitoring, and error alerts before selecting a paid always-on backend.
3. Expand deterministic evaluation coverage across the clean extended corpus without changing the official benchmark contract.
4. Revisit permanent hosting only when always-on public availability is required.

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
