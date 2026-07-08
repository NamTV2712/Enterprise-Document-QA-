# Project State

## Current Milestone

Steps 1-11 are complete for the MVP Enterprise Document QA / SEC 10-K RAG pipeline.
Phase 2A Step A, Streaming Response, is complete and verified.
Phase 2A Step A.1, Semantic Query Cache, is complete and verified.
Phase 2B Step C, Multi-turn Conversation with Memory, is complete and verified.
Phase 2B Step D, Query Decomposition, is integrated and verified for comparative queries.
Phase 2C Muc 2, deterministic evaluation metrics and enumeration retrieval diagnosis, is complete.
Phase 2C Muc 3, 30-case categorized evaluation set and decomposer-routed evaluation, is implemented. Full 30-case LLM-judge run is blocked by Groq free-tier quota.

Latest completed milestone commit:

```text
40175e5 Add multi-turn conversation memory
```

Recent completed commits:

```text
40175e5 Add multi-turn conversation memory
aad9a79 Document semantic cache completion
a697787 Add semantic query cache
db20e51 Update project state for BM25 optimization
29c3af3 Optimize BM25 chunk lookup
1df86d4 Update project state for streaming
b8e8fdb Add streaming query endpoint
8f440b7 Tidy SEC client comments
8b63374 Update README for hybrid retrieval
383272b Add hybrid retrieval reranking
79c7228 Document Step 10 completion
```

## Project Goal

Build an Enterprise Document QA system over SEC 10-K filings using a RAG pipeline:

```text
SEC Filing -> Section Extraction -> Chunking -> Embedding -> Query Rewrite -> Qdrant/BM25 -> Hybrid Retrieval -> Re-ranking -> Semantic Cache/Memory -> LLM Answer -> FastAPI/SSE
```

The MVP corpus currently covers latest 10-K filings for:

- AAPL
- MSFT
- AMZN

The system answers finance/document questions using retrieved filing context and citations, with explicit fallback when the available context is insufficient.

## Current Architecture

- `src/ingestion/sec_client.py`
  SEC EDGAR client for ticker-to-CIK lookup, filing metadata retrieval, rate-limited filing downloads, and SEC-specific exceptions.
- `src/ingestion/section_extractor.py`
  HTML-to-text conversion, text cleanup, and robust extraction of target 10-K sections.
- `src/ingestion/chunker.py`
  Recursive token-aware chunker for extracted sections.
- `src/retrieval/embedder.py`
  Nomic embedding wrapper using required document/query prefixes.
- `src/retrieval/vector_store.py`
  Qdrant wrapper for local persistent vector storage, upsert, metadata filters, and semantic search.
- `src/retrieval/retriever.py`
  Retrieval abstraction combining Embedder + VectorStore and returning clean `RetrievedChunk` objects.
- `src/retrieval/hybrid_retriever.py`
  Hybrid retriever combining BM25 keyword search, Qdrant semantic search, Reciprocal Rank Fusion, and cross-encoder re-ranking. Supports pre-computed query embeddings for cache-aware retrieval.
- `src/retrieval/semantic_cache.py`
  In-memory filter-aware semantic cache for full RAG responses and sources.
- `src/memory/conversation_memory.py`
  In-memory conversation session store with TTL cleanup and a small interface intended for future SQLite/Redis replacement.
- `src/memory/query_rewriter.py`
  LLM-powered follow-up query rewriter that converts pronoun-based questions into standalone retrieval queries.
- `src/generation/generator.py`
  LLM wrapper for non-streaming and streaming RAG answer generation with strict anti-hallucination prompt and optional conversation history. Current default provider is Groq.
- `src/generation/rag_pipeline.py`
  End-to-end RAG pipeline combining Retriever + Generator, including semantic cache checks, conversation memory, query rewriting, and `query_stream()` for SSE events.
- `src/evaluation/evaluator.py`
  LLM-as-judge evaluation for faithfulness, answer relevancy, and context precision, plus deterministic citation/fallback/recall-proxy checks.
- `src/evaluation/test_set.py`
  Fixed 30-case categorized evaluation set covering fact lookup, summary, enumeration, comparative, multi-hop, and out-of-corpus fallback questions.
- `src/api/app.py`
  FastAPI service exposing `/health`, `/query`, `/query/stream`, `/supported-tickers`, cache endpoints, session endpoints, and Swagger UI at `/docs`.
- `scripts/download_filings.py`
  Download and section extraction script.
- `scripts/chunk_filings.py`
  Chunk generation script.
