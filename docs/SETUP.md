# FilingScope — Setup and Operations

Current installation, corpus preparation, local Deep access and deployment instructions.
For the public story, see the [README](../README.md).
For a provider-free recording, use the [Demo Guide](DEMO_SCRIPT.md), which
needs no real `.env`, corpus or Groq request. For the product, follow the steps
below. A clean clone excludes `data/`, credentials and model caches.

## 1. Install the backend

Use Python 3.10+; the backend CI uses Python 3.12. From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` locally. Keep the checked-in pinned embedding/reranker revisions;
rebuild model/index provenance together if intentionally changing them.
Important settings (values below are placeholders, not credentials):

```text
GROQ_API_KEY=your_primary_groq_key
GROQ_API_KEY_FALL_BACK=optional_fallback_key
GROQ_KEY_POLICY=key5_only
QDRANT_MODE=local
QDRANT_LOCAL_PATH=data/processed/qdrant
QDRANT_INDEX_MANIFEST_PATH=data/processed/qdrant_index_manifest.json
EMBEDDING_GENERATIONS_DIR=data/embedding_generations
EMBEDDING_GENERATION_PATH=data/embedding_generations/<completed-generation-id>
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
WORKSPACE_MODE=public
ENABLE_WORKSPACE_EXECUTION=false
```

`key5_only` is a retained policy identifier selecting primary `GROQ_API_KEY`.
`pool` selects primary then optional fallback with deduplication and bounded
429 cooldown/failover for ordinary generation. Strict Agent decisions require
primary, one HTTP attempt and no fallback rotation. Generation/judging share
the credential policy but retain separate accounting. Keep real secrets out of
Git, URLs, logs and `VITE_*` variables. See [.env.example](../.env.example) for all
settings and [credential history](ENGINEERING_REFERENCE.md#local-setup).

## 2. Prepare searchable artifacts

Use an existing trusted local index or a complete Qdrant Cloud collection.
For a new local corpus, build in this order from the repository root:

```powershell
.venv\Scripts\python.exe -m scripts.download_filings
.venv\Scripts\python.exe -m scripts.chunk_filings
.venv\Scripts\python.exe -m scripts.add_table_chunks
.venv\Scripts\python.exe -m scripts.embed_chunks --generation-id <new-unused-generation-id>
.venv\Scripts\python.exe -m scripts.index_chunks
```

These commands download/process filings and models; they are not needed for the
fixture demo. Set a valid SEC User-Agent with your own contact identity in
[`scripts/download_filings.py`](../scripts/download_filings.py) before downloading.
Rechunking can remove appended table chunks, so rerun table extraction,
embedding and indexing in order. Do not assume old embeddings match new chunks.

Trusted embedding requires the pinned `EMBEDDING_MODEL_REVISION` from
`.env.example` and an unused generation ID. Embedding publishes an immutable
completed generation with disk-validated metadata and hashes. Set
`EMBEDDING_GENERATION_PATH` to that completed generation **before indexing**.
Indexing verifies corpus/vector/model fingerprints and point counts before
publishing its manifest; it does not fall back to older embedded JSONL.
Reuse requires exact metadata, canonical payload, file hash and vector shape.
[Full provenance/rebuild instructions](ENGINEERING_REFERENCE.md#local-setup).

## 3. Start the API and frontend

Backend terminal, repository root:

```powershell
.venv\Scripts\python.exe -m uvicorn src.api.app:app --reload --port 8000
```

Use **one API worker with Qdrant local mode** because its storage has a file
lock. Switch to Qdrant server/cloud before multiple API processes. Swagger is
`http://localhost:8000/docs`; readiness is `/health/ready` (`503` until ready).
Run `python -m scripts.diagnostics.rag_smoke_test` in the activated environment
for the opt-in product smoke; it can use configured providers.

Frontend terminal, repository root:

```powershell
cd frontend
bun install --frozen-lockfile
Copy-Item .env.example .env.local
bun run dev
```

Set `VITE_API_BASE_URL=http://localhost:8000` in `frontend/.env.local`. Open
`http://localhost:3000`, select **Research → Quick**, ask a filing question and
open its citations. The frontend is a separate React/TypeScript application;
do not run Python tools inside `frontend/`. See [frontend setup](../frontend/README.md).

## 4. Enable local Deep Research explicitly

Public mode is the default and leaves private workspace reads/writes/jobs
unavailable. For local research only, configure the server:

