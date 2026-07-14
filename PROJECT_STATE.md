# Project State

## Current Milestone

Steps 1-11 are complete for the MVP Enterprise Document QA / SEC 10-K RAG pipeline.
Phase 2A Step A, Streaming Response, is complete and verified.
Phase 2A Step A.1, Semantic Query Cache, is complete and verified.
Phase 2B Step C, Multi-turn Conversation with Memory, is complete and verified.
Phase 2B Step D, Query Decomposition, is integrated and verified for comparative queries.
Phase 2C Muc 2, deterministic evaluation metrics and enumeration retrieval diagnosis, is complete.
Phase 2C Muc 3, 30-case categorized evaluation set and decomposer-routed evaluation, is implemented. Full 30-case LLM-judge run is blocked by Groq free-tier quota.
Phase 2C Muc 4, financial table retrieval, is complete.
Phase 2C Muc 5, corpus expansion to 25 configured tickers, is locally ingested, chunked, embedded, and indexed with explicit corpus-quality reporting. The follow-up 50-company scale trial is also locally ingested and indexed, confirming that section extraction gaps persist at larger sample size.
Phase 2C Muc 7, Qdrant Cloud production configuration and migration, is implemented and verified.

Current Muc 7 Qdrant Cloud status:

- `configs/settings.py` supports `QDRANT_MODE`, `QDRANT_LOCAL_PATH`, `QDRANT_CLOUD_URL`, and `QDRANT_CLOUD_API_KEY`.
- `VectorStore` supports local persistent mode and Qdrant Cloud mode while preserving the old `VectorStore(path=...)` local call pattern.
- FastAPI startup, evaluation, and `scripts/diagnostics/rag_smoke_test.py` now use the configured Qdrant mode.
- `scripts/index_chunks.py` intentionally rebuilds only the local Qdrant index via `settings.qdrant_local_path` to avoid accidentally deleting a cloud collection.
- `scripts/migrate_to_qdrant_cloud.py` migrates the active local `sec_filings` collection to Qdrant Cloud. It upserts by default and only deletes/recreates the cloud collection when `--recreate` is explicitly passed.
- Qdrant Cloud migration completed for the earlier 25-company `sec_filings` snapshot: local points `3,944`, cloud points `3,944`. After the later 50-company local scale trial, local Qdrant has `7,142` points; Qdrant Cloud has not been remigrated for that expanded corpus.
- Qdrant Cloud required keyword payload indexes for filtered search; `ticker` and `section` indexes are now created by both `VectorStore.create_collection()` and the migration script.
- `scripts/verify_qdrant_cloud.py` compares local vs cloud top-5 chunk IDs for a smoke query after migration.
- Local-vs-cloud verification passed with exact top-5 match for `What was Apple's total net sales in 2024?` filtered to `AAPL`.
- README documents the Qdrant Cloud migration and verification flow.
- Validation after implementation: `.venv\Scripts\python.exe -m pytest tests/ -v` passes with `44 passed, 9 warnings`; `.venv\Scripts\python.exe -m compileall configs src scripts` passes.

Current corpus quality:

