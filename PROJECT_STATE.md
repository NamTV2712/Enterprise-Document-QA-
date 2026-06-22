# Project State

## Current Milestone

Steps 1-8 are complete for the MVP Enterprise Document QA / SEC 10-K RAG pipeline.

Latest completed milestone commit:

```text
d2dc7f2 Add RAG generation pipeline
```

Recent completed commits:

```text
d2dc7f2 Add RAG generation pipeline
cb48532 Add retrieval pipeline wrapper
268c36e Add Qdrant vector indexing
544ddb7 Add local embedding pipeline
cabd268 Add SEC filing chunking
02b7fca Add project state handoff and tiktoken dependency
6b2f599 Robust SEC filing section extraction
```

## Project Goal

Build an Enterprise Document QA system over SEC 10-K filings using a RAG pipeline:

```text
SEC Filing -> Section Extraction -> Chunking -> Embedding -> Vector DB -> Retrieval -> LLM Answer
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
- `src/generation/generator.py`
  LLM wrapper for RAG answer generation with strict anti-hallucination prompt. Current default provider is Groq.
- `src/generation/rag_pipeline.py`
  End-to-end RAG pipeline combining Retriever + Generator.
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

## Current Data Artifacts

These are generated locally and ignored by git because `data/` is ignored:

- Raw filings: `data/raw/{TICKER}/*.html`
- Extracted sections: `data/processed/{TICKER}/*_sections.json`
- Chunks: `data/processed/{TICKER}/*_chunks.jsonl`
- Embedded chunks: `data/processed/{TICKER}/*_chunks_embedded.jsonl`
- Qdrant local index: `data/processed/qdrant`

If a new session starts without these local artifacts, regenerate in order:

```text
python -m scripts.download_filings
python -m scripts.chunk_filings
python -m scripts.embed_chunks
python -m scripts.index_chunks
python -m scripts.test_rag
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
einops==0.8.2
qdrant-client==1.18.0
anthropic==0.111.0
google-genai==2.9.0
openai==2.43.0
groq==1.5.0
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
- Semantic search can return related financial/accounting chunks above the exact numeric table.
- Amazon AWS revenue growth query did not retrieve the exact numeric context even though relevant data may exist in the corpus.
- Groq free tier can return `429 Too Many Requests`; SDK retries can recover, but latency may spike.
- Gemini Flash Lite may return temporary `503 UNAVAILABLE` under high demand.
- OpenAI key in the current environment was not a valid OpenAI Platform key during testing.

## Next Step

Step 9: Evaluation Framework.

Recommended priorities:

1. Create a small golden QA set covering numeric, risk-factor, business, and out-of-scope questions.
2. Evaluate retrieval quality separately from generation quality.
3. Add checks for citation presence and answer faithfulness.
4. Add regression cases for known failures, especially Amazon AWS revenue growth retrieval.
5. Document known limitations in README, including financial table retrieval and free-tier provider limits.

Suggested Step 9 files:

- `src/evaluation/evaluator.py`
- `scripts/evaluate_rag.py`
- `data/evaluation/golden_questions.json` or equivalent, if data files are allowed locally.