- `scripts/embed_chunks.py`
  Embedding generation script.
- `scripts/index_chunks.py`
  Qdrant indexing script.
- `scripts/test_rag.py`
  Manual end-to-end RAG test script.
- `configs/settings.py`
  `.env`-backed settings and data paths.

## Implemented So Far

### Step 3: Section Extraction

Robust SEC 10-K extraction is complete and committed as:

```text
6b2f599 Robust SEC filing section extraction
```

Extracted sections:

- `business`
- `risk_factors`
- `mdna`
- `financial_statements`

Extractor behavior:

- Converts SEC HTML to text with BeautifulSoup/lxml.
- Removes `script` and `style` tags.
- Normalizes text and repairs known split headings, including `RIS\nK FACTORS`, `B\nUSINESS`, `FINANCIAL STATE\nMENTS`, and `INC\nOME`.
- Uses section-specific start/end boundaries.
- Rejects table-of-contents false matches via minimum section length.
- Skips self-reference matches such as `Risk Factors of this Annual Report`.
- Handles MD&A boundary before MSFT management responsibility/report sections.
- Strips trailing page/header noise only at section ends.

Validation:

- AAPL/MSFT/AMZN: all 12 section starts and ends manually validated.
- GOOGL latest 10-K generalization check passed with no warnings.
- Extraction quality is sufficient for MVP retrieval/RAG.

Remaining extraction limitations:

- Designed specifically for 10-K filings, not 10-Q/8-K/Forms 3/4/5.
- Not yet validated across 40-80 companies.
- No automated unit tests for extraction edge cases yet.
- Financial statement tables are usable but verticalized.

### Step 4: Chunking

Chunking is complete and committed as:

```text
cabd268 Add SEC filing chunking
```

Implemented files:

- `src/ingestion/chunker.py`
- `scripts/chunk_filings.py`

Chunking design:

```python
CHUNK_CONFIG = {
    "business": {"chunk_size": 500, "overlap": 75},
    "risk_factors": {"chunk_size": 500, "overlap": 75},
    "mdna": {"chunk_size": 500, "overlap": 75},
    "financial_statements": {"chunk_size": 900, "overlap": 100},
}
SEPARATORS = ["\n\n", "\n", ". ", " "]
```

Important implementation details:

- Uses `tiktoken` `cl100k_base` for token counting.
- Uses recursive splitting: paragraph -> line -> sentence -> word/token fallback.
- Uses larger chunks for `financial_statements` to reduce label/value table breakage.
- Guarded against `overlap >= chunk_size`.
- Counts tokens on the final joined chunk text, not just a sum of unit token counts. This prevents BPE/tokenizer boundary bugs where the final chunk exceeds the configured limit.
- If overlap plus the next unit would exceed the limit, overlap is dropped for that boundary to preserve hard token limits.

Chunk output files are generated locally under `data/processed/{TICKER}/` and are ignored by git because `data/` is ignored:

- `data/processed/AAPL/000032019325000079_chunks.jsonl`
- `data/processed/AMZN/000101872426000004_chunks.jsonl`
- `data/processed/MSFT/000095017025100235_chunks.jsonl`

Chunk counts:

| Ticker | Section | Chunks |
|---|---:|---:|
| AAPL | business | 7 |
| AAPL | financial_statements | 21 |
| AAPL | mdna | 10 |
| AAPL | risk_factors | 31 |
| AMZN | business | 7 |
| AMZN | financial_statements | 38 |
| AMZN | mdna | 23 |
| AMZN | risk_factors | 27 |
| MSFT | business | 21 |
| MSFT | financial_statements | 32 |
| MSFT | mdna | 23 |
| MSFT | risk_factors | 31 |

Chunk validation:

- Total chunks: 271.
- Min tokens: 125.
- Max tokens: 900.
- Token limit violations: 0.
- MSFT `Total assets` appears in `MSFT_000095017025100235_financial_statements_0000`, token count 897.
- `Total liabilities` is in the adjacent next chunk, which is acceptable for MVP retrieval.
- Overlap was confirmed between adjacent AAPL `risk_factors` chunks.

### Step 5: Embeddings

Embedding pipeline is complete and committed as:

```text
544ddb7 Add local embedding pipeline
```

Implemented files:

- `src/retrieval/embedder.py`
- `scripts/embed_chunks.py`

Model selected:

```text
nomic-ai/nomic-embed-text-v1.5
```

Reasoning:

