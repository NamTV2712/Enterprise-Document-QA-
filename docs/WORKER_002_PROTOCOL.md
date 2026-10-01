# WORKER-002 scheduling protocol

`worker-002-v1` supplements `obs-001-attribution-v1` and
`scale-002-benchmark-v1`, on the accepted DB-SCALE-001 runtime. It does not
redefine queue wait: durable create commit to durable running/claim commit.

## Execution and bounds

Run `python -m scripts.benchmarks.worker_002 --stage after --output <ignored-path>`.
Canonical runs require a tracked-clean runtime; every trial owns a temporary
SQLite database and real loopback TCP API/lifespan. Only the real Agent SDK
transport is synthetic: no live provider, corpus regeneration or credential
requirement. All SCALE correctness, reopen/integrity, resource, SSE and OBS
completeness gates remain enabled. Same-process server/client CPU and sampled
Windows working set are shared resource facts, not isolated server costs.

The fixed matrix has 26 points, three trials each. Four warmup jobs and four
warmup reads are excluded. Idle-confirmed sequential singles have 20 jobs and
polls 100/250/500/1000ms; they deliberately start after all consumers enter idle,
not at a uniformly random phase of a poll. Staggered arrivals have 20 jobs,
one producer and scheduled intervals 50/100/250/750ms; slow HTTP admission may
delay an arrival. Burst points have 1/2/5/10/25/50 concurrent admissions and
one idle consumer to expose first/second/later claims. Native unchanged
SCALE points are research clients10/jobs20/workers2/delay250ms and mixed
clients25/jobs25/workers2/delay250ms, plus workers1/2/4/8 with clients25/jobs25
at delays250/0ms. Idle checks run four seconds with two workers/poll500ms.
Restart admits 20 rows during a stopped-owner composition gap and starts a
fresh supervisor without inherited hints. A separate deterministic test
admits after startup's empty claim, loses every hint, and proves poll discovery.

The campaign has a 3600s deadline, each trial at most 330s; interruption leaves
an incomplete checkpoint, never merged into a canonical report. Each report
binds runtime SHA, tracked cleanliness, SCALE/OBS hashes, Python/SQLite/library
versions, operating system/CPU/RAM and both scheduler driver files' byte hash.
The before driver was developed in an ignored task directory on the unchanged
starting runtime, then promoted byte-for-byte for after measurement. Raw JSON,
logs and diagnostics stay in ignored `.local/worker-002/`; only reviewed
aggregate tables and methodology enter Git.

## Safe attribution

`worker-002-scheduler-facts-v1` wraps existing benchmark boundaries, with at most
65536 numeric state/claim/idle records of each kind per trial. There is no new
production telemetry, arbitrary label, job payload or serialized Task object.
Negative state, record overflow, non-finite values, missing observations and
owner/provider capacity excess fail closed. Warmups and shutdown are excluded
from measured counters; separate whole-trial counts expose startup/shutdown.

State intervals record active owners, idle consumers, ongoing claim attempts
and synthetic provider calls. Intersections with each durable queue window
yield job-time-weighted milliseconds while **all capacity is serving**, **any
consumer is idle**, **any claim is underway**, and **any provider call is
underway**. These intervals overlap and cannot be added into a causal partition.
Serving starts at executor entry; claim/telemetry/loop intervals can use capacity
without being classified as serving. A provider overlap indicates some occupied
capacity, not that all workers are waiting on the provider.

Global commit-to-next-claim-attempt means the next attempt starting after that
commit. An attempt already in flight may claim the row sooner; this is a safe
opportunity fact, not an exact per-row notice timestamp. First and second claim
commit times are relative to the first measured create commit, not per-consumer
identities. Later successful claim durations exclude the first two successful
attempts. Inclusive claim duration includes offload/scheduling/database work;
OBS `workspace.serialized_wait/job_claim` separately measures writer RLock wait.
Claim and admission interval overlap supports finite contention findings, not
engine-only attribution. No queued row is assigned to a future worker.

Summaries are medians of three trial statistics, not pooled percentiles. p50
requires two samples, p95 twenty, p99 one hundred. Unavailable is null, never
zero. Counters stay per trial; coalescing ratio is coalesced accepted attempts
divided by accepted attempts. Idle CPU, empty checks/second, task count and
claim/SQLite correctness must accompany any claimed wake benefit.

## Candidate and acceptance

Only after baseline attribution, test a payload-free supervisor Event. The
authorized async Agent admission route calls an injected composition callback
after its threadpool durable create returns, only for a queued result. The
callback refers to the existing lifespan owner. Missing/stopped/foreign-thread/
foreign-loop hints are ignored; notification failure cannot undo admission.
No thread enqueues callbacks or creates admission tasks. One flag coalesces
bursts, and only the fixed consumers wake to call unchanged SQLite claims.
All existing waiters may wake, bounded by configured capacity. Poll500ms remains
the durability fallback; defaults workers2/grace5000ms remain fixed.

Event ownership follows Python's [asyncio synchronization contract](https://docs.python.org/3.12/library/asyncio-sync.html)
and [event-loop thread rules](https://docs.python.org/3.12/library/asyncio-dev.html).
Shutdown/unexpected consumer failure sets the stop authority and wakes sleepers.
Existing shielded claim reconciliation, eligibility/order, CAS/cancellation,
restart interruption and no-effect-replay behavior remain authoritative.

Retention requires repeatable low-load durable commit-to-claim benefit, fixed
tasks and bounded hints, no meaningful idle CPU or DB contention regression,
and all correctness gates. Saturated service queueing is assessed separately.
Shorter polling or more workers are controls, not automatic new defaults. No
debounce, batch claim, priority, queue mirror or external broker is introduced
without separate evidence. The final receipt records retained/rejected choices
and exactly one next task; SCALE-003 remains not started.
