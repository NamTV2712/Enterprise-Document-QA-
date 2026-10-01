# DB-SCALE-001 final receipt

## Status and bindings

Optional repository concurrency extension on **main**. Accepted measured runtime:
**`7d445d5f053819e7244fdf0612ae706a316cf3cf`**. Starting before runtime:
**`cb6ed9e1aedc9d33431e5e6cf85c1baa3d478507`**. Required roadmap,
AGENT-001–006, UI-014, TEST-005, PROVIDER-001, CRED-001, SCALE-001/002 and
OBS-001 remain COMPLETE. SCALE-003 remains NOT STARTED. No next task implemented.

The runtime passed focused correctness and equivalent before/after acceptance.
Release requires the exact final documentation HEAD clean suite and normal main
push; their literal SHA and results belong in the closing report. A document
cannot contain its own final Git SHA. Failed final verification blocks closure.

Campaign `db-scale-001-v1`; workload `scale-002-benchmark-v1`; attribution
`obs-001-attribution-v1`. See the [protocol](DB_SCALE_001_PROTOCOL.md).
Both canonical campaigns were complete, tracked-clean, enabled, five points /
15 trials, three per point; no checkpoint merging, pooled percentiles or best-trial
selection. Four warmups excluded from measured windows. Whole-trial initialization
counts intentionally include startup, warmup and explicit reopen.

Identical before ignored-driver/after committed-driver SHA256:
`0b86072f4500df7fe3d03607fee1443e840bd29e59fa051c9d2f62da34d5de1c`.
Unchanged SCALE harness SHA256:
`a96d5789178885cc3731ff24f7be4f78e36b93771d9ba2c790fe97d28bd55ea2`.
Unchanged OBS harness/core SHA256:
`01b3122c1dafabcb58db1aeb9ddb62f3ee73f49033b23984a1844f6b1628c591`.

Same environment: Windows 10.0.26300, Python 3.12.7, SQLite 3.45.3,
24 logical CPUs, 16,890,322,944 bytes RAM. FastAPI 0.115.0, Starlette 0.38.6,
HTTPX 0.28.1, Uvicorn 0.32.0, Groq 1.5.0, Pydantic 2.13.4. Same loopback TCP,
real access/router/SQLite/worker/Agent/SDK paths, synthetic corpus and provider
transport; no live Groq or SEC. Fixed workers 2, polling 500ms, grace 5000ms;
mixed/SSE/research synthetic provider delay 250ms. Admission disables consumers.
No production data, dotenv, provider credential or previous report is required.

## Architecture audit and retained change

**Before:** each operation already owned an independent short-lived SQLite
connection. Reads did not take the Python writer RLock. Authorized factories
called full initialization per request, including quick integrity/schema/receipt
validation and connections under that same canonical-path writer RLock. Read/SSE
factories consequently waited behind repeated initialization and mutations.
Writers already confined DB/Python mutation work to `BEGIN IMMEDIATE`; provider,
tool, HTTP and waits occurred outside. Existing nested migration reentrancy and
transaction-local helpers were correct and did not need restructuring.

**After:** `ensure_initialized()` reuses a completed validation receipt held by
live database owners, bound to canonical path, filesystem identity and exact
migration tuple. A separate cold initialization RLock elects one complete
initializer. Publication follows full validation; failure clears the receipt.
Warm factories check identity without either operation lock or a connection.
The weak registry retains no job/event/result data or handle; the local lifespan
owns a live repository. Last-owner release discards the validation lifecycle.
Missing/replaced files or changed migration contracts require full validation.
Explicit `initialize()` still performs the complete integrity/schema audit on
every call, including backup/reopen checks. This is initialization metadata,
not a second durable authority or product cache.

Job detail/list/event/Agent event reads pin short explicit `BEGIN` snapshots on
their own connections, closing before serialization/network send. Existing
idempotency reads already used a transaction. Two counterfactual boundary probes
reproduced mixed job/step and count/item snapshots with the prior autocommit
behavior; the new deterministic tests pass with snapshots. Setup failures now
close the newly opened connection as well as ordinary success/failure paths.
No shared cursor, permanent connection, pool or thread-local connection exists.

Writers retain their existing RLock, `BEGIN IMMEDIATE`, CAS/revision checks,
atomic claim ordered `created_at ASC, job_id ASC`, contiguous events, result
commit, terminal immutability, cancellation and recovery. Queued work survives;
ambiguous owned work becomes interrupted, with no automatic external replay.
DATA-004 and DATA-005 remain authorities. Backup exclusions and consistency remain.
SQLite v7/WAL/NORMAL/busy5000, worker/default/provider contracts remain unchanged.
Public imports/startup open no private DB and start no pool; authorization stays
before factory construction.

## Initialization and deterministic correctness

- Eight fresh initializers and eight v6→v7 initializers each perform exactly one
  full validation and observe only complete seven-receipt schema publication.
- Two independent paths initialize concurrently. Exact migration-contract changes,
  file deletion/replacement, corrupt replacement, failed-init retry, explicit
  future-schema rejection and weak-state release have focused tests.
- Eight readers overlap with distinct owned connections and close them; authorized
  factories/readers progress while an uncommitted writer is held. They observe
  committed snapshots, never dirty events/steps/counts.
- Eight competing CAS updates produce one success with existing conflicts;
  eight claimants produce one owner/running event. Existing oldest-row order stays.
- Eight read pollers and 20 progress writes complete within a bounded fairness
  test; queued/running cancellation preserves stale conflicts and terminal state.
- Real Agent ASGI HTTP/SSE clients progress during a paused uncommitted worker
  append. Event order/resume/finite closure, cancellation and native 21 metrics
  remain valid, with no extra provider calls.
- Existing DATA-004 recovery, DATA-005/OBS, Agent/workers, provider/CRED and portable
  backup suites pass. Setup/read failure cleanup and weak registry reclamation are
  explicit tests. No OS-wide handle profiling is claimed.

Canonical before: 4,901 measured requests, 5,039 accepted traces / 130,899 spans,
621 selected durable summaries. After: 5,755 requests, 5,893 traces / 65,070 spans,
717 selected summaries. Both have 798 whole-trial job rows including warmups.
Measured lifecycle population each: 138 succeeded jobs and 600 intentionally
queued admission jobs. Every trial reopens at v7/integrity ok with zero active
rows after stop. Dynamic SSE batch counts differ because completion/poll timing
changes; population counts appear in the tables.

All 30 canonical trials have **zero** lost/duplicate job, execution/provider,
claim, lifecycle/revision, terminal mutation, event missing/duplicate/order,
SSE resume/connection, capacity, cancellation-extra-work, SQLite busy/error,
integrity, unhealthy-pool, missing API/worker observation and dropped-span counters.
The three separate diagnostic trials also pass every correctness counter.

## Acceptance, regressions and diagnostic attribution

The repeated target reduction is clear across all three mixed trials:

