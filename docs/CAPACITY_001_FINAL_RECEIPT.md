# CAPACITY-001 final receipt

Date: 2026-10-01. Optional characterization on `main`; required and completed optional milestones remain complete. Release is complete only after the exact latest receipt commit passes the clean-checkout, normal push and both full GitHub CI gates below. Literal final SHA/run IDs are supplied in the ignored closing report and final chat after those gates finish. No next task is started.

## Bindings and protocol

- Starting local/upstream/remote: `e6d4d0f66ae49cd5bc9911f46d58a3d4deda31f9`.
- Accepted measured runtime: **`8f2af8edf760e1958ec21f8a64004131e1baf394`**, tracked-clean, committed driver. Source/test changes after this runtime are documented separately; no production runtime change is retained.
- Protocol **capacity-001-v1**; [durable protocol](CAPACITY_001_PROTOCOL.md), unchanged SCALE-002/OBS-001/WORKER-002 correctness and statistic authorities.
- CAPACITY/WORKER driver SHA256: `4ee6204146a71bedf1f6db0f4be514c457dce584d1c26c722e7052e7b44f795c`.
- SCALE driver SHA256: `a96d5789178885cc3731ff24f7be4f78e36b93771d9ba2c790fe97d28bd55ea2`; OBS/core: `01b3122c1dafabcb58db1aeb9ddb62f3ee73f49033b23984a1844f6b1628c591`.
- Windows 10.0.26300, Python 3.12.7, SQLite 3.45.3, 24 logical CPUs, 16,890,322,944 bytes RAM. FastAPI 0.115.0 / Starlette 0.38.6 / HTTPX 0.28.1 / Uvicorn 0.32.0 / Groq 1.5.0 / Pydantic 2.13.4.
- **30 points / 86 trials / 2,075 succeeded measured jobs / 14,159 requests / 16,234 accepted traces / 251,134 spans.** Four warmups excluded. Every important point has three trials and 20 or 25 completed jobs. Idle/restart are single diagnostic controls. No checkpoint merging, best-trial selection or pooled percentiles.
- Real loopback TCP, access, lifespan, SQLite, Agent, tool adapters and strict Groq SDK; mocked external transport and synthetic corpus/model fixtures only. No live Groq/SEC or private corpus stress. CPU/RSS combine server, client and capture; process warming and ordered trials constrain causal inference. No SLA or Groq quota certification.

## Architecture and capacity authority

Accepted durable jobs → fixed WorkerSupervisor consumers → existing Agent executor/orchestrator → awaited decisions/tools and short DATA-004 writes → terminal result. DATA-004 is sole durable job/run authority; DATA-005 is sole telemetry authority. WorkerSupervisor owns process-local execution; provider adapter owns one-attempt semantics. No queue mirror, result queue, new DB or task per queued job.

Each fixed consumer holds its slot through the executor and reconciliation, then publishes telemetry before claiming again. Atomic oldest-row claims retain `created_at ASC, job_id ASC`, writer RLock/BEGIN IMMEDIATE/CAS, independent read connections and short WAL snapshots. Admission hint remains payload-free/coalesced after commit; fallback poll 500ms and grace 5000ms remain. Health/readiness and public/import refusal remain unchanged.

Normal awaited Agent decisions have at most one HTTP attempt per occupied worker. Configured worker count naturally bounds concurrent decision transport, including the default two workers. This is not a global provider quota: Chat, Evaluation and other Generator callers are outside this pool. RAG uses the existing synchronous query service and can outlive a cancelled/timed-out await. An offline barrier probe of that unchanged helper made two sequential timeouts leave one then two query threads live; both ended after release (zero after cleanup). It proves lifetime uncertainty, not live-provider concurrency. Worker count therefore cannot certify all Generator work under abandonment. The benchmark RAG fixture performs no real generation transport; that cost is unmeasured.

