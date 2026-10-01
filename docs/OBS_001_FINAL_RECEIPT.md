# OBS-001 final receipt — Performance Attribution & Safe Observability

Date: 2026-10-01. Optional measurement extension; required roadmap,
Agent/provider, SCALE-001/002 and CRED-001 remain COMPLETE. SCALE-003 is NOT STARTED.
Runtime/campaign acceptance is complete. The exact documentation HEAD clean gate
and normal GitHub push are release closure gates, recorded with their literal
SHA/results in the closing report.

## Identity and environment

- Branch: `main`; starting local/upstream/remote SHA:
  `6faacd5bfdd4259e7cb6d9504943ca392aa69f4f`.
- Measured runtime and harness SHA:
  **`6ea9d534ba55f24fc3f094095eefede74f526bf1`**.
- Final HEAD: the latest documentation commit updating this receipt. Resolve with
  `git log -1 --format=%H -- docs/OBS_001_FINAL_RECEIPT.md`; the closing report
  supplies the literal final/local/upstream/remote SHA after exact-HEAD validation.
- Protocol **obs-001-attribution-v1**, workload/statistics authority
  **scale-002-benchmark-v1**. Runtime/harness committed and tracked-clean before
  the accepted campaign. No mixed runtime/checkpoint populations.
- Windows 10.0.26300; Python 3.12.7; SQLite 3.45.3; 24 logical CPUs;
  16,890,322,944 bytes RAM. No username/hostname/process identity/path dimension.
- FastAPI 0.115.0, Starlette 0.38.6, HTTPX 0.28.1, Uvicorn 0.32.0,
  Groq 1.5.0, Pydantic 2.13.4. Same-process loopback TCP server/client.
- SCALE harness SHA256:
  `a96d5789178885cc3731ff24f7be4f78e36b93771d9ba2c790fe97d28bd55ea2`.
- OBS harness/core SHA256:
  `01b3122c1dafabcb58db1aeb9ddb62f3ee73f49033b23984a1844f6b1628c591`.

## Model, safety and compatibility

The [protocol](OBS_001_ATTRIBUTION_PROTOCOL.md) is the authoritative phase taxonomy
and timing definition. Closed 32 phases, 11 operations, four outcomes; strict
typed finite monotonic intervals and summaries. Spans are inclusive and may nest.
Never add nested phase durations/percentiles. API remainder is total minus the
union of clipped observed intervals, only without drops. Framework/thread-pool/
response scheduling remains in that remainder; ingress before ASGI is outside
server total. Total extends through the final awaited body send, including finite
SSE, and does not measure physical delivery.

Bounded 128 API/512 worker spans, 64 groups, 16,384 UTF-8 summary bytes, 24-hour
duration maximum. Deferred DB observations are bounded and emitted after the
existing outer reentrant lock releases. No new product serialization lock or
changed acquisition order. No telemetry lock wraps slow work. Context cleanup
covers exceptions/cancellation and ignores late closed-trace observations.

No prompts/goals/evidence/answers/provider payloads/headers/SQL/exceptions/rationale/
credentials or machine identities are captured. Safe existing request/job IDs and
closed route templates correlate summaries. Existing product frozen goals/final
answers remain legitimate product fields: OBS does not erase them or duplicate
them into performance records. Six sentinels verify secret exclusion across API,
worker, Agent, provider, tools, evaluation, SSE, durable state, events, logs and
analytics; content sentinels are excluded from attribution and events/logs.

`ENABLE_PERFORMANCE_ATTRIBUTION=false` by default. Local authorized requests only;
public/unauthorized requests cannot open the store for measurement. Durable API
summaries use server-random one-in-ten selection, independent of client IDs;
successful worker cycles are all selected. Analytics labels the sampled record
population `api_one_in_ten_worker_all`; it does not estimate all-request counts.
Benchmark capture is complete for every measured request/worker cycle. Persistence
uses the initialized DATA-005 authority, not another database or raw span queue.
Existing `telemetry_events`, record schema 1, SQLite v7, 30-day retention/pruning.
Protected summary aggregation reads at most 10,000 terminal summaries and reports
truncation. Existing request/quality/log/public-metrics populations stay separate.
Empty/error worker polls do not create durable rows. Abrupt shutdown can lose a
partial performance trace; durable product interruption/recovery stays authoritative.

Defaults remain **workers 2 / poll 500ms / grace 5000ms**. Agent decisions remain
one HTTP attempt, `max_retries=0`, no fallback rotation, historical `key5_only`
resolves primary only. Generator retains primary plus optional fallback and
bounded 429 failover. Native evaluation remains provider-free with 21 unchanged
metrics and identical report digest semantics. No new tool, route, migration,
dependency, lockfile, production frontend, quality metric or production SLA.

## Accepted fixed campaign

**16 scenarios / 48 trials**, three measured trials each; four warmups per trial
excluded. Six anchors each disabled/enabled, plus four enabled low-load poll
settings. Actual SDK protocol uses mocked external HTTP and synthetic SEC fixtures;
no live Groq/SEC/corpus network, private environment or `data/` regeneration.
Every trial reopens its same SQLite database at v7 with integrity `ok` and zero
active rows after shutdown. Existing SCALE-002 correctness/statistical semantics
are retained. OBS has a bounded 120-240s workload deadline plus up to 90s startup/
shutdown allowance, default campaign deadline 1800s. Failed checkpoints stay
incomplete and CLI failures emit a fixed safe message.

