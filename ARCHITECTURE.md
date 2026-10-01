# Architecture

This document describes the stable system design of Enterprise Document QA. Use
`README.md` for setup and public status, `PROJECT_STATE.md` for current metrics
and engineering decisions, and `AGENTS.md` for repository operating rules.

## System Context

OBS-001 adds opt-in content-free timing at existing Agent API, repository,
worker/provider/tool, native evaluation and SSE boundaries. Inclusive monotonic
spans are bounded and discarded after a typed sampled API/all-worker summary is written to
DATA-005's existing `telemetry_events` table (30-day retention, SQLite v7).
Python serialization wait, critical-section hold, connection opening, transaction
and read scopes are measured separately; instrumentation emits after product
locks release. There is no second telemetry store, new endpoint, dependency or
worker scheduling change. Private analytics keeps performance separate from
legacy request/quality populations. See the [protocol](docs/OBS_001_ATTRIBUTION_PROTOCOL.md).

Workspace initialization and ordinary operation ownership are separate. Authorized
factories use `ensure_initialized()` with a shared per-canonical-path validation
receipt, bound to filesystem identity and the exact migration contract. One cold
caller performs integrity/schema validation; concurrent callers wait for complete
publication. The registry holds weak references and retains no connection or
product data. Last-owner release ends that validation lifecycle; missing/replaced
files or different migration contracts require full validation. Explicit
`initialize()` always revalidates and clears the receipt on failure. The local
lifespan's repository retains the live owner; public startup/import remains lazy.

Ordinary readers already owned independent short-lived SQLite connections before
DB-SCALE-001. They were delayed by repeated factory initialization under the writer
RLock. Warm factories now bypass that boundary. Multi-statement job detail/list and
event reads use explicit `BEGIN` snapshots on their own connections. Connections
close on success/failure, including setup failure. Writers retain the existing
canonical-path RLock, nested migration reentrancy and `BEGIN IMMEDIATE`; no lock
is removed, no connection is shared, and provider/tool work remains outside writes.
WAL/NORMAL, busy timeout 5000ms, schema v7, DATA-004 CAS/events/recovery and DATA-005
authority are unchanged. See [DB-SCALE-001](docs/DB_SCALE_001_PROTOCOL.md).

```mermaid
flowchart LR
    Browser[Vite React Frontend]
    API[FastAPI Backend]
    Pipeline[RAG Pipeline]
    Retrieval[Hybrid Retriever]
    Qdrant[(Qdrant)]
    BM25[(In-Memory BM25)]
    Models[Local Embedding and Reranker Models]
    Providers[Groq API]
    Memory[(In-Memory Cache and Sessions)]

    Browser -->|REST / SSE| API
    API --> Pipeline
    Pipeline --> Retrieval
    Retrieval --> Qdrant
    Retrieval --> BM25
    Retrieval --> Models
    Pipeline --> Providers
    Pipeline --> Memory
```

The frontend and backend are separate applications and deployment units. The
backend Docker image does not build or serve the frontend. Browser-exposed
configuration is limited to `VITE_*` values and must not contain secrets.

The diagram shows the online answer path, not every authority. The current
system has three distinct access planes:

| Plane | FastAPI boundary | Authoritative state and work |
| --- | --- | --- |
| Public reads | Catalog, Search snapshots, provider-free Retrieval inspection, safe registries and published reports | Indexed corpus/Qdrant, in-memory BM25 and public report artifacts; no private workspace database is opened in public mode |
| Local private workspace | Explicit `WORKSPACE_MODE=local`, loopback socket peer, allowlisted Host/Origin and dedicated bearer | One SQLite database for typed Collections, transfer, durable jobs, evaluation job records and DATA-005 telemetry; browser conversations/preferences remain separately on-device |
| Execution-gated operations | Local private access plus `ENABLE_WORKSPACE_EXECUTION` | Bounded DATA-004 jobs; Pipeline stages in isolated destinations and EVAL-003 frozen plans, without automatic serving-corpus promotion or report publication |

The browser's shared connection owner holds the bearer only in memory for
Pipeline, Evaluation, Analytics, Logs and Settings private requests. Ordinary
Collections and model-test browser wrappers still lack that integration and
truthfully receive a refusal; public clients never inherit the bearer. Local
mode and its jobs assume one serving process. No Redis, Celery, Kafka, second
workspace database or external telemetry service is part of this topology.

