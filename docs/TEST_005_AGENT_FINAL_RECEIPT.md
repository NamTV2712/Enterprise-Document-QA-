# TEST-005 — Final Agent extension validation receipt

## A — Contract and matrix (2026-09-30)

Starting branch: `codex/bilingual-research-workspace`; starting HEAD:
`e5eedc69c01ba21d0ae5d09dbafb156dd10b3d35`. Tracked/staged source is
clean; the 12 pre-existing unrelated untracked paths are excluded from this
task. AGENT-001–006 and UI-014 are complete inputs. TEST-005 validates them
through the real product boundaries and repairs only reproduced P0–P2 defects.
There is no production structured decision provider. Scripted models establish
deterministic success; the production route must report unavailability.

| Layer | Authority and scenario | Gate / expected result | Final result |
|---|---|---|---|
| 1 Tool registry | `src/agent/registry.py`, `tools.py`; four exact typed tools, unknown/duplicate/unsafe capability refusal | `tests/test_agent_tools.py`, security suite; unchanged order and closed registry | Pass: focused Agent 188/188; four tools and closed registration preserved |
| 2 Orchestration | `orchestration.py`, policies/state; tool→observation→final, limits, provider split, cancellation and current-run refs | `tests/test_agent_orchestration.py`; no rejected service call or reasoning persistence | Pass: focused suite; real search→read→final and unavailable/cancel journeys |
| 3 Durability | `durable.py`, DATA-004; frozen plan, atomic claim, events, revisioned cancel, restart interruption | `tests/test_agent_durable.py` plus two-contender synchronization; one owner and no replay | Pass: synchronized claim race, persisted events/revisions, real cancellation and interruption |
| 4 Research/evidence | `research_models.py`, observation projection; objectives, gaps, dedup, multi-entity pairs, hostile RAG prose | `tests/test_agent_research.py` and AGENT-005 identity regression; canonical associations only | Pass: focused suite; real ledger retained two distinct AAPL chunks, sufficient objective, no gap |
| 5 Security | policy/access/observations; 20-class adversarial matrix, bearer/Host/Origin, secret/capability denial | `tests/test_agent_security.py` plus real API access; deterministic classes fail closed | Pass: focused matrix and real public/missing/wrong/valid bearer boundary |
| 6 Agent evaluation | `evaluation.py`, models; all 21 metrics, zero/unavailable/N/A, digest, corruption and no calls | `tests/test_agent_evaluation.py`; provider-free, no score or semantic overclaim | Pass: focused suite and real terminal reports with 21 metrics for failed/succeeded/cancelled/interrupted |
| 7 Private API | `agent_runs.py`; seven routes, status/revision/SSE, evaluation access and applicability | `tests/test_agent_api.py`, real HTTP, route inventory; 90 unique product routes | Pass: seven routes, 90 product method/path pairs, real events/resume/409/evaluation |
| 8 Frontend client | `agentApi.ts`, `agentTypes.ts`; wire unions, header bearer, numeric SSE and error boundary | Vitest plus real HTTP; no broad `any` or contract drift | Pass: TypeScript, 94 files/815 Vitest; built client crossed real HTTP boundaries |
| 9 Agent UI | `AgentWorkspace`, sections/hook; truthful state, research, metrics, cancellation and A→B→A | Component tests and built browser; no stale paint, fabricated evidence or CoT | Pass: UI-014 14/14, strengthened stale evaluation digest check, real UI/axe 12/12 |
| 10 Real product journey | built Vite + real FastAPI + temp SQLite; unavailable, scripted research, cancel, interrupted | Chromium/Firefox, controlled servers; real durable/event/evaluation reads in UI | Pass: TEST-005 12/12 (six journeys per engine), five responsive viewports |
| 11 Clean checkout | final committed HEAD without `.env`, `data/`, prior dist or untracked source | Imports, fresh/reopen v7, full owned suites, built real-server Agent smoke | Pending |
| 12 Hygiene | repository/git and browser storage; 12 unrelated paths, no secrets or generated artifacts | status/diff/secret audit, bearer reload/disconnect; exact HEAD pushed | Pending |

Expected baselines: primary backend **1583 passed, 188 warnings**; clean
data-free backend **1549 passed, 34 artifact-dependent skips**; **90** API
method/path pairs; SQLite **v7**; frontend **94 Vitest files / 815 tests**,
TypeScript and production build passing; UI-014 browser **14/14** in Chromium
and Firefox. Known bundle warning is about **508.30 kB**. These are starting
receipts, not TEST-005 outcomes.