| Metric p95, ms | Before trials 1/2/3 | After trials 1/2/3 |
| --- | --- | --- |
| Worker event append serialized wait | 350.401 / 462.505 / 338.073 | 7.407 / 4.180 / 0.224 |
| Worker step serialized wait | 266.397 / 249.477 / 204.854 | 26.900 / 15.524 / 21.690 |
| Read client | 1967.995 / 1826.321 / 2109.797 | 996.863 / 982.813 / 936.846 |
| Mixed client | 538.853 / 659.384 / 526.455 | 184.072 / 175.130 / 225.055 |
| SSE client | 699.738 / 576.337 / 603.006 | 221.115 / 177.278 / 251.609 |

Warm read/SSE factory initialization/writer-wait samples disappear, reported
**unavailable / eliminated boundary**, never fabricated zeros. Median mixed
event append wait p95 falls 350.401→4.180ms; step wait 249.477→21.690ms.
Read requests/sec rises 55.276→149.474; mixed jobs/sec 1.216→1.844; mixed
service p95 2455.694→1046.785ms and SSE delivery p95 1312.463→369.745ms.
Code remains small, preserving the existing writer boundary and dependencies.

There are real tradeoffs. Mixed create server p95 **340.264→615.350ms**,
claim wait p95 **68.162→367.060ms** and claim transaction p95
**6.692→17.755ms** rise. Create transaction p95 **3.165→23.808ms**,
event append transaction p95 **8.345→13.998ms** and several read scopes also
rise. Removing initialization throttling admits a concentrated create/read burst
to the unchanged writer boundary. Explicit snapshots also add `BEGIN`; inclusive
read/transaction scopes include Python scheduling and overlapping connection work.
Their relative increases must not be called pure SQLite-engine CPU regressions.

Three additional owned timing diagnostics on the accepted runtime retain the
unchanged mixed workload and OBS capture, adding only content-free terminal span
inspection. They are **diagnostic**, never merged into canonical medians:

| Diagnostic trial | Measured create transaction burst ms | First two measured claim waits ms | Overlapping create transactions | Later claim maximum ms | Read p95 during burst / afterward ms |
| --- | ---: | --- | --- | ---: | --- |
| 1 | 669.988 | 297.033 / 310.676 | 10 / 8 | 23.707 | 79.383 / 7.305 |
| 2 | 517.744 | 224.719 / 227.664 | 3 / 2 | 19.189 | 143.889 / 8.854 |
| 3 | 726.085 | 414.805 / 403.011 | 13 / 10 | 48.520 | 125.049 / 7.849 |

Only the first two measured claims exceed 50ms in each diagnostic; both overlap
the finite create transaction burst. Later claims complete and all 25 jobs succeed.
This directly locates the claim-tail increase at admission contention, rather
than sustained read/SSE starvation. Read scope increases also concentrate at
the burst. Exact pure-SQL versus Python/scheduling cost is not isolated. Absolute
claim/event transaction increases are 11.063/5.653ms, while overall mixed service
p95 falls 1408.909ms. We retain this explained finite admission tradeoff alongside
the substantial repeatable worker/read/SSE benefit; a fairness scheduler is not
introduced without a starvation defect.

Research queue p95 rises **3708.914→3840.910ms (+3.559%)**, E2E
4558.691→4651.571ms (+2.037%); service p95 falls 914.492→885.604ms,
jobs/sec rises 2.146→2.215. These small queue/scheduling changes under the same
bounded workers/polling are retained as limitations, not described as improvement.
Research loop-lag p95 rises 17.311→17.754ms. Three ordered trials and random
durable sampling do not establish statistical significance or isolate every cause.
CPU and peak RSS decrease at all five points; combined process observations do
not certify production memory, engine efficiency or a per-server allocation.

Two additional window tradeoffs remain visible: admission-control server p50
**261.525→354.103ms** and SSE-resume remainder p95 **9.956→108.851ms** rise,
even though admission client/server p95 and SSE-resume server p95 improve.
Factory initialization no longer staggers concurrent admission/read completion;
the unchanged writer admission scope and uninstrumented server window receive
more of that overlap. This is a scope/scheduling interpretation, not a direct
profile of the remainder. Retain these internal-window regressions explicitly;
do not claim every phase improves or that the remainder is pure network/engine
time. The product request and event-delivery tails improve in the same trials.

SSE single-job queue/service p50/p95 are unavailable (one sample per trial):
median per-trial maxima are queue **544.995→419.568ms**, service
**2347.018→990.735ms**. Delivery p50/p95/p99 **322.531/561.743/703.883→
129.562/269.972/305.362ms**. Mixed delivery p50/p95/p99
**226.025/1312.463/1586.378→110.045/369.745/443.318ms**.
Server batch processing and commit-to-frame windows differ; their unpaired
percentiles are never subtracted. API remainder uses the original interval union;
paired client-minus-server is not network latency. OBS/deferred emission,
server-random API sampling, all successful worker persistence and retention remain.

No production candidate was rejected: only the audited repeated-initialization
hypothesis and snapshot correction were implemented. Blind read-lock removal,
writer rewrites, indexes, pooling, caching and engine migration lacked evidence
and were not implemented. The historical rejected OBS observer stays excluded.
Two initial deterministic harness assertions were corrected (thread-owned close
inspection and removed initializer-only admission reads). A local release probe
initially counted framework docs/HEAD routes (98); filtering actual FastAPI
APIRoutes restores the unchanged 90-product-route inventory. These are P3 harness
issues, not product route changes or weakened correctness assertions.
P2 snapshot inconsistency and failed-setup handle cleanup are fixed. Unresolved
P0/P1/P2/P3 defects: **0**. Known measured admission tradeoff remains explicit.

## Remaining bottleneck and exactly one next task

Recommend **WORKER-002 — bounded worker queue/scheduling and admission fairness
attribution**, NOT STARTED. Mixed queue/service p95 is **11229.163/1046.785ms**;
research **3840.910/885.604ms**. Queue delay dominates job completion after
event/step writer waiting falls. Initial claims overlap the admission burst.
First distinguish finite admission, worker service and idle-poll scheduling;
do not automatically raise concurrency, change polling or introduce a scheduler.

Counter-evidence: read50 client p95 still 982.813ms and paired client-minus-server
p95 by endpoint remains 846.932–953.471ms; detail/list/result server remainder
p95 82.491–88.912ms is material. API overhead remains separate and is not solved
by this DB change. Pure SQLite-engine dominance and repeated cacheable work are
not proven. Synthetic corpus/provider, local process coupling, three ordered
trials and sampled durable telemetry limit production/causal claims. No SLA,
live-provider, deployment or remote-CI green claim. Implement no next task here.

## Tests and release gates actually run

