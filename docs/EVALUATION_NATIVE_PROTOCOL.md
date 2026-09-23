# Native evaluation protocol v1

EVAL-001 establishes a provider-free domain protocol. It does not run an
evaluation, call a judge, publish a report, or decide that a run is official.
The existing Phase 2 runner and public-report-v1 files retain their historical
formats and meanings. Future evaluation jobs and public comparison services
must opt into this protocol explicitly; they must not relabel legacy scores.

## Metric identity and meaning

Each metric has a namespaced `metric_id`, semantic `metric_version=1`, display
label, value kind, aggregate kind, direction, bounds, source, and required
inputs. `GET /evaluation/metrics` returns the six definitions and capability
flags without a credential or provider call. A future change in scoring
meaning requires a metric-version change; changing the protocol structure
requires a protocol-version change.

| Metric ID | Per-case meaning | Aggregate | Prerequisite |
| --- | --- | --- | --- |
| `native.faithfulness` | Existing native judge estimate of grounded answer claims, ratio `[0,1]` | Mean | Bound precomputed judge score, answer, exact rendered evidence, ground truth |
| `native.answer_relevancy` | Existing native judge estimate of answer relevance against question and ground truth, ratio `[0,1]` | Mean | Same judge prerequisites |
| `native.context_precision` | Existing native judge estimate of useful retrieved chunks, ratio `[0,1]` | Mean | Same judge prerequisites |
| `native.citation_index_validity` | Fraction of `Source N` references with in-range indices, ratio `[0,1]`; **not claim support** | Mean | Answer and exact rendered evidence |
| `native.keyword_recall_proxy` | Fraction of explicitly required keywords present in rendered evidence, ratio `[0,1]`; **not Recall@K** | Mean | Exact rendered evidence and nonempty required-keyword list |
| `native.fallback_correctness` | Boolean agreement between the existing fallback phrase check and `expects_fallback` | Success rate `[0,1]` | Answer and explicit fallback expectation |

All six have `higher_is_better` direction. None is a confidence or probability
claim. No metric threshold, composite pass/fail, or cross-metric weighting is
defined. In particular, the legacy `overall_judge_average` is **not** a
seventh canonical metric. Judge scores are accepted only as complete,
finite `[0,1]` values with the exact three canonical IDs and a judge binding;
the protocol never invokes Groq or another provider to create them.

## Case input and results

`NativeCaseInput` is private and bounded. It carries a stable caller-supplied
case ID, answer, exact rendered context, ground truth, optional keyword and
fallback labels, and optional precomputed judge scores. Completed generation
and judge scores must carry their per-case bindings; supplied generation and
judge evidence SHA-256 values must both match the exact rendered context.
The report retains only the case ID, a context SHA-256, and metric results—not
the question, answer, ground truth, evidence text, prompt, or secrets.
`preflight_native_cases` validates frozen inputs and reports how many cases
already carry bound scores versus how many still require externally budgeted
judging. It promises only **zero calls by the protocol core**; EVAL-003 must
price actual judge attempts and retries before any execution.

Every per-case result is one of:

- `computed`: an actual finite score or, for fallback, a boolean. Numeric zero
  and boolean false are real computed values.
- `unavailable`: a missing generation, context, ground truth, or bound judge
  result prevents computation. `reason_code` identifies the prerequisite.
- `not_applicable`: no source citation, no required keyword, or no fallback
  expectation makes that metric inapplicable. It has no numeric value.

Neither unavailable nor not-applicable is coerced to zero. Malformed source
evidence, missing truth accompanying supplied judge scores, mixed bindings,
duplicate case IDs, non-finite scores, unsafe identifiers, and oversized
inputs are rejected as invalid input. Missing ground truth accompanying judge
scores and an empty set have distinct domain error types. The protocol accepts at most 5,000
cases and 2 MiB of serialized report data; an empty set is rejected.

## Aggregation and report

One aggregate per metric records `total_cases`, `denominator` (computed cases),
`unavailable_count`, and `not_applicable_count`. The denominator never includes
unavailable or not-applicable cases. The mean/success rate is calculated from
unrounded per-case values with a stable summation order and rounded only at
the final four-decimal report value, matching existing benchmark display
precision. A zero denominator produces `value=null` and either unavailable
or not-applicable status, never zero. Input case order cannot change the
canonical report: cases are sorted by case ID and metrics follow registry
order. Any unavailable result makes the report `incomplete`; `complete` is
not an official-benchmark admission decision.

`NativeReport` has `protocol="native-evaluation"` and `protocol_version=1`.
It contains a run ID, status, engine ID/version, API-006 dataset
identity/version/revision, generator model ID/fingerprint, generation prompt
fingerprint and binding, frozen retrieval/config, embedding and reranker
fingerprints, context binding, optional judge model/prompt/binding, six
definitions, case results, six aggregates, and a `sha256:` digest. The dataset revision uses the **same**
ordered-full-`TestCase` canonical JSON SHA-256 algorithm as API-006's
`evaluation-test-set`; selection of a subset does not mint a second dataset
identity. Per-case context hashes identify the evidence used without exposing
its content. The report carries no timestamp so identical bound inputs
serialize identically.

The digest covers the sorted-key, compact, UTF-8 canonical JSON payload
excluding the digest field, using `src.retrieval.canonical_json`. It is an
integrity/checkpoint fingerprint, **not** a signature or authorization grant.
The parser rejects unknown protocol versions, legacy/public-v1 payloads,
duplicate JSON keys or cases, malformed metric IDs/versions/status/value
pairs, inconsistent aggregates or completeness, and digest mismatches. It
distinguishes unsupported versions from corrupt reports with separate error
types. It does not reinterpret existing Phase 2 or public reports as native v1.

## Integration boundary

The existing public `/evaluation/runs` and `/evaluation/runs/{run_id}` routes
continue serving validated public-report-v1 artifacts unchanged. The new
`/evaluation/metrics` route exposes definitions only. EVAL-002 may consume
native reports for comparison after defining explicit publication/adaptation
and binding-eligibility rules. EVAL-003 may pass frozen generation/judge
records into `build_native_report` once it owns execution and budgets. EVAL-001
does not schedule jobs, write evaluation artifacts, select providers, or add
Ragas. Generation, deterministic checks, and judging must continue to use
the same rendered evidence; a changed renderer requires a changed binding.
