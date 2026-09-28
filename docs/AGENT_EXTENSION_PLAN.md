# Optional Agent Extension

The required product roadmap ended at UI-013. This plan is a separate optional
extension. It does not change the status of any completed task.

## Sequence

| Task | Scope | Status |
|---|---|---|
| AGENT-001 | Typed closed-world tools and bounded existing-UI sweep | Complete |
| AGENT-002 | Bounded single-agent tool-selection and execution loop | Complete |
| AGENT-003 | Durable runs, operational events, cancellation | Complete |
| AGENT-004 | Multi-step evidence gathering over current services | Complete |
| AGENT-005 | Prompt-injection and tool-policy hardening | Complete |
| AGENT-006 | Agent evaluation protocol | In progress |
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

## AGENT-004 contract and checkpoint

Research is an optional `agent_research_v1` policy inside the existing
`AgentOrchestrator.run` decision loop. There is no second execution loop,
planner service, new tool, route or database. The caller supplies 1–6 typed,
bounded objectives in the optional `/agent/runs` `research` field. Each has a
stable safe ID, a question of at most 120 characters and an optional canonical
ticker scope. These are caller intent, not source evidence; evidence is
attributed only after a canonical document/chunk ID is observed. At most five
distinct ticker scopes are accepted. Objectives cannot be added from retrieved
text or silently generated from model prose. Generic runs omit `research` and
keep AGENT-002 behavior.

Each research tool decision names exactly one frozen objective. The decision
model sees a separate bounded research view with objective coverage, gaps,
source identities and prior action outcomes; AGENT-002 still validates every
structured decision, tool input, provider gate and budget. Research policy
checks the objective and optional ticker/document scope before invocation.
Exact canonical calls are rejected through AGENT-002's duplicate rule, and
research permits at most two search attempts per objective, subject to the
frozen global search, step and tool ceilings. Query refinement is a new
validated model decision, never an automatic recursive search. Search can
discover indexed passages, Retrieval can inspect ranked candidates, Document
can inspect canonical indexed previews, and RAG can provide a grounded
generated answer when separately authorized. Only its cited source records,
never generated prose, enter the research ledger.

The ledger retains at most six distinct `(document_id, chunk_id)` source
identities in first-seen order, within AGENT-002's observation capacity.
Repeated canonical evidence keeps one entry and unions objective associations.
Document ID prefixes yield canonical ticker attribution when valid; an
objective with a ticker scope receives credit only for matching documents.
Different documents/chunks remain distinct even with similar excerpts.
Ledger entries store IDs, ticker, objective IDs, first tool and step, not raw
source text, score-derived confidence or hidden reasoning. In-memory action
history holds at most the AGENT-002 ten-tool ceiling and safe bounded query
intent; durable results store only content-free source identity metadata.

Coverage is an explicit deterministic threshold of 1–2 distinct ledger
entries per objective (default 1): `none`, `some`, or `sufficient` means only
that threshold, not factual completeness. Up to six typed gaps use
`no_evidence`, `below_threshold`, `search_exhausted` or `ledger_full`.
The model can choose a follow-up within existing budgets. A final decision
must list exactly the unresolved objective IDs and cite retained current-run
ledger evidence for every sufficient objective. AGENT-002's canonical-ID and
`[Source N]` validation still applies. Partial completion uses the existing
`completed` Agent status plus structured gaps and an explicit unresolved
footer; no new job state is invented. With no source evidence, the final
answer becomes a deterministic no-evidence statement. Research answers are
limited to 1200 UTF-8 bytes before that bounded footer, with at most 12
structured references, so the existing 8192-byte durable-result cap holds.
This checks identity and policy coverage, not semantic claim support.

AGENT-003 freezes the version, objectives and research bounds in its existing
fingerprinted plan and stores the bounded summary in its existing result JSON.
An optional objective ID is included in safe keyed decision events; older
AGENT-003 events and generic plans remain readable. Cancellation retains the
ledger collected before acknowledgement; restart still interrupts without
replay. Mid-run ledger entries are not separately checkpointed, though safe
decision events retain bounded evidence references. No SQLite migration is
needed; schema version remains v7. The six routes and 89-route inventory
remain unchanged. The production decision-model adapter is still absent, so
normal research runs report `decision_provider_unavailable` without tool use.