| Gate | Result |
| --- | --- |
| Initial workspace/jobs/OBS focused | 104 passed / 1 inherited warning, 11.05s |
| Shared focused DATA-004/005, OBS, Agent/workers/provider/CRED/backup plus DB | 662 passed / 1 inherited warning, 44.94s |
| New DB-SCALE tests | 24 passed, included in shared/full gates |
| Prior autocommit snapshot counterfactual | Two reproduced inconsistent-snapshot assertions, PASS; overrides restored |
| Before canonical | 5 points / 15 trials, all correctness/missing/drop counters zero |
| After canonical | 5 points / 15 trials, all correctness/missing/drop counters zero |
| Mixed temporal diagnostics | 3 complete trials, all correctness counters zero; kept separate |
| Final primary full backend | **1899 passed / 188 warnings / 0 failures**, 129.82s |
| Measured-runtime data-free clean full backend | **1865 passed / 34 expected skips / 148 warnings / 0 failures**, 91.10s |
| Exact-final clean focused DB + OBS + CRED | Closing report, required PASS |
| Compile/import, public startup without DB/pool | PASS primary; exact-final clean required |
| Fresh/reopen/integrity/PRAGMAs/defaults | v7/v7, ok, WAL/NORMAL/busy5000; 2/500/5000 |
| API product method/path inventory | 90, zero added |
| Exact-final documentation HEAD clean full suite and normal push | Required closure; literal final SHA/results in closing report |
| Diff/secret/artifact audit | PASS before runtime commit; repeat for final documentation closure |

Primary and clean full suites run serially. Baseline primary 1875/188 warnings;
clean 1841/34 skips/148 warnings. Expected final increment is exactly 24 tests.
Frontend 94 files/818 tests and TypeScript/build PASS are inherited, not rerun:
production frontend and public API DTO/SSE payload contracts remain unchanged.
No whole browser matrix, live provider test or Ragas run.

Created: `docs/DB_SCALE_001_PROTOCOL.md`, this receipt,
`scripts/benchmarks/db_scale_001.py`, `tests/test_db_scale_concurrency.py`,
`tests/test_db_scale_agent_sse.py`, `tests/test_db_scale_benchmark.py`.
Modified: `src/workspace/database.py`, `src/workspace/jobs.py`,
`src/workspace/telemetry.py`, `src/api/app.py`,
`tests/test_performance_regressions.py`, `README.md`, `ARCHITECTURE.md`,
`PROJECT_STATE.md`, `docs/SCALING_ROADMAP.md`. Deleted: none.
Dependencies/lockfiles, migrations/indexes, frontend, provider/defaults: unchanged.

Commits: `7d445d5f053819e7244fdf0612ae706a316cf3cf`
`perf(db): reuse validated workspace initialization and pin read snapshots`;
final evidence/documentation commit SHA and message in the closing report.
Tracked/staged tree starts clean; the same 12 historical unrelated untracked
paths remain untouched. Task artifacts are ignored under `.local/db-scale-001/`.
No dotenv, credential, DB/WAL/SHM, raw JSON/CSV/log/trace, screenshots, generated
data, build/dependency output or unrelated file enters Git. Only named files
are staged. No branch/PR, amend, rebase, force push, reset, clean or stash.
Before normal `git push origin main`, fetch and verify remote main still equals
the starting SHA; otherwise stop. Closure requires local/upstream/remote final
SHA equality and ahead/behind **0/0**.

Known gaps persist: staged Collections/model-test browser bearer wiring, native
zoom manual/unverified, inherited bundle/backend warnings, optional Ragas,
Windows-only validation and the prior Linux CI OpenAPI hash uncertainty.
Initialization receipts do not continuously audit external in-place schema edits;
explicit audit/restart is required. Concurrent replacement of an active database
is unsupported. No extra product/lifecycle data is retained. **STOP** after exact
release verification, before WORKER-002, SCALE-003 or any other optimization.

All duration values are ms. Statistics are medians of three per-trial nearest-rank statistics; no pooling. Δ = after − before; relative Δ = Δ / before. Unavailable (—) is not zero. Counts are trial 1/2/3, or each when equal.

## Before/after workload and resource tables

### read

| Metric | Before | After | Absolute Δ | Relative Δ % | Unit |
| --- | --- | --- | --- | --- | --- |
| requests_per_second | 55.276 | 149.474 | 94.199 | 170.417 | per sec |
| jobs_per_second | — | — | — | — | per sec |
| cpu_seconds | 3.578 | 1.953 | -1.625 | -45.415 | sec |
| peak_rss_bytes | 781.297 | 778.707 | -2.590 | -0.331 | MiB |
| request_ms p50 | 620.073 | 184.145 | -435.928 | -70.303 | ms |
| request_ms p95 | 1967.995 | 982.813 | -985.182 | -50.060 | ms |
| queue_wait_ms p95 | — | — | — | — | ms |
| service_ms p95 | — | — | — | — | ms |
| end_to_end_ms p95 | — | — | — | — | ms |
| event_delivery_ms p95 | — | — | — | — | ms |
| loop_lag_ms p50 | 9.302 | 0.000 | -9.302 | -100.000 | ms |
| loop_lag_ms p95 | 119.247 | 6.433 | -112.814 | -94.605 | ms |
| loop_lag_ms max | 163.706 | 12.598 | -151.109 | -92.305 | ms |

| API endpoint / window | Before count | After count | Before p50 | After p50 | p50 Δ | p50 Δ % | Before p95 | After p95 | p95 Δ | p95 Δ % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| detail / server_ms | 50 each | 50 each | 229.529 | 75.912 | -153.617 | -66.927 | 349.604 | 109.272 | -240.332 | -68.744 |
| evaluation / server_ms | 50 each | 50 each | 266.677 | 121.384 | -145.293 | -54.483 | 473.390 | 181.824 | -291.566 | -61.591 |
| list / server_ms | 50 each | 50 each | 239.296 | 79.918 | -159.378 | -66.603 | 351.700 | 122.113 | -229.587 | -65.279 |
| result / server_ms | 50 each | 50 each | 240.709 | 78.547 | -162.162 | -67.368 | 358.469 | 109.232 | -249.237 | -69.528 |
| detail / server_remainder_ms | 50 each | 50 each | 160.809 | 65.558 | -95.251 | -59.232 | 308.977 | 88.912 | -220.065 | -71.224 |
| evaluation / server_remainder_ms | 50 each | 50 each | 193.286 | 82.142 | -111.144 | -57.502 | 406.861 | 100.091 | -306.770 | -75.399 |
| list / server_remainder_ms | 50 each | 50 each | 186.035 | 65.246 | -120.789 | -64.928 | 302.996 | 86.520 | -216.477 | -71.445 |
| result / server_remainder_ms | 50 each | 50 each | 185.078 | 64.745 | -120.333 | -65.017 | 320.079 | 82.492 | -237.588 | -74.228 |
| detail / client_observed_minus_server_ms | 50 each | 50 each | 389.269 | 66.779 | -322.490 | -82.845 | 1596.470 | 953.471 | -642.999 | -40.276 |
| evaluation / client_observed_minus_server_ms | 50 each | 50 each | 326.474 | 77.344 | -249.129 | -76.309 | 1912.897 | 924.026 | -988.871 | -51.695 |
| list / client_observed_minus_server_ms | 50 each | 50 each | 293.391 | 48.051 | -245.339 | -83.622 | 1790.576 | 877.680 | -912.895 | -50.983 |
| result / client_observed_minus_server_ms | 50 each | 50 each | 293.423 | 103.444 | -189.979 | -64.746 | 1647.118 | 846.932 | -800.187 | -48.581 |

