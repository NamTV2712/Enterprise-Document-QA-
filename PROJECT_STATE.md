# Project State

## Current Milestone

Steps 1-11 are complete for the MVP Enterprise Document QA / SEC 10-K RAG pipeline.
Phase 2A Step A, Streaming Response, is complete and verified.
Phase 2A Step A.1, Semantic Query Cache, is complete and verified.
Phase 2B Step C, Multi-turn Conversation with Memory, is complete and verified.
Phase 2B Step D, Query Decomposition, is integrated and verified for comparative queries.
Phase 2C Muc 2, deterministic evaluation metrics and enumeration retrieval diagnosis, is complete.
Phase 2C Muc 3, 30-case categorized evaluation set and decomposer-routed evaluation, is implemented. Full 30-case LLM-judge run is blocked by Groq free-tier quota.
Phase 2C Muc 4, financial table retrieval, is complete.
Phase 2C Muc 5, corpus expansion to 25 configured tickers, is locally ingested, chunked, embedded, and indexed with explicit corpus-quality reporting. Follow-up remains for section extraction gaps in filings that use annual-report cross-reference layouts.
Phase 2C Muc 7, Qdrant Cloud production configuration and migration, is implemented and verified.

Current Muc 7 Qdrant Cloud status:

- `configs/settings.py` supports `QDRANT_MODE`, `QDRANT_LOCAL_PATH`, `QDRANT_CLOUD_URL`, and `QDRANT_CLOUD_API_KEY`.
- `VectorStore` supports local persistent mode and Qdrant Cloud mode while preserving the old `VectorStore(path=...)` local call pattern.
- FastAPI startup, evaluation, and `scripts/test_rag.py` now use the configured Qdrant mode.
- `scripts/index_chunks.py` intentionally rebuilds only the local Qdrant index via `settings.qdrant_local_path` to avoid accidentally deleting a cloud collection.
- `scripts/migrate_to_qdrant_cloud.py` migrates the active local `sec_filings` collection to Qdrant Cloud. It upserts by default and only deletes/recreates the cloud collection when `--recreate` is explicitly passed.
- Qdrant Cloud migration completed for `sec_filings`: local points `3,944`, cloud points `3,944`.
- Qdrant Cloud required keyword payload indexes for filtered search; `ticker` and `section` indexes are now created by both `VectorStore.create_collection()` and the migration script.
- `scripts/verify_qdrant_cloud.py` compares local vs cloud top-5 chunk IDs for a smoke query after migration.
- Local-vs-cloud verification passed with exact top-5 match for `What was Apple's total net sales in 2024?` filtered to `AAPL`.
- README documents the Qdrant Cloud migration and verification flow.
- Validation after implementation: `.venv\Scripts\python.exe -m pytest tests/ -v` passes with `44 passed, 9 warnings`; `.venv\Scripts\python.exe -m compileall configs src scripts` passes.

Current Muc 5 corpus quality:

