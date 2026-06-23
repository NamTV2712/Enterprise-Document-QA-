# Enterprise Document QA

Enterprise Document QA is a RAG system over SEC 10-K filings for AAPL, MSFT, and AMZN.

Pipeline:

```text
SEC Filing -> Section Extraction -> Chunking -> Embedding -> Qdrant/BM25 -> Hybrid Retrieval -> Re-ranking -> LLM Answer -> FastAPI
```

## Status

Steps 1-11 are complete:

- SEC 10-K download and section extraction.
- Token-aware chunking.
- Local Nomic embeddings.
- Qdrant vector indexing.
- Retrieval wrapper.
- Groq/Gemini-backed RAG generation.
- LLM-as-judge evaluation.
- FastAPI service with Swagger UI.
- Hybrid retrieval with BM25, Reciprocal Rank Fusion, and cross-encoder re-ranking.

Latest completed milestone: Step 11, Hybrid Search + Re-ranking.

## API

Run locally:

```powershell
.venv\Scripts\python.exe -m uvicorn src.api.app:app --reload --port 8000
```

Endpoints:

- `GET /health`
- `POST /query`
- `GET /supported-tickers`
- `GET /docs`

Health response validated:

```json
{
  "status": "ok",
  "pipeline_ready": true
}
```

## Latency

Baseline Step 10 `/query` requests with semantic retrieval:

| Query | Filter | Latency |
|---|---|---:|
| Apple revenue | `ticker=AAPL`, `section=financial_statements` | 1.2503s |
| Microsoft cybersecurity risks | `ticker=MSFT` | 1.2090s |
| AWS revenue growth | none | 5.8362s |

Retrieval latency is low: query embedding plus vector search took about 0.14-0.18s.

End-to-end latency is dominated by the LLM provider. With Groq free tier, expect provider-dependent latency around 2-5s, with possible spikes when Groq returns `429 Too Many Requests` and retries.

Step 11 hybrid retrieval adds a CPU cross-encoder re-ranking stage, so retrieval is slower but more precise:

| Query | Filter | Latency |
|---|---|---:|
| Apple revenue | `ticker=AAPL`, `section=financial_statements` | 5.2665s |
| Microsoft cybersecurity risks | `ticker=MSFT` | 4.6938s |
| AWS revenue growth | none | 3.1727s |

The AWS no-filter query no longer returns MSFT cloud chunks in the final top-5 sources; all returned sources are AMZN.

## Evaluation

Step 9 semantic retrieval baseline:

| Metric | Score |
|---|---:|
| Faithfulness | 0.9000 |
| Answer relevancy | 0.9167 |
| Context precision | 0.3833 |
| Overall | 0.7333 |

Step 11 hybrid retrieval result:

| Metric | Score |
|---|---:|
| Faithfulness | 0.8667 |
| Answer relevancy | 0.9333 |
| Context precision | 0.4750 |
| Overall | 0.7583 |

Hybrid retrieval improved context precision from `0.3833` to `0.4750` and fixed the AWS no-filter MSFT-noise issue. It did not reach the target `0.55+` yet.

Remaining precision issues are mostly from broad revenue-source questions and numeric financial table retrieval, where the system still returns more context than the judge considers useful.

## Dependencies

Important retrieval/API dependencies:

- `sentence-transformers==5.6.0`
- `rank-bm25==0.2.2`
- `qdrant-client==1.18.0`
- `fastapi==0.115.0`
- `uvicorn==0.32.0`

## Known Limitations

- Financial statements are verticalized, so exact numeric retrieval can be weaker than prose retrieval.
- Dense semantic retrieval can return related but non-answer chunks; hybrid retrieval reduces but does not eliminate this.
- Cross-encoder re-ranking improves source quality but adds CPU latency at query time.
- Groq free tier can return `429 Too Many Requests`; SDK retries can recover but increase latency.
- Gemini Flash Lite may return temporary `503 UNAVAILABLE` under high demand.
- Generated artifacts under `data/` are local and ignored by git.

## Next Steps

- Continue improving Step 11 retrieval quality toward context precision `0.55+`.
- Step 12: Docker packaging.
