# Enterprise Document QA Frontend

Vite + React + TypeScript client for the Enterprise Document QA FastAPI backend. The frontend displays streamed answers, source citations, supported ticker filters, session history, and decomposed sub-queries.

The research workspace uses a warm paper/navy palette with calmer indigo action
accents and teal verification states in both light and dark themes.

The workspace keeps the primary question flow compact: advanced retrieval
settings, interpreted queries, decomposition traces, and filing evidence are
progressively disclosed so the answer remains the visual focus. The layout is
responsive for mobile drawers, keyboard navigation, dark mode, and reduced
motion preferences.

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
bun run test
bun run build
```

Production output is written to `dist/`.

The production build keeps the Markdown conversation renderer in a lazy chunk,
uses cacheable vendor chunks, and relies on lightweight CSS transitions for
micro-interactions. The indexed ticker catalog is browser-cacheable; health
and session history remain fresh requests.

## Vercel

Production deployment: `https://frontend-one-gamma-f9jf11u8ec.vercel.app`

Set the Vercel project Root Directory to `frontend` and define:

```text
VITE_API_BASE_URL=https://your-fastapi-backend.example.com
```

`vercel.json` gives Vite's content-hashed `/assets/*` files a one-year
immutable browser cache. Keep `index.html` revalidated so each deployment can
point clients at the latest asset hashes.

The backend URL must be reachable from the browser and must not be `localhost` in a hosted deployment. For the zero-cost demo, use the reserved ngrok URL while the local Docker backend and tunnel are running. Add the final Vercel origin to the backend's comma-separated `ALLOWED_ORIGINS` value.

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

Initialization requests share one `AbortController` and are cancelled on unmount. During an active SSE response, the input exposes a Stop button that aborts the request, preserves any partial answer already rendered, and immediately re-enables the input. Reloaded session history renders full assistant answers without client-side truncation.

Source objects contain `citation`, `score`, and `text_preview`. Decomposed responses also include `was_decomposed`, `sub_queries`, and `num_total_chunks`.
