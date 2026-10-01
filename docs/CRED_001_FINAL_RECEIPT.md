# CRED-001 — Groq credential consolidation

Date: 2026-10-01. Main starting HEAD:
`46c06ebd024cebdc6b02b4df6a364112fd08a966`.
Implementation commit: `d76fed562a2f7ea4a2c2c657fae6f59d44331343`.
Required roadmap remains COMPLETE; this is bounded optional configuration work.
OBS-001 has not started. Its unused branch remains at the starting main SHA.

## Configuration and local migration

Before: five numbered primary slots and two fallback slots. After: one primary
`GROQ_API_KEY` and one optional `GROQ_API_KEY_FALL_BACK`.

| Former name | Former use | Final disposition |
| --- | --- | --- |
| `GROQ_API_KEY` | First serving/judge pool slot | Active primary; previous local value replaced by former KEY5 value |
| `GROQ_API_KEY2` | Serving/judge and default evaluation generation | Removed from Settings, active readers, fixtures and Compose |
| `GROQ_API_KEY3` | Later serving/evaluation failover | Removed from active configuration |
| `GROQ_API_KEY4` | Later serving/evaluation failover | Removed from active configuration |
| `GROQ_API_KEY5` | Strict provider/campaign slot and later pool failover | Removed slot; former local value promoted to primary |
| `GROQ_API_KEY_FALL_BACK` | Dedicated evaluation generation slot | Preserved locally; optional serving/generation/judge fallback |
| `GROQ_API_KEY_FALL_BACK2` | Second dedicated evaluation generation slot | Removed; existing first fallback was nonempty, so second was not selected |

Local ignored `.env` migration was performed with in-memory comparisons only.
The former KEY5 value became primary; the existing first fallback was preserved.
Primary and fallback differ. Removed entries are absent. Noncredential lines and
unrelated parsed settings were preserved, including original line endings.
No values, prefixes, suffixes, lengths or hashes were displayed or copied into
diagnostic files. `.env` remains ignored and untracked.

## Provider and compatibility behavior

- `pool`: unique nonblank primary then fallback, at most two clients. Equal
  values construct one client. Fallback-only remains allowed for normal pool use.
- Historical `key5_only`: primary only; absent primary fails closed even when
  fallback exists or an explicit fallback is supplied. The literal and binding
  calculation remain unchanged; there is no fifth active slot.
- New transport aliases are `primary` and `fallback`, including fallback-only
  pool use. Historical `key5`, `key-1`, `key-2` telemetry remains readable and is
  not rewritten. Frozen provider identities and terminal evaluation reads survive
  reopening; the pre-consolidation serialized identity retains binding
  `groq_structured_d1fae7f776ea43c73856273d6c5024e9`.
- Generator preserves round-robin, cooldown and bounded 429 failover. Ordinary
  exceptions do not trigger fallback. Agent decisions preserve one HTTP attempt,
  `max_retries=0`, 60-second total deadline, no rotation, repair or prose fallback.
  Decision-provider consent and RAG provider permission remain independent.
- Generation and judging now share the policy's eligible credentials. Their
  distinct client objects, request accounting and bounded budgets remain intact.
  `phase2_runtime`, legacy `run_evaluation`, and `planner_wording_check` delegate
  selection to the shared authority. Decomposition, correction, evaluation jobs
  and model tests have no direct numbered-field readers. No checkpoint or judge
  record was modified and no evaluation campaign was run.
- Private jobs, workspace records, telemetry and portable transfer guards protect
  both active credentials. Synthetic fallback tests cover goal refusal and
  observation rejection without leaks into API, frozen plan, events, results,
  logs or native evaluation. Browser code receives neither credential.

## Validation

| Gate | Result |
| --- | --- |
| New CRED-001 tests | 33 passed |
| Initial provider/generator/evaluation/Compose suite | 172 passed / 1 warning |
| Agent/provider/permissions/storage/workers/evaluation/scale regressions | 581 passed / 1 warning |
| Full primary backend | 1814 passed / 188 warnings / zero failures |
| Compile/import, no-credential Settings and Agent refusal | PASS |
| Route inventory | 90 unique method/path pairs; zero new routes |
| SQLite fresh/reopen | v7/v7; zero migrations |
| Clean committed implementation | 1780 passed / 34 expected artifact skips / 148 warnings / zero failures |
| Clean credential tests and no-secret API/evaluation imports | 33 passed; imports, 90 routes, v7/v7 PASS |
| Final committed HEAD | Final clean gate and normal push recorded in closing chat |