- 50-company scale trial completed locally with the current extractor and CUDA embedding environment.
- Text-section ingestion report: 35 `success`, 9 `degraded`, 6 `failed`, 25 `skipped_existing` on latest idempotent rerun.
- Clean for evaluation/demo requiring all four text sections: AAPL, MSFT, AMZN, GOOGL, META, TSLA, BAC, GS, BRK-B, JNJ, UNH, WMT, HD, AMD, QCOM, AVGO, TXN, CRM, V, MA, AXP, LLY, MRK, ABBV, TMO, PG, KO, NKE, CAT, BA, LMT, UPS, RTX, VZ, T.
- Degraded but usable for some section-specific questions: NVDA, JPM, PFE, XOM, CVX, ORCL, NOW, IBM, PEP.
- Unusable until extractor is improved: MS, MCD, INTC, COST, GE, HON. These have `sections={}` and 0 chunks.
- Qdrant local currently indexes 7,142 chunks from 44 tickers. The 6 unusable tickers are not represented in the vector index.
- `scripts/download_filings.py` now marks 0-section extraction as `failed` instead of successful/skipped, and marks partial section extraction as `degraded` with explicit missing-section warnings.
- Structural limitation identified: degraded/unusable filings commonly use incorporation-by-reference language and annual-report/page-reference layouts around Item 7 and Item 8. Examples include JPM Item 7/8 pointing to MD&A pages 46-160 and financial statements pages 162-314, XOM Item 7/8 pointing to the Financial Section, CVX Item 7/8 pointing to Financial Table of Contents entries, and MS/MCD/INTC using annual-report layouts where relevant content is not exposed through standard `Item 7 ... Item 8` boundaries. This is not just a missing regex keyword. Some content may still be present in the same primary HTML, while other filings may require following referenced exhibits or report sections. Supporting these cases requires a separate annual-report/table-of-contents aware ingestion/extraction pass, out of scope for the current single-document section extractor.
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
- Docker deployment decision: use `QDRANT_MODE=local`, bundling the Qdrant local data directory into the container or mounting it as a volume, not Qdrant Cloud as the default runtime target. Measured evidence with `candidate_pool=10`: Cloud search adds about `0.30s` per `retrieve()` call versus local (`~0.357s` cloud vs `~0.059s` local), and total retrieval is about `0.737s` cloud versus `0.444s` local. This overhead is not justified for a single-container demo/portfolio deployment where the main benefit of Cloud, avoiding local data packaging, does not offset the latency and external-service dependency. Qdrant Cloud setup from Muc 7 is retained as a documented, working alternative for multi-instance or production scenarios; local and cloud collections currently both contain `3,944` points and match in point count.
- Performance optimization round after Muc 7: `candidate_pool` was reduced from `20` to `10` and wired as the default after deterministic `recall_proxy` sweep across all measurable priority-1 categories, including comparative, showed no recall loss and about 49% lower local `retrieve()` time. Cross-encoder `batch_size` was empirically tuned from the SentenceTransformers default `32` to `4` across 7 batch sizes on 10 real candidate pairs after pool reduction; `batch_size=4` was fastest (`0.308s` average vs `0.355s` at `32`), consistent with the small candidate pool benefiting from less padding/allocation overhead per batch. Two suspected issues were investigated and rejected with evidence: model re-initialization per request is not happening (`Embedder` and cross-encoder init log count each `1` across 3 sequential real HTTP requests), and cross-encoder cold-start is negligible (5 consecutive real-pair calls stayed in the `0.343s-0.353s` range with no first-call outlier), so startup warm-up was not implemented. Combined result: local `retrieve()` latency reduced about 52% (`0.86s -> 0.41s`) with zero measured recall degradation across test categories. Further major gains require infrastructure changes such as GPU inference or multiple model instances, not more CPU-side parameter tuning.
- Structured lookup expanded to `total equity` in addition to total assets, total liabilities, and total revenue. Root-cause investigation of an initial replacement-character-looking display (`�`) showed it was a console rendering artifact, not data corruption: stored data correctly contains `U+2019` right single quote from original SEC HTML entity `&#8217;`. Added `_normalize_quotes()` so Unicode and ASCII apostrophes match uniformly across canonical label comparisons, preventing future false negatives from quote-style mismatches. Tests now cover equity subcomponents such as retained earnings and additional paid-in capital as negative cases, note-prefix `Commitments and contingencies (...) - Total ... equity` labels as positive cases, and Unicode-vs-ASCII apostrophe equivalence. Net income structured lookup expansion is deferred: unlike assets/liabilities/equity, the net income figure is numerically identical whether matched from the income statement row or the cash-flow reconciliation row, so the risk is citation clarity rather than answer correctness. Deterministic `recall_proxy` sweep after this expansion at `candidate_pool=10` showed no regression: comparative, fact_lookup, multi_hop, and summary remained `1.0000`, while enumeration stayed at its known pre-existing `0.8750`.
- Final backend evaluation after all retrieval, structured lookup, concurrency, and performance optimizations completed 18/18 priority-1 cases with Groq `llama-3.3-70b-versatile` as judge and no skipped records. Results: Faithfulness `0.8889`, Answer Relevancy `0.9278`, Context Precision `0.4556`, Overall `0.7574`, Citation Correctness `1.0000`, Recall Proxy `1.0000`, Fallback Accuracy `1.0000`. This supersedes the earlier `0.6898` overall / `0.4250` context-precision table because it includes the MSFT total-assets YoY structured-lookup fix, `candidate_pool=10`, and cross-encoder `batch_size=4`. Multi-hop improved most significantly: category faithfulness moved from `0.50` to `0.83`, relevancy from `0.67` to `0.93`, and precision from `0.27` to `0.43`; the MSFT YoY case now scores `1.00/1.00/0.50` with recall `1.00`, replacing the pre-structured-lookup `0.00/0.20/0.00` failure. Context Precision `0.4556` remains the primary known limitation: correct answers are reliably retrieved (`Recall Proxy=1.0000`) but accompanied by more context than strictly necessary, a structural property of cross-encoder re-ranking on financial documents rather than a recall failure.
- Broader priority <= 2 evaluation completed after moving to the Legion RTX 5060 environment. Command: `.venv\Scripts\python.exe -m scripts.run_evaluation --priority 2`. It completed 30/30 cases with no skipped records and saved results to `data/evaluation_results_v2.json`. Results: Faithfulness `0.8767`, Answer Relevancy `0.9100`, Context Precision `0.4453`, Overall `0.7440`, Citation Correctness `1.0000`, Recall Proxy `0.9583`, Fallback Accuracy `1.0000`. Category table: comparative `N=6` Faith `0.80` Relev `0.8667` Prec `0.4667` Recall `1.0000`; enumeration `N=4` Faith `0.8750` Relev `0.9000` Prec `0.5750` Recall `1.0000`; fact_lookup `N=8` Faith `0.9375` Relev `0.9375` Prec `0.3575` Recall `0.8750`; multi_hop `N=3` Faith `0.8333` Relev `0.9333` Prec `0.4333` Recall `1.0000`; out_of_corpus `N=3` Faith `1.0000` Relev `1.0000` Prec `0.0000`; summary `N=6` Faith `0.8333` Relev `0.8667` Prec `0.6833` Recall `1.0000`. This broader N=30 snapshot is better for README reporting than the N=18 priority-1-only table because category sample sizes improved for fact_lookup, summary, comparative, and out_of_corpus. The run also exposed one remaining narrow fact_lookup recall miss on `Who audited Microsoft's financial statements?`, lowering fact_lookup recall to `0.8750`. Latency from this run should not be used as a stable performance benchmark because Groq returned repeated `429 Too Many Requests` responses and SDK retry backoff inflated end-to-end timings.
- MSFT auditor miss from the N=30 run was investigated and fixed after the evaluation. Direct retrieval showed the wrong report-header chunk `MSFT_000095017025100235_financial_statements_0029` ranked first with CE score `4.5658`, while the correct Deloitte signature chunk `MSFT_000095017025100235_financial_statements_0031` was BM25 rank `49`, semantic rank `24`, and CE score `-10.2210` when forced into a larger candidate pool. Root cause: the auditor signature appears at the tail of a chunk whose leading text is about uncertain tax positions, so semantic/BM25/cross-encoder ranking prefers the report header even though it lacks the firm name. Apple auditor passed because its signature chunk ranked first and contained `Ernst & Young LLP`. Added an auditor-signature branch to `structured_lookup()` that activates only for auditor/report-signed financial-statement questions and promotes `financial_statements` chunks containing `/s/` plus `served as ... auditor since`. Targeted verification now answers `Deloitte & Touche LLP` and promotes `MSFT_000095017025100235_financial_statements_0031` to rank 1 with score `10.0000`; full test suite after the fix: `67 passed, 9 warnings`. The full N=30 evaluation table has not yet been rerun after this targeted fix, so the saved `0.9583` recall proxy remains the pre-fix measured table.
- Legion RTX 5060 environment is now configured for CUDA PyTorch. The previous `.venv` had CPU-only PyTorch (`torch 2.12.1+cpu`, `cuda available False`) despite `nvidia-smi` detecting the GPU. Reinstalled with `pip uninstall torch -y` followed by `pip install torch --index-url https://download.pytorch.org/whl/cu128`, yielding `torch 2.11.0+cu128`, CUDA `12.8`, and `NVIDIA GeForce RTX 5060 Laptop GPU`. Embedder now uses `cuda:0`. Measured embedding throughput on 100 real chunks improved from `37.65s` (`2.7 chunks/s`) on Legion CPU to `4.28s` (`23.3 chunks/s`) on GPU, implying roughly `12.8` minutes for an estimated `17,930` chunks / 100-company corpus embedding pass, excluding download/extraction time.