- `BAAI/bge-base-en-v1.5` was tested first and rejected because `max_seq_length=512`, while financial statement chunks can be ~786 tokens under the model tokenizer after prefix.
- `nomic-ai/nomic-embed-text-v1.5` supports `max_seq_length=8192`, dimension 768, and safely handles the current 900-token financial statement chunks.

Model card requirements:

- Document/chunk prefix: `search_document: `
- Query prefix: `search_query: `

These prefixes are encapsulated in `Embedder` so future modules do not forget them.

Dependencies added:

- `sentence-transformers==5.6.0`
- `einops==0.8.2`

Embedding output files are generated locally and ignored by git:

- `data/processed/AAPL/000032019325000079_chunks_embedded.jsonl`
- `data/processed/AMZN/000101872426000004_chunks_embedded.jsonl`
- `data/processed/MSFT/000095017025100235_chunks_embedded.jsonl`

Embedding validation:

- AAPL: 69 chunks embedded.
- AMZN: 95 chunks embedded.
- MSFT: 107 chunks embedded.
- Total: 271 chunks embedded.
- Embedding dimension: 768 for every record.
- Missing embeddings: 0.
- CPU runtime for full embedding run: ~416 seconds.

Semantic sanity check:

```text
MSFT financial_statements_0000 vs financial_statements_0001: 0.8230
MSFT financial_statements_0000 vs business_0000: 0.6083
```

Interpretation: adjacent financial statement chunks are semantically closer than financial statement vs business, confirming embeddings are meaningful.

### Step 6: Vector Database

Qdrant vector indexing is complete and committed as:

```text
268c36e Add Qdrant vector indexing
```

Implemented files:

- `src/retrieval/vector_store.py`
- `scripts/index_chunks.py`

Dependency added:

- `qdrant-client==1.18.0`

Vector DB design:

- Qdrant local persistent mode under `data/processed/qdrant`.
- Collection name: `sec_filings`.
- Vector dimension: 768.
- Distance metric: Cosine.
- Payload includes `chunk_id`, `ticker`, `section`, `accession_number`, `filing_date`, `report_date`, `chunk_index`, `token_count`, and `text`.

Important implementation details:

- Uses deterministic UUIDs via `uuid.uuid5(uuid.NAMESPACE_URL, chunk_id)` instead of Python `hash()`, because `hash()` is randomized between Python processes.
- Batch upsert size is 100 to avoid local Qdrant request-size issues.
- Uses Qdrant `query_points` API because `client.search` is not available in `qdrant-client==1.18.0`.
- Adds `VectorStore.close()` and context manager support to avoid local client shutdown warnings/resource leaks.

Index validation:

```text
Collection info: {'vectors_count': 271, 'indexed_vectors_count': 0, 'points_count': 271, 'status': 'green'}
```

Note: `indexed_vectors_count=0` is normal for small local Qdrant collections below the HNSW indexing threshold. `points_count=271` is the important count.

Filtered search test:

Query:

```text
What are the main risk factors for Apple?
```

Filter:

```text
ticker=AAPL, section=risk_factors, top_k=3
```

Results had scores >0.73 and returned relevant AAPL risk factor chunks.

### Step 7: Retrieval Pipeline

Retrieval wrapper is complete and committed as:

```text
cb48532 Add retrieval pipeline wrapper
```

Implemented file:

- `src/retrieval/retriever.py`

Design:

- `Retriever` combines `Embedder.embed_query()` and `VectorStore.search()`.
- Uses dependency injection for `Embedder` and `VectorStore` to avoid repeated model loads and make testing easier.
- Returns `RetrievedChunk` dataclass with `chunk_id`, `ticker`, `section`, `filing_date`, `score`, `text`, and formatted `citation`.

Retrieval quality tests:

- Apple revenue with filters returned AAPL financial statement chunks; exact revenue chunk was present but not always rank 1.
- Microsoft revenue-source query returned relevant business chunks.
- Broad risk factor query returned risk factor sections across AAPL, AMZN, and MSFT.
- Amazon revenue/profit trend returned relevant MD&A results.
- Microsoft cloud dependency returned risk, MD&A, and cloud margin context.
- No-filter Apple revenue query returned 5/5 AAPL chunks, proving company discrimination works without hard ticker filtering.

Known retrieval limitation:

- Financial table retrieval can return related accounting/financial chunks above the exact numeric table chunk. This is expected with semantic retrieval over verticalized tables and should be documented in README/evaluation.

### Step 8: RAG Generation

RAG generation pipeline is complete and committed as:

```text
d2dc7f2 Add RAG generation pipeline
```

Implemented files:

