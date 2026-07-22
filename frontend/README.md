# Enterprise Document QA Frontend

Vite + React + TypeScript client for the Enterprise Document QA FastAPI backend. The frontend displays streamed answers, source citations, supported ticker filters, session history, and decomposed sub-queries.

## Local Development

Requirements: Node.js 18+ and Bun.

```bash
bun install
cp .env.example .env.local
bun run dev
```

The development server runs at `http://localhost:3000`. Configure the backend URL in `.env.local`:

```env
VITE_API_BASE_URL="http://localhost:8000"
```

`VITE_*` variables are embedded in the browser bundle and must never contain secrets.

## Build

```bash
bun run lint
bun run build
```

Production output is written to `dist/`.

## Vercel

Set the Vercel project Root Directory to `frontend` and define:

```text
VITE_API_BASE_URL=https://your-fastapi-backend.example.com
```

The backend URL must be reachable from the browser and must not be `localhost` in a hosted deployment.

## API Contract

All request and response bodies are JSON except the SSE stream. Query requests use:

```ts
{
  question: string;          // 5-500 characters
  ticker: string | null;
  section: "business" | "risk_factors" | "mdna" |
           "financial_statements" | "financial_table" | null;
  top_k: number;             // 1-10
  session_id: string | null;
}
```

| Method | Endpoint | Frontend use |
|---|---|---|
| `GET` | `/health` | Check backend and pipeline readiness |
| `GET` | `/supported-tickers` | Load searchable tickers and sections |
| `POST` | `/query` | Submit a non-streaming query |
| `POST` | `/query/stream` | Stream answer events over SSE |
| `POST` | `/query/decomposed` | Run comparative or complex queries |
| `GET` | `/session/{session_id}/history` | Load conversation history |
| `DELETE` | `/session/{session_id}` | Clear a conversation session |

The streaming endpoint returns records in this format:

```text
data: {"type":"sources|token|done|error","data":...}
```

Source objects contain `citation`, `score`, and `text_preview`. Decomposed responses also include `was_decomposed`, `sub_queries`, and `num_total_chunks`.
