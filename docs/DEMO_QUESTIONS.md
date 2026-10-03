# FilingScope — Demo Questions

Use these four examples with the existing TEST-005 environment in the
[Demo Script](DEMO_SCRIPT.md). Real FastAPI routes, HTTP/SSE, DATA-004 SQLite,
workers and native evaluation are exercised with deterministic corpus/model
fixtures. This does not demonstrate live financial-model accuracy.

## 1. Primary Quick question

**Ask:** “What evidence is available for Apple?”

- **Expected visible behavior:** Quick streams a fixture answer with a citation.
  Open it and inspect the indexed excerpt, document `AAPL:HARNESS` and chunk
  `AAPL_harness_0000`. Return to the answer, then click **Research deeper** to
  show a filled draft without an automatic Agent submission.
- **Fixture/live distinction:** The excerpt and generated text are synthetic;
  streaming and citation/source navigation use the real application contracts.
  The fixture's SEC-shaped URL is not proof of an admitted original filing.
- **Fallback if unavailable:** Show the current unavailable state honestly.
  Restore the local harness before the final rehearsal; do not substitute a
  screenshot or static answer and call it a live result.

## 2. Optional Quick follow-up

**Ask:** “Which filing supports that answer?”

- **Expected visible behavior:** Submit from the existing Quick conversation and
  open the returned source citation. The deterministic harness returns its
  synthetic Apple source; its rewrite/text is not a financial interpretation.
- **Fixture/live distinction:** Session and follow-up transport are real, while
  retrieval/generation dependencies remain fixtures. This question is an optional
  navigation demonstration, not evidence of semantic follow-up quality.
- **Fallback if unavailable:** Omit it and use the primary answer's citation.
  Keep the core Quick → source → Research deeper sequence within the time budget.

## 3. Deep Research goal — cancellation run

**Submit explicitly:** “Inspect current Apple risk evidence.”

- **Expected visible behavior:** With harness `waiting` mode selected, create one
  generic Deep run/card. Show Running and safe Research details, request
  cancellation, observe Cancelling, then release the held test boundary as
  documented in the Demo Script and observe Cancelled. Keep this run ID visible.
- **Fixture/live distinction:** Admission, durable state, workers, revision-safe
  cancellation and events are real. The scripted decision pauses deliberately;
  cancellation does not kill an external effect. Research details are safe
  activity, not hidden chain-of-thought.
- **Fallback if unavailable:** Stop and inspect the harness mode/connection
  off-camera. Do not label a Failed/Interrupted outcome as Cancelled or reuse a
  successful run to represent cancellation.

## 4. Prepared successful Deep run — separate structured record

**Prepare off-camera:** “Find recorded Apple risk evidence.” Use the explicit
`agent_research_v1` objective `apple_risk`, question “Find Apple risk evidence”
and ticker scope `AAPL` through the API preparation in the Demo Script.

- **Expected visible behavior:** In harness `research` mode, the script executes
  `search_documents` then `read_document`, ending **Completed** (`succeeded`) with “The recorded
  Apple filing contains risk evidence.” Open this distinct run from Run history
  in the full `/agent` inspector; show canonical `AAPL:HARNESS` /
  `AAPL_harness_0000` evidence and all **21 native structural metric entries**.
- **Fixture/live distinction:** This is a deterministic terminal record from real
  routes, tools and SQLite. Evaluation reads recorded structure; it does not
  rerun a model or certify financial accuracy. The generic composer did not
  automatically create its explicit research objective. Original filing access
  can be unavailable while the indexed excerpt remains inspectable.
- **Fallback if unavailable:** Prepare a fresh structured fixture run off-camera
  and repeat rehearsal. If unavailable persists, show that truthfully and record
  the missing checkpoint; never call the cancelled run a successful result.
