# Workspace completion plan

This document is the executable handoff for the bilingual research workspace
round. It is intentionally separate from `PROJECT_STATE.md`: this file tracks
the work package and acceptance gates, while the project journal records the
evidence produced by each run.

## Scope lock

- Product: personal/demo SEC research workspace for an AI Engineering and Data
  Science portfolio.
- Runtime: React/Vite frontend, FastAPI backend, local Qdrant, existing
  retrieval and V7 context rendering.
- Languages: English and Vietnamese UI/query support; no automatic LLM
  translation request.
- Provider budget: at most 120 real provider requests for the whole round,
  including retries and unknown outcomes. SDK retries are disabled.
- Explicitly out of scope: authentication, cloud sync, multi-user accounts,
  uploading private documents, paid services, public deployment, changing the
  official benchmark, and rebuilding the canonical corpus/index.
- Data boundary: `data/` remains local and ignored. Campaign receipts,
  checkpoints, diagnostic output, and secrets stay outside Git.

## Execution order and status

| Milestone | Deliverable | Current status | Evidence / next action |
|---|---|---|---|
| P0 | Baseline manifest, plan, tracking, isolated run IDs | PASS (offline) | Evidence Contract v3 manifest remains immutable; bilingual manifest is registered as `bilingual_evaluation_v1_window_02` with provider calls `0` |
| P1 | VI/EN query normalization, language binding, interpretation | PASS (offline) | `src/retrieval/query_normalizer.py`, API tests, frontend language tests |
| P2 | Durable Library, backup/import, multi-tab safety | PASS (offline) | `frontend/src/lib/conversationStore.ts`, state-chain and browser tests |
| P3 | Catalog, retrieval trace, public evaluation contract/API | PASS (offline) | Strict allowlisted publisher, `/evaluation/runs`, `/evaluation/runs/{id}`, path/schema/provenance tests |
| P4 | Navigation, URL state, VI/EN, light/dark, accessibility | PASS (offline, serial browser gate) | Evaluation/Analytics views, URL view state, EN/VI surfaces, theme and responsive gates; Chromium must use one worker in this Windows environment |
| P5 | Research utilities | PARTIAL | Templates, command palette, evidence collections, notes up to 10k, bookmarks/feedback/export are in; tags and answer variants remain |
| P6 | Evidence and Document Explorer | PARTIAL | Explorer and citations exist; add source highlight/deep-link and contract-facing checks |
| P7 | Retrieval Lab and architecture showcase | PASS (offline) | Preset comparison, timing/score-scale warning, JSON/CSV export; architecture/API docs remain a documentation polish item |
| P8 | Evaluation dashboard and experiment comparison | PASS (offline) | Validated public report publisher/API, recorded demo fixture, live/recorded dashboard and provenance display |
| P9 | Analytics, diagnostics and guided demo | PASS (offline) | Metadata-only local analytics, redacted export/clear, recorded evaluation mode and explicit provider-free wording |
| P10 | Offline freeze and 120-query fixture matrix | PARTIAL | Authored 40 × EN/VI/accentless = 120 fixture matrix and tests; final full browser/HTTP/Docker freeze remains |
| Provider A | Evidence Contract v3 campaign, max 60 requests | INCOMPLETE | Prior ledger is closed after 429; create a new campaign ID only after quota is available |
| Provider B | Bilingual campaign, max 60 requests | REGISTERED, NOT STARTED | `bilingual_evaluation_v1_window_02` manifest/runner are provider-free; execute only after quota and offline gates, then use a new campaign id if incomplete |
| P11 | Docker candidate receipt | PASS for current offline candidate | `data/diagnostics/local_release_receipt_bilingual.json`; rebuild if source/build inputs change |
| P12 | Docs, staged diff, PR, CI and handoff | IN_PROGRESS | PR #3 is open and green; update description and wait for final CI; do not merge/deploy |

## Dependency graph

1. Finish P0 tracking and public-report schemas.
2. Finish P3 publisher/API before P8; it is the only authority for dashboard
   data and must reject incomplete or unbound reports.
