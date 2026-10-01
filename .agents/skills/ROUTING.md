# SEC RAG skill routing

Use one primary authority per concern. Helpers are conditional and remain
inactive unless the evidence crosses their boundary.

| Trigger | Primary | Conditional helper | Keep inactive |
|---|---|---|---|
| SEC workspace UI, journey, state, accessibility, rendered quality | `rag-ui-ux` | `product-design:audit`, browser/computer-use | RAG specialists unless evidence crosses their boundary |
| Verified architecture or request/data-flow diagram | `rag-core` | `archify` | UI and quality specialists unless relevant |
| Missing/irrelevant passage, fusion, candidate, reranker issue | `rag-retrieval-quality` | `rag-evaluation` for comparison; `rag-performance` for measured cost | Provenance unless identity/representation is implicated |
| Metric, judge, dataset, checkpoint, or benchmark claim | `rag-evaluation` | Retrieval/provenance as diagnosed | UI and performance unless needed |
| Threat, prompt injection, unsafe acquisition, HTML, leakage | `rag-security` | Core/provenance for contract or identity changes | UI unless safe presentation changes |
| Measured latency, memory, streaming, cache, parsing, first useful content | `rag-performance` | Core/retrieval/provenance as attributed | Evaluation unless comparing quality |
| Wrong filing/source/citation, stale revision, representation or coverage mismatch | `rag-document-provenance` | UI for presentation; security for adversarial acquisition | Retrieval unless relevance is separately shown |
| Explicit deep external research | `deep-research` | One relevant project specialist | Unrelated skills |

“RAG issue” alone is insufficiently precise. Clarify or inspect enough to choose
the primary boundary. Do not use a UI issue to activate all RAG skills, and do
not use a performance issue to automatically tune retrieval.

## Handoff contract

A handoff names the receiving authority, the evidence already established, and
the boundary still unresolved. It does not copy the entire source skill or
automatically spawn another agent. The receiver must preserve the originating
scope, identity, revision, and test context.