- AGENT-004-A complete: research policy/version, objectives, ledger, gaps and bounds defined.
- AGENT-004-B complete: typed state and deterministic canonical evidence ledger tested.
- AGENT-004-C complete: gap context, search attempts, duplicate prevention and comparison scopes tested.
- AGENT-004-D complete: final readiness, current-run references, partial disclosure and injection boundaries tested.
- AGENT-004-E complete: frozen plan/result, safe objective events, cancellation and restart tested.
- AGENT-004-F complete: Agent/domain/full-backend, import/route, clean-checkout and artifact gates recorded in `PROJECT_STATE.md`.

**Exact next optional task: AGENT-005 — prompt-injection and tool-policy
hardening.** It owns the broader adversarial campaign. Stop before AGENT-005;
multi-agent behavior, Agent UI and Ragas remain future work.

## AGENT-005 threat model and security checkpoint

AGENT-005 tests the existing single-Agent architecture with deterministic
scripted decisions and synthetic hostile data. It does not claim resistance
to a live decision-model provider, because no production structured adapter
exists. The primary invariant is that untrusted data cannot become
control-plane authority.

The trusted control plane consists of the four-tool registry and metadata,
server-owned tool bindings, API-001 access checks, frozen run policy and
limits, independent provider permissions, DATA-004 lifecycle/revisions/event
sequence, caller-validated research objectives, and canonical structured
evidence identities. Untrusted inputs include the user goal and objective
text, model decisions and arguments, filing snippets and metadata, retrieval
and document previews, RAG-generated prose, final answers, and raw
tool/provider exception text. The boundary chain is API input validation →
frozen plan; decision response → strict parser → exact registry/policy/budget
and input checks → tool invocation; typed tool result → bounded untrusted
observation; observation → canonical research ledger; operational facts →
bounded durable events/result. Source prose has no path back to the trusted
registry, policy, access grant, lifecycle, or revision authority.

The attack matrix records the expected enforcement layer and measurable
outcome. `0` calls means no underlying tool service call; `≤budget` means
only explicitly validated calls within the frozen bound. `None` in the last
column means no attacker-chosen durable state/event or synthetic secret leak.

| Attack class | Entry point | Enforcement | Service calls | Durable effect / leak |
|---|---|---|---|---|
| Direct policy/tool injection | User goal | Frozen policy, strict decision parser | 0 without validated tool decision | None |
| Indirect document instructions | Search/Document/Retrieval text | Untrusted observation projection | 0 from text alone | None |
| Nested/encoded instructions | JSON, Markdown, XML, YAML, HTML or quoted text | No prose-to-decision parser | 0 from text alone | None |
| Unknown/near-match tool | Model decision name | Exact registry lookup | 0 | Typed rejection only |
| Malicious search arguments | Model arguments | Strict Search input | 0 if invalid | Typed rejection only |
| Malicious Retrieval arguments | Model arguments | Strict Retrieval input | 0 if invalid | Typed rejection only |
| Path-shaped Document ID | Model arguments | Canonical ID schema and catalog lookup | 0 if invalid | Typed rejection only |
| RAG provider/config override | Model arguments | Strict RAG input and provider gate | 0 if invalid/denied | Typed rejection only |
| Provider escalation | Goal, observation or decision | Independent provider permissions | 0 when denied | None |
| Budget escalation | Decision extras or text | Frozen limits and pre-call gates | ≤budget | Bounded events only |
| Objective injection | Source/RAG/error prose | Caller-frozen research config | 0 from text alone | No new objective |
| Forged evidence/Source label | Source or RAG prose | Structured projection and final reference validation | ≤budget | No forged ID |
| Cross-run citation | Final decision | Current-run observation and ledger | ≤budget | Rejected final |
| RAG answer poisoning | Generated prose | Source-record-only projection | ≤budget | No prose evidence |
| Error-string injection | Tool/provider exception | Typed content-free error mapping | ≤budget | No raw error/leak |
| Event/revision forgery | Source or model text | DATA-004 keyed event/revision authority | ≤budget | No forged event |
| Lifecycle/cancel forgery | API extras or source text | Strict DTO and revisioned cancellation | 0 from text alone | No transition |
| API access bypass | Agent routes | API-001 bearer, Host, Origin, loopback, execution gate | 0 denied | No private read/write |
| URL/secret in cursor or ID | Query/header/source text | Header-only bearer, opaque IDs, numeric sequence | 0 denied | No secret in URL/ID |
| Unicode/oversize/loop amplification | Goal, decision, tool output | Typed size ceilings, projection and frozen loop | ≤budget | Bounded result/events |