Latest completed milestone commit:

```text
e9692e1 Expand corpus ingestion
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
  Fixed 30-case categorized evaluation set covering fact lookup, summary, enumeration, comparative, multi-hop, and out-of-corpus fallback questions.
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

Dependencies added during Step 8/provider testing:

- `anthropic==0.111.0`
- `google-genai==2.9.0`
- `openai==2.43.0`
- `groq==1.5.0`

Current provider setup:

- Default provider: Groq.
- Default Groq model: `llama-3.3-70b-versatile`.
- Gemini provider is also supported.
- Default Gemini model: `gemini-2.5-flash-lite` for lower cost, but it returned temporary `503 UNAVAILABLE` during testing.
- `GROQ_API_KEY` and `GEMINI_API_KEY` are read from `.env` via `configs/settings.py`.

Provider status observed:

- Groq works with current key.
- Gemini `gemini-2.5-flash` worked in a small API test.
- Gemini `gemini-2.5-flash-lite` was selected for cost but returned `503 UNAVAILABLE` due to high demand in one test.
- Gemini older `2.0` models returned quota/permission issues for current key/project.
- OpenAI key currently appears to be an OpenRouter key (`sk-or-v1...`) and fails against OpenAI's default endpoint with `invalid_api_key`.

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

- `Generator.generate_stream()` streams tokens from the configured LLM provider.
- Groq streaming uses `client.chat.completions.create(..., stream=True)`, which matches the installed Groq SDK.
- Gemini streaming is implemented via `generate_content_stream()`.
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
python -m scripts.embed_chunks
python -m scripts.index_chunks
python -m scripts.diagnostics.rag_smoke_test
python -m scripts.run_evaluation
```

