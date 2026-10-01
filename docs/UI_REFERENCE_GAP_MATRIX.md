# UI Reference Gap Matrix — Appendix A

Complete standalone Appendix A of [UI_REBUILD_MASTER_PLAN.md](UI_REBUILD_MASTER_PLAN.md). These are the completed planning findings, transcribed without a new screenshot analysis. “Exists now” describes the audited pre-rebuild state, including dirty working-tree work; it does not claim implementation during Checkpoint 09.

## Nine-reference inventory

| Screen | Reference filename | Native dimensions |
| --- | --- | --- |
| Chat | rag-workbench-master-reference-dark.png | 1254 × 856 |
| Research | research-ui-reference-dark-v1.png | 1586 × 992 |
| Documents | documents-ui-reference-dark-v1.png | 1586 × 992 |
| Search | search-ui-reference-dark-v1.png | 1586 × 992 |
| Retrieval | retrieval-ui-reference-dark-v1.png | 1586 × 992 |
| Collections | collections-ui-reference-dark-v1.png | 1586 × 992 |
| Models | models-ui-reference-dark-v1.png | 1586 × 992 |
| Pipeline | pipeline-ui-reference-dark-v1.png | 1586 × 992 |
| Evaluation | evaluation-ui-reference-dark-v1.png | 1586 × 992 |

P0 = correctness/foundation gate; P1 = core research workflow; P2 = subsequent product capability; P3 = optional/deferred. “Target” distinguishes required product behavior from a control explicitly pictured. All means shared reference chrome. Reranker, Analytics, Datasets and Settings are additionally specified in the master plan, without inventing extra reference screenshots.