Agent remains one attempt, max_retries=0, 60s deadline and no fallback rotation. CRED remains primary plus optional fallback; historical key5_only is primary only. Generator bounded 429 fallback stays unchanged. Decision and RAG grants remain independent. No model, retrieval algorithm, budget, route, index, migration, dependency or production frontend change.

## Operating decision

| Concept | Retained policy |
| --- | --- |
| Production default workers | **2**, unchanged |
| Supported configuration / hard range | **1–16**, existing validation; not a performance or provider-quota guarantee |
| Validated benchmark range | **1–8**, sampled exactly at 1/2/4/8; maximum tested 8 |
| Recommended ordinary operating range | **1–2**; 1 favors local work, 2 balances local and wait-bound work |
| Conditional higher concurrency | 4 only after verifying decision-provider quota and local/API budgets on the intended workload; 8 is a tested wait-bound stress point, not a general recommendation |
| Explicit production provider gate | **None retained**; normal Agent decision concurrency ≤ configured workers |
| Real provider quota certified | **NO** |

| Workers | Wait-bound benefit | Local-bound cost | Synthetic transport maximum | Supported? / recommended? |
| --- | --- | --- | --- | --- |
| 1 | Lowest wait throughput; serial provider occupancy | Best 0ms throughput/service and loop lag here | 1 | Config supported / suitable local control |
| 2 | Nearly doubles wait throughput over 1 | Some local overhead; lower tails than 4/8 | 2 at nonzero delay | Config supported / default |
| 4 | Further wait throughput and queue benefit | Service/loop/API tails increase at 0ms and mixed load | 4 | Config supported / conditional workload-specific use |
| 8 | Highest synthetic wait throughput | Worst local service/lag and mixed API p95 | 8 | Config supported / tested stress, not ordinary recommendation |

9–16 are implemented configuration values but not benchmark-validated. Values outside the hard range and malformed native WorkerConfig values fail closed. No arbitrary new maximum of eight is added. Higher synthetic jobs/sec alone does not justify a larger default.

## Worker matrix

All durations are milliseconds. Queue/service/E2E cells are p50 / p95. CPU is process seconds, RSS is sampled peak MiB, API is aggregate client p95 and lag is loop p95. Statistics are medians of trial statistics; provider peak is the **maximum across the three trials**, not a median. Lifecycle service ends at durable terminal commit. SQLite busy/error/integrity/claim counters are zero at every point.

