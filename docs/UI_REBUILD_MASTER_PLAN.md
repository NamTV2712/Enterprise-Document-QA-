# UI Rebuild Master Plan

Status: completed planning specification, persisted by Checkpoint 09. This document does not start implementation. The exact next implementation task is TEST-001.

This saves the completed planning conversation. Audit and screenshot findings below are inherited findings, not a new analysis. The [standalone Appendix A](UI_REFERENCE_GAP_MATRIX.md) and [checkpoint](UI_REBUILD_PLAN_CHECKPOINT.md) are part of the specification.

## 1. Executive Summary

Rebuild a coherent SEC research product faithful to the nine references. Approximately 70% of presentation/composition is expected to be rewritten; this is an engineering estimate, not measured source-line coverage. Preserve reader engines, evidence identity, cancellation, bilingual behavior, conversation variants and storage compatibility.

Introduce routed pages and shared primitives. Add a single-user, local-first SQLite workspace for conversations, collections, annotations, jobs and content-free telemetry. Public deployments keep the new server workspace read-only and retain browser-local saving. Protect private reads as well as writes.

Separate discovery Search from diagnostic Retrieval. Pipeline uses isolated staging and durable records without automatic serving-corpus promotion. Native evaluation remains authoritative; optional isolated Ragas comes later. Defer TruLens, multi-user accounts, sharing, arbitrary model installation/switching and production promotion.

Backend work is an additive product/service layer. Retrieval ranking, generation prompts, chunk identifiers, index semantics and the official benchmark remain unchanged.

## 2. Current Architecture Audit

The completed audit covered major implementation boundaries, not every source line. The previous production-build reference suite passed 15/15 Chromium tests. That historical result does not replace visual review of the rebuild. Preserve the existing dirty tree: 71 tracked modified files plus untracked reconstruction/PDF work.

| Area | Existing evidence | Decision |
| --- | --- | --- |
| Frontend | React 19, Vite, TypeScript, Tailwind 4, Lucide, Bun | Keep stack |
| Navigation | Query-string navigation and large App composition | Router with compatibility adapter |
| Workbench | Shared layout/controller, source/document behavior | Reuse behavior; rebuild composition |
| Conversations | Schema v4, IndexedDB/localStorage fallback, tombstones, writer coordination | Preserve and explicitly migrate |
| Collections | Browser-local evidence and separate favorites | Typed repository |
| Reader | Structured, normalized, PDF.js, revision/hash identity | Preserve engines and binding |
| PDF | Derived representation of official content; no admitted original PDF bytes | Keep generated-page provenance explicit |
| Documents | Catalog pagination, chunks, manifests | Extend filters/facets/statistics |
| Search | Inspection-oriented selected candidates | New discovery contract |
| Retrieval | BM25, dense, lexical, RRF, reranker stages | Add metadata; preserve production behavior |
| Models | System information and settings | Configured/runtime registry |
| Pipeline | Serving snapshot and CLI algorithms | Staged orchestration and durable history |
| Evaluation | Native runners and validated public reports | Separate private execution jobs |
| Analytics | Browser/in-memory measurements | Content-free durable terminal events |
| Backend | Large API app module | Incremental router/service extraction |
| Deployment | Independent frontend/backend; local Qdrant single worker | Preserve boundaries |

Established corrections: decomposed streaming and PDF rendering already exist. Inspection already exposes most stage scores but differs from production structured promotion. Native citation correctness is source-number/index validity, not claim support. The public evaluation artifact directory was absent; no fabricated reports are allowed. Existing fixtures can be sparse or have inconsistent catalog/health totals; parity fixtures must be internally coherent and development-only. PROJECT_HANDOFF.md was absent. These three planning files were unwritten because the earlier run was restricted to planning.

## 3. Screenshot-by-Screenshot Product Specification

All nine images were individually inspected before this checkpoint. Appendix A preserves their full feature-level gaps.

| Reference | Native size | Required composition |
| --- | --- | --- |
| rag-workbench-master-reference-dark.png | 1254 × 856 | Sidebar about 158 px; answer, sources and document simultaneously visible. Cited answer actions, execution stages, composer, numbered source cards, insights and related questions. Reader toolbar, white paper, evidence/content/metadata and annotations. Current narrow composition loses panes. |
| research-ui-reference-dark-v1.png | 1586 × 992 | About 200 px navigation, 620 research, 340 sources, 420 reader; follow-up tiles/composer, taller cards, serif filing text and amber highlights. |
| documents-ui-reference-dark-v1.png | 1586 × 992 | Approximately 70/30 main/detail; search, four filters, four statistics, selectable sortable paginated table. Four detail tabs, metadata grid, representations, white preview and three actions. |
| search-ui-reference-dark-v1.png | 1586 × 992 | Query/filters, ranked highlighted cards; four metrics, facets/recent searches in rail. Rank/score/metadata, research/open/save, grouping and pagination. |
| retrieval-ui-reference-dark-v1.png | 1586 × 992 | Query/company/document/preset, four statistics, ranked chunks, selected row and white excerpt preview rather than whole-document reader; raw diagnostic scores. |
| collections-ui-reference-dark-v1.png | 1586 × 992 | Search/sort/view/create; broad list and approximately half-width details; folder/favorite, description/tags/count/time/actions; contents/notes/activity/settings. Sharing deferred. |
| models-ui-reference-dark-v1.png | 1586 × 992 | Upper routing/benchmark areas; lower role tabs, filters and actual-model table. Unsupported toggles become read-only facts; compatible benchmarks only. |
| pipeline-ui-reference-dark-v1.png | 1586 × 992 | Four statistics, six nodes, run table and selected-run step timeline/alerts. Empty history shows the definition, not successful sample runs. |
| evaluation-ui-reference-dark-v1.png | 1586 × 992 | Five metrics, run table, report rail, trends and failures. Real denominators/semantics; one run yields one point. |

