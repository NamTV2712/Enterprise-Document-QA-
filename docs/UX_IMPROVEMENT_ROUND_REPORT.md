# SEC Research Workspace — P0–P14 improvement receipt

Date: 2026-09-08
Branch: `codex/bilingual-research-workspace`
Scope: local frontend/backend improvement, provider smoke validation, and
source-backed architecture artifacts. No merge, Vercel deployment, corpus
regeneration, index regeneration, or official benchmark promotion was performed.

## Outcome

The SEC Research Workspace is now organized around the research journey rather
than a generic dashboard: ask a question, inspect the answer, open evidence,
search the indexed corpus, review saved conversations, and use advanced tools
when needed. The shell uses semantic Light/Dark tokens, the primary navigation
has explicit Overview/Conversation/Documents/Search/Library destinations, and
advanced retrieval/evaluation/architecture/system surfaces are grouped under
Tools.

The implementation keeps the existing RAG contract and local corpus intact.
Technical details remain available in provider-free tools or progressive
disclosure surfaces instead of competing with the answer and citation workflow.

## Phase status

| Phase | Status | Evidence / result |
|---|---|---|
| P0 — baseline and issue register | Complete | Existing UI baseline and target references were captured in the local `rag-ui-ux` skill; issues are listed below and were checked against the current repository and browser matrix. |
| P1 — skill and documentation layer | Complete | Four external skill repositories were read before UI implementation; project-local `.agents/skills/rag-ui-ux` was created and validated. `AGENTS.md` now points future UI work to the skill and frontend contracts. |
| P2 — product blueprint | Complete | Product/workflow/design decisions are recorded in `docs/frontend/DESIGN.md`, `docs/frontend/FRONTEND_CONTRACT.md`, and the local skill references. |
| P3 — CSS and primitives | Complete | `frontend/src/index.css` is an imports-only entry point for tokens, components, base rules, and motion; semantic surfaces, borders, focus rings, density, and reduced-motion behavior are centralized. |
| P4 — shell, navigation, and state boundaries | Complete | `WorkspaceView` routes and header/sidebar navigation cover Overview, Conversation, Documents, Search, Library, Retrieval Lab, Architecture, Evaluation, Analytics, and System. Existing conversation/library flows remain intact. |
| P5 — API reader and request state | Complete | Added safe `GET /chunks/{chunk_id}` detail retrieval and wired the evidence reader with abortable loading, fallback, and error states. No filesystem path is exposed. |
| P6 — Documents and connection recovery | Complete | Documents and connection state retain explicit loading, empty, offline, error, and retry/recovery surfaces; request ownership and stale-result protection remain bounded to the active view. |
| P7 — Chat, Markdown, and citations | Complete | Existing streaming, stop/partial-answer, Markdown, citation deep-link, evidence rail, copy, notes, and source-reader behavior was preserved and exercised by browser tests. |
| P8 — Search and utility workflow | Complete | Added provider-free Search workspace using `/retrieval/inspect`, explicit scope controls, empty/offline/error states, and a deliberate “Use in Research” handoff without auto-sending a query. |
| P9 — Library and advanced tools | Complete | Library remains the local persistence surface; advanced tools are grouped and reachable, with the legacy Retrieval Lab route preserved for existing workflows and tests. |
| P10 — Archify diagrams | Complete | Three source-backed Archify artifacts were generated, validated at `showcase` quality, delivered as standalone HTML, and copied to `frontend/public/architecture/` for lazy iframe loading. |
| P11 — performance | Complete | Tool/architecture/search panels are lazy-loaded; CSS ownership is consolidated. Production Library search stayed below the 200 ms p95 budget: 40.49 ms Chromium and 80.02 ms Firefox in the final one-worker browser run. |
| P12 — visual QA and regression | Complete | Production browser matrix covered Light/Dark, 390/640/768/1440 px layouts, reduced motion, accessibility scans, citation interactions, and tool routes. Archify visual checks passed all requested desktop sizes and themes; representative light/dark diagrams were manually inspected. |
| P13 — live smoke with KEY5 | Complete | Redacted receipt in `docs/KEY5_SMOKE_RECEIPT.json`: six bounded English/Vietnamese single, comparison, and insufficient-evidence cases returned HTTP 200 under `key5_only`. No N=30 replay was run. |
| P14 — handoff and close | Complete | README, project journal, operating guide, skill, architecture artifacts, smoke receipt, and this report are updated. Local preview instructions are below. |

## Issue register and resolution