The optional `src/agent/` package binds four in-process tools to the same
Search, Retrieval inspection, document catalog/chunk index and RAG services.
Its registry validates strict inputs, labels observations as untrusted data and
requires an explicit tool allowlist; RAG additionally requires an explicit
provider-execution policy. One run-local orchestrator accepts strict
structured decisions from one abstract decision model, applies step/tool and
observation bounds, validates final evidence IDs and returns a typed result.
Decision-model provider permission is independent of RAG provider permission.
The operational trace contains safe action facts, never model reasoning or raw
provider responses. Search writes only its existing bounded in-process
snapshot, and the document tool returns bounded indexed previews. This layer
has no HTTP self-calls or Agent UI. AGENT-003 wraps it in the same private
DATA-004 SQLite job authority used by Pipeline and Evaluation. A v7 migration
adds the `agent` namespace and bounded event summaries; one atomic job claim
owns each execution, and startup marks unreconciled active runs interrupted
without replay. `/agent/runs` reads require local bearer access, while creation
and cancellation also require execution capability. The runtime resolves a
decision model at execution. PROVIDER-001 binds one Groq native strict JSON
Schema adapter to the existing generator identity/credential authority. It
freezes safe provider/model/adapter/mechanism/key-policy metadata in the same
plan JSON, checks the binding at each decision, and leaves old unconfigured
plans unchanged. The protected configuration-status read exposes capability
without inference or probing; unsupported or unconfigured bindings fail closed.
The adapter has no tool execution or research loop: one bounded SDK proposal
passes strict local transport/semantic validation before existing orchestration
gates. Separate system control and untrusted goal/observation data are projected
from typed requests with remaining counts; configured secrets and machine paths
are refused. One attempt has no SDK or Generator retries, a 60 second total
deadline and five second connect timeout. Context-scoped SDK logging filters
prevent debug request/error disclosure without muting concurrent Generator
logs. Results retain only safe failure categories and execution facts.
AGENT-004 adds an optional
versioned research policy to that same loop: caller-declared bounded
objectives, a canonical source-identity ledger, typed gaps and final coverage
checks. Research configuration and terminal metadata use the existing frozen
plan/result JSON; decision events may name a safe objective ID. The workspace
schema remains v7. AGENT-006 evaluates a
terminal durable run as a read-only in-process snapshot of the frozen plan,
bounded events and result. Its versioned metrics keep operational outcomes,
structural evidence checks and missing prerequisites separate. The report
contains safe counters and provenance hashes, with no overall score,
provider call, Agent replay or storage mutation. UI-014 exposes that evaluator
through one private terminal-run read, bringing the API inventory to 90 method/path
pairs. The independent `/agent` frontend reuses the memory-only local bearer
owner, reads durable run/result/event state and renders the 21 native metric
results without calculating a score. See
[`docs/AGENT_EXTENSION_PLAN.md`](docs/AGENT_EXTENSION_PLAN.md) for the separate
optional sequence.

### Durable Agent worker ownership (SCALE-001)

Agent run creation now only admits/freeze-queues work; no Agent execution is
attached to the HTTP response. The application lifespan recovers DATA-004
running/cancelling jobs before starting one `WorkerSupervisor`. Startup is gated
by local workspace mode, execution enablement and the worker switch. Public
startup never opens SQLite; module imports never create worker tasks.

The immutable `ExecutorRegistry` is closed over application-owned callables,
with exactly `agent / bounded_agent_run` eligible in production. No persisted
namespace string imports code. Workers claim oldest `created_at ASC, job_id ASC`
using the existing listing index, a BEGIN IMMEDIATE write transaction and the
same revision/state/event primitive. The transaction closes before provider or
tool execution. The successful claim snapshot goes to `AgentJobExecutor`, which
resolves current runtime configuration, then `AgentDurableService.execute_claimed`
and the one existing AgentOrchestrator. Frozen policies/binding and durable
cancellation remain authoritative. Synchronous tool adapters are awaited in
thread offloads rather than blocking the shared event loop.

The default two fixed asyncio consumers (hard range 1–16) bound active Agent
execution; each holds its slot until its namespace executor returns. Each poll
retains at most one candidate per registry entry, not the queued payload set.
Idle/error polling waits on a stop-aware event for 500ms by default. There is no
per-queued-job execution task, memory queue, global queue cap, second database,
lease, heartbeat, automatic retry or job requeue. Executor failure is sanitized,
uncommitted owned work becomes interrupted, and the consumer continues. An
unexpected consumer death is logged without exception content, stops further
claims and makes existing readiness fail through a safe optional worker flag.