- `src/generation/generator.py`
- `src/generation/rag_pipeline.py`
- `scripts/test_rag.py`

Dependencies added during Step 8/provider testing:

- `anthropic==0.111.0`
- `google-genai==2.9.0`
- `openai==2.43.0`
- `groq==1.5.0`

Current provider setup:

- Default provider: Groq.
- Default Groq model: `llama-3.3-70b-versatile`.
- Gemini provider is also supported.
- Default Gemini model: `gemini-2.5-flash-lite` for lower cost, but it returned temporary `503 UNAVAILABLE` during testing.
- `GROQ_API_KEY` and `GEMINI_API_KEY` are read from `.env` via `configs/settings.py`.

Provider status observed:

- Groq works with current key.
- Gemini `gemini-2.5-flash` worked in a small API test.
- Gemini `gemini-2.5-flash-lite` was selected for cost but returned `503 UNAVAILABLE` due to high demand in one test.
- Gemini older `2.0` models returned quota/permission issues for current key/project.
- OpenAI key currently appears to be an OpenRouter key (`sk-or-v1...`) and fails against OpenAI's default endpoint with `invalid_api_key`.

System prompt rules:

- Use only provided SEC filing context.
- Cite every factual claim as `[Source N]`.
- If context is insufficient, fallback exactly rather than guessing.
- Do not speculate or infer beyond context.
- Quote numbers exactly as they appear.
- Always respond in English.

End-to-end Groq RAG test results:

Apple revenue question:

```text
Q: What was Apple's total revenue in fiscal year 2024?
A: According to [Source 1] and [Source 2], Apple's total net sales for 2024 were $391,035.
```

Hallucination check:

- `$391,035` was found in Source 1: `AAPL_000032019325000079_financial_statements_0018`.
- `$391,035` was found in Source 2: `AAPL_000032019325000079_financial_statements_0005`.
- `391,035` was also found in Source 4: `AAPL_000032019325000079_financial_statements_0000`.
- Conclusion: no hallucination for Apple revenue.

Microsoft risk factors question:

- Answer synthesized multiple risk factor chunks with citations.
- Content included competition, privacy/data/AI scrutiny, cybersecurity, economic/geopolitical risks, pandemic/epidemic risk, and platform abuse.
- Result was good and source-grounded.

Amazon AWS revenue growth question:

- Model correctly used fallback because retrieved MD&A chunks did not explicitly contain AWS revenue growth.
- Important limitation: corpus likely contains AWS revenue/operating metrics elsewhere, but retrieval did not return the right numeric chunk for this query. This is a retrieval/evaluation issue, not a generation bug.

Tesla revenue fallback:

- Query: `What is Tesla's revenue in 2024?`
- No Tesla corpus exists.
- Model correctly responded that there was insufficient information and did not invent Tesla revenue.

Groq free-tier behavior:

- One `429 Too Many Requests` occurred during the Tesla fallback test.
- Groq SDK automatically retried after ~14 seconds and completed successfully.
- Document this in README as a known free-tier limitation.

### Step 9: Evaluation Framework

RAG evaluation framework is complete and committed as:

```text
a5c4d39 Add RAG evaluation framework
```

Implemented files:

- `src/evaluation/test_set.py`
- `src/evaluation/evaluator.py`
- `scripts/run_evaluation.py`

Evaluation design:

- Uses a fixed six-question test set.
- Uses Groq LLM-as-judge for faithfulness, answer relevancy, and context precision.
- Separates generation quality from retrieval quality.
- Saves local output to `data/evaluation_results.json`, ignored by git.

Latest evaluation averages:

| Metric | Score |
|---|---:|
| Faithfulness | 0.9000 |
| Answer relevancy | 0.9167 |
| Context precision | 0.3833 |
| Overall | 0.7333 |

Main evaluation insight:

- Answers are mostly faithful and relevant when the right evidence is retrieved.
- Context precision is weak because semantic retrieval often returns related but non-answer chunks, especially for broad/no-filter cloud questions and verticalized financial tables.
- Tesla/no-corpus fallback correctly returns insufficient-context behavior; context precision is expected to be 0 for that case.

### Step 10: FastAPI Service

FastAPI service is complete and committed as:

```text
ee6c3f6 Add FastAPI RAG service
```

Implemented files:

- `src/api/app.py`
- `src/api/__init__.py`

API endpoints:

- `GET /health`: service status and `pipeline_ready` flag.
- `POST /query`: RAG answer with model name, retrieved source previews, and chunk count.
- `GET /supported-tickers`: currently supported tickers and sections.
- `GET /docs`: Swagger UI.