Shared language: navy surfaces, blue actions, cyan selection, subtle borders, compact radii, outlined icons and dense metadata. References do not define empty/error/hover/focus states. Add non-shifting hover, visible 2 px focus, non-color selection cues, disabled reasons, stable skeletons, useful empty actions, scoped errors retaining data and stale states retaining revision identity.

## 4. Information Architecture

A = largely backend-ready; B = product/backend extension; C = later bounded capability; D = deferred.

| Destination | Class | Decision |
| --- | --- | --- |
| Chat | A | Existing query/stream |
| Research | B | Persistent organization around existing deep-query behavior |
| Documents | B | Metadata, filters, facets/statistics |
| Search | B | Discovery distinct from inspection |
| Collections | B | Typed persistent assets |
| Retrieval | A | Existing diagnostics, additive metadata |
| Models | B | Configured/runtime registry; bounded local tests |
| Pipeline | B | Staged jobs/history |
| Reranker | A | Same-pool comparison |
| Evaluation | B | Reports plus private execution jobs |
| Analytics | B | Durable content-free aggregates |
| Datasets | B | Corpus/evaluation registry |
| Settings | A | Preferences/system facts plus workspace extensions |
| Logs | C | Local bounded sanitized events |
| API Keys | D | No page; configuration status in Settings |
| Users | D | Hidden; no simulated accounts |

History belongs within Chat, Research and Collections. Architecture/help belongs in Settings/help.

## 5. Shell and Responsive Layout

Group navigation into Workspace, Build, Evaluate and Manage; expose only available capabilities. Do not invent subscriptions or quotas. Display local size only when measured. Top bar: corpus/company scope, command palette, actual readiness/generator, theme/language/settings and Local workspace identity. Commands distinguish navigation, saved records and indexed discovery; typing must not execute providers.

| Width | Composition target |
| --- | --- |
| 1600+ | Full navigation and three content panes |
| 1440 | Navigation 184, answer 520, sources 300, document 420, splitter budget 16 px |
| 1280 | Navigation 160, answer 500, sources 264, document 340, splitter budget 16 px |
| 1254 | Navigation 158, answer 500, sources 250, document 330, splitter budget 16 px |
| 1024 | Compact navigation; answer plus tabbed source/document context |
| 768 | Navigation drawer and context sheet |
| 390 | Single view; full reader with back and focus restoration |

Honor container constraints and readable minimums, support user resizing and collapse context before clipping at short heights or zoom. Panes scroll independently. Composer/toolbars never cover content or focus.

## 6. Design System

| Token | Dark reference value |
| --- | --- |
| Canvas | #06182A |
| Sidebar | #061525 |
| Panel | #081D32 |
| Raised/input | #0A223B |
| Selected | #0B315B |
| Border | #163B5D |
| Primary | #0B8CFF |
| Cyan | #2DB6FF |
| Success | #12D6C5 |
| Warning | #F1C84B |
| Error | #FF5F75 |
| Text | #F3F7FF |
| Secondary | #B8CBE4 |
| Muted | #7894B2 |

Verify contrast and adjust where necessary; define equivalent light-theme semantics. Self-host Inter for UI/answers, serif for filings, monospace for identifiers. Titles 22–24 px, panels 15–16, body 14–16, metadata 12–13. Spacing 4/8/12/16/20/24; panel radius 8, controls 6; mobile targets 44 px; restrained shadows.

Primitives: AppShell, Sidebar, TopBar, PageHeader, Panel, MetricCard, DataTable, DetailRail, SearchField, FilterBar, Select, Tabs, Badge, StatusBadge, IconButton, EmptyState, LoadingSkeleton, SplitPane, EvidenceCard, ScoreBadge, Pagination, ChartCard, Modal/Drawer and CommandPalette. DocumentViewer composes existing engines.

## 7. Frontend Architecture and State

Structure: app (router/providers/bootstrap/legacy adapter), layouts, thin pages, domain features, shared/ui, shared/evidence, api (transport/generated contracts/query keys), styles. Add React Router and TanStack Query. Streaming, request epochs, cancellation and stale-response guards remain outside query-cache ownership. Reducers/context suffice; no Redux. Retain Markdown/PDF.js and use small accessible SVG charts with table alternatives.