Nearest-rank p50/p95/p99 require 2/20/100 samples. Unavailable is null (shown as
`—` below). Tables are medians of per-trial statistics, never pooled percentiles.
Counts are per-trial populations. Signed `client_observed_minus_server` pairs the
same request: it includes client/ingress/shared-loop/scheduling costs and is
**not network latency**. SSE commit-to-frame delivery and finite server batch
processing use different windows; their percentiles must not be subtracted.

All correctness counters are zero: ownership/capacity, exact provider decision
counts, lifecycle/events, no terminal mutation, no lost/duplicate jobs, SQLite
busy/error/integrity, SSE order/duplicates/missing/resume. Peak active workers are
2 for research/mixed, 1 for the one-job SSE workload; sampled task count never
exceeds 2. Admission intentionally leaves queued rows; reads execute only warmups.
Measured job rows: 1,836 (1,200 queued admission, 636 succeeded). Requests: 10,790.
Enabled capture: **6,020 traces / 163,654 spans**, all outcomes completed;
rejected/failed/cancelled counts zero. **982 selected durable summaries / 3,089,300
summary JSON bytes**. Missing/dropped observations zero. Raw reports/logs/databases
are ignored; no raw trace dump is committed.

### Anchors: client and authoritative job timing

Two configured workers; all anchors poll 500ms. Admission/read have 200 operations, research 20, mixed 25, SSE 25 subscribers observing one job. On/off each have three trials. Research client requests include create/result/evaluation. Mixed adds detail/list/SSE/resume. SSE request totals include repeated finite batches.

| Scenario | Timing | Req/s | Jobs/s | Client p50 | Client p95 | Client p99 | Queue p95 | Service p95 | E2E p95 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| admission 50 / 0ms | off | 64.908 | — | 401.468 | 2417.085 | 2731.676 | — | — | — |
| admission 50 / 0ms | on | 57.679 | — | 522.638 | 2362.424 | 2971.903 | — | — | — |
| read 50 / 0ms | off | 66.963 | — | 548.858 | 1681.984 | 2327.349 | — | — | — |
| read 50 / 0ms | on | 62.751 | — | 577.466 | 1797.731 | 2422.838 | — | — | — |
| research 10 / 0ms | off | 21.797 | 7.547 | 100.205 | 174.134 | — | 1212.716 | 315.341 | 1405.944 |
| research 10 / 0ms | on | 22.098 | 7.563 | 77.465 | 133.890 | — | 1145.784 | 199.065 | 1297.877 |
| research 10 / 250ms | off | 6.548 | 2.196 | 33.788 | 121.577 | — | 3916.079 | 914.428 | 4716.307 |
| research 10 / 250ms | on | 6.589 | 2.212 | 31.909 | 126.140 | — | 3658.011 | 857.056 | 4539.923 |
| mixed 25 / 250ms | off | 57.644 | 1.480 | 162.016 | 391.839 | 548.392 | 15215.665 | 1823.515 | 15994.023 |
| mixed 25 / 250ms | on | 51.174 | 1.267 | 183.239 | 501.473 | 673.440 | 17633.700 | 2217.795 | 18537.072 |
| sse 25 / 250ms | off | 68.049 | 0.372 | 251.365 | 463.911 | 550.309 | — | — | — |
| sse 25 / 250ms | on | 59.808 | 0.348 | 292.358 | 506.959 | 578.206 | — | — | — |

### API server and paired client attribution (enabled)

Every number below is milliseconds; counts are per trial. Routes: create/list `/agent/runs`; detail `/agent/runs/{run_id}`; result `/agent/runs/{run_id}/results`; evaluation `/agent/runs/{run_id}/evaluation`. SSE batch/resume both use `/agent/runs/{run_id}/events`. No raw URL or query dimension.