| DB population / phase / operation | Before count | After count | Before p50 | After p50 | p50 Δ | p50 Δ % | Before p95 | After p95 | p95 Δ | p95 Δ % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| api / /agent/runs / api.service_init / none | 50 each | 50 each | 46.866 | 1.857 | -45.009 | -96.037 | 94.636 | 3.871 | -90.765 | -95.910 |
| api / /agent/runs / workspace.initialize / none | 50 each | 0 | 46.035 | — | — | — | 92.980 | — | — | — |
| api / /agent/runs / workspace.read / job_list | 50 each | 50 each | 1.046 | 8.002 | 6.956 | 664.863 | 4.033 | 30.537 | 26.504 | 657.152 |
| api / /agent/runs / workspace.read / none | 300 each | 0 | 0.029 | — | — | — | 1.043 | — | — | — |
| api / /agent/runs / workspace.serialized_wait / none | 50 each | 0 | 32.647 | — | — | — | 79.257 | — | — | — |
| api / /agent/runs/{run_id} / api.service_init / none | 50 each | 50 each | 51.266 | 1.771 | -49.495 | -96.545 | 108.902 | 3.984 | -104.918 | -96.342 |
| api / /agent/runs/{run_id} / workspace.initialize / none | 50 each | 0 | 49.084 | — | — | — | 106.814 | — | — | — |
| api / /agent/runs/{run_id} / workspace.read / job_read | 50 each | 50 each | 0.339 | 3.284 | 2.946 | 869.994 | 1.753 | 9.443 | 7.690 | 438.788 |
| api / /agent/runs/{run_id} / workspace.read / none | 300 each | 0 | 0.028 | — | — | — | 0.878 | — | — | — |
| api / /agent/runs/{run_id} / workspace.serialized_wait / none | 50 each | 0 | 31.446 | — | — | — | 97.024 | — | — | — |
| api / /agent/runs/{run_id}/evaluation / api.service_init / none | 50 each | 50 each | 35.330 | 1.180 | -34.150 | -96.660 | 123.496 | 2.319 | -121.177 | -98.122 |
| api / /agent/runs/{run_id}/evaluation / workspace.initialize / none | 50 each | 0 | 34.096 | — | — | — | 122.743 | — | — | — |
| api / /agent/runs/{run_id}/evaluation / workspace.read / job_event_read | 50 each | 50 each | 0.604 | 7.455 | 6.851 | 1133.708 | 6.135 | 24.375 | 18.239 | 297.302 |
| api / /agent/runs/{run_id}/evaluation / workspace.read / job_read | 150 each | 150 each | 0.867 | 2.813 | 1.946 | 224.472 | 3.317 | 8.694 | 5.377 | 162.101 |
| api / /agent/runs/{run_id}/evaluation / workspace.read / none | 300 each | 0 | 0.026 | — | — | — | 0.459 | — | — | — |
| api / /agent/runs/{run_id}/evaluation / workspace.serialized_wait / none | 50 each | 0 | 22.853 | — | — | — | 108.646 | — | — | — |
| api / /agent/runs/{run_id}/results / api.service_init / none | 50 each | 50 each | 38.348 | 1.757 | -36.591 | -95.419 | 100.921 | 3.880 | -97.041 | -96.155 |
| api / /agent/runs/{run_id}/results / workspace.initialize / none | 50 each | 0 | 36.019 | — | — | — | 99.005 | — | — | — |
| api / /agent/runs/{run_id}/results / workspace.read / job_read | 50 each | 50 each | 0.321 | 3.296 | 2.975 | 927.431 | 1.087 | 8.727 | 7.640 | 702.843 |
| api / /agent/runs/{run_id}/results / workspace.read / none | 300 each | 0 | 0.027 | — | — | — | 1.316 | — | — | — |
| api / /agent/runs/{run_id}/results / workspace.serialized_wait / none | 50 each | 0 | 16.415 | — | — | — | 75.956 | — | — | — |

Client counts: 200 each → 200 each. Queue/service counts: 0 each → 0 each.

### mixed

| Metric | Before | After | Absolute Δ | Relative Δ % | Unit |
| --- | --- | --- | --- | --- | --- |
| requests_per_second | 45.625 | 89.730 | 44.105 | 96.670 | per sec |
| jobs_per_second | 1.216 | 1.844 | 0.628 | 51.653 | per sec |
| cpu_seconds | 18.297 | 12.344 | -5.953 | -32.536 | sec |
| peak_rss_bytes | 835.312 | 820.746 | -14.566 | -1.744 | MiB |
| request_ms p50 | 214.307 | 59.576 | -154.731 | -72.200 | ms |
| request_ms p95 | 538.853 | 184.072 | -354.781 | -65.840 | ms |
| queue_wait_ms p95 | 18579.621 | 11229.163 | -7350.458 | -39.562 | ms |
| service_ms p95 | 2455.694 | 1046.785 | -1408.909 | -57.373 | ms |
| end_to_end_ms p95 | 19503.268 | 12117.534 | -7385.734 | -37.869 | ms |
| event_delivery_ms p95 | 1312.463 | 369.745 | -942.717 | -71.828 | ms |
| loop_lag_ms p50 | 0.000 | 0.000 | 0.000 | — | ms |
| loop_lag_ms p95 | 39.658 | 20.623 | -19.035 | -47.997 | ms |
| loop_lag_ms max | 438.890 | 159.711 | -279.179 | -63.610 | ms |

