# Optional Agent Extension

The required product roadmap ended at UI-013. This plan is a separate optional
extension. It does not change the status of any completed task.

## Sequence

| Task | Scope | Status |
|---|---|---|
| AGENT-001 | Typed closed-world tools and bounded existing-UI sweep | Complete |
| AGENT-002 | Bounded single-agent tool-selection and execution loop | Complete |
| AGENT-003 | Durable runs, operational events, cancellation | Future |
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

**Exact next optional task: AGENT-003 — durable Agent runs, events and
cancellation.** It owns DATA-004 integration, persisted safe trace, lifecycle,
restart/interruption semantics, bounded event stream and API routes. AGENT-002
does not begin any of those concerns.