Shutdown stops claims, waits five seconds by default, then cancels unresolved
async owners and commits interruption. A pending short SQLite claim is shielded:
if cancellation races its commit, the bounded operation finishes and its owned
row is reconciled. Cleanup can therefore additionally wait for outstanding
SQLite busy-timeout operations. In-flight thread/provider effects remain
uncertain and may finish independently; cancellation does not claim they were
forcibly terminated. Startup interrupts all claimed running/cancelling work
without replay, including a crash before the first call or after an external
effect and before result commit. Never-claimed queued Agent work can execute
after restart. Ownership prevents competing concurrent execution in the known
single-process model; it does not promise exactly-once external effects.

Evaluation remains on its existing synchronous EVAL-003 response background
executor, preserving conservative attempted-slot/case/report receipts. Migrating
that thread/provider shutdown contract is separately scoped. The new registry
never steals Evaluation jobs. Pipeline remains queue/staging-only; model tests
remain bounded synchronous provider-free identity checks. Product routes stay
90; SQLite v7 and dependencies stay unchanged. No broker/distributed topology
or load/SLA claim is added. See [SCALING_ROADMAP](docs/SCALING_ROADMAP.md).

`src/api/app.py` owns FastAPI creation, lifespan/bootstrap, shared runtime
state, middleware, exception handling, and route registration. Existing
health, corpus metadata, system information, model/dataset registries,
published evaluation, session, cache, and metrics transports are grouped under
`src/api/routers/`; they receive
callbacks to the single application-owned pipeline and state instead of loading
models or stores. Query/SSE, retrieval inspection, and document/reader/PDF
routes remain at the application boundary while their compatibility-sensitive
transport and identity flows are still coupled there.

`src/workspace/telemetry.py` is the DATA-005 operational authority over the
existing workspace SQLite database. It stores immutable, content-free terminal
facts for a small allowlist of research operations and projects terminal
DATA-004 jobs directly from canonical job rows. `src/api/routers/telemetry.py`
owns the protected summary, timeseries, and cursor-log reads. Job events,
collection activity, terminal request telemetry, and conventional process logs
remain distinct concepts; no hidden JSON-lines or second database exists.

`src/api/registry.py` is the provider-free registry domain boundary. It derives
the three stable model roles from existing settings and already-loaded runtime
objects, without constructing or invoking them. Configuration, load, credential
presence, and availability are independent typed facts; remote provider
reachability remains unknown until an explicitly authorized provider operation
proves it. The same service exposes the serving corpus from API-003 catalog
statistics plus the Qdrant index manifest, and exposes only aggregate metadata
and a deterministic revision for the source-controlled evaluation test set.
Missing or inconsistent provenance is degraded rather than converted to healthy
or empty data. Public fields pass through identifier/hash allowlists, so settings
objects, credentials, and local filesystem paths never become response payloads.

## Deployment Topology

The default portfolio deployment is one FastAPI process with one Uvicorn worker:

```text
Vercel-hosted frontend
  -> HTTPS FastAPI backend
     -> local embedding and cross-encoder models
     -> local Qdrant volume
     -> Groq generation API
```

One worker is mandatory when `QDRANT_MODE=local` because embedded Qdrant uses a
file lock. Multi-worker or multi-instance serving requires Qdrant Server or
Qdrant Cloud plus shared state for rate limits, cache, and sessions.

The backend supports two vector-store modes behind the same `VectorStore`
interface:

| Mode | Intended use | Constraint |
|---|---|---|
| Local Qdrant | Default single-container deployment | One process must own the storage path |
| Qdrant Cloud | Multi-instance or externally managed deployment | Adds network latency and an external dependency |

Docker uses CPU-only PyTorch for portability. Local development can install a
CUDA PyTorch build independently.

## Offline Data Pipeline

```mermaid
flowchart LR
    SEC[SEC EDGAR 10-K HTML]
    Extract[Section Extraction]
    Chunk[Token-Aware Chunking]
    Tables[Financial Table Extraction]
    Embed[Local Embeddings]
    Index[Qdrant Index]
    Files[JSON / JSONL Artifacts]

    SEC --> Extract
    Extract --> Chunk
    SEC --> Tables
    Tables --> Chunk
    Chunk --> Embed
    Embed --> Index
    Extract --> Files
    Chunk --> Files
    Embed --> Files
```