| Scenario / endpoint | Window | Count | p50 | p95 | p99 | Max |
| --- | --- | --- | --- | --- | --- | --- |
| admission 50 / 0ms / create | ASGI total | 200 each | 195.912 | 421.268 | 469.679 | 473.652 |
| admission 50 / 0ms / create | paired client − server | 200 each | 130.899 | 2166.959 | 2805.278 | 3046.885 |
| admission 50 / 0ms / create | valid server remainder | 200 each | 176.701 | 347.114 | 452.179 | 459.796 |
| read 50 / 0ms / detail | ASGI total | 50 each | 174.976 | 331.869 | — | 402.424 |
| read 50 / 0ms / detail | paired client − server | 50 each | 348.411 | 1322.750 | — | 1824.305 |
| read 50 / 0ms / detail | valid server remainder | 50 each | 129.587 | 271.656 | — | 314.510 |
| read 50 / 0ms / evaluation | ASGI total | 50 each | 232.419 | 392.651 | — | 421.403 |
| read 50 / 0ms / evaluation | paired client − server | 50 each | 342.885 | 1862.431 | — | 2767.741 |
| read 50 / 0ms / evaluation | valid server remainder | 50 each | 176.011 | 300.096 | — | 347.157 |
| read 50 / 0ms / list | ASGI total | 50 each | 199.299 | 331.077 | — | 402.207 |
| read 50 / 0ms / list | paired client − server | 50 each | 352.569 | 1585.457 | — | 2098.146 |
| read 50 / 0ms / list | valid server remainder | 50 each | 157.175 | 268.607 | — | 340.644 |
| read 50 / 0ms / result | ASGI total | 50 each | 200.683 | 331.103 | — | 363.925 |
| read 50 / 0ms / result | paired client − server | 50 each | 277.371 | 1355.154 | — | 2083.051 |
| read 50 / 0ms / result | valid server remainder | 50 each | 149.835 | 303.596 | — | 340.385 |
| research 10 / 0ms / create | ASGI total | 20 each | 79.986 | 104.216 | — | 116.383 |
| research 10 / 0ms / create | paired client − server | 20 each | 11.411 | 33.909 | — | 46.602 |
| research 10 / 0ms / create | valid server remainder | 20 each | 55.607 | 78.771 | — | 98.702 |
| research 10 / 0ms / evaluation | ASGI total | 20 each | 85.439 | 117.740 | — | 137.626 |
| research 10 / 0ms / evaluation | paired client − server | 20 each | 2.040 | 29.775 | — | 37.163 |
| research 10 / 0ms / evaluation | valid server remainder | 20 each | 39.713 | 65.113 | — | 82.316 |
| research 10 / 0ms / result | ASGI total | 20 each | 39.604 | 95.395 | — | 104.988 |
| research 10 / 0ms / result | paired client − server | 20 each | 6.972 | 25.808 | — | 28.209 |
| research 10 / 0ms / result | valid server remainder | 20 each | 23.648 | 45.501 | — | 83.525 |
| research 10 / 250ms / create | ASGI total | 20 each | 42.883 | 105.866 | — | 120.016 |
| research 10 / 250ms / create | paired client − server | 20 each | 1.818 | 32.934 | — | 49.563 |
| research 10 / 250ms / create | valid server remainder | 20 each | 22.965 | 82.569 | — | 101.826 |
| research 10 / 250ms / evaluation | ASGI total | 20 each | 38.633 | 75.889 | — | 79.848 |
| research 10 / 250ms / evaluation | paired client − server | 20 each | 1.141 | 1.609 | — | 1.700 |
| research 10 / 250ms / evaluation | valid server remainder | 20 each | 3.788 | 25.011 | — | 30.202 |
| research 10 / 250ms / result | ASGI total | 20 each | 12.624 | 54.753 | — | 65.287 |
| research 10 / 250ms / result | paired client − server | 20 each | 1.455 | 2.577 | — | 14.241 |
| research 10 / 250ms / result | valid server remainder | 20 each | 1.221 | 18.500 | — | 24.051 |
| mixed 25 / 250ms / create | ASGI total | 25 each | 225.202 | 296.429 | — | 310.674 |
| mixed 25 / 250ms / create | paired client − server | 25 each | 108.336 | 221.713 | — | 236.366 |
| mixed 25 / 250ms / create | valid server remainder | 25 each | 201.336 | 280.071 | — | 285.191 |
| mixed 25 / 250ms / detail | ASGI total | 25 each | 233.658 | 515.652 | — | 545.889 |
| mixed 25 / 250ms / detail | paired client − server | 25 each | 23.532 | 54.106 | — | 55.340 |
| mixed 25 / 250ms / detail | valid server remainder | 25 each | 9.011 | 144.454 | — | 367.272 |
| mixed 25 / 250ms / evaluation | ASGI total | 25 each | 96.052 | 344.758 | — | 363.257 |
| mixed 25 / 250ms / evaluation | paired client − server | 25 each | 3.321 | 13.847 | — | 25.023 |
| mixed 25 / 250ms / evaluation | valid server remainder | 25 each | 12.408 | 85.513 | — | 123.447 |
| mixed 25 / 250ms / list | ASGI total | 25 each | 511.448 | 561.911 | — | 564.349 |
| mixed 25 / 250ms / list | paired client − server | 25 each | 54.097 | 159.864 | — | 187.936 |
| mixed 25 / 250ms / list | valid server remainder | 25 each | 184.655 | 391.960 | — | 413.039 |
| mixed 25 / 250ms / result | ASGI total | 25 each | 149.348 | 389.692 | — | 446.228 |
| mixed 25 / 250ms / result | paired client − server | 25 each | 2.170 | 5.758 | — | 6.257 |
| mixed 25 / 250ms / result | valid server remainder | 25 each | 3.263 | 139.333 | — | 182.300 |
| mixed 25 / 250ms / sse_batch | ASGI total | 874/850/930 | 161.961 | 455.514 | 621.038 | 714.809 |
| mixed 25 / 250ms / sse_batch | paired client − server | 874/850/930 | 6.347 | 50.959 | 118.750 | 233.572 |
| mixed 25 / 250ms / sse_batch | valid server remainder | 874/850/930 | 8.172 | 210.672 | 323.696 | 398.203 |
| mixed 25 / 250ms / sse_resume | ASGI total | 25 each | 148.375 | 355.269 | — | 582.013 |
| mixed 25 / 250ms / sse_resume | paired client − server | 25 each | 1.518 | 5.800 | — | 7.094 |
| mixed 25 / 250ms / sse_resume | valid server remainder | 25 each | 5.581 | 228.106 | — | 269.015 |
| sse 25 / 250ms / create | ASGI total | 1 each | — | — | — | 11.835 |
| sse 25 / 250ms / create | paired client − server | 1 each | — | — | — | 1.385 |
| sse 25 / 250ms / create | valid server remainder | 1 each | — | — | — | 1.303 |
| sse 25 / 250ms / sse_batch | ASGI total | 205/193/202 | 275.581 | 506.262 | 606.534 | 608.111 |
| sse 25 / 250ms / sse_batch | paired client − server | 205/193/202 | 6.512 | 46.479 | 53.107 | 247.719 |
| sse 25 / 250ms / sse_batch | valid server remainder | 205/193/202 | 7.067 | 225.753 | 297.941 | 301.865 |
| sse 25 / 250ms / sse_resume | ASGI total | 25 each | 276.499 | 334.745 | — | 334.748 |
| sse 25 / 250ms / sse_resume | paired client − server | 25 each | 1.361 | 2.134 | — | 3.023 |
| sse 25 / 250ms / sse_resume | valid server remainder | 25 each | 3.159 | 13.134 | — | 30.779 |

