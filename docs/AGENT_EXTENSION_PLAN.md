# Optional Agent Extension

The required product roadmap ended at UI-013. This plan is a separate optional
extension. It does not change the status of any completed task.

## Sequence

| Task | Scope | Status |
|---|---|---|
| AGENT-001 | Typed closed-world tools and bounded existing-UI sweep | Complete |
| AGENT-002 | Bounded single-agent tool-selection and execution loop | Complete |
| AGENT-003 | Durable runs, operational events, cancellation | Complete |
| AGENT-004 | Multi-step evidence gathering over current services | Future |
| AGENT-005 | Prompt-injection and tool-policy hardening | Future |
| AGENT-006 | Agent evaluation protocol | Future |
| UI-014 | Agent workspace and safe operational trace | Future |
| TEST-005 | Cross-layer and adversarial final validation | Future |

## AGENT-001 authority map

| Tool | Current owner | Access and effects | Provider |
|---|---|---|---|
| `search_documents` | `DiscoveryService.search`; BM25 index and bounded in-process snapshots | Public corpus; ephemeral snapshot only | None |
| `inspect_retrieval` | API-005 shared inspection function and `HybridRetriever.inspect` | Public corpus; read-only | Local embedding/reranker inference, no external generator |
| `read_document` | Startup catalog and canonical document-to-chunk index | Public corpus; read-only bounded previews | None |
| `ask_rag` | Shared query service and `RAGPipeline.query` | Public corpus; provider/cache effects | Configured generator; explicit policy required |

The optional package is `src/agent/`. `src.api.app.create_agent_tool_registry()`
binds application-owned dependencies without an internal HTTP request. The
registry has four ordered names, strict input schemas, typed output models,
explicit access/effect/provider metadata, and fail-closed lookup. Its default
policy has no allowed tools and rejects provider execution. The caller supplies
an allowlist and must separately enable provider execution. No model-produced
string can import a module, create a callable, change policy, or register a tool.
No planner, loop, durable Agent job, new API route, or Agent UI is part of this
task. DATA-004 remains unchanged.

All filing snippets, document previews, retrieval candidates and source text
are returned as `untrusted_data`. They are never parsed as instructions or tool
arguments. Agent observations and errors do not contain bearer tokens, API
keys or raw provider exceptions. The document tool accepts only a canonical
document ID and exposes bounded indexed previews. It does not claim a full
source representation or page location. Search deliberately uses the existing
in-process snapshot service, so its `search_id` has the same API-004 meaning;
the Agent does not persist a separate search result.

## Checkpoint

- AGENT-001-A complete: Search, Retrieval, Document, RAG, provider and DATA-004 boundaries mapped.
- AGENT-001-B complete: Strict inputs, typed outputs, registry, policy and error categories tested.
- AGENT-001-C complete: Search, Retrieval and Document adapters preserve canonical IDs and score meanings.
- AGENT-001-D complete: RAG provider gate, deterministic fake generation and hostile evidence tested.
- AGENT-001-E complete: Fourteen current routes inspected at 1440 and 390 px in dark EN/VI, eight dense routes also at 1024 px. One phone composer defect repaired.
- AGENT-001-F complete: Backend 1407 passed/188 warnings, route inventory 83; frontend 90 files/792 passed, TypeScript/build passed; bounded Chromium/Firefox sweep 32/32 and focused populated responsive gate 4/4. Intended files committed separately from generated artifacts.

## AGENT-002 contract and checkpoint

`AgentOrchestrator.run(goal, context, cancel_event=...)` is a request-local
single-Agent state machine over the existing four-tool registry. Its one
`AgentDecisionModel` returns a structured `tool` or `final` decision. The strict
discriminated parser rejects prose, unknown kinds, extra fields, nested
argument blobs, unsafe values and malformed evidence references. One validated
decision counts as one step. An executed tool counts once against the total
and its per-tool ceiling; rejected actions and final decisions do not consume
tool calls. A malformed model output increments the decision-call count but
not the validated-step count. A second call with the same canonical tool name
and validated arguments is rejected; there is no tool-result cache.

