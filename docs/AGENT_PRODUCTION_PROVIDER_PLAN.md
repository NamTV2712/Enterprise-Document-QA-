# PROVIDER-001: production structured decision provider

Status: checkpoints A–D implemented; final verification in progress. This optional extension
starts at `5a002d0c7f41c595f5a2ebd866dedd09a0a8f907` on
`codex/bilingual-research-workspace`. The required roadmap and AGENT-001–006,
UI-014 and TEST-005 remain complete.

## Capability audit and contract

- Installed and already pinned Groq SDK 1.5.0 exposes AsyncGroq,
  `response_format.json_schema.strict` and `include_reasoning=False`.
  Groq's [structured output documentation](https://console.groq.com/docs/structured-outputs)
  supports native strict schema for GPT OSS 120b and 20b. Initial support is
  explicitly limited to those two models; there is no inferred capability,
  JSON mode fallback, prose extraction, repair or malformed-output retry.
- Reuse the configured generator default or its loaded runtime model identity,
  and `configured_groq_keys` with the existing pool/key5 policy. No new
  credentials, model role, dependencies or database migration. No live request
  is necessary to read capability status.
- The existing protected `/system/configuration-status` is the capability
  authority. Add a safe provider capability there; no new endpoint. The shared
  in-memory frontend session projects only availability. Workspace execution
  and the explicit per-run decision grant remain independent checks. RAG
  permission remains separate and disabled in the create form.
- Freeze provider, exact model, adapter version, strict transport mechanism and
  credential policy into the existing plan JSON. A derived decision-model ID
  binds this identity. Old plans omit the optional identity and retain their
  fingerprints. Execution rejects changed bindings, never upgrades old runs.
- One existing orchestrator calls one adapter for one decision at a time. The
  SDK proposes decisions only, never executes tools. Transport uses a closed
  root object containing one tool/final union. Tool arguments travel as unique
  name/value pairs, then map losslessly to the existing scalar dictionary.
  This permits strict closed objects without changing ToolDecision semantics.
  Every field is required; absent optional semantic values use null/empty arrays.
  Strict local transport and semantic validation remain mandatory.
- Send typed allowlisted policy, schemas, remaining counters, goal, research
  view and bounded observations. Goal and observations are untrusted data;
  control is a separate system message. Reject configured secret values and
  sensitive/path text before transport or persistence; never serialize a
  settings/client object. No reasoning request or persisted reasoning.
- Reuse the SDK's 60 second timeout, with an additional 60 second total async
  deadline and five second connect timeout. Set `max_retries=0`, make one
  attempt per decision and do not use Generator's retry/key-rotation wrapper.
  Cancellation is cooperative at existing boundaries; an in-flight call can
  finish. No transport retry, restart replay or new worker exists.
- Bounded failure taxonomy: unavailable, authentication, rate limit, timeout,
  invalid JSON/response, schema violation and generic provider failure. No raw
  provider body, exception, request, headers or credentials enter results/events.
  SDK transport diagnostic logs are suppressed only within the Agent call
  context to prevent debug payload/exception disclosure.

## Checkpoints and verification plan

- A: capability audit, scope, contracts and test plan recorded before long runs.
- B: strict adapter/resolver, schema/parser and provider-free transport tests.
- C: security, failure categories, frozen identity, one owner, cancel/restart.
- D: existing API capability/run creation and minimal EN/VI UI integration.
- E: focused regressions, full backend/frontend, TypeScript/build, rendered
  production browser checks and optional bounded live smoke (key5 only).
- F: committed clean checkout without env/data/generated outputs, intended-file
  hygiene, exact HEAD verification and normal upstream push; COMPLETE then STOP.

Mandatory cases include all four tools/final/objective decisions; malformed,
duplicate-key, unknown/extra, oversized, multiple and hostile output; secret
absence; all four decision/RAG permission combinations; fake/cross-run refs;
research search/read/final; concurrent ownership with barriers; cancellation
before/during transport; restart without replay; provider-free evaluation with
the unchanged 21 native metrics; private API refusal and unavailable capability.

## UI semantics and risks

Entry `/agent`, intent create a bounded research run, primary action existing
create form, result existing durable detail. Shared session owns capability and
credential lifetime; hook owns request epochs, server owns state and SQLite.
Existing modal owns focus/scroll, existing detail/list own their scroll regions.
Connected/unconfigured, configured/unsupported, read-only, permitted execution,
loading/error/disconnected and historical unavailable states remain distinct.
No layout redesign. Five review risks: stale capability, accidental implicit
provider permission, conflating RAG permission, changing old run provenance,
and secret leakage through SDK debug logging. Verify EN/VI, light/dark, phone
and desktop, keyboard/modal focus and actual rendered provider notices.

## Baseline and known limitations

Backend 1583 passed / 188 warnings; clean 1549 passed / 34 artifact skips /
148 warnings. Frontend 94 files / 815 tests; TS/build pass; 90 product routes;
SQLite v7; bundle 508.30 kB warning. Preserve the 12 unrelated untracked paths.
Collections/model-test browser bearer integration, native zoom manual checks
and optional Ragas remain future limitations. Strict format does not establish
semantic correctness or resistance of the model to injected text; code gates
remain authoritative. Remote reachability/authentication is unknown until an
explicit permitted attempt. Single serving process remains required.

## Checkpoint E findings

The initial full primary suite passed 1677 tests / 188 unchanged warnings;
frontend 94 files / 818 tests, TypeScript and build passed. The provider browser
campaign passed 20/20 in Chromium/Firefox with focused Axe and overflow gates.
Review then strengthened rejection of configured runtime secrets before
observation state/result admission, beyond transport-only refusal. Two API
regressions explicitly cover secret observations in durable results, events
and evaluation. This final change requires renewed final backend verification.
The phone screenshot also exposed inherited text-input sizing on the consent
checkbox; a compact checkbox inside a 44px label fixes it. The first browser
attempt was stopped after the VI locator used an incorrect translated label;
the corrected locator campaign passed, with a subsequent final styling run.

Optional live smoke: **FAILED (`decision_provider_timeout`)**, one explicitly
authorized key5-only decision attempt, a 60 second total deadline, zero tools,
zero retry. No provider body/answer/credential was printed or retained. This
does not gate deterministic completion; live reachability remains unverified.
The probe allowed no tools and requested only a short final transport check,
with observation requirement disabled solely for that diagnostic.

The source-clean implementation checkout passed 1645 tests, 34 expected
artifact-dependent skips and 148 historical warnings; fresh frozen Bun
installation, TS/build and 94 files / 818 tests passed without lock drift.
API imports resolved to that checkout, unavailable capability was provider-free,
and the inventory remained 90 routes. Release review replaced the newly used
Python 3.11-only `asyncio.timeout` with `asyncio.wait_for` to preserve the
documented Python 3.10+ contract. The existing deadline/resource-closure test
verifies the same bounded behavior; final verification will cover this fix.