### Representative inclusive phase timings (enabled)

All sampled span outcomes in these tables are completed; failed/rejected/cancelled = 0. These are successful fixture populations, not failure latency distributions. Full phase names and operation/source/route define each population; do not add these nested rows. Max is the median of per-trial maxima.

| Population | Phase / operation | Count | p50 | p95 | p99 | Max |
| --- | --- | --- | --- | --- | --- | --- |
| admission 50 / 0ms / api /agent/runs | api.access / none | 200 each | 0.044 | 0.056 | 0.068 | 0.102 |
| admission 50 / 0ms / api /agent/runs | api.validation / none | 200 each | 0.030 | 0.037 | 0.056 | 0.081 |
| admission 50 / 0ms / api /agent/runs | api.freeze / none | 200 each | 0.070 | 0.086 | 0.105 | 0.121 |
| admission 50 / 0ms / api /agent/runs | api.admission / none | 200 each | 6.634 | 11.460 | 123.001 | 223.521 |
| admission 50 / 0ms / api /agent/runs | api.service_init / none | 200 each | 10.893 | 16.221 | 20.378 | 232.237 |
| admission 50 / 0ms / api /agent/runs | workspace.initialize / none | 200 each | 10.276 | 15.720 | 19.774 | 231.663 |
| admission 50 / 0ms / api /agent/runs | workspace.serialized_wait / none | 200 each | 2.632 | 8.274 | 12.371 | 222.407 |
| admission 50 / 0ms / api /agent/runs | workspace.serialized_wait / job_create | 200 each | 0.003 | 6.992 | 9.849 | 136.542 |
| admission 50 / 0ms / api /agent/runs | workspace.connection_open / job_create | 200 each | 1.444 | 2.832 | 3.511 | 6.538 |
| admission 50 / 0ms / api /agent/runs | workspace.critical_section / job_create | 200 each | 3.834 | 7.580 | 11.913 | 134.377 |
| admission 50 / 0ms / api /agent/runs | workspace.transaction / job_create | 200 each | 1.165 | 3.921 | 4.933 | 42.040 |
| read 50 / 0ms / api /agent/runs/{run_id} | api.read / none | 50 each | 1.593 | 10.097 | — | 20.116 |
| read 50 / 0ms / api /agent/runs/{run_id} | api.service_init / none | 50 each | 43.745 | 110.592 | — | 177.670 |
| read 50 / 0ms / api /agent/runs/{run_id} | workspace.initialize / none | 50 each | 43.068 | 110.092 | — | 176.978 |
| read 50 / 0ms / api /agent/runs/{run_id} | workspace.serialized_wait / none | 50 each | 30.730 | 86.332 | — | 103.845 |
| read 50 / 0ms / api /agent/runs/{run_id} | workspace.read / job_read | 50 each | 0.299 | 0.993 | — | 2.401 |
| read 50 / 0ms / api /agent/runs/{run_id}/evaluation | evaluation.compute / none | 50 each | 0.722 | 1.217 | — | 2.288 |
| research 10 / 250ms / worker worker.agent | worker.cycle / none | 20 each | 838.291 | 885.275 | — | 922.723 |
| research 10 / 250ms / worker worker.agent | worker.claim / none | 20 each | 8.437 | 30.170 | — | 30.720 |
| research 10 / 250ms / worker worker.agent | worker.service / none | 20 each | 826.374 | 874.340 | — | 915.745 |
| research 10 / 250ms / worker worker.agent | worker.poll_wait / none | 2 each | 504.117 | — | — | 509.955 |
| research 10 / 250ms / worker worker.agent | agent.decision / none | 60 each | 251.501 | 271.998 | — | 282.339 |
| research 10 / 250ms / worker worker.agent | agent.provider / none | 60 each | 249.204 | 269.934 | — | 273.746 |
| research 10 / 250ms / worker worker.agent | agent.tool.search_documents / none | 20 each | 0.544 | 0.699 | — | 0.768 |
| research 10 / 250ms / worker worker.agent | agent.tool.read_document / none | 20 each | 0.283 | 0.424 | — | 0.433 |
| research 10 / 250ms / worker worker.agent | retrieval.search / none | 20 each | 0.258 | 0.321 | — | 0.419 |
| research 10 / 250ms / worker worker.agent | agent.persist_result / none | 20 each | 9.009 | 12.203 | — | 20.543 |
| mixed 25 / 250ms / worker worker.agent | worker.cycle / none | 25 each | 1515.869 | 2528.988 | — | 2556.457 |
| mixed 25 / 250ms / worker worker.agent | worker.claim / none | 25 each | 49.873 | 242.662 | — | 507.680 |
| mixed 25 / 250ms / worker worker.agent | worker.service / none | 25 each | 1402.561 | 2228.102 | — | 2313.760 |
| mixed 25 / 250ms / worker worker.agent | worker.poll_wait / none | 2 each | 486.784 | — | — | 501.273 |
| mixed 25 / 250ms / worker worker.agent | agent.decision / none | 75 each | 255.057 | 367.837 | — | 487.831 |
| mixed 25 / 250ms / worker worker.agent | agent.provider / none | 75 each | 252.925 | 365.137 | — | 485.720 |
| mixed 25 / 250ms / worker worker.agent | agent.tool.search_documents / none | 25 each | 1.205 | 4.837 | — | 5.774 |
| mixed 25 / 250ms / worker worker.agent | agent.tool.read_document / none | 25 each | 1.554 | 6.398 | — | 8.324 |
| mixed 25 / 250ms / worker worker.agent | retrieval.search / none | 25 each | 0.276 | 0.307 | — | 0.310 |
| mixed 25 / 250ms / worker worker.agent | agent.persist_result / none | 25 each | 41.003 | 286.266 | — | 317.819 |
| mixed 25 / 250ms / worker worker.agent | workspace.serialized_wait / job_claim | 25 each | 16.926 | 170.735 | — | 220.166 |
| mixed 25 / 250ms / worker worker.agent | workspace.transaction / job_claim | 25 each | 1.604 | 4.159 | — | 6.961 |
| mixed 25 / 250ms / worker worker.agent | workspace.serialized_wait / job_step | 50 each | 9.934 | 231.624 | — | 370.585 |
| mixed 25 / 250ms / worker worker.agent | workspace.transaction / job_step | 50 each | 1.367 | 2.707 | — | 47.201 |
| mixed 25 / 250ms / worker worker.agent | workspace.serialized_wait / job_event_append | 75 each | 77.497 | 299.933 | — | 357.144 |
| mixed 25 / 250ms / worker worker.agent | workspace.transaction / job_event_append | 75 each | 1.788 | 6.202 | — | 45.794 |
| sse 25 / 250ms / api /agent/runs/{run_id}/events | api.service_init / none | 230/218/227 | 255.702 | 341.565 | 363.152 | 377.872 |
| sse 25 / 250ms / api /agent/runs/{run_id}/events | workspace.initialize / none | 230/218/227 | 254.085 | 340.832 | 362.556 | 377.341 |
| sse 25 / 250ms / api /agent/runs/{run_id}/events | workspace.serialized_wait / none | 230/218/227 | 241.982 | 323.536 | 352.344 | 366.496 |
| sse 25 / 250ms / api /agent/runs/{run_id}/events | sse.read_events / none | 230/218/227 | 3.244 | 28.812 | 41.470 | 128.309 |
| sse 25 / 250ms / api /agent/runs/{run_id}/events | sse.serialize / none | 325 each | 0.021 | 0.041 | 0.052 | 0.253 |
| sse 25 / 250ms / api /agent/runs/{run_id}/events | sse.send / none | 555/543/552 | 0.042 | 0.140 | 0.250 | 0.491 |
| mixed 25 / 250ms / api /agent/runs/{run_id}/events | api.service_init / none | 899/875/955 | 132.091 | 328.013 | 387.658 | 420.407 |
| mixed 25 / 250ms / api /agent/runs/{run_id}/events | sse.read_events / none | 899/875/955 | 2.898 | 19.513 | 36.934 | 150.297 |
| mixed 25 / 250ms / api /agent/runs/{run_id}/events | sse.send / none | 1224/1200/1280 | 0.053 | 0.167 | 0.308 | 0.548 |
| mixed 25 / 250ms / api /agent/runs/{run_id}/events | sse.serialize / none | 325 each | 0.024 | 0.044 | 0.057 | 0.192 |
| mixed 25 / 250ms / api /agent/runs/{run_id}/events | workspace.initialize / none | 899/875/955 | 129.093 | 327.619 | 387.110 | 419.969 |
| mixed 25 / 250ms / api /agent/runs/{run_id}/events | workspace.serialized_wait / none | 899/875/955 | 115.858 | 313.151 | 376.830 | 404.463 |