Validation:

- `/health` returned `pipeline_ready: true`.
- `/docs` returned Swagger UI successfully.
- `/query` was tested with ticker+section filter, ticker-only filter, and no filter.

Measured endpoint latency:

| Request | Filter | Latency |
|---|---|---:|
| Apple revenue | `ticker=AAPL`, `section=financial_statements` | 1.2503s |
| Microsoft cybersecurity risks | `ticker=MSFT` | 1.2090s |
| AWS revenue growth | no filter | 5.8362s |

Latency insight:

- Query embedding plus vector search took about 0.14-0.18s.
- End-to-end latency was dominated by the Groq LLM API call.
- With Groq free tier, expected end-to-end latency is provider-dependent, often around 2-5s, and can spike when Groq returns `429 Too Many Requests` and retries.

No-filter retrieval issue observed:

- The AWS revenue-growth query returned an MSFT MD&A chunk as Source 1 with score 0.7576, above the relevant AMZN chunks.
- The LLM still answered correctly from AMZN Sources 2-4, but MSFT Sources 1 and 5 were retrieval noise.
- This directly explains the low Step 9 context precision score and motivates Step 11: Hybrid Search + Re-ranking.

### Step 11: Hybrid Search + Re-ranking

Hybrid retrieval is complete and committed as:

```text
383272b Add hybrid retrieval reranking
```

BM25 lookup optimization was committed as:

```text
29c3af3 Optimize BM25 chunk lookup
```

Implemented files:

- `src/retrieval/hybrid_retriever.py`
- `src/api/app.py`
- `scripts/run_evaluation.py`
- `requirements.txt`

Dependency added:

- `rank-bm25==0.2.2`

Retrieval design:

- BM25 keyword search retrieves lexical candidates.
- Qdrant semantic search retrieves dense-vector candidates.
- Reciprocal Rank Fusion merges BM25 and semantic ranked lists without score normalization.
- Cross-encoder `cross-encoder/ms-marco-MiniLM-L-6-v2` re-ranks the fused candidate pool.
- FastAPI and evaluation now use `HybridRetriever`.
- BM25 candidate sorting uses a precomputed `chunk_id -> index` map, avoiding `list.index()` O(n) lookup inside every query sort.

Validation:

- The no-filter AWS revenue-growth query no longer returns MSFT cloud chunks in final top-5 sources; returned sources are AMZN.
- Context precision improved from `0.3833` to `0.4750`.
- Overall evaluation improved from `0.7333` to `0.7583`.
- BM25 sort benchmark on the current 271-chunk corpus improved from `0.083071s` to `0.018681s` over 2,000 loops, a `4.45x` speedup.

Hybrid evaluation comparison:

| Metric | Step 9 Baseline | Step 11 Hybrid |
|---|---:|---:|
| Faithfulness | 0.9000 | 0.8667 |
| Answer relevancy | 0.9167 | 0.9333 |
| Context precision | 0.3833 | 0.4750 |
| Overall | 0.7333 | 0.7583 |

Remaining Step 11 limitation:

- Context precision did not reach the target `0.55+` yet.
- Broad Microsoft revenue-source queries and numeric financial-table queries still return more context than the judge considers useful.
- Cross-encoder re-ranking improves precision but adds CPU latency at query time.

### Phase 2A Step A: Streaming Response

Streaming response is complete and committed as:

```text
b8e8fdb Add streaming query endpoint
```

Implemented files:

- `src/generation/generator.py`
- `src/generation/rag_pipeline.py`
- `src/api/app.py`

Streaming design:

- `Generator.generate_stream()` streams tokens from the configured LLM provider.
- Groq streaming uses `client.chat.completions.create(..., stream=True)`, which matches the installed Groq SDK.
- Gemini streaming is implemented via `generate_content_stream()`.
- `RAGPipeline.query_stream()` yields event tuples: `sources`, `token`, `done`, and `error`.
- FastAPI exposes `POST /query/stream` using Server-Sent Events.
- The SSE endpoint uses an `asyncio.Queue` plus a background thread to avoid collecting all events before yielding, so token streaming is real.

Verified SSE event format:

```text
data: {"type": "sources", "data": [...]}
data: {"type": "token", "data": "Based"}
data: {"type": "token", "data": " on"}
data: {"type": "done", "data": null}
```

Streaming validation query:

```text
What are Apple main risk factors?
```

Streaming timing:

| Metric | Seconds |
|---|---:|
| First SSE event, `sources` | 2.4945 |
| First token, end-to-end TTFT | 2.9459 |
| Last token | 3.5820 |
| Total | 3.5820 |

