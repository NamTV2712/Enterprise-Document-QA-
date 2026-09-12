# Enterprise Document QA improvement round report

Date: 2026-09-07
Branch: `codex/bilingual-research-workspace`
Scope: QA correctness, provider accounting, backend/frontend performance, and the compact Light/Dark research workspace.

## Scope decisions

- The existing canonical corpus and Qdrant index were treated as immutable.
- The reader uses existing retrieved excerpts, citations, and safe metadata. No
  PDF viewer or filesystem-backed document feature was added.
- All provider-backed calls in this improvement round used `GROQ_API_KEY5`
  through the strict `key5_only` policy. No fallback key was used.
- The provider budget was capped at 2,000 durable attempts for this round.
- Local and Docker CPU execution were verified. Merge and deployment remain
  separate manual decisions.

## Milestone closure

| Milestone | Result | Evidence |
|---|---|---|
| M0 audit and baseline | PASS | Source/history audit, canonical artifact identity, and immutable `data/` boundary preserved. |
| M1 strict provider policy and accounting | PASS | `src/generation/provider_policy.py`, `GROQ_KEY_POLICY=key5_only`, append-only `ProviderBudgetLedger`; `319/2000` slots reserved, `316` completed, `3` terminal transport errors, `0` unknown reservations. |
| M2 acceptance/performance harness | PASS | Fresh campaign IDs, immutable checkpoints, strict faithfulness/relevancy/precision gates, frontend Library p95 `70.31 ms` Chromium and `66.93 ms` Firefox. |
| M3 bilingual QA correctness | PASS | Deterministic bounded renderers for dependency, major-risk, international-risk, and growth comparison; Round7 passed both English/Vietnamese replicates. |
| M4 compact workspace layout | PASS | `EvidenceWorkspaceRail` adds a desktop source rail while preserving the center conversation and responsive mobile layout. |
| M5 semantic Light/Dark design system | PASS | Semantic surface/state/evidence tokens, no decorative gradients/glows, WCAG contrast gate green. |
| M6 evidence utility | PASS | Existing excerpt text, source number, filing date, section, ticker, and score are available in the rail reader; no PDF feature was introduced. |
| M7 frontend performance | PASS | Lazy-loaded tool panels, indexed Library search, debounced Document Explorer requests with abort/stale guards, and Analytics ranges (`24h`, `7d`, `30d`, `all`). |
| M8 backend performance/telemetry | PASS | Startup document/chunk metadata indexes, structured provider quota/unavailable errors, client rate-limit retry metadata, and provider-event counters. |
| M9 provider campaign gates | PASS | Round7 `COMPLETE / GO`, `54/60` campaign requests, both replicates passed. Earlier immutable rounds remain recorded as provenance. |
| M10 freeze and packaging | PASS | Backend, frontend, mocked browser, HTTP/SSE integration, compile, Docker Compose config, and CPU runtime image smoke all passed. |
| M11 handoff | PASS | This report, `PROJECT_STATE.md`, and `README.md` updated; generated diagnostics remain under ignored `data/diagnostics`; no merge/deploy performed. |

## Provider campaign receipt

The fresh improvement campaigns were run with unique IDs and only KEY5:

| Campaign | Requests | Result |
|---|---:|---|
| `bilingual_evaluation_improvement_round1_key5` | 2 | `INCOMPLETE` after transport interruption; closed and not resumed |
| `bilingual_evaluation_improvement_round2_key5` | 52 | `COMPLETE / NO-GO`, semantic quality |
| `bilingual_evaluation_improvement_round3_key5` | 53 | `COMPLETE / NO-GO`, semantic quality |
| `bilingual_evaluation_improvement_round4_key5` | 52 | `COMPLETE / NO-GO`, one risk-faithfulness case |
| `bilingual_evaluation_improvement_round5_key5` | 53 | `COMPLETE / NO-GO`, precision gate calibration |
| `bilingual_evaluation_improvement_round6_key5` | 53 | `COMPLETE / NO-GO`, growth renderer over-claim |
| `bilingual_evaluation_improvement_round7_key5` | 54 | `COMPLETE / GO`, both replicates passed |

Round7's bounded growth output reports AWS at `20%` and Microsoft Cloud at
`23%`, cites Sources 1 and 3, and avoids deriving a percentage-point
difference or inventing revenue units. The round status is recorded in
`data/diagnostics/bilingual_evaluation_improvement_round7_key5_status.json`.

## Verification receipt

- Backend: `727 passed, 121 warnings`.
- Python compile: `python -m compileall -q configs src scripts tests`.
- Frontend: TypeScript/lint, `107/107` Vitest tests, and production build.
- Mocked browser: `106/106` Chromium/Firefox checks with one worker.
- HTTP/SSE integration: `14/14` Chromium/Firefox checks with one worker.
- Docker image: `edqa-api:improvement-round`, image digest
  `sha256:8c96f2715666b35bff93bacec1a6d285e62c9fe0a122c3f5e2feda81a653f160`.
  The CPU image preloaded both pinned models; a temporary container reached
  `pipeline_ready=true`, reported `50` searchable companies, `10,053` indexed
  chunks, and `50` supported tickers.
- Docker Compose: `docker compose config --quiet` passed.

## Handoff limits

The official priority-2 benchmark, canonical corpus/index, and public
evaluation reports were not changed or promoted. The provider campaign is a
candidate acceptance receipt, not an official benchmark replacement. The
branch is ready for review; merge, deployment, and any public evaluation
promotion remain manual.