The fixed anchors exercise search/read/final decisions. `agent.tool.inspect_retrieval`, `agent.tool.ask_rag`, `retrieval.inspect` and `generator.transport` have **zero anchor samples** and no benchmark percentiles. Hermetic tool/provider integration tests cover those boundaries; two separate guarded Generator probes cover completed/failed transport and bounded failover. Synthetic 250ms transport is configured delay per call (three decisions per research job), not live Groq latency; observed timer values can be slightly below the configured delay due to timer/scheduling precision. Evaluation is pure native compute, with no provider calls.

### Queue, worker utilization and SSE delivery

Queue is monotonic creation-commit → claim-commit; service is claim-commit → terminal-commit. The worker service span wraps coordinator execution and has a different window. Poll span is the last completed idle sleep preceding a successful cycle, not the job's queue wait. No production per-job timing map is retained.

| Enabled scenario | Window | Count | p50 | p95 | p99 | Max |
| --- | --- | --- | --- | --- | --- | --- |
| research 10 / 0ms | queue commit → claim | 20 each | 787.998 | 1145.784 | — | 1262.984 |
| research 10 / 0ms | claim operation | 20 each | 9.095 | 23.050 | — | 34.385 |
| research 10 / 0ms | claim → terminal | 20 each | 162.470 | 199.065 | — | 200.005 |
| research 10 / 0ms | creation → terminal | 20 each | 942.746 | 1297.877 | — | 1405.544 |
| research 10 / 250ms | queue commit → claim | 20 each | 3287.152 | 3658.011 | — | 3796.183 |
| research 10 / 250ms | claim operation | 20 each | 5.650 | 20.275 | — | 23.019 |
| research 10 / 250ms | claim → terminal | 20 each | 823.032 | 857.056 | — | 909.191 |
| research 10 / 250ms | creation → terminal | 20 each | 4074.925 | 4539.923 | — | 4621.630 |
| mixed 25 / 250ms | queue commit → claim | 25 each | 11613.724 | 17633.700 | — | 18506.687 |
| mixed 25 / 250ms | claim operation | 25 each | 24.117 | 175.480 | — | 235.740 |
| mixed 25 / 250ms | claim → terminal | 25 each | 1469.067 | 2217.795 | — | 2294.974 |
| mixed 25 / 250ms | creation → terminal | 25 each | 13148.067 | 18537.072 | — | 19311.048 |
| mixed 25 / 250ms | SSE event commit → client frame | 200 each | 199.205 | 1240.865 | 1426.468 | 1551.658 |
| sse 25 / 250ms | queue commit → claim | 1 each | — | — | — | 655.647 |
| sse 25 / 250ms | claim operation | 1 each | — | — | — | 268.573 |
| sse 25 / 250ms | claim → terminal | 1 each | — | — | — | 2170.268 |
| sse 25 / 250ms | creation → terminal | 1 each | — | — | — | 2877.350 |
| sse 25 / 250ms | SSE event commit → client frame | 200 each | 308.265 | 503.541 | 538.246 | 609.697 |