Interpretation:

- End-to-end TTFT includes hybrid retrieval and CPU cross-encoder re-ranking before the LLM call.
- After sources were emitted, Groq produced the first streamed token in about 0.45s.
- Streaming now improves perceived responsiveness even when total generation time remains provider-dependent.

### Phase 2A Step A.1: Semantic Query Cache

Semantic query caching is complete and committed as:

```text
a697787 Add semantic query cache
```

Implemented files:

- `src/retrieval/semantic_cache.py`
- `src/retrieval/hybrid_retriever.py`
- `src/generation/rag_pipeline.py`
- `src/api/app.py`

Cache design:

- The cache stores full generated answers plus serialized retrieved sources.
- Cache lookup uses cosine similarity over query embeddings.
- Cache entries are scoped by exact request filters: `ticker`, `section`, and `top_k`.
- Default threshold is `0.95`, with `max_entries=500` and `ttl_seconds=3600`.
- `RAGPipeline` embeds the query once and reuses that embedding for cache lookup and hybrid retrieval on cache misses.
- Cached streaming responses replay `sources`, word-split `token` events, and `done` without calling the LLM.

New API endpoints:

- `GET /cache/stats`
- `POST /cache/clear`
- `POST /cache/test`

Cache validation:

| Check | Result |
|---|---:|
| Exact repeated `/query` model | `llama-3.3-70b-versatile (cached)` |
| Exact repeated `/query` latency | `0.1080s` |
| Same query with different ticker | cache miss |
| Cached `/query/stream` first event | `0.1212s` |
| Cached `/query/stream` first token | `0.1212s` |
| Cached `/query/stream` done | `0.1212s` |

Threshold tuning results:

| Query A | Query B | Similarity | Cache Hit at `0.95` |
|---|---|---:|---|
| What was Apple revenue in 2024? | Apple 2024 total net sales figure | 0.901063 | No |
| What was Apple revenue in 2024? | What was Apple net income in 2024? | 0.919944 | No |
| What was Apple revenue in 2024? | What was Apple operating cash flow in 2024? | 0.870379 | No |
| What was Apple revenue in 2024? | What are Apple's main risk factors? | 0.603403 | No |
| What was Apple revenue in 2024? | What was Microsoft revenue in 2024? | 0.867607 | No |

Interpretation:

- `0.90` would be unsafe because Apple revenue vs Apple net income scored `0.919944`.
- `0.95` is conservative and currently only intended to catch exact or near-identical repeats.
- Broader paraphrase caching should wait for a larger threshold calibration set.

### Phase 2B Step C: Multi-turn Conversation with Memory

Multi-turn conversation support is complete and committed as:

```text
40175e5 Add multi-turn conversation memory
```

Implemented files:

- `src/memory/__init__.py`
- `src/memory/conversation_memory.py`
- `src/memory/query_rewriter.py`
- `src/generation/rag_pipeline.py`
- `src/generation/generator.py`
- `src/api/app.py`

Memory design:

- Uses Option A: in-memory conversation storage for the current demo stage.
- Stores conversation history per `session_id`.
- Keeps recent turns for LLM context injection.
- Tracks `rewritten_query` per turn for debugging and validation.
- Uses TTL-based cleanup; default session TTL is 30 minutes.
- Interface is intentionally small so a future SQLite or Redis implementation can replace the in-memory backend without changing pipeline/API code.

Multi-turn RAG design:

- Stateless requests continue to work when `session_id` is omitted.
- Session requests load recent conversation history from `ConversationMemory`.
- Follow-up questions are rewritten into standalone retrieval queries before embedding and retrieval.
- Retrieval uses the rewritten query, while generation receives the original user question plus conversation history.
- Multi-turn requests bypass semantic cache because answer context depends on the active conversation.
- Stateless requests still use semantic cache as before.

New/updated API behavior:

- `POST /query` accepts optional `session_id`.
- `POST /query/stream` accepts optional `session_id`.
- `GET /session/{session_id}/history` returns recent turns and rewritten queries for debugging/UI rendering.
- `DELETE /session/{session_id}` clears one conversation session.
- `GET /health` includes memory stats.

Validation:

| Check | Result |
|---|---|
| Follow-up query | `What about their revenue?` |
| Rewritten query | `What is Apple's total revenue?` |
| Turn 2 answer | Returned Apple total net sales: `$416,161` for 2025, `$391,035` for 2024, and `$383,285` for 2023 |
| Stateless cache compatibility | Second identical stateless query returned `llama-3.3-70b-versatile (cached)` |
| Stateless cache latency | `0.1261s` |
| Session isolation | Session A had 1 turn while Session B had 0 turns |

