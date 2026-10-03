# FilingScope RAG Quality Benchmark

## Scope

This **controlled development benchmark of historical frozen answers and
evidence** reports the six version-1 metrics in the [native evaluation
protocol](EVALUATION_NATIVE_PROTOCOL.md). It does not measure the current live
application or general SEC QA accuracy. There is no overall score. Agent
terminal evaluation's 21 structural/operational entries are a separate surface.

The entire previously selected **priority `<=2`, N=30** cohort is retained,
including three out-of-corpus cases. Selection follows the existing official
benchmark policy, not the resulting scores. No case is excluded or cherry-picked.

## Benchmark identity

| Field | Identity |
|---|---|
| Benchmark | `filingscope-rag-public-v1` |
| Protocol / metrics | `native-evaluation` v1; six metric versions = 1 |
| Dataset | `evaluation-test-set` / `evaluation-test-set-v1`; 30 cases from the frozen historical 52-case registry |
| Native evaluator source | `4fe40cc8e03684d149667c1961d51d932a65e60f`; implementation unchanged by this publication |
| Compatible historical verification/rendering source | `5c582b50774757b948cf783be1dc206422838246` |
| Frozen context strategy | `selective_packed_v5_enumeration_candidate` |
| Historical generator / judge | Both `openai/gpt-oss-120b` through Groq |
| Provider usage for this publication | **Zero live generation calls; zero live judge calls** |