Peak active owners per trial: research/mixed **2**, SSE **1**, admission/read measured **0**. Task peak is 2 where the pool runs. Queue/service separation establishes capacity waiting; no fabricated utilization percentage. Every mixed/SSE trial completes all 25 subscriber streams and cursor resumes. Enabled batch counts: mixed **874/850/930**, SSE **205/193/202**. Delivery populations include 200 event frames per trial; server totals measure individual finite HTTP batches. Emission timing is ASGI await cost, not physical delivery; paired batch differences are in the API table.

### Instrumentation overhead: off → on

| Scenario | Req/s Δ% | Jobs/s Δ% | Client p50 Δ% | Client p95 Δ% | CPU seconds | CPU Δ% | RSS MiB | Loop lag p95 ms | Loop lag max ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| admission / 0ms | -11.138 | — | 30.182 | -2.261 | 2.859 → 3.047 | 6.557 | 767.770 → 786.805 | 34.338 → 37.382 | 136.700 → 232.010 |
| read / 0ms | -6.289 | — | 5.212 | 6.882 | 2.781 → 3.188 | 14.607 | 789.176 → 794.496 | 92.281 → 79.833 | 147.830 → 147.476 |
| research / 0ms | 1.379 | 0.215 | -22.694 | -23.111 | 1.750 → 1.828 | 4.464 | 797.832 → 799.031 | 41.921 → 25.285 | 124.837 → 43.204 |
| research / 250ms | 0.626 | 0.740 | -5.560 | 3.754 | 2.156 → 2.062 | -4.348 | 799.477 → 799.984 | 19.411 → 16.983 | 32.732 → 28.880 |
| mixed / 250ms | -11.223 | -14.420 | 13.100 | 27.979 | 13.938 → 16.141 | 15.807 | 805.664 → 851.977 | 29.122 → 35.178 | 313.960 → 375.938 |
| sse / 250ms | -12.110 | -6.474 | 16.308 | 9.279 | 3.234 → 3.406 | 5.314 | 854.375 → 856.637 | 12.630 → 11.378 | 251.969 → 288.482 |