## Environment Variables

Currently supported in `configs/settings.py`:

```text
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=
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
anthropic==0.111.0
google-genai==2.9.0
openai==2.43.0
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
- A single 30-case evaluation run exhausted both Groq generation/planning quota and Gemini judge free-tier quota within one session. The checkpoint/resume mechanism preserved partial completion (`13/30` OK in the first full Muc 3 run) without data loss. Full CI-style evaluation requires quota reset across multiple sessions or a paid tier.
- Gemini Flash Lite may return temporary `503 UNAVAILABLE` under high demand.
- OpenAI key in the current environment was not a valid OpenAI Platform key during testing.
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
- Partial Muc 3 live evaluation status: `13/30` cases have full judge scores, `17/30` were skipped due to Groq generation/planning quota or Gemini judge quota. Checkpoint file `data/eval_checkpoint.jsonl` preserves completed cases; resuming only requires re-running `python -m scripts.run_evaluation` after quota reset.
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
- Full 30-case post-Muc 4 evaluation attempt is blocked by daily free-tier quotas. Gemini judge hit `GenerateRequestsPerDayPerProjectPerModel-FreeTier` (`20` requests/day), and Groq hit `100,000` tokens/day in the same session. Retry after provider daily reset.
- Checkpoint backups preserved locally: `data/eval_checkpoint_before_muc4.jsonl` contains the pre-Muc 4 partial baseline (`13/30` OK), and `data/eval_checkpoint_gemini_blocked.jsonl` contains this session's blocked post-Muc 4 attempt (`0/30` OK; skipped records only).

Recommended priorities:

1. Add query rewriting/expansion for growth/trend questions so terms like `growth` retrieve tables containing the underlying year-by-year values.
2. Decide whether API/UI should automatically search both `financial_table` and `financial_statements` for numeric financial questions or keep the new section as an explicit filter.
3. After quota reset, delete `data/eval_checkpoint.jsonl` from the blocked run and rerun `python -m scripts.run_evaluation --priority 1` to generate a clean core post-Muc 4 evaluation. Use `--priority 2` only when quota is sufficient for the full 30-case run.

Deferred production-quality item:

- Streamlit UI remains the next demo/productization step after the backend reasoning improvements.

Step 12: Docker packaging.

Recommended priorities:

1. Add a `Dockerfile` for FastAPI serving.
2. Add `.dockerignore` excluding `.env`, `data/`, caches, and local virtual environments.
3. Document how generated artifacts are provided or rebuilt for container use.