History validation output:

```json
{
  "session_id": "test-session-rewrite-002",
  "turns": [
    {
      "user": "What are Apple's main risk factors?",
      "assistant": "Based on the provided context sections, Apple's main risk factors include...",
      "rewritten_query": null
    },
    {
      "user": "What about their revenue?",
      "assistant": "The Company's total net sales were $416,161 for 2025, $391,035 for 2024, and $383,285 for 2023...",
      "rewritten_query": "What is Apple's total revenue?"
    }
  ]
}
```

Important implementation note:

- The rewriter prompt was tightened so revenue follow-ups target total revenue or total net sales, not revenue recognition policy. This fixed an initial retrieval path that returned revenue-recognition context instead of numeric revenue context.

## Current Data Artifacts

These are generated locally and ignored by git because `data/` is ignored:

- Raw filings: `data/raw/{TICKER}/*.html`
- Extracted sections: `data/processed/{TICKER}/*_sections.json`
- Chunks: `data/processed/{TICKER}/*_chunks.jsonl`
- Embedded chunks: `data/processed/{TICKER}/*_chunks_embedded.jsonl`
- Qdrant local index: `data/processed/qdrant`
- Evaluation results: `data/evaluation_results.json`
- Expanded evaluation results: `data/evaluation_results_v2.json`

If a new session starts without these local artifacts, regenerate in order:

```text
python -m scripts.download_filings
python -m scripts.chunk_filings
python -m scripts.embed_chunks
python -m scripts.index_chunks
python -m scripts.test_rag
python -m scripts.run_evaluation
```

## Environment Variables

Currently supported in `configs/settings.py`:

```text
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=
```

For the current working RAG test, `GROQ_API_KEY` is required.

## Current Dependencies

Important pinned dependencies:

```text
python-dotenv==1.0.1
pydantic-settings==2.4.0
requests==2.31.0
beautifulsoup4==4.12.3
lxml==5.3.0
tiktoken==0.13.0
sentence-transformers==5.6.0
rank-bm25==0.2.2
einops==0.8.2
qdrant-client==1.18.0
anthropic==0.111.0
google-genai==2.9.0
openai==2.43.0
groq==1.5.0
fastapi==0.115.0
uvicorn==0.32.0
```

## Validation Summary

Validated section starts and ends for all 12 sections across AAPL, MSFT, and AMZN.

Current processed section token counts using `cl100k_base`:

| Ticker | Section | Characters | Tokens |
|---|---:|---:|---:|
| AAPL | business | 16,071 | 2,941 |
| AAPL | risk_factors | 68,050 | 11,631 |
| AAPL | mdna | 18,110 | 4,137 |
| AAPL | financial_statements | 62,127 | 15,401 |
| MSFT | business | 48,751 | 8,553 |
| MSFT | risk_factors | 69,024 | 11,933 |
| MSFT | mdna | 46,316 | 9,128 |
| MSFT | financial_statements | 103,782 | 24,506 |
| AMZN | business | 13,545 | 2,684 |
| AMZN | risk_factors | 60,765 | 10,655 |
| AMZN | mdna | 46,462 | 9,011 |
| AMZN | financial_statements | 124,074 | 28,459 |

Note: the `Characters` column is character count, not token count.

## Known Limitations