Default bounds (schema ceilings in parentheses): 8 steps (20), 5 total tool
calls (10), `search_documents` 2, `inspect_retrieval` 2,
`read_document` 3, `ask_rag` 1 (each at most 10), 5 observations (10), 8
evidence records per observation (20), 160 excerpt characters (500), 4096
serialized bytes per observation (32768), and 16384 serialized observation
bytes per run (65536). Budget checks for tool count, per-tool count and
observation count occur before service execution. Projection deterministically
removes excerpts and then whole records when needed; it never cuts canonical
IDs or changes score field names/values. A tool already executed when its
minimum observation cannot fit is counted and the run ends with
`budget_exhausted/observation_bytes`.

The default research policy requires at least one observation before a final
answer. An explicit generic policy can allow a zero-tool final. The decision
provider permission belongs to `AgentRunPolicy`; the independent `ask_rag`
provider permission belongs to `ToolPolicy`. Neither permission grants the
other. The model receives distinct `system_policy`, `user_goal`, truthful tool
metadata/schemas and bounded observations labeled `untrusted_data`. This is a
structured request contract, not a raw prompt or chain-of-thought protocol.
The in-memory trace contains only decision index, selected tool, argument
*names*, outcome, canonical evidence references and content-free failure
codes; it contains no hidden reasoning or raw provider body.

Final evidence references must exactly match IDs retained in this run's
observations. `[Source N]` labels must resolve to one unambiguous observed
source and a cited document/chunk ID; canonical IDs written in the answer must
also appear in its structured references. Duplicate structured references
are rejected. This validates identity, not claim support. Tool output with
malformed IDs, non-finite scores or unsafe metadata fails with a typed
`invalid_observation` result. Results distinguish completed, invalid decision,
policy denial, budget exhaustion, unavailable dependency, failure and local
cancellation. Cancellation is checked between calls, not during an in-flight
provider call.

The existing generator does not provide a guaranteed structured Agent
decision response. AGENT-002 therefore defines the provider-independent
`AgentDecisionModel` protocol and tests it with a scripted fake. A real
provider adapter is deferred until a strict structured completion contract
can be supplied; no free-form/Markdown parsing or live quota use was added.
No Agent route, UI, durable job, extra tool, database change, dependency,
multi-agent role or Ragas integration is in this stage.

- AGENT-002-A complete: contract, model strategy, state, bounds and two independent provider gates defined.
- AGENT-002-B complete: strict decisions and typed goal, state, result and operational trace.
- AGENT-002-C complete: bounded loop, registry invocation, duplicate detection and scripted-model tests.
- AGENT-002-D complete: bounded evidence projection, citation validation, injection isolation and typed failures.
- AGENT-002-E complete: real adapter explicitly deferred; AGENT-001 tests pass.
- AGENT-002-F complete: full backend, import/route, clean-checkout and artifact gates recorded in `PROJECT_STATE.md`.

## AGENT-003 contract and checkpoint

The only durable authority is the existing DATA-004 `SQLiteJobRepository` in
the private local workspace. Additive, checksum-tracked migration v7 widens the
`jobs.namespace` constraint to `agent` and adds keyed bounded Agent decision
summaries to the existing `job_events` sequence. It transactionally rebuilds
the constrained table and preserves existing Pipeline, Evaluation, model-test,
step and event rows. No second database, jobs table, resume scheduler or
state-machine framework exists. An external `agent_<opaque>` run ID maps to an
internal DATA-004 `job_<opaque>` identity; request IDs and search IDs remain
separate.

