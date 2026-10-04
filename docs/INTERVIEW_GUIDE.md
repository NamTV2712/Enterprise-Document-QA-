# FilingScope — Interview Guide

Public project name: **FilingScope**. Repository: **Enterprise Document QA**.

Answers describe the implemented project and its frozen code release
`cbaacc3765f8dbca2ff04247cb24fd773751a0f9`. Use the
[case study](PORTFOLIO_CASE_STUDY.md) for the narrative and the linked receipts
for measurement provenance. Adapt ownership statements to your actual work.

## RAG

### 1. Why hybrid retrieval?

Financial filings contain exact company names, fiscal periods and accounting
terms alongside paraphrased explanations. BM25 preserves lexical matches while
Qdrant retrieves semantic matches. Combining candidate rankings reduces reliance
on either signal alone; it does not guarantee that the correct passage is found.
See [retrieval architecture](../ARCHITECTURE.md).

### 2. Why Reciprocal Rank Fusion?

BM25 and dense similarity scores have different scales. RRF combines their rank
positions without treating those raw scores as comparable probabilities. The
project preserves separate lexical, dense, fusion and reranker fields so an
inspection can identify the stage where evidence was lost.

### 3. Why add a cross-encoder reranker?

Candidate retrieval must search broadly; the generation context must stay
bounded. A cross-encoder scores the question and each candidate together to
improve the final ordering. Its logits, including negative values, are ranking
signals, not confidence or factual correctness. It also adds latency, so the
project measures retrieval and reranking separately.

### 4. How do citations stay traceable?

Selected chunks retain canonical document/chunk identities through context,
generation and source navigation. The frontend lets a reader inspect the cited
evidence and its representation. Acquisition of a full filing is separate from
indexing; an unavailable representation must remain visible. Traceability helps
audit an answer but does not prove that every generated claim is supported.
See [source contracts](frontend/FRONTEND_CONTRACT.md).

### 5. What happens with insufficient context?