| API endpoint / window | Before count | After count | Before p50 | After p50 | p50 Δ | p50 Δ % | Before p95 | After p95 | p95 Δ | p95 Δ % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| create / server_ms | 25 each | 25 each | 257.315 | 214.249 | -43.066 | -16.737 | 340.264 | 615.350 | 275.085 | 80.845 |
| detail / server_ms | 25 each | 25 each | 367.338 | 33.569 | -333.769 | -90.862 | 397.344 | 96.754 | -300.591 | -75.650 |
| evaluation / server_ms | 25 each | 25 each | 97.102 | 26.546 | -70.556 | -72.662 | 412.455 | 136.399 | -276.056 | -66.930 |
| list / server_ms | 25 each | 25 each | 262.893 | 114.517 | -148.377 | -56.440 | 480.567 | 273.773 | -206.794 | -43.031 |
| result / server_ms | 25 each | 25 each | 225.783 | 11.142 | -214.640 | -95.065 | 539.231 | 50.489 | -488.742 | -90.637 |
| sse_batch / server_ms | 841/819/777 | 1088/1085/1032 | 183.191 | 43.439 | -139.752 | -76.288 | 516.323 | 113.011 | -403.312 | -78.112 |
| sse_resume / server_ms | 25 each | 25 each | 149.934 | 30.972 | -118.962 | -79.343 | 506.362 | 81.986 | -424.376 | -83.809 |
| create / server_remainder_ms | 25 each | 25 each | 239.076 | 34.153 | -204.923 | -85.715 | 321.175 | 43.228 | -277.947 | -86.541 |
| detail / server_remainder_ms | 25 each | 25 each | 2.548 | 10.841 | 8.293 | 325.504 | 25.411 | 42.906 | 17.495 | 68.846 |
| evaluation / server_remainder_ms | 25 each | 25 each | 17.354 | 4.327 | -13.026 | -75.064 | 162.115 | 73.312 | -88.803 | -54.778 |
| list / server_remainder_ms | 25 each | 25 each | 64.595 | 13.256 | -51.339 | -79.478 | 195.369 | 106.763 | -88.606 | -45.353 |
| result / server_remainder_ms | 25 each | 25 each | 3.125 | 2.929 | -0.196 | -6.285 | 198.237 | 25.744 | -172.492 | -87.013 |
| sse_batch / server_remainder_ms | 841/819/777 | 1088/1085/1032 | 10.365 | 14.420 | 4.055 | 39.118 | 226.833 | 77.221 | -149.612 | -65.957 |
| sse_resume / server_remainder_ms | 25 each | 25 each | 7.080 | 9.697 | 2.617 | 36.968 | 54.773 | 37.983 | -16.789 | -30.652 |
| create / client_observed_minus_server_ms | 25 each | 25 each | 118.740 | 29.479 | -89.261 | -75.174 | 258.616 | 63.635 | -194.981 | -75.394 |
| detail / client_observed_minus_server_ms | 25 each | 25 each | 1.815 | 6.184 | 4.369 | 240.784 | 46.368 | 34.141 | -12.227 | -26.370 |
| evaluation / client_observed_minus_server_ms | 25 each | 25 each | 3.673 | 2.668 | -1.005 | -27.372 | 31.251 | 15.870 | -15.381 | -49.218 |
| list / client_observed_minus_server_ms | 25 each | 25 each | 92.081 | 7.893 | -84.188 | -91.428 | 230.071 | 23.141 | -206.930 | -89.942 |
| result / client_observed_minus_server_ms | 25 each | 25 each | 2.398 | 2.707 | 0.309 | 12.895 | 8.217 | 10.140 | 1.923 | 23.402 |
| sse_batch / client_observed_minus_server_ms | 841/819/777 | 1088/1085/1032 | 8.418 | 11.860 | 3.442 | 40.894 | 50.033 | 73.162 | 23.129 | 46.227 |
| sse_resume / client_observed_minus_server_ms | 25 each | 25 each | 1.763 | 2.611 | 0.848 | 48.114 | 5.952 | 12.764 | 6.812 | 114.442 |

| DB population / phase / operation | Before count | After count | Before p50 | After p50 | p50 Δ | p50 Δ % | Before p95 | After p95 | p95 Δ | p95 Δ % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| api / /agent/runs / api.service_init / none | 50 each | 50 each | 19.076 | 1.234 | -17.843 | -93.533 | 323.476 | 5.171 | -318.305 | -98.401 |
| api / /agent/runs / workspace.initialize / none | 50 each | 0 | 17.447 | — | — | — | 320.335 | — | — | — |
| api / /agent/runs / workspace.read / job_list | 25 each | 25 each | 5.000 | 89.100 | 84.100 | 1682.061 | 20.195 | 189.768 | 169.573 | 839.672 |
| api / /agent/runs / workspace.read / none | 300 each | 0 | 0.027 | — | — | — | 0.789 | — | — | — |
| api / /agent/runs / workspace.serialized_wait / job_create | 25 each | 25 each | 0.004 | 142.887 | 142.884 | 3968994.444 | 10.432 | 425.425 | 414.994 | 3978.235 |
| api / /agent/runs / workspace.serialized_wait / none | 50 each | 0 | 7.986 | — | — | — | 315.167 | — | — | — |
| api / /agent/runs / workspace.transaction / job_create | 25 each | 25 each | 1.333 | 10.983 | 9.650 | 723.884 | 3.165 | 23.808 | 20.643 | 652.254 |
| api / /agent/runs/{run_id} / api.service_init / none | 25 each | 25 each | 364.018 | 3.320 | -360.698 | -99.088 | 394.484 | 5.446 | -389.038 | -98.619 |
| api / /agent/runs/{run_id} / workspace.initialize / none | 25 each | 0 | 363.392 | — | — | — | 394.039 | — | — | — |
| api / /agent/runs/{run_id} / workspace.read / job_read | 25 each | 25 each | 0.324 | 7.568 | 7.243 | 2233.549 | 0.886 | 13.255 | 12.369 | 1396.725 |
| api / /agent/runs/{run_id} / workspace.read / none | 150 each | 0 | 0.026 | — | — | — | 0.865 | — | — | — |
| api / /agent/runs/{run_id} / workspace.serialized_wait / none | 25 each | 0 | 345.701 | — | — | — | 378.192 | — | — | — |
| api / /agent/runs/{run_id}/evaluation / api.service_init / none | 25 each | 25 each | 53.558 | 0.659 | -52.900 | -98.770 | 322.043 | 1.572 | -320.471 | -99.512 |
| api / /agent/runs/{run_id}/evaluation / workspace.initialize / none | 25 each | 0 | 52.978 | — | — | — | 321.605 | — | — | — |
| api / /agent/runs/{run_id}/evaluation / workspace.read / job_event_read | 25 each | 25 each | 0.483 | 0.773 | 0.291 | 60.244 | 4.690 | 11.956 | 7.266 | 154.924 |
| api / /agent/runs/{run_id}/evaluation / workspace.read / job_read | 75 each | 75 each | 0.820 | 0.600 | -0.220 | -26.855 | 2.493 | 7.461 | 4.968 | 199.286 |
| api / /agent/runs/{run_id}/evaluation / workspace.read / none | 150 each | 0 | 0.026 | — | — | — | 0.882 | — | — | — |
| api / /agent/runs/{run_id}/evaluation / workspace.serialized_wait / none | 25 each | 0 | 37.810 | — | — | — | 281.608 | — | — | — |
| api / /agent/runs/{run_id}/events / api.service_init / none | 866/844/802 | 1113/1110/1057 | 137.440 | 2.033 | -135.408 | -98.521 | 421.904 | 4.321 | -417.583 | -98.976 |
| api / /agent/runs/{run_id}/events / workspace.initialize / none | 866/844/802 | 0 | 136.239 | — | — | — | 420.786 | — | — | — |
| api / /agent/runs/{run_id}/events / workspace.read / job_event_read | 866/844/802 | 1113/1110/1057 | 0.352 | 2.233 | 1.881 | 533.958 | 1.050 | 10.049 | 8.999 | 856.846 |
| api / /agent/runs/{run_id}/events / workspace.read / job_read | 866/844/802 | 1113/1110/1057 | 0.314 | 2.180 | 1.866 | 593.543 | 0.725 | 8.760 | 8.035 | 1108.957 |
| api / /agent/runs/{run_id}/events / workspace.read / none | 5196/5064/4812 | 0 | 0.027 | — | — | — | 0.924 | — | — | — |
| api / /agent/runs/{run_id}/events / workspace.serialized_wait / none | 866/844/802 | 0 | 125.085 | — | — | — | 397.247 | — | — | — |
| api / /agent/runs/{run_id}/results / api.service_init / none | 25 each | 25 each | 158.711 | 0.942 | -157.769 | -99.407 | 355.219 | 2.810 | -352.410 | -99.209 |
| api / /agent/runs/{run_id}/results / workspace.initialize / none | 25 each | 0 | 154.723 | — | — | — | 354.891 | — | — | — |
| api / /agent/runs/{run_id}/results / workspace.read / job_read | 25 each | 25 each | 0.472 | 0.782 | 0.310 | 65.812 | 0.987 | 6.835 | 5.848 | 592.252 |
| api / /agent/runs/{run_id}/results / workspace.read / none | 150 each | 0 | 0.026 | — | — | — | 1.082 | — | — | — |
| api / /agent/runs/{run_id}/results / workspace.serialized_wait / none | 25 each | 0 | 137.539 | — | — | — | 338.139 | — | — | — |
| worker / worker.agent / workspace.read / job_read | 275 each | 275 each | 0.332 | 0.369 | 0.037 | 11.185 | 0.935 | 1.613 | 0.678 | 72.540 |
| worker / worker.agent / workspace.serialized_wait / job_claim | 25 each | 25 each | 11.927 | 0.003 | -11.924 | -99.975 | 68.162 | 367.060 | 298.897 | 438.508 |
| worker / worker.agent / workspace.serialized_wait / job_event_append | 75 each | 75 each | 65.275 | 0.003 | -65.272 | -99.995 | 350.401 | 4.180 | -346.221 | -98.807 |
| worker / worker.agent / workspace.serialized_wait / job_step | 50 each | 50 each | 12.981 | 0.004 | -12.977 | -99.970 | 249.477 | 21.690 | -227.787 | -91.306 |
| worker / worker.agent / workspace.serialized_wait / job_transition | 25 each | 25 each | 0.003 | 0.003 | -0.001 | -16.667 | 0.006 | 0.005 | -0.000 | -3.571 |
| worker / worker.agent / workspace.transaction / job_claim | 25 each | 25 each | 2.037 | 5.827 | 3.791 | 186.120 | 6.692 | 17.755 | 11.063 | 165.302 |
| worker / worker.agent / workspace.transaction / job_event_append | 75 each | 75 each | 2.995 | 4.143 | 1.147 | 38.308 | 8.345 | 13.998 | 5.653 | 67.742 |
| worker / worker.agent / workspace.transaction / job_step | 50 each | 50 each | 1.727 | 1.315 | -0.413 | -23.881 | 4.226 | 3.525 | -0.700 | -16.575 |
| worker / worker.agent / workspace.transaction / job_transition | 25 each | 25 each | 1.656 | 1.623 | -0.033 | -2.005 | 3.110 | 2.596 | -0.513 | -16.504 |