Baseline: primary 1779/188 warnings; clean 1745/34 expected artifact skips/148
warnings. This change adds 35 cases (33 new credential cases and two fallback
secret API cases). No production frontend, dependency, lockfile, migration or
route change. Inherited frontend: 94 files/818 tests, TypeScript/build PASS;
not rerun. Existing bundle warning and optional Ragas remain unchanged.

The first attempted test command used system Python and failed collection
because backend dependencies were absent there. Successful gates use the
existing repository `.venv`. A new guard test initially used the wrong telemetry
helper signature and was corrected before the passing gates. Diff review also
restored accidentally changed Unicode lines before full validation.

## Deployment and security follow-up

Both GitHub Actions workflows and Dockerfile were audited: no numbered Groq
secret references and no embedded keys. Backend CI is hermetic and does not use
Groq repository secrets; no GitHub secret rename is required by these workflows.
External deployments must configure the two current names and intentionally
choose strict primary or pool. Secret storage outside Git was not changed.
This Windows validation does not certify GitHub Linux CI: its previously observed
OpenAPI hash mismatch is an existing separate limitation.

Removing slots does not revoke keys. After checking external project usage,
consider manually revoking former KEY1, KEY2, KEY3, KEY4 and the unused second
fallback in Groq. Former KEY5 remains active as the primary. No remote revocation,
live Groq call or quota use was performed.

No secrets, runtime DBs, raw diagnostics, generated data, build outputs or caches
are included. The same 12 unrelated untracked paths are preserved. Historical
receipts and dated journal sections remain unchanged. Main-only work uses normal
push with a final upstream-movement check; no force, rebase or destructive cleanup.

## Residual legacy references

Unexplained active legacy references: **0**.

- Old dated `PROJECT_STATE.md` sections, README's controlled probe, improvement/
  UX reports, KEY5 smoke JSON, completed UX recovery/workspace/master plans and
  implementation-progress entries are HISTORICAL RECEIPT. Their credential
  descriptions remain facts about those completed runs, not current setup.
- `tests/test_credential_consolidation.py` names removed variables solely to
  prove they cannot supply active credentials: ACTIVE TEST, explicit backward
  compatibility. This receipt's former-name table is ACTIVE DOCUMENTATION,
  explicit migration history. Current project-state entries use the same rule.
- Retained `key5_only` occurrences in runtime/types/scripts/tests/current docs
  describe the frozen compatibility identifier. Frontend policy types are
  unchanged. Historical telemetry aliases in request-ledger tests prove old
  metadata remains accepted. `agent-key-1` in durable tests is an unrelated
  idempotency key, not a credential slot.
- Generic secret-name denylist entries are ACTIVE RUNTIME/TEST protection;
  current primary/fallback references are active configuration, not residual
  numbered-slot dependencies.

The following table classifies every pre-migration search occurrence. Final
runtime/config/fixture/setup audit found no removed-field reader. New references
in ARCHITECTURE are ACTIVE DOCUMENTATION; new credential tests are ACTIVE TEST;
this receipt and the current CRED journal section are ACTIVE DOCUMENTATION.

## Next action

OBS-001 — Performance Attribution & Safe Observability, as a separate task.
STOP; no OBS-001 implementation, new telemetry, performance spans or benchmark.

## Reference audit classification

Before changes: 201 matching lines in 44 tracked files. All tracked files were searched, including workflows, Docker, decomposer, correction, evaluation jobs and model tests. The table assigns every matched occurrence by its original line number.

