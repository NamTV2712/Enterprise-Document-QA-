# PROVIDER-001 verification receipt

Status: **COMPLETE** — implementation and verification; exact final SHA and
normal upstream release verification are reported in the final chat receipt.
Scope is only the new optional
production decision provider. Required roadmap, AGENT-001–006, UI-014 and
TEST-005 remain completed historical milestones. Branch:
`codex/bilingual-research-workspace`; starting SHA:
`5a002d0c7f41c595f5a2ebd866dedd09a0a8f907`.

## Adapter and authority

Production implements the existing `AgentDecisionModel.decide` protocol using
Groq SDK **1.5.0**, already pinned in requirements. Explicit initial model
support is **openai/gpt-oss-120b** and **openai/gpt-oss-20b**, using native strict
JSON Schema with `include_reasoning=False`, no streaming and one choice.
Support is based on the [official Groq capability contract](https://console.groq.com/docs/structured-outputs)
and the installed SDK's response-format types, not chat-model inference.
There is no JSON-mode/tool-call/prose fallback or output repair.

The existing generator default or loaded generator identity selects the model;
existing `configured_groq_keys` selects eligible credentials. Pool selects the
first eligible key; key5-only requires key5. The adapter neither uses Generator
completion/retry rotation nor changes RAG generation. Model registry keeps its
three roles. No new credential setting/system, runtime dependency or migration.

The existing orchestrator is the only decision/research loop. The SDK receives
no native tools and executes no action. A root closed object contains exactly
one tool/final decision. Arguments use unique name/value pairs, mapped
losslessly into existing scalar ToolDecision arguments. All wire fields are
required and objects closed. Local transport and semantic validation reject
duplicate JSON/argument keys, extras, coercion, malformed/fenced/prose/empty/
multiple decisions, non-finite numbers and excess bounds. Registry typed
argument, exact-tool, policy, duplicate, budget, research and current-run
reference checks remain the execution authority.

## Context, provenance, permissions and failures

Only typed policy, allowed definitions/schemas, remaining step/tool/per-tool
counts, locale, bounded goal, research view and bounded observations are sent.
System control is separate from untrusted user/data messages. No settings,
headers, credentials, cookies, environment values, database/machine paths,
Python repr, raw exception or previous reasoning is serialized. Context is
bounded at 128 KiB; provider content at 64 KiB before strict decoding.

Safe provider/model/adapter/mechanism/credential-policy provenance is frozen in
existing plan JSON and its fingerprint. The derived decision-model ID binds
the exact identity; each decision rechecks runtime binding. Old plans omit the
optional provenance and keep their original fingerprints. Changed model or
policy cannot silently replace the frozen provider. No credential/client enters
SQLite. The existing protected configuration-status route reports capability
without construction/inference/probing. Missing keys or unsupported models
remain `decision_provider_unavailable`; remote reachability is unprobed.

Workspace execution, per-run decision-provider consent and RAG provider-tool
permission remain independent. All four decision/RAG grant combinations are
tested: denied decision means zero SDK/tools; granted decision without RAG
grant rejects ask_rag; both grants permit admitted RAG execution. The UI
projects only backend availability, requires initially unchecked explicit
decision consent, clears consent on connection generation change, and leaves
RAG consent disabled. Missing capability fails closed. Old unavailable results
remain visible in EN/VI.

Safe failure categories distinguish unavailable, auth (401/403), rate limit
(429), timeout, invalid response/JSON, schema violation and generic provider
failure. No body or raw exception enters events/results. Groq/httpx/httpcore
diagnostic logging is filtered only in the Agent async call context, including
DEBUG request options and exception bodies; concurrent Generator contexts
remain unaffected. Configured key/bearer values are refused before run input
persistence, goal/research/observation state admission, transport and final
acceptance. Synthetic sentinel checks cover model messages, frozen plan,
in-memory/durable results, events, API, rendered UI, storage, logs and evaluation.

Each adapter invocation makes at most one HTTP attempt: SDK `max_retries=0`,
no wrapper retry/key rotation, 60 second total `asyncio.wait_for` deadline and
five second SDK connect timeout. This preserves README's Python 3.10+ API
compatibility; validation used Python 3.12.7. Decision-call counters measure
model invocations, not a billing/quota scheduler. Cancellation is cooperative
at existing boundaries. Barrier tests show one durable owner, no calls before
cancel, no premature in-flight cancellation claim and no restart replay.

## Verification evidence

| Gate | Baseline | Provider verification |
|---|---:|---:|
| Primary backend | 1583 passed / 188 warnings | 1679 passed / 188 warnings |
| Source-clean backend | 1549 passed / 34 skips / 148 warnings | 1645 passed / 34 skips / 148 warnings |
| New adapter/API tests | none | 96 passed, provider-free |
| Frontend unit suite | 94 files / 815 tests | 94 files / 818 tests |
| TypeScript / production build | pass | pass |
| Provider production browser | none | 20/20 Chromium + Firefox |
| Existing UI-014 / TEST-005 browser | 14 / 12 | 14/14 + 12/12 |
| Product method/path pairs | 90 | 90 |
| Workspace SQLite | v7 | v7 |
| Main build chunk warning | 508.30 kB | 508.63 kB |

The full suites include Generator/model tests, Agent tools/orchestration,
research/security/durability, provider-free native evaluation and API contracts.
The new tests also use the actual AsyncGroq SDK with httpx MockTransport to
prove one attempt for auth, rate, network and timeout failures. Successful
research uses the production adapter and existing loop for search → read →
final, with a sufficient canonical ledger and current references. Unknown or
cross-run IDs and Source 999 are rejected. Native Agent v1 remains provider-free
and deterministic, with exactly 21 unchanged metrics and no overall score.

The built browser harness retains real resolver, SDK, FastAPI, access, SQLite,
tools, events and evaluation; only external transport/model/corpus dependencies
are synthetic. Twenty tests cover configured and missing/unsupported states,
explicit consent and three-attempt research across EN/VI × light/dark ×
390/1440px × Chromium/Firefox. Focused modal/result Axe A/AA analyses and
root overflow checks have zero violations. Screenshots were inspected; the
consent checkbox was corrected from inherited text-input sizing to a compact
control within a 44px touch label. The first campaign was stopped after an
incorrect VI ticker-label locator timed out; corrected campaigns passed.
Default browser discovery excludes the dedicated provider server spec.

Clean verification starts without `.env`, `data/`, unrelated untracked source,
frontend dependencies or build output. Backend uses the existing external
Python environment, with source imports verified against the clean checkout;
no backend dependency upgrade is claimed. Fresh Bun 1.3.14 frozen installation
installed 284 packages with no lockfile drift. TS/build/full frontend pass.
No SDK credentials or live network are prerequisites. The 34 clean skips are
existing artifact-dependent cases, not provider tests. Warning counts remain
the historical 188 primary / 148 clean, without warning suppression.

A release rerun mistakenly launched primary and clean backend suites together.
The HTTP/SSE fixtures probe the same starting ports without atomic reservation;
both suites reached shared session and rate-limit state. Each run showed the
same two failures (retained-turn count and 2/minute bucket). This is a validation
process error, not evidence of a provider defect. Final full suites must run
serially; no assertion, test selection, production code or warning gate was
weakened to resolve it.

Final serial verification of `ab7614f228ef3a1cc4803dfd0cec4b313626cc9e`
passed **1679 primary tests / 188 warnings** and **1645 clean tests / 34
expected artifact skips / 148 warnings**, with zero failures in both suites.
The final documentation commit changes no runtime/test/dependency source;
the exact final committed HEAD is checked again before release.

Optional live smoke: **FAILED (`decision_provider_timeout`)**. One authorized
key5-only attempt, 60 second deadline, zero tools, zero retries; only safe
status/counters printed. Live reachability/interoperability remains unverified.
It is independent of completion and will not be retried as part of this task.

## Changes, commits and hygiene

Created (9):

- `src/agent/provider.py`, `src/agent/provider_models.py`
- `tests/test_agent_provider.py`, `tests/test_agent_provider_api.py`
- `tests/integration/provider_product_server.py`
- `frontend/e2e/provider-001.spec.ts`, `frontend/playwright.provider.config.ts`
- `docs/AGENT_PRODUCTION_PROVIDER_PLAN.md`, this receipt

Modified (22):

- `src/agent/decision.py`, `durable.py`, `durable_models.py`, `orchestration.py`, `state.py`
- `src/api/app.py`, `src/api/routers/health.py`
- `tests/test_workspace_access.py`, `tests/integration/agent_product_server.py`
- `frontend/src/components/agent/AgentWorkspace.tsx`, `AgentWorkspace.test.tsx`, `agentCopy.ts`
- `frontend/src/lib/agentTypes.ts`, `localWorkspaceSession.tsx`
- `frontend/src/types.ts`, `frontend/src/styles/agent.css`, `frontend/playwright.config.ts`
- `README.md`, `ARCHITECTURE.md`, `PROJECT_STATE.md`
- `docs/AGENT_EXTENSION_PLAN.md`, `docs/frontend/FRONTEND_CONTRACT.md`

Deleted: **none**. Dependencies, lockfiles, settings, RAG Generator, native
evaluator and migrations unchanged. AGENTS.md stays stable. The old extension
plan receives only a historical-context reference to this separate extension.

- `99eb1e9e9ad2adae4519095a6b351cf522518698` —
  `feat(agent): add strict production decision provider`: adapter, contracts,
  security/durable/API/UI integration, tests, harness and setup docs.
- `ab7614f228ef3a1cc4803dfd0cec4b313626cc9e` —
  `fix(agent): preserve Python 3.10 decision deadlines`: compatible total
  deadline and checkpoint finding.
- Final documentation commit records completion/verification here and in
  PROJECT_STATE/provider plan; its full SHA and push verification are reported
  in the final chat response.

Intended-file staging, diff/check/status and recent-commit review precede each
commit. Changed-file scan finds zero configured runtime secret values and no
forbidden data/env/dependency/build/diagnostic artifacts. Managed verification
worktrees are archived after final verification; reproducible ignored build and
dependency output is not a committed artifact.

The same 12 unrelated untracked paths remain untouched: `.audit-runtime/`,
`.mimosa/`, `.zcodeignore`, `PROJECT_CONTEXT.md`, `frontend/.audit-runtime/`,
`frontend/.mimosa/`, `frontend/e2e/capture-ui-round.mjs`,
`frontend/e2e/probe-box.mjs`, `frontend/e2e/probe-contrast.mjs`,
`frontend/e2e/v5-1-visual-capture.spec.ts`, `harness_stacks.txt`, `screenshots/`.

## Release boundary and limitations

Normal push target is `origin` / `codex/bilingual-research-workspace` at
`https://github.com/NamTV2712/Enterprise-Document-QA-.git`. No force push or PR
publication is part of this scope. The exact final SHA must match the remote
branch and local upstream after push; that receipt is reported in chat.

Strict output format does not certify semantic quality or model resistance to
prompt injection. Code gates are authoritative. Live provider interoperability
is unverified after the timeout. Workspace deployment still assumes one serving
process; no distributed exactly-once/provider quota claim is made. Collections
and model-test browser bearer integration remain staged; native zoom is manual
and unverified; the inherited large-chunk warning remains; Ragas remains
optional. No new deterministic regression remains in tested scope.

Next action after verified release: **STOP**. No subsequent provider task,
roadmap reopening or automatic live retry is authorized by this extension.
