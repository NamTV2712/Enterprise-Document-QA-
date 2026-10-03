# FilingScope — Engineering Case Study

Public project name: **FilingScope**. Repository: **Enterprise Document QA**.

An evidence-led portfolio project for SEC 10-K research, combining hybrid RAG
with bounded, durable Agent execution. [Product overview](../README.md),
[architecture](../ARCHITECTURE.md), [demo](DEMO_SCRIPT.md).

## Problem

Financial filings contain useful information across long narrative sections,
tables, footnotes and reporting periods. A question about risk may need a small
passage; a comparison may need evidence from several companies. Finding relevant
text is only part of the problem. The answer must preserve the filing identity,
units, period and source location so a reader can check it.

A language model presented with a broad question can produce plausible prose
without adequate evidence. Vector similarity alone can miss an exact accounting
label, and lexical matching alone can miss a paraphrase. A polished chat interface
also hides operational problems if a cancelled request keeps updating the screen
or a research run disappears when its browser tab closes.

I approached these as connected retrieval, execution and product problems. The
repository is configured for a 50-company SEC corpus, with generated data kept
outside source control. It is a technical portfolio project: there is no claim
of enterprise customer adoption, production traffic or a certified service SLA.

## Goals

The primary goal was grounded question answering with inspectable citations.
Follow-up questions should retain conversational meaning; comparative questions
should retrieve evidence for their requested scope. Missing context should remain
visible rather than being replaced with an unsupported answer.

For longer research, I wanted a durable execution record with bounded tools,
explicit cancellation and conservative restart behavior. The user should be able
to inspect safe progress, evidence and the terminal result. A single Research
workspace should expose those capabilities without silently turning an ordinary
RAG question into an Agent run.

Engineering goals included clear state ownership, local private-access controls,
reproducible evaluation, content-free attribution and tests that run without SEC,
Groq or model downloads. The design also needed an honest account of what remained
single-process, synthetic or unverified.

## Architecture

### Ingestion and corpus identity

The offline pipeline downloads SEC filings, extracts supported sections, creates
token-aware chunks, appends financial-table chunks, embeds them and builds the
Qdrant index. These are explicit steps, not automatic side effects of opening a
document. Generated filings, chunks, embedding generations and local vector
storage stay under ignored `data/`.

Embedding and index provenance bind the serving representation to its source.
This matters because an attractive source viewer is not evidence that a newly
downloaded filing has been indexed. Document acquisition, reader representation
and retrieval admission have separate contracts. Financial tables also preserve
units and periods rather than treating every extracted number as interchangeable.

### Retrieval and reranking

The online RAG pipeline combines BM25 with Qdrant semantic retrieval. Reciprocal
Rank Fusion merges rankings, then a cross-encoder reranks the candidate pool.
Ticker and section constraints preserve submitted scope. Narrow structured
lookups support documented financial-row and auditor patterns; they are not a
general financial parser.

Sentence Transformers supplies local embeddings and cross-encoder inference.
The configured embedding model is `nomic-ai/nomic-embed-text-v1.5`; the reranker is
`cross-encoder/ms-marco-MiniLM-L-6-v2`. The implementation protects shared model
inference with a lock, which trades concurrent throughput for a verified
thread-safety boundary. Retrieval inspection exposes stage-specific evidence;
a ranking score is not presented as answer confidence.

### Generation and Quick Research

Quick uses the existing FastAPI RAG paths, including streaming, bounded session
history, follow-up rewriting and optional query decomposition. Retrieved evidence
feeds grounded generation through Groq. Prompts require source citations and
explicit insufficient-context handling. Numeric answers preserve the period/value
pairs and units supplied by evidence.

The React 19/Vite/TypeScript frontend renders tokens, citations and source readers.
Stopping a stream preserves visible partial text while rejecting obsolete updates.
Comparative answering remains a Quick capability; it is not the Deep execution
engine. The frontend is deployed separately from the backend Docker image and
supports English/Vietnamese presentation and light/dark themes.

### Durable Deep Research

Deep Research submits the user's explicit goal to the Agent API. DATA-004, in the
local SQLite workspace, owns the frozen plan, state, revision, ordered events and
terminal result. One lifespan-owned WorkerSupervisor runs fixed consumers over
durable eligible rows. Two consumers are the default; queued rows do not allocate
one execution task each.