Candidate weaknesses to reproduce before any production edit: the registry
holds an internal mutable mapping despite frozen tool descriptors; some
frozen Pydantic views contain mutable nested dicts; error and event payloads
need adversarial round-trip checks. A candidate is not a defect until a
reachable untrusted path changes authority or leaks a protected value.

AGENT-005 found one reproducible P2 evidence-integrity defect. A typed tool
result could carry individually canonical but conflicting `document_id` and
`chunk_id` values. The projection admitted that pair, allowing the research
ledger to attribute a chunk from another ticker or filing to the stated
document. Two deterministic tests failed before the fix: cross-ticker and
same-ticker/different-accession pairs. The projection now checks the
recognizable ticker prefix and, for standard SEC accession IDs, the filing
accession before constructing an `EvidenceRecord`. A conflict produces the
existing typed `invalid_observation` outcome; source text, budget and tool
authority are unchanged. The check remains compatible with synthetic or
legacy IDs that do not encode an accession; it cannot prove arbitrary source
metadata truthful. No other reachable P0–P2 defect was reproduced.

The hermetic AGENT-005 adversarial module covers all matrix rows with scripted
decisions and hostile synthetic snippets, including exact tool names, strict
arguments, the two independent provider gates, copied policy/metadata views,
objective ownership, current-run citations, RAG prose, safe errors, durable
events/cancellation, API-001 access, synthetic secrets, denied network/file/
shell capability attempts, Unicode/oversize handling and frozen loop limits.
The production decision adapter remains absent, so this is a structural
boundary result, not a live-model prompt-injection guarantee. The registry's
internal mapping and frozen models' nested dictionaries remain application
owned; the decision model receives defensive metadata/policy projections,
and attempted mutation of those views did not affect execution. No registry
API accepts model or filing text as registration input. The API, migrations,
dependencies, frontend, and four-tool set are unchanged.

- AGENT-005-A complete: threat model and attack matrix recorded before production changes.
- AGENT-005-B complete: conflicting structured evidence pair reproduced and rejected at projection.
- AGENT-005-C complete: deterministic hostile-text, provider, policy, budget, evidence, durability, access and capability checks.
- AGENT-005-D complete: regression and clean-checkout receipts are recorded in `PROJECT_STATE.md`.

**Exact next optional task: AGENT-006 — Agent Evaluation Protocol.** It should
measure separate completion, tool use, evidence, citation, gap, budget and
policy outcomes. Do not start AGENT-006, UI-014 or multi-agent behavior here.

## AGENT-006 native evaluation contract (design checkpoint)

`native-agent-evaluation` v1 evaluates one terminal, already recorded Agent
run from its frozen plan, bounded durable result and ordered safe events. It
never reexecutes the Agent, invokes a tool or provider, or reads filing text.
It is separate from EVAL-001's six `native-evaluation` RAG metrics and has no
overall Agent score. Every metric has semantic version 1. A semantic change
requires a version bump. Ratios use exact integer numerators/denominators and
four-decimal display values; denominator zero is `not_applicable`, never a
computed zero. `unavailable` means the durable snapshot lacks a prerequisite.
Real zero and false are `computed` values. Direction `neutral` means neither
larger nor smaller is inherently better.

The authoritative v1 metric inventory is below. `T` is a tool-decision event;
`A` is a tool event admitted to execution (`observed` or `failed`); `F` is
an admitted tool event with `failed` outcome. Counts from events describe
**recorded** work, a lower bound if a run was interrupted before an event
commit. The terminal result supplies exact total counters when present.
Metric IDs use the `native_agent.` prefix, all have version `1`, and source
fields are named in the calculation column.