| Reference screen | Feature | Visible in screenshot | Exists now | Backend support | Reuse | Rebuild | New backend | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| All | Grouped sidebar | Yes | Partial | Partial capabilities | Navigation concepts | Shell/groups | Capability flags | P0 |
| All | Corpus/scope selector | Yes | Partial | Ticker/catalog | Scope logic | Compact control | Corpus registry | P1 |
| All | Global command/search | Yes | Yes, local commands | Local command registry | Registry | Discovery integration | Discovery API | P1 |
| All | Health/readiness | Yes | Yes | Readiness API | Actual status | Precise wording | None | P0 |
| All | Active LLM | Yes | Partial | Query identity | Identity | Header | Registry | P1 |
| All | Theme/settings | Yes | Partial | Browser preferences | Preferences | Controls | Local settings | P1 |
| All | Profile | Yes | No authentication | None | None | Local identity | No fake account | P0 |
| All | Storage/quota | Yes | Browser status | No quota | Storage status | Truthful footer | Measured size only | P2 |
| All | Upgrade | Yes | No | None | None | Omit | Deferred | P3 |
| Chat | Question/answer | Yes | Yes | Query/SSE | Domain transport | Presentation | Conversation persistence | P1 |
| Chat | Citations/count | Yes | Yes | Source payload | Exact identity | Compact markers | None | P0 |
| Chat | Model/latency/state | Yes | Partial | Response/stages | Measurements | Labels | Terminal telemetry | P1 |
| Chat | Copy/regenerate/feedback | Yes | Yes | Query/local feedback | Actions | Action row | Feedback persistence | P1 |
| Chat | Notes | Yes | Yes | Browser notes | Target identity | Notes flow | Workspace storage | P1 |
| Chat | Execution stages | Yes | Yes | Stage events | Execution state | Geometry | No invented stages | P1 |
| Chat | Composer controls | Yes | Partial | SEC/decomposition | Draft/scope | Composer | Hide unsupported Web/upload | P1 |
| Chat | Source cards/ranking | Yes | Yes | Sources | Source binding | Dense cards | None | P1 |
| Chat | Insights | Yes | Partial | Counts/timings | Real fields | Cards | Missing explicit | P1 |
| Chat | Related questions | Yes | Templates | No generated suggestions | Templates | Presentation | None | P2 |
| Chat | Reader tabs/highlight | Yes | Yes | Reader/PDF | Engines | Chrome | None | P0 |
| Chat | Annotations | Yes | Partial | Browser notes | Note concepts | Evidence-bound flow | Persistence | P1 |
| Research | Dedicated destination | Yes | Partial | Shared RAG | Conversation | Mode/route | Mode persistence | P1 |
| Research | Deeper comparison | Yes | Yes | Decomposed stream | Existing capability | Explicit control | None | P1 |
| Research | Follow-ups | Yes | Partial | Templates | Templates | Tiles | None | P1 |
| Research | History | Yes | Local | Session memory | Library | History UI | SQLite conversations | P1 |
| Research | Saved evidence/notes | Yes | Partial | Browser | Snapshots | Workspace flow | SQLite | P1 |
| Documents | Company/content search | Yes | Partial | Metadata/chunks | Catalog | Separate search scopes | Company search | P1 |
| Documents | Type/year/section | Yes | Partial | Section/date | Existing filters | Filter grid | Type/year facets | P1 |
| Documents | Counts | Yes | Partial | Catalog/health | Real totals | Metric cards | Statistics | P1 |
| Documents | Sort/page size/pagination | Yes | Partial | Pagination | Existing paging | Controls | Sorting | P1 |
| Documents | Selectable table | Yes | Yes | Catalog | Identity | Density | None | P1 |
| Documents | Detail tabs | Yes | Yes | Reader/catalog | Manifests | Rail | Metadata extension | P1 |
| Documents | Summary | Yes | Factual metadata | No LLM summary | Metadata | Honest label | No LLM invention | P2 |
| Documents | Representation/preview | Yes | Yes | Reader/PDF | Engines | Layout | None | P0 |
| Documents | Add to collection | Yes | Partial | No server collection | Save concept | Picker | Document item | P1 |
| Documents | Import/My documents | Yes | Unsupported | No upload/ownership | None | Hide | Deferred | P3 |
| Search | Keyword/natural language | Yes | Diagnostic substitute | Inspection | Primitives | Discovery | Discovery service | P1 |
| Search | Collection/type/date filters | Yes | Partial | Limited metadata | Facet concepts | Filters | Prefiltering | P1 |
| Search | Grouping | Yes | Limited | No grouping contract | Identity | Grouped cards | Group metadata | P1 |
| Search | Highlights | Yes | Yes | Chunks | Safe rendering | Highlight layout | Optional ranges | P1 |
| Search | Count/latency/score | Yes | Partial | Diagnostics | Measurements | Scope labels | Snapshot/count scope | P0 |
| Search | Facets | Yes | Selected subset | No facet API | UI concepts | Rail | Scoped counts | P1 |
| Search | Recent/saved | Yes | Local recent | None | Local history | Explicit saves | No query-content log | P2 |
| Search | Research/open/save actions | Yes | Yes | Reader/inspection | Handoffs | Actions | Collection persistence | P1 |
| Search | Pagination | Yes | No | Top-k only | None | Pagination | Snapshot | P1 |
| Retrieval | Query/preset/parameters | Yes | Yes | Inspection | API/controls | Engineering layout | None | P1 |
| Retrieval | Document filters | Yes | Partial | Ticker/section | Filter logic | Controls | Eligible document IDs | P1 |
| Retrieval | Counts | Yes | Backend trace | Trace | Actual counts | Cards | None | P0 |
| Retrieval | Stage scores | Yes/implicit | Yes | All diagnostic stages | Fields | Columns | Semantics metadata | P1 |
| Retrieval | Structured promotion | Implicit target | Not in inspection | Production only | Established distinction | Not-executed label | Observer metadata only | P0 |
| Retrieval | Selected/dropped | Yes | Flag | Trace flag | Selection flag | Filters | Known reasons only | P1 |
| Retrieval | Evidence preview | Yes | Yes | Chunk/reader | Binding | Detail rail | None | P1 |
| Retrieval | Export/save/open | Yes | Yes | Existing export/handoffs | Existing actions | Controls | Collections | P1 |
| Collections | Cards/list/search/sort | Yes | Partial | Browser records | Records | Controls | Repository | P1 |
| Collections | Description/tags/favorite | Yes | Partial | No server support | Favorite import | Editing | Persistent fields | P1 |
| Collections | Mixed items | Yes | Evidence only | No server support | Snapshots | Typed items | Document/answer/note | P1 |
| Collections | Notes/activity | Yes | Partial/no activity | None | Notes | Tabs | Actual events | P1 |
| Collections | Add/remove/export | Yes | Partial | Browser | Export validation | Flows | CRUD/export | P1 |
| Collections | Shared visibility | Yes | No authentication | None | None | Private label | Sharing deferred | P3 |
| Models | Roles | Yes | Partial | System info/settings | Configuration | Registry table | Registry | P2 |
| Models | Revision/dimension/status | Yes/target | Partial | Runtime metadata | Metadata | Details | Allowlisted fields | P2 |
| Models | Routing | Yes | Fixed | No dynamic routing | Current routing | Read-only diagram | No switching | P2 |
| Models | Benchmark comparison | Yes | Partial | Reports | Evaluation metadata | Eligible comparison | Comparison service | P2 |
| Models | Tests | Yes | No UI | Loaded local models | Local calls | Result UI | Bounded test | P2 |
| Models | Add/default/fallback/A-B | Yes | Unsupported | No lifecycle | None | Hide | Deferred | P3 |
| Pipeline | Summary | Yes | Snapshot | No runs | Corpus info | Metrics | Durable jobs | P2 |
| Pipeline | Six-node flow | Yes | No execution UI | CLI algorithms | Algorithms | Nodes | Orchestrator | P2 |
| Pipeline | Table-chunk dependency | Not explicit | CLI capability | Required enrichment | Table logic | Nested chunk step | Dependency gate | P0 |
| Pipeline | History | Yes | No | None | None | Run table | Durable history | P2 |
| Pipeline | Step timings | Yes | No | Partial CLI | Stage boundaries | Timeline | Events | P2 |
| Pipeline | Run/cancel/retry | Yes/target | No UI | CLI | Stage functions | Local controls | Job lifecycle | P2 |
| Pipeline | Schedule/templates | Yes | No | Fixed definition | Definition | Hide schedule | Deferred | P3 |
| Pipeline | Logs/details | Yes | No | Partial CLI | Categories | Rail | Sanitized events | P2 |
| Evaluation | Metrics | Yes | Partial | Native reports | Definitions | Precise labels | Catalog | P0 |
| Evaluation | Run table | Yes | Yes | Reports | Publisher | Job/report distinction | Job store | P2 |
| Evaluation | Dataset/judge/duration | Yes | Partial | Artifacts | Bindings | Details | Registry metadata | P2 |
| Evaluation | New run | Yes | No API | Runners | Native runner | Budgeted launch | Jobs | P2 |
| Evaluation | Trends | Yes | Partial | No comparable series | Chart concepts | Eligible trends | Trend service | P2 |
| Evaluation | Failures | Yes | Partial | Reasons/gates | Recorded failures | Categories | Aggregation | P2 |
| Evaluation | Compare | Target need | Basic client | Reports | Comparison logic | Eligibility reasons | Server comparison | P2 |
| Evaluation | Ragas/TruLens | Not explicit | Absent | Native evaluation | Frozen inputs | Engine labels | Optional Ragas; defer TruLens | P3 |

## Interpretation and validation boundary

All nine reference screens are represented in both inventory and detailed rows. A pictured feature does not authorize fabricated data or unsupported operations. P3 rows remain explicit scope decisions. The master plan defines API access, persistence, task dependencies, metric semantics and visual gates. Checkpoint 09 validates document coverage and consistency only; future TEST-003 performs actual rebuilt-screen validation.
