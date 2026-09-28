# Optional Agent Extension

The required product roadmap ended at UI-013. This plan is a separate optional
extension. It does not change the status of any completed task.

## Sequence

| Task | Scope | Status |
|---|---|---|
| AGENT-001 | Typed closed-world tools and bounded existing-UI sweep | Complete |
| AGENT-002 | Bounded single-agent tool-selection and execution loop | Next |
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

AGENT-002 may add a bounded single-agent orchestration loop with explicit
step/tool/search limits, a model tool-choice schema, safe observation
accumulation and a final answer. It must retain the current authority boundary
and must not implicitly enable provider calls or persist hidden reasoning.
Durability, Agent UI, multi-agent behavior and Agent evaluation are separate
later decisions.