3. Add P4 route/view shell, then P5/P6/P7 user flows. These must remain
   provider-free and must not alter production retrieval defaults.
4. Add P8/P9 dashboard, local analytics, recorded demo, and export paths.
5. Expand P10 fixtures and run all offline gates. Freeze source bindings.
6. Run Provider A and B only if quota is explicitly available. A 429/quota
   stop records `INCOMPLETE`; it never becomes semantic PASS or FAIL.
7. Rebuild Docker from the final source SHA, generate a non-secret receipt,
   update docs, push, and verify CI.

## Acceptance gates

### Offline gates

- Backend full suite, `compileall`, frontend unit tests, typecheck, lint,
  production build, contrast, Chromium and Firefox browser suites, and HTTP/SSE
  integration all pass.
- Every public evaluation report has a schema, source artifact hash, corpus /
  model / profile / rubric bindings, run status, and a non-empty case
  denominator. Invalid, incomplete, or arbitrary-path reports are rejected.
- Retrieval Lab uses no provider call and its displayed trace is observationally
  equal to the selected retrieval output.
- Recorded mode is visibly labelled and makes zero provider requests.
- Analytics distinguishes local activity from measured backend/provider usage;
  export redacts questions, answers, source text, session IDs and secrets by
  default.
- VI/EN × light/dark works at 390/768/1440px, keyboard-only primary flows work,
  IME composition is preserved, reduced motion is honoured, and axe has no
  serious/critical violation.

### Provider gates

- Campaign A: F=1 per case, dependency AR=1, Microsoft risk AR >= 0.95,
  aggregate AR >= 0.975 and CP >= 0.67 for both independent replicates.
- Campaign B: F=1 per case, AR >= 0.95 per case, aggregate AR >= 0.975 per
  replicate, and no protected fact disagreement. Vietnamese AR may not be more
  than 0.05 below the matching English intent.
- Legacy scores are reported separately and never replace the v3 gates.
- Candidate is GO only when both campaigns are provider-complete and all
  registered gates pass. Otherwise handoff is
  `IMPLEMENTATION COMPLETE / VALIDATION INCOMPLETE` or `NO-GO` with reasons.

## Safe commands and resume rules

```powershell
# Offline validation from the repository virtual environment
.\.venv\Scripts\python.exe -m pytest -q --disable-warnings
.\.venv\Scripts\python.exe -m compileall -q src tests
Set-Location frontend
bun run test
bun run typecheck
bun run build
Set-Location ..

# Register a new provider window only after quota is confirmed; never resume a
# closed incomplete ledger and never use --fresh to delete receipts.
.\.venv\Scripts\python.exe -m scripts.diagnostics.evidence_contract_v3_manifest `
  --campaign-id evidence_contract_v3_window_02
.\.venv\Scripts\python.exe -m scripts.run_evidence_contract_v3_campaign `
  --campaign-id evidence_contract_v3_window_02

# Provider B: preflight is safe and makes zero provider calls. The explicit
# execution command is intentionally separate and consumes the 60-slot ledger.
.\.venv\Scripts\python.exe -m scripts.diagnostics.bilingual_evaluation_manifest `
  --campaign-id bilingual_evaluation_v1_window_02
.\.venv\Scripts\python.exe -m scripts.run_bilingual_evaluation_campaign `
  --campaign-id bilingual_evaluation_v1_window_02
# Only after an explicitly confirmed provider window:
.\.venv\Scripts\python.exe -m scripts.run_bilingual_evaluation_campaign `
  --campaign-id bilingual_evaluation_v1_window_03 --execute
```

The campaign ledger reserves a slot before each transport attempt. A retry,
429, timeout, or unknown outcome consumes that slot. There is no R3 and no
sample selection after seeing scores.

## Handoff record

At source freeze update this section with the actual values, not estimates:

- source SHA:
- PR:
- CI run IDs:
- backend/frontend/browser gate counts:
- Docker image ID and receipt SHA:
- Campaign A manifest/ledger/report hashes and request count:
- Campaign B manifest/ledger/report hashes and request count:
- final state: `GO`, `NO-GO`, or `VALIDATION INCOMPLETE`:
- known limitations and exact resume command:
