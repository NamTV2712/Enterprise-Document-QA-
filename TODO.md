# TODO

This file tracks only the current actionable queue. Historical results,
rejected experiments, and detailed evidence remain in `PROJECT_STATE.md`.

## Always-On Deployment

- [ ] Choose the backend host: prefer Oracle A1 when free capacity is available;
      use Fly.io only with explicit approval for ongoing charges.
- [x] Verify the Docker `builder` stage for `linux/arm64`. CPU PyTorch and all
      requirements installed successfully through BuildKit emulation.
- [ ] Build the full ARM64 runtime image, verify both model downloads/imports,
      and pass a memory smoke test before committing to Oracle A1.
- [ ] Deploy the backend with persistent storage, secrets, HTTPS, health checks,
      and trusted-proxy configuration.
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