| File | Classification and original lines |
| --- | --- |
| `.agents/skills/rag-ui-ux/SKILL.md` | ACTIVE DOCUMENTATION: 68, 69 |
| `.env.example` | ACTIVE CONFIG: 1, 2, 3, 4, 5, 6, 7, 8, 10 |
| `PROJECT_STATE.md` | HISTORICAL RECEIPT: 2584, 2585, 2605, 2607, 2660, 4409, 4456, 4884, 5292, 5293, 5300, 5908, 5941 |
| `README.md` | HISTORICAL RECEIPT: 857; ACTIVE DOCUMENTATION: 1482, 1483, 1484, 1485, 1486, 1487, 1488, 1489, 1520, 1521, 1714 |
| `configs/settings.py` | ACTIVE RUNTIME: 68, 69, 70, 71, 72, 73, 74, 76 |
| `docker-compose.yml` | ACTIVE CONFIG: 18, 19, 20, 21, 22, 23 |
| `docs/IMPROVEMENT_ROUND_REPORT.md` | HISTORICAL RECEIPT: 12, 13, 23 |
| `docs/KEY5_SMOKE_RECEIPT.json` | HISTORICAL RECEIPT: 4 |
| `docs/UX_IMPROVEMENT_ROUND_REPORT.md` | HISTORICAL RECEIPT: 40, 54, 128, 148, 228 |
| `docs/UX_RECOVERY_GOAL_PLAN.md` | HISTORICAL RECEIPT: 29, 189, 208 |
| `docs/WORKSPACE_COMPLETION_PLAN.md` | HISTORICAL RECEIPT: 174 |
| `docs/frontend/FINAL_MASTER_EXECUTION_PLAN.md` | HISTORICAL RECEIPT: 52, 203 |
| `docs/frontend/FRONTEND_CONTRACT.md` | ACTIVE DOCUMENTATION: 142 |
| `docs/implementation-progress.md` | HISTORICAL RECEIPT: 972 |
| `frontend/src/lib/agentTypes.ts` | ACTIVE RUNTIME: 54 |
| `frontend/src/lib/workspaceBackup.ts` | ACTIVE RUNTIME: 35 |
| `scripts/benchmarks/scale_002_runtime.py` | ACTIVE TEST: 343, 345, 346 |
| `scripts/diagnostics/planner_wording_check.py` | ACTIVE RUNTIME: 37, 38, 42, 45, 46, 47 |
| `scripts/run_bilingual_evaluation_campaign.py` | ACTIVE RUNTIME: 130, 132, 136, 138, 380 |
| `scripts/run_evaluation.py` | ACTIVE RUNTIME: 399, 400, 404, 407, 408, 409 |
| `src/agent/provider_models.py` | ACTIVE RUNTIME: 17 |
| `src/evaluation/phase2_runtime.py` | ACTIVE RUNTIME: 86, 89, 90, 93, 96, 97, 98, 109, 115, 116, 117, 118, 119 |
| `src/generation/generator.py` | ACTIVE RUNTIME: 160 |
| `src/generation/provider_policy.py` | ACTIVE RUNTIME: 12, 28, 29, 31, 38, 39, 40, 41, 42, 57, 62, 65, 66, 68, 71, 78 |
| `src/workspace/jobs.py` | ACTIVE RUNTIME: 83, 234, 235, 236, 237, 238, 239, 240 |
| `src/workspace/repository.py` | ACTIVE RUNTIME: 100, 133, 134, 135, 136, 137, 138, 139 |
| `src/workspace/telemetry.py` | ACTIVE RUNTIME: 173, 174, 175, 176, 177, 178, 179 |
| `src/workspace/transfer.py` | ACTIVE RUNTIME: 61, 268, 269 |
| `tests/integration/agent_product_server.py` | ACTIVE TEST: 88, 89, 92 |
| `tests/integration/final_product_server.py` | ACTIVE TEST: 95, 96, 99 |
| `tests/integration/harness_server.py` | ACTIVE TEST: 60, 61 |
| `tests/integration/provider_product_server.py` | ACTIVE TEST: 21, 22, 23, 25, 81 |
| `tests/integration/scale_product_server.py` | ACTIVE TEST: 20, 21, 22, 24, 84 |
| `tests/test_agent_durable.py` | ACTIVE TEST: 43, 123, 128, 129 |
| `tests/test_agent_provider.py` | ACTIVE TEST: 35, 341, 342 |
| `tests/test_agent_provider_api.py` | ACTIVE TEST: 19, 20, 21, 82 |
| `tests/test_agent_worker.py` | ACTIVE TEST: 221 |
| `tests/test_generator_key_rotation.py` | ACTIVE TEST: 45, 65 |
| `tests/test_registries.py` | ACTIVE TEST: 42, 43, 44, 45, 46 |
| `tests/test_release_compose_contract.py` | ACTIVE TEST: 42, 43, 44, 45, 46, 71, 72 |
| `tests/test_request_ledger.py` | ACTIVE TEST: 107, 123 |
| `tests/test_run_evaluation_phase2.py` | ACTIVE TEST: 674, 675, 676, 677, 678, 679, 680 |
| `tests/test_workspace_access.py` | ACTIVE TEST: 340 |
| `tests/test_workspace_persistence.py` | ACTIVE TEST: 487 |
