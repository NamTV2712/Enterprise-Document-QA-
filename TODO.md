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
9. [x] Rebuild the Phase 1 retrieval artifact against the hard-group index
       before Phase 2. Done offline with determinism verification: artifact
       acc61c63... bound to corpus 91828b..., 12/12 decomposed evidence_ok.
10. [x] Financial-table remediation order from the read-only audit
        (data/diagnostics/financial_table_audit.json): first extend table
        discovery to reuse the recovery TOC-anchor path for NVDA -> ORCL ->
        PEP; then AVGO/HD window extension plus year-header tolerance; then
        GS exhibit following. CVX/IBM/JPM/XOM stay deferred to the separate
        incorporation-by-reference extraction milestone.
11. [x] Rebuild Phase 1 against the PEP-recovery index and complete its
        historical official Phase 2 N=30 evaluation. Artifact 40980956... is
        superseded; do not treat that run as the current-corpus benchmark.
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
       - Same-document resolver and corpus rebuild complete: CVX (33 tables), XOM (4), and JPM
         (6) pass deterministic clean-boundary, fiscal-year, primary-statement,
         de-duplication, and contamination gates. The resolver is enabled only
         for those three tickers; generation `nomic-e9b6763-fy2026-hard-group-table-recovery-20260828-attempt-01`
         is promoted and indexed at 10,021 points. This historical note is
         superseded by the IBM companion-recovery generation below.
13. [x] Add six priority-3 hard-group evaluation cases for CVX/JPM/XOM
        (three fact lookups and three year-over-year multi-hop checks). These
        cases do not alter the official priority-2 benchmark; run a separate
        deterministic retrieval replay before any provider evaluation.
14. [x] Complete the read-only IBM companion-document audit. The filing
       references pages 42-116 of the 2025 Annual Report to Stockholders and
       links `ibm-20251231_d2.htm`. The temporary companion passed the
       deterministic read-only audit with six unique statement tables and
       complete income/balance-sheet/cash-flow evidence. Production now uses
       the page-bounded companion route and serves 32 supplemental chunks.
       Report: `data/diagnostics/ibm_companion_document_audit.json`.
15. [x] Harden the IBM audit to schema v2 with explicit page-interval
       resolution, trial chunk IDs, companion hashing, tri-state gates, and
       an internal byte-determinism check. A complete synthetic companion
       passes all gates; the real corpus remains unchanged and NO-GO.
16. [x] Implement the generic production companion resolver and rebuild the
       corpus, immutable embedding generation, and trusted local index. The
       active generation is `nomic-e9b6763-fy2026-ibm-companion-20260829` at
       10,053 points; coverage is 50/50 tickers with financial-table chunks.
17. [x] Rebind the deterministic Phase 1 artifact to the IBM companion corpus
       The current artifact is `sha256:8283b628…`, with 30/30 priority <= 2
       cases, 61 non-empty queries, byte-identical determinism, and 12/12
       decomposed-plan evidence checks. Add IBM priority-3 retrieval contracts
       and verify the 22-case priority-3 replay at keyword recall `1.0000`.
       and complete the current-corpus official Phase 2 run. The run achieved
       30/30 generation and 30/30 judgment records with no skips or parse
       failures; see the pinned metrics in `README.md` and `PROJECT_STATE.md`.
18. [x] Improve Phase 2 judge integrity based on the comparative/enumeration
       failure audit. The production judge now parses only `[Source N]`
       boundaries, preserves internal blank lines and complete evidence text,
       and fingerprints the context builder so stale judge checkpoints cannot
       be reused. The corrected official rerun reaches Faithfulness `0.9793`,
       Answer Relevancy `0.9733`, Context Precision `0.6197`, and Overall
       `0.8574` on 30/30 cases.
19. [x] Run the deterministic answer-integrity audit on the corrected
       benchmark. It covers all 30 answers and reports 2 uncited non-fallback
       answers, 1 legacy line-citation answer, and 4 numeric-review cases.
       The report is generated offline by
       `scripts.diagnostics.answer_integrity_audit` and is not folded into
       official LLM-judge metrics.
20. [x] Tighten generation and decomposed-synthesis contracts: canonical
       `[Source N]` citations only, no irrelevant-source fallback claims,
       exact numeric/period handling, and no general-knowledge category
       invention during enumeration planning.
21. [x] Re-run a quota-gated sentinel set for the six audit-flagged answers.
       All 6/6 generation and judge calls completed; legacy citations fell to
       zero, uncited non-fallback answers fell to zero, and numeric flags did
       not increase. The run is non-official and stored in the ignored
       `data/eval_artifacts/answer_sentinel_summary.json`.