```text
WORKSPACE_MODE=local
LOCAL_WORKSPACE_TOKEN=<dedicated-random-token-at-least-32-non-whitespace-characters>
LOCAL_WORKSPACE_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
LOCAL_WORKSPACE_ALLOWED_HOSTS=localhost,127.0.0.1,[::1]
ENABLE_WORKSPACE_EXECUTION=true
WORKSPACE_DB_PATH=.local/workbench/workspace.sqlite3
WORKSPACE_RUNS_DIR=.local/workbench/runs
WORKSPACE_SQLITE_BUSY_TIMEOUT_MS=5000
```

Access requires a direct loopback socket peer plus exact allowed Host, Origin
and bearer. Forwarding headers do not bypass this boundary. Use a dedicated
workspace token, never a provider key. Connect through the local workspace UI;
the browser verifies access and retains the token only in memory. Disconnect or
a full reload forgets it; reconnect to inspect saved runs.

Choose **Deep Research**, submit the visible goal and explicitly permit decision
provider use for that run. Configured model availability and remaining budget
still apply. The full inspector is `/agent`. Its DATA-004 SQLite rows own the
result/evidence/evaluation, while conversation cards contain safe references.
The two fixed consumers start in one process. Do not use the public Vercel site
as a substitute for the local access boundary.

SQLite uses foreign keys, WAL where supported, bounded busy timeout and short
serialized writes with ordered migrations. Relative workspace paths stay under
ignored `.local/`, separate from canonical corpus/index/PDF data. Public mode
does not open/create this private DB. Run/job history and telemetry are excluded
from portable workspace backup. See [authority and persistence](../ARCHITECTURE.md).

## 5. Docker, cloud and public frontend

The backend Docker image uses CPU-only PyTorch and **does not bundle or serve
the frontend**. `.dockerignore` excludes `frontend/`. For local mode, corpus
artifacts must exist on the host under `data/processed/` before Compose starts.
Use the [local release runbook](LOCAL_RELEASE_RUNBOOK.md) to bind the image
and health receipt to the Git revision:

```powershell
$releaseSha = (git rev-parse HEAD).Trim()
$env:GIT_REVISION = $releaseSha
docker compose build --build-arg GIT_REVISION=$releaseSha
docker tag edqa-api:local edqa-api:$releaseSha
docker compose up -d --no-build
```

Verify `http://localhost:8000/health/ready` reports `pipeline_ready=true`.
The release smoke checks readiness/ticker discovery without a query provider
call. [Docker details](ENGINEERING_REFERENCE.md#running-with-docker).

For Qdrant Cloud, configure `QDRANT_CLOUD_URL` / `QDRANT_CLOUD_API_KEY`, run
`scripts.migrate_to_qdrant_cloud`, then `scripts.verify_qdrant_cloud` before
switching `QDRANT_MODE=cloud`. Migration upserts by default; `--recreate` replaces
the collection and is only for an intentional rebuild. Cloud startup hydrates
complete chunk payloads to rebuild BM25/structured lookup, so a stateless hosted
image does not require ignored local corpus files.
[Cloud migration commands](ENGINEERING_REFERENCE.md#qdrant-cloud).

Deploy Vercel with project root **`frontend`** and a reachable
`VITE_API_BASE_URL` backend URL. Add the exact deployed frontend origin to
`ALLOWED_ORIGINS`; never use wildcard CORS. CORS is not authentication.
The existing public demo uses the owner's local Docker/ngrok services:

```powershell
.\scripts\start_demo.ps1
# After the demonstration:
.\scripts\stop_demo.ps1
```

The frontend stays available when those services stop; questions require them
to be online. Ngrok browser fetches may require `ngrok-skip-browser-warning:
true`, already supported by the frontend. Configure `TRUSTED_PROXY_CIDRS` only
for actual proxy peers when public per-IP limits run behind a tunnel/proxy.
[Demo operations](ENGINEERING_REFERENCE.md#zero-cost-public-demo).

## 6. Run local checks

Backend, repository root:

```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
.venv\Scripts\python.exe -m compileall src scripts configs
```

The hermetic suite blocks unmocked external sockets. `live_network` is excluded
by default; real SEC connectivity belongs in the opt-in
`python -m scripts.diagnostics.sec_live_smoke`, not ordinary tests.

Frontend, from `frontend/`:

```bash
bun install --frozen-lockfile
bun run lint
bun run test
bun run build
bun e2e/token-contrast.mjs
bun run test:e2e
bun run test:e2e-integration
bun run test:e2e-product
```

Use `bun run test` (Vitest/jsdom), not Bun's native `bun test`. Browser gates
serve production builds and mocked routes; HTTP/SSE and product gates use real
FastAPI handlers with synthetic dependencies and isolated SQLite. Activate a
backend test environment or set `HARNESS_PYTHON` for harness gates. No live
Groq call is needed. The existing path-filtered Backend/Frontend CI is retained.
[CI gate details](ENGINEERING_REFERENCE.md#continuous-integration).
