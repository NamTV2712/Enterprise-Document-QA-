# FilingScope — Recording Cheat Sheet

Companion to the [Demo Script](DEMO_SCRIPT.md) and the four
[demo examples](DEMO_QUESTIONS.md). Target **6:45**; keep the architecture segment
to **40 seconds**. Use the observed rehearsal outcomes in the
[Demo Receipt](DEMO_001_RECEIPT.md), rather than assuming every prepared step worked.

## Before record

- Start the existing TEST-005 harness and production frontend preview using the
  Demo Script. Keep the backend on loopback and use an isolated runtime directory.
- Prepare the successful structured research run off-camera, save its run ID,
  then select `waiting` mode for the separate cancellation demonstration.
- After New Research, reload the landing page off-camera to avoid the observed
  stale preparation session; preserve the Library. Connect before recording
  with the **public synthetic TEST-005 fixture token**.
  Keep real Groq keys and workspace credentials out of browser, terminals, URLs,
  logs and shell history. Do not show the preparation Authorization header.
- Use a clean browser with only demo tabs, no notifications, no personal files
  and no DevTools. Choose one theme and readable zoom. Prefer 1920×1080, 16:9,
  30 FPS or higher; 1280×720 is acceptable if the text remains legible.
- Open README, the selected existing system architecture image, Research and the
  relevant metric receipts. Keep the prepared run available through Run history.
- Complete one uninterrupted timed rehearsal. Record its actual duration and
  visible outcomes. Rehearsal readiness and a recorded final video are separate.

## Timeline

### 0:00–0:30 — Problem

Show **FilingScope** and its subtitle. Explain that long SEC filings spread
evidence across narrative, tables and reporting periods. Quick gives cited
answers; Deep adds separately authorized, inspectable execution.

Say: “This demo uses deterministic local fixtures for repeatability and does not
claim live financial-model accuracy.” FastAPI, HTTP/SSE, SQLite, workers and the
browser are real; corpus, generation and Agent decisions are fixture dependencies.

### 0:30–1:10 — Architecture

Show the same [existing system architecture image](architecture/sec-research-workspace.visual-check.2048x1320.light.png)
used in README. Point out React → FastAPI/SSE → hybrid retrieval → reranking →
grounded generation → citations. Explain that Deep crosses Agent API → DATA-004
→ fixed workers → bounded Agent → closed tools, sharing retrieval and evidence.
The image documents the RAG infrastructure; the
[full architecture](../ARCHITECTURE.md) specifies durable Agent authority.
Keep this explanation within 40 seconds.

### 1:10–2:20 — Quick

Keep Quick selected and submit “What evidence is available for Apple?” Show the
streamed fixture answer and open its citation. Point to document `AAPL:HARNESS`
and chunk `AAPL_harness_0000`, then return to the answer. Click **Research deeper**
and pause on the populated Deep draft. No run has been submitted by that click.
Skip the optional follow-up if it would crowd out source inspection.

### 2:20–4:20 — Deep

Replace the populated draft with “Inspect current Apple risk evidence.” and
submit explicitly. Show one durable card,
Running and Research details. Activity reports safe execution facts, not hidden
chain-of-thought. Request cancellation: show Cancelling, release the harness's
held boundary off-camera as documented, then show Cancelled.

Open the full run and select the **different** prepared successful run from Run
history. Show its distinct ID, **Completed** (`succeeded`), final result, canonical evidence and
21 native structural evaluation entries. The successful run used an explicit
API research objective; the generic composer does not synthesize that objective.
Open its document workspace. If the original source is unavailable, explain that
the fixture supplies indexed excerpts; use Quick's citation inspector for the
excerpt. Never present the cancelled run as the successful one.

### 4:20–5:15 — Engineering

Explain browser reference ownership versus DATA-004 state/result/event authority.
SQLite claims are short and revisioned; provider work stays outside transactions.
Two fixed workers run in one process. Cancellation finishes at a supported safe
boundary. SSE presents safe events; native evaluation reads terminal records
without rerunning a model. Show the frozen release receipt, not a fresh-test claim.

### 5:15–6:15 — Metrics

Show the README measurement table and its linked receipts. Read50 client p95
changed from 1967.995 to 982.813 ms; idle-confirmed queue p95 changed from
502.753 to 9.340 ms. Warm navigation p95 was 63.30 ms in Chromium and 42.00 ms
in Firefox. Say **controlled development measurements, not a production SLA**.
Mention the frozen release's validation counts below. Do not read every metric.

### 6:15–6:45 — Limitations / closing

Show visible limitations: single-process workers, unverified production SLA and
real Groq quota, bundle warning, manual zoom gate, staged bearer integrations and
optional Ragas. The public frontend can be available while its backend is offline.
Close on evidence traceability and explicit execution ownership.

## Facts to remember

- Configured corpus: **50 companies**; canonical local index: **10,053 chunks**.
  These are historical corpus facts, not the small fixture corpus or user counts.
- Frozen code release: **1958 primary backend passes**, **844 frontend tests**,
  **542 browser passes / 4 inherited skips**. Skips are not passes.
- Prepared Agent success: **two tool calls**, **21 native metric entries**;
  structural checks do not certify factual accuracy.

## Claims to avoid

- Guaranteed accuracy, zero hallucination, full security or accessibility certification.
- Distributed execution, exactly-once external effects or automatic hidden planning.
- Live model inference in this fixture, production SLA or universal speedup.
- Final video recorded, published or uploaded without the corresponding artifact.

## Closing sentence

“FilingScope makes evidence inspectable and research execution durable, bounded
and explicit about its limits.”