- Extraction is robust for tested 10-K filings but not broadly validated across 40-80 companies yet.
- No automated test suite for section extraction, chunking, retrieval, or RAG evaluation yet.
- Financial statements are verticalized, so exact numeric retrieval can be weaker than prose retrieval.
- Semantic search can return related financial/accounting chunks above the exact numeric table; hybrid retrieval reduces but does not eliminate this.
- Amazon AWS revenue growth query did not retrieve the exact numeric context even though relevant data may exist in the corpus.
- Cross-encoder re-ranking improves context precision but adds CPU latency before streaming can begin.
- Semantic cache is in-memory only; entries are lost on process restart and the current list scan should be replaced by an indexed/vector-backed implementation at larger scale.
- Semantic cache threshold is conservative. It catches exact or near-identical repeats, but does not yet cache broader paraphrases safely.
- Conversation memory is in-memory only; sessions are lost on process restart and are not shared across multiple API workers.
- Query rewriting adds one LLM call for follow-up questions with history, so multi-turn latency can be higher than stateless queries.
- Enumeration-type queries such as `What are the main sources of revenue for Microsoft?` underperform compared with fact-lookup queries. Current hypothesis: the system architecture (`top_k=5` plus a single-answer generation prompt) is tuned for focused QA, not exhaustive listing. Diagnostic result: Azure appears inside the top-20 candidate pool but outside the final top-5 for the Microsoft revenue-source query, indicating a top-k/query-type sizing issue rather than a hard retrieval miss. Candidate fix: extend query decomposition to detect single-company enumeration queries, not only multi-company comparisons.
- Query decomposer currently does not detect single-company enumeration as needing decomposition. Partial Muc 3 evaluation confirmed `enumeration decomposition_correct = 0/4 = 0.00` for the four enumeration cases, while comparative multi-company cases do trigger decomposition.
- Groq free tier can return `429 Too Many Requests`; SDK retries can recover, but latency may spike.
- Full 30-case Muc 3 evaluation could not complete under current Groq free-tier token limits. Retrying after quota exhaustion causes long waits and contaminates latency metrics, so official category-level results should be generated from a clean run after quota reset or with a lower-cost judge/model configuration.
- Gemini Flash Lite may return temporary `503 UNAVAILABLE` under high demand.
- OpenAI key in the current environment was not a valid OpenAI Platform key during testing.

## Latest Step

Phase 2C Muc 3: Expanded evaluation set and decomposer-routed evaluation are implemented.

Implemented evaluation behavior:

1. `src/evaluation/test_set.py` now contains 30 cases across six categories: `fact_lookup`, `summary`, `enumeration`, `comparative`, `multi_hop`, and `out_of_corpus`.
2. Each test case has `category` and `expects_decomposition` metadata.
3. `scripts/run_evaluation.py` routes every test case through `QueryDecomposer.run()` instead of directly calling `RAGPipeline.query()`.
4. Simple questions still use the normal RAG path because the decomposer returns `was_decomposed=False` and falls back internally.
5. Evaluation output now includes `DecompOK`, category summaries, sub-query metadata, answer text, and writes to `data/evaluation_results_v2.json`.
6. Out-of-corpus fallback failures log the actual answer for debugging.

Validation notes:

- The 3-company cybersecurity comparison returned 3 chunks each for AAPL, MSFT, and AMZN after fixing a shared-model thread-safety issue.
- Known limitation: Query decomposition dispatches sub-queries concurrently via `ThreadPoolExecutor`, but a global lock around `retrieve()` serializes model inference (`Embedder` + cross-encoder) to prevent a confirmed race condition in Nomic BERT's rotary embedding cache. Measured overhead: `2.98x` vs single query (`n=3` sub-queries), consistent with near-full serialization. Scoped locking around only `model.encode()` and `cross_encoder.predict()` would restore I/O-bound parallelism, but is deferred pending corpus expansion to validate the gain.
- Muc 2 Microsoft revenue-source diagnostic confirmed that Azure evidence chunks (`business_0006`, `business_0007`, `business_0008`) appear inside top-20 BM25 and semantic candidate pools, but not in top-3 for either method. This confirms an enumeration/query-shaping and final top-k issue, not a hard retrieval miss.
- Partial Muc 3 run reached all four enumeration cases. All four had `expects_decomposition=True`, `was_decomposed=False`, and `decomposition_correct=False`, so enumeration decomposition correctness is currently `0/4 = 0.00`.
- Full 30-case grouped category table is still unavailable because Groq returned repeated `429` quota errors before the run completed. Long retry sleeps should not be counted as valid latency data.

## Next Step

Phase 2C: Close Muc 3 with a clean full evaluation run, then decide whether to fix enumeration detection immediately.

Recommended priorities:

1. Rerun `python -m scripts.run_evaluation` after Groq quota reset, or switch to a lower-cost judge/model configuration for evaluation only.
2. Capture the full six-category summary table from `data/evaluation_results_v2.json`.
3. Use the confirmed `enumeration decomposition_correct = 0.00` result to update `DECOMPOSE_SYSTEM_PROMPT` for single-company enumeration queries.
4. Re-run the enumeration subset after prompt changes before changing retrieval top-k globally.

Deferred production-quality item:

- Streamlit UI remains the next demo/productization step after the backend reasoning improvements.

Step 12: Docker packaging.

Recommended priorities:

1. Add a `Dockerfile` for FastAPI serving.
2. Add `.dockerignore` excluding `.env`, `data/`, caches, and local virtual environments.
3. Document how generated artifacts are provided or rebuilt for container use.