| Workers | Delay | Jobs/s | Queue p50/p95 | Service p50/p95 | E2E p50/p95 | API p95 | Lag p95 | CPU s | RSS MiB | Provider peak |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0 | 17.603 | 654.796 / 1167.467 | 36.254 / 43.122 | 689.243 / 1201.456 | 186.119 | 9.109 | 1.188 | 774.605 | 1 |
| 2 | 0 | 14.723 | 768.318 / 1338.725 | 84.647 / 226.781 | 852.306 / 1421.959 | 237.264 | 19.595 | 1.250 | 789.941 | 1 |
| 4 | 0 | 15.535 | 747.375 / 1248.938 | 166.230 / 330.425 | 894.545 / 1398.749 | 368.517 | 44.586 | 1.250 | 801.016 | 3 |
| 8 | 0 | 13.923 | 503.189 / 1251.405 | 347.608 / 568.053 | 871.498 / 1568.426 | 441.525 | 77.430 | 1.016 | 800.910 | 4 |
| 1 | 100 | 3.879 | 3092.540 / 5824.388 | 236.630 / 287.629 | 3351.795 / 6054.849 | 158.605 | 16.262 | 1.516 | 806.035 | 1 |
| 2 | 100 | 5.962 | 1969.374 / 3489.263 | 281.649 / 359.235 | 2259.195 / 3777.209 | 186.092 | 22.037 | 1.328 | 806.094 | 2 |
| 4 | 100 | 10.170 | 1025.290 / 1940.909 | 327.041 / 424.674 | 1365.126 / 2240.934 | 204.872 | 28.018 | 1.094 | 806.426 | 4 |
| 8 | 100 | 11.969 | 544.059 / 1314.674 | 455.143 / 705.449 | 1251.434 / 1776.164 | 322.952 | 64.220 | 1.266 | 806.785 | 8 |
| 1 | 250 | 1.784 | 6735.838 / 12795.053 | 544.622 / 573.668 | 7283.882 / 13324.598 | 159.056 | 14.404 | 1.484 | 801.797 | 1 |
| 2 | 250 | 3.240 | 3591.325 / 6559.878 | 572.725 / 628.936 | 4148.811 / 7126.293 | 181.699 | 15.210 | 1.422 | 796.605 | 2 |
| 4 | 250 | 5.464 | 2128.102 / 3469.470 | 642.754 / 716.132 | 2738.793 / 4124.710 | 227.684 | 21.756 | 1.469 | 802.336 | 4 |
| 8 | 250 | 9.120 | 846.366 / 1639.396 | 646.577 / 749.435 | 1485.780 / 2306.462 | 288.594 | 33.695 | 1.250 | 806.414 | 8 |
| 1 | 500 | 0.937 | 12802.577 / 24448.829 | 1050.105 / 1088.819 | 13871.263 / 25491.907 | 157.778 | 12.230 | 1.906 | 803.625 | 1 |
| 2 | 500 | 1.755 | 6596.026 / 11968.958 | 1070.992 / 1154.848 | 7683.804 / 12985.252 | 176.041 | 15.844 | 1.859 | 807.480 | 2 |
| 4 | 500 | 3.123 | 3511.820 / 5790.604 | 1115.077 / 1188.096 | 4619.730 / 6908.738 | 204.720 | 20.560 | 1.469 | 800.410 | 4 |
| 8 | 500 | 5.375 | 1402.475 / 2607.683 | 1168.794 / 1275.105 | 2564.776 / 3804.148 | 261.865 | 28.812 | 1.359 | 806.703 | 8 |

At 250ms, 1→8 workers raises jobs/sec 1.784→9.120 while peak decision transport rises 1→8. At 0ms, 1→8 lowers jobs/sec 17.603→13.923 and service p95 rises 43.122→568.053ms; loop p95 rises 9.109→77.430ms. The 100/500ms controls show the same wait/local tradeoff, not a universal capacity improvement.

## Default anchors, mixed fairness and diagnostic gate

| Point | Jobs/s | Queue p50/p95 | Service p50/p95 | E2E p50/p95 | API p95 | Lag p95 | CPU s | RSS MiB | Provider peak |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| research-10-0 | 9.375 | 664.463 / 968.921 | 147.016 / 306.661 | 842.948 / 1102.401 | 124.274 | 24.633 | 1.719 | 809.281 | 2 |
| research-10-250 | 2.207 | 3334.797 / 3744.917 | 855.198 / 916.683 | 4160.954 / 4587.118 | 82.243 | 17.921 | 1.984 | 809.883 | 2 |
| research-10-500 | 1.199 | 6567.595 / 6769.704 | 1619.744 / 1666.110 | 8189.240 / 8398.861 | 85.884 | 17.355 | 2.344 | 800.281 | 2 |
| mixed-25-2-250 | 2.000 | 5976.000 / 10467.105 | 889.858 / 1094.478 | 6856.735 / 11268.561 | 187.987 | 21.739 | 11.438 | 835.750 | 2 |
| mixed-25-4-250 | 3.562 | 3164.646 / 5565.740 | 959.674 / 1191.006 | 4168.420 / 6525.413 | 318.344 | 28.081 | 6.641 | 840.156 | 4 |
| mixed-25-8-250 | 5.217 | 1541.132 / 2928.748 | 1167.644 / 1422.111 | 2823.036 / 4083.167 | 581.896 | 47.123 | 4.594 | 840.172 | 8 |
| gate-2-worker-4-250 | 3.623 | 2917.780 / 5230.075 | 1012.694 / 1086.182 | 3941.176 / 6240.518 | 203.643 | 20.204 | 1.391 | 840.000 | 2 |
| gate-2-worker-8-250 | 3.633 | 1879.013 / 4181.648 | 2005.520 / 2048.622 | 3889.762 / 6158.896 | 267.620 | 24.153 | 1.453 | 840.961 | 2 |
| gate-2-mixed-4-250 | 2.327 | 4752.145 / 8256.987 | 1534.254 / 1795.595 | 6344.542 / 9765.747 | 219.398 | 23.785 | 9.953 | 841.109 | 2 |
| gate-2-mixed-8-250 | 2.362 | 3142.659 / 6393.544 | 3004.078 / 3233.800 | 6116.116 / 9534.893 | 274.339 | 22.631 | 10.281 | 839.520 | 2 |