The pipeline is intentionally file-backed and explicit:

1. `scripts.download_filings` downloads filings and extracts target sections.
2. `scripts.chunk_filings` creates text chunks.
3. `scripts.add_table_chunks` appends supplemental financial-table chunks.
4. `scripts.embed_chunks` generates embeddings and reprocesses stale outputs.
5. `scripts.index_chunks` rebuilds the local Qdrant collection.

Generated filings, chunks, embeddings, Qdrant storage, and evaluation artifacts
remain under `data/` and are excluded from git.

The extractor targets standard 10-K Item boundaries. Annual-report layouts,
page-range references, and incorporation-by-reference filings use separate
guarded extraction branches; the current IBM companion resolver is one such
branch and does not alter the standard section path. Remaining unsupported
annual-report layouts require their own read-only audit before production use.

## Online Query Paths

### Standard Query

```mermaid
sequenceDiagram
    participant C as Client
    participant A as FastAPI
    participant P as RAGPipeline
    participant R as HybridRetriever
    participant L as LLM Provider

    C->>A: POST /query
    A->>P: query(question, filters, session)
    P->>P: Rewrite follow-up when history exists
    P->>R: Retrieve grounded chunks
    R-->>P: Ranked evidence
    P->>L: Generate answer with evidence
    L-->>P: Cited answer
    P-->>A: Answer and sources
    A-->>C: JSON response
```

`/query` runs synchronous pipeline work in an abandonable AnyIO worker. The HTTP
request returns `504` after the hard deadline. Python cannot safely terminate a
thread already executing, so a timed-out worker may finish in the background and
its result is discarded.

### Streaming Query

`/query/stream` uses Server-Sent Events with `sources`, `token`, `done`, and
`error` events. A shared `threading.Event` propagates cancellation from client
disconnect or timeout through the pipeline and provider token loops. Partial
answers are not stored in cache or conversation memory after cancellation.

### Decomposed Query

```mermaid
flowchart LR
    Question[Complex Question]
    Planner[QueryDecomposer Planner]
    Validate[Validate Ticker and Section]
    Subqueries[Focused Sub-Queries]
    Retrieve[Hybrid Retrieval]
    Guard[Minimum Evidence Guard]
    Synthesize[Grounded Synthesis]

    Question --> Planner --> Validate --> Subqueries --> Retrieve --> Guard --> Synthesize
```

`/query/decomposed` handles comparative and enumeration-style questions. Planner
output is treated as untrusted: unsupported tickers and invalid sections are
dropped before execution. The endpoint currently returns one completed JSON
response; the frontend labels it as an execution summary rather than a live
trace.

## Retrieval Architecture

The retriever combines complementary signals:

1. BM25 retrieves exact terms, company names, numbers, and table labels.
2. Qdrant retrieves semantically similar chunks from local embeddings.
3. Query-shaper hints can add a scoped lexical candidate ladder in strict
   `exact_phrase -> full_terms -> partial_terms -> fuzzy` order. Fuzzy matching
   requires a ticker and runs only when every preceding tier misses.
4. Reciprocal Rank Fusion merges BM25, semantic, and any ladder ranking.
5. A cross-encoder re-ranks the fused candidate pool.
6. Filters enforce ticker and section constraints.
7. Structured lookup promotes high-confidence financial rows and auditor
   signature evidence for supported query patterns.

Embedding and cross-encoder inference share a model lock. This prevents a
confirmed model thread-safety race but serializes the expensive inference region
inside concurrent decomposed requests.

Structured lookup is deliberately narrow. It does not replace semantic retrieval
or attempt to parse every financial concept. New patterns should be added only
when exact labels can be matched without promoting related subtotals.

## Generation And Grounding

The generation layer receives only retrieved filing evidence and applies these
rules:

- Cite factual claims with `[Source N]`.
- Quote financial values as represented in evidence.
- Do not answer from unsupported general knowledge.
- Return an explicit insufficient-context response when evidence is inadequate.