- Text-section ingestion report: 16 `success`, 6 `degraded`, 3 `failed`, 25 `skipped_existing` on latest idempotent rerun.
- Clean for evaluation/demo requiring 4 text sections plus `financial_table`: 14 tickers: AAPL, AMD, AMZN, BAC, BRK-B, CRM, GOOGL, JNJ, META, MSFT, QCOM, TSLA, UNH, WMT.
- Degraded but usable for some section-specific questions: CVX, GS, HD, JPM, NVDA, ORCL, PFE, XOM.
- Unusable until extractor is improved: INTC, MCD, MS. These have `sections={}` and 0 chunks.
- Qdrant currently indexes 3,944 chunks from 22 tickers. The 3 unusable tickers are not represented in the vector index.
- `scripts/download_filings.py` now marks 0-section extraction as `failed` instead of successful/skipped, and marks partial section extraction as `degraded` with explicit missing-section warnings.
- Structural limitation identified: degraded/unusable filings commonly use incorporation-by-reference language and annual-report/page-reference layouts around Item 7 and Item 8. Examples include JPM Item 7/8 pointing to MD&A pages 46-160 and financial statements pages 162-314, XOM Item 7/8 pointing to the Financial Section, CVX Item 7/8 pointing to Financial Table of Contents entries, and MS/MCD/INTC using annual-report layouts where relevant content is not exposed through standard `Item 7 ... Item 8` boundaries. This is not just a missing regex keyword. Some content may still be present in the same primary HTML, while other filings may require following referenced exhibits or report sections. Supporting these cases requires a separate annual-report/table-of-contents aware ingestion/extraction pass, out of scope for the current single-document section extractor.
- For evaluation and portfolio demos, prefer the 14 clean tickers. Degraded tickers remain usable only for sections that were actually extracted, especially business and risk-factor queries.
- Cross-encoder score calibration finding: generic summary-style questions such as `What are X's main risk factors?` can score low or negative even when retrieval is verified correct by ticker, section, and content. Confirmed scores: AAPL `0.78` (positive outlier), MSFT `-1.70`, AMZN `-1.95`, JNJ `0.24`, BAC `-4.68`, UNH `-5.19`, GOOGL `-5.10`. Root cause: `ms-marco-MiniLM` scores specific query-passage relevance; broad summary queries do not have one strongly matching passage the same way fact-lookup queries do. Current impact is safe because `Generator.LOW_SCORE_THRESHOLD = 0.50` only logs a warning and does not block answer generation or trigger fallback. Before using retrieval score for fallback decisions or user-facing confidence, thresholds must be calibrated by query type/category instead of using one global cutoff.
- Evaluation finding: derived/trend phrasing remains a retrieval limitation for raw financial table evidence. Examples: `How did Microsoft's total assets change year over year?` and the earlier `AWS revenue growth` case. The correct table chunks exist, but cross-encoder ranking scores the table evidence poorly for broad change/growth wording, even when `financial_table` is forced. This is a query formulation/ranking limitation, not table extraction failure.
- Evaluation safety guard: `QueryDecomposer` now has a minimum-evidence guard (`MIN_CHUNKS_FOR_SYNTHESIS = 2`) that returns a fallback instead of synthesizing when decomposition retrieves too little evidence. Unit tests cover both fallback and normal synthesis paths. Follow-up evidence showed the Amazon business-segment case is not covered by this quantity guard because it retrieves enough chunks, and the current `AMZN_business_0000` chunk explicitly contains the segment sentence (`North America`, `International`, `Amazon Web Services`). Treat the prior Amazon judge score of `0.00` as an evaluation/context-audit item rather than confirmed hallucination until the exact judge context is inspected.
- Evaluation context visibility had two layers of truncation risk. First, the LLM judge previously saw only the first 250 characters of each retrieved chunk, hiding the Amazon segment evidence; this was increased to `JUDGE_CONTEXT_CHARS_PER_CHUNK = 1000`. Second, the Apple auditor case proved that a fixed prefix can still miss evidence (`Ernst & Young` and `October 31` appear around offsets `1453-1547` in `AAPL_000032019325000079_financial_statements_0019`). The evaluator now uses relevance windowing (`_extract_relevant_window`) to select a query-relevant 1000-character window instead of always taking the chunk prefix, with regression tests for both Amazon-style and Apple-auditor-style failures. Previous faithfulness/context-precision scores from Muc 3 through the latest priority-1 run may be underestimates and should be re-evaluated before being treated as final metrics.
- Pre-evaluation Tier 1 checks completed: `/supported-tickers` was fixed to report the 22 tickers with embedded chunks instead of the old hardcoded 3-ticker list, and API validation now accepts dash tickers such as `BRK-B`.
- Degraded ticker section audit: NVDA has `business/mdna/risk_factors`; JPM, XOM, and CVX have `business/risk_factors`; ORCL has `business/mdna/risk_factors`; PFE has `business/financial_statements/financial_table/risk_factors`. Financial questions for degraded tickers without `financial_table` or `financial_statements` should be treated as limited-data cases.
- Single-turn trend/growth query expansion added before the clean priority-1 evaluation: AWS revenue growth now retrieves the AWS net sales evidence at rank 1, and Microsoft total assets year-over-year now retrieves `MSFT_000095017025100235_financial_table_0001` at rank 1 under `financial_table`.
- Current unit test suite after these fixes: `48 passed, 9 warnings`.
- Trade-off: trend/growth query expansion adds one LLM rewrite call for underspecified single-turn trend queries. This improves retrieval for known table-backed trend cases but increases token budget consumption; it contributed to Groq quota exhaustion before completing the `multi_hop` and `out_of_corpus` categories in the latest priority-1 evaluation attempt.
- Latest priority-1 evaluation attempt after all fixes judged 14/18 cases before Groq TPD quota stopped the run. Judged averages: Faithfulness `0.6964`, Answer Relevancy `0.7286`, Context Precision `0.6736`, Overall `0.6995`, Citation Correctness `1.0`, Recall Proxy `0.9231`, Fallback Accuracy `0.9286`. Category coverage: `fact_lookup=4/4`, `summary=3/3`, `enumeration=4/4`, `comparative=3/3`, `multi_hop=0/3`, `out_of_corpus=0/1`. Do not publish this as the final README/CV metric until the skipped cases are completed after quota reset.