| Enabled scenario | Captured traces | Captured spans | Selected durable rows | Durable JSON bytes |
| --- | --- | --- | --- | --- |
| admission 50 / 0ms | 200/200/200 | 5000/5000/5000 | 22/19/18 | 51570/44560/42196 |
| read 50 / 0ms | 200/200/200 | 4700/4700/4700 | 14/21/13 | 26127/40133/23868 |
| research 10 / 0ms | 80/80/80 | 2822/2822/2822 | 27/23/26 | 104769/96705/102938 |
| research 10 / 250ms | 80/80/80 | 2822/2822/2822 | 25/25/25 | 101226/100633/98763 |
| mixed 25 / 250ms | 1049/1025/1105 | 26803/26227/28147 | 103/135/154 | 285975/353383/395779 |
| sse 25 / 250ms | 232/220/229 | 6260/5972/6188 | 23/22/25 | 55907/53698/60302 |

Counts above show trial 1/2/3. Durable rows include measured selected API and worker summaries; warmups are excluded. Persistence occurs after the API root closes, so its cost affects CPU/throughput and shared scheduling without being included in that request's server total. Capture/analysis overhead is also inside the combined process measurements.

### Low-load poll experiment (enabled)

One client, 20 sequential jobs, two workers, zero provider delay, three trials per setting; fresh same-runtime warmups excluded. Duration per trial about 1.2–2.9s. No p99 with 20 jobs.

| Poll ms | Queue count | Queue p50 | Queue p95 | Queue p99 | Queue max |
| --- | --- | --- | --- | --- | --- |
| 100 | 20 each | 4.537 | 41.890 | — | 94.017 |
| 250 | 20 each | 4.702 | 67.794 | — | 190.770 |
| 500 | 20 each | 4.573 | 10.492 | — | 444.323 |
| 1000 | 20 each | 4.599 | 8.977 | — | 939.970 |


## Interpretation and next task

**Recommend exactly one next task: DB-SCALE-001 — repository serialization and
initialization under mixed read/SSE/worker load. Do not implement it in OBS-001.**

Mixed worker event persistence has serialized wait p95 **299.933ms**, compared
with transaction-scope p95 **6.202ms**; worker step wait/transaction p95 are
**231.624/2.707ms**, claim wait/transaction **170.735/4.159ms**. API SSE factory
initialization p95 **328.013ms**, including serialized wait **313.151ms**;
serialization/send p95 only **0.044/0.167ms**. This supports Python-side
serialization/initialization as the first explicit repository concern, rather
than a database-engine throughput conclusion. Transaction/read scopes also include
Python work; these are not measurements of pure SQLite CPU. No busy/integrity errors.

Worker capacity remains a separate strong contributor: moderate research queue/
service p95 **3,658.011/857.056ms**, mixed **17,633.700/2,217.795ms**. Synthetic
provider waits account for much of research service; search/read tool boundaries
are sub-millisecond there. This fixture does not characterize dense/reranker or
real corpus performance; retrieval dominance is not established.

Counter-evidence/uncertainty: admission/read client times are much larger than
ASGI totals, and valid server remainder is substantial. Admission server root
p95 **421.268ms**, remainder **347.114ms**, client-minus-server **2,166.959ms**.
Read server p95 **331-393ms**, remainder **269-304ms**, paired difference
**1,323-1,862ms** by endpoint. Authorization/protected-value/freeze compute is
tiny, but its thread-pool scheduling is not inside those function spans. Do not
claim repository changes alone will resolve that plateau. The next task must
retain ingress/scheduling and on/off controls, measure fairness/progress and
preserve DATA-004 CAS/idempotency/cancellation and DATA-005 populations.

Poll experiment: **INCONCLUSIVE for materially tracking median/p95 low-load
queue latency**. Medians stay about 4.6ms; p95 is non-monotonic. Maxima grow with
poll interval, but the maximum per trial includes very few observations and two
consumers can alternate immediate claims. This is not a causal recommendation
to lower production polling. Its default remains 500ms.

Overhead is observable, not zero: admission/read request throughput declines
11.14/6.29%; mixed jobs/sec declines 14.42%, request p95 rises 27.98%; research
differences vary in sign. Ordered campaigns, warm process memory, random durable
selection, 3-trial populations and shared client/server loop limit causal precision.
Windows sampled RSS includes benchmark traces/clients; it is not isolated product
memory or a leak finding. Largest individual observed loop-lag maximum across
accepted trials is **417.416ms**; median per-trial maxima are in the tables.
No confidence intervals, SLA, production-user capacity or performance score.

## Defects and excluded work

- P0: none. No secret exposure/auth bypass/data corruption.
- Initial P1 observer progress defect: repeated per-summary initialization/full
  persistence made growing telemetry feed more integrity scans and starved mixed
  workers. Initial mixed point exceeded 58s; a 240s diagnostic still had 21 queued
  and two interrupted owners. Corrected by initialized-store reuse and sampled
  durable API summaries. Product initialization/locks/defaults are unchanged.
  Corrected diagnostic: 21.600s, 1,048 full traces, 26,779 spans, 125 durable rows,
  all correctness gates pass. Fresh full canonical campaign binds the fix commit.