The protected official legacy result remains unchanged, SHA-256
`a5b3c16e43c44ea79199c525e6345acf837172d956d8b659e5a234dc4692a7ba`.
Its Phase-1 artifact fingerprint is
`sha256:1ad021ce72af2116f9b4f7ad780d5c6e809fd5a01e46d30d0ae4bfecd62599d9`.
The [engineering reference](ENGINEERING_REFERENCE.md#evaluation-results)
retains its historical promotion and meanings. This explicit native adaptation
does not promote a newer runtime or repeat that provider campaign.

Frozen API-006 dataset revision:
`sha256:b7d6c623cb168a23b2285d20e95197f514fbf521d3c993aa99178fb5918b24bd`.
It hashes the ordered full historical TestCase registry, not only the selected
30 cases. Later priority-3 label revisions change the current full-registry
digest; reproduction intentionally uses the packaged historical registry.

## Results

| Metric | Result | Computed / total | N/A | Unavailable |
|---|---:|---:|---:|---:|
| Faithfulness | 1.0000 | 30 / 30 | 0 | 0 |
| Answer relevancy | 0.9917 | 30 / 30 | 0 | 0 |
| Context precision | 0.7613 | 30 / 30 | 0 | 0 |
| Citation index validity | 1.0000 | 27 / 30 | 3 | 0 |
| Keyword recall proxy | 1.0000 | 24 / 30 | 6 | 0 |
| Fallback correctness | 1.0000 | 30 / 30 | 0 | 0 |

All aggregate statuses are `computed`. The first five use the mean of computed
per-case values; fallback uses the success rate. Native v1 aggregates unrounded
values in stable order and rounds only the final value to four decimals.
Unavailable and N/A cases never become zero or enter a denominator. Three
citation N/A cases contain no citation; six keyword N/A cases have no required
keywords. They remain in the 30-case cohort.

Perfect structural/proxy values need their scope: the historical packing policy
uses **required-keyword donor selection** for applicable fact, summary and
multi-hop contexts. The cohort is **not fully label-blind**, and keyword coverage
does not establish independent retrieval quality.

## Metric meaning

- **`native.faithfulness`:** existing judge estimate of answer claims grounded
  in the exact evidence; not deterministic claim verification.
- **`native.answer_relevancy`:** existing judge estimate of answer relevance
  against the question and authored ground truth.
- **`native.context_precision`:** existing judge estimate of useful retrieved
  chunks; not labelled retrieval Precision@K.
- **`native.citation_index_validity`:** fraction of `Source N` references with
  in-range indices; **not factual citation support**.
- **`native.keyword_recall_proxy`:** fraction of explicit required keywords in
  rendered evidence; **not Recall@K or semantic answer correctness**.
- **`native.fallback_correctness`:** agreement between the repository's fallback
  phrase check and the explicit expectation, across all 30 labelled cases.

None is a confidence probability. The legacy `overall_judge_average` is not a
seventh metric and is omitted.

## Dataset composition

| Dimension | Known cohort labels |
|---|---|
| Priorities | 18 priority 1; 12 priority 2 |
| Categories | Fact lookup 8; summary 6; enumeration 4; comparative 6; multi-hop 3; out-of-corpus 3 |
| Ticker labels | AAPL 7; MSFT 7; AMZN 7; unscoped 9 |
| Section filters | Unrestricted 17; MD&A 5; risk factors 6; business 2 |
| Ground truth / keyword labels | 30 nonempty ground truths; 24 nonempty keyword lists |
| Fallback / decomposition | 30 explicit fallback labels, 3 true; 10 decomposition expectations |
| Language | No language field; questions are authored in English |
| Rendered evidence captions | 71 source blocks; 9 ticker captions; Business, Financial Statements, Financial Table, MD&A and Risk Factors |

The answerable scope primarily concerns Apple, Microsoft and Amazon. Negative
cases request Netflix, Disney and Shopify. Section filters describe requests,
not retrieved-section distribution. Rendered captions are metadata, not full
filing-coverage claims. Frozen Phase-1 candidates also contain
donor evidence from additional companies. Public inputs preserve the actual
selected evidence, rather than claiming it came only from the three scoped
companies. English questions do not establish Vietnamese quality. The broader
52-case registry and configured 50-company corpus are not the evaluated population.

## Method and provenance

Inventory found frozen Phase-1/Phase-2 artifacts, legacy checkpoint campaigns
and the protected complete N=30 result; no existing native publication history
was present. Priority-3 and later non-official/sentinel/bilingual experiments
are not merged into this cohort. The two-company/four-chunk demo fixture is not
quality evidence.

Before adaptation, all **30 generation bindings**, **30 individual judge
bindings**, answers and numeric scores matched the promoted summary. Each exact
rendered context matched its original admission-receipt hash. Historical source
was used to validate its schema-5 generation binding; current schema-6 generation
bindings were not substituted. The exact artifact hashes and original individual
judge bindings are retained in the curated inputs.

The small [reproduction module](../scripts/reproduce_rag_public_benchmark.py)
calls `preflight_native_cases` and `build_native_report`; it does not reimplement
metric formulas or invoke generation/judging. Preflight found 30 bound judge
cases, zero missing judge cases and zero required provider attempts or retries.
The native publication's batch judge binding hashes the verified case IDs,
answer/context hashes, original per-call bindings and numeric scores. It is an
explicit adapter binding, not an original provider-call binding or fresh judgment.

Public artifacts:

- [Curated frozen inputs](evaluation/filingscope-rag-public-v1.inputs.json): final
  answer text, exact public SEC evidence, already-public dataset labels, finite
  judge scores and safe provenance. No raw API envelope, prompt, rationale,
  credential, private path or hidden reasoning is included.
- [Native publication](evaluation/filingscope-rag-public-v1.native.json): content-free
  case IDs, context hashes, metric definitions/results, denominators and bindings.

Input file SHA-256 (UTF-8, LF-normalized for cross-platform Git checkouts):
`ccdba7451775a413fc751109fbefdc2af0338a8295284199e3b26055168b7eea`.
Native report digest:
`sha256:e5c004215a69b5c4094a35467569d3c76f88e17803400881e728fc68c32c9d16`.
The publication envelope has an operator-supplied UTC timestamp; the native report
has no timestamp and is byte-deterministic. Digests provide integrity, not signatures.

## Limitations

This small, development-selected historical cohort is useful for a bounded
portfolio claim, but is not representative of general SEC research. Contexts
were selected with label assistance. Reusing frozen outputs does not test fresh
generation or judge variability. Generator and judge use the same model; judge
estimates inherit rubric, model and authored-label limitations. Citation and
keyword checks can be perfect while an answer remains unsuitable. Fallback
checking recognizes the defined phrase, not every semantically appropriate refusal.

Evidence identifiers are limited to the recorded chunk/citation metadata;
missing accession/source URL/document identity is not invented. This is not
financial advice, financial-correctness certification, production SLA or a
guarantee of accurate answers. Native completeness establishes prerequisite
coverage, not a quality grade or automatic official admission.

## Reproduction

From a checkout with the declared Python dependencies already installed:

```powershell
.venv\Scripts\python.exe -m scripts.reproduce_rag_public_benchmark --check
```

The command blocks network access before imports, requires the admitted input
hash, checks the entire cohort and original per-call judge bindings, runs native
preflight/scoring, validates the native schema/digest and compares the committed
publication. No `.env`, local corpus/index, API key or historical Git snapshot is
required. It **recomputes metrics over frozen inputs**, not retrieval, answers or
judge estimates.

For an explicit local output, add `--output` with a fresh diagnostic path. Two
provider-free reruns produced identical canonical report bytes and the digest
above. Product behavior, providers, dependencies, lockfiles, migrations and CI
are unchanged.
