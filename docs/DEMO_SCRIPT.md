# SEC Research Copilot — 5–7 Minute Demo

Public display name: **SEC Research Copilot** (original repository: Enterprise Document QA).

A seven-minute recording plan with an executable provider-free path. See the
[README](../README.md), [case study](PORTFOLIO_CASE_STUDY.md) and
[release evidence](IMPROVEMENT_FINAL_RECEIPT.md).

The [Live Demo](https://frontend-one-gamma-f9jf11u8ec.vercel.app) is the running
frontend preview, separate from this recording guide. It reported **API offline**
on 2026-10-03; use the prepared local environment below for the recording.

## Choose the demonstration environment

The default below uses the existing TEST-005 local harness. It runs real FastAPI
routes, access controls, DATA-004 SQLite, workers, events and native evaluation;
corpus/model/provider dependencies are synthetic. Quick answer text and the
successful Agent decisions are fixtures, not live inference or financial advice.
Keep that distinction visible in the recording title or opening narration.

The Deep composer sends a generic goal. The harness's successful research script
requires an explicitly declared objective, so prepare that terminal run through
the API. During the recording, create a separate generic run in the UI using the
harness's waiting mode to show durable progress and cancellation, then inspect
the prepared successful run for result/evidence/evaluation. Do not imply that
the generic composer automatically created the structured objective.

Alternatively, use an already prepared local product workspace with approved
provider configuration and existing terminal results. Rehearse its behavior
before recording; show an unavailable state honestly if configuration is missing.
The recording does not require a live Groq call.

## Off-camera preparation

### 1. Dependencies and isolated backend

Use the dependency-install portion of [Local Setup](../README.md#local-setup)
and [frontend setup](../frontend/README.md#local-development). Skip SEC download,
chunking, embedding and indexing for this fixture demo. Use Bun 1.3.14 and a
Python environment with the declared requirements. No real `.env`, private
corpus, Groq key or model download is needed by the harness.

Terminal A, from the repository root, PowerShell:

```powershell
$env:TEST005_WORKSPACE_MODE = 'local'
$env:TEST005_API_PORT = '8788'
$env:TEST005_RUNTIME_DIR = Join-Path ([System.IO.Path]::GetTempPath()) ('edqa-portfolio-' + [guid]::NewGuid())
.venv\Scripts\python.exe tests/integration/agent_product_server.py
```

The server binds only `127.0.0.1:8788`, uses the fresh runtime directory and
enforces an offline socket guard. Its `__test005__` controls exist only in the
test server. Keep this harness on loopback; it is not a deployment entry point.

Terminal B, from the repository root:

```powershell
cd frontend
bun install --frozen-lockfile
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8788'
bun run build --outDir dist-agent-product
bunx vite preview --outDir dist-agent-product --port 4187 --strictPort
```

Use exactly `http://localhost:4187` in the browser: the harness allowlists that
Origin. `dist-agent-product` is ignored build output. If either port is already
occupied, stop the conflicting demo process through its own terminal before
rehearsal; do not reuse an unknown server.

### 2. Prepare one successful recorded run

Terminal C, from the repository root:

```powershell
$demoApi = 'http://127.0.0.1:8788'
$demoHeaders = @{
  Authorization = 'Bearer test005-synthetic-local-token-0123456789abcdef'
  Origin = 'http://localhost:4187'
}
Invoke-RestMethod -Method Post -Uri "$demoApi/__test005__/agent/mode" `
  -ContentType 'application/json' -Body '{"mode":"research"}'
$demoBody = @{
  goal = 'Find recorded Apple risk evidence.'
  locale = 'en'
  research = @{
    version = 'agent_research_v1'
    objectives = @(@{
      objective_id = 'apple_risk'
      question = 'Find Apple risk evidence'
      ticker_scope = 'AAPL'
    })
  }
} | ConvertTo-Json -Depth 6
$demoCreateHeaders = $demoHeaders.Clone()
$demoCreateHeaders['Idempotency-Key'] = 'portfolio-recorded-' + [guid]::NewGuid()
$demoRecorded = Invoke-RestMethod -Method Post -Uri "$demoApi/agent/runs" `
  -Headers $demoCreateHeaders -ContentType 'application/json' -Body $demoBody
$demoRecordedId = $demoRecorded.run_id
Invoke-RestMethod -Uri "$demoApi/agent/runs/$demoRecordedId" -Headers $demoHeaders
```

Refresh that last read until terminal. Expected: `succeeded`, the fixture answer
“The recorded Apple filing contains risk evidence.”, two tool calls, canonical
`AAPL:HARNESS` / `AAPL_harness_0000` evidence and 21 native metric results from
`GET /agent/runs/{run_id}/evaluation`. Keep the returned run ID for the recording.
You may bookmark `http://localhost:4187/agent/runs/<the returned run_id>`;
opening it as a full page navigation clears the bearer and requires reconnecting.
Do not record the preparation terminal's Authorization header.

After the prepared run is terminal, select the controllable waiting mode:

```powershell
Invoke-RestMethod -Method Post -Uri "$demoApi/__test005__/agent/mode" `
  -ContentType 'application/json' -Body '{"mode":"waiting"}'
```

In the browser, choose English/light or dark, open Research and start with Quick.
Use a separate demo browser profile/tab state if you want an empty conversation
history; preserve your normal saved Library. Connect only when the script reaches
Deep, using the **public synthetic fixture token** above. Never use a real token
on camera. The input clears after connection and the bearer remains in memory.

### 3. Rehearse once

Confirm Quick streaming and source opening, one Deep card, running → cancelling
→ cancelled, and the prepared inspector's result/evidence/metrics. The waiting
decision deliberately holds until the release command below. Clear pending demo
work before another rehearsal by cancelling it and releasing that boundary.
Keep the prepared run ID, architecture section and CI links ready in browser tabs.
The harness may still display the production decision-provider-unavailable banner:
its test controls inject a scripted model without configuring a real provider.
Explain that fixture distinction; do not present the banner as live model availability.

## Recording flow

### 0:00–0:30 — Problem and project

**Click/show:** README title and product overview, then Research.

**Say:** “Long financial filings are hard to search and compare while retaining
source traceability. I built a production-style SEC research workspace with cited
Quick RAG answers and separately admitted durable Deep Research. This recording
uses deterministic local fixtures; it demonstrates product behavior, not live
model quality.”

**Do not say:** Used by enterprises, production-ready as an absolute, or a
guaranteed accurate financial assistant.

### 0:30–1:15 — Architecture overview

**Click/show:** [README architecture](../README.md#architecture-at-a-glance).
Point to the Quick branch, Deep branch, shared RAG stack and DATA-004 authority.

**Say:** “BM25 and Qdrant rankings are fused, then cross-encoder reranking selects
evidence for grounded generation. Deep uses bounded typed tools and a process-local
worker pool. SQLite owns Agent runs; the browser owns only their references.”

**Do not say:** Each tool calls an independent microservice, the topology is
distributed, or every Deep run uses every tool.

### 1:15–2:30 — Quick answer and source

**Click:** Keep **Quick** selected. Ask “What evidence is available for Apple?”
and submit. Show streamed text, click a citation and inspect the source excerpt
and document identity. Return to the answer and point to follow-up controls.
Click **Research deeper**: show the populated Deep draft without sending yet.

**Say:** “Quick is the ordinary RAG path. A reader can inspect the retrieved source
behind a citation. In this harness the text is synthetic; the real streaming and
source-navigation contracts are being exercised. Research deeper prepares a goal
and requires another explicit submission.”

**Do not say:** The fixture proves financial accuracy, the source date is the
number's fiscal period, or Research deeper automatically executes an Agent.

### 2:30–4:30 — Deep lifecycle, result and evidence

**Click:** Connect the local workspace with the synthetic fixture token. With
**Deep Research** selected, submit “Inspect current Apple risk evidence.”
If decision-provider consent is offered, grant it only for this fixture run.
Observe one run card and **Running**; expand **Research details**. Click
**Request cancellation** and show cancellation acknowledgement.

In Terminal C, off-camera or with only this command visible, release the held
test boundary:

```powershell
Invoke-RestMethod -Method Post -Uri "$demoApi/__test005__/agent/release"
```

Return to the card and show **Cancelled**. Click **Open full run**, point out its
run ID, then select the prepared completed “Find recorded Apple risk evidence.”
entry from **Run history**. This keeps the current memory-only connection.
Show final result, research evidence and the native metrics. Click **Open document**;
if the catalog opens, choose AAPL's **Open document workspace** action. Show the
canonical ID and unavailable full-source state honestly: this fixture retains
indexed excerpts, not an admitted original filing. Quick's citation inspector
provides the excerpt demonstration.

**Say:** “This new generic run demonstrates durable state and revision-safe
cancellation. The cancellation finishes at a safe boundary, which the fixture
holds for presentation. Here is a separate successful run prepared with an
explicit API objective: its result and evidence come from DATA-004, and the
inspector evaluates its terminal record without rerunning the model. The current
generic composer does not synthesize a hidden multi-objective plan.”

**Do not say:** The two run IDs are one run, cancellation kills an external effect,
safe activity is hidden chain-of-thought, or native metrics prove factual accuracy.

### 4:30–5:30 — Engineering internals

**Click/show:** Retrieval design, [worker receipt](WORKER_002_FINAL_RECEIPT.md),
DATA-004 ownership in [architecture](../ARCHITECTURE.md#state-and-persistence),
and the frozen release's [Backend CI](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/runs/37085104945)
and [Frontend CI](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/runs/37085104875).

**Say:** “Claims are atomic and short; provider work is outside transactions.
Two fixed workers wake on a payload-free durable-admission hint, with polling
fallback. Agent API events contain safe execution facts. I verified contracts,
storage, cancellation and HTTP/SSE with provider-free tests.”

**Do not say:** Exactly-once external effects, a global provider concurrency cap,
or that this fixture performs real vector/model inference.

### 5:30–6:30 — Measurements and validation

**Click/show:** README measured improvements and Validation, then the receipts.

**Say:** “In controlled local campaigns, read50 client p95 changed from
1967.995 to 982.813ms, and idle-confirmed queue p95 from 502.753 to 9.340ms.
These measure specific development workloads. The frozen code release has 1958
primary backend passes, 1924 clean passes with 34 expected skips, 844 frontend
unit tests and 542 browser passes with four inherited skips. Both exact-release
workflows succeeded.”

**Do not say:** End-to-end internet latency, a production SLA, universal speedup,
zero-warning certification, or that skipped cases passed.

### 6:30–7:00 — Tradeoffs and close

**Click/show:** README limitations and case-study lessons.

**Say:** “The worker topology remains single-process. Real Groq quota and
production SLA are unverified; the bundle warning, manual zoom gate, staged
bearer integrations and optional Ragas remain visible. The main lesson was
making evidence, authority and execution lifetimes explicit.”

**Do not say:** Automatic distributed scalability, hidden automatic planning,
full accessibility certification, or a live deployment is always available.

## After recording

Stop each task-owned server using Ctrl+C in its own terminal. Keep your original
workspace/data intact. Do not publish tokens, private filings, diagnostic traces
or generated test screenshots. Review the video for legible source IDs and the
fixture disclosure. For a five-minute version, shorten internals and measurements;
retain Quick/source inspection, Deep lifecycle, the prepared result and limitations.
