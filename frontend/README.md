# Enterprise Document QA Frontend

Vite + React + TypeScript client for the Enterprise Document QA FastAPI backend. The frontend displays streamed answers, source citations, supported ticker filters, saved local conversations, session history, and decomposed sub-queries.

The research workspace uses a warm paper/navy palette with calmer indigo action
accents and teal verification states in both light and dark themes.

The workspace keeps the primary question flow compact: advanced retrieval
settings, interpreted queries, decomposition traces, and filing evidence are
progressively disclosed so the answer remains the visual focus. The layout is
responsive for mobile drawers, keyboard navigation, dark mode, and reduced
motion preferences.

## Conversation Library

Conversations persist through a schema-v2 repository that writes both IndexedDB
and a localStorage mirror, then merges both backends by `revision` on load:

- Custom titles (`titleMode: "custom"`) survive autosave; the auto title only
  follows the first question until you rename the conversation.
- Deletions write revision tombstones, so a stale fallback copy can never
  resurrect a deleted conversation.
- Corrupt or unreadable storage is left untouched and reported; a newer
  IndexedDB schema opens read-only instead of being wiped.
- Write results are explicit: `persisted`, `volatile`, or `failed`. The Library
  shows "Saved on this device" only after a durable write, and "Only kept in
  this tab" whenever storage is unavailable. Deletion stays retryable when no
  durable backend accepts the tombstone.
- Limits are 100 conversations and 25 MiB of UTF-8 JSON. Reaching a limit never
  silently drops records; the newest conversation stays in memory with a
  warning while older records remain readable and exportable.

Saved conversations whose backend session has expired become read-only: history
stays readable, searchable, bookmarkable, and exportable, while sending and
retry are locked. The composer still accepts drafts so they can be carried into
a new conversation. `Ctrl/Cmd+K` focuses the Library search; the Help dialog in
the header documents usage and shortcuts.

Answers expose a per-answer Bookmark control, and the Library's "Bookmarked
answers" filter opens the exact message. Each evidence panel has a literal,
case-insensitive search that filters excerpts while keeping the original
`[Source N]` numbering, plus a per-excerpt copy button that includes the
citation, company, section, and filed date. Filed dates are document metadata
and are never presented as the fiscal period of a number.

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

## Browser Verification

Browser tests run against the production build with fully mocked API routes;
no test reaches a real backend or provider.

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 bun run test:e2e
bun e2e/token-contrast.mjs
```

`test:e2e` builds, serves `dist/` with `vite preview`, and runs Playwright
across Chromium and Firefox: streaming and dropped-stream normalization,
bookmarks, evidence search and copy, read-only sessions, help and shortcuts,
theme persistence, and a Light/Dark x 390/768/1440 screenshot matrix written
to `e2e/screenshots/`. The token contrast script verifies the real Light/Dark
CSS token pairs against WCAG ratios (4.5:1 body text, 3:1 state text and
focus indicators). Traces, reports, and screenshots stay outside Git; CI
uploads them as artifacts on failure.

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
| `GET` | `/session/{session_id}/history` | Load conversation history plus backend context metadata |
| `DELETE` | `/session/{session_id}` | Clear a conversation session |

The streaming endpoint returns records in this format:

```text
data: {"type":"sources|token|done|error","data":...}
```

Initialization requests share one `AbortController` and are cancelled on unmount. During an active SSE response, the input exposes a Stop button that aborts the request, preserves any partial answer already rendered, and immediately re-enables the input. Reloaded session history renders full assistant answers without client-side truncation.

Source objects contain `citation`, `score`, `text_preview`, and optional full
`text` plus `chunk_id`, `ticker`, `section`, and `filing_date` metadata. The
health payload may include `corpus.searchable_company_count` and
`corpus.indexed_chunk_count`. Decomposed responses also include
`was_decomposed`, `sub_queries`, and `num_total_chunks`.

Session history responses may include an optional `context` object
(`status: "available" | "missing"`, `retained_turns`,
`ttl_remaining_seconds`). Older backends without `context` are supported:
the frontend infers availability from the turns array.
