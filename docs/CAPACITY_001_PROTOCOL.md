# CAPACITY-001 measurement protocol

Protocol `capacity-001-v1`. This optional characterization closes the current
performance round. Required milestones remain complete. No live provider calls.

## Authority and workload

Run from a committed, tracked-clean `main` runtime:

```powershell
.venv\Scripts\python.exe -m scripts.benchmarks.capacity_001 --output .audit-runtime/capacity-001/campaign.json
```

The driver reuses SCALE-002 real loopback TCP/lifespan/SQLite/Agent SDK and its
correctness/statistics gates, OBS-001 complete bounded captures and WORKER-002
numeric scheduler state. External model/corpus/transport boundaries are synthetic.
No route, tool adapter, access handler, durable repository or worker is replaced.
Four warm jobs and four warm reads are excluded; mixed additionally warms SSE.

30 points / 86 measured trials: workers 1/2/4/8 at each 0/100/250/500ms synthetic
decision transport delay, 25 jobs and 25 clients, three trials. Research10 has
20 jobs at 0/250/500ms and two workers. Mixed25 uses 25 jobs at 250ms and 2/4/8
workers with admission/list/detail/result/evaluation/SSE/resume. Two-worker
inspection and RAG variants have 25 jobs, zero transport delay and three trials.
Idle and queued-restart each have one trial, reusing WORKER-002 controls.
Four diagnostic points use workers 4/8, provider limit 2 and worker/mixed profiles
at 250ms, three trials each. This is a finite semaphore around the existing
decision adapter in the benchmark only; fixed consumers await it. No production
gate is implied. Matrix sizes remain below the prior WORKER-002 campaign.

Worker profile executes read then final (two decisions); research/mixed executes
search, read, final (three decisions). Supplemental runs select inspection or RAG
then final (two decisions). Independent decision/RAG grants remain authoritative.
The legacy offline inspector fixture is enriched with typed trace metadata and
truthfully labeled synthetic score semantics. RAG uses the existing query service
with the legacy fake pipeline. Its generation/model costs are unmeasured; no
engine performance or real Groq quota inference is valid from these fixtures.

## Attribution and populations

Existing OBS records only; no new production phase or performance store. For each
complete worker service root, clip all intervals to that root. Apply union length
subtraction in this explicit priority: provider (`agent.provider` and
`generator.transport`), tools (all four), final persistence, remaining workspace
intervals, unattributed remainder. Tools exclude nested provider work; persistence
excludes work already assigned; workspace excludes all prior unions. The partition
sums exactly to that individual service root, within floating point rounding.
Inclusive per-job decision/provider/tool/persistence unions are reported separately.
Do not add inclusive phases or percentile rows. Unattributed time includes
orchestration, scheduling, decision serialization/parsing and diagnostic gate wait;
it is not CPU time. Workspace includes lock wait and cannot prove SQLite engine
dominance. Claim and queue windows precede service and remain separate.

The existing content-free publish callback is timed outside worker service to
report post-service DATA-005 telemetry occupancy. This includes thread scheduling,
summary creation and persistence; do not insert it into the service partition.
Benchmark-only maps hold at most 256 completed jobs; raw record budgets and all
existing missing/drop gates stay fixed. Warmup maps clear at the existing measured
window reset. Missing, duplicate, incomplete or dropped captures fail closed.

Nearest-rank p50/p95/p99 require 2/20/100 samples. Summaries are medians of per-trial
statistics, never pooled percentiles. Per-job zero tool occupancy means not invoked;
inclusive individual-call OBS populations distinguish those from measured calls.
API evaluation is outside worker service. It remains provider-free and has 21 metrics.
CPU and RSS are combined server/client/capture process values, not isolated server
resources. Loop-lag probe interval is 20ms. Order/process warming and sampled
telemetry persistence limit causal precision. No production SLA is certified.

## Bounds, validation and artifacts

One campaign deadline 1800s; at most 330s per trial. Every trial has a new temporary
DB, real lifecycle and shutdown/reopen/integrity checks, no checkpoint merging.
The report binds Git SHA, tracked cleanliness, environment and byte hashes for
SCALE, OBS/attribution and CAPACITY/WORKER drivers. Smoke is diagnostic only.
All accepted jobs must reach intended terminal states; ownership/claim/decision/
event/SSE/SQLite errors, missing and dropped records must be zero. Provider peak
cannot exceed configured workers or the diagnostic limit. Fixed consumers and
private/public startup, cancellation, grace/restart, wake/poll and credential
semantics are also tested outside the timing campaign, without live network.

Ignored `.audit-runtime/capacity-001/` holds raw reports and safe logs. No prompt,
goal, answer, evidence/document text, reasoning, provider body, credentials,
headers, SQL or raw exception body is a timing dimension or artifact field.
All historical untracked files and `.env` are preserved. No data regeneration.
Canonical reporting requires a complete report and exact final local/clean tests,
push with no upstream movement, and both full GitHub workflows at final SHA.