| ID | Problem observed | Resolution |
|---|---|---|
| UX-001 | Header/sidebar mixed too many destinations and made the research journey hard to parse. | Added a small primary workspace IA and grouped technical destinations under Tools. |
| UX-002 | Long product labels and titles could clip or consume the answer viewport. | Added compact responsive labels, bounded text, ellipsis rules, and mobile-specific navigation. |
| UX-003 | Search and architecture were not first-class destinations. | Added validated `WorkspaceView` routes, command-palette entries, lazy Search, and Architecture views. |
| UX-004 | Offline, empty, loading, and API error states could look like the same blank result. | Kept explicit state boundaries and provider-free fallback surfaces in Documents, Search, reader, and connection UI. |
| UX-005 | Evidence could be discoverable but not readable in full. | Added safe chunk detail retrieval and abortable full-text loading in the evidence rail. |
| UX-006 | CSS ownership was difficult to reason about after several UI passes. | Split the stylesheet into tokens, components, base, and motion imports while preserving the existing user-authored baseline separately. |
| PERF-001 | Large tool and diagram surfaces competed with initial chat load. | Lazy-loaded tool routes and architecture panel; diagrams are standalone static artifacts loaded on demand. |
| OPS-001 | `key5_only` could still construct a multi-key generator pool at startup. | Fixed generator key selection to honor the effective policy, so key5-only startup creates a single-key client. |
| QA-001 | Local `frontend/.env.local` points at the ngrok demo URL while offline browser fixtures need loopback. | Did not rewrite user environment configuration; browser validation explicitly builds with `VITE_API_BASE_URL=http://127.0.0.1:8000`. |

## Design and implementation decisions

The external references were used as layered review inputs, not competing
design authorities:

- Product cognition and UX quality gates informed the workflow, state matrix,
  progressive disclosure, recovery paths, responsive behavior, and anti-generic
  UI checks.
- The frontend-design reference informed the visual direction: a restrained
  SEC research workspace with strong typography, evidence-oriented hierarchy,
  semantic surfaces, and a deliberate Light/Dark identity.
- The frontend implementation reference informed React/TypeScript component
  boundaries, lazy loading, interaction states, and production validation.
- UI/UX Pro Max was used as the final accessibility, form, navigation,
  responsive, and interaction audit layer; product-specific RAG behavior took
  precedence where a generic checklist would be misleading.

The product is a research workspace for analysts who need grounded answers from
SEC 10-K filings. Its core objects are questions, answers, citations, source
chunks, filings, conversations, retrieval traces, evaluation reports, and local
annotations. The primary success criterion is not merely “an answer rendered”:
the user must be able to understand the answer, verify the supporting source,
recover from a missing backend or weak retrieval result, and return to prior
research without losing local work.

## Archify deliverables

Archify was pinned to revision `06bd6fea5752bc06b8170a1f09085c798df5aa13` and
passed its doctor check. The diagrams use repository evidence and the inspected
backend/retrieval/frontend boundaries; they do not invent a new runtime
architecture.

| Artifact | Source IR | Standalone viewer |
|---|---|---|
| Workspace architecture | [`sec-research-workspace.architecture.json`](architecture/sec-research-workspace.architecture.json) | [`sec-research-workspace.html`](architecture/sec-research-workspace.html) |
| Query dataflow | [`sec-research-query.dataflow.json`](architecture/sec-research-query.dataflow.json) | [`sec-research-query.html`](architecture/sec-research-query.html) |
| Research workflow | [`sec-research-workflow.workflow.json`](architecture/sec-research-workflow.workflow.json) | [`sec-research-workflow.html`](architecture/sec-research-workflow.html) |

Each artifact passed `archify validate --quality showcase` with zero errors and
zero warnings. The final browser visual-check receipts passed Light/Dark at
1440×900 and 2048×1320 with no horizontal or vertical overflow. Redundant
supporting cards were removed from the query/workflow standalone views after
visual validation showed they created first-screen overflow; the primary nodes,
labels, lanes, and guided views remain present.

## Verification record

The following checks were run against the local working tree:

```text
frontend: bun run lint                         PASS
frontend: bun run test                         PASS (current Vitest suite)
frontend: VITE_API_BASE_URL=loopback bun run build; bunx playwright test --workers=1
                                                 PASS (106 browser checks)
frontend: VITE_API_BASE_URL=loopback bun run build
                                                 PASS
backend:  python -m compileall -q src tests     PASS
backend:  pytest -q tests/test_api.py           PASS (54 passed)
backend:  pytest -q tests/test_generator_key_rotation.py tests/test_provider_budget.py
                                                 PASS (6 passed)
```

The production browser suite covers 106 Chromium/Firefox checks and the final
stateful run passed all 106 with `--workers=1`. A parallel exploratory run
exposed timing sensitivity in IndexedDB/Web Locks, so the one-worker command is
the reproducible release gate. The loopback build is important: the checked-in local environment file points
to the public ngrok demo URL, while the test fixtures intentionally mock the
local API.

