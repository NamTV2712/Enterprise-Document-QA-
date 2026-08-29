# Project State

## Current Milestone

The current-corpus evaluation closure is complete. Phase 1 was rebuilt against the active IBM companion-recovery corpus with `--verify-determinism` after one-time Hugging Face metadata resolution via the explicit `--allow-network` escape hatch; the resulting artifact is byte-identical across both executions and has fingerprint `sha256:8283b628bb755b00bef86a26d7c608f9b385836c28dad588992b7d533ea51ee4`. It executes all `30/30` priority <= 2 cases with `61` non-empty queries and `12/12` decomposed-plan `evidence_ok` checks, bound to corpus `sha256:1d5b99ed…`, index manifest `sha256:5ac5362a…`, embedding `sha256:0c4ee351…`, reranker `sha256:16ff6fc9…`, retrieval config `sha256:6bf7801a…`, and test set `sha256:92dc7bc0…`. The two Phase 2 runners now pin this artifact and regression tests refuse the superseded hard-group artifact. The separate priority-3 replay covers `22` cases at keyword recall `1.0000`; IBM net-income retrieval required and now uses a caption-aware structured lookup preference for the consolidated income statement. The current-corpus Phase 2 run is official after a judge-context integrity fix: `30/30` generation OK, `30/30` judgment OK, no skips or parse failures; source markers now preserve complete SEC chunks across internal blank lines and the context-builder fingerprint prevents stale judge checkpoint reuse. Corrected scores are Faithfulness `0.9793`, Answer Relevancy `0.9733`, Context Precision `0.6197`, and Overall `0.8574`. Deterministic checks remain citation correctness `1.0000`, recall proxy `1.0000`, and fallback accuracy `1.0000`; the next improvement should target comparative context precision and out-of-corpus abstention precision.

The IBM companion production milestone is complete. A generic resolver now discovers a uniquely linked relative Annual Report companion, resolves the incorporated Item-8 page range, and admits only deduplicated multi-year statement-like tables within that interval; missing or ambiguous companions remain a safe no-op. IBM's audited companion `ibm-20251231_d2.htm` is stored at `data/raw/IBM/` with SHA-256 `6bad6022e0585cce956917bae6e85b3dd881234b274771343fcd8c3382c85b48`. It produced 32 supplemental `financial_table` chunks, an immutable embedding generation `nomic-e9b6763-fy2026-ibm-companion-20260829`, corpus fingerprint `sha256:1d5b99ed962ab9dff88f268ea17da4efd5c7128900961a123bdfb5e49716c8f4`, and a green trusted local Qdrant index with 10,053 points. Coverage is now 50/50 searchable tickers with financial-table chunks; IBM remains degraded only because its text `financial_statements` section is still not reconstructed. The read-only audit passes on the installed companion, and no Phase 2 evaluation was run.

The TOC-link financial-table fallback is now implemented and verified. Production table discovery preserves the Item-8..Item-9 primary path and follows individual statement TOC links only when the primary path yields no parseable tables. PEP recovers 29 parseable financial tables through its root Financial Statements anchor, while NVDA/ORCL/AVGO/GS remain covered by the existing fallback. The hard-group recovery appended 43 additional chunks (CVX 33, XOM 4, JPM 6), built immutable CUDA generation `nomic-e9b6763-fy2026-hard-group-table-recovery-20260828-attempt-01` with 10,021 points and corpus fingerprint `sha256:91828b033f530d32fba3c0dd415ffd8ee89222cf9a2e9108c5064ec838f233e0`, atomically promoted its canonical payloads, and rebuilt the trusted local index green at 10,021 points. Coverage is now 46 clean / 4 degraded / 49 financial-table; IBM is the only searchable ticker without table chunks. Filtered total-assets retrieval for CVX, XOM, and JPM promotes their new table evidence at score `10.0`. Phase 1 is rebuilt offline and byte-deterministically as artifact `sha256:acc61c6382d4f3e9c46470f602a108bb76037288b3a8d28f396638d14bcbc422` (30 cases, 61 non-empty queries, 77 unique chunks, 12/12 decomposed plans `evidence_ok`) and both frozen-evidence runners bind to it. A three-case quota probe on this binding completed 3/3 generation and 3/3 judge records, passed the FY2024 comparative acceptance, and remains non-official self-judge evidence; the previous 9,978-point Phase 2 aggregate is historical and no full N=30 Phase 2 run has been made on this corpus.

The six hard-group priority-3 cases (three fact lookups and three year-over-year multi-hop checks for CVX/JPM/XOM) are now covered by two independent deterministic retrieval replays. All `6/6` cases achieve keyword recall `1.0000`, the expected `financial_table` ticker/section, rank-1 primary evidence, and structured score `10.0000`. These cases do not alter the official priority-2 benchmark. The IBM companion-document audit v2 is complete and read-only: Item 8 references pages `42–116` of IBM's 2025 Annual Report to Stockholders, and the filing links `ibm-20251231_d2.htm`. The SEC companion was downloaded only to a temporary directory with SHA-256 `6bad6022e0585cce956917bae6e85b3dd881234b274771343fcd8c3382c85b48`; IBM's anchor-page layout resolves the interval and produces six unique statement tables with income/balance-sheet/cash-flow evidence for fiscal years 2023–2025, no duplicate chunks, and no contamination. All audit gates pass with report fingerprint `sha256:a637313aa5691d596f549489b40544bda856694b4dd039e4c99a799b93be1cea`; the primary IBM filing inputs remained unchanged. This is audit GO only: no production resolver, corpus rebuild, embedding generation, or index update has been performed.

The read-only TOC-anchor counterfactual v2 is complete and deterministic. It ranks root anchors explicitly, records DOM boundaries and tables before/inside/after each boundary, isolates non-overlapping statement-link intervals, deduplicates by table fingerprint before one chunk-build call, and never modifies corpus inputs. Two independent runs produced byte-identical JSON. NVDA and ORCL pass all gates through statement-link intervals with five buildable chunks each; AAPL, MSFT, and AMZN controls pass; PEP correctly fails this route because its root Item-8/Item-9 pair is a table-of-contents boundary with zero parseable tables inside. This does not invalidate PEP's active root-anchor fallback, which intentionally recovers statement tables preceding that root anchor; its 29-table quality audit remains a separate follow-up. Validation: targeted counterfactual tests `11 passed`; full hermetic backend suite `346 passed`.

The PEP root-anchor quality audit is now complete and read-only. It reproduces the canonical 29 PEP `financial_table` chunks exactly from the raw filing, with byte-identical independent reports and immutable raw/sections/chunks input hashes. The set contains five primary statements (income, comprehensive income, cash flow, balance sheet, and equity), ten supporting financial tables, and fourteen financial notes. The presence of the five primary statements proves the fallback serves its core purpose, while the note/supporting coverage is intentional current scope rather than evidence to narrow production selection. No production discovery, corpus, embedding generation, index, or evaluation artifact changed. The audit output is ignored under `data/diagnostics/pep_root_anchor_quality_audit.json`; validation adds fixture and real-corpus regressions.

The hard-group financial recovery audit is complete and read-only. It proves that the stored sections for CVX, XOM, JPM, and IBM are stale/missing, but it also rejects the tempting fresh-extraction output because CVX, XOM, and JPM financial-statements text is a contaminated suffix of MD&A through Item 9, Part IV, and signatures. The raw filings nevertheless expose deterministic same-document recovery routes: CVX and XOM via Financial Table of Contents internal targets, and JPM via same-document financial page anchors. IBM is structurally different: its Item 8 explicitly incorporates pages 42-116 of a separate Annual Report to Stockholders, so it requires a verified companion-document milestone. The generic same-document resolver was gated on clean boundaries, primary-statement coverage, fiscal-year parsing, and no MD&A/Part-IV contamination; fresh section text remains rejected. The ignored report is `data/diagnostics/hard_group_financial_recovery_audit.json`.

The read-only hard-group interval counterfactual now passes those gates for CVX, XOM, and JPM. It selects a deterministic same-document statement interval and stops before the notes boundary: CVX yields 33 unique tables, XOM 4, and JPM 6. Each interval has fiscal years 2023-2025, income/balance-sheet/cash-flow/equity evidence, no duplicate table fingerprints, and no MD&A, Part IV, or signature contamination. Independent reports are byte-identical (`sha256:c63c5aad6ad03b145bdeb5965cbec1fb75b2663a9496a054b74cc9bcf5999116`). The fixture-first generic resolver is now implemented in table discovery and enabled only for CVX/XOM/JPM when the primary Item-8 route is unavailable. A read-only dry run reproduces `33/4/6` unique chunks; it does not change corpus data, embeddings, the index, or evaluation artifacts. The pipeline has deliberately not been run, so current served coverage remains unchanged until a separately authorized data rebuild. IBM remains a separate companion-document milestone. The ignored report is `data/diagnostics/hard_group_interval_counterfactual.json`.