Research10/250 is comparable to WORKER-002 (2.243 jobs/s, queue/service p95 3667.924/915.828ms); current 2.207, 3744.917/916.683ms does not establish an improvement. Mixed25/250 current 2.000 jobs/s, queue/service p95 10467.105/1094.478ms versus prior 2.057, 10199.134/1099.260ms. Different task capture/order and ordinary timing variability preclude a causal before/after claim; production runtime is unchanged.

The two-permit diagnostic keeps synthetic transport peak exactly two while fixed 4/8 consumers wait. Four workers offer useful local overlap: worker/mixed jobs/sec improves about 11.8%/16.3% over two natural workers, with lower E2E. Service p95 rises about 72.7%/64.1% and API p95 rises about 12.1%/16.7%. Eight adds only about 0.3%/1.5% throughput over gated four and roughly doubles blocked service. Gate wait belongs to the unattributed remainder, not provider occupancy or CPU.

**Retained:** existing fixed worker configuration, default two, current wake/poll/grace and all authorities. **Rejected:** a larger default, new hard limit, production provider semaphore/config and eight-worker ordinary recommendation. The modest synthetic overlap gain does not create an operating requirement for an independent gate at recommended 1–2; the gate would add lifecycle/deadline composition and still would not bound abandoned Generator threads or other routes. No permit-release tests are claimed for a production gate because none is retained. The diagnostic async context releases its permit on exit; every accepted control drains with zero correctness errors.

Mixed admission, list/detail/result/evaluation, SSE terminal progress and suffix resume complete at every tested/control capacity. Higher throughput has an API cost: mixed client p95 187.987→318.340→581.900ms at 2/4/8 natural workers. No starvation occurred in these bounded workloads; this is not a production fairness/SLA guarantee.

## Service occupancy

Cells are p50 / p95 of **per-completed-worker** intervals, milliseconds. Provider, tools, final persistence, remaining workspace and unattributed are an exclusive partition from clipped interval unions with the documented priority. Do not add these percentile cells: quantiles do not partition quantiles. The individual partitions do sum to each OBS worker.service root; that root extends through executor return/reconciliation beyond terminal commit. Workspace includes wait/connection/transaction costs and is not SQLite engine CPU. Unattributed includes decision parsing/serialization, scheduling and orchestration; under the diagnostic gate it also includes permit wait.