Generation instructions require an honest insufficient-context response rather
than filling gaps from general knowledge. Context selection remains bounded,
and numeric claims need the relevant period and units. Evaluation distinguishes
retrieval coverage from answer correctness; prompt instructions alone are not
an accuracy guarantee. See [generation design](ENGINEERING_REFERENCE.md#generation-design).

## Agent

### 6. Why add an Agent when Chat already works?

Quick handles a conversational RAG turn. Deep admits a separately authorized,
bounded research execution that may inspect retrieval, read evidence and invoke
RAG. Its work can outlive a browser request and needs explicit progress,
cancellation and persisted results. A simple question can still use Quick.

### 7. Why a closed tool registry?

The registry exposes only `search_documents`, `inspect_retrieval`,
`read_document` and `ask_rag`. Typed arguments, capability policy and provider
permission are checked before adapters reuse existing services. Document text
cannot register tools or select arbitrary shell, HTTP, SQL or filesystem actions.
See [registry](../src/agent/registry.py).

### 8. Why durable runs?

DATA-004 owns the run state, revision, ordered events, result and evaluation.
The browser stores references, so reload or navigation does not create a second
execution authority. After a restart, eligible queued work can be claimed;
uncertain previously claimed work is interrupted rather than blindly replayed.
See [state and persistence](../ARCHITECTURE.md#state-and-persistence).

### 9. How does cancellation work?

The client requests cancellation against the current revision and reconciles a
conflict with server state. An active run can enter `cancelling` before it reaches
a safe boundary and becomes `cancelled`. The project does not claim that a
cancellation request kills an in-flight thread or undoes an external effect.

### 10. Why keep hidden reasoning out of the UI?

The UI displays bounded execution facts: state, tool activity, result, evidence
and evaluation. Raw hidden reasoning and provider response bodies are unnecessary
for that audit trail and would introduce leakage and misleading explanations.
Safe activity records explain what happened without claiming access to a model's
private reasoning.

## Backend and system design

### 11. Why SQLite?

It fits a local, single-process workspace with durable transactions and a small
operational footprint. SQLite v7 uses WAL, NORMAL synchronous mode and a 5000ms
busy timeout. Revision checks and short transactions enforce authority; provider
work stays outside transactions. This choice does not establish distributed
scalability. See [DB-SCALE receipt](DB_SCALE_001_FINAL_RECEIPT.md).

### 12. Why two workers by default?

The WorkerSupervisor has two fixed consumers rather than a thread for each run.
Controlled capacity tests showed benefits for some waiting workloads and limits
under database/provider contention. Ordinary use remains 1–2 workers; the
configurable range of 1–16 is not a recommendation to maximize concurrency.
See [capacity receipt](CAPACITY_001_FINAL_RECEIPT.md).

### 13. How are duplicate claims prevented?

The canonical SQLite writer uses `BEGIN IMMEDIATE` to atomically select and
claim the oldest eligible run. Revision comparison protects subsequent writes.
Idempotent admission and atomic claims protect local state, but neither promises
exactly-once external provider effects across crashes.

### 14. Why not Redis or Celery now?

The documented deployment is one process, and SQLite plus fixed workers meets
that bounded scope with fewer moving parts. Adding a distributed queue would
require evidence of a deployment need and a new ownership/recovery contract.
The project has not measured a Redis/Celery alternative, so I would not claim
SQLite is universally faster or cheaper.

### 15. What would have to change for distributed deployment?

First define cross-process claims, leases, recovery and idempotency for external
effects, then choose shared durable storage and worker coordination. Qdrant local
storage also has a file lock; multi-process serving needs server/cloud mode.
Those are future design requirements, not existing project capabilities.

## Evaluation

### 16. How is RAG quality evaluated?

The project separates retrieval evidence, deterministic answer checks and model
judging. The official reported benchmark is the documented clean priority ≤2,
N=30 run; later experiments retain their own provenance. Generation checkpoints
bind configuration and rendered context, and changed bindings require a fresh
checkpoint. Quota-skipped or mixed checkpoints cannot become final metrics.
See [evaluation results](ENGINEERING_REFERENCE.md#evaluation-results) and
[frozen release receipt](IMPROVEMENT_FINAL_RECEIPT.md).
The [public native adaptation](RAG_QUALITY_BENCHMARK.md) recomputes six metrics
offline from all 30 frozen cases. Judge estimates are reused; historical packing
uses required-keyword donors. It is not fully label-blind or current-runtime accuracy.

### 17. How is Agent behavior evaluated?

Native evaluation reads a terminal DATA-004 snapshot and produces 21 structural
metrics without rerunning a model. It checks execution and evidence properties;
it does not collapse them into an overall factual-accuracy score. Provider-free
tests separately verify lifecycle, budgets, access policy and adversarial inputs.
See [Agent evaluation implementation](../src/agent/evaluation.py) and the
[cross-layer receipt](TEST_005_AGENT_FINAL_RECEIPT.md).

## Performance

### 18. What bottleneck did you reproduce?

Two concrete findings were repeated SQLite initialization/locking under local
HTTP contention and idle workers waiting for the next poll. I measured those
stages separately rather than attributing all latency to the LLM. Content-free
telemetry retains timing, counts and status without prompt or answer content.
See [observability receipt](OBS_001_FINAL_RECEIPT.md).

### 19. What did DB-SCALE change?

Initialization was guarded for reuse and read snapshots were separated from the
writer lifecycle. In the receipt's local real-HTTP workload with synthetic
dependencies, read50 client p95 changed from 1967.995 to 982.813ms. These are
median trial statistics for that campaign; mixed-workload admission contention
remained. This is not an internet production latency claim.

### 20. Why reject eight workers as the default?

More workers did not help every workload. At zero artificial provider delay,
the capacity receipt measured 17.603 jobs/s with one worker versus 13.923 with
eight. Waiting workloads benefited more, but real Groq quota was not tested.
The ordinary recommendation stayed 1–2; worker count is a tradeoff, not a
universal throughput multiplier.

### 21. What improved the idle queue delay?

A payload-free, coalesced wake hint follows durable admission; SQLite still owns
the job. Polling remains the recovery fallback. In the controlled idle-confirmed
campaign with two workers and 500ms polling, queue p95 changed from 502.753 to
9.340ms. The setup intentionally exposed remaining-poll delay; it is not a
claim about saturated queues. See [worker receipt](WORKER_002_FINAL_RECEIPT.md).

## Security and product boundaries

### 22. Why is the browser bearer memory-only?

Persisting it in Library records, browser storage or exports would extend its
lifetime and expose a capability to unrelated readers. Reload clears the bearer;
reconnection is required to read a saved run reference. Browser-exposed `VITE_*`
configuration contains only public settings, never provider secrets.

### 23. Why keep Quick and Deep separate execution paths?

The user must know whether they are asking one RAG question or admitting an
Agent run. The generic Deep composer sends its visible goal and locale; it does
not silently inherit Quick history/filters or generate hidden objectives.
Research deeper prepares a draft and requires another submit. See
[unified Research receipt](UX_AGENT_001_FINAL_RECEIPT.md).

### 24. How do provider calls and untrusted evidence stay bounded?

Evidence is data, not policy. Tool arguments and availability are validated,
and external execution requires explicit permission. Agent structured decisions
use one HTTP attempt, no repair/fallback loop and a 60s deadline; normal RAG has
its separately documented bounded fallback behavior. Sanitized errors and
content-free telemetry avoid exposing credentials or raw provider bodies.
See [credential/provider receipt](CRED_001_FINAL_RECEIPT.md).

## Closing answer: what remains unverified?

Single-process workers, no production SLA or real provider quota certification,
the approximately 527.24 kB bundle warning, manual/unverified native zoom,
staged Collections/model-test browser bearer wiring and optional Ragas remain
visible. The frontend began as a Google AI Studio generated application; describe
your integration, fixes and validation contribution precisely rather than claiming
every original component. The [published silent demo](DEMO_SCRIPT.md) shows the current product with
its synthetic fixture and validation scope disclosed.