Groq is the only LLM provider. Serving, rewriting, decomposition, synthesis, and
evaluation use `openai/gpt-oss-120b` through the Groq API.
`src/generation/provider_policy.py` is the credential authority: `pool` selects
unique primary `GROQ_API_KEY` then optional `GROQ_API_KEY_FALL_BACK`. The retained
historical `key5_only` identifier selects primary only and preserves frozen
Agent binding IDs. Generator cooldown/failover is bounded; Agent decisions make
one HTTP attempt with no fallback rotation. Generation and judge clients share
eligible credentials but keep separate request accounting. No credentials enter
browser configuration, frozen plans, observations, events or evaluation reports.
Provider streams are closed in `finally` blocks, but provider-side billing
cancellation remains best effort.

## State And Persistence

| State | Current storage | Persistence behavior |
|---|---|---|
| Vector index | Local Qdrant or Qdrant Cloud | Persistent |
| Chunk and embedding artifacts | Local files under `data/` | Persistent |
| BM25 index | Process memory, rebuilt at startup | Lost on restart |
| Semantic response cache | Process memory | Lost on restart |
| Conversation sessions | Process memory with TTL | Lost on restart |
| Rate-limit counters | Process memory | Lost on restart |
| Workspace records and durable jobs | Local workspace SQLite | Persistent in explicit local mode; excluded from public mode |
| Terminal request telemetry | Same local workspace SQLite | Immutable, 30-day retention; portable backup excludes it |
| Sanitized logs | Read projection over telemetry and terminal jobs | Seven-day query window; no second log store |

Conversation history retains a bounded number of turns. The history API and LLM
rewrite path both use complete stored messages; presentation does not truncate
assistant answers.

Stateless cache entries are filter-aware so responses are not reused across
incompatible ticker or section constraints.

### Terminal telemetry and operational logs

The terminal request population is intentionally smaller than all HTTP traffic:
standard/decomposed query, both query streams, discovery Search, and retrieval
inspection. Non-streaming duration uses the completed application response.
Streaming duration closes only on the actual terminal stream event, timeout,
disconnect/cancellation, or incomplete producer close; HTTP headers are not a
latency endpoint. Unknown timing remains null.

Each record has a server identity, UTC terminal timestamp, route template,
subsystem/capability, independent severity and outcome, safe request
correlation, optional allowlisted error code, and small typed metadata. The
ingress rejects credential-shaped values, configured secrets, absolute paths,
control/newline input, unsupported fields, and oversized data before SQLite.
Client request IDs are accepted only as bounded opaque values; unsafe values
are replaced and never echoed. Legacy in-memory `/metrics` also aggregates by
route template so dynamic private identifiers do not enter its snapshot.

Telemetry writes are idempotent and immutable by server record ID, but are
best-effort relative to the already completed request. A write failure cannot
rewrite or fail that request, and there is no exactly-once claim across process
loss before the write. DATA-004 terminal jobs are not copied: protected reads
derive `job_terminal` records from the canonical job state/revision. Cancelled
and interrupted remain distinct outcomes; `budget_exhausted` remains the stored
job failure condition but uses warning rather than provider-error severity.

All operational reads reuse the API-001 local-only bearer/loopback/Host/Origin
boundary. Public mode returns the fail-closed private-workspace response without
opening SQLite. Summary populations define their numerators and denominators;
timeseries selectors and UTC bucket counts are bounded; logs use deterministic
`occurred_at DESC, record_id DESC` cursor pages. No query/document content,
free-form exception, provider body, stack trace, cost, token count, resource
measurement, or quality estimate is stored or derived.

## API Reliability And Security

The API uses layered controls:

| Control | Behavior |
|---|---|
| CORS | Allows configured browser origins, methods, and headers only |
| Error sanitization | Hides internal provider, path, and credential details |
| Query timeouts | Bounds non-streaming and streaming response duration |
| Per-IP rate limits | Shared burst and daily budgets across LLM routes; identity resolves through configured trusted proxies only |
| Cache protection | Limits cache diagnostics and disables cache clearing by default |
| Liveness | `/health/live` reports process availability |
| Readiness | `/health/ready` returns `503` until the pipeline is ready |

CORS is not authentication. Direct non-browser clients can call public routes.
Rate-limit identity comes from the ASGI client address unless the socket peer
belongs to `TRUSTED_PROXY_CIDRS`; only then is `X-Forwarded-For` walked
right-to-left through trusted hops to the first non-trusted address. Malformed
headers and unconfigured deployments fall back to the socket peer. The current
in-memory limiter is suitable only for the single-worker topology.

