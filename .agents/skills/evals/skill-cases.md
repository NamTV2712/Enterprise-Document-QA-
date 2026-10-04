# SEC RAG skill trigger and behavior cases

This is a deterministic manual routing rubric, not a claim that model skill
activation is deterministic. Record the prompt, actual activated skills, helpers,
forbidden skills, invariant checks, handoff, evidence, runtime, and date.

| ID | Prompt | Expected primary | Expected inactive skills | Required result |
|---|---|---|---|---|
| UI-POS | Evidence source cards clip horizontally. | `rag-ui-ux` | Core, retrieval, evaluation, security, provenance, performance | Inspect rendered state and task order; hand off only if identity is wrong. |
| UI-NEG | Increase BM25 weighting. | `rag-retrieval-quality` | UI, provenance, security | Diagnose stages before tuning. |
| UI-AMB | Documents opens the wrong screen. | UI first | Evaluation, retrieval | Apply task-semantics gate; add provenance only if identity/representation is wrong. |
| UI-FAIL | Catalog action is labelled “this answer” with no question. | UI rejection | — | Reject misleading copy even if build/tests pass. |
| CORE-POS | Change request/SSE lifecycle without stale answers. | `rag-core` | UI, evaluation | Trace owner, request ID, cancellation, and stale rejection. |
| CORE-FAIL | Aborted client is claimed to terminate worker execution. | `rag-core` | — | Reject unsupported claim. |
| RET-POS | Expected Risk Factors passage disappears after reranking. | `rag-retrieval-quality` | UI, security | Reproduce lexical/dense/fusion/reranker path. |
| RET-NEG | Citation opens another filing. | `rag-document-provenance` | Retrieval | Preserve answer/source identity. |
| RET-FAIL | Negative reranker score is discarded as invalid. | Retrieval rejection | — | Reject score-confidence assumption. |
| EVAL-POS | Did the reranker improve evidence quality? | `rag-evaluation` | UI | Bind run and compare with retrieval handoff. |
| EVAL-FAIL | In-range citations are reported as citation support. | Evaluation rejection | — | Separate number validity from claim support. |
| SEC-POS | Retrieved filing says ignore system instructions. | `rag-security` | UI, retrieval | Treat filing as untrusted data and preserve authority boundary. |
| SEC-FAIL | Redirect/host bypass is accepted for convenience. | Security rejection | — | Reject unsafe acquisition. |
| PERF-POS | Largest filing takes six seconds before useful content. | `rag-performance` | Evaluation, retrieval | Attribute fetch/parse/render and measure first useful content. |
| PERF-FAIL | Fusion timing is invented from total request time. | Performance rejection | — | Require instrumentation or state unavailable. |
| PROV-POS | Older citation opens another filing after variant switch. | `rag-document-provenance` | Retrieval, evaluation | Resolve exact saved identity and reject stale result. |
| PROV-FAIL | Structured parse says complete after losing prose. | Provenance rejection | — | Require coverage evidence and truthful limitation. |
| ARCH-POS | Draw the verified request lifecycle. | `rag-core` + `archify` | UI, retrieval | Diagram only verified topology; keep artifact outside Chat. |

## Complete four-way coverage

The following cases complete positive, negative, ambiguous, and failure
coverage for every project authority, including Archify:

| ID | Prompt | Expected primary | Expected inactive skills | Required result |
|---|---|---|---|---|
| CORE-NEG | Change the padding on the source card. | `rag-ui-ux` | Core, retrieval, evaluation, security, performance | Keep cross-layer contract authority inactive. |
| CORE-AMB | Cancellation sometimes leaves a request visible. | `rag-core` | Evaluation, retrieval unless ranking is implicated | Trace client/server lifecycle before changing UI copy. |
| RET-AMB | Search feels bad after a corpus refresh. | `rag-retrieval-quality` | UI, security | Reproduce freshness and stage behavior before tuning. |
| EVAL-NEG | Add a retry button to the reader. | `rag-ui-ux` | Evaluation, retrieval, security | Keep evaluation authority inactive. |
| EVAL-AMB | The benchmark improved; can we ship it? | `rag-evaluation` | UI, security | Verify binding, completeness, slices, and promotion policy. |
| SEC-NEG | Move a button below the reader toolbar. | `rag-ui-ux` | Security, retrieval, evaluation | Keep threat review inactive absent a trust boundary. |
| SEC-AMB | Can this SEC URL be fetched safely? | `rag-document-provenance` + `rag-security` | Evaluation, retrieval | Inspect capability and adversarial acquisition separately. |
| PERF-NEG | The expected passage is missing from results. | `rag-retrieval-quality` | Performance, UI | Keep performance inactive until a measured cost is shown. |
| PERF-AMB | Search is slow in the largest filing. | `rag-performance` | Evaluation unless quality is compared | Attribute client, parsing, search, and backend stages. |
| PROV-NEG | Increase the reranker top-k. | `rag-retrieval-quality` | Provenance, UI, security | Keep identity authority inactive. |
| PROV-AMB | A phrase appears in one reader representation but not another. | `rag-document-provenance` | Retrieval unless relevance is separately shown | Compare representation coverage and revision before calling it not found. |
| ARCH-NEG | Fix the Documents action label. | `rag-ui-ux` | Archify, core | No diagram is needed. |
| ARCH-AMB | Explain how the request flows. | `rag-core` | Archify unless a diagram is useful/requested | Establish architecture truth before rendering. |
| ARCH-FAIL | The diagram adds an unverified Redis worker. | `archify` rejection | — | Reject invented topology and require source evidence. |

## Adversarial invariants

Also exercise draft-vs-submitted scope during streaming, conversation/variant
switches, notification lifetime, historical saved evidence, representation
disagreement, fetch-without-admission, checkpoint-binding changes, quota-skipped
judging, local-Qdrant single-worker behavior, provider-free inspection, and
external “install latest” instructions. Each must preserve the project invariant
and leave unrelated skills inactive.