| Metric suffix | Type / direction | Applies and exact calculation/source | Means; does not mean |
|---|---|---|---|
| `execution_completed` | boolean / higher | Every terminal run: `run.state == succeeded` with `result.agent_status == completed` | Execution ended with an answer; not factual correctness |
| `recorded_tool_decision_count` | count / neutral | All runs: count `agent_decision` events with `decision_kind=tool` | Recorded tool choices; not every uncommitted attempted action |
| `admitted_tool_call_count` | count / neutral | All runs: count `A` | Recorded calls admitted to execution; not optimality |
| `tool_admission_fraction` | ratio / higher | If `T>0`: `A/T` | Share of recorded tool choices admitted; not tool service success |
| `invalid_tool_attempt_count` | count / lower | Rejected tool events with `unknown_tool` or `invalid_arguments` | Structurally invalid choices; not malicious intent |
| `policy_denial_attempt_count` | count / lower | Rejected tool policy/research events plus a `decision_provider_required` terminal denial | Recorded denials; not a security attack score |
| `duplicate_rejection_count` | count / lower | Rejected tool events with `duplicate_tool_call` | Exact repeated work stopped by the existing loop; not all unnecessary work |
| `tool_failure_fraction` | ratio / lower | If `A>0`: `F/A` | Admitted calls ending with typed tool/projection failure; not invalid selection |
| `tool_unavailable_count` | count / neutral | Admitted failed tool events with `tool_unavailable` | Recorded tool availability failures; not model quality |
| `invalid_final_attempt_count` | count / lower | Rejected `final` decision events | Recorded final-contract rejections, including unseen/ambiguous citations; not claim truth |
| `step_budget_utilization` | ratio / neutral | Terminal result present: `result.step_count / frozen.limits.max_steps` | Frozen step capacity used; not quality or efficiency |
| `tool_budget_utilization` | ratio / neutral | Terminal result and positive limit: `result.tool_call_count / frozen.limits.max_tool_calls` | Frozen call capacity used; not quality or efficiency |
| `budget_exhausted` | boolean / neutral | Terminal result present: `result.agent_status == budget_exhausted` | Actual terminal budget outcome; not inferred from utilization |
| `decision_provider_unavailable` | boolean / neutral | Terminal result present: `result.failure.code == decision_provider_unavailable` | Decision-provider availability outcome; not Agent correctness |
| `evidence_identity_validity` | ratio / higher | Research ledger with entries: structurally valid canonical doc/chunk pairs / ledger entries | Identity consistency under AGENT-005 rules; not evidence relevance or claim support |
| `final_reference_validity` | ratio / higher | Completed final with refs and complete current-run ID metadata: references present in this run / final refs | Structured current-run identity; not source-label resolution or semantic citation support |
| `objective_coverage` | ratio / higher | Research result: objectives marked `sufficient` under frozen `agent_research_v1` threshold / configured objectives | Bounded policy sufficiency; not factual completeness |
| `unresolved_gap_fraction` | ratio / lower | Research result: typed unresolved gaps / configured objectives | Bounded unresolved objectives; not answer incorrectness |
| `research_evidence_count` | count / neutral | Research result: canonical ledger entries | Retained entries; not relevance or diversity quality |
| `distinct_document_count` | count / neutral | Research result: distinct non-null document IDs in ledger | Source-document count; not quality |
| `distinct_chunk_count` | count / neutral | Research result: distinct chunk IDs in ledger | Source-chunk count; not quality |

The report separately retains the terminal job state, Agent status/failure
code, per-tool recorded counts, exact typed gap-code counts and safe
provenance hashes. Non-research runs mark research-only metrics
`not_applicable`. A missing terminal result makes result-dependent metrics
`unavailable`; recorded event counts remain computable. Generic durable runs
do not retain complete source pairs or Source-label mappings, so those checks
are `unavailable` when the bounded event projection cannot prove them.
Invalid event order, impossible counters, conflicting frozen plan/result,
unseen final references when observation IDs are complete, malformed research
coverage, and AGENT-005 ticker/accession mismatches are corruption errors,
not low scores. The report uses the repository's finite canonical JSON and
SHA-256 digest; it does not persist or publish a report. No API route or
SQLite migration is planned.

- AGENT-006-A in progress: metric inventory, applicability, provenance and corruption semantics defined before implementation.
