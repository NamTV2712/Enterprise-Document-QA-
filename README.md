# Enterprise Document QA

Enterprise Document QA is a RAG system over SEC 10-K filings for AAPL, MSFT, and AMZN.

Pipeline:

```text
SEC Filing -> Section Extraction -> Chunking -> Embedding -> Qdrant -> Retrieval -> LLM Answer -> FastAPI
```

## Status

Steps 1-10 are complete:

- SEC 10-K download and section extraction.
- Token-aware chunking.
- Local Nomic embeddings.
- Qdrant vector indexing.
- Retrieval wrapper.
- Groq/Gemini-backed RAG generation.
- LLM-as-judge evaluation.
- FastAPI service with Swagger UI.

Latest completed milestone: Step 10, FastAPI service.

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

Measured `/query` requests:

| Query | Filter | Latency |
|---|---|---:|
| Apple revenue | `ticker=AAPL`, `section=financial_statements` | 1.2503s |
| Microsoft cybersecurity risks | `ticker=MSFT` | 1.2090s |
| AWS revenue growth | none | 5.8362s |

Retrieval latency is low: query embedding plus vector search took about 0.14-0.18s.

End-to-end latency is dominated by the LLM provider. With Groq free tier, expect provider-dependent latency around 2-5s, with possible spikes when Groq returns `429 Too Many Requests` and retries.

## Evaluation

Latest evaluation averages:

| Metric | Score |
|---|---:|
| Faithfulness | 0.9000 |
| Answer relevancy | 0.9167 |
| Context precision | 0.3833 |
| Overall | 0.7333 |

The main current weakness is context precision. A no-filter AWS query retrieved an MSFT cloud chunk above relevant AMZN AWS chunks because dense retrieval treats generic cloud language as semantically close. The LLM still answered from AMZN sources, but irrelevant context remained in the source list.

This is the motivation for Step 11: Hybrid Search + Re-ranking.

## Known Limitations

- Financial statements are verticalized, so exact numeric retrieval can be weaker than prose retrieval.
- Dense semantic retrieval can return related but non-answer chunks, lowering context precision.
- Groq free tier can return `429 Too Many Requests`; SDK retries can recover but increase latency.
- Gemini Flash Lite may return temporary `503 UNAVAILABLE` under high demand.
- Generated artifacts under `data/` are local and ignored by git.

## Next Steps

- Step 11: Hybrid Search + Re-ranking to improve context precision.
- Step 12: Docker packaging.