Client counts: 991/969/927 → 1238/1235/1182. Queue/service counts: 25 each → 25 each.

### sse

| Metric | Before | After | Absolute Δ | Relative Δ % | Unit |
| --- | --- | --- | --- | --- | --- |
| requests_per_second | 54.479 | 129.249 | 74.770 | 137.244 | per sec |
| jobs_per_second | 0.346 | 0.709 | 0.363 | 105.063 | per sec |
| cpu_seconds | 3.891 | 2.578 | -1.312 | -33.735 | sec |
| peak_rss_bytes | 842.051 | 824.602 | -17.449 | -2.072 | MiB |
| request_ms p50 | 326.617 | 97.051 | -229.566 | -70.286 | ms |
| request_ms p95 | 603.006 | 221.115 | -381.892 | -63.331 | ms |
| queue_wait_ms p95 | — | — | — | — | ms |
| service_ms p95 | — | — | — | — | ms |
| end_to_end_ms p95 | — | — | — | — | ms |
| event_delivery_ms p95 | 561.743 | 269.972 | -291.771 | -51.940 | ms |
| loop_lag_ms p50 | 0.000 | 0.000 | 0.000 | — | ms |
| loop_lag_ms p95 | 12.116 | 7.199 | -4.917 | -40.581 | ms |
| loop_lag_ms max | 362.404 | 139.462 | -222.942 | -61.518 | ms |

| API endpoint / window | Before count | After count | Before p50 | After p50 | p50 Δ | p50 Δ % | Before p95 | After p95 | p95 Δ | p95 Δ % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| create / server_ms | 1 each | 1 each | — | — | — | — | — | — | — | — |
| sse_batch / server_ms | 206/189/161 | 204/231/207 | 317.775 | 61.156 | -256.619 | -80.755 | 595.481 | 137.692 | -457.789 | -76.877 |
| sse_resume / server_ms | 25 each | 25 each | 409.736 | 149.931 | -259.805 | -63.408 | 440.761 | 173.443 | -267.317 | -60.649 |
| create / server_remainder_ms | 1 each | 1 each | — | — | — | — | — | — | — | — |
| sse_batch / server_remainder_ms | 206/189/161 | 204/231/207 | 10.250 | 26.986 | 16.736 | 163.282 | 280.275 | 80.918 | -199.358 | -71.129 |
| sse_resume / server_remainder_ms | 25 each | 25 each | 4.436 | 84.801 | 80.365 | 1811.702 | 9.956 | 108.851 | 98.895 | 993.328 |
| create / client_observed_minus_server_ms | 1 each | 1 each | — | — | — | — | — | — | — | — |
| sse_batch / client_observed_minus_server_ms | 206/189/161 | 204/231/207 | 8.075 | 20.044 | 11.969 | 148.214 | 50.265 | 86.672 | 36.407 | 72.430 |
| sse_resume / client_observed_minus_server_ms | 25 each | 25 each | 1.603 | 16.722 | 15.119 | 943.274 | 2.840 | 27.914 | 25.074 | 882.898 |