- P2 initial timing decorator annotation regression: preserved evaluated callable
  signature restores FastAPI's Request dependency; full contracts pass.
- P2 existing analytics/log defect: legacy projections rejected terminal Agent
  jobs against their three-namespace schema. Queries exclude only the legitimate
  Agent namespace; corrupt/unknown namespaces still reject. Legacy populations
  and schemas remain unchanged; Agent performance is a separate population.
- P3 initial harness deadline/logging: bounded OBS allowance, incomplete failure
  checkpoint and fixed safe CLI failure output. Initial local stderr tracebacks
  contained framework paths; these rejected diagnostics are ignored, never Git.
- Initial SHA `023ec89…` campaign's 27 completed trials and unfinished mixed point
  are excluded completely. No checkpoint-mixed final results. Initial fixture
  assertion errors were repaired without weakening production assertions.
- Unresolved P0/P1/P2: **0**. No underlying bottleneck optimization implemented.

## Validation and release

| Gate | Actual result |
| --- | --- |
| New OBS timing core | 17 passed |
| New OBS integration/safety/equivalence/lock/provider/tools/evaluation/SSE | 26 passed |
| New OBS enabled worker regressions/harness/statistics | 18 passed |
| Combined OBS + existing DATA-005 focused gate | 99 passed / 1 inherited warning |
| CRED-001 regression | 33 passed (included in full suites and clean focused gate) |
| Original worker/Agent/provider/SCALE-002 regressions | Included unchanged in passing full release suite |
| Fixed observer mixed-25 diagnostic | PASS, 21.600s, zero correctness failures |
| Accepted benchmark | 16 scenarios / 48 trials, zero correctness failures/missing/dropped spans |
| Final primary runtime suite | **1875 passed / 188 warnings / 0 failed**, 130.77s |
| Committed measured-runtime clean suite | **1841 passed / 34 expected skips / 148 warnings / 0 failed**, 81.98s |
| Clean focused OBS + CRED | **94 passed / 1 inherited warning**, 14.69s |
| Compile/import / no import startup | PASS; clean imports need no dotenv/data/provider credential |
| Route inventory | 90 unique method/path pairs, 0 added |
| SQLite fresh/reopen/integrity/receipts | v7/v7 / ok / seven unchanged receipts |
| Generator transport probe | Two guarded cases PASS: bounded 429 fallback and non-429 single attempt; content-free completed/failed spans |
| Diff/secret/artifact audit | PASS; no configured secret or generated/private artifact in intended Git files |
| Exact final documentation HEAD clean suite and push | Required closure; exact SHA/results in closing report |

Primary and clean full suites ran serially. Warning totals match baselines
1814/188 primary and 1780/34 skips/148 clean. Added 61 tests. Frontend 94 files /
818 tests, TypeScript/build PASS are inherited, not rerun: production frontend
is untouched. No whole browser matrix or optional Ragas run was needed.

Created: `src/workspace/attribution.py`, `src/api/attribution.py`,
`scripts/benchmarks/obs_001.py`, three `tests/test_performance_*.py` files,
this receipt and the attribution protocol. Modified: `.env.example`,
`configs/settings.py`, `README.md`, `ARCHITECTURE.md`, `PROJECT_STATE.md`,
`docs/SCALING_ROADMAP.md`, SCALE-002 runtime seams, API access/app/Agent SSE/
telemetry models/owner, Agent durable/orchestration/provider/registry/tools/
evaluation, Generator, workspace database/jobs/telemetry/worker. Deleted: none.
Dependencies/lockfiles/frontend/migrations: no changes.

Commits:

1. `023ec89b4b8e37b0dd657f760ff71a9b36feb4e5`
   `feat(obs): add safe performance attribution and fixed benchmark`.
2. `6ea9d534ba55f24fc3f094095eefede74f526bf1`
   `fix(obs): prevent observer-induced worker starvation` — measured runtime.
3. `12be777f232f269c8075f3252359cea27d70ed59`
   `docs(obs): record performance attribution findings`.
4. Final documentation clarification: `docs(obs): clarify result route identity`;
   literal SHA and exact normal push verification in closing report.

Tracked/staged tree initially clean; same 12 historical untracked paths preserved.
Only explicit OBS files staged; no screenshots/traces/raw reports/databases/data/
dotenv/cache/build outputs entered Git. Local diagnostics use ignored `.local/obs-001/`.
No branch/PR/rebase/amend/force push. Before `git push origin main`, fetch and verify
remote main still equals the starting SHA; if it moved, stop. Successful closure
requires local/upstream/remote final SHA equality and ahead/behind 0/0.

Known limitations persist: staged Collections/model-test browser bearer wiring,
manual native zoom, inherited bundle/backend warnings, optional Ragas, no SLA,
no live provider/corpus attribution, process-coupled benchmark/Windows sampling,
sampled durable analytics and lossy partial traces on abrupt shutdown. The prior
Linux CI OpenAPI hash gap is not certified fixed by Windows checks; remote CI is
not claimed green. Next action: separately scope **DB-SCALE-001**. **STOP** before
that optimization or SCALE-003.
