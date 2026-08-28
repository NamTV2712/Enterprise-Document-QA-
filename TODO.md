# TODO

This file tracks only the current actionable queue. Historical results,
rejected experiments, and detailed evidence remain in `PROJECT_STATE.md`.

## Active Quality Backlog

1. [x] Finish annual-report extraction adapters for MCD and INTC, which do not
       expose same-document TOC anchors. Keep the new anchor fallback for MS,
       COST, GE, and HON covered by fixture tests; do not overwrite generated
       artifacts until each recovered section passes a dry-run audit.
2. [x] Review the dry-run anchor sections for MS, COST, GE, and HON for
       boundary quality, especially the final financial-statements tail.
3. [x] After both checks pass, explicitly rebuild affected generated artifacts
       in order: chunking, table chunks, immutable embedding generation, and
       trusted local index; then run deterministic retrieval checks.
4. [x] Add evaluation cases for newly searchable tickers without changing the
       official clean N=30 benchmark.
5. [ ] Extend Vietnamese retrieval translation only from labelled EN/VI tests;
       current support is intentionally limited to explicit financial metrics.
6. [ ] Keep `/metrics` disabled unless the deployment protects it. Monitor
       429, 5xx, request count, and latency through aggregate telemetry.
7. [x] Finalize the FY2026 corpus recovery and table fallback: NOW/NVDA/ORCL
       financial_statements and PFE mdna restored; NVDA/ORCL/AVGO/GS/PEP/HD
       table fallback appended (46 clean / 4 degraded / 46 table / 9,978
       chunks) on trusted generation nomic-e9b6763-fy2026-pep-table-recovery-
       20260828-attempt-01; deterministic spot-checks and coverage baseline
       pinned.
8. [x] Audit why NVDA, ORCL, and PEP recovered statements still yield zero
       financial_table chunks (statement tables live in layouts the current
       table extractor misses); same audit covers AVGO, GS, and HD.
       - Result: audit v2 complete; classification recorded in
         `data/diagnostics/financial_table_audit.json` (schema v2).
       - NVDA/ORCL/PEP = `layout_or_exhibit` (statements outside Item-8 window)
       - AVGO/HD = `layout_or_exhibit` + `row_filter_miss`
       - GS = `layout_or_exhibit` with stub FS
       - CVX/IBM/JPM/XOM = `financial_statements_missing`
9. [x] Rebuild the Phase 1 retrieval artifact against the table-fallback index
       before Phase 2. Done offline with determinism verification: artifact
       40980956... bound to corpus dbfd75..., 12/12 decomposed evidence_ok.
10. [x] Financial-table remediation order from the read-only audit
        (data/diagnostics/financial_table_audit.json): first extend table
        discovery to reuse the recovery TOC-anchor path for NVDA -> ORCL ->
        PEP; then AVGO/HD window extension plus year-header tolerance; then
        GS exhibit following. CVX/IBM/JPM/XOM stay deferred to the separate
        incorporation-by-reference extraction milestone.
11. [x] Rebuild Phase 1 and run the official Phase 2 N=30 evaluation against
        the PEP-recovery index. Artifact 40980956... is deterministic with
        12/12 evidence_ok; Phase 2 completed 30/30 generation and 30/30
        judging with no skipped or parse-invalid records.
12. [x] Conditional TOC-anchor fallback: NVDA, ORCL, AVGO, GS, HD, and PEP
       are active in `add_table_chunks`; PEP root-anchor recovery yields 29
       parseable financial tables. Remaining missing-table tickers are CVX,
       IBM, JPM, and XOM.
       - Counterfactual v2 is complete and deterministic: NVDA and ORCL pass
         via non-overlapping statement-link intervals; PEP correctly fails
         that route because its Item-8/Item-9 pair is a TOC boundary. Audit
         the quality of PEP's separate 29-table root-anchor fallback before
         altering production discovery again.
       - Quality audit complete: all 29 canonical PEP table chunks reproduce
         exactly; five are primary statements, ten are supporting financial
         tables, and fourteen are financial notes. Keep the current fallback
         unchanged; it has the intended statement coverage.
       - Hard-group route audit complete: CVX/XOM use same-document Financial
         Table of Contents targets, JPM uses same-document page anchors, and
         IBM requires a separate Annual Report to Stockholders. Fresh sections
         are rejected as contaminated MD&A suffixes; implement no resolver
         until a read-only interval counterfactual passes clean-boundary gates.

## Always-On Deployment

- [ ] Provision `VM.Standard.A1.Flex` in the Singapore home region, targeting
      `2 OCPU / 8 GB`. The Console exposes this Always Free-eligible option,
      but actual host capacity remains unverified until instance creation.
- [x] Verify the Docker `builder` stage for `linux/arm64`. CPU PyTorch and all
      requirements installed successfully through BuildKit emulation.
- [x] Build the full ARM64 runtime image, verify offline inference through both
      models, and run the API memory smoke test. Peak cgroup memory was
      `1.821 GiB` with no OOM events under QEMU.