| DB population / phase / operation | Before count | After count | Before p50 | After p50 | p50 Δ | p50 Δ % | Before p95 | After p95 | p95 Δ | p95 Δ % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| api / /agent/runs / api.service_init / none | 1 each | 1 each | — | — | — | — | — | — | — | — |
| api / /agent/runs / workspace.initialize / none | 1 each | 0 | — | — | — | — | — | — | — | — |
| api / /agent/runs / workspace.read / none | 6 each | 0 | 0.024 | — | — | — | — | — | — | — |
| api / /agent/runs / workspace.serialized_wait / job_create | 1 each | 1 each | — | — | — | — | — | — | — | — |
| api / /agent/runs / workspace.serialized_wait / none | 1 each | 0 | — | — | — | — | — | — | — | — |
| api / /agent/runs / workspace.transaction / job_create | 1 each | 1 each | — | — | — | — | — | — | — | — |
| api / /agent/runs/{run_id}/events / api.service_init / none | 231/214/186 | 229/256/232 | 285.227 | 2.566 | -282.661 | -99.100 | 442.863 | 6.110 | -436.754 | -98.620 |
| api / /agent/runs/{run_id}/events / workspace.initialize / none | 231/214/186 | 0 | 284.208 | — | — | — | 439.870 | — | — | — |
| api / /agent/runs/{run_id}/events / workspace.read / job_event_read | 231/214/186 | 229/256/232 | 0.440 | 6.049 | 5.609 | 1274.148 | 2.066 | 22.340 | 20.274 | 981.302 |
| api / /agent/runs/{run_id}/events / workspace.read / job_read | 231/214/186 | 229/256/232 | 0.367 | 4.899 | 4.532 | 1234.232 | 1.203 | 12.711 | 11.508 | 956.562 |
| api / /agent/runs/{run_id}/events / workspace.read / none | 1386/1284/1116 | 0 | 0.030 | — | — | — | 0.727 | — | — | — |
| api / /agent/runs/{run_id}/events / workspace.serialized_wait / none | 231/214/186 | 0 | 268.374 | — | — | — | 423.357 | — | — | — |
| worker / worker.agent / workspace.read / job_read | 11 each | 11 each | 0.358 | 0.374 | 0.016 | 4.382 | — | — | — | — |
| worker / worker.agent / workspace.serialized_wait / job_claim | 1 each | 1 each | — | — | — | — | — | — | — | — |
| worker / worker.agent / workspace.serialized_wait / job_event_append | 3 each | 3 each | 264.372 | 0.004 | -264.368 | -99.999 | — | — | — | — |
| worker / worker.agent / workspace.serialized_wait / job_step | 2 each | 2 each | 233.545 | 0.003 | -233.542 | -99.999 | — | — | — | — |
| worker / worker.agent / workspace.serialized_wait / job_transition | 1 each | 1 each | — | — | — | — | — | — | — | — |
| worker / worker.agent / workspace.transaction / job_claim | 1 each | 1 each | — | — | — | — | — | — | — | — |
| worker / worker.agent / workspace.transaction / job_event_append | 3 each | 3 each | 2.869 | 5.321 | 2.452 | 85.487 | — | — | — | — |
| worker / worker.agent / workspace.transaction / job_step | 2 each | 2 each | 2.397 | 1.453 | -0.944 | -39.372 | — | — | — | — |
| worker / worker.agent / workspace.transaction / job_transition | 1 each | 1 each | — | — | — | — | — | — | — | — |

Client counts: 232/215/187 → 230/257/233. Queue/service counts: 1 each → 1 each.

### research

| Metric | Before | After | Absolute Δ | Relative Δ % | Unit |
| --- | --- | --- | --- | --- | --- |
| requests_per_second | 6.381 | 6.601 | 0.220 | 3.456 | per sec |
| jobs_per_second | 2.146 | 2.215 | 0.069 | 3.223 | per sec |
| cpu_seconds | 2.547 | 1.984 | -0.562 | -22.086 | sec |
| peak_rss_bytes | 846.242 | 828.520 | -17.723 | -2.094 | MiB |
| request_ms p50 | 37.915 | 27.748 | -10.167 | -26.815 | ms |
| request_ms p95 | 164.429 | 68.759 | -95.671 | -58.184 | ms |
| queue_wait_ms p95 | 3708.914 | 3840.910 | 131.996 | 3.559 | ms |
| service_ms p95 | 914.492 | 885.604 | -28.888 | -3.159 | ms |
| end_to_end_ms p95 | 4558.691 | 4651.571 | 92.880 | 2.037 | ms |
| event_delivery_ms p95 | — | — | — | — | ms |
| loop_lag_ms p50 | 10.400 | 10.547 | 0.147 | 1.417 | ms |
| loop_lag_ms p95 | 17.311 | 17.754 | 0.443 | 2.558 | ms |
| loop_lag_ms max | 45.868 | 66.893 | 21.025 | 45.839 | ms |

| API endpoint / window | Before count | After count | Before p50 | After p50 | p50 Δ | p50 Δ % | Before p95 | After p95 | p95 Δ | p95 Δ % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| create / server_ms | 20 each | 20 each | 44.502 | 31.007 | -13.495 | -30.325 | 137.853 | 55.377 | -82.476 | -59.829 |
| evaluation / server_ms | 20 each | 20 each | 43.896 | 30.228 | -13.668 | -31.138 | 89.097 | 67.746 | -21.351 | -23.964 |
| result / server_ms | 20 each | 20 each | 18.140 | 8.878 | -9.262 | -51.056 | 43.408 | 36.947 | -6.462 | -14.886 |
| create / server_remainder_ms | 20 each | 20 each | 18.049 | 14.243 | -3.806 | -21.087 | 108.198 | 23.947 | -84.251 | -77.867 |
| evaluation / server_remainder_ms | 20 each | 20 each | 13.018 | 4.306 | -8.713 | -66.928 | 30.111 | 35.474 | 5.363 | 17.809 |
| result / server_remainder_ms | 20 each | 20 each | 1.724 | 1.767 | 0.043 | 2.476 | 21.485 | 15.340 | -6.145 | -28.599 |
| create / client_observed_minus_server_ms | 20 each | 20 each | 4.019 | 3.356 | -0.663 | -16.502 | 40.124 | 14.474 | -25.650 | -63.926 |
| evaluation / client_observed_minus_server_ms | 20 each | 20 each | 1.398 | 1.360 | -0.039 | -2.767 | 2.333 | 3.163 | 0.830 | 35.553 |
| result / client_observed_minus_server_ms | 20 each | 20 each | 1.952 | 1.825 | -0.127 | -6.522 | 13.049 | 4.461 | -8.588 | -65.814 |