| Point | OBS service root | Provider | Tools excluding provider | Final persistence | Remaining workspace | Unattributed | Post-service telemetry |
| --- | --- | --- | --- | --- | --- | --- | --- |
| workers-1-delay-0 | 39.674 / 47.266 | 2.766 / 3.686 | 0.205 / 0.418 | 9.119 / 11.776 | 19.734 / 23.056 | 8.066 / 10.042 | 4.280 / 7.780 |
| workers-2-delay-0 | 94.731 / 237.120 | 6.367 / 23.176 | 0.720 / 7.826 | 12.659 / 28.050 | 42.356 / 120.969 | 23.726 / 44.039 | 10.624 / 23.320 |
| workers-4-delay-0 | 165.501 / 291.541 | 32.823 / 72.557 | 6.615 / 26.202 | 17.135 / 31.907 | 56.421 / 97.452 | 60.404 / 111.157 | 25.633 / 59.450 |
| workers-8-delay-0 | 322.127 / 550.075 | 79.493 / 108.392 | 22.158 / 49.220 | 14.431 / 31.256 | 70.883 / 159.454 | 127.482 / 189.901 | 47.982 / 84.969 |
| workers-1-delay-250 | 548.982 / 578.287 | 500.378 / 524.079 | 0.338 / 0.477 | 9.733 / 12.711 | 28.275 / 34.774 | 10.183 / 12.143 | 4.237 / 8.810 |
| workers-2-delay-250 | 577.818 / 629.301 | 503.604 / 527.479 | 0.650 / 4.554 | 12.278 / 23.092 | 33.715 / 58.151 | 19.108 / 44.949 | 5.892 / 26.434 |
| workers-4-delay-250 | 650.434 / 706.589 | 519.621 / 550.302 | 3.088 / 7.844 | 11.674 / 26.962 | 47.688 / 82.816 | 36.013 / 61.479 | 16.530 / 32.574 |
| workers-8-delay-250 | 667.456 / 756.694 | 524.531 / 565.118 | 1.891 / 18.491 | 13.370 / 33.381 | 51.386 / 91.244 | 54.373 / 114.230 | 22.735 / 58.711 |
| workers-1-delay-100 | 240.972 / 291.096 | 191.855 / 220.950 | 0.268 / 0.427 | 10.017 / 13.076 | 28.809 / 53.759 | 10.198 / 12.919 | 4.271 / 6.962 |
| workers-2-delay-100 | 296.173 / 405.196 | 206.679 / 224.059 | 0.859 / 5.840 | 13.666 / 27.830 | 40.803 / 119.760 | 19.911 / 44.007 | 10.493 / 23.445 |
| workers-4-delay-100 | 342.197 / 394.295 | 208.952 / 237.495 | 4.007 / 25.498 | 12.724 / 27.023 | 47.596 / 72.808 | 43.482 / 78.650 | 21.568 / 51.564 |
| workers-8-delay-100 | 456.464 / 637.581 | 255.341 / 299.052 | 7.633 / 31.242 | 14.254 / 34.766 | 58.691 / 86.386 | 86.102 / 230.456 | 40.605 / 69.270 |
| workers-1-delay-500 | 1053.738 / 1093.237 | 1006.877 / 1038.872 | 0.308 / 0.541 | 10.228 / 13.662 | 28.466 / 34.149 | 10.217 / 12.694 | 4.175 / 7.115 |
| workers-2-delay-500 | 1074.593 / 1129.107 | 1008.390 / 1030.439 | 0.525 / 4.240 | 11.299 / 25.216 | 32.749 / 52.087 | 17.207 / 58.127 | 6.858 / 22.814 |
| workers-4-delay-500 | 1125.400 / 1180.860 | 1009.653 / 1047.168 | 3.520 / 9.823 | 13.989 / 29.808 | 44.078 / 69.287 | 41.951 / 81.615 | 17.291 / 52.595 |
| workers-8-delay-500 | 1203.833 / 1268.533 | 1023.389 / 1059.756 | 3.912 / 13.160 | 12.162 / 33.984 | 50.774 / 73.190 | 85.151 / 131.710 | 34.421 / 74.513 |
| research-10-0 | 147.351 / 274.308 | 8.973 / 22.236 | 8.564 / 14.763 | 11.504 / 28.343 | 75.806 / 194.067 | 38.917 / 64.066 | 12.457 / 36.439 |
| research-10-250 | 859.441 / 925.247 | 756.834 / 788.631 | 1.162 / 7.062 | 12.075 / 25.694 | 54.924 / 97.243 | 18.466 / 50.342 | 11.630 / 55.071 |
| research-10-500 | 1621.760 / 1684.947 | 1511.964 / 1548.103 | 4.246 / 8.582 | 12.977 / 27.335 | 56.468 / 91.187 | 26.770 / 45.796 | 10.827 / 34.419 |
| mixed-25-2-250 | 893.441 / 1102.594 | 740.755 / 798.351 | 3.054 / 14.271 | 16.901 / 42.861 | 100.584 / 211.707 | 31.771 / 64.054 | 13.430 / 58.153 |
| mixed-25-4-250 | 953.404 / 1157.511 | 762.404 / 912.426 | 7.210 / 66.912 | 17.581 / 49.003 | 105.008 / 151.038 | 48.741 / 131.987 | 33.077 / 90.265 |
| mixed-25-8-250 | 1150.193 / 1376.759 | 820.165 / 983.623 | 20.932 / 91.914 | 20.420 / 48.981 | 134.264 / 220.804 | 119.677 / 237.317 | 52.047 / 142.952 |
| tool-inspect_retrieval | 90.248 / 203.357 | 7.232 / 22.757 | 2.905 / 17.404 | 12.047 / 26.216 | 39.490 / 111.926 | 24.151 / 46.638 | 9.755 / 25.297 |
| tool-ask_rag | 96.835 / 249.127 | 8.372 / 22.924 | 1.261 / 14.934 | 11.526 / 26.177 | 43.378 / 135.353 | 26.066 / 44.107 | 11.087 / 23.175 |
| restart | 101.011 / 154.700 | 6.586 / 15.569 | 2.532 / 7.583 | 12.786 / 23.893 | 42.910 / 71.119 | 25.948 / 52.012 | 10.430 / 22.675 |
| gate-2-worker-4-250 | 1018.199 / 1076.224 | 505.154 / 537.257 | 1.537 / 5.574 | 10.986 / 20.654 | 29.798 / 58.809 | 463.581 / 513.343 | 5.337 / 13.079 |
| gate-2-worker-8-250 | 2004.753 / 2052.109 | 495.312 / 531.573 | 1.532 / 2.845 | 10.117 / 14.073 | 30.312 / 118.810 | 1462.364 / 1519.595 | 4.414 / 6.436 |
| gate-2-mixed-4-250 | 1547.448 / 1737.099 | 759.227 / 893.863 | 12.596 / 25.504 | 18.836 / 36.841 | 104.082 / 226.939 | 620.729 / 776.656 | 14.945 / 43.322 |
| gate-2-mixed-8-250 | 3009.321 / 3245.192 | 748.825 / 828.397 | 9.774 / 16.642 | 17.379 / 47.587 | 103.971 / 176.436 | 2143.642 / 2326.965 | 15.334 / 36.049 |