The browser campaign will use the existing TEST-004 offline product harness
as its real-server base and a dedicated Agent deterministic injection boundary
if needed. The test replaces only model/corpus/provider dependencies; Agent
routes, storage, events, cancellation, evaluation, frontend client and local
access remain real. A focused responsive/Axe sweep checks the five required
viewports, EN/VI and dark/light, long IDs, research and metric content.
Fixed-port product gates and full backend suites run serially. A stopped or
timed-out command is unknown until its live handle is polled or authoritative
process state is inspected.

No candidate defect is assumed. Reproduce and add a failing regression before
repairing any P0–P2 contract violation. The final matrix and gate counts will
be filled from observed results. This receipt will distinguish tested
structural attack classes from universal security claims, and retain all
production/provider/evaluation/zoom/load limitations.

## B–G — Observed gates and defect disposition

The seven focused Agent backend modules passed **188/188** (one warning).
The final primary backend passed **1583/1583** with the historical **188
warnings**. `tests/test_agent_durable.py` uses `threading.Event` for its
two-contender claim race and verifies one model/tool execution. The Agent
security module exercises direct and indirect instructions, encoded payloads,
fuzzy tools, malformed arguments, provider/budget escalation, forged
objectives/evidence/events/lifecycle, cross-run references, poisoned generated
prose and errors, secret sentinels, network/filesystem denial, oversized text
and loop amplification. These are tested structural classes under deterministic
fixtures, not a claim of universal prompt-injection immunity. The source-pair
identity regression still rejects conflicting ticker/accession identities
while keeping distinct valid chunks and embedded text inert.

The UI client and product build passed TypeScript, **94/94 Vitest files and
815/815 tests**, and the 2079-module production build. Main JS is **508.30
kB** and still emits Vite's known 500 kB warning. UI-014's hermetic
production-build browser regression passed **14/14** across Chromium and
Firefox. The A→B→A selected-run regression now checks the evaluation digest
as well as the run ID, so a same-ID stale report is detectable.

`tests/integration/agent_product_server.py` reuses the offline TEST-004
corpus/provider harness and injects a bounded decision model only for success
or waiting/cancellation. The product's Agent router, tool registry, DATA-004
SQLite repository, SSE, cancellation, evaluator, API access checks and built
frontend client remain real. A production-path service without a decision
factory recorded `decision_provider_unavailable`, zero tool calls and no
answer. A scripted run searched, read `AAPL:HARNESS`, recorded two canonical
chunk identities, completed its objective and final result, emitted ordered
events with cursor resume, and returned the native 21-metric evaluation.
Another run was cancelled at a deterministic model boundary after the UI
sent `If-Match`; the stale revision returned 409. A persisted running job
recovered as interrupted without replay and retained a terminal evaluation.
The four access cases were public 404, missing bearer 401, wrong bearer 401,
and valid local bearer 200.

The real-server browser gate passed **12/12** (six journeys in each of
Chromium and Firefox). Focused Axe returned **zero A/AA violations** for
disconnected, provider-unavailable, completed research, cancelled and five
responsive connected states. Body/root horizontal overflow was zero at
1440×900, 1024×768, 768×900, 390×844 and 1440×700, spanning EN/VI and
dark/light. Desktop and phone captures were inspected. The synthetic bearer
was absent from local/session storage, supported IndexedDB contents, cookies,
URL and DOM; reload forgot it and disconnect cleared private UI state. No
critical page or console errors appeared in the browser campaign. Safe trace
and evaluation displayed recorded facts only, with no hidden reasoning or
aggregate/semantic-quality claim.

The first browser pass exposed **two mistaken test locators**, not product
defects: one chunk ID appeared in two UI elements and the real ledger had two
evidence cards rather than one. The assertions were narrowed to the canonical
chunk code and a specific card's document handoff; both engines then passed.
No deterministic production P0/P1/P2 defect was reproduced, and no production
Agent behavior was changed. TEST-005 added only a test harness, browser
regression and one stronger selected-run unit assertion.

Production still lacks a structured Agent decision-provider adapter. A
cancellation request is cooperative and an in-flight call can finish; restart
recovery marks interrupted instead of replaying. Identity and objective
threshold metrics do not verify factual completeness or semantic support;
the digest detects alteration but is not an authenticity signature. This
campaign is offline, deterministic and not a load or live-provider test.
Native browser zoom at 125/150/200 remains manual. Staged Collections and
model-test browser bearer integration, optional Ragas and the bundle warning
remain separate future work.