Latest completed milestone commit:

```text
e9692e1 Expand corpus ingestion
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

The configured corpus currently covers latest 10-K filings for:

- AAPL
- MSFT
- AMZN
- GOOGL
- META
- NVDA
- TSLA
- JPM
- BAC
- GS
- MS
- BRK-B
- JNJ
- UNH
- PFE
- WMT
- HD
- MCD
- XOM
- CVX
- AMD
- INTC
- QCOM
- CRM
- ORCL

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
  Idempotent batch download and section extraction script for configured tickers.
- `scripts/chunk_filings.py`
  Chunk generation script.
- `scripts/embed_chunks.py`
  Resumable embedding generation script.
- `scripts/index_chunks.py`
  Qdrant indexing script that recreates the collection from embedded files.
- `configs/tickers.py`
  Corpus ticker list and ticker-to-CIK overrides for SEC ticker-map edge cases.
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
QDRANT_MODE=local
QDRANT_LOCAL_PATH=data/processed/qdrant
QDRANT_CLOUD_URL=
QDRANT_CLOUD_API_KEY=
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
- Query decomposer now detects single-company enumeration and validates LLM-generated ticker/section fields before execution. Regression tests cover unsupported ticker leaks such as `NVDA` and mixed valid/invalid plans.
- Groq free tier can return `429 Too Many Requests`; SDK retries can recover, but latency may spike.
- Full 30-case Muc 3 evaluation could not complete under current Groq free-tier token limits. Retrying after quota exhaustion causes long waits and contaminates latency metrics, so official category-level results should be generated from a clean run after quota reset or with a lower-cost judge/model configuration.
- A single 30-case evaluation run exhausted both Groq generation/planning quota and Gemini judge free-tier quota within one session. The checkpoint/resume mechanism preserved partial completion (`13/30` OK in the first full Muc 3 run) without data loss. Full CI-style evaluation requires quota reset across multiple sessions or a paid tier.
- Gemini Flash Lite may return temporary `503 UNAVAILABLE` under high demand.
- OpenAI key in the current environment was not a valid OpenAI Platform key during testing.
- Initial Muc 4 diagnostics show that core AAPL/MSFT/AMZN financial statement rows are represented as native HTML `<table>` structures, but SEC table cells include spacer columns, separate `$`/`%` tokens, and non-fixed header row positions. Table-aware extraction must pattern-match content rather than hardcode row offsets.
- MSFT `Microsoft Cloud gross margin percentage` is not present as a numeric table in the raw filing; the numeric `69%` appears in MD&A prose. In the current corpus, percentage-derived metrics are often narrative MD&A content, while native tables primarily contain absolute financial values.

## Latest Step

Phase 2C Muc 3: Expanded evaluation set and decomposer-routed evaluation are partially evaluated.

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
- Deterministic unit tests for decomposition planner validation pass: `6/6` in `tests/test_query_decomposer.py`. This protects the defense-in-depth guard that validates LLM structured output instead of trusting prompt-only constraints.
- Partial Muc 3 live evaluation status: `13/30` cases have full judge scores, `17/30` were skipped due to Groq generation/planning quota or Gemini judge quota. Checkpoint file `data/eval_checkpoint.jsonl` preserves completed cases; resuming only requires re-running `python -m scripts.run_evaluation` after quota reset.
- Partial category coverage with judge scores: `fact_lookup` `7/8` judged (`Faith=0.8571`, `Precision=0.8571`), `summary` `4/6` judged (`Faith=0.7500`, `Precision=0.7750`), `enumeration` `2/4` judged (`decomposition_correct=1.0000` for judged cases, `4/4` confirmed including judge-skipped generated records).
- Comparative and multi-hop quality are not fully measured yet: `comparative` has `0/6` judged but `3/6` generated records confirmed `decomposition_correct=True`; `multi_hop` has `0/3` judged and remains the highest-priority category to complete after quota reset.
- Out-of-corpus coverage is incomplete: Tesla and Google were skipped before answer generation; Nvidia generated a correct insufficient-information answer, and the new validation guard prevents unsupported ticker subqueries from being trusted going forward.

## Next Step

Phase 2D / Muc 4: Table-aware financial chunks are integrated as supplemental local artifacts.

Current diagnostic status:

- `src/ingestion/table_extractor.py` parses native SEC HTML financial tables into captioned markdown that preserves metric/year/value relationships.
- `src/ingestion/chunker.py` now has `build_table_chunks()`, which creates supplemental `financial_table` chunks. Existing `financial_statements` prose chunks are retained; parsed table chunks are additive, not replacements.
- `scripts/add_table_chunks.py` appends table chunks idempotently to existing `*_chunks.jsonl` files.
- Verified real-table rows: MSFT `Total revenue` maps to `281,724 / 245,122 / 211,915`, AAPL `Total net sales` maps to `416,161 / 391,035 / 383,285`, and AMZN `Total net sales` preserves the filing's `2023 -> 2024 -> 2025` year order.
- MSFT self-consistency check passes: product revenue plus service-and-other revenue equals total revenue for 2025, 2024, and 2023.
- Percentage-primary table handling is currently protected by a synthetic unit test only because the current corpus has no confirmed real percentage-primary financial table.
- Corrected full financial-section table scan results after following TOC `href` anchors and detecting years inside longer header cells: AAPL `22/33` tables parsed with rows, MSFT `36/51`, and AMZN `31/46`. Empty parses are still expected for layout, signature, glossary, and non-year-header tables, but some remaining empty tables contain real data with multi-level non-year headers and should be preserved through prose chunks if not parsed structurally.
- Table caption context is required metadata. Duplicate row labels such as AMZN `North America` / `International` / `AWS` refer to different financial concepts depending on nearby caption text, for example property and equipment by segment versus depreciation and amortization by segment.
- Local table chunk generation added AAPL `22`, MSFT `36`, and AMZN `31` `financial_table` chunks (`89` total). Chunk files now contain `360` records, up from `271`.
- Re-running `python -m scripts.embed_chunks` and `python -m scripts.index_chunks` embedded and indexed all `360` chunks. Qdrant collection `sec_filings` reports `points_count=360`.
- Retrieval smoke test with `ticker=AAPL`, `section=financial_table`, and `What was Apple's total net sales in fiscal year 2024?` returns clean table chunks containing `Total net sales | 416,161 | 391,035 | 383,285`. The broader question ranks net-sales breakdown tables first; adding `consolidated statements of operations` retrieves the income statement table as top-1.
- No-filter Apple fact lookup confirms automatic ranking improvement: for `What was Apple's total net sales in fiscal year 2024?`, `financial_table` ranks #1 and #2 (`CE=6.3033`, `5.1253`), ahead of `mdna` and `financial_statements` (`3.6-3.9`). The answer correctly returns `$391,035`.
- No-filter Apple multi-hop trend check succeeds: `How did Apple's total net sales trend from 2023 to 2025?` ranks `financial_table` #1 and #3 and answers all three values correctly (`383,285`, `391,035`, `416,161`). This is the first successful multi-hop-style live result recorded after the Muc 4 integration.
- New query-side limitation: `What is Amazon's AWS revenue growth?` still fails with no section filter because the relevant table chunks contain raw values but not the derived term `growth`. Rephrasing to include explicit years/metric, such as `AWS segment net sales 2024 2025 Amazon`, retrieves a `financial_table` chunk at rank #1. Candidate fix direction is query rewriting/expansion for growth/trend questions rather than extraction.
- AMZN table index `38` confirmed a two-level segment structure: one-cell segment headers (`North America`, `International`, `AWS`, `Consolidated`) followed by repeated metric rows (`Net sales`, `Operating expenses`, `Operating income`). The parser now carries segment headers forward into labels such as `AWS - Net sales`, preventing generic repeated labels.
- Minor parsing edge case: AMZN `International - Operating income (loss)` currently misses the 2023 negative value formatted as `( 2,656 )`. Likely cause is the parenthesized negative number being split across cells and partially treated as symbol-only text. This is lower priority than preserving segment labels because most financial table values are positive and the original prose chunks remain available as fallback.
- After the segment-label fix, local table chunks were regenerated by removing old `financial_table` chunks and appending the corrected ones: AAPL removed/appended `22`, MSFT `36`, AMZN `31` (`89` total). Chunk files remain at `360` records.
- Re-embedding and re-indexing after regeneration kept Qdrant stable at `points_count=360`, confirming no duplicate point growth.
- AWS growth retest after segment-prefix regeneration is unchanged: `What is Amazon's AWS revenue growth?` still retrieves `financial_statements_0007` only and returns an insufficient-information answer. This confirms the remaining issue is query phrasing/derived-metric expansion, not stale table labels.
- Post-Muc 4 evaluation preparation: 8 numeric-heavy `fact_lookup`/`multi_hop` cases in `src/evaluation/test_set.py` now use `section=None` instead of hardcoded `financial_statements`/`mdna`, allowing `financial_table` chunks to compete naturally during evaluation.
- Evaluation set now supports priority-based runs: `priority=1` is an 18-case quota-safe core set (`fact_lookup=4`, `summary=3`, `enumeration=4`, `comparative=3`, `multi_hop=3`, `out_of_corpus=1`), while `priority=2` restores the full 30-case set. Use `python -m scripts.run_evaluation --priority 1` for the core run and `--priority 2` for the full run.
- Full 30-case post-Muc 4 evaluation attempt is blocked by daily free-tier quotas. Gemini judge hit `GenerateRequestsPerDayPerProjectPerModel-FreeTier` (`20` requests/day), and Groq hit `100,000` tokens/day in the same session. Retry after provider daily reset.
- Checkpoint backups preserved locally: `data/eval_checkpoint_before_muc4.jsonl` contains the pre-Muc 4 partial baseline (`13/30` OK), and `data/eval_checkpoint_gemini_blocked.jsonl` contains this session's blocked post-Muc 4 attempt (`0/30` OK; skipped records only).

Recommended priorities:

1. Add query rewriting/expansion for growth/trend questions so terms like `growth` retrieve tables containing the underlying year-by-year values.
2. Decide whether API/UI should automatically search both `financial_table` and `financial_statements` for numeric financial questions or keep the new section as an explicit filter.
3. After quota reset, delete `data/eval_checkpoint.jsonl` from the blocked run and rerun `python -m scripts.run_evaluation --priority 1` to generate a clean core post-Muc 4 evaluation. Use `--priority 2` only when quota is sufficient for the full 30-case run.

Deferred production-quality item:

- Streamlit UI remains the next demo/productization step after the backend reasoning improvements.

Step 12: Docker packaging.

Recommended priorities:

1. Add a `Dockerfile` for FastAPI serving.
2. Add `.dockerignore` excluding `.env`, `data/`, caches, and local virtual environments.
3. Document how generated artifacts are provided or rebuilt for container use.