- [ ] Deploy the backend with persistent storage, secrets, HTTPS, health checks,
      and trusted-proxy configuration.
- [ ] Run the native ARM64 startup, Tesla query, latency, and memory smoke tests.
      Use Fly.io only with explicit approval if Oracle capacity or native
      validation fails.
- [ ] Point the existing Vercel frontend `VITE_API_BASE_URL` at the always-on
      backend and update backend `ALLOWED_ORIGINS`.
- [ ] Verify readiness, ticker discovery, streaming, session history, and a
      comparative query on the final public URL.

## Diagnostics

- [x] Run the quota-free EN/VI x unfiltered/TSLA retrieval matrix.
- [x] Record top-five ticker, section, score, and chunk ID results.
- [x] Classify the Tesla failure: it combines unfiltered ticker contamination,
      cross-language score collapse, and an English structured-lookup gap.
- [x] Audit the pre-fix financial routing. `structured_lookup()` required a
      ticker and recognized `total revenue`, but its canonical labels did not
      match Tesla's `Revenues - Total revenues` row. The correct 2024 value
      (`97,690`) existed in `financial_table_0002` but was absent from every
      tested top result.

## Evaluation Integrity

- [x] Reject malformed or schema-invalid judge responses instead of recording
      silent zero scores; preserve retries for provider/network failures.
- [x] Confirm the official N=30 artifact contains no silent parse-error records.
- [x] Fingerprint checkpoints against all semantic test-case fields plus explicit
      generator/judge models and a schema version; reject incompatible legacy
      records instead of reusing by question text alone.
- [x] Share one mode-aware chunk loader across API, evaluation, and diagnostics.
      Local mode reads nested embedded JSONL artifacts without retaining dense
      vectors; cloud mode scrolls Qdrant payloads. Source-selection and local
      filesystem behavior are covered by dedicated regression tests.
- [x] Add deterministic corpus/retrieval/replay/diagnostic fingerprints and
      trusted local-index manifest generation. The manifest binds canonical
      payloads, exact vector build inputs, pinned embedding revision, dimension,
      distance metric, point count, and builder version; it is published only
      after successful verification.
- [x] Add immutable staged embedding generations. Completion manifests bind
      deterministic file hashes, corpus/vector fingerprints, pinned model and
      build metadata; index schema v2 accepts only an explicitly selected,
      fully revalidated generation and never falls back to canonical vectors.
- [x] With explicit approval, force re-embed all chunks using the pinned model
      revision into an immutable generation, validate it, rebuild local Qdrant,
      publish its schema-v2 trusted manifest, and pass deterministic retrieval
      plus API restart verification.
- [x] Persist the pinned embedding revision in local `.env`, document it in
      `.env.example`, forward it through Docker Compose, and verify host API
      startup plus deterministic retrieval using the persisted setting.
- [x] Resolve the year contract for the year-unspecified Apple-vs-Amazon
       revenue comparison before the current-model N=30 Phase 2 run. The
       question now pins FY2024, production states the fiscal year used
       for year-unspecified questions, and the official two-phase N=30
       run completed with gpt-oss-120b generation and judging.
- [ ] Keep Cloud remigration NO-GO until exact point-ID set, canonical payload
      fingerprint, and vector snapshot verification are implemented and pass.

## Quality Gates

- [x] Run path-filtered backend CI with CPU-only dependencies, offline model
      guards, the full test suite, and compile checks.
- [x] Run path-filtered frontend CI with pinned Bun, frozen dependencies,
      TypeScript checking, Vitest, and the production build.

## Backlog

- [x] Add entity/ticker auto-detection for unambiguous company names.
      Implemented via deterministic `query_normalizer` scoping; see
      `PROJECT_STATE.md` and `tests/test_api.py::test_query_auto_scopes_and_translates_supported_vietnamese_metric`.
      The Tesla diagnostic showed scoping is necessary but not sufficient
      by itself, so unfiltered ambiguity handling remains out of scope.
- [ ] Add query translation or multilingual retrieval only if diagnostics show
      a cross-language retrieval gap. Vietnamese reranker scores were all
      negative (`-6.1564` best with `ticker=TSLA`) versus positive English
      scores (`3.2882` best), confirming the gap.
- [x] Extend structured total-revenue matching to prefixed/plural row labels.
      Tesla regression coverage and a real pipeline query confirm the correct
      table chunk ranks first and the answer includes `97,690`.
- [ ] Treat bilingual response generation as a separate product feature.
- [x] Add extraction support for MS, MCD, INTC, COST, GE, and HON.
- [ ] Expand evaluation coverage across the clean extended corpus.
- [x] Run the audited near-duplicate context replay on the clean N=30 artifact.
      It found no exact duplicates or semantic-only pairs at `>=0.95`; adjacent
      overlap has no negative association with Context Precision, so production
      deduplication is not justified by the current evidence.

## Explicitly Rejected

- Scale to 100 companies without separate extraction work.
- Reintroduce the adaptive score-gap cutoff without new evidence.
- Retune `candidate_pool` or cross-encoder batch size without new evidence.