Creation freezes protocol v1, goal, locale, ordered tool allowlist, both
independent provider permissions, final-evidence and duplicate-call policy,
all AGENT-002 limits, and a safe server-owned decision-model identity. A
SHA-256 fingerprint binds the immutable payload. DATA-004 hashes the bounded
Idempotency-Key and rejects conflicting reuse. The sole coarse durable step
is `execute_agent`. Atomic `queued -> running` claim admits one owner; the
worker constructs one `AgentOrchestrator` from the frozen plan and an
execution-time model factory. The default production factory is absent, so a
run finishes `failed` with a bounded `unavailable` Agent result and
`decision_provider_unavailable` code; it never fabricates an answer or calls
a tool. Tests inject a deterministic scripted model. No provider object or
credential is serialized.

AGENT-002's optional trace sink writes one keyed `agent_decision` event per
operational decision. DATA-004 system events (`created`, `state_changed`,
`step_changed`, `cancellation_requested`, `cancelled`, `interrupted`) share the
same monotonic per-run sequence. Decision events are limited to 20, keyed by
decision index, idempotent on identical delivery, and limited to 2048 UTF-8
bytes each. Their strict allowlist contains tool name, argument *names*,
outcome, bounded canonical evidence IDs/count and counters. Source excerpts,
raw model output, hidden chain-of-thought and credentials are excluded. The
terminal Agent result stores answer only on completion, validated evidence
references, counters and typed failure, within 8192 UTF-8 bytes. No full
AGENT-002 observations are persisted. Durable Agent status remains distinct
inside the DATA-004 state: only `completed` maps to `succeeded`; invalid,
unavailable, exhausted and other noncompleted outcomes map to `failed` with
their explicit Agent status/code. A cancellation request maps `running ->
cancelling`; acknowledgement maps `cancelling -> cancelled` and can retain
safe counters. Queued cancellation is immediately terminal. `If-Match`
revision conflicts never overwrite newer state.

Local startup drains every page of DATA-004 active jobs to `interrupted` and
never replays an Agent. A queued run left before claim stays queued; an
idempotent repeat of the same create request can redispatch it. There is no
automatic queued-run scheduler or resume endpoint. A process can die after a
provider/tool effect and before its event or terminal commit. That effect is
ambiguous; no exactly-once external execution guarantee is claimed. Local
cancellation is polled between AGENT-002 calls, not an interrupt of an
in-flight decision/provider call. A finite SSE fetch uses DATA-004 sequence
as `Last-Event-ID`; transport closure has no success meaning. Run detail is
authoritative. No bearer appears in an event URL or cursor.

Six backend routes are owned here: GET/POST `/agent/runs`, GET
`/agent/runs/{run_id}`, GET `/agent/runs/{run_id}/results`, POST
`/agent/runs/{run_id}/cancel`, and GET `/agent/runs/{run_id}/events`. Reads
require API-001 local workspace access. Create and cancel additionally require
execution capability. Creation dispatches once via the existing current-process
background-task pattern; repeated dispatch cannot pass DATA-004's claim.
The frontend remains unchanged. The final product route inventory is 89.

- AGENT-003-A complete: DATA-004 owner, v7 migration, route/access, interruption and event contracts mapped.
- AGENT-003-B complete: frozen run and result models, one DATA-004 namespace, persistence and migration tests.
- AGENT-003-C complete: atomic claim, injected model factory and direct AGENT-002 reuse.
- AGENT-003-D complete: ordered keyed safe events, bounded terminal result and Unicode tests.
- AGENT-003-E complete: revision-safe cancellation, startup recovery and three crash-window tests.
- AGENT-003-F complete: private API, `If-Match`, `Last-Event-ID`, access and route contracts.
- AGENT-003-G complete: Agent/DATA/Pipeline/Evaluation/full-backend, clean-checkout and artifact gates recorded in `PROJECT_STATE.md`.

**Exact next optional task: AGENT-004 — Agentic Research / bounded multi-step
evidence gathering.** It may use these durable runs and four existing tools;
it does not require multi-agent behavior. AGENT-003 does not start that work.