Steps 1-12 are complete for the MVP Enterprise Document QA / SEC 10-K RAG pipeline.
Phase 2A Step A, Streaming Response, is complete and verified.
Phase 2A Step A.1, Semantic Query Cache, is complete and verified.
Phase 2B Step C, Multi-turn Conversation with Memory, is complete and verified.
Phase 2B Step D, Query Decomposition, is integrated and verified for comparative queries.
Phase 2C Muc 2, deterministic evaluation metrics and enumeration retrieval diagnosis, is complete.
Phase 2C Muc 3, 30-case categorized evaluation set and decomposer-routed evaluation, is implemented and has a complete current LLM-judge run.
Phase 2C Muc 4, financial table retrieval, is complete.
Phase 2C Muc 5, corpus expansion to 25 configured tickers, is locally ingested, chunked, embedded, and indexed with explicit corpus-quality reporting. The follow-up 50-company scale trial is also locally ingested and indexed, confirming that section extraction gaps persist at larger sample size.
Phase 2C Muc 7, Qdrant Cloud production configuration and migration, is implemented and verified.
Step 12, Docker backend deployment packaging, is implemented and smoke-tested with local Qdrant volume mounting.
The Vite/React frontend is integrated and verified end to end against the Docker backend through ngrok. Its current production UX includes separate Overview and Conversation views, compact question bubbles, bounded research-response cards, evidence inspection, viewport-safe tooltips, and a resizable desktop control sidebar. Frontend validation passes 13 tests, TypeScript checking, and the production build. Runtime services are intentionally treated as session-local and are not assumed to be active.
Evaluation integrity is restored on the FY2026 corpus and the zero-table audit is complete. Phase 1 was rebuilt fully offline (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, local model cache) with `--verify-determinism`: `30/30` cases executed, `61` queries with zero empty results, two executions byte-identical, and the new embedded artifact fingerprint is `sha256:6341419c1922e465637f1881810f82a7d6c547a51ab4119ad13e22c4ea03cb87` bound to corpus `sha256:e2499754…`, index manifest `sha256:9a5e2f0d0333809d769f8b7bc04b40c03dcd130f9c605a5fbec9d90efef29b3d`, with plan `sha256:d3915eeb…`, test-set `sha256:92dc7bc0…`, embedding, reranker, and retrieval-config fingerprints unchanged from the trusted manifests. The decomposed-plan audit passes `12/12 evidence_ok` on the new artifact, with Apple-vs-Amazon FY2024 keeping balanced evidence (`AAPL:2 / AMZN:2`). Both `scripts.run_quota_probe.EXPECTED_ARTIFACT_FINGERPRINT` and `scripts.run_evaluation_phase2.EXPECTED_ARTIFACT_FINGERPRINT` now pin `6341419c…`; regression tests assert both runners share the pin, that both superseded fingerprints (`f1129d81…`, `8848d68b…`) are refused by `load_bound_artifact`, and that `main()` fails when heavier retrieval machinery is already loaded (Phase 2 never reruns the retriever). No Phase 2 run was executed and no quota consumed; the published N=30 table remains the historical result of corpus `dc44c926…`. The read-only financial-table audit (`scripts/diagnostics/financial_table_audit.py`) walked the production funnel (FS anchor → Item-8..Item-9 window tables → year-header row parsing → buildable chunks vs served artifacts) across all ten tickers lacking table chunks while hashing every read input before/after to prove `data/` immutability. Classification: CVX/IBM/JPM/XOM = `financial_statements_missing` (extraction-level incorporation-by-reference layouts; CVX/XOM/JPM show statement-analysis tables doc-wide but no Item-8 body; IBM's document has only 27 HTML tables total, so statements live in separate exhibits). NVDA/ORCL/PEP = `layout_or_exhibit`: their anchor-recovered FS text is real, but the table-discovery window anchored on the Item-8 stub text finds zero `<table>` elements while genuine statement tables exist elsewhere in each document (NVDA "Consolidated Statements of Income"/"Consolidated Balance Sheets"; ORCL statements-of-stockholders-equity region; PEP consolidated cash-flow tables). AVGO/HD = `layout_or_exhibit` plus `row_filter_miss` (real balance-sheet/equity/cash-flow tables sit outside the window; the single in-window table yields no year-header rows). GS = `layout_or_exhibit` with a 1,730-character incorporation-by-reference FS stub and ten statement-like tables elsewhere. Remediation ranking: (1) NVDA, (2) ORCL, (3) PEP — extend table discovery to reuse the same same-document TOC-anchor path the section recovery already resolves, which should expose existing statement tables without touching the extractor's text path; then AVGO/HD (window extension plus year-header tolerance), then GS (exhibit following), with CVX/IBM/JPM/XOM deferred to dedicated extraction work. Report stored under ignored `data/diagnostics/financial_table_audit.json`. Validation: targeted recovery/coverage/pin/audit tests `51 passed`; full hermetic suite `331 passed`.

The corpus 46/50 milestone is finalized on trusted generation `nomic-e9b6763-fy2026-corpus-recovery-20260826-attempt-01`. Root cause of the five remaining degraded filings was twofold: NOW/NVDA/ORCL/PEP sections JSON predated the annual-report recovery adapters (fresh extraction with existing code already restored their `financial_statements`), while PFE's MD&A intro contains an inline cross-reference ("...related notes in Item 8.") that made the nearest mdna end boundary a 463-char slice, dropping the section. `extract_sections_from_html()` now walks later end candidates while keeping a genuine start heading and rejects start candidates whose first end sits within 200 characters as table-of-contents page references, so TOC noise can never leak into or swallow sections; previously remediated and core filings verified byte-identical on fresh extraction. The full pipeline reran in order: chunking, `add_table_chunks` (+1,706 table chunks), immutable CUDA embedding generation (50 files, 9,935 finite 768-dim vectors), canonical embedded promotion verified by per-file SHA-256 plus canonical BM25 payload fingerprint, and a green local Qdrant rebuild with schema-v2 manifest binding corpus `sha256:e2499754d522d5f4d85a639a177a451973ba1b5415cb6cb6c3fd6df29ea0bc0a`, generation fingerprint `sha256:65cc3f9f84d965f825a968e576529b74b6d80bdd9631ca9be359907809dbc3fb`, point count `9935`, and pinned revision `e9b6763023c676ca8431644204f50c2b100d9aab`; `.env` selects the new generation through `EMBEDDING_GENERATION_PATH`. Coverage matrix now reports `46 clean / 4 degraded (CVX, IBM, JPM, XOM) / 40 financial_table / 9,935 chunks`, and `tests/test_corpus_coverage_matrix.py` pins this baseline including the missing-table set `{AVGO, CVX, GS, HD, IBM, JPM, NVDA, ORCL, PEP, XOM}` — note that NVDA/ORCL/PEP have real recovered statements but still zero table chunks because their statement tables live in layouts `table_extractor` does not capture, which joins AVGO/GS/HD in the financial-table audit backlog. New deterministic offline spot-checks (`tests/test_corpus_recovery_spot_checks.py`) verify ticker/section metadata, genuine body markers (consolidated balance sheets / total assets / statements of income for FS tickers, "ITEM 7." body-heading start plus "The following MD&A" for PFE mdna), anti-TOC assertions, and lexical BM25 retrievability of substantive hits for each recovered section without any provider or model call. Validation: targeted recovery/coverage tests pass `16/16` and the full hermetic backend suite passes `322 passed` offline with `--basetemp` inside the workspace. The official N=30 benchmark remains a historical result of the prior corpus `sha256:dc44c926…`: the Phase 1 artifact is stale against the new trusted index and MUST be rebuilt via `scripts.run_evaluation_phase1` before any future Phase 2 run.

The P1 context-precision experiment completed with a pre-registered, gate-gated merge. Offline per-case baseline (`scripts/diagnostics/context_packing_baseline.py`, tiktoken `cl100k_base`) measured the frozen artifact at `61,889` rendered evidence tokens across 30 cases (avg `4.37` chunks/case) and route-aware packing at `29,839` tokens (`51.79%` reduction, avg `2.13` chunks) with keyword and comparative-ticker coverage preserved in `30/30` cases. The packing algorithm (`src/evaluation/context_packing.py`) is a deterministic mandatory-set selection: primary chunk, structured promotions (score >= 10.0) plus at most one supporting passage for direct fact lookup, best-chunk-per-ticker balance for comparative plans, required-keyword donors for multi-hop facts, fill-to-four for summary/enumeration, primary-only for out-of-corpus; it never changes source order, citations, text, or adds evidence beyond the full set, and uncovered keywords are reported instead of hidden. The packed-all arm (`route_aware_v2`) ran official `30/30 + 30/30` against the same frozen Phase 1 artifact: Context Precision `0.2872 -> 0.4167` (`+0.1295`) with recall/citation intact and fallback improved, but Faithfulness regressed `-0.0800`, concentrated in enumeration (`-0.37` Microsoft risk factors), comparative-topical (`-0.60` AWS-vs-Azure), and out-of-corpus (`-0.5` Disney) cases — so packed-all was REJECTED per the faithfulness bar. The paired per-case evidence motivated `selective_packed_v1`, which packs only `fact_lookup`, `multi_hop`, and `summary`; this scope was pre-registered BEFORE its confirmatory run to avoid post-hoc selection bias. The confirmatory run completed official `30/30 + 30/30` and passed all four merge gates: Context Precision `+0.1111` (gate `>= +0.08` or `>= 0.55`), Recall Proxy unchanged `1.0000`, Faithfulness `-0.0350` (bar `-0.05`), rendered tokens `-20.19%` (bar `>= 20%`); citation correctness stayed `1.0000` and fallback accuracy improved to `1.0000`. Gate arithmetic is stored in ignored `data/diagnostics/context_packing_ab_gates.json`. Decision: `selective_packed_v1` is MERGED as the default context strategy for `scripts/run_evaluation_phase2.py` and the README benchmark now reports its official numbers (Faithfulness `0.5663`, Answer Relevancy `0.9417`, Context Precision `0.3983`, Overall `0.6354`); `full_evidence_v1` remains available via flag for replay, and production serving behavior is intentionally unchanged pending separate runtime adoption work.

The FY2024 evaluation contract is resolved end to end, and the first official two-phase N=30 run completed with `openai/gpt-oss-120b` for BOTH generation and judging. Production rule 7 in `Generator.SYSTEM_PROMPT` requires answering year-unspecified questions from the latest fiscal year available in context while stating that fiscal year. The benchmark comparative case was renamed to `Which company, Apple or Amazon, had higher total revenue in fiscal year 2024?` with FY2024 totals pinned in ground truth and required keywords; company-name keywords are intentionally excluded because financial-table chunk texts carry figures while ticker identity lives in chunk metadata. The decomposed-plan audit override key follows the rename and `extract_required_numbers` now excludes bare calendar years so period metadata cannot create false retrieval-miss classifications. Probe acceptance values agree with the question by construction, and the counterfactual diagnostics are marked superseded historical evidence. The planner snapshot was re-captured live from one schema-validated gpt-oss call under the new wording (both branches keep `financial_table` with explicit fiscal-year subquery wording). `apply_frozen_plan_overrides` can inject code-owned override plans when their question is selected but absent from the official artifact, so renamed questions do not require legacy records, and `run_evaluation_phase1` exempts the override question from the official-artifact requirement. The rebuilt Phase 1 artifact is byte-deterministic across an in-process replay: embedded artifact `sha256:8848d68b4236afbb1df5cef1be6cf9980d104bd1291703506a98d7cccd67f2ad`, file SHA-256 `a2dff43483dc66832e285e2c52ce13e43cef8e59cb6e59ea14adcf3c517b2470`, plan `sha256:d3915eeb21dc5ea68b4955abd972546390feaf03f65c841cb7341c96a5ac2e07`, test set `sha256:92dc7bc0bf9831406c9ffc45e857cc9e1c2d6425d27806e1a0b3f1a30042726d`; corpus, index-manifest, embedding, reranker, and retrieval-config fingerprints are unchanged, and the decomposed-plan audit passes `12/12 evidence_ok` including balanced `AAPL:2 / AMZN:2` evidence for the renamed case. The comparative-only probe passed every deterministic acceptance gate (both FY2024 totals cited, Amazon identified higher, citation correctness `1.0`). New `scripts/run_evaluation_phase2.py` binds to the pinned fingerprint, refuses drift, checkpoints both phases, stops immediately on quota, and gates `official=true` on full OK coverage under one binding plus an explicit completeness check so an early stop can never look official. The first attempt stopped at judge case 10 when gpt-oss spent its entire 1024-token completion budget on reasoning and returned empty content; the shared Phase 2 completion budget is now `2048`, it flows into the judge binding explicitly in both runners, and generation bindings exclude completion caps, so all 30 generation checkpoints survived without re-spending quota. Final official run: `30/30` generations OK and `30/30` judgments OK, no skipped records, no parse failures. Scores: Faithfulness `0.6013`, Answer Relevancy `0.9283`, Context Precision `0.2872`, Overall `0.6056`, Citation Correctness `1.0000`, Recall Proxy `1.0000`, Fallback Accuracy `0.9667`. Category table (faithfulness/relevancy/precision): fact_lookup `N=8` `0.6875/1.0000/0.2162`, summary `N=6` `0.5083/0.9250/0.5600`, enumeration `N=4` `0.5225/0.9000/0.3200`, comparative `N=6` `0.4833/0.8000/0.2867`, multi_hop `N=3` `0.6667/1.0000/0.1750`, out_of_corpus `N=3` `0.8333/0.9667/0.0000`. Judge-model confound: this table must NOT be compared with the earlier llama-3.3-70b-versatile-judged aggregate (`Faithfulness 0.8533`, overall `0.7501`); the gpt-oss self-judge is measurably stricter, and several zero-faithfulness cases (Apple auditor, AWS net sales change, Amazon North America operating income) quote values verbatim present in frozen evidence, mirroring the known judge strictness pattern. Deterministic checks are model-independent and stay perfect except one conservative abstention: the AWS-segment-vs-Azure-growth comparison answered with the explicit insufficient-context fallback, the single fallback-accuracy miss (`29/30`). Out-of-corpus context precision is `0.0` by design. Latency is not a benchmark because Groq returned repeated `429`s during judging. README now reports this run as the official benchmark with the confound disclosed and documents the two-phase commands; the old llama-judged table survives only as historical context here.

The read-only corpus coverage audit (`python -m scripts.corpus_coverage_matrix`) now provides the authoritative per-ticker coverage matrix over served embedded chunks. It reports section presence/absence, text and financial-table chunk counts, clean/degraded/missing status, deterministic JSON output with schema version 1, and reuses `compute_corpus_fingerprint`, which reproduces the trusted manifest fingerprint exactly. [HISTORICAL BASELINE, superseded by the FY2026 corpus recovery: the audit at that time confirmed 50 configured and searchable tickers, 41 clean, 9 degraded (CVX, IBM, JPM, NOW, NVDA, ORCL, PEP, PFE, XOM), 39 with financial_table chunks, and 9,703 total chunks; missing-section detail showed PFE lacking only mdna, NOW/NVDA/ORCL/PEP lacking only financial_statements, and the remaining five degraded tickers lacking both mdna and financial_statements.] Tests cover status logic, byte-identical reruns, corpus immutability via tree hashing, and the local baseline regression (skipped when the ignored local corpus is absent). Validation: full backend suite passes with no regressions.
The backend test suite is now hermetic by default. An autouse fixture in `tests/conftest.py` replaces `socket.socket` with a subclass whose outbound `connect`/`connect_ex`/`sendto` raise immediately for non-loopback targets and blocks external `getaddrinfo`/`gethostbyname`/`create_connection`; loopback stays allowed because CPython event loops create 127.0.0.1 self-pipes internally (blocking it broke 48 tests before the carve-out). `pytest.ini` registers `integration` and `live_network` markers and deselects `live_network` from default runs via `addopts`. The former live-network `test_get_cik_apple` was replaced by twelve mocked `SECEdgarClient` tests covering User-Agent wiring, exact ticker-map URL, AAPL CIK parsing (`320193`), map caching, override short-circuiting, unknown tickers, `404`->`EdgarNotFoundError`, `429`->`EdgarRateLimitError`, other HTTP errors propagating unchanged, filings metadata/submissions URL, accession-dash handling, and missing-form errors; a new opt-in live smoke lives at `python -m scripts.diagnostics.sec_live_smoke`, outside pytest collection. Meta-tests prove external TCP/DNS/create-connection are blocked while loopback binds/connects still work. Hermetic proof: the full suite passes `263 passed` twice — once normally and once with poisoned `HTTP_PROXY`/`HTTPS_PROXY` (`10.255.255.1:9`) plus `HF_HUB_OFFLINE=1`/`TRANSFORMERS_OFFLINE=1`. CI needs no changes because the guard ships in-repo and the workflow already sets the HF offline flags.
The shared-rate-limit-bucket bug behind ngrok is fixed via `TRUSTED_PROXY_CIDRS` (empty default preserves legacy peer keying). `src/api/proxy.py` resolves the slowapi bucket identity: only a socket peer inside a configured trusted CIDR has `X-Forwarded-For` honored, the header is walked right-to-left past trusted hops to the first non-trusted address, and malformed headers, untrusted peers, or all-trusted chains fall back to the socket peer, so direct clients cannot forge their bucket. Invalid CIDR entries are logged and grant no trust. Tests cover IPv4/IPv6 (including bracketed tokens), multi-hop chains, seven malformed-header shapes, API-level separate buckets behind one proxy peer, and unique-header sharding refusal; docker-compose forwards the variable and `.env.example`, README, and ARCHITECTURE document the ngrok/Docker topology.
The current-planner snapshot for `Which company, Apple or Amazon, has higher total revenue?` is now frozen into deterministic Phase 1 plan provenance. The single schema-validated `openai/gpt-oss-120b` planner call retained the bare per-company revenue wording but selected `financial_table` for both branches; this lets structured lookup promote the correct AAPL and AMZN `Total net sales` rows at score `10.0`, unlike the stale llama-era `financial_statements` filters. Only this one N=30 case changed. The rebuilt artifact is byte-identical across an in-process determinism replay and an independent process: embedded artifact fingerprint `sha256:f1129d814274e95d3b2019aa58ef840fc28817c1d82b548a613e2de697986841`, file SHA-256 `50e45dce42a9a0e657503036905850866eff7115687e86e10e26953f01376e92`, and plan fingerprint `sha256:e296e0e34cf5afb03b555381db67cc5bc071de9b85617b274e8fe490bf37369a`. The corpus/index/embedding/reranker/retrieval fingerprints remain unchanged, the decomposed-plan audit is now `12/12 evidence_ok`, and the new generation binding sees zero compatible records from the old three-case probe.
The comparative-only Phase 2 probe against that artifact completed with exactly one generation and one judge call. `openai/gpt-oss-120b` answered that Amazon is higher, cited in-range sources (`citation_correctness=1.0`), and the self-judge scored Faithfulness `1.0`, Answer Relevancy `1.0`, and Context Precision `0.5`; the result remains explicitly non-official. The answer selected the latest 2025 columns (`Apple 416,161`, `Amazon 716,924`) because the question does not specify a year, rather than the approved diagnostic acceptance's FY2024 figures (`391,035`, `637,959`). Deterministic probe acceptance therefore remains false even though the comparison and judge scores pass. Do not start the full N=30 Phase 2 run until the evaluation contract explicitly resolves this year ambiguity; do not hide it with a probe-only prompt.
Stable architecture documentation is complete in `ARCHITECTURE.md`, with README, project journal, agent guide, and frontend guide responsibilities explicitly separated to prevent stale duplicated status.
Mode-aware retrieval chunk loading is now centralized in `src/retrieval/chunk_loader.py`. FastAPI startup, evaluation, and all hybrid-retrieval diagnostics use the same source-selection contract: local mode reads nested `*_chunks_embedded.jsonl` artifacts and removes stored embeddings before building in-memory indexes, while cloud mode scrolls payloads from the active Qdrant collection. Dedicated tests cover mutually exclusive cloud/local interactions, nested ticker directories, blank JSONL lines, suffix filtering, and embedding removal. Moving the local loader out of `hybrid_retriever.py` reduced its isolated cold test from `28.85s` to `0.03s` by avoiding SentenceTransformers/PyTorch imports. Validation after the migration: `127 passed, 9 warnings`; Python compile checks pass.
Near-duplicate context diagnostics now have pure, separately owned metric, replay-contract, fingerprint, runner, and composition layers. The pre-registered contract separates exact duplicates, adjacent five-gram containment, semantic-only pairs, token-weighted pairwise overlap pressure, replay fidelity, out-of-corpus exclusions, low/high Context Precision cohorts, grouped descriptive summaries, and Spearman association. Original-query proxy is locked as the deterministic primary policy for the three direct official cases whose historical effective rewrites were not stored; those cases remain descriptive-only. The official artifact maps to 18 direct and 12 decomposed routes, including 43 saved subqueries, with a pre-replay primary eligibility ceiling of 24/30.
The audited context-duplicate replay has now run on the complete official N=30 artifact against the trusted local 7,940-chunk corpus: all 30 replays succeeded, with 24 primary-eligible cases, 3 original-query-proxy exclusions, and 3 out-of-corpus exclusions. It found zero exact duplicate pairs and zero semantic-only pairs at thresholds `0.95` and `0.98`. Adjacent five-gram overlap does not explain low Context Precision: low-precision cases had lower mean pairwise overlap mass (`0.0288`) than high-precision cases (`0.0491`), and the eligible-case Spearman association was weakly positive (`+0.0946`). No production deduplication should be added from this evidence. The report is stored under ignored `data/diagnostics/context_duplicate_report.json`; its corpus/replay/contract fingerprints are recorded, while retrieval fingerprint is explicitly `None` because a complete runtime retrieval-provenance manifest has not yet been published.
Annual-report extraction remediation is complete for MS, MCD, INTC, COST, GE, and HON. `extract_sections_from_html()` preserves Item boundaries as the primary path, then recovers missing sections from same-document anchors or exact annual-report headings. The extraction audit passes for all six filings with four target sections each. [Historical state, superseded by the FY2026 rebuild:] The rebuilt corpus contained 9,703 chunks, including 1,688 financial-table chunks; all 50 configured tickers were searchable at that point. The API also auto-scopes an unambiguous company name and deterministically translates only explicit Vietnamese financial intents (`doanh thu`, `rủi ro`, `tài sản`, `lợi nhuận`) for English retrieval; ambiguous Vietnamese requests remain unchanged. Aggregate request telemetry records only route/status/latency/error counters, attaches `X-Request-ID`, and keeps `/metrics` disabled by default.
The immutable generation `nomic-e9b6763-annual-report-rebuild-20260818-attempt-05` [SUPERSEDED by `nomic-e9b6763-fy2026-corpus-recovery-20260826-attempt-01`] completed with 9,703 finite 768-dimensional vectors, corpus fingerprint `sha256:dc44c9266856b044e8e928a0681f6f05a5e4889a3217c8eae3cdd0b080d391e2`, vector snapshot `sha256:83fb66ffbe1d1ba8c451fbddc242113523030101ee4b320bd5549b5df43a626a`, and generation fingerprint `sha256:3d787ba44324b2726d66bf2119597b1adcfc9de6f5413a71c4923b5c6bd46ba1`. The builder can now reuse a completed generation only after exact model metadata, manifest hash, canonical payload, and vector-dimension checks; unchanged files were reused and changed filings were re-embedded. Local Qdrant was rebuilt and verified green at 9,703 points with a schema-v2 manifest. Priority-1 deterministic retrieval remains `0.9688`, preserving the previous result.
Groq retired `llama-3.3-70b-versatile` for free/developer access on 2026-08-16. Serving and future evaluation defaults now use Groq's recommended `openai/gpt-oss-120b`. A live smoke query returned HTTP 200 and the correct Apple 2024 total net sales of `$391,035 million`; the remaining smoke batch encountered provider rate limiting, not a retrieval or model-ID failure. The Windows smoke script now forces UTF-8 output so Unicode model responses do not crash the diagnostic.
Groq key rotation now supports two independent pools. Serving and judging rotate `GROQ_API_KEY` with `GROQ_API_KEY2`; evaluation generation rotates `GROQ_API_KEY_FALL_BACK` with `GROQ_API_KEY_FALL_BACK2`, falling back to the primary pool only when both evaluation keys are blank. Keys are deduplicated, never logged, selected round-robin, and placed on a parsed cooldown after `429`/rate-limit responses so another available key is tried immediately. Streaming opens its provider connection through the same rotation path.
Trusted local-index manifest support is implemented and has now completed its first approved local execution. Canonical corpus identity hashes 7,940 sorted chunk payloads to `sha256:0166056c9e2f9f641e4af532ecc6416403b86887a58dfafcde8a4184575a2da3` while excluding vectors, paths, and timestamps. The immutable generation `nomic-e9b6763-corpus-0166056c-builder-v1-attempt-01` was built in one completed CUDA run with Nomic revision `e9b6763023c676ca8431644204f50c2b100d9aab`, builder `embedding-builder-v1-generation`, 44 output files, and 7,940 finite 768-dimensional vectors. Independent disk revalidation produced vector snapshot `sha256:abdd5a1821104de96e4084f666f1ef7fcbf1d43cd134ddf8ee2613dd6399cd1a` and generation fingerprint `sha256:fd1241d3aa2b9284e9f611a74961c3f5ff7a3217e98676beba09805d6e738bf0`. Local Qdrant was rebuilt in place, verified green at 7,940 points, and bound to a schema-v2 index manifest. Critical deterministic retrieval checks passed for AAPL/MSFT total assets, Tesla revenue, AWS change, Apple auditor evidence, and ticker/section isolation; the full direct priority-1 diagnostic retained average keyword recall `0.9688`, with only the known non-decomposed Microsoft enumeration case at `0.5`. The pinned revision is now persisted in the ignored local `.env`, documented in `.env.example`, and explicitly forwarded by Docker Compose. A host API restart using only the persisted setting and offline model cache returned ready, exposed 44 supported tickers, and reproduced the same `0.9688` priority-1 retrieval result. Docker Compose configuration validation passes, but the container was not recreated during this verification because Docker Desktop was not running. A SHA-256 verified same-volume backup is retained at `D:\Enterprise_Document_QA_Backups\nomic-e9b6763-corpus-0166056c-builder-v1-attempt-01`; it protects procedural rollback, not whole-drive failure. The Cloud index still predates trusted verification and remains untrusted/NO-GO.
Immutable embedding-generation support now closes the mixed-generation gap identified during read-only rebuild preflight. A build must target a new validated generation ID outside `data/processed`; existing directories fail fast, individual JSONL outputs use atomic replacement, and the completion manifest is published only after all outputs are reloaded from disk. The manifest records deterministic relative paths, record counts and file hashes plus corpus/vector fingerprints, model revision, device/runtime metadata, dtype, normalization policy, and builder version. Its fingerprint excludes only `completed_at` and itself. `scripts/index_chunks` requires an explicit generation path, recomputes all file/corpus/vector facts, verifies both source chunks and the canonical embedded payload used by local BM25, and rejects incomplete, stale, traversing, or mixed inputs before opening Qdrant. Index manifest schema is now version 2 and obtains model/vector/generation provenance only from the validated generation manifest; schema-v1 manifests are not trusted. Failed and old generations are not cleaned up automatically, and the old in-place embedding helper was removed so staging is the only CLI build path. Validation passes 37 targeted tests and the full backend suite passes 201 tests with 9 existing warnings. Initial implementation validation used workspace fixtures without touching `data/`; the later approved local execution and its resulting trusted artifacts are recorded separately above.

Current deployment milestone: the zero-cost Vercel frontend is live at `https://frontend-one-gamma-f9jf11u8ec.vercel.app`, with the reserved ngrok endpoint forwarding to the owner's local Docker backend. Startup/shutdown automation, final-origin CORS, public readiness, 44-ticker discovery, and a real Apple query are verified. The owner must keep Docker and ngrok running during demo sessions.

Current Muc 7 Qdrant Cloud status:

- `configs/settings.py` supports `QDRANT_MODE`, `QDRANT_LOCAL_PATH`, `QDRANT_CLOUD_URL`, `QDRANT_CLOUD_API_KEY`, and the comma-separated `ALLOWED_ORIGINS` CORS allowlist.
- `VectorStore` supports local persistent mode and Qdrant Cloud mode while preserving the old `VectorStore(path=...)` local call pattern.
- FastAPI startup, evaluation, and `scripts/diagnostics/rag_smoke_test.py` now use the configured Qdrant mode.
- `scripts/index_chunks.py` intentionally rebuilds only the local Qdrant index via `settings.qdrant_local_path` to avoid accidentally deleting a cloud collection.
- `scripts/migrate_to_qdrant_cloud.py` migrates the active local `sec_filings` collection to Qdrant Cloud. It upserts by default and only deletes/recreates the cloud collection when `--recreate` is explicitly passed.
- Qdrant Cloud was remigrated non-destructively after the 50-company scale trial and restored table chunks: local points `7,940`, cloud points `7,940`. The first attempt exposed a stale cloud endpoint in `.env` via an immediate `404` before any write; after updating the endpoint, all local points were upserted without recreating the collection. Post-migration verification returned an exact ordered top-5 chunk-ID match for the fixed Apple net-sales query.
- Qdrant Cloud required keyword payload indexes for filtered search; `ticker` and `section` indexes are now created by both `VectorStore.create_collection()` and the migration script.
- `scripts/verify_qdrant_cloud.py` compares local vs cloud top-5 chunk IDs for a smoke query after migration.
- Local-vs-cloud verification passed with exact top-5 match for `What was Apple's total net sales in 2024?` filtered to `AAPL`.
- README documents the Qdrant Cloud migration and verification flow.
- Validation after implementation: `.venv\Scripts\python.exe -m pytest tests/ -v` passes with `44 passed, 9 warnings`; `.venv\Scripts\python.exe -m compileall configs src scripts` passes.

Corpus quality during the annual-report-recovery era (HISTORICAL; superseded by the FY2026 recovery — current state is 46 clean / 4 degraded / 40 financial_table / 9,935 chunks, see the corpus-recovery entry near the top of this journal):

- 50-company scale trial completed locally with the current extractor and CUDA embedding environment.
- Text-section status at that time: 41 filings exposed all four target sections and 9 remained degraded but searchable; no configured ticker was unusable.
- Before annual-report recovery, the 50-company trial measured `35 clean / 9 degraded / 6 unusable`; this is retained as the pre-fix baseline rather than the current corpus status.
- Clean for evaluation/demo requiring all four text sections: AAPL, MSFT, AMZN, GOOGL, META, TSLA, MS, BAC, GS, BRK-B, JNJ, UNH, WMT, HD, MCD, AMD, INTC, QCOM, AVGO, TXN, CRM, V, MA, AXP, LLY, MRK, ABBV, TMO, PG, KO, COST, NKE, CAT, GE, BA, LMT, HON, UPS, RTX, VZ, T.
- Degraded but usable for some section-specific questions: NVDA, JPM, PFE, XOM, CVX, ORCL, NOW, IBM, PEP.
- Qdrant local indexed 9,703 chunks from all 50 configured tickers at that time (now 9,935 after the FY2026 recovery).
- `financial_table` chunks are present for 39 searchable tickers; the 11 tickers still missing them are AVGO, CVX, GS, HD, IBM, JPM, NOW, NVDA, ORCL, PEP, and XOM.
- Pipeline hazard fixed: `scripts.chunk_filings` overwrites `*_chunks.jsonl` via `save_chunks(... open("w"))`, which removes appended `financial_table` chunks unless `scripts.add_table_chunks` is rerun afterward. The first attempted recovery appended 1,336 table chunks but `scripts.embed_chunks` skipped stale `_chunks_embedded.jsonl` files because it checked only output existence, leaving Qdrant unchanged at 7,142 points. `scripts.embed_chunks` now compares modification times and re-embeds when the source `*_chunks.jsonl` is newer than the embedded output. Final verification: chunk files total `7,940`, embedded files total `7,940`, and Qdrant points_count is `7,940`.
- `scripts/download_filings.py` now marks 0-section extraction as `failed` instead of successful/skipped, and marks partial section extraction as `degraded` with explicit missing-section warnings.
- Structural limitation identified: degraded/unusable filings commonly use incorporation-by-reference language and annual-report/page-reference layouts around Item 7 and Item 8. Examples include JPM Item 7/8 pointing to MD&A pages 46-160 and financial statements pages 162-314, XOM Item 7/8 pointing to the Financial Section, CVX Item 7/8 pointing to Financial Table of Contents entries, and MS/MCD/INTC using annual-report layouts where relevant content is not exposed through standard `Item 7 ... Item 8` boundaries. The three newly failed 50-company tickers, COST, GE, and HON, also produced `sections={}` exactly like MS/MCD/INTC, confirming a recurring extractor-layout limitation rather than six unrelated failures. This is not just a missing regex keyword. Some content may still be present in the same primary HTML, while other filings may require following referenced exhibits or report sections. Supporting these cases requires a separate annual-report/table-of-contents aware ingestion/extraction pass, out of scope for the current single-document section extractor.
- For evaluation and portfolio demos, prefer the 35 clean tickers. Degraded tickers remain usable only for sections that were actually extracted, especially business and risk-factor queries.
- Cross-encoder score calibration finding: generic summary-style questions such as `What are X's main risk factors?` can score low or negative even when retrieval is verified correct by ticker, section, and content. Confirmed scores: AAPL `0.78` (positive outlier), MSFT `-1.70`, AMZN `-1.95`, JNJ `0.24`, BAC `-4.68`, UNH `-5.19`, GOOGL `-5.10`. Root cause: `ms-marco-MiniLM` scores specific query-passage relevance; broad summary queries do not have one strongly matching passage the same way fact-lookup queries do. Current impact is safe because `Generator.LOW_SCORE_THRESHOLD = 0.50` only logs a warning and does not block answer generation or trigger fallback. Before using retrieval score for fallback decisions or user-facing confidence, thresholds must be calibrated by query type/category instead of using one global cutoff.
- Evaluation finding: derived/trend phrasing remains a retrieval limitation for raw financial table evidence. Examples: `How did Microsoft's total assets change year over year?` and the earlier `AWS revenue growth` case. The correct table chunks exist, but cross-encoder ranking scores the table evidence poorly for broad change/growth wording, even when `financial_table` is forced. This is a query formulation/ranking limitation, not table extraction failure.
- Evaluation safety guard: `QueryDecomposer` now has a minimum-evidence guard (`MIN_CHUNKS_FOR_SYNTHESIS = 2`) that returns a fallback instead of synthesizing when decomposition retrieves too little evidence. Unit tests cover both fallback and normal synthesis paths. Follow-up evidence showed the Amazon business-segment case is not covered by this quantity guard because it retrieves enough chunks, and the current `AMZN_business_0000` chunk explicitly contains the segment sentence (`North America`, `International`, `Amazon Web Services`). Treat the prior Amazon judge score of `0.00` as an evaluation/context-audit item rather than confirmed hallucination until the exact judge context is inspected.
- Evaluation context visibility had two layers of truncation risk. First, the LLM judge previously saw only the first 250 characters of each retrieved chunk, hiding the Amazon segment evidence; this was increased to `JUDGE_CONTEXT_CHARS_PER_CHUNK = 1000`. Second, the Apple auditor case proved that a fixed prefix can still miss evidence (`Ernst & Young` and `October 31` appear around offsets `1453-1547` in `AAPL_000032019325000079_financial_statements_0019`). The evaluator now uses relevance windowing (`_extract_relevant_window`) to select a query-relevant 1000-character window instead of always taking the chunk prefix, with regression tests for both Amazon-style and Apple-auditor-style failures. Previous faithfulness/context-precision scores from Muc 3 through the latest priority-1 run may be underestimates and should be re-evaluated before being treated as final metrics.
- Pre-evaluation Tier 1 checks completed: `/supported-tickers` was fixed to report the 22 tickers with embedded chunks instead of the old hardcoded 3-ticker list, and API validation now accepts dash tickers such as `BRK-B`.
- Degraded ticker section audit: NVDA has `business/mdna/risk_factors`; JPM, XOM, and CVX have `business/risk_factors`; ORCL has `business/mdna/risk_factors`; PFE has `business/financial_statements/financial_table/risk_factors`. Financial questions for degraded tickers without `financial_table` or `financial_statements` should be treated as limited-data cases.
- Single-turn trend/growth query expansion added before the clean priority-1 evaluation: AWS revenue growth now retrieves the AWS net sales evidence at rank 1, and Microsoft total assets year-over-year now retrieves `MSFT_000095017025100235_financial_table_0001` at rank 1 under `financial_table`.
- Current unit test suite after these fixes: `48 passed, 9 warnings`.
- Trade-off: trend/growth query expansion adds one LLM rewrite call for underspecified single-turn trend queries. This improves retrieval for known table-backed trend cases but increases token budget consumption; it contributed to Groq quota exhaustion before completing the `multi_hop` and `out_of_corpus` categories in the latest priority-1 evaluation attempt.
- Latest priority-1 evaluation attempt after all fixes judged 14/18 cases before Groq TPD quota stopped the run. Judged averages: Faithfulness `0.6964`, Answer Relevancy `0.7286`, Context Precision `0.6736`, Overall `0.6995`, Citation Correctness `1.0`, Recall Proxy `0.9231`, Fallback Accuracy `0.9286`. Category coverage: `fact_lookup=4/4`, `summary=3/3`, `enumeration=4/4`, `comparative=3/3`, `multi_hop=0/3`, `out_of_corpus=0/1`. Do not publish this as the final README/CV metric until the skipped cases are completed after quota reset.
- `scripts/run_evaluation.py` now supports repeated `--category` filters so quota-sensitive categories can be evaluated first, for example `--category multi_hop --category out_of_corpus`.
- Priority-1 `multi_hop/out_of_corpus` were evaluated separately after relevance windowing. Results: Apple net sales trend `1.0/1.0/1.0`, Amazon AWS net sales change `0.0/0.5/1.0`, Microsoft total assets YoY `1.0/1.0/1.0`, Netflix out-of-corpus `1.0/1.0/0.0`. This confirms the Microsoft total assets retrieval/generation fix works end-to-end. The remaining AWS issue is answer completeness: retrieved context is precise and recall is `1.0`, but the answer gives only `20%` growth instead of quoting the 2024 and 2025 net sales amounts expected by the ground truth. Netflix fallback is correct; context precision is `0.0` because retrieved chunks are intentionally irrelevant for out-of-corpus questions.
- Financial `total X` fact lookup has a confirmed retrieval-routing boundary. LLM financial query expansion fixed MSFT total assets (`$619,003`) and AMZN total assets works but remains fragile with low/negative retrieval scores. AAPL total assets is not fixed: `AAPL_000032019325000079_financial_table_0002` contains `Total assets | 359,241 | 364,980`, but it does not rank into final context even after rewriting; the system safely falls back instead of citing the wrong `long-lived assets` figure. Root cause: query rewriting improves semantic similarity but does not guarantee the correct table row beats near-duplicate line items in cross-encoder re-ranking. A robust fix requires retrieval routing or a structured table lookup path for `total X` queries, deferred as a known architectural boundary.
- Final Phase 2 full 18-case judged table with all fixes applied could not be obtained in the same session because Gemini judge quota was exhausted from the start of the final attempt (`JUDGE_SKIPPED_QUOTA` for the first 14 generated cases), and Groq TPD quota then blocked the final 4 cases. This final attempt produced no new OK judged records, so it must not be treated as a scored evaluation run. Confidence in the last fixes is based on deterministic tests and exact string checks against generated answers in `data/eval_checkpoint.jsonl`: MSFT total assets FY2025 contains `619,003`, Apple auditor/date contains `Ernst & Young` and `October 31, 2025`, and Amazon AWS net sales contains `128,725`. Current suite is `55 passed, 9 warnings`. The next official full evaluation should wait for a full daily quota reset on both Groq and Gemini before starting.
- Priority-1 full 18-case evaluation was completed with no skipped records after switching the judge provider from Gemini to Groq (`llama-3.1-8b-instant`) because Gemini free-tier RPD blocked the start of consecutive sessions. Generation used Groq `llama-3.3-70b-versatile`, with `GROQ_API_KEY_FALL_BACK` selected for evaluation generation and the primary `GROQ_API_KEY` used for judging. Scores from this run are not perfectly comparable to prior Gemini-judged runs because different judge models may calibrate severity differently. Self-grading bias risk increased slightly (same provider, different model) versus the original cross-provider judge design, but this was accepted to obtain actual scores rather than none. Results: Faithfulness `0.6594`, Answer Relevancy `0.5500`, Context Precision `0.4000`, Overall `0.5365`, Citation Correctness `1.0000`, Recall Proxy `0.9375`, Fallback Accuracy `1.0000`, Avg Latency `15.7051s`. Category table: fact_lookup `4` cases `0.75/0.60/0.475`; summary `3` cases `0.7333/0.7333/0.50`; enumeration `4` cases `0.7675/0.775/0.50`; comparative `3` cases `0.5333/0.4667/0.40`; multi_hop `3` cases `0.3333/0.2667/0.20`; out_of_corpus `1` case `1.0/0.0/0.0`. Compared with the previous merged 18/18 Gemini-judged baseline (`Faithfulness=0.7083`, `Context Precision=0.6906`), this Groq-judged run is lower, but the comparison is judge-confounded. Important case notes: AWS revenue growth answer now includes both absolute values (`$107,556 million` in 2024 and `$128,725 million` in 2025) plus `20%`, but Groq 8B judge still scored it `0/0/0` while claiming those values were unsupported, indicating possible judge/context-understanding weakness. MSFT total assets fact lookup answer includes `$619,003`, but Groq 8B judge scored it `0/0/0` for the same unsupported-context reason. MSFT total-assets YoY regressed in retrieval/generation during this run and answered with incorrect figures (`$371,902` and `$301,369`), so that case remains a real retrieval-routing issue.
- Judge model regression confirmed: Groq `llama-3.1-8b-instant` produces false-negative faithfulness/precision scores even when exact expected numbers are verbatim present in the judge context. Confirmed examples: MSFT total assets answer cites `$619,003` and the retrieved context contains `Assets - Total assets | 619,003 | 512,163`; AWS revenue-growth answer cites `$107,556 million` and `$128,725 million`, and the retrieved context contains `AWS 107,556 128,725` plus `AWS ... 20` year-over-year growth. The 8B judge still claimed those values were not present. Therefore the `0.5365` overall score from the 8B-judged run is invalid and must not be used for README/CV. `scripts/run_evaluation.py` now uses Groq `llama-3.3-70b-versatile` for the judge again. This accepts same-model self-grading bias in exchange for a judge that can read the financial context reliably.
- MSFT total assets YoY is confirmed as a genuine retrieval bug, not a rewrite-quality issue. The LLM-rewritten query correctly requests `balance sheet total assets, not a subtotal like current assets or long-lived assets`, but the retriever/cross-encoder still ranked the wrong long-lived/geographic-assets chunk above the correct `financial_table` evidence in the direct pipeline test. Forcing literal numeric values into the query (`619,003 512,163`) moves `MSFT_000095017025100235_financial_table_0001` to rank 1, confirming that the cross-encoder responds to exact number overlap but not reliably to natural-language disambiguation. This extends the AAPL total-assets structural limitation to MSFT under trend-question phrasing; the `total X` retrieval gap is broader than one company and should be addressed with structured row lookup or explicit retrieval routing rather than more rewrite prompting.
- Priority-1 evaluation was rerun with Groq `llama-3.3-70b-versatile` for both generation and judging. It completed 12/18 judged OK records before Groq 70B quota/rate limits skipped the final 6 cases, so it is not a final 18/18 table. Partial judged averages over the 12 OK cases: Faithfulness `0.8833`, Answer Relevancy `0.9250`, Context Precision `0.5292`, Overall `0.7792`, Citation Correctness `1.0000`, Recall Proxy `1.0000`, Fallback Accuracy `1.0000`, Avg Latency `12.9622s`. Covered categories: fact_lookup `4/4` (`1.00/1.00/0.34`), summary `3/3` (`0.80/0.83/0.73`), enumeration `4/4` (`0.85/0.93/0.55`), comparative `1/3` (`0.80/0.90/0.60`). Skipped due to quota: Apple-vs-Amazon revenue comparison, cybersecurity comparison, all 3 multi-hop cases, and Netflix out-of-corpus. The 70B judge corrected the earlier 8B false negative on MSFT total assets: the fact-lookup case scored `1.00/1.00/0.20` with `$619,003` present. This partial run is useful evidence that 70B judging is more reliable than 8B, but it must not be published as a complete priority-1 score.
- FINAL reliable evaluation snapshot for current reporting: use the Groq 70B judge 12/18 quota-limited run as the reference metric with explicit partial-coverage disclosure. Scores: Faithfulness `0.8833`, Answer Relevancy `0.9250`, Context Precision `0.5292`, Citation Correctness `1.0000`, Recall Proxy `1.0000`, Fallback Accuracy `1.0000`. This is the most trustworthy score obtained in the project because switching only the judge from `llama-3.1-8b-instant` to `llama-3.3-70b-versatile` moved the same fact_lookup coverage from false-negative behavior to Faithfulness `1.0000`. The 8B-judged `0.5365` overall score is excluded from reporting. Coverage: fact_lookup `4/4`, summary `3/3`, enumeration `4/4`, comparative `1/3`; not covered: multi_hop `0/3`, out_of_corpus `0/1`, remaining comparative `2/3`. Fact_lookup Context Precision `0.3375` is the clearest quantified instance of the long-standing retrieval-noise limitation: correct answers are reliably found, but retrieved context includes more irrelevant chunks than necessary. Decision: stop the same-day re-run cycle after repeated quota exhaustion; use this 12/18 70B-judged snapshot for README/CV with the partial-coverage caveat.
- FINAL priority-1 evaluation completed with Groq `llama-3.3-70b-versatile` for both generation and judging after a fresh 70B quota probe passed. This is the first reliable 18/18 priority-1 table with the 70B judge and no skipped records. Results: Faithfulness `0.8000`, Answer Relevancy `0.8444`, Context Precision `0.4250`, Overall `0.6898`, Citation Correctness `1.0000`, Recall Proxy `0.9375`, Fallback Accuracy `0.9444`, Avg Latency `14.2639s`. Category table: fact_lookup `4/4` = `1.00/1.00/0.3375`; summary `3/3` = `0.80/0.8333/0.6333`; enumeration `4/4` = `0.85/0.9250/0.55`; comparative `3/3` = `0.70/0.6667/0.4667`; multi_hop `3/3` = `0.50/0.6667/0.2667`; out_of_corpus `1/1` = `1.00/1.00/0.00`. The 8B-judged `0.5365` overall score remains invalid and excluded from reporting. Key interpretation: fact_lookup is now validated at perfect faithfulness/relevancy, but context precision remains low because retrieval returns extra chunks; MSFT total-assets YoY remains the real known retrieval failure (`0.00/0.20/0.00`, recall `0.00`, fallback incorrect) due to total-assets table-row routing; AWS net sales change includes the required values (`107,556`, `128,725`, `20%`) and scored partially (`0.50/0.80/0.20`) due to context precision/judge strictness; Netflix out-of-corpus fallback scored `1.00/1.00/0.00` with fallback correct.
- AWS net sales change reason audit: the 70B judge credited the `20%` increase but claimed the absolute figures `$107,556 million` and `$128,725 million` were not present in retrieved context. Direct context inspection shows both values are present in Source 2 (`AWS 107,556 128,725`), so this case should be treated as improved generation with a remaining judge/context-window strictness artifact plus low context precision (`only one chunk out of five relevant`), not as a fully unfixed generation issue.
- Lightweight structured financial-table lookup implemented for confident balance-sheet/income-statement `total X` queries. It parses existing markdown `financial_table` chunks at retrieval time, matches exact canonical row labels such as `Assets - Total assets`, and promotes the matched chunk to rank 1 before returning hybrid results. This intentionally avoids data regeneration and does not override explicit incompatible section filters. Direct verification: AAPL total assets now retrieves `AAPL_000032019325000079_financial_table_0002` at rank 1 and answers `359,241`; MSFT total assets fact lookup retrieves `MSFT_000095017025100235_financial_table_0001` at rank 1 and answers `619,003`; MSFT total-assets YoY retrieval now ranks the same correct financial-table chunk first with both `619,003` and `512,163`, pushing the old long-lived/geographic-assets chunk below it. End-to-end generation re-verification for `How did Microsoft's total assets change year over year?` now answers correctly with `619,003`, `512,163`, and the computed increase `106,840`, so the previous `0.00/0.20/0.00` evaluation result should be treated as pre-structured-lookup historical evidence, not the current behavior. Full test suite after this change: `58 passed, 9 warnings`.
- C3 scoped-lock experiment result: narrowing the `HybridRetriever` lock to only `embed_query()` and `cross_encoder.predict()` while excluding BM25, Qdrant search, RRF merge, filtering, and sorting produced negligible improvement (`3.20x` -> `3.18x` overhead for 3 concurrent sub-queries versus a single query). This confirms the overhead is structural, bound by serialized CPU model inference, not by lock scope. BM25 and Qdrant search were not the bottleneck. Further lock tuning is not expected to help; the only real levers are multiple model instances with RAM/VRAM cost, or GPU inference after migrating to the Legion RTX 5060, where per-call inference time should drop substantially even if the relative serialization ratio persists. Safety was confirmed via stress test: 3 concurrent `/query/decomposed` requests, representing 9 potential concurrent cross-encoder calls, completed with 0 exceptions and no recurrence of the Muc 1 rotary-embedding-cache race condition. Full validation after C1/C3 concurrency hardening: `61 passed, 9 warnings`, real HTTP session-isolation/rapid-fire test passed, and decomposed stress test passed.
- Adaptive top-k cutoff experiment (gap-based): tested 4 thresholds (`0.5`, `1.0`, `1.5`, `2.0`) offline via deterministic `recall_proxy` across all 16 measurable priority-1 cases. `gap=1.0` improves fact_lookup chunk efficiency (`avg_chunks 3.25 -> 2.00`, `useful_chunk_ratio 0.5625 -> 0.6875`) with no recall loss for fact_lookup or multi_hop, but breaks comparative recall (`1.0 -> 0.5`). Root cause: comparative queries are already routed through per-company sub-queries with small `top_k` via `QueryDecomposer`, so applying the same score-gap cutoff on top of an already-thin result set risks dropping one company's evidence entirely. Only `gap=2.0` preserves recall globally, but it yields negligible chunk reduction (`3.50 -> 3.19`), not worth the added complexity. Decision: not wired into production. Safe deployment would require a reliable single-fact versus decomposed-subquery detector; this is deferred as a documented, evidence-based non-implementation, not an unexplored gap.
- `candidate_pool` default reduced from `20` to `10` in `HybridRetriever`. Deterministic sweep across all 16 measurable priority-1 cases plus separate comparative-only verification confirmed identical `recall_proxy` (`0.9688` overall, `1.0000` comparative) at pool `10` versus pool `20`, while average `retrieve()` time dropped about 45% (`0.86s -> 0.44s` in local mode) because fewer cross-encoder pairs are processed. Unlike the rejected adaptive score-gap cutoff, reducing `candidate_pool` applies uniformly before decomposition and did not drop company evidence in multi-company comparisons. Full test suite after wiring the new default: `61 passed, 9 warnings`.
- Docker deployment decision: use `QDRANT_MODE=local`, bundling the Qdrant local data directory into the container or mounting it as a volume, not Qdrant Cloud as the default runtime target. Measured evidence with `candidate_pool=10`: Cloud search adds about `0.30s` per `retrieve()` call versus local (`~0.357s` cloud vs `~0.059s` local), and total retrieval is about `0.737s` cloud versus `0.444s` local. This overhead is not justified for a single-container demo/portfolio deployment where the main benefit of Cloud, avoiding local data packaging, does not offset the latency and external-service dependency. Qdrant Cloud setup from Muc 7 is retained as a documented, working alternative for multi-instance or production scenarios; local and cloud collections currently both contain `7,940` points and match in point count.
- Qdrant local mode uses a file lock and is safe for a single application process. Running multiple diagnostic processes against `data/processed/qdrant` in parallel produced `Storage folder ... is already accessed by another instance of Qdrant client`, so Docker/FastAPI should run with one worker when `QDRANT_MODE=local`. Use Qdrant server or Qdrant Cloud before enabling multi-worker API processes.
- Docker backend packaging completed with `.dockerignore`, `Dockerfile`, `docker-compose.yml`, and `.env.example`. The image uses CPU-only PyTorch for portability and pre-downloads both `nomic-ai/nomic-embed-text-v1.5` and `cross-encoder/ms-marco-MiniLM-L-6-v2` at build time. The first build attempt exposed a common ML Docker pitfall: letting pip resolve PyTorch through normal requirements pulled large CUDA 13 dependencies and timed out. The Dockerfile now installs the CPU torch wheel explicitly before `requirements.txt`, while `requirements.txt` intentionally does not pin torch so local Legion development can keep CUDA `cu128` acceleration.
- Docker smoke test passed after building `enterprise_document_qa-rag-api:latest`: image disk usage `3.32GB`, model pre-download log contained `Models pre-downloaded successfully.`, `/health` returned `pipeline_ready: true`, `/supported-tickers` returned `44` tickers, and a real Apple financial-table query returned `391,035` with `num_chunks_retrieved=2`, top score `10.0`, and total end-to-end time about `1.269s` including the Groq API call. Docker/WSL was shut down afterward with `docker compose down`, `DockerCli.exe -Shutdown`, and `wsl --shutdown` to release `VmmemWSL` memory.
- Performance optimization round after Muc 7: `candidate_pool` was reduced from `20` to `10` and wired as the default after deterministic `recall_proxy` sweep across all measurable priority-1 categories, including comparative, showed no recall loss and about 49% lower local `retrieve()` time. Cross-encoder `batch_size` was empirically tuned from the SentenceTransformers default `32` to `4` across 7 batch sizes on 10 real candidate pairs after pool reduction; `batch_size=4` was fastest (`0.308s` average vs `0.355s` at `32`), consistent with the small candidate pool benefiting from less padding/allocation overhead per batch. Two suspected issues were investigated and rejected with evidence: model re-initialization per request is not happening (`Embedder` and cross-encoder init log count each `1` across 3 sequential real HTTP requests), and cross-encoder cold-start is negligible (5 consecutive real-pair calls stayed in the `0.343s-0.353s` range with no first-call outlier), so startup warm-up was not implemented. Combined result: local `retrieve()` latency reduced about 52% (`0.86s -> 0.41s`) with zero measured recall degradation across test categories. Further major gains require infrastructure changes such as GPU inference or multiple model instances, not more CPU-side parameter tuning.
- Structured lookup expanded to `total equity` in addition to total assets, total liabilities, and total revenue. Root-cause investigation of an initial replacement-character-looking display (`�`) showed it was a console rendering artifact, not data corruption: stored data correctly contains `U+2019` right single quote from original SEC HTML entity `&#8217;`. Added `_normalize_quotes()` so Unicode and ASCII apostrophes match uniformly across canonical label comparisons, preventing future false negatives from quote-style mismatches. Tests now cover equity subcomponents such as retained earnings and additional paid-in capital as negative cases, note-prefix `Commitments and contingencies (...) - Total ... equity` labels as positive cases, and Unicode-vs-ASCII apostrophe equivalence. Net income structured lookup expansion is deferred: unlike assets/liabilities/equity, the net income figure is numerically identical whether matched from the income statement row or the cash-flow reconciliation row, so the risk is citation clarity rather than answer correctness. Deterministic `recall_proxy` sweep after this expansion at `candidate_pool=10` showed no regression: comparative, fact_lookup, multi_hop, and summary remained `1.0000`, while enumeration stayed at its known pre-existing `0.8750`.
- Final backend evaluation after all retrieval, structured lookup, concurrency, and performance optimizations completed 18/18 priority-1 cases with Groq `llama-3.3-70b-versatile` as judge and no skipped records. Results: Faithfulness `0.8889`, Answer Relevancy `0.9278`, Context Precision `0.4556`, Overall `0.7574`, Citation Correctness `1.0000`, Recall Proxy `1.0000`, Fallback Accuracy `1.0000`. This supersedes the earlier `0.6898` overall / `0.4250` context-precision table because it includes the MSFT total-assets YoY structured-lookup fix, `candidate_pool=10`, and cross-encoder `batch_size=4`. Multi-hop improved most significantly: category faithfulness moved from `0.50` to `0.83`, relevancy from `0.67` to `0.93`, and precision from `0.27` to `0.43`; the MSFT YoY case now scores `1.00/1.00/0.50` with recall `1.00`, replacing the pre-structured-lookup `0.00/0.20/0.00` failure. Context Precision `0.4556` remains the primary known limitation: correct answers are reliably retrieved (`Recall Proxy=1.0000`) but accompanied by more context than strictly necessary, a structural property of cross-encoder re-ranking on financial documents rather than a recall failure.
- Broader priority <= 2 evaluation completed after moving to the Legion RTX 5060 environment. Command: `.venv\Scripts\python.exe -m scripts.run_evaluation --priority 2`. It completed 30/30 cases with no skipped records and saved results to `data/evaluation_results_v2.json`. Results: Faithfulness `0.8767`, Answer Relevancy `0.9100`, Context Precision `0.4453`, Overall `0.7440`, Citation Correctness `1.0000`, Recall Proxy `0.9583`, Fallback Accuracy `1.0000`. Category table: comparative `N=6` Faith `0.80` Relev `0.8667` Prec `0.4667` Recall `1.0000`; enumeration `N=4` Faith `0.8750` Relev `0.9000` Prec `0.5750` Recall `1.0000`; fact_lookup `N=8` Faith `0.9375` Relev `0.9375` Prec `0.3575` Recall `0.8750`; multi_hop `N=3` Faith `0.8333` Relev `0.9333` Prec `0.4333` Recall `1.0000`; out_of_corpus `N=3` Faith `1.0000` Relev `1.0000` Prec `0.0000`; summary `N=6` Faith `0.8333` Relev `0.8667` Prec `0.6833` Recall `1.0000`. This broader N=30 snapshot is better for README reporting than the N=18 priority-1-only table because category sample sizes improved for fact_lookup, summary, comparative, and out_of_corpus. The run also exposed one remaining narrow fact_lookup recall miss on `Who audited Microsoft's financial statements?`, lowering fact_lookup recall to `0.8750`. Latency from this run should not be used as a stable performance benchmark because Groq returned repeated `429 Too Many Requests` responses and SDK retry backoff inflated end-to-end timings.
- MSFT auditor miss from the earlier N=30 run was investigated and fixed after that evaluation. Direct retrieval showed the wrong report-header chunk `MSFT_000095017025100235_financial_statements_0029` ranked first with CE score `4.5658`, while the correct Deloitte signature chunk `MSFT_000095017025100235_financial_statements_0031` was BM25 rank `49`, semantic rank `24`, and CE score `-10.2210` when forced into a larger candidate pool. Root cause: the auditor signature appears at the tail of a chunk whose leading text is about uncertain tax positions, so semantic/BM25/cross-encoder ranking prefers the report header even though it lacks the firm name. Apple auditor passed because its signature chunk ranked first and contained `Ernst & Young LLP`. Added an auditor-signature branch to `structured_lookup()` that activates only for auditor/report-signed financial-statement questions and promotes `financial_statements` chunks containing `/s/` plus `served as ... auditor since`. Targeted verification answers `Deloitte & Touche LLP` and promotes `MSFT_000095017025100235_financial_statements_0031` to rank 1 with score `10.0000`; full test suite after the fix was `67 passed, 9 warnings`. The July 26 N=30 rerun supersedes the pre-fix table and confirms recall proxy `1.0000`, while retaining the separate judge/context-window outlier documented below.
- The extended-corpus `priority=3` slice now contains 12 cases. Six recovery-specific cases cover Morgan Stanley, McDonald's, Intel, Costco, GE Aerospace, and Honeywell alongside the existing Visa, Mastercard, Eli Lilly, RTX, Coca-Cola, and Visa-vs-Mastercard cases. This keeps the official priority `<=2` N=30 benchmark stable. Deterministic retrieval verification after the 9,703-point rebuild passed all keyword-bearing cases with average keyword recall `1.0000`.
- Priority-3 judge validation was run with the existing 30-case checkpoint, so only the 6 new cases consumed generation/judge quota. New-case results: Visa total assets `1.00/0.80/0.50`, Mastercard total assets `1.00/0.80/0.50`, Eli Lilly total assets `1.00/1.00/0.50`, RTX total net sales trend `1.00/0.80/0.50`, Visa-vs-Mastercard risk factors `0.80/0.90/0.70`, and Coca-Cola competition risk factors `0.50/0.60/0.20`. The financial/table-backed cases and V-vs-MA comparative case validate the expanded-corpus path; the KO risk-factor case is an isolated outlier where the answer was conservative but the judge found the retrieved context only indirectly competitive and low precision. Do not publish the checkpoint-merged N=36 aggregate as the official benchmark: it reused stale N=30 records, including the pre-whitespace-normalization MSFT auditor `recall_proxy=0.00`, so N=30 remains the official clean score table.
- Fixed an expanded-corpus decomposition blocker: `QueryDecomposer` previously validated LLM-planned sub-query tickers against the original hardcoded `AAPL/MSFT/AMZN` set, so expanded-corpus comparative plans such as `V` vs `MA` could be dropped and silently fall back to raw retrieval. `SUPPORTED_TICKERS` now comes from `configs.tickers.TICKERS`, and tests cover `V`/`MA` as valid while preserving rejection of true out-of-corpus tickers such as `DIS` and `NFLX`.
- Legion RTX 5060 environment is now configured for CUDA PyTorch. The previous `.venv` had CPU-only PyTorch (`torch 2.12.1+cpu`, `cuda available False`) despite `nvidia-smi` detecting the GPU. Reinstalled with `pip uninstall torch -y` followed by `pip install torch --index-url https://download.pytorch.org/whl/cu128`, yielding `torch 2.11.0+cu128`, CUDA `12.8`, and `NVIDIA GeForce RTX 5060 Laptop GPU`. Embedder now uses `cuda:0`. Measured embedding throughput on 100 real chunks improved from `37.65s` (`2.7 chunks/s`) on Legion CPU to `4.28s` (`23.3 chunks/s`) on GPU, implying roughly `12.8` minutes for an estimated `17,930` chunks / 100-company corpus embedding pass, excluding download/extraction time.
- README and `requirements.txt` are now aligned with the deployment state: README documents the 50-company corpus, Docker flow, local Qdrant volume mount, and CPU-only container decision; `requirements.txt` explicitly pins `httpx==0.28.1` for the Docker healthcheck and documents that PyTorch must be installed separately for Docker CPU versus local CUDA workflows.
- Frontend integration completed with the actual generated stack, Vite/React/TypeScript using Bun, not Next.js. Configuration is standardized on browser-public `VITE_API_BASE_URL`; stale provider metadata/dependencies, `NEXT_PUBLIC_*` compatibility, and the unsupported `GOOG` sample were removed. Real Chrome E2E verification against `https://blog-making-bloated.ngrok-free.dev` passed all four flows: pipeline badge ready, 44 searchable tickers loaded, a normal Apple query streamed multiple UI text updates with real source citations, and an Apple-vs-Microsoft risk-factor query returned `was_decomposed=true` with AAPL and MSFT sub-queries. The UI trace rendered sub-query 1 then sub-query 2 about `200ms` apart, matching the intended stagger. Final browser run had no console errors or failed resources after adding the missing favicon. Frontend TypeScript lint and production build pass; Vite reports only the accepted bundle-size warning at about `509KB` minified.
- Pre-deploy frontend hardening completed: connection and pipeline state now start as unknown and render neutral connecting UI until the first real health response; active query requests use `AbortController` and reject stale state updates when superseded, reset, or unmounted; ngrok headers and API debug logs are conditional; icon-only controls have accessible labels; and the root layout uses the dynamic viewport height. The decomposed-query panel is now labeled as an execution summary because `/query/decomposed` returns a complete response before the client-side staggered reveal. A true `/query/decomposed/stream` SSE endpoint is explicitly deferred rather than implying that the current replay animation is live server execution.
- Fixed an API event-loop blocking bug in `/query/decomposed`: `QueryDecomposer.run()` now executes through FastAPI's `run_in_threadpool` while preserving question, ticker, section, top-k, and session filters. A real ASGI concurrency regression test holds the mock decomposer in blocking work and verifies `/health` still responds before release. Final Docker verification: targeted concurrency test passed, `tests/test_api.py` passed `10/10`, and the full suite passed `73` tests with `9` existing warnings. The local Windows venv could not collect API tests because Windows Application Control blocked SciPy's `_group_columns` DLL, so verification ran in the existing Linux Docker image with source, tests, and data mounted read-only; no security policy was bypassed.
- Pre-public API hardening completed: wildcard CORS was replaced with the environment-driven `ALLOWED_ORIGINS` allowlist, methods are limited to `GET/POST/DELETE`, and request headers are limited to `Content-Type` plus the ngrok warning bypass header. Defaults allow only local Vite development on ports `3000` and `5173`; the final Vercel domain must be added through env before deployment. `/query`, `/query/decomposed`, and both SSE exception paths now log full server-side errors but return one generic public message, preventing exception strings from leaking credentials, paths, or provider details. Regression tests cover origin/method/header preflight rejection and secret-bearing exceptions across normal, decomposed, and streaming queries. Docker verification passed `17/17` API tests and the full suite passed `80` tests with `9` existing warnings.
- Streaming cancellation now propagates from `/query/stream` through `RAGPipeline.query_stream()` into the Groq token loop. Client disconnect and a 60-second hard timeout set a shared thread-safe event; the pipeline checks it between rewrite, embedding, retrieval, cache replay, generation, and persistence stages, does not store partial answers, and closes provider stream objects in `finally`. Retrieval or embedding already executing inside one synchronous call cannot be preempted mid-function, but processing stops at the next checkpoint. Closing the provider HTTP stream is best effort and does not guarantee that the provider stops billing immediately. The API also sanitizes pipeline-generated `error` events before sending SSE data. Deterministic tests cover disconnect, timeout, producer shutdown, partial-cache prevention, and Groq connection closure. Docker verification passed `20/20` API tests, `7/7` targeted streaming tests, and the full suite passed `86` tests with `9` existing warnings.
- Completed a full async-endpoint blocking audit. `/cache/test` was the only remaining runtime endpoint performing heavy synchronous ML work on the event loop; `/supported-tickers` also performed bounded synchronous filesystem glob/stat work. Both now use `run_in_threadpool`. Cache testing embeds both queries sequentially inside one worker because `HybridRetriever._model_lock` would serialize two parallel workers anyway. ASGI regression tests hold each worker operation in a blocked state, verify `/health` responds before release, and assert the ticker scan runs off the main thread while both embeddings use the same worker thread. All other runtime endpoints are either already offloaded/producer-threaded or perform only short bounded in-memory work. Docker verification passed `22/22` API tests and the full suite passed `88` tests with `9` existing warnings.
- The July 26 clean priority `<=2` rerun exposed and fixed checkpoint contamination in `scripts/run_evaluation.py`: a filtered N=30 invocation previously aggregated every successful record in a shared N=36 checkpoint. Checkpoint loading now restricts records to the selected questions, `--fresh` explicitly deletes the active checkpoint before a run, and any skipped case makes the command exit nonzero. After Groq rolling TPD interrupted the first corrected attempt at `27 OK + 3 SKIPPED_QUOTA`, the same clean checkpoint was resumed and completed all three out-of-corpus cases. Final output reports `num_test_cases=30` and `num_skipped=0`: Faithfulness `0.8533`, Answer Relevancy `0.9300`, Context Precision `0.4670`, Overall `0.7501`, Citation Correctness `1.0000`, Recall Proxy `1.0000`, and Fallback Accuracy `1.0000`. Category counts are fact lookup `8`, summary `6`, enumeration `4`, comparative `6`, multi-hop `3`, and out-of-corpus `3`. The Microsoft auditor case now answers `Deloitte & Touche LLP` with citation correctness and recall proxy `1.00`, confirming the retrieval fix, but the judge assigned faithfulness/context precision `0.00` while claiming that evidence was absent; the official aggregate preserves this measured outlier without manual adjustment. Latency `12.9332s` is not a stable performance benchmark because the resumed checkpoint includes records affected by Groq retry backoff. The checkpoint-filter regression test and full suite pass with `89 passed, 9 warnings`.
- Added a 60-second hard response timeout to `/query` and `/query/decomposed`. The implementation uses AnyIO's worker thread with `abandon_on_cancel=True`; this is required because Starlette's default `run_in_threadpool()` shields cancellation until synchronous work finishes and would make a surrounding `wait_for()` ineffective as a hard deadline. Both endpoints now return HTTP `504` with a stable public timeout message, while unexpected exceptions remain sanitized as `500`. Python cannot safely terminate a synchronous thread already executing, so a timed-out worker may finish in the background and its result is discarded; the request and event loop are released at the deadline. Deterministic tests block each worker for two seconds, set a 50ms timeout, and verify both responses return `504` in under 750ms. API tests pass `24/24`; the full suite passes `91 tests` with `9` existing warnings.
- Frontend request cancellation is complete for initialization and active streaming. The initial health, supported-ticker, and session-history requests share one `AbortController`; unmount aborts all pending work, only `AbortError` is ignored, and real network/parse failures still update connection state. Active SSE responses expose an accessible Stop button that aborts the fetch, marks the streaming message complete, preserves partial text, uses `Generation stopped.` only when no token arrived, and re-enables the input immediately. Added the first frontend Vitest/Testing Library suite with regression coverage for unmount cancellation, shared initialization signals, partial-answer preservation on Stop, and full historical-answer rendering. Frontend type-check, 4 tests, and production build pass; the existing approximately 513 kB bundle-size warning remains.
- Session-history truncation was isolated to the API presentation layer and removed. `ConversationSession.to_llm_messages()` already passes complete user and assistant messages to the rewrite LLM, while `GET /session/{session_id}/history` alone sliced assistant answers to 200 characters. The endpoint now returns each stored answer verbatim; payload remains bounded by `MAX_HISTORY_TURNS=5`. Backend regression coverage uses a 500-character answer, and frontend coverage confirms a long historical answer renders after initialization without client-side truncation.
- Final pre-deploy backend protection is complete. SlowAPI `0.1.9` enforces shared per-IP budgets of `10/minute` and `100/day` across `/query`, `/query/stream`, and `/query/decomposed`; decomposed queries additionally allow only `5/minute`, and `/cache/test` allows `10/minute`. Limits use in-memory storage, which is correct for the mandatory single-worker local-Qdrant runtime; multi-instance serving will require shared storage such as Redis. `get_remote_address` uses the ASGI client address, so the selected hosting provider must be configured with Uvicorn proxy headers and a narrow trusted-proxy allowlist before public traffic. `/cache/clear` is disabled by default and returns `403` unless `ENABLE_CACHE_CLEAR=true`. Health semantics are separated into `/health/live` for process liveness, `/health/ready` for pipeline readiness with `503` when unavailable, and backward-compatible `/health` for the current frontend. Docker Compose now checks `/health/ready`. Regression tests cover shared cross-route limits, the lower decomposed threshold, client-IP isolation, cache-test limiting, cache-clear protection, and all three health contracts. Final validation: backend `100 passed, 9 warnings`; frontend type-check and `4` tests pass; frontend production build passes with the existing approximately `513 kB` warning. The rebuilt Docker image includes SlowAPI `0.1.9`; container health reached `healthy`, live and ready checks passed with `pipeline_ready=true`, and cache clear returned `403`. The container, Docker Desktop, and WSL were shut down afterward. Backend pre-deploy reliability work is now closed; the next milestone is selecting and configuring the hosting platform.
- Added `ARCHITECTURE.md` as the stable system-design reference with GitHub-rendered Mermaid diagrams for system context, ingestion, standard query, and decomposition flows. It documents frontend/backend deployment separation, Qdrant mode boundaries, retrieval and generation responsibilities, state persistence, cancellation, rate limiting, health semantics, evaluation safeguards, intentional constraints, and supported extension paths. Mutable corpus counts, benchmark scores, operational findings, and rejected experiments remain in README or this journal instead of being duplicated into the architecture contract. README now includes an explicit documentation map for future contributors.
- LLM integration is now Groq-only. Serving, streaming, query rewriting, decomposition, synthesis, and evaluation all use Groq chat completions; alternate-provider runtime branches, settings, environment variables, dependencies, tests, and current documentation were removed. Validation passes with `99` backend tests and `9` existing warnings, frontend type-check, `4` frontend tests, and the production build. The rebuilt Docker image reached `healthy`; `/health/live`, `/health/ready`, and `/supported-tickers` returned `200`, cache clearing remained disabled with `403`, and a real Apple financial-table query returned `391,035` using `llama-3.3-70b-versatile`.
- Zero-cost demo deployment is complete. `scripts/start_demo.ps1` starts Docker Desktop when needed, launches the Compose backend, waits for readiness, starts only its tracked ngrok process on the reserved URL, and verifies public readiness; `scripts/stop_demo.ps1` safely stops that tunnel, Compose, and optionally Docker Desktop. Vercel production embeds the ngrok backend URL and the backend CORS response allows only the exact Vercel origin. The frontend UX now keeps the composer out of the evidence scroll area, shows full legal company names alongside tickers, uses professional section names without SEC item prefixes, explains section filters and runtime metrics, preserves a useful evidence summary while collapsed, labels cross-encoder values as non-probabilistic rank scores, and adds first-visit project guidance. Hover explanations that were clipped by scroll containers were replaced with visible inline guidance for connection status, rank scores, and memory metrics; remaining help tooltips use a viewport-aware body portal and cannot be clipped by sidebar overflow. The public header no longer displays the backend URL and now switches between Overview and Conversation without deleting history. The desktop search sidebar is resizable from `280` to `480` pixels by pointer or keyboard, with the saved width restored locally. Conversation turns use a compact right-aligned question bubble and a bounded left-aligned research-response card, with interpreted-query metadata separated from answer content while decomposition and evidence remain inside the response card. Chrome device emulation confirms `390px` viewport width with no document overflow. Final validation passes `101` backend tests with `9` existing warnings, `13` frontend tests, TypeScript checking, and the production build; the accepted bundle warning is approximately `524 kB` minified.
- Stateless Qdrant Cloud startup now scrolls payloads without vectors to rebuild BM25 and structured lookup when git-ignored local artifacts are unavailable. Live validation loaded exactly `7,940` chunks across `44` tickers with no missing text. A cloud-mode Docker smoke test used no corpus volume, reached readiness in `36.5s`, returned the correct `44` searchable tickers, kept cache clearing disabled, and answered the Apple `391,035` query through Groq. A Railway Trial deployment then confirmed that the current image cannot run within a `1 GB` RAM cap: the process was repeatedly OOM-killed while loading the embedding model. A local Docker run constrained to `2 GB` succeeded and stabilized around `1.30 GiB`. Rather than add paid hosting for a portfolio demo, the Railway project and its secrets were deleted and the active deployment plan changed to Vercel plus the reserved ngrok URL and an owner-operated local Docker backend.
- A quota-free Tesla retrieval diagnostic compared English and Vietnamese queries with and without `ticker=TSLA`, plus canonical English controls. The correct evidence exists in `TSLA_000162828026003952_financial_table_0002` as `Revenues - Total revenues | 94,827 | 97,690 | 96,773`, but no tested query retrieved it. Unfiltered English returned one TSLA chunk plus QCOM and BRK-B contamination; applying the ticker removed cross-company results but still ranked unrelated related-party revenue first. Vietnamese returned only negative cross-encoder scores (`-6.1564` best with the ticker versus `3.2882` for English) and litigation/other unrelated TSLA chunks, confirming a cross-language retrieval gap. The canonical English `total revenue` query also failed with the ticker because structured lookup requires exact canonical row matching and does not match Tesla's prefixed, plural `Revenues - Total revenues` label. The observed failure therefore combines ticker scoping, cross-language retrieval weakness, and an existing structured-lookup coverage gap; entity detection or translation alone is not a complete fix. These findings are backlog evidence and do not block the separate always-on deployment milestone.
- The Tesla structured-lookup gap is fixed with exact canonical variants for `total revenues` and `Revenues - Total revenues`; the matcher itself was not broadened. Test-first baseline verification showed the new positive regression failing while unrelated revenue-row controls passed. After the fix, both targeted tests passed, `tests/test_structured_lookup.py` passed `14/14`, and the full backend suite passed `103` tests with `9` existing warnings. A real `RAGPipeline.query()` call for `What was Tesla's total revenue in 2024?` with `ticker=TSLA` promoted `TSLA_000162828026003952_financial_table_0002` to rank 1 with score `10.0000`; Groq `llama-3.3-70b-versatile` answered that Tesla's 2024 total revenue was `$97,690`. This closes only the English ticker-scoped structured-label bug; unfiltered entity scoping and Vietnamese retrieval remain separate evidence-backed backlog items.
- Oracle ARM64 gate 1 passed with `docker buildx build --platform linux/arm64 --target builder --progress=plain .`. Docker BuildKit advertised `linux/arm64`, installed the Debian ARM64 GCC/G++ toolchain, downloaded the CPython 3.12 AArch64 CPU wheel for `torch 2.13.0+cpu`, and installed the complete requirements set including native ARM64 wheels for `lxml`, `tiktoken`, NumPy, SciPy, scikit-learn, gRPC, pydantic-core, and tokenizers. Buildx history reports `8m22s` for the uncached emulated builder build. This is stronger than a compiler-only check because the current builder stage installs all Python dependencies, but it does not execute the runtime-stage model downloads.
- Oracle ARM64 gate 2 passed for architecture and memory feasibility. The full tagged `linux/arm64` image built in `2m50s` with the builder cache reused; the runtime model-load layer took `133.7s` and printed `Models pre-downloaded successfully.`. A separate offline container test performed actual inference, not only initialization: `platform.machine()` returned `aarch64`, Nomic produced a finite `(1, 768)` embedding, and the cross-encoder returned `10.3427`. The API loaded all `7,940` local chunks and reached readiness after `118.5s` internally (`154s` observed polling). Idle usage was about `1.715 GiB`; cgroup peak after the real Tesla query was `1,955,897,344` bytes (`1.821 GiB`), with `oom=0` and `oom_kill=0`. The uncached HTTP request returned the designed `504` after `60.179s` because QEMU cross-encoder inference took about `130.5s`; its abandoned worker still completed retrieval, promoted `TSLA_000162828026003952_financial_table_0002` at score `10.0000`, received Groq `200`, and cached the correct `97,690` answer. Repeating the request returned that cached answer in `3.312s`. This timeout under x86-to-ARM emulation is not a native Oracle A1 latency measurement. The technical evidence supports testing Oracle A1 at the proposed `2 OCPU / 8 GB`; Oracle account region capacity remains the open infrastructure gate.
- Oracle Gate 3 is intentionally deferred to a separate deployment session. The Singapore home-region Console exposes `VM.Standard.A1.Flex` as Always Free-eligible and accepts the target `2 OCPU / 8 GB` configuration, but no instance was created, so this does not yet prove current host capacity. The next session starts with provisioning, then VCN/public-subnet and SSH hardening, Docker deployment with persistent data and HTTPS, native Tesla/latency/memory validation, and only then the Vercel API URL cutover. Fly.io remains a paid fallback requiring explicit approval. The local `enterprise-document-qa:arm64-test` image and dangling ARM builder image were deleted after validation because Compose does not use them; the existing `enterprise_document_qa-rag-api:latest` image was preserved. Docker Desktop and WSL were shut down afterward.
- The decomposed-answer synthesis exception leak is confirmed and fixed test-first. The new regression forced the direct Groq synthesis call to raise a non-retryable exception containing a fake API key and internal path; before the fix, `_synthesize()` failed exactly as predicted because its public return value included both secrets. Non-retryable synthesis failures now log the full stack trace server-side and return one stable generic answer, while rate-limit, quota, `503`, and unavailable errors retain the existing re-raise behavior for upstream retry/API handling. The targeted regression passes, all `11` query-decomposer tests pass, and the full backend suite passes `104` tests with `9` existing warnings.
- The comparative evidence-coverage finding is confirmed and fixed test-first. The baseline regression planned AAPL and MSFT branches but returned two unique AAPL chunks; the old total-count guard passed and called synthesis once with one-sided evidence. Multi-company plans with at least two distinct non-null expected tickers now fall back unless the retrieved evidence collectively covers every expected ticker. This intentionally does not require every topical branch in a single-company enumeration to return evidence. The inverse regression confirms valid AAPL and MSFT evidence still reaches synthesis. Both targeted tests pass, all `13` query-decomposer tests pass, and the full backend suite passes `106` tests with `9` existing warnings.
- The structured-lookup section-filter violation is confirmed and fixed at the integration boundary. Deterministic integration regressions exercised the real structured lookup, section filtering, reranking, and promotion path: before the fix, a total-assets query explicitly filtered to `financial_statements` still injected a `financial_table` match, while an auditor query filtered to `financial_table` injected a `financial_statements` signature. `HybridRetriever` now discards a structured match immediately before promotion when its section conflicts with a non-null requested section; `structured_lookup()` remains section-agnostic. The inverse regression confirms `section=None` still promotes the correct total-assets table at score `10.0`. The three new integration tests pass, existing structured/concurrency retrieval tests pass `16/16`, and the full backend suite passes `109` tests with `9` existing warnings. This closes the final Phase 1 correctness finding from the audit.
- Phase 2 evaluation-integrity hardening started with judge-response validation. The official `data/evaluation_results_v2.json` N=30 artifact was checked before implementation: all `30` records are `OK`, no record has three zero scores, and no reason contains `parse error`, so the published `0.8533` Faithfulness result is not affected by the old silent-zero path and does not require a rerun for this fix. The baseline regression then confirmed malformed judge text returned a fabricated `EvalResult` with three zero scores, while network retry and valid JSON-to-`OK` behavior remained correct. Judge output now requires an exact six-field JSON object, finite numeric scores within `[0,1]`, and string reasons; malformed JSON and invalid schemas raise `JudgeParseError`. The evaluation runner does not retry this response-quality failure, checkpoints it as `JUDGE_PARSE_INVALID`, excludes it from aggregates, and still retries other provider/network exceptions under the existing cap before using `JUDGE_SKIPPED_QUOTA`. Evaluation-targeted tests pass `18/18`; the full backend suite passes `121` tests with `9` existing warnings.
- Evaluation checkpoint identity is now fingerprinted instead of reusing successful records by question text alone. The truthful baseline was `1 pass / 3 fail`: same-question/same-fingerprint reuse passed incidentally under the old question-only loader, while changed ground truth, changed judge model, and missing legacy fingerprint were all incorrectly reused. Each selected case now receives a deterministic SHA-256 fingerprint over fingerprint schema version `1`, explicit generator and judge model constants, and every semantic `TestCase` field. Success and skipped checkpoint records store that fingerprint, final output reports the fingerprint schema version, and checkpoint loading accepts only exact question-plus-fingerprint matches; legacy records are intentionally incompatible. Explicit model constants are available before checkpoint loading, avoiding ML initialization reordering and hidden default drift. Checkpoint-targeted tests pass `8/8`; the full backend suite passes `125` tests with `9` existing warnings. Existing official N=30 output remains unchanged and does not require a rerun until a new evaluation is intentionally started.
- Separate path-filtered GitHub Actions workflows now protect backend and frontend changes. The backend job uses Python 3.12, CPU-only PyTorch, Hugging Face offline flags, the full quota-free test suite, and compile checks; the frontend job uses pinned Bun `1.3.14`, frozen lockfile installation, TypeScript checking, Vitest, and the Vite production build. A duration audit confirmed all `125` backend tests are isolated from real model/network calls: the slowest test took `0.83s`. Local frontend validation passed type-check, `13/13` Vitest tests, and the production build with the existing approximately `524 kB` bundle warning. The audit also caught that `bun test` invokes Bun's native runner and fails the Vitest/jsdom suite; CI correctly uses `bun run test`. First remote runs passed on commit `935b6f1`: Backend CI run `31019758730` and Frontend CI run `31019758380`. README includes live status badges and reproducible local commands.

Latest pushed milestone commit before this state refresh:

```text
853f9a3 Record Groq-only validation milestone
```

Recent completed commits:

```text
40175e5 Add multi-turn conversation memory
aad9a79 Document semantic cache completion
a697787 Add semantic query cache
db20e51 Update project state for BM25 optimization
29c3af3 Optimize BM25 chunk lookup
1df86d4 Update project state for streaming
b8e8fdb Add streaming query endpoint
8f440b7 Tidy SEC client comments
8b63374 Update README for hybrid retrieval
383272b Add hybrid retrieval reranking
79c7228 Document Step 10 completion
```

## Project Goal

Build an Enterprise Document QA system over SEC 10-K filings using a RAG pipeline:

```text
SEC Filing -> Section Extraction -> Chunking -> Embedding -> Query Rewrite -> Qdrant/BM25 -> Hybrid Retrieval -> Re-ranking -> Semantic Cache/Memory -> LLM Answer -> FastAPI/SSE
```

The configured corpus currently targets 50 latest 10-K filings:

```text
AAPL, MSFT, AMZN, GOOGL, META, NVDA, TSLA,
JPM, BAC, GS, MS, BRK-B,
JNJ, UNH, PFE,
WMT, HD, MCD,
XOM, CVX,
AMD, INTC, QCOM, AVGO, TXN,
CRM, ORCL, NOW, IBM,
V, MA, AXP,
LLY, MRK, ABBV, TMO,
PG, KO, PEP, COST, NKE,
CAT, GE, BA, LMT, HON, UPS, RTX,
VZ, T
```

Of these, 44 currently have searchable embedded chunks in local Qdrant and 6 are unusable until section extraction is improved.

The system answers finance/document questions using retrieved filing context and citations, with explicit fallback when the available context is insufficient.

## Current Architecture

- `src/ingestion/sec_client.py`
  SEC EDGAR client for ticker-to-CIK lookup, filing metadata retrieval, rate-limited filing downloads, and SEC-specific exceptions.
- `src/ingestion/section_extractor.py`
  HTML-to-text conversion, text cleanup, and robust extraction of target 10-K sections.
- `src/ingestion/chunker.py`
  Recursive token-aware chunker for extracted sections.
- `src/retrieval/embedder.py`
  Nomic embedding wrapper using required document/query prefixes.
- `src/retrieval/vector_store.py`
  Qdrant wrapper for local persistent vector storage, upsert, metadata filters, and semantic search.
- `src/retrieval/retriever.py`
  Retrieval abstraction combining Embedder + VectorStore and returning clean `RetrievedChunk` objects.
- `src/retrieval/hybrid_retriever.py`
  Hybrid retriever combining BM25 keyword search, Qdrant semantic search, Reciprocal Rank Fusion, and cross-encoder re-ranking. Supports pre-computed query embeddings for cache-aware retrieval.
- `src/retrieval/semantic_cache.py`
  In-memory filter-aware semantic cache for full RAG responses and sources.
- `src/memory/conversation_memory.py`
  In-memory conversation session store with TTL cleanup and a small interface intended for future SQLite/Redis replacement.
- `src/memory/query_rewriter.py`
  LLM-powered follow-up query rewriter that converts pronoun-based questions into standalone retrieval queries.
- `src/generation/generator.py`
  LLM wrapper for non-streaming and streaming RAG answer generation with strict anti-hallucination prompt and optional conversation history. Current default provider is Groq.
- `src/generation/rag_pipeline.py`
  End-to-end RAG pipeline combining Retriever + Generator, including semantic cache checks, conversation memory, query rewriting, and `query_stream()` for SSE events.
- `src/evaluation/evaluator.py`
  LLM-as-judge evaluation for faithfulness, answer relevancy, and context precision, plus deterministic citation/fallback/recall-proxy checks.
- `src/evaluation/test_set.py`
  Fixed 30-case priority `<=2` categorized evaluation set plus 6 priority-3 extended-corpus cases covering fact lookup, summary, comparative, multi-hop, and out-of-corpus fallback questions.
- `src/api/app.py`
  FastAPI service exposing `/health`, `/query`, `/query/stream`, `/supported-tickers`, cache endpoints, session endpoints, and Swagger UI at `/docs`.
- `scripts/download_filings.py`
  Idempotent batch download and section extraction script for configured tickers.
- `scripts/chunk_filings.py`
  Chunk generation script.
- `scripts/embed_chunks.py`
  Resumable embedding generation script.
- `scripts/index_chunks.py`
  Qdrant indexing script that recreates the collection from embedded files.
- `configs/tickers.py`
  Corpus ticker list and ticker-to-CIK overrides for SEC ticker-map edge cases.
- `scripts/diagnostics/rag_smoke_test.py`
  Manual end-to-end RAG test script.
- `configs/settings.py`
  `.env`-backed settings and data paths.

## Implemented So Far

### Step 3: Section Extraction

Robust SEC 10-K extraction is complete and committed as:

```text
6b2f599 Robust SEC filing section extraction
```

Extracted sections:

- `business`
- `risk_factors`
- `mdna`
- `financial_statements`

Extractor behavior:

- Converts SEC HTML to text with BeautifulSoup/lxml.
- Removes `script` and `style` tags.
- Normalizes text and repairs known split headings, including `RIS\nK FACTORS`, `B\nUSINESS`, `FINANCIAL STATE\nMENTS`, and `INC\nOME`.
- Uses section-specific start/end boundaries.
- Rejects table-of-contents false matches via minimum section length.
- Skips self-reference matches such as `Risk Factors of this Annual Report`.
- Handles MD&A boundary before MSFT management responsibility/report sections.
- Strips trailing page/header noise only at section ends.

Validation:

- AAPL/MSFT/AMZN: all 12 section starts and ends manually validated.
- GOOGL latest 10-K generalization check passed with no warnings.
- Extraction quality is sufficient for MVP retrieval/RAG.

Remaining extraction limitations:

- Designed specifically for 10-K filings, not 10-Q/8-K/Forms 3/4/5.
- Not yet validated across 40-80 companies.
- No automated unit tests for extraction edge cases yet.
- Financial statement tables are usable but verticalized.

### Step 4: Chunking

Chunking is complete and committed as:

```text
cabd268 Add SEC filing chunking
```

Implemented files:

- `src/ingestion/chunker.py`
- `scripts/chunk_filings.py`

Chunking design:

```python
CHUNK_CONFIG = {
    "business": {"chunk_size": 500, "overlap": 75},
    "risk_factors": {"chunk_size": 500, "overlap": 75},
    "mdna": {"chunk_size": 500, "overlap": 75},
    "financial_statements": {"chunk_size": 900, "overlap": 100},
}
SEPARATORS = ["\n\n", "\n", ". ", " "]
```

Important implementation details:

- Uses `tiktoken` `cl100k_base` for token counting.
- Uses recursive splitting: paragraph -> line -> sentence -> word/token fallback.
- Uses larger chunks for `financial_statements` to reduce label/value table breakage.
- Guarded against `overlap >= chunk_size`.
- Counts tokens on the final joined chunk text, not just a sum of unit token counts. This prevents BPE/tokenizer boundary bugs where the final chunk exceeds the configured limit.
- If overlap plus the next unit would exceed the limit, overlap is dropped for that boundary to preserve hard token limits.

Chunk output files are generated locally under `data/processed/{TICKER}/` and are ignored by git because `data/` is ignored:

- `data/processed/AAPL/000032019325000079_chunks.jsonl`
- `data/processed/AMZN/000101872426000004_chunks.jsonl`
- `data/processed/MSFT/000095017025100235_chunks.jsonl`

Chunk counts:

| Ticker | Section | Chunks |
|---|---:|---:|
| AAPL | business | 7 |
| AAPL | financial_statements | 21 |
| AAPL | mdna | 10 |
| AAPL | risk_factors | 31 |
| AMZN | business | 7 |
| AMZN | financial_statements | 38 |
| AMZN | mdna | 23 |
| AMZN | risk_factors | 27 |
| MSFT | business | 21 |
| MSFT | financial_statements | 32 |
| MSFT | mdna | 23 |
| MSFT | risk_factors | 31 |

Chunk validation:

- Total chunks: 271.
- Min tokens: 125.
- Max tokens: 900.
- Token limit violations: 0.
- MSFT `Total assets` appears in `MSFT_000095017025100235_financial_statements_0000`, token count 897.
- `Total liabilities` is in the adjacent next chunk, which is acceptable for MVP retrieval.
- Overlap was confirmed between adjacent AAPL `risk_factors` chunks.

### Step 5: Embeddings

Embedding pipeline is complete and committed as:

```text
544ddb7 Add local embedding pipeline
```

Implemented files:

- `src/retrieval/embedder.py`
- `scripts/embed_chunks.py`

Model selected:

```text
nomic-ai/nomic-embed-text-v1.5
```

Reasoning:

- `BAAI/bge-base-en-v1.5` was tested first and rejected because `max_seq_length=512`, while financial statement chunks can be ~786 tokens under the model tokenizer after prefix.
- `nomic-ai/nomic-embed-text-v1.5` supports `max_seq_length=8192`, dimension 768, and safely handles the current 900-token financial statement chunks.

Model card requirements:

- Document/chunk prefix: `search_document: `
- Query prefix: `search_query: `

These prefixes are encapsulated in `Embedder` so future modules do not forget them.

Dependencies added:

- `sentence-transformers==5.6.0`
- `einops==0.8.2`

Embedding output files are generated locally and ignored by git:

- `data/processed/AAPL/000032019325000079_chunks_embedded.jsonl`
- `data/processed/AMZN/000101872426000004_chunks_embedded.jsonl`
- `data/processed/MSFT/000095017025100235_chunks_embedded.jsonl`

Embedding validation:

- AAPL: 69 chunks embedded.
- AMZN: 95 chunks embedded.
- MSFT: 107 chunks embedded.
- Total: 271 chunks embedded.
- Embedding dimension: 768 for every record.
- Missing embeddings: 0.
- CPU runtime for full embedding run: ~416 seconds.

Semantic sanity check:

```text
MSFT financial_statements_0000 vs financial_statements_0001: 0.8230
MSFT financial_statements_0000 vs business_0000: 0.6083
```

Interpretation: adjacent financial statement chunks are semantically closer than financial statement vs business, confirming embeddings are meaningful.

### Step 6: Vector Database

Qdrant vector indexing is complete and committed as:

```text
268c36e Add Qdrant vector indexing
```

Implemented files:

- `src/retrieval/vector_store.py`
- `scripts/index_chunks.py`

Dependency added:

- `qdrant-client==1.18.0`

Vector DB design:

- Qdrant local persistent mode under `data/processed/qdrant`.
- Collection name: `sec_filings`.
- Vector dimension: 768.
- Distance metric: Cosine.
- Payload includes `chunk_id`, `ticker`, `section`, `accession_number`, `filing_date`, `report_date`, `chunk_index`, `token_count`, and `text`.

Important implementation details:

- Uses deterministic UUIDs via `uuid.uuid5(uuid.NAMESPACE_URL, chunk_id)` instead of Python `hash()`, because `hash()` is randomized between Python processes.
- Batch upsert size is 100 to avoid local Qdrant request-size issues.
- Uses Qdrant `query_points` API because `client.search` is not available in `qdrant-client==1.18.0`.
- Adds `VectorStore.close()` and context manager support to avoid local client shutdown warnings/resource leaks.

Index validation:

```text
Collection info: {'vectors_count': 271, 'indexed_vectors_count': 0, 'points_count': 271, 'status': 'green'}
```

Note: `indexed_vectors_count=0` is normal for small local Qdrant collections below the HNSW indexing threshold. `points_count=271` is the important count.

Filtered search test:

Query:

```text
What are the main risk factors for Apple?
```

Filter:

```text
ticker=AAPL, section=risk_factors, top_k=3
```

Results had scores >0.73 and returned relevant AAPL risk factor chunks.

### Step 7: Retrieval Pipeline

Retrieval wrapper is complete and committed as:

```text
cb48532 Add retrieval pipeline wrapper
```

Implemented file:

- `src/retrieval/retriever.py`

Design:

- `Retriever` combines `Embedder.embed_query()` and `VectorStore.search()`.
- Uses dependency injection for `Embedder` and `VectorStore` to avoid repeated model loads and make testing easier.
- Returns `RetrievedChunk` dataclass with `chunk_id`, `ticker`, `section`, `filing_date`, `score`, `text`, and formatted `citation`.

Retrieval quality tests:

- Apple revenue with filters returned AAPL financial statement chunks; exact revenue chunk was present but not always rank 1.
- Microsoft revenue-source query returned relevant business chunks.
- Broad risk factor query returned risk factor sections across AAPL, AMZN, and MSFT.
- Amazon revenue/profit trend returned relevant MD&A results.
- Microsoft cloud dependency returned risk, MD&A, and cloud margin context.
- No-filter Apple revenue query returned 5/5 AAPL chunks, proving company discrimination works without hard ticker filtering.

Known retrieval limitation:

- Financial table retrieval can return related accounting/financial chunks above the exact numeric table chunk. This is expected with semantic retrieval over verticalized tables and should be documented in README/evaluation.

### Step 8: RAG Generation

RAG generation pipeline is complete and committed as:

```text
d2dc7f2 Add RAG generation pipeline
```

Implemented files:

- `src/generation/generator.py`
- `src/generation/rag_pipeline.py`
- `scripts/diagnostics/rag_smoke_test.py`

Current generation dependency:

- `groq==1.5.0`

Current provider setup:

- Groq is the only LLM provider.
- The serving and evaluation model is `llama-3.3-70b-versatile`.
- `GROQ_API_KEY` and optional `GROQ_API_KEY_FALL_BACK` are read from `.env` via `configs/settings.py`.

Provider status observed:

- Groq works with the current key and serves `llama-3.3-70b-versatile`.

System prompt rules:

- Use only provided SEC filing context.
- Cite every factual claim as `[Source N]`.
- If context is insufficient, fallback exactly rather than guessing.
- Do not speculate or infer beyond context.
- Quote numbers exactly as they appear.
- Always respond in English.

End-to-end Groq RAG test results:

Apple revenue question:

```text
Q: What was Apple's total revenue in fiscal year 2024?
A: According to [Source 1] and [Source 2], Apple's total net sales for 2024 were $391,035.
```

Hallucination check:

- `$391,035` was found in Source 1: `AAPL_000032019325000079_financial_statements_0018`.
- `$391,035` was found in Source 2: `AAPL_000032019325000079_financial_statements_0005`.
- `391,035` was also found in Source 4: `AAPL_000032019325000079_financial_statements_0000`.
- Conclusion: no hallucination for Apple revenue.

Microsoft risk factors question:

- Answer synthesized multiple risk factor chunks with citations.
- Content included competition, privacy/data/AI scrutiny, cybersecurity, economic/geopolitical risks, pandemic/epidemic risk, and platform abuse.
- Result was good and source-grounded.

Amazon AWS revenue growth question:

- Model correctly used fallback because retrieved MD&A chunks did not explicitly contain AWS revenue growth.
- Important limitation: corpus likely contains AWS revenue/operating metrics elsewhere, but retrieval did not return the right numeric chunk for this query. This is a retrieval/evaluation issue, not a generation bug.

Tesla revenue fallback:

- Query: `What is Tesla's revenue in 2024?`
- No Tesla corpus exists.
- Model correctly responded that there was insufficient information and did not invent Tesla revenue.

Groq free-tier behavior:

- One `429 Too Many Requests` occurred during the Tesla fallback test.
- Groq SDK automatically retried after ~14 seconds and completed successfully.
- Document this in README as a known free-tier limitation.

### Step 9: Evaluation Framework

RAG evaluation framework is complete and committed as:

```text
a5c4d39 Add RAG evaluation framework
```

Implemented files:

- `src/evaluation/test_set.py`
- `src/evaluation/evaluator.py`
- `scripts/run_evaluation.py`

Evaluation design:

- Uses a fixed six-question test set.
- Uses Groq LLM-as-judge for faithfulness, answer relevancy, and context precision.
- Separates generation quality from retrieval quality.
- Saves local output to `data/evaluation_results.json`, ignored by git.

Latest evaluation averages:

| Metric | Score |
|---|---:|
| Faithfulness | 0.9000 |
| Answer relevancy | 0.9167 |
| Context precision | 0.3833 |
| Overall | 0.7333 |

Main evaluation insight:

- Answers are mostly faithful and relevant when the right evidence is retrieved.
- Context precision is weak because semantic retrieval often returns related but non-answer chunks, especially for broad/no-filter cloud questions and verticalized financial tables.
- Tesla/no-corpus fallback correctly returns insufficient-context behavior; context precision is expected to be 0 for that case.

### Step 10: FastAPI Service

FastAPI service is complete and committed as:

```text
ee6c3f6 Add FastAPI RAG service
```

Implemented files:

- `src/api/app.py`
- `src/api/__init__.py`

API endpoints:

- `GET /health`: service status and `pipeline_ready` flag.
- `POST /query`: RAG answer with model name, retrieved source previews, and chunk count.
- `GET /supported-tickers`: currently supported tickers and sections.
- `GET /docs`: Swagger UI.

Validation:

- `/health` returned `pipeline_ready: true`.
- `/docs` returned Swagger UI successfully.
- `/query` was tested with ticker+section filter, ticker-only filter, and no filter.

Measured endpoint latency:

| Request | Filter | Latency |
|---|---|---:|
| Apple revenue | `ticker=AAPL`, `section=financial_statements` | 1.2503s |
| Microsoft cybersecurity risks | `ticker=MSFT` | 1.2090s |
| AWS revenue growth | no filter | 5.8362s |

Latency insight:

- Query embedding plus vector search took about 0.14-0.18s.
- End-to-end latency was dominated by the Groq LLM API call.
- With Groq free tier, expected end-to-end latency is provider-dependent, often around 2-5s, and can spike when Groq returns `429 Too Many Requests` and retries.

No-filter retrieval issue observed:

- The AWS revenue-growth query returned an MSFT MD&A chunk as Source 1 with score 0.7576, above the relevant AMZN chunks.
- The LLM still answered correctly from AMZN Sources 2-4, but MSFT Sources 1 and 5 were retrieval noise.
- This directly explains the low Step 9 context precision score and motivates Step 11: Hybrid Search + Re-ranking.

### Step 11: Hybrid Search + Re-ranking

Hybrid retrieval is complete and committed as:

```text
383272b Add hybrid retrieval reranking
```

BM25 lookup optimization was committed as:

```text
29c3af3 Optimize BM25 chunk lookup
```

Implemented files:

- `src/retrieval/hybrid_retriever.py`
- `src/api/app.py`
- `scripts/run_evaluation.py`
- `requirements.txt`

Dependency added:

- `rank-bm25==0.2.2`

Retrieval design:

- BM25 keyword search retrieves lexical candidates.
- Qdrant semantic search retrieves dense-vector candidates.
- Reciprocal Rank Fusion merges BM25 and semantic ranked lists without score normalization.
- Cross-encoder `cross-encoder/ms-marco-MiniLM-L-6-v2` re-ranks the fused candidate pool.
- FastAPI and evaluation now use `HybridRetriever`.
- BM25 candidate sorting uses a precomputed `chunk_id -> index` map, avoiding `list.index()` O(n) lookup inside every query sort.

Validation:

- The no-filter AWS revenue-growth query no longer returns MSFT cloud chunks in final top-5 sources; returned sources are AMZN.
- Context precision improved from `0.3833` to `0.4750`.
- Overall evaluation improved from `0.7333` to `0.7583`.
- BM25 sort benchmark on the current 271-chunk corpus improved from `0.083071s` to `0.018681s` over 2,000 loops, a `4.45x` speedup.

Hybrid evaluation comparison:

| Metric | Step 9 Baseline | Step 11 Hybrid |
|---|---:|---:|
| Faithfulness | 0.9000 | 0.8667 |
| Answer relevancy | 0.9167 | 0.9333 |
| Context precision | 0.3833 | 0.4750 |
| Overall | 0.7333 | 0.7583 |

Remaining Step 11 limitation:

- Context precision did not reach the target `0.55+` yet.
- Broad Microsoft revenue-source queries and numeric financial-table queries still return more context than the judge considers useful.
- Cross-encoder re-ranking improves precision but adds CPU latency at query time.

### Phase 2A Step A: Streaming Response

Streaming response is complete and committed as:

```text
b8e8fdb Add streaming query endpoint
```

Implemented files:

- `src/generation/generator.py`
- `src/generation/rag_pipeline.py`
- `src/api/app.py`

Streaming design:

- `Generator.generate_stream()` streams tokens from Groq.
- Groq streaming uses `client.chat.completions.create(..., stream=True)`, which matches the installed Groq SDK.
- `RAGPipeline.query_stream()` yields event tuples: `sources`, `token`, `done`, and `error`.
- FastAPI exposes `POST /query/stream` using Server-Sent Events.
- The SSE endpoint uses an `asyncio.Queue` plus a background thread to avoid collecting all events before yielding, so token streaming is real.

Verified SSE event format:

```text
data: {"type": "sources", "data": [...]}
data: {"type": "token", "data": "Based"}
data: {"type": "token", "data": " on"}
data: {"type": "done", "data": null}
```

Streaming validation query:

```text
What are Apple main risk factors?
```

Streaming timing:

| Metric | Seconds |
|---|---:|
| First SSE event, `sources` | 2.4945 |
| First token, end-to-end TTFT | 2.9459 |
| Last token | 3.5820 |
| Total | 3.5820 |

Interpretation:

- End-to-end TTFT includes hybrid retrieval and CPU cross-encoder re-ranking before the LLM call.
- After sources were emitted, Groq produced the first streamed token in about 0.45s.
- Streaming now improves perceived responsiveness even when total generation time remains provider-dependent.

### Phase 2A Step A.1: Semantic Query Cache

Semantic query caching is complete and committed as:

```text
a697787 Add semantic query cache
```

Implemented files:

- `src/retrieval/semantic_cache.py`
- `src/retrieval/hybrid_retriever.py`
- `src/generation/rag_pipeline.py`
- `src/api/app.py`

Cache design:

- The cache stores full generated answers plus serialized retrieved sources.
- Cache lookup uses cosine similarity over query embeddings.
- Cache entries are scoped by exact request filters: `ticker`, `section`, and `top_k`.
- Default threshold is `0.95`, with `max_entries=500` and `ttl_seconds=3600`.
- `RAGPipeline` embeds the query once and reuses that embedding for cache lookup and hybrid retrieval on cache misses.
- Cached streaming responses replay `sources`, word-split `token` events, and `done` without calling the LLM.

New API endpoints:

- `GET /cache/stats`
- `POST /cache/clear`
- `POST /cache/test`

Cache validation:

| Check | Result |
|---|---:|
| Exact repeated `/query` model | `llama-3.3-70b-versatile (cached)` |
| Exact repeated `/query` latency | `0.1080s` |
| Same query with different ticker | cache miss |
| Cached `/query/stream` first event | `0.1212s` |
| Cached `/query/stream` first token | `0.1212s` |
| Cached `/query/stream` done | `0.1212s` |

Threshold tuning results:

| Query A | Query B | Similarity | Cache Hit at `0.95` |
|---|---|---:|---|
| What was Apple revenue in 2024? | Apple 2024 total net sales figure | 0.901063 | No |
| What was Apple revenue in 2024? | What was Apple net income in 2024? | 0.919944 | No |
| What was Apple revenue in 2024? | What was Apple operating cash flow in 2024? | 0.870379 | No |
| What was Apple revenue in 2024? | What are Apple's main risk factors? | 0.603403 | No |
| What was Apple revenue in 2024? | What was Microsoft revenue in 2024? | 0.867607 | No |

Interpretation:

- `0.90` would be unsafe because Apple revenue vs Apple net income scored `0.919944`.
- `0.95` is conservative and currently only intended to catch exact or near-identical repeats.
- Broader paraphrase caching should wait for a larger threshold calibration set.

### Phase 2B Step C: Multi-turn Conversation with Memory

Multi-turn conversation support is complete and committed as:

```text
40175e5 Add multi-turn conversation memory
```

Implemented files:

- `src/memory/__init__.py`
- `src/memory/conversation_memory.py`
- `src/memory/query_rewriter.py`
- `src/generation/rag_pipeline.py`
- `src/generation/generator.py`
- `src/api/app.py`

Memory design:

- Uses Option A: in-memory conversation storage for the current demo stage.
- Stores conversation history per `session_id`.
- Keeps recent turns for LLM context injection.
- Tracks `rewritten_query` per turn for debugging and validation.
- Uses TTL-based cleanup; default session TTL is 30 minutes.
- Interface is intentionally small so a future SQLite or Redis implementation can replace the in-memory backend without changing pipeline/API code.

Multi-turn RAG design:

- Stateless requests continue to work when `session_id` is omitted.
- Session requests load recent conversation history from `ConversationMemory`.
- Follow-up questions are rewritten into standalone retrieval queries before embedding and retrieval.
- Retrieval uses the rewritten query, while generation receives the original user question plus conversation history.
- Multi-turn requests bypass semantic cache because answer context depends on the active conversation.
- Stateless requests still use semantic cache as before.

New/updated API behavior:

- `POST /query` accepts optional `session_id`.
- `POST /query/stream` accepts optional `session_id`.
- `GET /session/{session_id}/history` returns recent turns and rewritten queries for debugging/UI rendering.
- `DELETE /session/{session_id}` clears one conversation session.
- `GET /health` includes memory stats.

Validation:

| Check | Result |
|---|---|
| Follow-up query | `What about their revenue?` |
| Rewritten query | `What is Apple's total revenue?` |
| Turn 2 answer | Returned Apple total net sales: `$416,161` for 2025, `$391,035` for 2024, and `$383,285` for 2023 |
| Stateless cache compatibility | Second identical stateless query returned `llama-3.3-70b-versatile (cached)` |
| Stateless cache latency | `0.1261s` |
| Session isolation | Session A had 1 turn while Session B had 0 turns |

History validation output:

```json
{
  "session_id": "test-session-rewrite-002",
  "turns": [
    {
      "user": "What are Apple's main risk factors?",
      "assistant": "Based on the provided context sections, Apple's main risk factors include...",
      "rewritten_query": null
    },
    {
      "user": "What about their revenue?",
      "assistant": "The Company's total net sales were $416,161 for 2025, $391,035 for 2024, and $383,285 for 2023...",
      "rewritten_query": "What is Apple's total revenue?"
    }
  ]
}
```

Important implementation note:

- The rewriter prompt was tightened so revenue follow-ups target total revenue or total net sales, not revenue recognition policy. This fixed an initial retrieval path that returned revenue-recognition context instead of numeric revenue context.

## Current Data Artifacts

These are generated locally and ignored by git because `data/` is ignored:

- Raw filings: `data/raw/{TICKER}/*.html`
- Extracted sections: `data/processed/{TICKER}/*_sections.json`
- Chunks: `data/processed/{TICKER}/*_chunks.jsonl`
- Embedded chunks: `data/processed/{TICKER}/*_chunks_embedded.jsonl`
- Qdrant local index: `data/processed/qdrant`
- Evaluation results: `data/evaluation_results.json`
- Expanded evaluation results: `data/evaluation_results_v2.json`

If a new session starts without these local artifacts, regenerate in order:

```text
python -m scripts.download_filings
python -m scripts.chunk_filings
python -m scripts.add_table_chunks
python -m scripts.embed_chunks
python -m scripts.index_chunks
python -m scripts.diagnostics.rag_smoke_test
python -m scripts.run_evaluation
```

## Environment Variables

Currently supported in `configs/settings.py`:

```text
GROQ_API_KEY=
GROQ_API_KEY_FALL_BACK=
QDRANT_MODE=local
QDRANT_LOCAL_PATH=data/processed/qdrant
QDRANT_CLOUD_URL=
QDRANT_CLOUD_API_KEY=
```

For the current working RAG test, `GROQ_API_KEY` is required.

## Current Dependencies

Important pinned dependencies:

```text
python-dotenv==1.0.1
pydantic-settings==2.4.0
requests==2.31.0
beautifulsoup4==4.12.3
lxml==5.3.0
tiktoken==0.13.0
sentence-transformers==5.6.0
rank-bm25==0.2.2
einops==0.8.2
qdrant-client==1.18.0
groq==1.5.0
fastapi==0.115.0
uvicorn==0.32.0
```

## Validation Summary

Validated section starts and ends for all 12 sections across AAPL, MSFT, and AMZN.

Current processed section token counts using `cl100k_base`:

| Ticker | Section | Characters | Tokens |
|---|---:|---:|---:|
| AAPL | business | 16,071 | 2,941 |
| AAPL | risk_factors | 68,050 | 11,631 |
| AAPL | mdna | 18,110 | 4,137 |
| AAPL | financial_statements | 62,127 | 15,401 |
| MSFT | business | 48,751 | 8,553 |
| MSFT | risk_factors | 69,024 | 11,933 |
| MSFT | mdna | 46,316 | 9,128 |
| MSFT | financial_statements | 103,782 | 24,506 |
| AMZN | business | 13,545 | 2,684 |
| AMZN | risk_factors | 60,765 | 10,655 |
| AMZN | mdna | 46,462 | 9,011 |
| AMZN | financial_statements | 124,074 | 28,459 |

Note: the `Characters` column is character count, not token count.

## Known Limitations

- Extraction is robust for tested 10-K filings but not broadly validated across 40-80 companies yet.
- No automated test suite for section extraction, chunking, retrieval, or RAG evaluation yet.
- Financial statements are verticalized, so exact numeric retrieval can be weaker than prose retrieval.
- Semantic search can return related financial/accounting chunks above the exact numeric table; hybrid retrieval reduces but does not eliminate this.
- Amazon AWS revenue growth query did not retrieve the exact numeric context even though relevant data may exist in the corpus.
- Cross-encoder re-ranking improves context precision but adds CPU latency before streaming can begin.
- Semantic cache is in-memory only; entries are lost on process restart and the current list scan should be replaced by an indexed/vector-backed implementation at larger scale.
- Semantic cache threshold is conservative. It catches exact or near-identical repeats, but does not yet cache broader paraphrases safely.
- Conversation memory is in-memory only; sessions are lost on process restart and are not shared across multiple API workers.
- Query rewriting adds one LLM call for follow-up questions with history, so multi-turn latency can be higher than stateless queries.
- Enumeration-type queries such as `What are the main sources of revenue for Microsoft?` underperform compared with fact-lookup queries. Current hypothesis: the system architecture (`top_k=5` plus a single-answer generation prompt) is tuned for focused QA, not exhaustive listing. Diagnostic result: Azure appears inside the top-20 candidate pool but outside the final top-5 for the Microsoft revenue-source query, indicating a top-k/query-type sizing issue rather than a hard retrieval miss. Candidate fix: extend query decomposition to detect single-company enumeration queries, not only multi-company comparisons.
- Query decomposer now detects single-company enumeration and validates LLM-generated ticker/section fields before execution. Regression tests cover unsupported ticker leaks such as `NVDA` and mixed valid/invalid plans.
- Groq free tier can return `429 Too Many Requests`; SDK retries can recover, but latency may spike.
- Full 30-case Muc 3 evaluation could not complete under current Groq free-tier token limits. Retrying after quota exhaustion causes long waits and contaminates latency metrics, so official category-level results should be generated from a clean run after quota reset or with a lower-cost judge/model configuration.
- A historical 30-case evaluation run exhausted provider quotas within one session. The checkpoint/resume mechanism preserved partial completion (`13/30` OK in the first full Muc 3 run) without data loss. Full CI-style evaluation requires sufficient Groq quota or a paid tier.
- Initial Muc 4 diagnostics show that core AAPL/MSFT/AMZN financial statement rows are represented as native HTML `<table>` structures, but SEC table cells include spacer columns, separate `$`/`%` tokens, and non-fixed header row positions. Table-aware extraction must pattern-match content rather than hardcode row offsets.
- MSFT `Microsoft Cloud gross margin percentage` is not present as a numeric table in the raw filing; the numeric `69%` appears in MD&A prose. In the current corpus, percentage-derived metrics are often narrative MD&A content, while native tables primarily contain absolute financial values.

## Latest Step

Phase 2C Muc 3: Expanded evaluation set and decomposer-routed evaluation are partially evaluated.

Implemented evaluation behavior:

1. `src/evaluation/test_set.py` now contains 30 cases across six categories: `fact_lookup`, `summary`, `enumeration`, `comparative`, `multi_hop`, and `out_of_corpus`.
2. Each test case has `category` and `expects_decomposition` metadata.
3. `scripts/run_evaluation.py` routes every test case through `QueryDecomposer.run()` instead of directly calling `RAGPipeline.query()`.
4. Simple questions still use the normal RAG path because the decomposer returns `was_decomposed=False` and falls back internally.
5. Evaluation output now includes `DecompOK`, category summaries, sub-query metadata, answer text, and writes to `data/evaluation_results_v2.json`.
6. Out-of-corpus fallback failures log the actual answer for debugging.

Validation notes:

- The 3-company cybersecurity comparison returned 3 chunks each for AAPL, MSFT, and AMZN after fixing a shared-model thread-safety issue.
- Known limitation: Query decomposition dispatches sub-queries concurrently via `ThreadPoolExecutor`, but a global lock around `retrieve()` serializes model inference (`Embedder` + cross-encoder) to prevent a confirmed race condition in Nomic BERT's rotary embedding cache. Measured overhead: `2.98x` vs single query (`n=3` sub-queries), consistent with near-full serialization. Scoped locking around only `model.encode()` and `cross_encoder.predict()` would restore I/O-bound parallelism, but is deferred pending corpus expansion to validate the gain.
- Muc 2 Microsoft revenue-source diagnostic confirmed that Azure evidence chunks (`business_0006`, `business_0007`, `business_0008`) appear inside top-20 BM25 and semantic candidate pools, but not in top-3 for either method. This confirms an enumeration/query-shaping and final top-k issue, not a hard retrieval miss.
- Deterministic unit tests for decomposition planner validation pass: `6/6` in `tests/test_query_decomposer.py`. This protects the defense-in-depth guard that validates LLM structured output instead of trusting prompt-only constraints.
- Historical partial Muc 3 status: `13/30` cases had full judge scores and `17/30` were quota-skipped. The later official Groq-only N=30 run supersedes this snapshot.
- Partial category coverage with judge scores: `fact_lookup` `7/8` judged (`Faith=0.8571`, `Precision=0.8571`), `summary` `4/6` judged (`Faith=0.7500`, `Precision=0.7750`), `enumeration` `2/4` judged (`decomposition_correct=1.0000` for judged cases, `4/4` confirmed including judge-skipped generated records).
- Comparative and multi-hop quality are not fully measured yet: `comparative` has `0/6` judged but `3/6` generated records confirmed `decomposition_correct=True`; `multi_hop` has `0/3` judged and remains the highest-priority category to complete after quota reset.
- Out-of-corpus coverage is incomplete: Tesla and Google were skipped before answer generation; Nvidia generated a correct insufficient-information answer, and the new validation guard prevents unsupported ticker subqueries from being trusted going forward.

## Next Step

Phase 2D / Muc 4: Table-aware financial chunks are integrated as supplemental local artifacts.

Current diagnostic status:

- `src/ingestion/table_extractor.py` parses native SEC HTML financial tables into captioned markdown that preserves metric/year/value relationships.
- `src/ingestion/chunker.py` now has `build_table_chunks()`, which creates supplemental `financial_table` chunks. Existing `financial_statements` prose chunks are retained; parsed table chunks are additive, not replacements.
- `scripts/add_table_chunks.py` appends table chunks idempotently to existing `*_chunks.jsonl` files.
- Verified real-table rows: MSFT `Total revenue` maps to `281,724 / 245,122 / 211,915`, AAPL `Total net sales` maps to `416,161 / 391,035 / 383,285`, and AMZN `Total net sales` preserves the filing's `2023 -> 2024 -> 2025` year order.
- MSFT self-consistency check passes: product revenue plus service-and-other revenue equals total revenue for 2025, 2024, and 2023.
- Percentage-primary table handling is currently protected by a synthetic unit test only because the current corpus has no confirmed real percentage-primary financial table.
- Corrected full financial-section table scan results after following TOC `href` anchors and detecting years inside longer header cells: AAPL `22/33` tables parsed with rows, MSFT `36/51`, and AMZN `31/46`. Empty parses are still expected for layout, signature, glossary, and non-year-header tables, but some remaining empty tables contain real data with multi-level non-year headers and should be preserved through prose chunks if not parsed structurally.
- Table caption context is required metadata. Duplicate row labels such as AMZN `North America` / `International` / `AWS` refer to different financial concepts depending on nearby caption text, for example property and equipment by segment versus depreciation and amortization by segment.
- Local table chunk generation added AAPL `22`, MSFT `36`, and AMZN `31` `financial_table` chunks (`89` total). Chunk files now contain `360` records, up from `271`.
- Re-running `python -m scripts.embed_chunks` and `python -m scripts.index_chunks` embedded and indexed all `360` chunks. Qdrant collection `sec_filings` reports `points_count=360`.
- Retrieval smoke test with `ticker=AAPL`, `section=financial_table`, and `What was Apple's total net sales in fiscal year 2024?` returns clean table chunks containing `Total net sales | 416,161 | 391,035 | 383,285`. The broader question ranks net-sales breakdown tables first; adding `consolidated statements of operations` retrieves the income statement table as top-1.
- No-filter Apple fact lookup confirms automatic ranking improvement: for `What was Apple's total net sales in fiscal year 2024?`, `financial_table` ranks #1 and #2 (`CE=6.3033`, `5.1253`), ahead of `mdna` and `financial_statements` (`3.6-3.9`). The answer correctly returns `$391,035`.
- No-filter Apple multi-hop trend check succeeds: `How did Apple's total net sales trend from 2023 to 2025?` ranks `financial_table` #1 and #3 and answers all three values correctly (`383,285`, `391,035`, `416,161`). This is the first successful multi-hop-style live result recorded after the Muc 4 integration.
- New query-side limitation: `What is Amazon's AWS revenue growth?` still fails with no section filter because the relevant table chunks contain raw values but not the derived term `growth`. Rephrasing to include explicit years/metric, such as `AWS segment net sales 2024 2025 Amazon`, retrieves a `financial_table` chunk at rank #1. Candidate fix direction is query rewriting/expansion for growth/trend questions rather than extraction.
- AMZN table index `38` confirmed a two-level segment structure: one-cell segment headers (`North America`, `International`, `AWS`, `Consolidated`) followed by repeated metric rows (`Net sales`, `Operating expenses`, `Operating income`). The parser now carries segment headers forward into labels such as `AWS - Net sales`, preventing generic repeated labels.
- Minor parsing edge case: AMZN `International - Operating income (loss)` currently misses the 2023 negative value formatted as `( 2,656 )`. Likely cause is the parenthesized negative number being split across cells and partially treated as symbol-only text. This is lower priority than preserving segment labels because most financial table values are positive and the original prose chunks remain available as fallback.
- After the segment-label fix, local table chunks were regenerated by removing old `financial_table` chunks and appending the corrected ones: AAPL removed/appended `22`, MSFT `36`, AMZN `31` (`89` total). Chunk files remain at `360` records.
- Re-embedding and re-indexing after regeneration kept Qdrant stable at `points_count=360`, confirming no duplicate point growth.
- AWS growth retest after segment-prefix regeneration is unchanged: `What is Amazon's AWS revenue growth?` still retrieves `financial_statements_0007` only and returns an insufficient-information answer. This confirms the remaining issue is query phrasing/derived-metric expansion, not stale table labels.
- Post-Muc 4 evaluation preparation: 8 numeric-heavy `fact_lookup`/`multi_hop` cases in `src/evaluation/test_set.py` now use `section=None` instead of hardcoded `financial_statements`/`mdna`, allowing `financial_table` chunks to compete naturally during evaluation.
- Evaluation set now supports priority-based runs: `priority=1` is an 18-case quota-safe core set (`fact_lookup=4`, `summary=3`, `enumeration=4`, `comparative=3`, `multi_hop=3`, `out_of_corpus=1`), while `priority=2` restores the full 30-case set. Use `python -m scripts.run_evaluation --priority 1` for the core run and `--priority 2` for the full run.
- A historical full post-Muc 4 attempt was blocked by daily free-tier quotas. The later official Groq-only N=30 run supersedes it.
- Historical checkpoint backups remain local under `data/` and are not valid official benchmark inputs.

Recommended priorities:

1. Add query rewriting/expansion for growth/trend questions so terms like `growth` retrieve tables containing the underlying year-by-year values.
2. Decide whether API/UI should automatically search both `financial_table` and `financial_statements` for numeric financial questions or keep the new section as an explicit filter.
3. After quota reset, delete `data/eval_checkpoint.jsonl` from the blocked run and rerun `python -m scripts.run_evaluation --priority 1` to generate a clean core post-Muc 4 evaluation. Use `--priority 2` only when quota is sufficient for the full 30-case run.

Deferred production-quality item:

- The Vite frontend supersedes the deferred Streamlit UI plan and is now the demo/productization path.

Step 12: Docker packaging.

Recommended priorities:

1. Add a `Dockerfile` for FastAPI serving.
2. Add `.dockerignore` excluding `.env`, `data/`, caches, and local virtual environments.
3. Document how generated artifacts are provided or rebuilt for container use.

Financial table audit v2 and TOC-anchor counterfactual completed (2026-08-27). The read-only financial-table audit v2 (`scripts/diagnostics/financial_table_audit.py`, schema version 2) walked the production funnel (FS anchor → Item-8..Item-9 window tables → year-header row parsing → buildable chunks vs served artifacts) across all ten tickers lacking table chunks while hashing every read input before/after to prove `data/` immutability (`read_inputs_immutable: true`). Classification: CVX/IBM/JPM/XOM = `financial_statements_missing` (extraction-level incorporation-by-reference layouts; CVX/XOM/JPM show statement-analysis tables doc-wide but no Item-8 body; IBM's document has only 27 HTML tables total, so statements live in separate exhibits). NVDA/ORCL/PEP = `layout_or_exhibit`: their anchor-recovered FS text is real, but the table-discovery window anchored on the Item-8 stub text finds zero `<table>` elements while genuine statement tables exist elsewhere in each document (NVDA "Consolidated Statements of Income"/"Consolidated Balance Sheets"; ORCL statements-of-stockholders-equity region; PEP consolidated cash-flow tables). AVGO/HD = `layout_or_exhibit` plus `row_filter_miss` (real balance-sheet/equity/cash-flow tables sit outside the window; the single in-window table yields no year-header rows). GS = `layout_or_exhibit` with a 1,730-character incorporation-by-reference FS stub and ten statement-like tables elsewhere. Remediation ranking: (1) NVDA, (2) ORCL, (3) PEP — extend table discovery to reuse the same same-document TOC-anchor path the section recovery already resolves, which should expose existing statement tables without touching the extractor's text path; then AVGO/HD (window extension plus year-header tolerance), then GS (exhibit following), with CVX/IBM/JPM/XOM deferred to dedicated extraction work. Report stored under ignored `data/diagnostics/financial_table_audit.json` (schema version 2). Validation: targeted recovery/coverage tests pass `16/16`; full hermetic suite passes `331 passed`. The read-only counterfactual TOC-anchor diagnostic (`scripts/diagnostics/toc_anchor_counterfactual.py`) tested the alternative table-discovery path on NVDA/ORCL/PEP. ORCL passes all pre-registered PASS gates; NVDA fails on duplicate chunk IDs (same tables found via multiple TOC anchors); PEP fails on zero parsed/buildable chunks (tables lack year headers). Since the pre-registered gate required ALL three tickers to PASS, the conditional production TOC-anchor fallback is NOT merged. Report stored under ignored `data/diagnostics/toc_anchor_counterfactual.json`. Validation: targeted recovery/coverage tests pass `16/16`; full hermetic suite passes `331 passed`. The official N=30 benchmark remains a historical result of corpus `dc44c926…`: the Phase 1 artifact is now rebuilt on the new corpus but Phase 2 has not been rerun.
The current-corpus evaluation closure is complete. Phase 1 was rebuilt against the active IBM companion-recovery corpus with `--verify-determinism` after one-time Hugging Face metadata resolution via the explicit `--allow-network` escape hatch; the resulting artifact is byte-identical across both executions and has fingerprint `sha256:8283b628bb755b00bef86a26d7c608f9b385836c28dad588992b7d533ea51ee4`. It executes all `30/30` priority <= 2 cases with `61` non-empty queries and `12/12` decomposed-plan `evidence_ok` checks, bound to corpus `sha256:1d5b99ed…`, index manifest `sha256:5ac5362a…`, embedding `sha256:0c4ee351…`, reranker `sha256:16ff6fc9…`, retrieval config `sha256:6bf7801a…`, and test set `sha256:92dc7bc0…`. The two Phase 2 runners now pin this artifact and regression tests refuse the superseded hard-group artifact. The separate priority-3 replay covers `22` cases at keyword recall `1.0000`; IBM net-income retrieval required and now uses a caption-aware structured lookup preference for the consolidated income statement. No Phase 2 provider call or quota was consumed on this current binding; the published benchmark remains historical until a full Phase 2 run is intentionally authorized.