The orchestrator accepts strict structured decisions and applies a closed typed
registry: `search_documents`, `inspect_retrieval`, `read_document` and `ask_rag`.
Tool allowlists, provider grants, budgets and observation validation remain
application controls. The optional research policy accepts caller-declared
objectives; the current generic Deep composer does not invent them. Safe activity
facts are inspectable, while hidden model reasoning and raw provider bodies are
excluded from the trace.

### Persistence and observability

Browser conversations use record v5, envelope v4 and IndexedDB v2. An Agent
message stores its run reference, not a browser copy of authoritative results or
events. Reload loses the memory-only bearer and requires reconnection to read the
same run. Legacy Quick records retain their meaning.

DATA-005 shares the workspace database but has a different responsibility:
bounded content-free terminal telemetry and optional performance attribution.
Performance summaries exclude goals, prompts, answers, evidence, provider bodies,
credentials and SQL. Population labels distinguish sampled API records from
successful worker summaries; unavailable timing stays unavailable.

## Key engineering decisions

### Hybrid search rather than vector-only retrieval

I used complementary lexical and semantic signals because filing questions mix
exact financial language with natural paraphrases. RRF merges rank positions
without assuming BM25 and vector scores share a numerical scale. This choice
does not guarantee that every relevant passage reaches the candidate pool, so
retrieval diagnosis and evaluation remain necessary.

### Rerank a bounded candidate pool

A cross-encoder can compare the query with a passage more directly than a stored
embedding can. Applying it after fusion concentrates that cost on candidates.
Reranking cannot recover evidence that earlier stages discarded, and its score
is neither probability nor factual correctness.

### Separate Quick from durable Deep

Quick is a conversational RAG turn; Deep is a separately admitted bounded run.
I retained explicit selection and independent permissions because latency,
persistence and external-call ownership differ. Research deeper prepares a draft
and still requires submission. Quick history and filters are not silently
transferred into an Agent's hidden context.

### Use SQLite as the local authority

One SQLite database keeps job states, revisions and events within a tractable
transaction boundary. Canonical writer serialization, `BEGIN IMMEDIATE` and
compare-and-swap revisions protect transitions. An atomic oldest-eligible claim
establishes ownership before execution begins. This simplifies the documented
single-process topology; it does not prove distributed or exactly-once external
execution.

### Bound workers and preserve conservative recovery

Fixed consumers bound normal awaited Agent decisions. A payload-free admission
hint wakes the existing owner after durable commit; polling remains a fallback
for lost hints and restart. Claimed work interrupted by process loss is recorded
as interrupted and is not automatically replayed. A thread or provider effect
already in progress may outlive cancellation, so the design refuses to claim
that external effects were forcibly terminated.

### Make provider semantics and security explicit

Normal generation uses one primary Groq credential with an optional fallback;
the historical `key5_only` binding now means primary only. Agent decisions keep
one HTTP attempt, `max_retries=0`, a 60-second deadline and no fallback rotation
or repair loop. Strict structured output still passes application validation.
Private access additionally requires local mode, loopback peer, allowlisted
Host/Origin and a dedicated bearer; CORS alone is not authentication.

## Problems encountered and what changed

Repeated workspace initialization serialized otherwise independent reads behind
the writer lock. DB-SCALE separated guarded live-store validation from ordinary
connection ownership. Readers retain independent short-lived connections, and
multi-query reads pin WAL snapshots. Explicit initialization still performs a
full audit, including on reopen. Snapshot consistency and failed-setup cleanup
were verified alongside latency.

At low load, newly admitted Agent jobs could wait almost a complete 500ms poll.
WORKER-002 added a coalesced, payload-free wake hint after the durable HTTP
admission commit. Consumers still use SQLite claims. This addresses idle wake
delay without replacing the durable queue with an in-memory mirror or shortening
the fallback poll to chase a benchmark.

CI exposed OpenAPI representation drift between declared and development
Pydantic versions: equivalent object schemas represented unrestricted extra
properties differently. CI-FIX normalized the omitted/explicit-true equivalence
while preserving checks that reject real semantic changes. Frontend failures
also exposed cancellation-fixture readiness and focus ownership problems; fixes
made the tests exercise actual request boundaries rather than incidental timing.