| DB population / phase / operation | Before count | After count | Before p50 | After p50 | p50 Δ | p50 Δ % | Before p95 | After p95 | p95 Δ | p95 Δ % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| api / /agent/runs / api.service_init / none | 20 each | 20 each | 9.854 | 0.506 | -9.348 | -94.869 | 20.724 | 1.068 | -19.655 | -94.845 |
| api / /agent/runs / workspace.initialize / none | 20 each | 0 | 9.389 | — | — | — | 19.177 | — | — | — |
| api / /agent/runs / workspace.read / none | 120 each | 0 | 0.028 | — | — | — | 0.390 | — | — | — |
| api / /agent/runs / workspace.serialized_wait / job_create | 20 each | 20 each | 0.003 | 6.175 | 6.171 | 181514.706 | 11.924 | 32.962 | 21.039 | 176.443 |
| api / /agent/runs / workspace.serialized_wait / none | 20 each | 0 | 0.004 | — | — | — | 10.157 | — | — | — |
| api / /agent/runs / workspace.transaction / job_create | 20 each | 20 each | 1.939 | 1.433 | -0.507 | -26.137 | 3.893 | 3.265 | -0.628 | -16.123 |
| api / /agent/runs/{run_id}/evaluation / api.service_init / none | 20 each | 20 each | 16.150 | 0.609 | -15.542 | -96.230 | 22.086 | 1.120 | -20.966 | -94.928 |
| api / /agent/runs/{run_id}/evaluation / workspace.initialize / none | 20 each | 0 | 14.878 | — | — | — | 21.538 | — | — | — |
| api / /agent/runs/{run_id}/evaluation / workspace.read / job_event_read | 20 each | 20 each | 0.466 | 0.466 | -0.000 | -0.021 | 0.918 | 1.474 | 0.556 | 60.586 |
| api / /agent/runs/{run_id}/evaluation / workspace.read / job_read | 60 each | 60 each | 0.467 | 0.441 | -0.026 | -5.607 | 0.913 | 1.153 | 0.240 | 26.289 |
| api / /agent/runs/{run_id}/evaluation / workspace.read / none | 120 each | 0 | 0.027 | — | — | — | 0.457 | — | — | — |
| api / /agent/runs/{run_id}/evaluation / workspace.serialized_wait / none | 20 each | 0 | 4.374 | — | — | — | 10.011 | — | — | — |
| api / /agent/runs/{run_id}/results / api.service_init / none | 20 each | 20 each | 11.975 | 0.711 | -11.264 | -94.060 | 18.319 | 1.533 | -16.786 | -91.633 |
| api / /agent/runs/{run_id}/results / workspace.initialize / none | 20 each | 0 | 10.038 | — | — | — | 17.427 | — | — | — |
| api / /agent/runs/{run_id}/results / workspace.read / job_read | 20 each | 20 each | 0.491 | 0.502 | 0.012 | 2.344 | 0.878 | 0.955 | 0.077 | 8.750 |
| api / /agent/runs/{run_id}/results / workspace.read / none | 120 each | 0 | 0.030 | — | — | — | 0.622 | — | — | — |
| api / /agent/runs/{run_id}/results / workspace.serialized_wait / none | 20 each | 0 | 0.003 | — | — | — | 3.659 | — | — | — |
| worker / worker.agent / workspace.read / job_read | 220 each | 220 each | 0.304 | 0.290 | -0.015 | -4.763 | 0.677 | 0.636 | -0.040 | -5.941 |
| worker / worker.agent / workspace.serialized_wait / job_claim | 20 each | 20 each | 0.003 | 0.003 | -0.000 | -6.667 | 9.187 | 13.148 | 3.961 | 43.119 |
| worker / worker.agent / workspace.serialized_wait / job_event_append | 60 each | 60 each | 0.003 | 0.003 | -0.000 | -3.226 | 5.551 | 0.007 | -5.543 | -99.867 |
| worker / worker.agent / workspace.serialized_wait / job_step | 40 each | 40 each | 0.003 | 0.003 | 0.000 | 3.125 | 2.334 | 9.004 | 6.669 | 285.705 |
| worker / worker.agent / workspace.serialized_wait / job_transition | 20 each | 20 each | 0.003 | 0.003 | -0.001 | -15.152 | 0.005 | 0.005 | 0.001 | 14.583 |
| worker / worker.agent / workspace.transaction / job_claim | 20 each | 20 each | 1.912 | 2.069 | 0.157 | 8.223 | 3.598 | 3.434 | -0.164 | -4.552 |
| worker / worker.agent / workspace.transaction / job_event_append | 60 each | 60 each | 2.796 | 2.831 | 0.035 | 1.252 | 3.895 | 4.391 | 0.495 | 12.719 |
| worker / worker.agent / workspace.transaction / job_step | 40 each | 40 each | 1.496 | 1.429 | -0.067 | -4.480 | 2.748 | 2.157 | -0.590 | -21.490 |
| worker / worker.agent / workspace.transaction / job_transition | 20 each | 20 each | 2.040 | 1.722 | -0.318 | -15.612 | 3.122 | 2.169 | -0.953 | -30.537 |

Client counts: 60 each → 60 each. Queue/service counts: 20 each → 20 each.

### admission

| Metric | Before | After | Absolute Δ | Relative Δ % | Unit |
| --- | --- | --- | --- | --- | --- |
| requests_per_second | 44.702 | 123.980 | 79.277 | 177.345 | per sec |
| jobs_per_second | — | — | — | — | per sec |
| cpu_seconds | 4.094 | 1.609 | -2.484 | -60.687 | sec |
| peak_rss_bytes | 847.039 | 839.836 | -7.203 | -0.850 | MiB |
| request_ms p50 | 555.171 | 371.459 | -183.712 | -33.091 | ms |
| request_ms p95 | 3324.892 | 540.846 | -2784.046 | -83.733 | ms |
| queue_wait_ms p95 | — | — | — | — | ms |
| service_ms p95 | — | — | — | — | ms |
| end_to_end_ms p95 | — | — | — | — | ms |
| event_delivery_ms p95 | — | — | — | — | ms |
| loop_lag_ms p50 | 22.927 | 0.000 | -22.927 | -100.000 | ms |
| loop_lag_ms p95 | 74.874 | 1.927 | -72.948 | -97.426 | ms |
| loop_lag_ms max | 233.886 | 127.115 | -106.771 | -45.651 | ms |

| API endpoint / window | Before count | After count | Before p50 | After p50 | p50 Δ | p50 Δ % | Before p95 | After p95 | p95 Δ | p95 Δ % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| create / server_ms | 200 each | 200 each | 261.525 | 354.103 | 92.578 | 35.399 | 586.593 | 474.429 | -112.164 | -19.121 |
| create / server_remainder_ms | 200 each | 200 each | 235.314 | 58.995 | -176.319 | -74.929 | 568.667 | 152.299 | -416.368 | -73.218 |
| create / client_observed_minus_server_ms | 200 each | 200 each | 170.680 | 5.654 | -165.027 | -96.688 | 3131.871 | 152.775 | -2979.096 | -95.122 |

| DB population / phase / operation | Before count | After count | Before p50 | After p50 | p50 Δ | p50 Δ % | Before p95 | After p95 | p95 Δ | p95 Δ % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| api / /agent/runs / api.service_init / none | 200 each | 200 each | 13.848 | 0.470 | -13.378 | -96.603 | 23.076 | 1.036 | -22.041 | -95.511 |
| api / /agent/runs / workspace.initialize / none | 200 each | 0 | 13.066 | — | — | — | 22.105 | — | — | — |
| api / /agent/runs / workspace.read / none | 1200 each | 0 | 0.029 | — | — | — | 0.786 | — | — | — |
| api / /agent/runs / workspace.serialized_wait / job_create | 200 each | 200 each | 0.005 | 258.584 | 258.579 | 5501689.362 | 9.520 | 400.217 | 390.697 | 4103.962 |
| api / /agent/runs / workspace.serialized_wait / none | 200 each | 0 | 3.365 | — | — | — | 11.841 | — | — | — |
| api / /agent/runs / workspace.transaction / job_create | 200 each | 200 each | 1.825 | 1.513 | -0.312 | -17.092 | 4.388 | 4.234 | -0.154 | -3.512 |

Client counts: 200 each → 200 each. Queue/service counts: 0 each → 0 each.

## Whole-trial initialization counts

| Scenario | Before initialize calls | After ensure calls | After initialize calls | Before expensive | After expensive |
| --- | --- | --- | --- | --- | --- |
| read | 211/211/211 | 210/210/210 | 2/2/2 | 211/211/211 | 2/2/2 |
| mixed | 1004/982/940 | 1250/1247/1194 | 2/2/2 | 1004/982/940 | 2/2/2 |
| sse | 245/228/200 | 242/269/245 | 2/2/2 | 245/228/200 | 2/2/2 |
| research | 71/71/71 | 70/70/70 | 2/2/2 | 71/71/71 | 2/2/2 |
| admission | 207/207/207 | 206/206/206 | 2/2/2 | 207/207/207 | 2/2/2 |
