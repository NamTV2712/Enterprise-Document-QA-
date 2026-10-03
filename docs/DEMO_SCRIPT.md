# FilingScope — Demo Guide

Public display name: **FilingScope** (original repository: Enterprise Document QA).

An executable provider-free recording path. See the
[README](../README.md), [case study](PORTFOLIO_CASE_STUDY.md) and
[release evidence](IMPROVEMENT_FINAL_RECEIPT.md).

The [Live Demo](https://frontend-one-gamma-f9jf11u8ec.vercel.app) is the running
frontend preview, separate from this recording guide. It reported **API offline**
on 2026-10-03; use the prepared local environment below for the recording.

## Published silent tour

[Watch Demo](https://github.com/NamTV2712/Enterprise-Document-QA-/releases/tag/demo-v1) · [Download MP4](https://github.com/NamTV2712/Enterprise-Document-QA-/releases/download/demo-v1/filingscope-portfolio-demo.mp4)

Published 2026-10-03: **2:27.67**, 1600×900, H.264, encoded 30 FPS, no audio.
The owner requested a quick functional recording and waived narration and the
original 5–7 minute length. Native browser frames are unaltered; cuts remove gaps
between actions. Screenshot sampling is lower than the encoded frame rate.

The tour shows Quick/citation/source, an explicit Deep submission and cancellation,
a separate prepared successful Agent run, tools/evidence/final references, native
Agent evaluation, Documents, Search and Retrieval Lab. Brief document cards show
the historical RAG benchmark, measured performance, frozen validation and
architecture; the closing card preserves their limitations. These cards render
existing documentation and are not live measurement dashboards.

The extended narrated timeline below is **optional**; it is not the published
video's timeline. See the [shipping receipt](PORTFOLIO_SHIP_001_RECEIPT.md).

## Choose the demonstration environment

The default below uses the existing TEST-005 local harness. It runs real FastAPI
routes, access controls, DATA-004 SQLite, workers, events and native evaluation;
corpus/model/provider dependencies are synthetic. Quick answer text and the
successful Agent decisions are fixtures, not live inference or financial advice.
Keep that distinction visible in the recording title or opening disclosure.

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

Use the dependency-install portion of [Setup and Operations](SETUP.md#1-install-the-backend)
and [frontend setup](../frontend/README.md#local-development). Skip SEC download,
chunking, embedding and indexing for this fixture demo. Use Bun 1.3.14 and a
Python environment with the declared requirements. No real `.env`, private
corpus, Groq key or model download is needed by the harness.

Terminal A, from the repository root, PowerShell. Launch from a fresh runtime
directory so the repository's `.env` is not loaded:

```powershell
$env:TEST005_WORKSPACE_MODE = 'local'
$env:TEST005_API_PORT = '8788'
$env:TEST005_RUNTIME_DIR = Join-Path ([System.IO.Path]::GetTempPath()) ('edqa-portfolio-' + [guid]::NewGuid())
$demoRepo = (Get-Location).Path
New-Item -ItemType Directory -Path $env:TEST005_RUNTIME_DIR | Out-Null
Set-Location -LiteralPath $env:TEST005_RUNTIME_DIR
& "$demoRepo\.venv\Scripts\python.exe" "$demoRepo\tests\integration\agent_product_server.py"
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
history; preserve your normal saved Library. After **New Research**, reload the
Research landing page off-camera before connecting: the rehearsal encountered
a stale in-tab session during preparation, resolved by this fresh load.
Connect off-camera before the timed
rehearsal using the **public synthetic fixture token** above, then return to Quick.
Never use a real token on camera. The input clears after connection and the bearer
remains in memory.

### 3. Rehearse once

Confirm Quick streaming and source opening, one Deep card, running → cancelling
→ cancelled, and the prepared inspector's result/evidence/metrics. The waiting
decision deliberately holds until the release command below. Clear pending demo
work before another rehearsal by cancelling it and releasing that boundary.
Keep the prepared run ID, architecture section and CI links ready in browser tabs.
The harness may still display the production decision-provider-unavailable banner:
its test controls inject a scripted model without configuring a real provider.
Explain that fixture distinction; do not present the banner as live model availability.

## Optional extended narrated recording flow

### 0:00–0:30 — Problem and project

**Click/show:** README title and product overview, then Research.

**Say:** “Long financial filings are hard to search and compare while retaining
source traceability. I built FilingScope, an SEC research workspace with cited
Quick RAG answers and separately admitted durable Deep Research. This recording
uses deterministic local fixtures; it demonstrates product behavior, not live
model quality.”

The app retains its historical **RAG System** header; introduce FilingScope as
the public project name without editing or compositing the application.

**Do not say:** Used by enterprises, production-ready as an absolute, or a
guaranteed accurate financial assistant.

### 0:30–1:10 — Architecture overview

**Click/show:** [README architecture](../README.md#architecture) and its
[existing system image](architecture/sec-research-workspace.visual-check.2048x1320.light.png).
Point out the RAG path. Explain Deep's shared infrastructure orally: the preserved
image does not draw Agent workers or DATA-004. Keep narration within 40 seconds.

**Say:** “BM25 and Qdrant rankings are fused, then cross-encoder reranking selects
evidence for grounded generation. Deep uses bounded typed tools and a process-local
worker pool. SQLite owns Agent runs; the browser owns only their references.”

**Do not say:** Each tool calls an independent microservice, the topology is
distributed, or every Deep run uses every tool.

### 1:10–2:20 — Quick answer and source

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

### 2:20–4:15 — Deep lifecycle, result and evidence

**Click:** Use the local workspace connected off-camera with the synthetic token. With
**Deep Research** selected, replace the populated draft with
“Inspect current Apple risk evidence.” and submit explicitly.
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
The inspector labels the `succeeded` state **Completed** in English. Show final
result, research evidence and the native metrics. Click **Open document**;
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

### 4:15–5:10 — RAG quality and Agent evaluation

**Click/show:** The separate successful run's native evaluation, then
[README RAG quality](../README.md#rag-quality) and the
[public benchmark](RAG_QUALITY_BENCHMARK.md).

**Say:** “These 21 Agent entries check recorded execution structure and operation;
they are not RAG accuracy. The separate RAG benchmark keeps all 30 historical
cases: faithfulness 1.0000, answer relevancy 0.9917 and context precision 0.7613.
Citation validity is 1.0000 on 27 cases, keyword coverage 1.0000 on 24, and
fallback correctness 1.0000 on all 30. N/A cases remain disclosed. Publication
reuses frozen answers, exact contexts and bound judge scores with zero live calls.
Historical context packing uses required-keyword donors, so it is label-assisted,
not current-runtime or general SEC QA accuracy. There is no overall score.”

**Do not say:** 100% accurate, zero hallucination, Recall@K, factual citation
support, confidence probabilities or that this small demo fixture produced the benchmark.

### 5:10–5:55 — Performance and engineering

**Click/show:** Retrieval design, [worker receipt](WORKER_002_FINAL_RECEIPT.md),
DATA-004 ownership in [architecture](../ARCHITECTURE.md#state-and-persistence),
and the frozen release's [Backend CI](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/runs/37085104945)
and [Frontend CI](https://github.com/NamTV2712/Enterprise-Document-QA-/actions/runs/37085104875).

**Say:** “Claims are atomic and short; provider work is outside transactions.
Two fixed workers wake on a payload-free durable-admission hint, with polling
fallback. Agent API events contain safe execution facts. I verified contracts,
storage, cancellation and HTTP/SSE with provider-free tests. In controlled local
campaigns, Read50 client p95 changed from 1967.995 to 982.813ms; idle-confirmed
queue p95 changed from 502.753 to 9.340ms. These are different workload stages,
not end-to-end production latency. More workers did not help every capacity case.”

**Do not say:** Exactly-once external effects, a global provider concurrency cap,
or that this fixture performs real vector/model inference.

### 5:55–6:30 — Validation and architecture depth

**Click/show:** README measured improvements and Validation, then the receipts.

**Say:** “The frozen code release has 1958
primary backend passes, 1924 clean passes with 34 expected skips, 844 frontend
unit tests and 542 browser passes with four inherited skips. Both exact-release
workflows succeeded.”

**Do not say:** End-to-end internet latency, a production SLA, universal speedup,
zero-warning certification, or that skipped cases passed.

### 6:30–6:50 — Tradeoffs and close

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

## Recording package

- [Recording Cheat Sheet](DEMO_RECORDING_CHEATSHEET.md): the silent tour and optional 6:50 narration timeline.
- [Demo Questions](DEMO_QUESTIONS.md): four fixture-aware examples and fallbacks.
- [DEMO-001 receipt](DEMO_001_RECEIPT.md): actual rehearsal outcomes and recording status.