In the Research10/250 anchor, provider occupancy dominates the individual service root (approximately three 250ms decisions). At 0ms, provider transport becomes small and local/DB/orchestration overhead dominates. Post-service telemetry is measured separately through the existing publish callback; it includes summary/thread scheduling/persistence and is never folded into service. Engine costs for dense/reranker/model generation remain synthetic or unmeasured; no live retrieval, CPU-engine or telemetry bottleneck certification follows.

### Inclusive per-job tool and decision populations

Zero means not invoked. These **inclusive** unions are not additive to the exclusive table. Search/read are exercised by research/mixed; inspection/RAG have dedicated 25-job controls. The old inspector fixture keeps its computed synthetic ranks and receives typed metadata; scores are labeled synthetic. RAG reuses the query adapter with a fake pipeline, so its tool envelope is measured but real generation transport is absent.

| Point | Decision | Provider | Search | Inspection | Read | RAG | Persist result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| research-10-0 | 15.128 / 29.555 | 8.973 / 22.236 | 5.255 / 9.783 | 0.000 / 0.000 | 4.171 / 5.911 | 0.000 / 0.000 | 11.504 / 28.343 |
| research-10-250 | 764.819 / 796.083 | 756.834 / 788.631 | 0.690 / 4.444 | 0.000 / 0.000 | 0.364 / 4.152 | 0.000 / 0.000 | 12.075 / 25.694 |
| research-10-500 | 1518.055 / 1555.210 | 1511.964 / 1548.103 | 1.002 / 5.348 | 0.000 / 0.000 | 0.884 / 4.296 | 0.000 / 0.000 | 12.977 / 27.335 |
| mixed-25-2-250 | 747.230 / 805.652 | 740.755 / 798.351 | 1.564 / 7.950 | 0.000 / 0.000 | 1.574 / 6.543 | 0.000 / 0.000 | 16.901 / 42.861 |
| tool-inspect_retrieval | 11.836 / 26.827 | 7.232 / 22.757 | 0.000 / 0.000 | 2.905 / 17.404 | 0.000 / 0.000 | 0.000 / 0.000 | 12.047 / 26.216 |
| tool-ask_rag | 12.917 / 27.432 | 8.372 / 22.924 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 | 1.261 / 14.934 | 11.526 / 26.177 |