22. [x] Pre-register and pass the comparative packing v3 offline gate. The
       strategy preserves 30/30 evidence coverage and source boundaries,
       keeps all 24 non-comparative contexts byte-identical, preserves branch
       coverage for all 6 comparative cases, and reduces comparative rendered
       tokens from 20,939 to 10,211 (51.23%). No provider call was made.
23. [x] Add the first shared deterministic query shaper and validate the AWS
       counterfactual: the original `Amazon AWS growth` query misses both
       required AWS values, while the shaped query retrieves them in rank 1.
       The decomposed audit now correctly classifies the old frozen case as
       `retrieval_miss` instead of `evidence_ok`.
24. [x] Bind the shared shaper to Phase 1 execution and artifact identity.
       Phase 1 schema v2 now stores original and shaped retrieval queries plus
       a deterministic rules fingerprint; Phase 2-derived runners reject an
       artifact without matching provenance. The 61-subquery local A/B shaped
       two queries with zero ticker leaks, zero required-term regressions, and
       byte-identical repeated output. Rebuild Phase 1 before any new Phase 2
       provider run; the existing artifact remains historical only.
25. [x] Extend the shaper into a field-aware lexical ladder (`exact_phrase`,
       `full_terms`, `partial_terms`, then guarded `fuzzy`) and merge its
       candidates into RRF only after offline ticker/recall gates pass. The
       61-subquery A/B passed twice with identical bytes, zero ticker leaks,
       zero required-term regressions, 59 unhinted queries byte-stable, and
       both hinted AWS queries retaining fact evidence at rank 1. Fuzzy is
       ticker-scoped, last-resort, length-guarded, and threshold-guarded.
26. [x] Rebuild the schema-v2 Phase 1 artifact offline with shaper and lexical-
       ladder fingerprints, verify byte determinism and decomposed evidence
       coverage, then pin the new artifact before any provider-backed Phase 2.
       Artifact `sha256:3f02a791…` covers 30/30 cases and 61 non-empty
       queries, has zero ticker leakage, and passes `12/12 evidence_ok`; all
       Phase 2-derived runners now pin it. No provider call was made.
27. [x] Run comparative packing v3 offline against the schema-v2 artifact.
       Two reports serialized byte-identically; the gate passed 30/30 evidence
       coverage, 30/30 source boundaries, 24/24 non-comparative byte stability,
       6/6 comparative branch coverage, and 51.23% comparative token reduction.
       The strategy is exposed as experimental and is not the Phase 2 default.
28. [x] Run the pre-registered provider A/B on the six comparative cases. Both
       arms completed 6/6 generation and 6/6 judging. V3 improved context
       precision by `+0.2233`, reduced tokens `51.23%`, and kept deterministic
       metrics perfect, but is NO-GO: answer relevancy moved `-0.0766` and the
       AWS answer omitted `107,556` and `128,725`. The audit also fixed the
       runner so generation, deterministic metrics, and judging now consume
       the same renderer-bound context; old packing runs are historical only.
29. [x] Build comparative packing v4 as an offline counterfactual using branch
       top 1 plus a query-intent/fact donor instead of blind top 2. Two reports
       are byte-identical and pass 30/30 evidence and source boundaries, 24/24
       non-comparative byte stability, 6/6 branch contracts, and every pinned
       A/B finding. AMZN cyber rank 4 and Microsoft Cloud rank 3 are retained,
       both AWS values remain present, Apple international rank 2 is dropped,
       and comparative tokens fall `20,939 -> 6,737` (`67.83% >= 45%`). V4
       remains offline-only; no provider call was made.
30. [x] After v4 passes offline, tighten exact numeric-pair prompt adherence and
       run only the AWS sentinel. The sentinel completed `1/1` generation and
       `1/1` judging with both `107,556` and `128,725` plus their periods in a
       grounded, cited non-fallback answer; all pre-registered gates passed.
       The result is non-official and stored under ignored `data/`.
31. [x] Implement comparative packing v5 as the oracle-free follow-up. Share
       the selector between production `/query/decomposed` and the Phase 2
       offline adapter, add the Microsoft Cloud filing-native trend hint, and
       lock the period/value prompt contract across direct, synthesis, and
       Phase 2 generation. Rebuild the active artifact to
       `sha256:986991219560…`; the local shaper A/B passes 61/61 subqueries,
       and the v5 gate passes 30/30 evidence/boundary checks, 24/24
       non-comparative byte stability, 6/6 branch contracts, and 67.23%
       comparative token reduction. No provider call was made.
32. [ ] Run a fresh pre-registered six-case provider A/B for comparative v5
       versus full evidence. Admit v5 only if both arms complete, context
       precision improves, faithfulness/relevancy stay within bounds,
       deterministic metrics do not regress, and all AWS numeric-pair
       integrity gates pass.

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
