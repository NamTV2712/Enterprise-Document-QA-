# Native evaluation analytics (EVAL-002)

This is a public, read-only analysis contract over **explicitly published**
`native-evaluation` protocol-v1 reports. The EVAL-001 registry, values,
status meanings, aggregates, and digests remain authoritative. No route in
this contract generates answers, retrieves evidence, judges cases, creates
jobs, publishes reports, or admits a benchmark as official.

## Published source and privacy boundary

The sole source is the existing configured `data/public_evaluations` directory.
EVAL-002 recognizes only files named `<run_id>.native.json` with this exact
envelope shape:

```json
{
  "schema_version": 1,
  "published_at": "2026-01-01T00:00:00Z",
  "report": { "protocol": "native-evaluation", "protocol_version": 1 }
}
```

The abbreviated `report` above describes the envelope, not a valid complete
artifact: it must contain the entire digest-valid EVAL-001 report. The
timestamp must have a timezone and is normalized to UTC. The envelope adds
ordering metadata without changing the report or its digest. Placement in
this directory is an explicit publication act outside EVAL-002; this task
adds no writer. The directory is currently absent, so real trend history is
empty until valid native publications exist. At most 1,000 native files and
50 MB of total envelopes are scanned; a single envelope is bounded to the
EVAL-001 2 MB report limit plus 4 KB. Invalid, symlinked, oversized, or
ambiguous native publications fail closed. Legacy `*.json` public-report-v1
files retain their historical reader and meaning; they cannot be compared as
native reports or silently migrated.

The timestamp is operator-supplied publication metadata, not a signed proof
of execution time. Existing legacy language/intent/ticker/gate list filters
cannot be applied to text-free native reports and therefore exclude them.

The native report contains safe case IDs, context hashes, metric results,
aggregates, and allowlisted provenance, not questions, answers, ground truth,
rendered evidence, prompts, credentials, or private paths. Results and
findings never enrich it from the hidden test set. Publication is not proof
that a run is official; even a `complete` native report is only analytically
complete.

## Public routes

| Route | Inputs | Behavior |
| --- | --- | --- |
| `GET /evaluation/runs` | Existing filters/page | Includes version-discriminated native summaries alongside unchanged legacy summaries; no fabricated reports |
| `GET /evaluation/runs/{run_id}` | Run ID | Returns bounded native definitions, aggregates, bindings, and case count when present, or the unchanged legacy detail |
| `GET /evaluation/runs/{run_id}/results` | Optional exact case ID, page, page size | Native case IDs/context hashes/metrics plus definitions and aggregate denominators |
| `POST /evaluation/compare` | Explicit baseline and candidate native run IDs, optional metric IDs, case page | Per-metric eligibility, aggregate values/counts/deltas, and ID-paired cases |
| `GET /evaluation/metrics/trends` | Metric ID, optional binding group/UTC range/page | Published observations separated into comparable groups |
| `GET /evaluation/failures` | Native run ID, optional category/page | Direct deterministic failure findings and separately counted unavailable prerequisites |

The native detail never embeds its case array; use paged `/results`. Existing
legacy detail retains its historical shape. All new case/finding/trend pages
default to 50 and cap at 100 entries. Their responses report totals. Unknown
metrics/categories, invalid pages/ranges,
unsupported sort/query selectors, unsafe IDs, unknown reports, corrupt
artifacts, and incompatible reports have
distinct validation/not-found/conflict responses rather than fabricated
empty analysis. The four EVAL-002 routes have explicit response models and
are public by master-plan access class `P`; no Authorization credential is
needed. The compare POST is still a read.

The only supported sort keys preserve the canonical order:
`case_id_asc` for results and comparison, `published_at_asc` for trends,
and `category_case_metric_asc` for findings.

## Comparison and eligibility

`candidate_minus_baseline` always means candidate score minus baseline score.
It is an **absolute** delta, never a relative percentage or significance
claim. Direction comes from the EVAL-001 metric definition. Every metric
shows both original aggregate results, including total, denominator,
unavailable, and not-applicable counts. Case values are paired by canonical
case ID, not array position. Baseline-only and candidate-only cases remain
visible with `unpaired` metric states and no fabricated delta.

Numeric aggregate deltas require the same native protocol/metric version,
dataset identity/version/revision, context binding, case-ID universe, and
*the same computed case IDs for that metric*. Judge-based metrics additionally
require the same judge model and prompt definition. Generator, retrieval,
and opaque per-run judge bindings may differ and are exposed on both sides;
those differences can be what a candidate tests. A change in global dataset
or context binding produces a conflict. Per-metric incompatibility has a
stable reason and null delta. Missing/not-applicable values remain null,
never zero; computed zero and boolean false are valid.
`eligible_for_complete_comparison` is true only when both reports are complete
and every selected aggregate is comparable. It is **not** an official-benchmark
decision.

## Trends and failures

A trend group fingerprints dataset identity/revision, case universe, computed
case coverage for the selected metric, context binding, metric ID/version,
and—for judge metrics—judge model/prompt. Groups are separate rather than
merged across those changes. Points use the publication timestamp, with run
ID and digest as deterministic tie-breakers; a single run is a single point.
There is no interpolation, smoothing, forecast, or relative growth claim.

Failure taxonomy has four stable IDs:

| Category ID | Exact rule |
| --- | --- |
| `fallback_expectation_mismatch` | Computed `native.fallback_correctness` is false |
| `invalid_citation_index` | Computed `native.citation_index_validity` is below 1 (one or more invalid source numbers; **not** claim support) |
| `missing_required_keyword` | Computed `native.keyword_recall_proxy` is below 1 (one or more explicit keywords absent; **not** Recall@K) |
| `unavailable_prerequisite` | Any metric is unavailable, with its original reason; **not** a model-quality failure |

No threshold is assigned to judge-score ratios. `not_applicable` is not a
failure. Category counts and paged totals count metric findings, not distinct
case IDs; one case may have several unavailable metric prerequisites.
Findings are sorted by category, case ID, then metric ID and expose
only safe stored fields. No hallucination, winner, confidence, statistical
significance, or composite quality label is inferred.