### API native evaluation and workspace contention

Evaluation is invoked after terminal state through the read-only Agent route, outside worker service; 21 metrics remain unchanged and no provider call is made. The table uses existing OBS individual inclusive spans and SCALE commit/lock populations. Nested DB phases cannot be added.

| Point | Evaluation compute p50/p95 | Write lock wait p50/p95 | Transaction p50/p95 | Claim p50/p95 |
| --- | --- | --- | --- | --- |
| research-10-0 | 0.857 / 1.105 | 0.417 / 26.315 | 1.372 / 3.815 | 20.001 / 34.359 |
| research-10-250 | 0.903 / 1.452 | 0.001 / 21.378 | 1.537 / 3.751 | 14.179 / 29.394 |
| research-10-500 | 1.003 / 1.649 | 0.001 / 22.719 | 1.437 / 3.766 | 15.279 / 30.035 |
| mixed-25-2-250 | 0.929 / 1.484 | 0.001 / 45.602 | 1.761 / 10.008 | 11.169 / 53.989 |
| mixed-25-4-250 | 0.872 / 1.452 | 0.001 / 39.058 | 1.535 / 7.814 | 17.605 / 73.663 |
| mixed-25-8-250 | 0.848 / 1.298 | 4.380 / 46.916 | 1.307 / 8.075 | 27.924 / 53.073 |

## Idle, boundedness and correctness

Idle diagnostic: workers two, four seconds, CPU 0.109s, RSS 839.844 MiB, loop p95 11.894ms, empty claims/sec 4.013, provider peak zero, fixed task count two. This is one diagnostic trial, not a statistically comparable idle-CPU improvement/regression against the prior three-trial campaign. No production idle mechanism changed; no new task or timer exists.

All 86 accepted trials: **zero** lost/duplicate durable IDs, executions, provider attempts, claims, terminals, invalid lifecycle, event ordering, terminal mutation, cancellation extra-work, research coverage, status mismatch, SQLite busy/error/integrity/claim failure, unhealthy pool, SSE missing/duplicate/order/resume/connection errors. Missing API/worker captures and dropped spans are zero. Peak owners/tasks never exceed configured workers; peak synthetic transport never exceeds workers or the diagnostic two-permit bound. Every trial stops and reopens its same SQLite database at v7/integrity ok with zero active rows.

New barrier tests prove exactly 1/2/4/8 active fixed consumers and matching mocked provider peaks with 40 queued jobs, one invocation per job, no task count proportional to backlog, SDK retries disabled and all 40 contexts closed. Separate 24-row lifecycle tests at 1/2/4/8 prove queued cancellation has zero work, expired grace interrupts every held owner, fresh pools drain only never-claimed rows and no replay/duplicate occurs. Existing real Agent cancellation, stale CAS, cooperative provider boundaries, shutdown/restart, wake/lost-hint polling, DB read/write fairness, OBS and CRED/provider regressions remain required.

## Defects and exclusions