## Evaluation Architecture

The current product's native path is EVAL-001's versioned six-metric protocol
and explicit computed/unavailable/not-applicable semantics, EVAL-002's validated
public publications with backend-owned comparison/trends/failure aggregation,
then EVAL-003's protected, frozen, budgeted DATA-004 jobs surfaced by UI-011.
Private job completion is not public publication; one published run supplies
one observed trend point, not an interpolated history. EVAL-004/Ragas is an
optional isolated extension, not a dependency of this native path. DATA-005
records content-free terminal requests and canonical terminal-job projections
in the same SQLite database; UI-012 reads bounded Analytics/Logs from that
authority. Logs are not process-log ingestion, and absent timing stays null.

The following older Phase 2 benchmark and provider discussion is retained for
evaluation provenance, not as a replacement for the native UI/job protocol.

Evaluation routes fixed test cases through the same query decomposition and RAG
paths used by the application. It combines:

- LLM-as-judge faithfulness, answer relevancy, and context precision.
- Deterministic citation correctness, fallback accuracy, and recall proxy.
- Per-case checkpointing for quota-safe resume.
- Priority and category filters for controlled benchmark slices.

Context-rendering strategy is a binding evaluation input. The experimental
`comparative_packed_v3` strategy changes only comparative cases: it keeps the
first two unique chunks from each decomposition branch and then retains
structured hits and required-fact donors. Its provider A/B was rejected.
The offline-only v4 counterfactual instead keeps branch top 1 and adds only a
missing query-intent or explicit branch-fact donor. Non-comparative contexts
remain byte-identical to the frozen artifact. The oracle-free v5 selector is
shared with production `/query/decomposed` and passed its six-case provider
candidate gate, but remains experimental. The offline `selective_packed_v2`
composite applies the already admitted selective v1 policy to
`fact_lookup`/`multi_hop`/`summary`, v5 to `comparative`, and full evidence to
enumeration/out-of-corpus. Its fresh full N=30 replay passed the registered
completion, semantic, deterministic, answer-integrity, and comparative
contracts, so `selective_packed_v2` is now the Phase 2 evaluation default.

The direct generator, decomposed synthesis prompt, and Phase 2 generation
template share the same numeric-pair contract. When evidence contains
period/value pairs, answers must list the exact pairs before summarizing a
trend; they may not calculate differences or percentages, round or abbreviate
values, introduce ranges or numeric shorthand, or emit numbers absent from
the cited evidence. The focused two-case provider preflight for
`selective_packed_v2` passed this contract in both the focused preflight and the
admitted full N=30 replay.

Generation, deterministic metrics, and judging must consume the same rendered
evidence context. The generation binding includes a renderer fingerprint in
addition to the named strategy; changing context-renderer semantics invalidates
old checkpoints. This prevents a packed judge context from being attached to an
answer generated from full evidence.

Checkpoint records are filtered to the selected test questions before aggregation.
Fresh runs can explicitly remove the active checkpoint. A run with skipped cases
exits unsuccessfully and must not replace official reported metrics.

The official benchmark and current scores belong in `README.md` and
`PROJECT_STATE.md`, not this architecture document.

## Intentional Boundaries

The following are deliberate current boundaries, not accidental omissions:

- The backend does not serve the frontend bundle.
- Local Qdrant does not support multiple backend workers.
- Decomposed responses are not streamed as a live sub-query trace.
- Cache, sessions, and rate-limit counters are not distributed.
- Remaining annual-report cross-references need dedicated extraction routes;
  IBM's verified companion route is already supported separately.
- Retrieval parameters already rejected by measured experiments should not be
  reopened without new evidence.

## Extension Paths

The architecture supports these upgrades without redesigning the entire system:

- Move Qdrant from local mode to Qdrant Server or Cloud.
- Move cache, sessions, and rate-limit counters to Redis.
- Add a persistent session backend behind the conversation-memory interface.
- Add hosting-specific trusted-proxy configuration.
- Add annual-report-aware extraction for remaining unsupported layouts as
  separate ingestion paths.
- Add true decomposed SSE events while preserving existing response contracts.

Any upgrade that changes retrieval behavior, evaluation methodology, ingestion
order, or deployment topology should first be recorded with evidence in
`PROJECT_STATE.md`.