The unified Research work uncovered late creates redirecting newer navigation,
older saves dropping accepted Agent references, stale reads overwriting drafts,
and SelectField close behavior stealing focus. Request ownership, origin-bound
reference linking and synchronous close-focus restoration repaired those
reproduced cases. FINAL-IMPROVE additionally caught entrance animation delays
under reduced motion. One CSS selector disabled those animations in that mode,
with a failing-before/passing-after browser assertion and an unchanged Axe gate.

## Results and evidence

These are controlled development benchmarks, not production SLA measurements.
The historical campaigns retain separate runtime bindings and use medians of
trial statistics; results are not pooled across campaigns.

| Observation | Recorded result | Context and source |
| --- | --- | --- |
| DB-SCALE read50 client p95 | 1967.995 → 982.813ms | Local real HTTP/SQLite, synthetic dependencies; [receipt](DB_SCALE_001_FINAL_RECEIPT.md) |
| WORKER idle default queue p95 | 502.753 → 9.340ms | Idle-confirmed singles, two workers, 500ms poll; [receipt](WORKER_002_FINAL_RECEIPT.md) |
| Final warm navigation p95 | Chromium 63.30ms; Firefox 42.00ms | Local synthetic frontend, 30 observations per engine, 200ms budget; [receipt](IMPROVEMENT_FINAL_RECEIPT.md) |

The DB campaign used five points and fifteen trials per stage. WORKER used
twenty-six points and seventy-eight trials per stage, with three trials per
point. Idle-confirmed singles intentionally favor observing a full remaining
poll. Saturated workloads and some admission/service tails did not improve
uniformly; the receipts preserve that counter-evidence.

At frozen code release `cbaacc3765f8dbca2ff04247cb24fd773751a0f9`, validation
recorded 1958 primary backend passes; 1924 clean passes plus 34 expected artifact
skips; 96 frontend files/844 unit tests; 542 browser passes/four inherited skips;
16 HTTP/SSE, 32 Agent shell and 12 durable Agent product cases. TypeScript,
build and contrast passed. Exact-release [Backend CI](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/runs/37085104945)
and [Frontend CI](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/runs/37085104875)
completed successfully. The [canonical receipt](IMPROVEMENT_FINAL_RECEIPT.md)
distinguishes starting-SHA primary tests, accepted-candidate tests and exact-final
verification; these are release observations, not new portfolio-task test runs.

## Tradeoffs and limitations

Capacity characterization justified keeping the default at two workers and an
ordinary recommendation of one to two. In CAPACITY's zero-delay synthetic
workload, throughput at one/eight workers was 17.603/13.923 jobs/s; extra
concurrency raised local costs. Wait-bound trials benefited from more consumers,
but that does not certify Groq quota or all Generator concurrency. See the
[capacity receipt](CAPACITY_001_FINAL_RECEIPT.md) for the full workload matrix.

Workers, sessions, cache and rate limits remain process-local. Local Qdrant also
requires one owning backend process. Distributed serving would need explicit
shared-state, ownership and recovery design. No production SLA, live-provider
quota certification or full accessibility certification is claimed.

The 527.24kB main bundle warning remains. Native zoom is manual/unverified,
Collections/model-test ordinary browser bearer wiring is staged, and Ragas is
optional. Agent evaluation has 21 provider-free structural/operational metrics
and no overall score; it does not certify factual quality. Reload requires server
authority and reconnection. Generic Deep is not a hidden multi-objective planner.

## What I learned

I learned to define ownership before adding asynchronous behavior. A browser
reference, a durable job and an in-flight provider call have different lifetimes;
giving each an explicit authority made cancellation and recovery easier to reason
about. I chose conservative interruption semantics because uncertainty about an
external effect is more useful than a misleading success or replay guarantee.

I measured stages before choosing an optimization. Removing repeated validation
and idle poll delay had specific evidence behind them, while larger worker
defaults and broad caching did not. A lower percentile in one synthetic workload
is insufficient justification for a production policy.

I also learned to separate quality, performance and release evidence. Native
metrics, judge results, benchmark timing and green CI answer different questions.
Test counts become useful when linked to contracts and exact code populations.
The frontend began as an AI Studio-generated application; my engineering focus
was the integrated Research behavior, typed contracts, state boundaries and
verification recorded in this repository, rather than a claim of hand-authoring
every initial UI element.

For a presentation, use the [seven-minute demo](DEMO_SCRIPT.md). For application
materials, use [portfolio bullets](PORTFOLIO_BULLETS.md); for technical discussion,
use the [interview guide](INTERVIEW_GUIDE.md).