- P0/P1 production defects or new regressions: none found in tested scope.
- Resolved benchmark P2: callback-window accounting included a late warmup. Initial canonical SHA ecc8cb4 stopped after two complete trials; old-driver reproducer later observed 26 captured/published callbacks for 25 measured jobs. Fixed by selecting exact durable IDs returned by the existing verifier, with warmup/missing/duplicate tests. That entire partial campaign is excluded. The accepted full campaign is fresh at 8f2af8e; no populations merged.
- Resolved benchmark P3: legacy synthetic inspection fixture lacked typed Agent metadata. Supplemental smoke failed closed; benchmark-only metadata/score labels repaired it, preserving real tool/API adapters and production ranking.
- Remaining limits: RAG/generation engine costs and global provider/thread capacity under abandonment are unvalidated; native zoom, staged Collections/model-test bearer wiring, optional Ragas, inherited backend warnings and 508.86kB bundle warning remain. No production quota, SLA or exactly-once external-effect claim.

## Validation and release

Primary and clean full backend run serially. Baseline: primary 1931/188 warnings; clean 1897/34 expected skips/149 warnings; frontend 94 files/819 tests, routes 90 and SQLite v7. Final measured-source validation results and exact final release gates are filled below before release closure.

| Gate | Result |
| --- | --- |
| New capacity tests | 18 passed |
| Focused Worker/DB/OBS/CRED/provider/access/telemetry regressions | 319 passed / 1 warning before the last nine new cases; final full suite includes all additions |
| Corrected smoke | 8 points passed, excluded from canonical statistics |
| Canonical campaign | 30 points / 86 trials PASS |
| Primary full backend | 1949 passed / 188 warnings / 0 failed, 124.37s |
| Exact-final clean full backend | Required after final receipt commit; literal SHA/result in closing report |
| Primary frozen frontend install / TypeScript / unit / build | PASS / PASS / 94 files 819 tests / PASS; Bun 1.3.14, unchanged 508.86kB warning |
| Exact-final clean frontend | Frozen install / TypeScript / full unit / build required; closing report |
| Import/public startup/routes/SQLite | Required final gates; closing report |
| Secret/artifact/preserved-file audit | Required final gates; closing report |
| Exact final GitHub Backend and Frontend CI | Both SUCCESS required, exact SHA/run IDs in closing report; no failure rerun to mask nondeterminism |

Changed files: new benchmark driver, new capacity tests, protocol and this receipt; PROJECT_STATE and SCALING_ROADMAP updates. Both workflows gain this receipt in push/PR path filters so documentation closure triggers their full existing gates. No workflow test/timeout/retry/skip/ownership/budget change. No runtime/frontend production, dependency, lockfile, schema/index/migration, README, ARCHITECTURE or AGENTS changes. Deleted files: none.

Commits: ecc8cb4bf0c266341cfeeaf473c834c2d08dc252 — test(capacity): characterize agent service limits; 8f2af8edf760e1958ec21f8a64004131e1baf394 — fix(capacity): bind occupancy to measured durable jobs. The final policy/documentation commit is resolved by git log -1 --format=%H -- docs/CAPACITY_001_FINAL_RECEIPT.md and reported literally in the closing report.

Raw reports/logs/probes remain ignored in `.audit-runtime/capacity-001/`. No prompt/goal/answer/evidence/document text, provider body/reasoning, credential/header/SQL/raw exception dimension enters timing artifacts or Git. `.env`, `data/` and the same 12 historical untracked paths are preserved; only the task-owned new capacity subdirectory is added inside the existing audit directory. Normal main-only commits/push; no PR/feature branch, rebase/amend/reset/clean/stash/force push. Fresh fetch before push must show origin/main still at the starting SHA; divergence stops release.

## Roadmap and stop boundary

CRED-001, OBS-001, DB-SCALE-001, WORKER-002 and CI-FIX-001 remain COMPLETE. CAPACITY-001 closes only after the exact-SHA release gates succeed. **UX-AGENT-001 is NEXT**; FINAL-IMPROVE is NOT STARTED; SCALE-003 remains NOT STARTED / DEFERRED. Remaining optimization ideas belong to future backlog, outside this round. STOP after release; do not start UX or another performance task.
