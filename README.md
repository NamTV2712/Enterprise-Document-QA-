# SEC Research Copilot

> Hybrid RAG + Durable Deep Research Agent for SEC 10-K Filings

Turn long financial filings into cited answers and inspectable research. Quick
Research streams a conversational RAG answer; Deep Research runs a bounded Agent
with durable progress, cancellation and evidence. This technical portfolio
project combines retrieval, execution and an EN/VI research workspace.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-149ECA?logo=react&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-DC244C)
[![Backend CI](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/workflows/backend.yml/badge.svg)](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/workflows/backend.yml)
[![Frontend CI](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/workflows/frontend.yml/badge.svg)](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/workflows/frontend.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[🚀 Live Demo](https://frontend-one-gamma-f9jf11u8ec.vercel.app) ·
[🏗 Architecture](#architecture) · [📖 Case Study](docs/PORTFOLIO_CASE_STUDY.md) ·
[▶ Demo Guide](docs/DEMO_SCRIPT.md) · [⚙ Setup](#local-setup)

## Live Demo

**[Open the frontend preview](https://frontend-one-gamma-f9jf11u8ec.vercel.app).**
The Vercel site resolves and loads the workspace, but the backend reported
**API offline** in the 2026-10-03 audit. Live RAG requires the owner's backend
and tunnel to be running. Private Deep execution requires the local workspace
connection described below; Vercel alone does not provide it.

The [Demo Guide](docs/DEMO_SCRIPT.md) is a separate 5–7 minute recording plan
using provider-free fixtures and real API/SQLite behavior. No demo video is
published yet. The original repository name is **Enterprise Document QA**;
the repository slug and product routes remain unchanged.

## Product overview

Filings spread financial facts across narrative sections, tables, footnotes and
reporting periods. Lexical search helps with exact accounting terms; semantic
search helps with paraphrases. The workspace combines both, then reranks and
generates against bounded evidence so readers can inspect what supports an answer.

Use Quick for a filing question or follow-up. Use Deep for an explicit research
goal that needs an inspectable execution record. **Research deeper** prepares a
visible draft from a completed Quick question and requires another submit.

## Quick vs Deep Research

| Dimension | Quick | Deep Research |
|---|---|---|
| Purpose | One conversational RAG turn | Bounded research execution |
| Execution | FastAPI retrieval and streamed generation | Fixed worker → single Agent → closed tools |
| Persistence | Browser Library conversation; transient server session/cache | DATA-004 SQLite state, ordered events, result and evaluation; browser run reference only |
| Cancellation | Stops the active answer stream at supported boundaries | Revision-safe request; terminal acknowledgement at a safe boundary |
| Evidence | Citations and source chunks | Canonical evidence, tool activity and native terminal evaluation |
| Admission | Public RAG, subject to configured limits | Local connection, execution capability and per-run decision-provider consent |
| Duration | Retrieval/generation dependent | Queue plus multiple decision/tool boundaries; no fixed duration promise |

The generic Deep composer submits the visible goal and locale. It does not
inherit Quick history/filters or create a hidden multi-objective plan.

<a id="architecture-at-a-glance"></a>

## Architecture

![SEC Research Copilot: separate Quick RAG and durable Deep Research paths sharing retrieval and evidence](docs/assets/sec-research-copilot-architecture.svg)

Quick and Deep share the SEC corpus, Qdrant retrieval and Groq infrastructure.
Deep uses `search_documents`, `inspect_retrieval`, `read_document` and `ask_rag`;
provider-backed decisions and `ask_rag` require their configured permission.
DATA-004 owns durable Agent state. DATA-005 stores optional content-free telemetry
in the shared workspace database. The browser keeps references; the default is
**two fixed workers in one backend process** with a single bounded Agent
orchestrator. This topology has no distributed or hidden multi-agent execution.

[Full architecture](ARCHITECTURE.md) ·
[Open showcase HTML locally](docs/architecture/sec-research-copilot-showcase.html) ·
[Reproducible source](docs/architecture/sec-research-copilot-showcase.architecture.json)

Detailed interactive diagrams: [System Architecture](docs/architecture/sec-research-workspace.html),
[Query Data Flow](docs/architecture/sec-research-query.html),
[Research Workflow](docs/architecture/sec-research-workflow.html).
Download/open the standalone HTML files locally; GitHub's file view does not run
them. These detailed diagrams document the existing research/RAG paths;
[ARCHITECTURE.md](ARCHITECTURE.md) also covers durable Agent contracts.

## Key features

| Feature | What a reader can do |
|---|---|
| Quick Research | Stream cited answers, ask follow-ups and inspect source evidence |
| Deep Research | Start a durable run, inspect bounded tool activity, cancel, and read terminal evidence/evaluation |
| Hybrid retrieval | Combine BM25 and Qdrant candidates with RRF and cross-encoder reranking |
| Evidence-first UX | Open canonical chunks and document readers from citations; inspect provenance and unavailable states |
| Conversation and research | Use query rewrite/decomposition, scoped comparisons and EN/VI workspace controls |
| Execution engineering | Inspect FastAPI/SSE contracts, SQLite authority, bounded workers and content-free observability |

## Tech stack

| Layer | Technologies |
|---|---|
| AI / retrieval | Sentence Transformers embeddings, BM25, Qdrant, RRF, cross-encoder, Groq |
| Backend | Python, FastAPI, Pydantic, SQLite, SSE |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, Bun 1.3.14 |
| Verification / operations | pytest, Vitest, Playwright, GitHub Actions, deterministic provider doubles |

## Engineering highlights

- **Complementary retrieval signals:** rank fusion combines lexical and semantic
  candidates without treating unrelated scores as probabilities. Reranking
  precedes bounded generation context; its score is not confidence.
- **Traceable evidence:** canonical document/chunk identities survive context
  construction and citations. Acquisition, ingestion and reader representations
  have separate responsibilities; insufficient context stays visible.
- **Durable authority:** short SQLite writes own revisions, events, results and
  evaluation. Provider work runs outside transactions. Restart reconciliation
  marks uncertain claimed work interrupted instead of replaying external effects.
- **Bounded tools and cancellation:** typed closed tools validate arguments and
  capabilities. Fixed consumers preserve the process boundary; requesting cancel
  and reaching terminal cancellation are separate states.
- **Measured operation:** optional DATA-005 records bounded timings, counts and
  outcomes without goals, answers or credentials. Hermetic doubles exercise real
  API, storage, HTTP/SSE and browser boundaries without live provider calls.

## Measured results

| Measurement | Recorded result | Evidence and scope |
|---|---|---|
| Configured corpus | 50 companies | Configuration, not customers; [coverage history](docs/ENGINEERING_REFERENCE.md#supported-corpus) |
| Canonical local index | 10,053 chunks/points | Authorized unit-metadata rebuild; [corpus reference](docs/ENGINEERING_REFERENCE.md#financial-table-unit-preservation--canonical-rebuild-complete) |
| Read50 client p95 | 1967.995 → 982.813 ms | Real HTTP/SQLite with synthetic dependencies, median trial statistics; [DB-SCALE receipt](docs/DB_SCALE_001_FINAL_RECEIPT.md) |
| Idle-confirmed queue p95 | 502.753 → 9.340 ms | Two workers, 500ms polling fallback; [WORKER-002 receipt](docs/WORKER_002_FINAL_RECEIPT.md) |
| Warm navigation p95 | Chromium 63.30 ms / Firefox 42.00 ms | 30 observations per engine, synthetic workload; [final receipt](docs/IMPROVEMENT_FINAL_RECEIPT.md) |

**Controlled local/development measurements; not production SLA results.**
The corpus is not bundled with a clean clone or inferred from the Vercel preview.
Measurements describe different stages/populations. Saturated queues and mixed
admission contention remain; more workers did not improve every workload.
[Capacity tradeoffs](docs/CAPACITY_001_FINAL_RECEIPT.md) include counterevidence.

## Validation

Frozen **code release**: `cbaacc3765f8dbca2ff04247cb24fd773751a0f9`.
These are recorded gates for that release, not fresh tests of this docs change.

| Gate | Recorded result |
|---|---|
| Backend primary / clean checkout | 1958 passes / 1924 passes + 34 expected artifact-dependent skips |
| Frontend unit / browser matrix | 96 files / 844 tests; 542 browser passes, 4 inherited skips, 0 failures |
| HTTP/SSE / Agent shell / durable Agent harness | 16 / 32 / 12 passes in separate gates |
| TypeScript / production build / contrast | PASS |
| Exact code-release CI | [Backend SUCCESS](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/runs/37085104945) / [Frontend SUCCESS](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/runs/37085104875) |

Skips are not passes. Backend warnings remain (188 primary; 149 clean).
The [final receipt](docs/IMPROVEMENT_FINAL_RECEIPT.md) records candidate/closure
provenance, warning/skip reasons and gate scopes. Browser and contrast checks do
not imply a blanket accessibility certification. The docs showcase has its own
[artifact quality receipt](docs/SHOWCASE_002_RECEIPT.md).

<a id="setup-and-usage"></a>

## Local Setup

For a provider-free recording, use [the Demo Guide](docs/DEMO_SCRIPT.md), which
needs no real `.env`, corpus or Groq request. For the product, follow the steps
below. A clean clone excludes `data/`, credentials and model caches.

### 1. Install the backend

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
Git, URLs, logs and `VITE_*` variables. See [.env.example](.env.example) for all
settings and [credential history](docs/ENGINEERING_REFERENCE.md#local-setup).

### 2. Prepare searchable artifacts

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
[`scripts/download_filings.py`](scripts/download_filings.py) before downloading.
Rechunking can remove appended table chunks, so rerun table extraction,
embedding and indexing in order. Do not assume old embeddings match new chunks.

Trusted embedding requires the pinned `EMBEDDING_MODEL_REVISION` from
`.env.example` and an unused generation ID. Embedding publishes an immutable
completed generation with disk-validated metadata and hashes. Set
`EMBEDDING_GENERATION_PATH` to that completed generation **before indexing**.
Indexing verifies corpus/vector/model fingerprints and point counts before
publishing its manifest; it does not fall back to older embedded JSONL.
Reuse requires exact metadata, canonical payload, file hash and vector shape.
[Full provenance/rebuild instructions](docs/ENGINEERING_REFERENCE.md#local-setup).

### 3. Start the API and frontend

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
do not run Python tools inside `frontend/`. See [frontend setup](frontend/README.md).

### 4. Enable local Deep Research explicitly

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
from portable workspace backup. See [authority and persistence](ARCHITECTURE.md).

### 5. Docker, cloud and public frontend

The backend Docker image uses CPU-only PyTorch and **does not bundle or serve
the frontend**. `.dockerignore` excludes `frontend/`. For local mode, corpus
artifacts must exist on the host under `data/processed/` before Compose starts.
Use the [local release runbook](docs/LOCAL_RELEASE_RUNBOOK.md) to bind the image
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
call. [Docker details](docs/ENGINEERING_REFERENCE.md#running-with-docker).

For Qdrant Cloud, configure `QDRANT_CLOUD_URL` / `QDRANT_CLOUD_API_KEY`, run
`scripts.migrate_to_qdrant_cloud`, then `scripts.verify_qdrant_cloud` before
switching `QDRANT_MODE=cloud`. Migration upserts by default; `--recreate` replaces
the collection and is only for an intentional rebuild. Cloud startup hydrates
complete chunk payloads to rebuild BM25/structured lookup, so a stateless hosted
image does not require ignored local corpus files.
[Cloud migration commands](docs/ENGINEERING_REFERENCE.md#qdrant-cloud).

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
[Demo operations](docs/ENGINEERING_REFERENCE.md#zero-cost-public-demo).

### 6. Run local checks

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
[CI gate details](docs/ENGINEERING_REFERENCE.md#continuous-integration).

## Limitations

- Single-process Agent workers; ordinary recommendation is 1–2. Capacity
  results do not establish a distributed system, service SLA or live Groq quota
  certification. Generic goals have no hidden automatic multi-objective planner.
- The 50-company corpus has uneven extraction coverage. Four filings remain
  degraded but searchable; table and annual-report layouts need source checking.
  Canonical rebuilds do not automatically promote the protected quality benchmark.
- Retrieval/citations improve auditability, not guaranteed correctness. Check
  filing identity, period, units and supporting text. Native Agent evaluation is
  structural and does not supply an overall factual-accuracy score.
- Public API routes are unauthenticated. Exact CORS, input validation and
  configured per-IP limits mitigate abuse but do not prevent every direct client.
  Private capabilities require the loopback/Host/Origin/bearer boundary.
- Server session memory and semantic cache are transient. Follow-up rewriting
  adds a provider call; Groq `429` responses/cooldown can increase latency.
- Collections and model-test browser bearer integration remain staged. Ragas is
  optional. Do not weaken the server boundary to work around unavailable clients.
- Native zoom at 125/150/200% is manual/unverified. The ~527.24 kB main bundle
  warning and backend parser/dependency warnings remain.
- The public website is a frontend preview when its backend is offline. No
  always-on hosted RAG/Deep operation is implied.

[Detailed limitations/history](docs/ENGINEERING_REFERENCE.md#known-limitations) ·
[Case study tradeoffs](docs/PORTFOLIO_CASE_STUDY.md#tradeoffs-and-limitations)

## Technical reference

### Retrieval, generation and API

BM25 and dense candidates are fused with RRF, then cross-encoder reranked.
Query rewrite preserves follow-up meaning; decomposition supports comparative
scope. Structured financial lookup and table unit preservation complement the
passage pipeline. The generation renderer binds the same evidence to generation,
deterministic metrics and judging. Its binding fingerprints prevent stale
checkpoint resume after semantic changes. [Retrieval design](docs/ENGINEERING_REFERENCE.md#retrieval-design)
and [generation design](docs/ENGINEERING_REFERENCE.md#generation-design).

| API family | Representative routes / behavior |
|---|---|
| Health / metadata | `/health/live`, `/health/ready`, `/supported-tickers`, `/system/info`, `/models`, `/datasets` |
| Quick / retrieval | `/query`, `/query/stream`, `/query/decomposed`, `/retrieval/inspect`, `/search` |
| Evidence | `/documents`, `/documents/{document_id}/chunks`, `/chunks/{chunk_id}`; safe metadata/text, no machine paths |
| Durable Agent | Protected Agent run admission, state, ordered events, cancellation, result/evidence/evaluation; [Agent contract](docs/frontend/FRONTEND_CONTRACT.md) |
| Local operations | Protected Pipeline/Evaluation job history, analytics and logs; execution has a separate capability |
| Sessions / cache | Transient server session history and semantic cache; cache clear disabled by default |

Swagger at `/docs` is the runtime API reference. The frozen release has 90
method/path pairs over 80 unique paths; historical endpoint tables are not a
complete route inventory. [Detailed endpoint reference](docs/ENGINEERING_REFERENCE.md#api-endpoints).

The non-streaming query timeout is 60s (`504`). Python cannot safely kill a
running synchronous thread; a timed-out result may complete in the background
and is discarded. Public query defaults are 10/minute and 100/day per IP;
decomposed queries additionally use 5/minute. In-memory rate-limit storage
matches the single-process local-Qdrant setup; multiple instances would require
shared storage. Proxy identity trusts only explicitly configured socket peers.

### Evaluation and evidence

The official reported quality benchmark remains clean priority `<=2`, N=30,
unless the journal explicitly supersedes it. It is distinct from the canonical
corpus rebuild, native Agent structural metrics and local performance campaigns.
Quota-skipped, checkpoint-mixed or provider-incomplete candidates are not final
results. A generation checkpoint is append-only with one binding; changes require
a fresh path. Judge checkpoints need complete per-case provenance checks.

Phase 1 produces a deterministic offline retrieval artifact. Phase 2 generates
and judges frozen contexts with binding-verified resume. Promotion requires a
separate admission audit; the protected official result path refuses overwrite
without the explicit override. Use fresh candidate checkpoint/output paths and
configured provider budget for an intentional campaign.
[Commands and historical results](docs/ENGINEERING_REFERENCE.md#evaluation-results) ·
[Project journal](PROJECT_STATE.md).

## Detailed documentation

- **Portfolio:** [Case Study](docs/PORTFOLIO_CASE_STUDY.md),
  [Demo Guide](docs/DEMO_SCRIPT.md), [CV / Portfolio Copy](docs/PORTFOLIO_BULLETS.md),
  [Interview Guide](docs/INTERVIEW_GUIDE.md).
- **Architecture:** [System contracts](ARCHITECTURE.md),
  [Frontend design](docs/frontend/DESIGN.md),
  [Frontend contract](docs/frontend/FRONTEND_CONTRACT.md),
  [Agent UX evidence](docs/UX_AGENT_001_FINAL_RECEIPT.md).
- **Engineering evidence:** [Final improvement receipt](docs/IMPROVEMENT_FINAL_RECEIPT.md),
  [DB read benchmark](docs/DB_SCALE_001_FINAL_RECEIPT.md),
  [Worker wake benchmark](docs/WORKER_002_FINAL_RECEIPT.md),
  [Capacity tradeoffs](docs/CAPACITY_001_FINAL_RECEIPT.md).
- **Setup/history:** [Engineering reference](docs/ENGINEERING_REFERENCE.md),
  [Local release runbook](docs/LOCAL_RELEASE_RUNBOOK.md),
  [Frontend README](frontend/README.md), [Project state](PROJECT_STATE.md).
- **Browse:** [Documentation index](docs/README.md), [Security policy](SECURITY.md),
  [Agent operating guide](AGENTS.md). Developer tooling under `.agents/` and
  historical receipts remain available without being prerequisites to the overview.

## License

Project source and documentation are available under the [MIT license](LICENSE).
Bundled third-party material retains its own licenses and notices, including
[Archify's MIT notice](.agents/skills/archify/LICENSE) and
[third-party notices](.agents/skills/archify/THIRD_PARTY_NOTICES.md).
Dependencies and external SEC filing content are not relicensed by the root license.
See [skill source provenance](.agents/skills/SOURCES.md).

<!-- Historical README links resolve here; detailed sections are preserved in the engineering reference. -->
<a id="enterprise-document-qa"></a>
<a id="why-this-project-exists"></a>
<a id="what-it-does"></a>
<a id="measured-engineering-improvements"></a>
<a id="current-boundaries"></a>
<a id="continuous-integration"></a>
<a id="running-with-docker"></a>
<a id="qdrant-cloud"></a>
<a id="zero-cost-public-demo"></a>
<a id="overview"></a>
<a id="documentation"></a>
<a id="current-v5-research-workbench"></a>
<a id="provenance-bound-pdf-representation"></a>
<a id="supported-corpus"></a>
<a id="api-endpoints"></a>
<a id="retrieval-design"></a>
<a id="generation-design"></a>
<a id="repository-structure"></a>
<a id="data-and-secrets"></a>
<a id="engineering-notes-and-evidence"></a>
<a id="start-here--current-product"></a>
<a id="evaluation-results"></a>
<a id="financial-table-unit-preservation--canonical-rebuild-complete"></a>
<a id="comparative-answerability-guard-v1--non-official-no-go"></a>
<a id="comparative-evidence-contract-v2--non-official-no-go"></a>
<a id="evidence-contract-v3--provider-incomplete--no-go"></a>
<a id="frontend-workspace-ux-and-themes"></a>
<a id="evaluation-analytics-and-quota-safe-campaign-handoff"></a>
<a id="historical-evaluation-log"></a>
<a id="historical-retrieval-and-packing-milestones"></a>
<a id="performance-notes"></a>
<a id="current-status"></a>
<a id="known-limitations"></a>
<a id="roadmap"></a>
<a id="why-this-project-matters"></a>
<a id="skill-governance"></a>