Prior planning references: [React Router](https://reactrouter.com/start/declarative/installation), [TanStack Query](https://tanstack.com/query/latest/docs/framework/react/overview). Versions are selected during implementation, not this checkpoint.

Routes: /chat, /chat/:conversationId, /research, /research/:conversationId, /documents, /documents/:documentId, /search, /collections, /collections/:collectionId, /retrieval, /models, /pipeline, /pipeline/runs/:runId, /reranker, /evaluation, /evaluation/runs/:runId, /analytics, /datasets, /settings, /logs.

Preserve legacy query-string view links and evidence hashes through an adapter; configure frontend direct-route rewrites. Conversations share mode chat or research. Chat is direct; Research adds notes/comparison/organization. Mode switches never regenerate answers or mutate evidence. Requests capture mode and submitted scope. Saved history is not persistent backend memory; session expiry is explicit.

## 8. Backend Architecture and Access

Keep bootstrap/lifecycle/middleware/dependencies at the application boundary; routers own validation/transport, services own domain operations. Extract incrementally while retaining existing URLs/wire behavior.

Public is the default posture for the new server workspace: private data unavailable and mutations disabled/read-only. Public catalog, provider-free discovery, system facts and validated published reports remain available. Browser-local saving remains usable.

Local workspace requires explicit configuration, loopback binding, a dedicated bearer token and exact host/origin checks. Never put the token in VITE variables; user-entered credentials stay in memory. Protect private reads and writes. Forwarded headers cannot bypass the boundary. Execution additionally requires capability/resource/provider budgets.

## 9. Page-by-Page Plans

### Chat

- Visual: master reference with answer/source/document composition.
- Reuse: SSE, request/source identities, Markdown, variants, feedback and readers.
- Frontend: routed controller, compact actions/stages/composer.
- Backend/API: existing query plus conversation persistence; unchanged retrieval semantics.
- Persistence: submitted scope, mode, exact variants and feedback.
- Risks: cross-response evidence, historical citations and expired sessions.
- Tests: cancel/regenerate/old citations/reload/storage failure/keyboard.
- Done: exact evidence tuple and truthful execution state for every answer.

### Research

- Visual: research reference, follow-up tiles, notes and comparison.
- Reuse: decomposition stream, draft/session logic and templates.
- Frontend: explicit deeper-query control, mode-aware route/organization.
- Backend/API: shared conversations and existing decomposition.
- Persistence: mode, scope, notes, evidence and variants.
- Risks: templates mistaken for findings; saved history mistaken for live memory.
- Tests: deep follow-ups, expiry, mode change and reload.
- Done: persistent research without hidden regeneration or identity changes.

### Documents

- Visual: filters/statistics/table/detail rail with four tabs.
- Reuse: catalog/chunks/manifests and representations.
- Frontend: type/year/sort/page-size/selection/collection picker.
- Backend/API: extended documents, facets and stats.
- Persistence: saved document references and presentation preferences.
- Risks: missing metadata/representations and stale pages.
- Tests: combined filters, stable order, unknown values, representations.
- Done: real counts and exact document identity across actions.

### Search

- Visual: ranked highlighted cards and metrics/facets/recent rail.
- Reuse: safe highlights, source presentation, reader/handoffs.
- Frontend: keyword/hybrid discovery, grouping/pagination; remove engineering presets from primary flow.
- Backend/API: bounded snapshots, prefilters, scoped facets, expiry.
- Persistence: browser recent queries, explicit saves, temporary snapshots.
- Risks: bounded candidate counts represented as whole corpus totals.
- Tests: prefilters, expiry, empty pages and research/open/save handoffs.
- Done: scoped counts and stable snapshot navigation.

### Collections

- Visual: list/cards and contents/notes/activity/settings details.
- Reuse: snapshots, export and source verification.
- Frontend: CRUD, mixed typed items, tags/favorites, notes/private settings.
- Backend/API: SQLite repository; browser repository in public mode.
- Persistence: documents/evidence/answers/notes and actual activity.
- Risks: import loss, duplicates, conflicts and stale references.
- Tests: idempotency, failed writes, conflicts, tombstones, missing sources.
- Done: lossless round trip with honest stale/source-gone state.

### Retrieval

- Visual: engineering controls, four metrics, ranked table, excerpt preview.
- Reuse: inspection, presets, exports and stage fields.
- Frontend: stage columns, selected/dropped filters, diagnostic labels.
- Backend/API: additive document/date filters and versioned trace.
- Persistence: explicit saves only; queries are not telemetry.
- Risks: inspection confused with production structured promotion.
- Tests: legacy compatibility, unchanged production, raw scores.
- Done: named stage semantics including not-executed stages.

### Models

- Visual: routing/benchmark area and role-filtered registry.
- Reuse: settings, actual runtime identity, evaluation artifacts.
- Frontend: configured/loaded facts and compatible comparisons.
- Backend/API: allowlisted registry, bounded supported local tests.
- Persistence: measured test results/evaluation references; server-owned config.
- Risks: configured mistaken for loaded, unknown revisions, secret exposure.
- Tests: unknown revision/redaction/no implicit downloads or providers.
- Done: actual models and results; no unsupported hot switching/installing.

### Pipeline

- Visual: six nodes, four metrics, run table, selected-run timeline/alerts.
- Reuse: existing ingestion/chunking/embedding/indexing algorithms.
- Frontend: run details, progress/events/cancel and honest empties.
- Backend/API: durable local jobs and isolated staging adapters.
- Persistence: run/step records and owned staged artifacts.
- Risks: canonical overwrite, omitted financial tables, locks/stale outputs.
- Tests: ordering, restart interruption, cancellation, freshness, isolation/manifests.
- Done: successful staging changes no serving corpus; no automatic promotion.

### Reranker

- Visual: fusion/cross-encoder comparison from one trace.
- Reuse: inspection trace and model identity.
- Frontend: rank movement, raw scores, metadata/query context, accessible plot/table.
- Backend/API: inspection and registry.
- Persistence: explicit saved results only.
- Risks: scores treated as probabilities or unequal pools compared.
- Tests: negative scores, ties, skipped stage, same-pool identity.
- Done: actual scores from the same candidates.

### Evaluation

- Visual: metrics/runs/report rail/trends/failures/comparison.
- Reuse: report validation, frozen artifacts, native runners, checkpoints/ledgers.
- Frontend: separate job state from publication state; explicit metric semantics.
- Backend/API: private jobs/results and public definitions/compare/trends/failures.
- Persistence: SQLite metadata and immutable result/provenance artifacts.
- Risks: mixed bindings, fabricated pass/fail, skipped judges, conflated engines.
- Tests: missing/incomplete/incompatible/malformed results, budgets/cancel.
- Done: source, definition, denominator and eligibility for every metric.

### Analytics

- Visual: shared metrics/charts/tables with range/scope controls.
- Reuse: allowlisted events and actual request lifecycle.
- Frontend: local/server namespace, ranges and honest empties.
- Backend/API: content-free events/aggregates.
- Persistence: 30-day telemetry.
- Risks: headers mistaken for terminal latency; content leakage.
- Tests: complete/error/cancel/duplicate/empty/missing events.
- Done: defined rate/percentile populations and terminal timing.

### Datasets

- Visual: registry, corpus/evaluation tabs and coverage/provenance.
- Reuse: manifests, bindings and selectors.
- Frontend: detail/missing/degraded states.
- Backend/API: allowlisted registry referring to original authorities.
- Persistence: metadata/references, not duplicate canonical data.
- Risks: target-section coverage mistaken for full coverage.
- Tests: missing artifacts, degraded manifests, hash/version mismatch.
- Done: actual versions and coverage, no invented completeness.

### Settings

- Visual: preferences/storage/import/local connection/retention/provider status.
- Reuse: browser preferences/storage status/system facts.
- Frontend: allowlisted settings and recovery/import.
- Backend/API: protected settings/configuration-status flags.
- Persistence: browser presentation preferences; SQLite operational settings.
- Risks: secrets or arbitrary path/model/key mutation.
- Tests: public/local boundary, redaction, invalid imports/unsupported settings.
- Done: useful settings without fake users or keys management.

## 10. API Plan and Contract Rules

These are proposed additive endpoints, not claims of current implementation. Existing query/SSE, session, reader, chunk, PDF and health contracts remain compatible. Register static document facets/stats routes before dynamic document paths.

Shared contracts:

- Page<T>: items, total, page, page_size. Discovery also states count_scope, snapshot identity and expiry; bounded totals never imply corpus totals.
- EvidenceRef: document/chunk/source IDs, content hash, revisions and representation/location when known.
- Conversation: compatible existing record plus mode, submitted scope and exact variant identity.
- Collection: id/name/description/tags/favorite/private visibility/revision/timestamps. CollectionItem kind is document, evidence, answer or note with typed snapshot/reference.
- Job: id/type/state/timestamps/progress/sanitized failure/configuration fingerprint/artifact references. PipelineRun adds ordered steps; EvaluationJob adds frozen bindings.
- Metric: engine/key/version/value/unit/status/counts/denominator/definition/binding. Missing or not-applicable is not zero.
- DocumentSummary, facets and statistics derive from the same catalog. DiscoverySnapshot owns stable ranked/grouped pages. Trace is versioned. Registry distinguishes configured, loaded, available and unknown.
- Receipt identifies committed operations/imports. Tombstones prevent resurrection. Activity and events represent recorded operations.

Mutations return committed revisions; use If-Match/revision preconditions and 409 conflicts. Imports and job creation are idempotent. Opaque IDs never accept arbitrary filesystem paths. P = public, allowlisted, provider-free; L = protected local workspace, including reads; J = L plus execution/resource/provider-budget checks.

| Method | Path | Request/parameters | Response | Service/storage | Access | Contract test |
| --- | --- | --- | --- | --- | --- | --- |
| GET | /documents | Company/type/year/sort/page filters | Page<DocumentSummary> | Catalog/memory | P | Combined filters/stable order |
| GET | /documents/facets | Catalog filters | Facet counts/scope | Catalog/memory | P | Filter consistency |
| GET | /documents/stats | None | Counts/availability/timestamp | Catalog/memory | P | Unknown versus zero |
| POST | /search | Query/mode/filters/grouping/page size | DiscoverySnapshot first page | Discovery/bounded memory | P | Prefilter |
| GET | /search/{search_id} | Page/page size | Snapshot page/scope/expiry | Discovery/bounded memory | P | Expired/stale |
| POST | /retrieval/inspect | Existing request plus document/date | Versioned Trace | Inspection/no new persistence | P | Legacy/production compatibility |
| GET | /conversations | Search/mode/page | Page<ConversationSummary> | Workspace/SQLite | L | Private isolation |
| POST | /conversations | Mode/title | Conversation | Workspace/SQLite | L | Validation |
| GET | /conversations/{id} | ID | Conversation | Workspace/SQLite | L | Exact variants |
| PUT | /conversations/{id} | Record/revision | Committed Conversation | Workspace/SQLite | L | Conflict/interrupted write |
| DELETE | /conversations/{id} | Revision | Tombstone receipt | Workspace/SQLite | L | No resurrection |
| GET | /collections | Search/tags/favorite/sort/page | Page<Collection> | Collections/SQLite | L | Stable filters |
| POST | /collections | Name/description/tags | Collection | Collections/SQLite | L | Bounds |
| GET | /collections/{id} | ID | Collection detail | Collections/SQLite | L | Identity |
| PATCH | /collections/{id} | Fields/revision | Committed Collection | Collections/SQLite | L | Concurrency |
| DELETE | /collections/{id} | Revision | Receipt | Collections/SQLite | L | Atomic deletion |
| GET | /collections/{id}/items | Kind/page | Page<CollectionItem> | Collections/SQLite | L | Mixed assets |
| POST | /collections/{id}/items | Typed asset/reference/snapshot | CollectionItem | Collections/SQLite | L | Duplicate/stale |
| DELETE | /collections/{id}/items/{item_id} | Revision | Receipt | Collections/SQLite | L | Parent ownership |
| POST | /collections/{id}/notes | Text/optional EvidenceRef | Note | Collections/SQLite | L | Bound/unbound |
| PATCH | /collections/{id}/notes/{note_id} | Text/revision | Committed Note | Collections/SQLite | L | Conflict |
| DELETE | /collections/{id}/notes/{note_id} | Revision | Receipt | Collections/SQLite | L | Ownership |
| GET | /collections/{id}/activity | Page | Page<Activity> | Collections/SQLite | L | Actual history |
| GET | /collections/{id}/export | JSON or Markdown | Download | Collections/read-only | L | Portable export |
| POST | /workspace/imports/preview | Versioned backup | Counts/conflicts/digest | Import/no mutation | L | Malformed/future schema |
| POST | /workspace/imports | Backup/preview digest | Idempotent receipt | Import/SQLite transaction | L | Retry |
| GET | /workspace/export | None | Versioned backup | Workspace/SQLite | L | Round trip |
| GET | /models | Role | Configured/runtime registry | Registry/settings | P | No fake models/secrets |
| POST | /models/{id}/tests | Supported local test | Measured result | Model tests/SQLite | J | No implicit provider/download |
| GET | /pipeline | None | Definition/capabilities | Pipeline/static | P | Actual order |
| GET | /pipeline/runs | Status/page | Page<PipelineRun> | Jobs/SQLite | L | History |
| POST | /pipeline/runs | Registered input IDs/staging profile | PipelineRun job | Jobs/SQLite/isolated artifacts | J | No canonical writes |
| GET | /pipeline/runs/{id} | ID | Steps/artifacts/status | Jobs/SQLite | L | Partial failure |
| POST | /pipeline/runs/{id}/cancel | ID | Cancellation state | Jobs/SQLite | J | Stop future work |
| GET | /pipeline/runs/{id}/events | Last-Event-ID | Ordered SSE | Jobs/SQLite | L | Reconnect |
| GET | /evaluation/runs | Compatible existing filters | Published summaries | Validated report files | P | No private jobs |
| GET | /evaluation/runs/{id} | ID | Validated published report | Validated report files | P | Compatibility |
| GET | /evaluation/runs/{id}/results | Case filter/page | Cases/metric metadata | Validated report files | P | Denominators/missing |
| GET | /evaluation/metrics | None | Definitions/capabilities | Metric registry | P | Semantics |
| POST | /evaluation/compare | Run IDs/metric IDs | Eligibility/differences/reasons | Reports/read-only | P | Bindings |
| GET | /evaluation/metrics/trends | Metric/binding group/range | Comparable observations | Validated report files | P | No synthetic trend |
| GET | /evaluation/failures | Run ID/category/page | Failure groups/cases | Validated report files | P | No invented hallucination labels |
| GET | /evaluation/jobs | Status/page | Page<EvaluationJob> | Jobs/SQLite | L | Privacy |
| POST | /evaluation/jobs | Registered frozen artifact/engine/metrics/mode/budget | EvaluationJob | Jobs/SQLite/artifacts | J | Budget/binding |
| GET | /evaluation/jobs/{id} | ID | Job/result references/provenance | Jobs/SQLite | L | Incomplete |
| GET | /evaluation/jobs/{id}/results | Page | Private cases/metrics | Private artifacts | L | Exact context |
| POST | /evaluation/jobs/{id}/cancel | ID | Cancellation state | Jobs/SQLite | J | No further attempts |
| GET | /evaluation/jobs/{id}/events | Last-Event-ID | Ordered SSE | Jobs/SQLite | L | Resume |
| GET | /analytics/summary | Range | Counts/rates/percentiles/denominators | Events/SQLite | L | Terminal streaming timing |
| GET | /analytics/timeseries | Range/interval/metric | Aggregates | Events/SQLite | L | Empty/missing |
| GET | /datasets | Kind | Registry summaries | Manifests | P | Actual versions |
| GET | /datasets/{id} | ID | Coverage/provenance | Manifests | P | Missing/hash mismatch |
| GET | /workspace/settings | None | Allowlisted settings | Settings/SQLite | L | Secret exclusion |
| PATCH | /workspace/settings | Supported preferences | Committed settings | Settings/SQLite | L | Reject model/path/key mutation |
| GET | /system/configuration-status | None | Flags/capabilities | Runtime configuration | L | No secret fragments |
| GET | /logs | Category/level/cursor/bounded limit | Sanitized events | Events/SQLite | L | Redaction/bounds |

Public search POST is provider-free/ephemeral. Comparison POST is read-only over published artifacts. Import preview is protected and non-mutating. Private job results never enter public report reads automatically. Pipeline and evaluation have distinct job namespaces and validated publication remains separate.

## 11. Persistence, Migration and Recovery

Use built-in SQLite, explicit SQL/migrations, no ORM/PostgreSQL/Redis/external queue. Future paths: .local/workbench/workspace.sqlite3 and .local/workbench/runs/{run_id}/. Add ignore rules during implementation; this checkpoint creates neither runtime directories nor data artifacts.

Use WAL, foreign keys, short transactions, bounded busy handling and serialized writes. Entities include workspace records/revisions/tombstones, imports, migrations, jobs/steps, allowlisted settings and content-free events. Recover interrupted jobs truthfully.

Migration: detect conversation v4, evidence v1/v2, favorites and notes; offer original downloadable backup; preview counts/conflicts with digest; transactional import with legacy-ID mapping; idempotent receipt; retain originals; select one authoritative repository. No silent dual writes. Disconnects retain unsaved/exportable work rather than pretending server save; public mode keeps browser persistence.

Research content is deliberately stored in the workspace; telemetry contains no research content. Telemetry retention 30 days, sanitized logs 7 days, research until user deletion, job artifacts until explicit cleanup. Cleanup never reaches canonical corpus data.

## 12. Native Evaluation, Ragas and TruLens

Native remains authoritative. Expose true namespaced semantics:

| Key | Meaning |
| --- | --- |
| native.faithfulness | Existing native judge definition/binding |
| native.answer_relevancy | Existing native relevance definition/binding |
| native.context_precision | Existing native context precision definition |
| native.citation_index_validity | Valid source numbers, not claim support |
| native.keyword_recall_proxy | Deterministic proxy, not semantic context recall |
| native.fallback_correctness | Existing fallback-case correctness |

Engine protocol: capabilities, required inputs, preflight budgets, frozen-case evaluation, typed results and engine/version/prompt/model/embedding fingerprints. Implement native first. Ragas is optional, isolated and gated by hermetic adapter tests; it is never a serving dependency. Its datasets/OpenAI/Instructor/LangChain ecosystem requires a separately pinned environment.

Generation, deterministic metrics and judging must receive the same rendered evidence. Context recall requires reference inputs; missing prerequisites are not-applicable, not zero. Keep engine definitions/bindings separate; no implicit provider fallback or merged unlike metrics. All internal attempts/retries count in the ledger. Preserve KEY5-only provider-key use. Installing a package does not make judging provider-free; explicit offline/deterministic substitutes need separate labels/bindings.

Costs depend on cases, metrics, context/claim counts and retries. Generation checkpoints are append-only, single-binding; a changed binding requires a fresh path. Judge per-case bindings require complete provenance. Quota-skipped/incomplete/mixed aggregates are not official. The clean priority <=2 N=30 benchmark remains official unless PROJECT_STATE.md explicitly supersedes it.

Defer TruLens: overlapping tracing/console and added core/dashboard/feedback/telemetry dependencies do not justify immediate adoption. Keep protocol extensibility without an empty selectable engine.

Previously consulted sources: [Ragas faithfulness](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/faithfulness/), [context precision](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/context_precision/), [answer relevance](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/answer_relevance/), [Ragas manifest](https://raw.githubusercontent.com/vibrantlabsai/ragas/main/pyproject.toml), [TruLens manifest](https://raw.githubusercontent.com/truera/trulens/main/pyproject.toml). These preserve prior research provenance; this checkpoint did not repeat it.

## 13. Stitch Strategy

Reuse project 3773610233677432915, Enterprise Document QA — High-Fidelity Screenshot Reconstruction, with 12 exportable screens. No Stitch mutations occurred during planning. Local screenshots override differing export dimensions.

Map exports to local references; import into ignored frontend/.stitch-import; inspect HTML/CSS/assets/licenses/dependencies; extract geometry; rewrite using repository primitives; remove demos/unsupported controls/generated clutter; bind real APIs; compare native sizes; retain reviewed assets/code only. Generated output must not replace proven domain logic or automatically introduce dependencies.

## 14. Phases and Gates

| Phase | Scope | Exit gate |
| --- | --- | --- |
| 0 | Save plans, compatibility baseline | Saved specification and baseline evidence |
| 1 | Access, SQLite, contracts | Privacy/migration safety |
| 2 | Tokens/router/shell | Legacy links/responsiveness |
| 3 | Chat/Research/readers | Exact evidence/variant identity |
| 4 | Documents/Search/Retrieval/Reranker | Honest counts, unchanged production retrieval |
| 5 | Collections/import | Lossless round trip |
| 6 | Models/Datasets | Actual configuration/provenance |
| 7 | Pipeline | Isolated completion; canonical data unchanged |
| 8 | Native Evaluation | Bindings/budgets/publication boundary |
| 9 | Optional Ragas, Analytics, Logs, Settings | Isolation/privacy/defined metrics |
| 10 | Product/visual QA, cleanup | Review and safe removal gates |

Use route rollout controls without concurrent authoritative writers. Rollback may restore old routes while retaining new records. Remove legacy code only after compatibility/zero-reference gates.

## 15. Testing Plan

Frontend: component states/accessibility, nullable/missing contracts, routed/legacy links; E2E citation/read/save/old-variant flows; request races/cancellation; storage denial/import/revision conflicts. Test the production build in Chromium and Firefox, controlling storage-sensitive suites with one worker where needed.

Backend: API compatibility; SQLite rollback/concurrency/tombstones; search prefilters/count scope/expiry/stable pages; inspection and production invariants. Pipeline: enrichment ordering, explicit destinations/path isolation, restart/crash/cancel/manifests. Evaluation: binding changes, every attempted provider call, budgets, missing/malformed records, cancellation and public/private separation. Verify redaction and terminal timing.

Preserve the hermetic socket guard. Ordinary tests cannot reach SEC, Hugging Face, Groq or Qdrant Cloud. Explicit integration/live_network markers and the established diagnostic SEC live-smoke workflow remain required. No implementation tests or dependency installation occur in Checkpoint 09.

## 16. Visual Validation Plan

Review all nine references at native dimensions, then widths 1600/1440/1280/1024/768/390; dark/light, English/Vietnamese, populated/empty/loading/error/stale, zoom 125/150/200%. Review zoom manually where automation does not faithfully represent it.

Use coherent development-only populated fixtures for parity and real/sparse data to verify honesty. Never add fabricated production metrics to match images. Compare screenshots side by side for geometry/proportions, alignment, density, type hierarchy, borders/selection, paper surface/highlights, composer position, scrolling and focus. Passing tests alone are not visual proof; record per-screen review and differences.

## 17. Risk Register

| Risk | Mitigation/gate |
| --- | --- |
| Existing dirty tree | Preserve baseline; scoped diffs, no blanket revert |
| Migration loss | Backup/digest preview/transaction/idempotency/retain originals |
| Cross-answer evidence | Exact response/source/document/revision/variant binding |
| Fake page/model/job state | Actual capabilities, explicit unknown/empty |
| Private data exposed | Protect reads/writes; exact local access boundary |
| Pipeline corrupts serving corpus | Isolated destinations; no automatic promotion |
| Missing financial tables | Enrichment required before embedding/indexing |
| Diagnostics confused with production | Stage semantics and not-executed labels |
| Search overstates counts | Snapshot/bounds/count scope |
| Metric conflation | Namespaces/definitions/denominators/binding eligibility |
| Dependency/provider expansion | Isolated optional environment and budgets |
| Partial readiness appears healthy | Separate configured/loaded/available/operational facts |
| Tests pass, visual differs | Native side-by-side review |
| Header timing called full latency | Terminal completion/error/cancel events |

## 18. Keep, Reuse, Rewrite and Delete

Keep identity, SEC URL validation, errors/recovery, deep links, reader locations, backup validation and tests. Keep with adapters: reader engines, conversation migration, cancellation/session logic and variants.

Reuse domain logic in ChatMessage, documents/search/retrieval, evaluation comparison, collections, analytics and related-question templates. Rewrite App navigation/header/layout, feature composition/controllers, console presentation and duplicated state ownership.

Delete obsolete wrappers/context composition/styles/generated demo imports only after zero references, passing replacement tests and recorded migration/rollback mapping. Untracked does not mean disposable. Retain legacy URL and browser-schema readers until compatibility gates permit retirement.

## 19. Backend Work Packages

Create domain routers/schemas/services, explicit SQLite migrations, local access dependencies, job repository/coordinator, pipeline staging adapters, engine protocol/native and optional isolated Ragas workers, discovery snapshots and registries. Incrementally modify bootstrap, document settings/environment flags, add terminal telemetry, extend inspection additively, give staging explicit destination ownership and preserve public-report compatibility. Do not redesign ingestion algorithms/source identity while exposing workflows.

## 20. Dependencies and Deployment

Frontend: React Router, TanStack Query, self-hosted Inter; retain compatible lockfile discipline. No broad UI framework/diagram runtime/unrelated upgrades. Backend: built-in persistence/coordination, no new database/queue service. Optional Ragas has its own pinned environment/lock, not main requirements. Preserve Docker CPU-only PyTorch and model revision behavior. No TruLens installation.

Frontend remains independent and excluded from backend Docker. Vercel root is frontend, VITE_API_BASE_URL is reachable, browser variables contain no secrets, and direct-route rewrites work. Preserve explicit CORS and required ngrok warning header. Local Qdrant remains single-worker; server/cloud mode is required for multiple workers. No such files or dependencies are changed in this checkpoint.

## 21. Full Implementation Task Graph

First ten priorities: TEST-001, API-001, DATA-001, UI-001, UI-002, API-002, DATA-002, UI-003, API-003, API-004. This is ordering, not a calendar estimate. Parallel opportunities describe independent areas, not authorization for delegation or shared-file concurrent edits.

Saved planning documents are the external prerequisite for TEST-001. TEST-002 enumerates API/data/native-evaluation gates; TEST-003 enumerates UI gates. Optional EVAL-004 adds its own verification when enabled but does not block native-only completion.

| Task ID | Goal/output | Dependencies | Files/area | Validation gate | Parallel opportunity |
| --- | --- | --- | --- | --- | --- |
| TEST-001 | Compatibility baseline | None; saved planning documents | Existing API/frontend/E2E tests | Routes/schemas/behavior baseline | First implementation task |
| API-001 | Local access boundary | TEST-001 | API dependencies/settings/environment docs | Public/local read/write matrix | UI-001 |
| DATA-001 | SQLite and migrations | API-001 | Persistence | Transactions/revisions/migration | Shell |
| UI-001 | Tokens/fonts/primitives | TEST-001 | Styles/shared UI/fonts | Contrast/states | API-001 |
| UI-002 | Router/shell/legacy adapter | UI-001 | App/layouts/navigation/hosting | Direct/back/old hashes | DATA-001 |
| API-002 | Compatible router extraction | TEST-001 | API app/routers/schemas | Unchanged wire behavior | Avoid shared bootstrap edits |
| DATA-002 | Browser import/repository adapter | DATA-001 | Stores/import UI/API | Idempotent/lossless | API-003 |
| UI-003 | Chat/Research | UI-002, DATA-002 | Conversation pages/hooks | Cancel/variants/persistence | Catalog |
| API-003 | Catalog facets/stats | API-002 | Documents services | Counts/filters | DATA-002 |
| UI-004 | Source/document composition | UI-003 | Workbench/reader chrome | Exact/stale/ambiguous evidence | Sequential reader gate |
| API-004 | Discovery snapshots | API-002, API-003 | Search/retrieval filters | Prefilter/bounded/stable | UI-004 |
| API-005 | Inspection metadata | API-002 | Retrieval trace | Legacy/production unchanged | After filter ownership settled |
| UI-005 | Documents | UI-002, API-003 | Documents feature | Filter/select/read/save | API-004 |
| UI-006 | Search | UI-002, API-004 | Search feature | Group/facet/expiry/handoff | Collections backend |
| UI-007 | Retrieval/Reranker | UI-002, API-005 | Engineering features | Same pool/raw scores | UI-006 |
| DATA-003 | Typed collections | DATA-001, DATA-002 | Collections repository/router | Mixed assets/conflicts | UI-006 |
| UI-008 | Collections | UI-002, DATA-003, UI-004 | Collections feature | Save/export/reopen/stale | Registries |
| API-006 | Model/dataset registries | API-002 | Registry services | Actual config/manifests | UI-008 |
| UI-009 | Models/Datasets | UI-002, API-006 | Registry features | Unknown/configured/loaded | Jobs |
| DATA-004 | Durable jobs | DATA-001 | Job repository/coordinator | Idempotency/order/interrupted | UI-009 |
| API-007 | Pipeline staging | DATA-004 | Pipeline/script adapters | No canonical writes | Sequential stage gate |
| UI-010 | Pipeline | UI-002, API-007 | Pipeline feature | Submit/cancel/complete/reconnect | Evaluation services |
| EVAL-001 | Metrics/native protocol | API-002 | Evaluation services | Same scores/bindings | Pipeline UI |
| EVAL-002 | Compare/trends/failures | EVAL-001 | Public reports | Eligibility/denominators | EVAL-003 |
| EVAL-003 | Frozen budgeted jobs | EVAL-001, DATA-004 | Evaluation worker | Fresh binding/budget/cancel | EVAL-002 |
| UI-011 | Evaluation | UI-002, EVAL-002, EVAL-003 | Evaluation feature | Missing/one-run/incomplete/compare | Telemetry |
| EVAL-004 | Optional isolated Ragas | EVAL-003 | Optional environment/worker | Hermetic; distinct metrics/bindings | Optional after native gate |
| DATA-005 | Terminal telemetry/logs | DATA-001, DATA-004 | Events/retention | Privacy/terminal duration | UI-011 |
| UI-012 | Analytics/Logs/Settings | UI-002, DATA-005, API-001 | Operational features | Retention/privacy/capabilities | Optional Ragas |
| TEST-002 | Cross-layer contracts | API-001, API-002, API-003, API-004, API-005, API-006, API-007, DATA-001, DATA-002, DATA-003, DATA-004, DATA-005, EVAL-001, EVAL-002, EVAL-003 | Contract tests | Compatibility/migration/privacy; EVAL-004 checks if enabled | Throughout |
| TEST-003 | Nine-reference visual validation | UI-001, UI-002, UI-003, UI-004, UI-005, UI-006, UI-007, UI-008, UI-009, UI-010, UI-011, UI-012 | Playwright fixtures/captures/review | Actual side-by-side review | Per completed page |
| TEST-004 | Full product validation | TEST-002, TEST-003 | Browser/integration suites | Widths/locales/two browsers | Final integration |
| UI-013 | Cleanup/documentation | TEST-004 | Old wrappers/styles/README/contracts/project state | Zero references/compatibility/rollback | Last |

Spine: TEST-001 branches into UI-001 → UI-002 → pages, API-001 → DATA-001 → import/collections/jobs, and API-002 → services. DATA-004 enables Pipeline and evaluation execution. Service/page work converges at TEST-002 and TEST-003, then TEST-004, then UI-013. This is the planning dependency graph; current completion status is recorded at the top of `PROJECT_STATE.md` and `UI_REBUILD_PLAN_CHECKPOINT.md`.

## 22. Definition of Done

Every visible destination is backed by an actual capability. All nine references have recorded visual review. Browser migration preserves research content, variants and evidence identity. Readers/cancellation/retrieval/old links remain compatible. Pipeline cannot overwrite canonical serving data. Evaluation exposes definitions/denominators/bindings, obeys budgets and separates official reports from private/incomplete jobs. Workspace privacy and content-free telemetry are verified.

Required contracts, integration, browser and visual gates pass. Documentation reflects implemented behavior. Cleanup follows compatibility and rollback gates. The final status of these gates is recorded in the current project state and checkpoint; the earlier planning-only status is historical, not a pending implementation instruction.

## Appendix A. Reference Gap Matrix

The complete feature-level matrix is the standalone [UI_REFERENCE_GAP_MATRIX.md](UI_REFERENCE_GAP_MATRIX.md), including all nine references and shared/page-specific rows. It is part of this plan and is not replaced by Section 3's summary.
