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
- [ ] Resolve the year contract for the year-unspecified Apple-vs-Amazon
      revenue comparison before the current-model N=30 Phase 2 run. The
      current planner snapshot retrieves both 2024 and 2025 correctly, while
      `gpt-oss-120b` reasonably answers with the latest 2025 column and the
      approved probe acceptance still pins FY2024 values.
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
