# TODO

This file tracks only the current actionable queue. Historical results,
rejected experiments, and detailed evidence remain in `PROJECT_STATE.md`.

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
- [ ] Share one mode-aware chunk loader across API, evaluation, and diagnostics.

## Quality Gates

- [x] Run path-filtered backend CI with CPU-only dependencies, offline model
      guards, the full test suite, and compile checks.
- [x] Run path-filtered frontend CI with pinned Bun, frozen dependencies,
      TypeScript checking, Vitest, and the production build.

## Backlog

- [ ] Add entity/ticker auto-detection only if diagnostics show that unfiltered
      company scoping is a material failure mode. The Tesla diagnostic confirms
      this is material, but it is not sufficient by itself.
- [ ] Add query translation or multilingual retrieval only if diagnostics show
      a cross-language retrieval gap. Vietnamese reranker scores were all
      negative (`-6.1564` best with `ticker=TSLA`) versus positive English
      scores (`3.2882` best), confirming the gap.
- [x] Extend structured total-revenue matching to prefixed/plural row labels.
      Tesla regression coverage and a real pipeline query confirm the correct
      table chunk ranks first and the answer includes `97,690`.
- [ ] Treat bilingual response generation as a separate product feature.
- [ ] Add extraction support for MS, MCD, INTC, COST, GE, and HON.
- [ ] Expand evaluation coverage across the clean extended corpus.
- [ ] Reduce near-duplicate context to improve Context Precision.

## Explicitly Rejected

- Scale to 100 companies without separate extraction work.
- Reintroduce the adaptive score-gap cutoff without new evidence.
- Retune `candidate_pool` or cross-encoder batch size without new evidence.