## KEY5 smoke receipt

The backend was started with one worker and `GROQ_KEY_POLICY=key5_only`, which
is required for local Qdrant mode. Health and readiness both returned 200 and
the server loaded 10,053 indexed chunks. The six-case smoke returned:

| Case group | Cases | Result |
|---|---:|---|
| Single query | 2 | HTTP 200; 2 sources each |
| Comparison/decomposed query | 2 | HTTP 200; 2 sources each |
| Insufficient evidence | 2 | HTTP 200; explicit fallback each |

The detailed redacted data is [`KEY5_SMOKE_RECEIPT.json`](KEY5_SMOKE_RECEIPT.json).
No key value, request header, or secret was written to the repository. This was
a bounded smoke only; it does not reclassify the official benchmark or claim
that a provider campaign completed.

## Local preview and handoff

Run the backend from the repository root:

```powershell
$env:GROQ_KEY_POLICY = "key5_only"
.venv\Scripts\python.exe -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --workers 1
```

In a second terminal, run the frontend with a loopback API for local viewing:

```powershell
cd frontend
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
bun run dev
```

Open [http://localhost:3000/](http://localhost:3000/) and use the workspace
navigation. A production-like local preview is available with `bun run build`
followed by `bun run preview --host 127.0.0.1 --port 4173`.

The Vercel URL was not updated in this task. Deployment remains a separate
explicit action because the frontend is independently hosted and the backend
origin/CORS/ngrok lifecycle must be coordinated before publishing.

## Scope preserved

- `data/` corpus, chunks, embeddings, Qdrant storage, and evaluation artifacts
  were not deleted, moved, regenerated, or rewritten.
- The official benchmark remains the documented clean priority evaluation; no
  checkpoint-mixed result was promoted.
- `.env` values were not printed or committed, and the smoke receipt contains
  only the alias `key5` and policy metadata.
- The original user-authored `frontend/src/index.css` baseline was preserved
  outside the repository before the imports-only stylesheet refactor.

## 2026-09-08 correction receipt

The first visual pass was not accepted as final after real browser screenshots
showed a 350px inherited tool column, a persisted oversized sidebar, a mobile
header overlap, and raw transport errors. The corrective work is intentionally
architectural rather than cosmetic:

- The desktop sidebar is a fixed 216px navigation rail with one scroll owner;
  the stored resize path and duplicate Library/Research navigation were
  removed.
- Only a conversation with retrieved evidence creates the evidence-rail grid.
  Documents, Retrieval Lab, Evaluation, Architecture, Analytics, and System
  use their full primary canvas and their own adaptive grids.
- The composer owns current scope, Top K, and comparison settings; the chat
  empty state offers examples that fill the draft but never auto-send.
- Documents maintains separate list/chunk errors and retries; all workspace
  fetch surfaces map unreachable backend, timeout, quota, and server errors
  to safe recovery copy.
- Architecture is a launcher for the three standalone Archify artifacts. The
  README now links the viewers and includes an artifact-bound static preview.
- Browser testing now rebuilds with `VITE_API_BASE_URL=http://127.0.0.1:8000`
  for hermetic fixtures; it no longer inherits `.env.local`. The e2e suite
  follows the collapsed Tools navigation and guards wide-tool geometry.

Final correction checks: TypeScript/lint passed, Vitest passed `110/110`, the
production build passed, targeted Chromium responsive/keyboard/tool checks
passed `7/7`, the guided tool route passed, and Library search p95 measured
`40.59 ms` over 100 samples (budget `<200 ms`). Visual inspection covered
desktop light/dark retrieval and evaluation, mobile Documents recovery, and
the mobile header at 390px. No deployment was performed, and no Groq request
was necessary or made in this correction pass.

## 2026-09-09 verification addendum

This follow-up verified the current working tree after the evidence-bound
execution-transparency additions. Four residual direct color utilities in
message, tooltip, sub-query, and error-recovery components now resolve through
the shared semantic tokens. The HTTP/SSE integration selector was also updated
to use the current scope popover and listbox accessibility contract rather
than the removed native-select DOM id.

- Frontend: TypeScript/lint, `131/131` Vitest tests, and the production build
  passed. The one-worker production browser matrix previously passed
  `108/108` checks; Library-search p95 remained below the 200 ms budget.
- Integration: the real local FastAPI harness and fragmented SSE proxy passed
  `14/14` Chromium/Firefox checks after the selector update.
- Backend: the full hermetic suite passed `730` tests (the 121 existing parser
  warnings are unchanged).
- Provider scope: no new Groq call was made. The bounded six-case
  `key5_only` result remains the redacted receipt dated 2026-09-08; this
  addendum did not alter provider-selection code or claim a new live run.
